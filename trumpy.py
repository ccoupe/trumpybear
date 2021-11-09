# trumpy.py TrumpyBear.
'''
  Trumpybear is multi-threaded.   MQTT message handlers will run code in
  different threads. The siren/alarm/tts are also rentrant since
  they can be stopped by another thread (mqtt message)
  JSON is usually sent and received from the mqtt broker topics.
  
  The front panel is a separate GUI program that uses MQTT to manage trumpybear
  manual control and tests. It is not synchronously coupled but does rely the
  state machines. There are state machines for 'normal', 'register', and 'mean'
  modes.  Hubitat (and Alexa via Hubitat) is also listening to the mqtt topics and
  sending some messages.  We don't know and cant know who sent the message
  (use mosquitto_pub cli for debugging, eh?).
  
  Mycroft interactions are also through MQTT (and a proxy program too)
  
  Remember - it's trumpybear. It doesn't need to be perfect - no one is 
  going to look at the code. Right? 
'''
import paho.mqtt.client as mqtt
import sys
import json
import argparse
import warnings
from datetime import datetime
import time, threading, sched
from threading import Lock, Thread
import socket
import os
import shutil
import traceback
from subprocess import Popen
from lib.Settings import Settings
from lib.Homie_MQTT import Homie_MQTT
from lib.Audio import AudioDev
from lib.Constants import State, Event, Role
from lib.TrumpyBear import TrumpyBear
import urllib.request
import logging
import logging.handlers
import numpy as np
import cv2
import imutils
from imutils.video import VideoStream
# Face Recognition uses
import websocket  # websocket-client
import base64

# Tracking uses:
from lib.ImageZMQ import imagezmq
import zmq

# globals
settings = None
hmqtt = None
debug_level = 1
applog = None
trumpy_state = None
trumpy_bear = None    # object of class TrumpyBear
sm_lock = Lock()      # state machine lock - only one thread at a time
waitcnt = 0
timerl_thread = None
registering = False
state_machine = None
video_dev = None
active_timer = None

play_mp3 = False
player_obj = None
zmqsender = None

class NuclearOption(Exception):
  pass
  


def mp3_player(fp):
  global player_obj, applog, audiodev
  cmd = f'{audiodev.play_mp3_cmd} {fp}'
  player_obj = Popen('exec ' + cmd, shell=True)
  player_obj.wait()

# Restore volume if it was changed
def player_reset():
  global settings, applog, audiodev
  if settings.player_vol != settings.player_vol_default and not audiodev.broken:
    applog.info(f'reset player vol to {settings.player_vol_default}')
    settings.player_vol = settings.player_vol_default
    audiodev.set_volume(settings.player_vol_default)

def playUrl(url):
  global hmqtt, audiodev, applog, settings, player_mp3, player_obj
  applog.info(f'playUrl: {url}')
  if url == 'off':
    if player_mp3 != True:
      return
    player_mp3 = False
    applog.info("killing tts")
    player_obj.terminate()
    player_reset()
    hmqtt.set_status("ready")
  else:
    try:
      urllib.request.urlretrieve(url, settings.tmpf)
    except:
      applog.warn(f"Failed download of {url}")
    hmqtt.set_status("busy")
    # change the volume?
    if settings.player_vol != settings.player_vol_default and not audiodev.broken:
      applog.info(f'set player vol to {settings.player_vol}')
      audiodev.set_volume(settings.player_vol)
    player_mp3 = True
    mp3_player(settings.tmpf)
    player_reset()
    hmqtt.set_status("ready")
    applog.info('tts finished')
  
# in order to kill a subprocess running mpg123 (in this case)
# we need a Popen object. I want the Shell too. 
playSiren = False
siren_obj = None

def siren_loop(fn):
  global playSiren, isDarwin, hmqtt, applog, siren_obj
  cmd = f'{audiodev.play_mp3_cmd} sirens/{fn}'
  while True:
    if playSiren == False:
      break
    siren_obj = Popen('exec ' + cmd, shell=True)
    siren_obj.wait()
    
# Restore volume if it was changed
def siren_reset():
  global settings, applog, audiodev
  if settings.siren_vol != settings.siren_vol_default and not audiodev.broken:
    applog.info(f'reset siren vol to {settings.siren_vol_default}')
    settings.siren_vol = settings.siren_vol_default
    audiodev.set_volume(settings.siren_vol_default)

def sirenCb(msg):
  global applog, hmqtt, playSiren, siren_obj, audiodev
  if msg == 'off':
    if playSiren == False:
      return
    playSiren = False
    hmqtt.set_status("ready")
    applog.info("killing siren")
    siren_obj.terminate()
    siren_reset()
  else:
    if settings.siren_vol != settings.siren_vol_default and not audiodev.broken:
      applog.info(f'set siren vol to {settings.siren_vol}')
      audiodev.set_volume(settings.siren_vol)
    if msg == 'on':
      fn = 'Siren.mp3'
    else:
      fn = msg
    applog.info(f'play siren: {fn}')
    hmqtt.set_status("busy")
    playSiren = True
    siren_loop(fn)
    siren_reset()
    applog.info('siren finished')
    hmqtt.set_status("ready")


play_chime = False
chime_obj = None

def chime_mp3(fp):
  global chime_obj, applog, audiodev
  cmd = f'{audiodev.play_mp3_cmd} {fp}'
  chime_obj = Popen('exec ' + cmd, shell=True)
  chime_obj.wait()

