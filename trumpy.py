#!/usr/bin/env python3
#
# Trumpybear is multi-threaded. MQTT message handler will run code in
# this file under a different thread. The siren/alarm/tts are rentrant since
# they can be stopped by another thread (mqtt message)
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
import rpyc

# globals
settings = None
hmqtt = None
debug_level = 1
applog = None
trumpy_state = None
trumpy_bear = None    # object of class TrumpyBear
sm_lock = Lock()      # state machine lock - only one thread at a time
face_proxy = None
waitcnt = 0
timerl_thread = None
registering = False
state_machine = None



play_mp3 = False
player_obj = None

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
  
    
# TODO: order Lasers with pan/tilt motors. ;-)       
def strobeCb(msg):
  global applog, hmqtt
  applog.info(f'missing lasers for strobe {msg} Cheapskate!')

  
def main():
  global settings, hmqtt, applog, face_proxy, audiodev, trumpy_state
  global state_machine
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
  
  # connect to the face recogition server
  face_proxy = rpyc.connect(settings.face_server_ip, settings.face_port, 
          config={'allow_public_attrs': True})
  # Turn off display, mute mycroft
  hmqtt.display_cmd('off')
  hmqtt.tts_mute()
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
  
  
# Tame Mode state machine (
def tame_machine(evt, arg=None):
  global applog, settings, hmqtt, trumpy_state, trumpy_bear
  global tm_lock
  cur_state = trumpy_state
  next_state = cur_state
  applog.debug("Tm entry {} {}".format(trumpy_state, evt))
  sm_lock.acquire()
  if evt == Event.start:
    next_state = State.starting
  elif evt == Event.motion:
    # generally, ignore motion - stay in same state
    next_state = cur_state
    if cur_state == State.starting:
      if arg == 'true':
        applog.info('Call ranger for distance')
        time.sleep(1) # time to get in place and stand still
        next_state = State.waitrange
        hmqtt.ranger_mode('snap')
      else:
        next_state = State.starting
    elif cur_state == State.role_dispatch:
      # typically motion = false
      next_state = State.starting
  elif evt == Event.ranger:
    d = int(arg)
    if cur_state == State.waitrange:
      applog.info(f'ranger reports {arg}')
      if d >= 300:
        # nowhere near close enough
        hmqtt.display_cmd('off')
        next_state = State.starting
      elif d < 300 and d > 150:
        # loop in this state 
        time.sleep(0.1)
        applog.info('ranger looping')
        hmqtt.display_text('Approach')
        next_state = State.waitrange
        hmqtt.ranger_mode('snap')
      elif d < 150:
        applog.info(f'Close enough {d}')
        role = Role.owner
        next_state = State.waitface
        request_picture('face')
    else:
      next_state = State.starting
  elif evt == Event.pict:
    if cur_state == State.waitface:
      if trumpy_bear is None:
        trumpy_bear = TrumpyBear(settings, arg)
      trumpy_bear.face_path = "/var/www/camera/face.jpg"
      # recognition is synchronous, not an event
      vis_name = do_recog(trumpy_bear)
      applog.debug(f'recognized {vis_name}')
      if vis_name != None:
        # we have a 'registered' user.
        hmqtt.display_text(f'Hi {vis_name}')
        next_state = State.role_dispatch
      else:
        hmqtt.display_text('Sorry')
        next_state = State.starting
    else:
      applog.debug(f'unknown state for {evt}')
      
  elif evt == Event.abort:
    next_state = State.starting
  else:
    applog.info('unknown state for tame mode')
  trumpy_state = next_state
  applog.debug("Tm exit {} {} => {}".format(cur_state, evt, trumpy_state))
  
  # unlock machine - now we can call long running things
  sm_lock.release()
  if trumpy_state == State.role_dispatch:
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
    interaction_finished()
  if trumpy_state == State.role_dispatch:
    trumpy_state = State.initialized
    role_dispatch(trumpy_bear)

# Yes there is a lot of duplication. It's better than weird args and globals
# - we have enough of those.
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
    if arg == 'login':
      next_state = State.waitrecog
      time.sleep(1)
      request_picture('face')
    else:
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
        time.sleep(3)
        next_state = State.waitface
        request_picture('face')
  elif evt == Event.pict:
    if trumpy_state == State.waitrecog:
      # doing a login? 
      hmqtt.start_ranger(0);  # zero stops ranger.
      trumpy_bear = TrumpyBear(settings,None)
      trumpy_bear.face_path = "/var/www/camera/face.jpg"
      #aud_name = trumpy_bear.name
      # recognition is synchronous, not an event
      vis_name = do_recog(trumpy_bear)
      applog.debug(f'recognized {vis_name}')
      if vis_name != None:
        vis_role = trumpy_bear.check_user(vis_name)
        if vis_role != Role.unknown:
          hmqtt.display_text(f'Hello {vis_name}. Unlocking')
          dt = {"cmd": "user", "user": vis_name, "role": vis_role}
          hmqtt.login(json.dumps(dt))
          logout_timer()
          next_state = State.starting
      else:
        # not a registered person - ignore
        hmqtt.display_text("I don't recognize you.")
        logout_timer()
        next_state = State.starting
    elif trumpy_state == State.waitface:
      # finish registration - have face and picture.
      # send them to fc server
      trumpy_bear.face_path = "/var/www/camera/face.jpg"
      save_recog(trumpy_bear)
      hmqtt.display_text(f'Registered {trumpy_bear.name}')
      dt = {"cmd": "user", "user": trumpy_bear.name, "role": Role.aquaintance}
      hmqtt.login(json.dumps(dt))
      logout_timer()
      next_state = State.starting
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
    interaction_finished()
  if trumpy_state == State.role_dispatch:
    trumpy_state = State.initialized
    role_dispatch(trumpy_bear)
  
