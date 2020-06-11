#!/usr/bin/env python3
#
# Trumpybear is multi-threaded. MQTT message handler will run code in
# this file under a different thread. The siren/alarm are rentrant since
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
isPi = False
applog = None
trumpy_state = None
trumpy_bear = None    # object of class TrumpyBear
sm_lock = Lock()      # state machine lock - only one thread at a time
face_proxy = None
waitcnt = 0


def playUrl(url):
  global hmqtt, isPi, applog
  applog.info("playUrl: %s" % url)
  if True:
    try:
      urllib.request.urlretrieve(url, "tmp.mp3")
    except:
      applog.warn("Failed download")
    url = "tmp.mp3"
  #synchronous playback
  hmqtt.set_status("busy")
  os.system('mpg123 -q --no-control tmp.mp3')
  hmqtt.set_status("ready")
  #hmqtt.client.loop()
  
# in order to kill a subprocess running mpg123 (in this case)
# we need a Popen object. I want a Shell too. 
playSiren = False
sirenThread = None
siren_obj = None

def siren_loop(fn):
  global playSiren, isPi, hmqtt, applog, siren_obj
  while True:
    if playSiren == False:
      break
    cmd = f'mpg123 -q --no-control chimes/{fn}'
    siren_obj = Popen('exec ' + cmd, shell=True)
    siren_obj.wait()

def sirenCb(msg):
  global applog, isPi, hmqtt, playSiren, sirenThread, siren_obj
  if msg == 'off':
    if playSiren == False:
      return
    playSiren = False
    hmqtt.set_status("ready")
    applog.info("killing siren")
    siren_obj.terminate()
  else:
    if msg == 'on':
      fn = 'Siren.mp3'
    else:
      fn = msg
    applog.info(f'play siren: {fn}')
    hmqtt.set_status("busy")
    playSiren = True
    siren_loop(fn)
    #sirenThread = Thread(target=siren_loop, args=(fn,))
    #sirenThread.start()


play_chime = False
#chime_thread = None
chime_obj = None

def chime_mp3(fp):
  global chime_obj, applog
  cmd = f'mpg123 -q --no-control {fp}'
  chime_obj = Popen('exec ' + cmd, shell=True)
  chime_obj.wait()

def chimeCb(msg):
  global applog, _obj, play_chime
  if msg == 'off':
    if play_chime != True:
      return
    play_chime = False
    hmqtt.set_status("ready")
    applog.info("killing chime")
    chime_obj.terminate()
  else:
    flds = msg.split('-')
    num = int(flds[0].strip())
    nm = flds[1].strip()
    fn = 'chimes/' + nm + '.mp3'
    applog.info(f'play chime: {fn}')
    hmqtt.set_status("busy")
    play_chime = True
    chime_mp3(fn)
    #chime_thread = Thread(target=chime_mp3, args=(fn,))
    #chime_thread.start()

  
    
# TODO: order Lasers with rotating/pan motors. ;-)       
def strobeCb(msg):
  global applog, isPi, hmqtt
  applog.info(f'missing lasers for strobe {msg} Cheapskate!')

  