# Restore volume if it was changed
def chime_reset():
  global settings, applog, audiodev
  if settings.chime_vol != settings.chime_vol_default and not audiodev.broken:
    applog.info(f'reset chime vol to {settings.chime_vol_default}')
    settings.chime_vol = settings.chime_vol_default
    audiodev.set_volume(settings.chime_vol_default)

def chimeCb(msg):
  global applog, chime_obj, play_chime, settings, audiodev
  if msg == 'off':
    if play_chime != True:
      return
    play_chime = False
    applog.info("killing chime")
    chime_obj.terminate()
    chime_reset()
    hmqtt.set_status("ready")
  else:
    # if volume != volume_default, set new volume, temporary
    if settings.chime_vol != settings.chime_vol_default and not audiodev.broken:
      applog.info(f'set chime vol to {settings.chime_vol}')
      audiodev.set_volume(settings.chime_vol)
    flds = msg.split('-')
    num = int(flds[0].strip())
    nm = flds[1].strip()
    fn = 'chimes/' + nm + '.mp3'
    applog.info(f'play chime: {fn}')
    hmqtt.set_status("busy")
    play_chime = True
    chime_mp3(fn)
    chime_reset()
    hmqtt.set_status("ready")
    applog.info('chime finished')
  
    
# TODO: order Lasers with pan/tilt motors. Like the turrets? ;-)       
def strobeCb(msg):
  global applog, hmqtt
  applog.info(f'missing lasers for strobe {msg} Cheapskate!')

def start_muted():
  global applog, hmqtt
  applog.info(f'startup muting')
  hmqtt.display_cmd('off')
  hmqtt.tts_mute()

def main():
  global settings, hmqtt, applog, audiodev, trumpy_state
  global state_machine, video_dev, ml_dict
  # process cmdline arguments
  loglevels = ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL')
  ap = argparse.ArgumentParser()
  ap.add_argument("-c", "--conf", required=True, type=str,
    help="path and name of the json configuration file")
  ap.add_argument("-s", "--syslog", action = 'store_true',
    default=False, help="use syslog")
  ap.add_argument("-q", "--quiet", action = 'store_true',
    default=False, help="disable TTS")
  ap.add_argument("-d", "--debug", action='store', type=int, default='3',
    nargs='?', help="debug level, default is 3")
  ap.add_argument("-e", "--espeak", action = 'store_true',
    default=False, help="use espeak TTS")
  args = vars(ap.parse_args())
  
  # logging setup
  applog = logging.getLogger('trumpybear')
  #applog.setLevel(args['log'])
  if args['syslog']:
    applog.setLevel(logging.DEBUG)
    handler = logging.handlers.SysLogHandler(address = '/dev/log')
    # formatter for syslog (no date/time or appname. Just  msg, lux, luxavg
    formatter = logging.Formatter('%(name)s-%(levelname)-5s: %(message)-30s')
    handler.setFormatter(formatter)
    applog.addHandler(handler)
  else:
    logging.basicConfig(level=logging.DEBUG,datefmt="%H:%M:%S",format='%(asctime)s %(levelname)-5s %(message)-40s')
  
  audiodev = AudioDev()
  isDarwin = audiodev.isDarwin  
  state_machine = tame_machine
  
  settings = Settings(args["conf"], 
                      audiodev,
                      applog)
  hmqtt = Homie_MQTT(settings, 
                    playUrl,
                    chimeCb,
                    sirenCb,
                    strobeCb,
                    state_machine)
  settings.print()
  
    
  # TODO: minus style points here
  # set another callback function in the Mqtt Object for the TB state machine
  hmqtt.controller = trumpy_recieve
  
  # Setup video capture if not using a mqttcamera
  if settings.local_cam is not None:
    applog.info(f'Using local camera: {settings.local_cam}')
    video_dev = cv2.VideoCapture(settings.local_cam)
    video_dev.release()
  
  # Turn off display, mute mycroft
  th = threading.Timer(2 * 60, start_muted)
  th.start()
  
  state_machine(Event.start)
  # All we do now is loop over a 5 minute delay
  # and let the threads do the work.
  while True:
    time.sleep(5*60)

def new_sm(ns):
  global state_machine, trumpy_state, hmqtt
  state_machine = ns
  hmqtt.state_machine = ns
  trumpy_state = State.initialized
  
  
# Tame Mode state machine - deprecation begins. It was not a
# well thought out idea
def tame_machine(evt, arg=None):
  global applog, settings, hmqtt, trumpy_state, trumpy_bear
  global sm_lock
  cur_state = trumpy_state
  next_state = cur_state
  applog.debug("Tm entry {} {}".format(trumpy_state, evt))
  sm_lock.acquire()
  if evt == Event.start:
    next_state = State.starting
  elif evt == Event.motion:
    # ignore motion - stay in same state
    next_state = cur_state    
  elif evt == Event.abort:
    next_state = State.starting
  elif evt == Event.reply or evt == Event.pict:
    next_state = State.starting
  else:
    applog.info(f'unknown {evt} for tame mode')
    next_state = State.starting
  trumpy_state = next_state
  applog.debug("Tm exit {} {} => {}".format(cur_state, evt, trumpy_state))
  
  # unlock machine - now we can call long running things
  sm_lock.release()
  if trumpy_state == State.role_dispatch:
    # should not happen? 
    applog.info('tame: mic on')
    hmqtt.tts_unmute()
    tame_mycroft()

   