def role_dispatch(trumpy_bear):
  role = trumpy_bear.role
  print('Dispatch:', trumpy_bear.name,"is",role)
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
  global hmqtt, applog
  hmqtt.login('{"cmd": "logout"}')
  hmqtt.display_cmd("off")
  applog.info('logging off')
  
def logout_timer(min=5):
  print('creating logout timer')
  th = threading.Timer(min * 60, logout_timer_fired)
  th.start()
  
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
  global hmqtt, warning_level
  applog.info('closing interaction')
  hmqtt.tts_mute()
  hmqtt.display_cmd('off')
  hmqtt.set_status('ready')
  new_sm(tame_machine)

def begin_mycroft():
  global hmqtt
  applog.info('starting mycroft')
  long_timer(4)
  hmqtt.speak('You have to say "Hey Mycroft", wait for the beep and then ask your question. \
  Try hey mycroft what about the lasers')
  hmqtt.display_text("say 'Hey Mycroft'")

def tame_mycroft():
  global hmqtt
  applog.info('tame mycroft running')
  long_timer(4)
  hmqtt.display_text("Mycroft Active")

def begin_rasa(tb):
  global hmqtt
  print('starting rasa')
  hmqtt.display_text(f"{tb.name} to see Mr. Sanders")
  #hmqtt.speak("Mister Sanders is not available {}. Try later.".format(tb.name))
  hmqtt.ask('Mister Sanders, {} is here'.format(tb.name))
  long_timer(1)
      
def begin_intruder():
  print('begin intruder')
  hmqtt.enable_player()      # sets mqtt switch to wake up a HE RM rule
  cnt = 0
  while cnt < 31:
    print("intruder", cnt)
    hmqtt.display_text("Hands Up")
    time.sleep(1)
    hmqtt.display_text("On Your Knees")
    time.sleep(1)
    cnt += 1
  print('exiting intruder')
  long_timer(2)

# return name string or None for the picture (path) in 
# TrumpyBear object.
def do_recog(tb):
  global face_proxy
  print('get_face_name {}'.format(tb.face_path))
  bfr = open(tb.face_path, 'rb').read()
  # call remote
  result = face_proxy.root.face_recog(bfr)
  return result

def save_recog(tb):
  global face_proxy
  print(f'save_face: {tb.name}, {tb.face_path}')
  bfr = open(tb.face_path, 'rb').read()
  result = face_proxy.root.save_recog(tb.name, bfr)
  return result
    
def request_picture(typ):
  global settings, hmqtt, applog
  # get a picture from the camera
  topic = "homie/%s/control/cmd/set" % settings.homie_device
  payload = { "reply": topic,
              "path": "/var/www/camera/{}.jpg".format(typ) }
  applog.debug("capture ask %s %s" % (settings.camera_topic, json.dumps(payload)))
  hmqtt.client.publish(settings.camera_topic, 'capture='+json.dumps(payload))

    
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
  new_sm(register_machine)
  applog.info("Trumpy Bear login attempt")
  state_machine(Event.start, 'login')
  hmqtt.client.publish(settings.status_topic, 'login')


# the command channel controls the device from hubitat via mqtt
def trumpy_recieve(jsonstr):
  global settings, hmqtt, applog, trumpy_bear, trumpy_state
  global state_machine
  rargs = json.loads(jsonstr)
  cmd = rargs['cmd']
  if cmd == 'init':
    # hubitat can send an init, can override camera motion sensor choice in json
    topic = rargs['reply']
    settings.camera_topic = 'homie/'+topic+'/motionsensor/control/set'
    settings.status_topic = 'homie/'+settings.homie_device+'/control/cmd'
    hmqtt.client.publish(settings.status_topic,'initialized')
    trumpy_state = State.initialized
  elif cmd == 'begin':
    # this came from hubitat (mqtt switchy alarmy driver thingy) OR debug with
    # mosquitto_pub -h pi4 -t homie/trumpy_bear/control/cmd/set -m '{"cmd": "begin"}'
    # wake up TrumpyBear
    wakeup_mean()
  elif cmd == 'login':
    wakeup_login()
  elif cmd == 'register':
    wakeup_register()
  elif cmd == 'end':
    # kill and reset
    state_machine(Event.abort)
  elif cmd == 'capture_done':
    if state_machine is None:
      applog.warning('Cecil, init the state_machine')
    state_machine(Event.pict)
  elif cmd == 'mycroft':
      hmqtt.tts_unmute()
      begin_mycroft()
  elif cmd == 'alarm':
    #TODO not needed? my_tts(rargs['text'])
    pass
  

  
if __name__ == '__main__':
  sys.exit(main())