def main():
  global isPi, settings, hmqtt, applog, face_proxy
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
  applog = logging.getLogger('mqttplayer')
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
  
  isPi = os.uname()[4].startswith("arm")
  
  settings = Settings(args["conf"], 
                      None,
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
  # Turn off display
  hmqtt.display_cmd('off')
  # All we do now is loop over a 5 minute delay
  while True:
    time.sleep(5*60)


# The state machine controls the interaction with mycroft(replys),
# mqttcamera and other events. 
# BE WATCHFUL about threading
#  mqtt calls into state_machine() on it's thread. You don't want
#  to block it with a sleep() if you depend on publishing to mqtt first
#     I use a hack. 
#  Most of the sleeps are ad hoc timing to keep mycroft
#  queue from building since it is LIFO
def state_machine(evt, arg=None):
  global applog, settings, hmqtt, trumpy_state, trumpy_bear
  global sm_lock, waitcnt, playSiren
  applog.debug("Sm entry {} {}".format(trumpy_state, evt))
  cur_state = trumpy_state
  # lock machine
  sm_lock.acquire()
  next_state = None
  if evt == Event.start:
    trumpy_state = State.starting
    next_state = State.waitrange
    waitcnt = 0
    hmqtt.set_status('running')
    hmqtt.display_text('Trumpy Bear is awake')
    hmqtt.ask('awaken the trumpy bear')
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
          hmqtt.ask('awaken the trumpy bear')
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
          # TODO: start mycroft or rasa for origin story
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
      # wait for speech to finish
      time.sleep(3)
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
    
def role_dispatch(trumpy_bear):
  role = trumpy_bear.role
  print('Dispatch:', trumpy_bear.name,"is",role)
  if role == Role.player:
    begin_rasa(trumpy_bear)
  elif role == Role.friend or role == Role.aquaintance or role == Role.relative:
    begin_mycroft()
  elif role == Role.owner:
    hmqtt.speak("You are very annoying, {}. Are you with the failing New York Times?".format(trumpy_bear.name))
    #time.sleep(2)
    #hmqtt.ask('What does tronald dump think about hilary clinton')
    interaction_finished()
  elif role == Role.unknown:
    begin_intruder()
  else:
    interaction_finished()
   
timerl_thread = None

def long_timer_fired():
  print('timer_long')
  interaction_finished()

def long_timer(min=5):
  global timerl_thread
  print('creating long timer')
  timerl_thread = threading.Timer(min * 60, long_timer_fired)
  timerl_thread.start()

# called directly or via long_timer()
def interaction_finished():
  global hmqtt, warning_level 
  print('closing interaction')
  hmqtt.tts_mute()
  hmqtt.display_cmd('off')
  hmqtt.set_status('idle')

def begin_mycroft():
  global hmqtt
  print('starting mycroft')
  long_timer(2)
  hmqtt.display_text("say 'Hey Mycroft'")
  hmqtt.speak("You can ask questions by saying hey mycroft")

def begin_rasa(tb):
  global hmqtt
  print('starting rasa')
  hmqtt.display_text(f"{tb.name} to see Mr. Sanders")
  #hmqtt.speak("Mister Sanders is not available {}. Try later.".format(tb.name))
  hmqtt.ask('Mister Sanders, {} is here'.format(tb.name))
  long_timer(1)
      
def begin_intruder():
  print('begin intruder')
  hmqtt.enable_player()      # sets mqtt switch to wake up a RM rule
  #hmqtt.set_status('alarm') 
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

  
def request_picture(typ):
  global settings, hmqtt, applog
  # get a picture from the camera
  topic = "homie/%s/control/cmd/set" % settings.homie_device
  payload = { "reply": topic,
              "path": "/var/www/camera/{}.jpg".format(typ) }
  applog.debug("capture ask %s %s" % (settings.camera_topic, json.dumps(payload)))
  hmqtt.client.publish(settings.camera_topic, 'capture='+json.dumps(payload))

    
def wakeup():
  global settings, hmqtt, applog
  global pict_count
  pict_count = 0
  applog.info("Trumpy Bear awakens")
  hmqtt.tts_unmute()
  hmqtt.speak("Trumpy Bear sees you. Approach and face the Bear!")
  state_machine(Event.start)
  #time.sleep(2)
  hmqtt.client.publish(settings.status_topic, 'awakens')


# the command channel controls the device from hubitat via mqtt
def trumpy_recieve(jsonstr):
  global settings, hmqtt, applog, trumpy_bear, trumpy_state
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
    wakeup()
  elif cmd == 'end':
    # kill and reset
    state_machine(Event.abort)
  elif cmd == 'capture_done':
    state_machine(Event.pict)
  elif cmd == 'alarm':
    #TODO not needed? my_tts(rargs['text'])
    pass
  

  
if __name__ == '__main__':
  sys.exit(main())