# The state machine controls the interaction with mycroft(replys),
# mqttcamera and other events. 
# BE WATCHFUL about threading
#  mqtt calls into state_machine() on it's thread(s). 
#  You can block it with a sleep(). That's OK in most situations. 
#  Most of the sleeps are ad hoc timing to keep mycroft
#  queue from building since it is LIFO
def mean_machine(evt, arg=None):
  global applog, settings, hmqtt, trumpy_state, trumpy_bear
  global sm_lock, waitcnt, playSiren, registering
  applog.debug("Sm entry {} {}".format(trumpy_state, evt))
  cur_state = trumpy_state
  # lock machine
  sm_lock.acquire()
  next_state = None
  if evt == Event.motion:
    next_state = cur_state 
  elif evt == Event.start:
    trumpy_state = State.starting
    next_state = State.waitrange
    waitcnt = 0
    hmqtt.set_status('running')
    hmqtt.tts_unmute()
    hmqtt.display_text('Trumpy Bear is awake')
    hmqtt.ask('awaken the hooligans')
    if settings.ranger_mode is not None:
      hmqtt.ranger_mode(settings.ranger_mode)
      hmqtt.start_ranger(75)
  elif evt == Event.reply:
    if arg != None:
      flds = arg.split('=')
      ans_typ = flds[0]
      if len(flds) == 2: arg = flds[1]
    else:
      applog.warn("null arg")
    if trumpy_state == State.aborting or trumpy_state == State.initialized:
      # This can happen when the switch is turned off and mycroft is
      # interacting (publishing to reply/set)
      applog.info('swallowing Event.reply in State.aborting')
      next_state = State.aborting
      #pass
    elif trumpy_state == State.waitname:
      # have a name. Maybe.
      if arg == None or arg == '':   
        if waitcnt < 2:
          next_state = State.waitname  # do over
          hmqtt.speak("I didn't catch that. Wait for the tone, Kay?")
          time.sleep(1)
          waitcnt += 1
          hmqtt.ask('awaken the hooligans')
        else:
          next_state = State.role_dispatch
          trumpy_bear.role = Role.unknown
      else:
        trumpy_bear = TrumpyBear(settings, arg)
        role = trumpy_bear.check_user(arg)
        # For Testing, force role.unknown
        # role = Role.unknown
        if role == Role.owner:
          hmqtt.speak(f"Verifying {trumpy_bear.name}")
          hmqtt.display_text(f"Verifying {trumpy_bear.name}")
        else:
          hmqtt.speak("I'm going to take your picture. Face the bear and stand up straight")
          hmqtt.display_text("Face the Bear")
          time.sleep(2)
        next_state = State.waitface
        request_picture('face')
    elif trumpy_state == State.four_qs:
      next_state = State.four_qs
      if ans_typ == 'ans1':
        trumpy_bear.ans1 = arg
        hmqtt.display_text('dialing..')
        time.sleep(2.0)
        hmqtt.display_text('connected..')
        time.sleep(3.0)
        hmqtt.display_text('On Their way')
      elif ans_typ == 'ans2':
        trumpy_bear.ans2 = arg
        time.sleep(2)
        hmqtt.display_text("Arming Defenses")
      elif ans_typ == 'ans3':
        trumpy_bear.ans3 = arg
        time.sleep(2)
        hmqtt.display_text('Music or Talk?')
      elif ans_typ == 'ans4':
        applog.debug(f"answered {arg}")
        trumpy_bear.ans4 = arg
        if arg == 'talk':
          # TODO: start mycroft 
          next_state = State.role_dispatch
        elif arg == 'music' or arg == None:
          # leave the state_machine cycle
          next_state = State.role_dispatch
        else:
          next_state = State.role_dispatch
      else:
        applog.warn(f'unknown ans {ans_typ} {arg}')
    else:
      applog.debug('no handler in {} for {}'.format(trumpy_state, evt))
  elif evt == Event.pict:
    if trumpy_state == State.aborting or trumpy_state == State.initialized:
      # This can happen when the picture is canceled by user action
      # interacting (publishing to reply/set)
      applog.info('swallowing Event.reply in State.aborting')
      next_state = State.aborting
    if trumpy_state == State.waitface:
      hmqtt.start_ranger(0);
      trumpy_bear.face_path = "/var/www/camera/face.jpg"
      aud_name = trumpy_bear.name
      # recognition is synchronous, not an event
      vis_name = do_recog(trumpy_bear)
      applog.debug(f'recognized {vis_name} using {aud_name}')
      if vis_name != None:
        vis_role = trumpy_bear.check_user(vis_name)
        if vis_role == Role.owner:
          trumpy_bear.name = aud_name
          trumpy_bear.check_user(aud_name)
        else:
          # camera overrides lying talkers.
          trumpy_bear.name = vis_name
      else:
        trumpy_bear.role = Role.unknown
      trumpy_bear.save_user()
      hmqtt.speak('Got it')
      if trumpy_bear.role == Role.unknown:
        time.sleep(1)
        next_state = State.four_qs 
        hmqtt.display_text('You are Unknown')
        hmqtt.ask('send in the terrapin')
      else:
        next_state = State.role_dispatch
        hmqtt.speak('Your access permissions are being checked, {}'.format(trumpy_bear.name))
        hmqtt.display_text('Hi {}'.format(trumpy_bear.name))
    else:
      applog.debug('no handler in {} for {}'.format(trumpy_state, evt))
  elif evt == Event.ranger:
    next_state = trumpy_state
    rng = int(arg)
    print(f'ranger stop at {rng}')
    if rng == 0:
      # timed out. The perp can't follow instructions
      next_state = State.role_dispatch
      trumpy_bear = TrumpyBear(settings, 'perp')
      hmqtt.speak('I asked nicely. Oh Well. Too Bad');
    if trumpy_state == State.waitrange:
      next_state = State.waitname

  elif evt == Event.abort:
    next_state = State.aborting
  elif evt == Event.watchdog:
    # TODO: implement. maybe.
    applog.debug('no handler in {} for {}'.format(trumpy_state, evt))
  
  else:
    applog.warn("Unhandled event: %s" % evt)
    
  # end the pass through the state machine
  trumpy_state = next_state
  applog.debug("Sm exit {} {} => {}".format(cur_state, evt, trumpy_state))
  # unlock machine
  sm_lock.release()
  if trumpy_state == State.aborting:
    trumpy_state = State.initialized
    interaction_canceled()
  if trumpy_state == State.role_dispatch:
    trumpy_state = State.initialized
    role_dispatch(trumpy_bear)

# Yes there is a lot of duplication. It's better than weird args and globals
# - we have enough of those.
def login_machine(evt, arg=None):
  global applog, settings, hmqtt, trumpy_state, trumpy_bear
  global sm_lock, waitcnt
  applog.debug("lm entry {} {}".format(trumpy_state, evt))
  cur_state = trumpy_state
  # lock machine
  sm_lock.acquire()
  next_state = None
  if evt == Event.abort:
    next_state = State.aborting
  elif evt == Event.motion:
    # ignore motion events
    next_state = cur_state 
  elif evt == Event.start:
    next_state = State.waitrecog
    time.sleep(1)
    trumpy_bear = TrumpyBear(settings, None)
    trumpy_bear.face_path = "/var/www/camera/face.jpg"
    if os.path.isfile(trumpy_bear.face_path):
      applog.info(f'removing old pict {trumpy_bear.face_path}')
      os.remove(trumpy_bear.face_path)
    else:
      applog.info(f'no file to delete {trumpy_bear.face_path}')
    request_picture('face')
  elif evt == Event.reply:
    # no voice replys
    next_state = cur_state
  elif evt == Event.pict:
    if trumpy_state == State.waitrecog:
      # doing a login
      # recognition is synchronous, not an event
      applog.debug(f'lm calling recog for {trumpy_bear}')
      vis_name = do_recog(trumpy_bear)
      applog.debug(f'recognized {vis_name}')
      if vis_name != None and vis_name != 'None':
        vis_role = trumpy_bear.check_user(vis_name)
        hmqtt.display_text(f'Hello {vis_name}. Unlocking')
        trumpy_bear.save_user()
        dt = {"cmd": "user", "user": vis_name, "role": vis_role}
        hmqtt.login(json.dumps(dt))
        logout_timer()
        next_state = State.starting
      else:
        # not a registered person - ignore
        hmqtt.display_text("I don't recognize you.")
        applog.info(f'unknown person ({vis_name}) attempting login')
        next_state = State.starting
    else:
      applog.debug(f'no handler in {trumpy_state} for {evt}')
  elif evt == Event.ranger:
    next_state = cur_state
  else:
    applog.warn(f"Unhandled event: {evt} in login_machine")

  trumpy_state = next_state
  applog.debug("lm exit {} {} => {}".format(cur_state, evt, trumpy_state))
  # unlock machine
  sm_lock.release()
  # nothing else to do for a panel login.
  if trumpy_state == State.aborting:
    trumpy_state = State.initialized
    trumpy_bear = None
  if trumpy_state == State.role_dispatch:
    trumpy_state = State.initialized
    trumpy_bear = None
    # role_dispatch(trumpy_bear) 

def register_machine(evt, arg=None):
  global applog, settings, hmqtt, trumpy_state, trumpy_bear
  global sm_lock, waitcnt
  applog.debug("rm entry {} {}".format(trumpy_state, evt))
  cur_state = trumpy_state
  # lock machine
  sm_lock.acquire()
  next_state = None
  if evt == Event.abort:
    next_state = State.aborting
  elif evt == Event.motion:
    # ignore motion events
    next_state = cur_state 
  elif evt == Event.start:
    trumpy_state = State.starting
    next_state = State.waitrange
    waitcnt = 0
    hmqtt.set_status('running')
    hmqtt.tts_unmute()
    hmqtt.display_text('Trumpy Bear is awake')
    #hmqtt.ask('awaken the hooligans')
    if settings.ranger_mode is not None:
      hmqtt.ranger_mode(settings.ranger_mode)
      hmqtt.start_ranger(75)
  elif evt == Event.reply:
    if arg != None:
      flds = arg.split('=')
      ans_typ = flds[0]
      if len(flds) == 2: arg = flds[1]
    else:
      applog.warn("null arg")
    if trumpy_state == State.aborting:
      # This can happen when the switch is turned off and mycroft is
      # interacting (publishing to reply/set)
      next_state = State.aborting
    elif trumpy_state == State.waitname:
      # have a name. Maybe.
      if arg == None or arg == '':   
        if waitcnt < 2:
          next_state = State.waitname  # do over
          hmqtt.speak("I didn't catch that. Wait for the tone, Kay?")
          time.sleep(1)
          waitcnt += 1
          hmqtt.ask('awaken the hooligans')
        else:
          hmqtt.speak("Too many failures to continue")
          hmqtt.display_text('Please retry from beginning')
          next_state = State.starting
      else:
        # Register
        trumpy_bear = TrumpyBear(settings, arg)
        role = trumpy_bear.check_user(arg)
        hmqtt.speak("I'm going to take your picture. Face the bear and stand up straight")
        hmqtt.display_text("Face the Bear")
        time.sleep(2)
        next_state = State.waitface
        request_picture('face')
  elif evt == Event.pict:
    if trumpy_state == State.waitface:
      name1 = trumpy_bear.name
      hmqtt.speak("Thank you")
      hmqtt.tts_mute()
      hmqtt.display_text(f"Saving {name1}'s picture")
      # finish registration - have face and picture.
      # send them to fc server
      trumpy_bear.face_path = "/var/www/camera/face.jpg"
      # save_recog(trumpy_bear) This should not be needed. TODO: delete.
      trumpy_bear.save_user()
      do_recog(trumpy_bear)
      if trumpy_bear.name == name1:
        hmqtt.display_text(f'Registered {trumpy_bear.name}')
        hmqtt.speak("Now try logging in by pushing the login button")
      else:
        hmqtt.speak("Your name doesn't match the picture. It can happen. Talk to Cecil")
        hmqtt.display_text("Please restart")
      next_state = State.starting
    else:
      applog.debug('no handler in {} for {}'.format(trumpy_state, evt))
  elif evt == Event.ranger:
    rng = int(arg)
    print(f'ranger stop at {rng}')
    if rng == 0:
      # ranger timed out. They didn't follow instructions
      next_state = State.aborting
      hmqtt.speak('Try Again');
    elif trumpy_state == State.waitrange:
      next_state = State.waitname
      hmqtt.ask('awaken the hooligans')

  elif evt == Event.abort:
    next_state = State.aborting
  elif evt == Event.watchdog:
    # TODO: implement. maybe.
    applog.debug('no handler in {} for {}'.format(trumpy_state, evt))
  else:
    applog.warn("Unhandled event: %s" % evt)

  trumpy_state = next_state
  applog.debug("rm exit {} {} => {}".format(cur_state, evt, trumpy_state))
  # unlock machine
  sm_lock.release()
  if trumpy_state == State.aborting:
    trumpy_state = State.initialized
    trumpy_bear = None
  if trumpy_state == State.role_dispatch:
    trumpy_state = State.initialized
    trumpy_bear = None

  
def role_dispatch(trumpy_bear):
  global applog
  role = trumpy_bear.role
  applog.info(f'Dispatch: {trumpy_bear.name} is {role}')
  if role == Role.player:
    begin_rasa(trumpy_bear)
  elif role == Role.friend or role == Role.aquaintance or role == Role.relative:
    begin_mycroft()
  elif role == Role.owner:
    hmqtt.speak("You are very annoying, {}. Are you with the failing New York Times?".format(trumpy_bear.name))
    interaction_finished()
  elif role == Role.unknown:
    if trumpy_bear.ans4 == 'talk':
      begin_mycroft()
    else:
      begin_intruder()
  else:
    interaction_finished()

def logout_timer_fired():
  global hmqtt, applog, active_timer
  hmqtt.login('{"cmd": "logout"}')
  hmqtt.display_cmd("off")
  applog.info('logging off')
  
def logout_timer(min=5):
  global active_timer
  print('creating logout timer')
  active_timer = threading.Timer(min * 60, logout_timer_fired)
  active_timer.start()
  
def extend_logout(min=3):
  global active_timer
  # cancel current timer
  if active_timer:
    print('reset logout timer')
    active_timer.cancel()
    active_timer = None
  logout_timer(min)
  
def long_timer_fired():
  print('timer_long fired')
  interaction_finished()

def long_timer(min=5):
  global timerl_thread
  print('creating long timer')
  timerl_thread = threading.Timer(min * 60, long_timer_fired)
  timerl_thread.start()

# called directly or via long_timer()
def interaction_finished():
  global hmqtt, warning_level, state_machine
  applog.info('closing interaction')
  hmqtt.tts_mute()
  hmqtt.display_cmd('off')
  hmqtt.set_status('ready')
  if state_machine == mean_machine:
    hmqtt.cops_arrive()
  new_sm(tame_machine)
  
def interaction_canceled():
  global hmqtt, warning_level, state_machine
  applog.info('canceled interaction')
  hmqtt.tts_mute()
  hmqtt.display_cmd('off')
  hmqtt.set_status('ready')
  new_sm(tame_machine)

def begin_mycroft():
  global hmqtt, applog
  applog.info('starting mean mycroft')
  hmqtt.tts_unmute()
  long_timer(2)
  hmqtt.speak('You have to say "Hey Mycroft", wait for the beep and then ask your question. \
  Try hey mycroft what about the lasers')
  hmqtt.display_text("say 'Hey Mycroft'")

def tame_mycroft():
  global hmqtt, applog
  applog.info('tame mycroft running')
  hmqtt.tts_unmute()
  long_timer(4)
  hmqtt.display_text("Mycroft Active")

def begin_rasa(tb):
  global hmqtt, applog
  applog.info('starting rasa')
  hmqtt.display_text(f"{tb.name} to see Mr. Sanders")
  #hmqtt.speak("Mister Sanders is not available {}. Try later.".format(tb.name))
  hmqtt.ask('Mister Sanders, {} is here'.format(tb.name))
  long_timer(1)
      
def begin_intruder():
  global applog, hmqtt
  applog.info('begin intruder')
  hmqtt.start_music_alarm()      # sets mqtt switch to wake up a HE rule
  hmqtt.display_text("Lasers are Tracking")
  begin_tracking(0.5, False, False);
  print('exiting intruder')
  long_timer(2)


# return name string or None for the picture (path) in 
# TrumpyBear object.
def do_recog(tb):
  global applog, settings
  applog.debug(f'get_face_name {tb.face_path}')
  bfr = open(tb.face_path, 'rb').read()
  # Use websocket-client, find one that is up and running.
  ws = websocket.WebSocket()
  for ip in settings.face_server_ip:
    try:
      uri = f'ws://{ip}:{settings.face_port}'
      applog.debug(f'do_recog() trying {ip}')
      ws.connect(uri, timeout=1)
      break
    except ConnectionRefusedError:
      applog.warning(f'Fail {ip} Switching to next backup')

  ws.send(base64.b64encode(bfr))
  reply = ws.recv()
  ws.close()

  js = json.loads(reply)
  details = js['details']
  mats = details['matrices']
  names = []
  for i in range(len(mats)):
    names.append(mats[i]['tag'])
  if len(names) == 0:
    names = [None]
  return names[0]
  
def request_picture(typ):
  global settings, hmqtt, applog, video_dev
  # get a picture from the camera
  topic = "homie/%s/control/cmd/set" % settings.homie_device
  path = f"/var/www/camera/{typ}.jpg"
  payload = {"reply": topic,
              "path": path}
  applog.debug(f"capture ask {settings.camera_topic} {json.dumps(payload)}")
  if settings.local_cam is None:
    hmqtt.client.publish(settings.camera_topic, 'capture='+json.dumps(payload))
  else:
    #th = Thread(target=capture_camera_capture_to_file, args=(json.dumps(payload),))
    #th.start()
    capture_camera_capture_to_file(json.dumps(payload))

def capture_read_cam(dim):
  global video_dev
  cnt = 0
  ret = False
  frame = None
  frame_n = None
  while cnt < 120:
    ret, frame = video_dev.read()
    if ret == True and np.shape(frame) != ():
      frame_n = cv2.resize(frame, dim)
      break
    cnt += 1
  if cnt >= 120:
    print("Crashing soon")
  return frame_n

def capture_camera_capture_to_file(jsonstr):
  global video_dev, applog, state_machine, hmqtt, settings
  args = json.loads(jsonstr)
  applog.debug("begin capture on demand")
  
  video_dev = cv2.VideoCapture(settings.local_cam)
  fr = capture_read_cam((640,480))
  cv2.imwrite(args['path'], fr)
  video_dev.release()
  applog.debug("local Capture to %s reply %s" % (args['path'], args['reply']))
  #state_machine(Event.pict)
  hmqtt.client.publish(args['reply'], json.dumps({"cmd": "capture_done"}))
  
def wakeup_mean():
  global settings, hmqtt, applog
  global pict_count
  global state_machine
  pict_count = 0
  new_sm(mean_machine)
  applog.info("Trumpy Bear awakens")
  hmqtt.tts_unmute()
  hmqtt.speak("Trumpy Bear sees you. Approach and face the Bear!")
  state_machine(Event.start)
  hmqtt.client.publish(settings.status_topic, 'awakens')
  # if w/o ranger
  if settings.ranger_mode == None:
    time.sleep(0.25)
    state_machine(Event.ranger, '75')

def wakeup_register():
  global settings, hmqtt, applog
  global pict_count
  global state_machine
  pict_count = 0
  time.sleep(1)
  new_sm(register_machine)
  applog.info("Trumpy Bear awakens")
  hmqtt.tts_unmute()
  state_machine(Event.start)
  hmqtt.client.publish(settings.status_topic, 'registering')
  
def wakeup_login():
  global settings, hmqtt, applog
  global pict_count
  global state_machine
  pict_count = 0
  time.sleep(1)
  new_sm(login_machine)
  applog.info("Trumpy Bear login attempt")
  state_machine(Event.start, 'login')
  hmqtt.client.publish(settings.status_topic, 'login')

def begin_logout():
  global settings, hmqtt, applog, tracking_stop_flag, tame_machine
  global state_machine
  hmqtt.display_cmd(self, 'off')
  tracking_stop_flag = True
  new_sm(tame_machine)
  
# the command channel controls the device from hubitat via mqtt
# AND from the Touch Screen (login) app
def trumpy_recieve(jsonstr):
  global settings, hmqtt, applog, trumpy_bear, trumpy_state
  global state_machine
  rargs = json.loads(jsonstr)
  cmd = rargs['cmd']
  if cmd == 'init':
    '''
    # hubitat can send an init, which can override camera motion sensor choice in json
    topic = rargs['reply']
    settings.camera_topic = 'homie/'+topic+'/motionsensor/control/set'
    settings.status_topic = 'homie/'+settings.homie_device+'/control/cmd'
    hmqtt.client.publish(settings.status_topic,'initialized')
    '''
    trumpy_state = State.initialized
  elif cmd == 'begin':
    # this came from hubitat (mqtt switchy alarmy driver thingy) OR debug with
    # mosquitto_pub -h pi4 -t homie/trumpy_bear/control/cmd/set -m '{"cmd": "begin"}'
    # wake up TrumpyBear (mean mode)
    wakeup_mean()
  elif cmd == 'login':
    wakeup_login()
  elif cmd == 'register':
    wakeup_register()
  elif cmd == 'end':
    # abort and reset. Hubitat can do this in a number of ways. 
    state_machine(Event.abort)
  elif cmd == 'capture_done':
    if state_machine is None:
      applog.warning('Cecil, init the state_machine')
    state_machine(Event.pict)
  elif cmd == 'keepalive':
    s = rargs.get('minutes', 2)
    extend_logout(s)
  elif cmd == 'mycroft':
      begin_mycroft()
  elif cmd == 'track':
    try:
      dbg = rargs.get('debug',False)
      test = rargs.get('test',False)
      applog.info('calling begin_tracking')
      begin_tracking(0.1, dbg, test)
    except:
      traceback.print_exc()
  elif cmd == 'calib':
    begin_calibrate(rargs['distance'],rargs['time'])
  elif cmd == 'closing':
    # Front panel logoff - probably manual.
    begin_logout
  elif cmd == 'get_turrets':
    dt = {'cmd': 'set_turrets', 'turrets': settings.turrets}
    hmqtt.login(json.dumps(dt))
  elif cmd == 'alarm':
    #TODO not needed? HE already knows? 
    pass
    
  
def image_serialize(frame):
  image = frame 
  _, jpg = cv2.imencode('.jpg',image)
  bfr = jpg.tostring()
  return bfr

'''
def motion_track_rpc(display):
  global tracking_stop_flag, video_dev, ml_dict, applog
  global settings
  # camera warmup time:
  #applog.info('motion_track_rpc called')
  time.sleep(1)
  mlobj = ml_dict['Cnn_Shapes']
  rc = settings.use_ml == 'remote_rpc'
  cnt = 0
  hits = 0
  applog.info(f'begin rpc loop: {tracking_stop_flag}')
  while not tracking_stop_flag:
    tf, frame = video_dev.read()
    if not tf:
      applog.info('failed camera read')
      continue
    cnt += 1
    if rc: 
      # send frame to rpc, get back a (boolean, rect) if true, then rect is good
      found, rect = mlobj.proxy.root.detectors (settings.ml_algo, False, 
          settings.confidence, image_serialize(frame))
    else:
      applog.info(f'lcl processing frame {cnt} {type(mlobj)}')
      found, rect = mlobj.proxy(settings.ml_algo, False, 
          settings.confidence, frame)
    if found: 
      (x, y, ex, ey) = rect     
      hits += 1 
      #!! json does not handle numpy int64's. Convert to int.
      dt = {'cmd': "trk", 'cnt': cnt, "x": int(x), "y": int(y), "ex": int(ex), "ey": int(ey)}
      jstr = json.dumps(dt)
      for tur in settings.turrets: 
        hmqtt.client.publish(f"{tur['topic']}/set", jstr)
       
      cv2.rectangle(frame,(x,y),(ex,ey),(0,255,210),4)
      if display:
        dt = {'cmd': 'tracking', 'msg': jstr} 
        hmqtt.login(json.dumps(dt))
    
  applog.info(f'ending rpc loop {cnt} frames {cnt/120} fps for {hits}')
  video_dev.release()
'''

'''
Zmq Trickiness: We can't detect that the zmq 'hub' is not answering
until we try to send to it AND it times out. Then we can try a different
Server. The working tracker will notify Kodi or Front Panel mpeg playes
so we don't have to do that here.

Beware: The tracker(s) are listening on a mqtt topic so they will both run
AND they will init and wait in their respective create_stream(). If they are both running
only the first will be sent images. If the first one doesn't respond then
the second one will be sent the images. This COULD leave a clean up problem.


'''
zmqsender = None
zmqSenderIdx = 0
zmqDebug = False
zmqPanel = True

def motion_track_zmq(display, panel):
  global tracking_stop_flag, video_dev, zmqsender, zmqSenderIdx, applog
  global settings
  applog.info('motion_track_zmq called')
  time.sleep(1)
  jpeg_quality = 95
  cnt = 0
  while not tracking_stop_flag:
    tf, frame = video_dev.read()
    if not tf:
      applog.info('failed camera read')
      continue
    cnt += 1
    ret_code, jpg_buffer = cv2.imencode(
            ".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), jpeg_quality])
    try:
      zmqsender.send_jpg('trumpy4', jpg_buffer)
    except (zmq.ZMQError, zmq.ContextTerminated):
      # Try the first available zmq hub. Will drop the frame on retry.
      set_zmqSender()
      applog.info(f'failed sending frame# {cnt} trying next server')
      traceback.print_exc()
      
    #applog.info(f'sent {cnt}')
  
  applog.info(f'closing image socket, {cnt} , {cnt/120} fps')
  #zmqsender.close() # There is no close(). 
  zmqsender = None
  zmqSenderIdx = 0
  video_dev.release()
  
def tracking_timer(minutes=0.5,testing=False):
  print('creating tracking timer')
  tracking_thread = threading.Timer(minutes * 60, tracking_finished, args=(testing,))
  tracking_thread.start()

'''
def pick_imagezmq(ips, port):
  global applog
  # returns open and workable zeromq sender given list to try
  for ip in ips:
    try:
      uri = f'tcp://{ip}:{port}'
      applog.info(f'trying tracker at {uri}')
      zmq = imagezmq.ImageSender(connect_to=uri)
      applog.info(f'connected to {uri}')
      return zmq
    except (KeyboardInterrupt, SystemExit):
      return nil  # Ctrl-C was pressed to end program
    except  Exception as ex: 
      applog.debug('its a', ex)
      traceback.print_exc()
      continue
'''
def set_zmqSender():
  global settings, zmqsender, zmqSenderIdx, zmqDebug, zmqPanel
  if zmqSenderIdx < len(settings.zmq_tracker_ip):
    uri = f'tcp://{settings.zmq_tracker_ip[zmqSenderIdx]}:{settings.zmq_port}'
    hmqtt.tracker(json.dumps({'begin':settings.zmq_tracker_ip[zmqSenderIdx],
        'debug': zmgDebug, 'panel': zmqPanel}))
    applog.info(f'trying tracker at {uri}')
    zmqsender = imagezmq.ImageSender(connect_to=uri, send_timeout=0.100, recv_timeout=0.100)
    zmqSenderIdx += 1
    return 
  else:
    # out of servers to try.
    raise NuclearOption
    

# it gets complicated. we need some time for the server to get
# cranking
def begin_tracking(delay=0.1, debug=False, test=False):
  global hmqtt, applog, settings, tracking_stop_flag, video_dev
  global zmqsender, zmqSenderIdx, zmqDebug, zmqPanel
  # open the camera 
  video_dev = cv2.VideoCapture(settings.local_cam)
  video_dev.set(3, 640)
  video_dev.set(4, 480)
  # TODO: move hmqtt.tracker() call to inside zmqSender() ? 
  time.sleep(2) # 2 sec for camera to settle and for server to set up
  try:
    if settings.use_ml == 'remote_zmq': 
      zmqSenderIdx = 0
      zmqDebug = debug
      zmqPanel = test
      set_zmqSender()
      
    applog.info("trumpy begin tracking thread")
    tracking_stop_flag = False
    tracking_timer(delay, testing=test)
    if settings.use_ml == 'remote_zmq':
      trk_thread = Thread(target=motion_track_zmq, args=(debug,test))
    #elif settings.use_ml == 'remote_rpc':
    #  trk_thread = Thread(target=motion_track_rpc, args=(debug,test))
    trk_thread.start()
  except:
    traceback.print_exc()
  
def tracking_finished(test):
  global tracking_stop_flag, applog, settings, hmqtt
  tracking_stop_flag = True
  applog.info('tracking timer fired')
  hmqtt.tracker(json.dumps({'end':True,'panel':test}))

    
def calib_machine(evt, arg=None):
  global sm_lock, trumpy_state, calib_distance
  applog.debug("cm entry {} {}".format(trumpy_state, evt))
  cur_state = trumpy_state
  # lock machine
  sm_lock.acquire()
  next_state = None
  if evt == Event.abort:
    next_state = State.aborting
  elif evt == Event.ranger:
    next_state = trumpy_state
    calib_distance = int(arg)
  else:
    applog.info('unknown state for calib mode')
  trumpy_state = next_state
  applog.debug("cm exit {} {} => {}".format(cur_state, evt, trumpy_state))
  
  # unlock machine - now we can call long running things
  sm_lock.release()


def begin_calibrate(meters, secs):
  global settings, hmqtt, video_dev, applog, state_machine, ml_dict
  # create directory for 'meters' arg. Holds pict<n>.jpg and data.csv
  # files. 
  if settings.local_cam is None:
    applog.warn('The camera must be owned by TrumpyBear')
    return
  from os import path
  path  = f'{os.getenv("HOME")}/.calib/{meters}M'
  if os.path.isdir(path):
    shutil.rmtree(path)
  os.makedirs(path)
  csv_path = f'{path}/data.csv'
  csvf = open(csv_path, mode='w')
  applog.info(f'Begin {meters} Meter sweep for {secs}')
  # csv format: f'{cnt}, {fr_num}, {range}, {x}, {y}, {ex}, {ey}, {area}, {ctr_x}, {ctr_y}
  # open camera, wait for two secs to warmup and human move to place.
  video_dev = cv2.VideoCapture(settings.local_cam)
  video_dev.set(3, 640)
  video_dev.set(4, 480)
  mlobj = ml_dict['Cnn_Shapes']

  time.sleep(1+meters)
  # compute ending time.
  now = time.time()
  et = now + secs
  applog.info(f'begin {time.time()} --> {et}')
  # Need a new state machine for dealing with Evt.Ranger coming in aysnchronously
  #old_machine = state_machine # save current
  #new_sm(calib_machine)
  # turn on ranger.
  
  frnum = 0
  cnt = 0
  rc = settings.use_ml == 'remote_rpc'
  #rc = False
  while time.time() <= et:
    tf, frame = video_dev.read()
    if tf is None:
      # trouble ahead
      applog.info('failed to get frame')
      break
    
    frnum += 1
    applog.info(f'have frame {frnum} {type(mlobj)}')
    # get a recog rect
    
    if rc:
      # send frame to rpc, get back a (boolean, rect) if true, then rect is good
      found, rect = mlobj.proxy.root.detectors (settings.ml_algo, False, 
          settings.confidence, image_serialize(frame))
    else:
      found, rect = mlobj.proxy(settings.ml_algo, False, 
          settings.confidence, frame)
    if found: 
      #print(f'{type(rect)} {rect}')
      (x, y, ex, ey) = rect
      cv2.rectangle(frame,(x,y),(ex,ey),(0,255,210),4)
      cnt += 1
      # save pict
      fn = f'{path}/pict{cnt}.jpg'
      cv2.imwrite(fn, frame)
      w = ex - x
      h = ey - y
      ctr_x = int((w / 2) + x)
      ctr_y = int((h / 2) + y)
      # append to data file
      msg = f'{frnum},{cnt},{x},{y},{ex},{ey},{w*h},{ctr_x},{ctr_y}'
      csvf.write(f'{msg},{fn}\n')
      #dt = {'cmd': 'tracking', 'msg': msg} 
      #hmqtt.login(json.dumps(dt))
      
  applog.info('closing sweep')
  # close data file
  csvf.close()
  # close video_dev
  video_dev.release()
  # turn off ranger.
  # reset statemachine

  new_sm(old_machine)
if __name__ == '__main__':
  sys.exit(main())
