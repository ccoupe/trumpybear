#!/usr/bin/env python3
import paho.mqtt.client as mqtt
import sys
import json
import argparse
import warnings
from datetime import datetime
import time, threading, sched
from threading import Lock
import socket
import os
from lib.Settings import Settings
from lib.Homie_MQTT import Homie_MQTT
from lib.Constants import State, Event, Role
from lib.TrumpyBear import TrumpyBear

#from lib.Algo import Algo
import urllib.request
#from playsound import playsound
import logging
import logging.handlers
#import numpy as np
#import cv2
import websocket

# globals
settings = None
hmqtt = None
debug_level = 1
isPi = False
applog = None
trumpy_state = None
trumpy_bear = None    # object of class TrumpyBear
my_tts = None         # object to do TTS: espeak or mycroft, None for quiet mode
#myc_conn = None       # websocket to mycroft
sm_lock = Lock()      # state machine lock - only one thread at a time

def playUrl(url):
  global hmqtt, isPi, applog
  #log(url)
  applog.info("playUrl: %s" % url)
  if True:
    try:
      urllib.request.urlretrieve(url, "tmp.mp3")
    except:
      applog.warn("Failed download")
    url = "tmp.mp3"
  #synchronous playback, I believe.
  hmqtt.set_status("busy")
  if isPi:
    os.system('mpg123 -q --no-control tmp.mp3')
  else:
    playsound(url)
  hmqtt.set_status("ready")

def alarmUrl(url):
  log(url)
  
def log(msg, level=2):
  global debug_level
  if level > debug_level:
    return
  (dt, micro) = datetime.now().strftime('%H:%M:%S.%f').split('.')
  dt = "%s.%03d" % (dt, int(micro) / 1000)
  logmsg = "%-14.14s%-60.60s" % (dt, msg)
  print(logmsg, flush=True)
  
def my_speak(text):
  global hmqtt
  hmqtt.speak(text)
  
def my_ask(text):
  global hmqtt
  hmqtt.ask(text)
  
 
def main():
  global isPi, settings, hmqtt, applog, my_speak, my_ask
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
                    alarmUrl,
                    state_machine)
  settings.print()
    
  # TODO this should be part of the state machine.
  # set some callback functions in the Mqtt Object
  hmqtt.controller = trumpy_recieve
  # All we do now is loop over a 5 minute delay
  while True:
    time.sleep(5*60)


# The state machine controls the interaction with mycroft(replys)
def state_machine(evt, arg=None):
  global applog, settings, hmqtt, trumpy_state, trumpy_bear
  global sm_lock
  applog.debug("Sm entry {} {}".format(trumpy_state, evt))
  cur_state = trumpy_state
  # lock machine
  sm_lock.acquire()
  next_state = None
  if evt == Event.start:
    trumpy_state = State.starting
    hmqtt.ask('awaken the trumpy bear')
    next_state = State.starting
  elif evt == Event.reply:
    if trumpy_state == State.starting:
      # have a name. Maybe. What role matches? 
      if arg == None or arg == '':
        next_state = State.starting  # do over
        hmqtt.speak("I didn't catch that. Starting over")
        time.sleep(1)
        hmqtt.ask('awaken the trumpy bear')
      else:
        trumpy_bear = TrumpyBear(settings, arg)
        role = trumpy_bear.check_user(arg)
        # For Testing, force role.unknown
        role = Role.unknown
        if role == Role.owner:
          next_state = State.mycroft 
        else:
          hmqtt.speak("I'm going to take your picture. Face the bear and stand up straight")
          time.sleep(1)
          request_picture('face')
          next_state = State.waitfr
    
  elif evt == Event.frpict:
    if trumpy_state == State.waitfr:
      trumpy_bear.front_path = "/var/www/camera/face.jpg"
      # TODO - thread the call to do_recog so we don't re-enter a locked sm
      #next_state = State.waitrecog
      #do_recog(img)
      # until then, 
      time.sleep(1) # TODO: turn on buzzer? flash an led? Or in request_picture?
      hmqtt.speak('Click. Done. Please turn right 90 degrees for a side picture.')
      time.sleep(2)
      next_state = State.waitsd
      request_picture('side')
    else:
      # error. 
      pass
  elif evt == Event.sdpict:
    if trumpy_state == State.waitsd:
      trumpy_bear.side_path = "/var/www/camera/left.jpg"
      trumpy_bear.save_user()
      # need to leave statemachine (unlock it)
      # if we were to quiz a buglar then we'd have more states
      next_state = State.role_dispatch
    else:
      # error
      pass
  elif evt == Event.recog:
    if trumpy_state == State.waitrecog:
      # arg will have a name or none.
      if arg == None:
        next_state = State.waitsd
        # speak, get a pict from camera device
      else:
        role = trumpy_bear.check_user(name)
        if role == Role.player:
          next_state = State.rasa
        elif role == Role.friend or role == Role.aquaintance:
          next_state = State.mycroft
        else: 
          next_state = State.alarm
    pass
  elif evt == Event.timers:
    pass
  elif evt == Event.timerl:
    pass
  else:
    applog.warn("Unhandled event: %s" % evt)
    
  trumpy_state = next_state
  applog.debug("Sm exit {} {} => {}".format(cur_state, evt, trumpy_state))
  # unlock machine
  sm_lock.release()
  if trumpy_state == State.role_dispatch:
    trumpy_state = State.initialized
    role_dispatch(trumpy_bear)
    
def role_dispatch(trumpy_bear):
  role = trumpy_bear.role
  print('Dispatch:', trumpy_bear.name,"is",role)
  if role == Role.unknown:
    begin_fighting(trumpy_bear)
  elif role == Role.player:
    begin_rasa(trumpy_bear)
  elif role == Role.friend or role == Role.aquaintance or role == Role.relative:
    begin_mycroft()
  else:
    hmqtt.speak("You are very annoying {}! Are you with the failing New York Times?".format(trumpy_bear.name))
    time.sleep(2)
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

def interaction_finished():
  global hmqtt, warning_level 
  print('closing interaction')
  hmqtt.speak("Thanks for playing. Turning off now.")
  time.sleep(1)
  hmqtt.tts_mute()

def begin_mycroft():
  global hmqtt
  print('starting mycroft')
  long_timer(5)
  hmqtt.speak("You can ask questions by saying hey mycroft")


def begin_rasa(tb):
  global hmqtt
  print('starting rasa')
  hmqtt.speak("Mister Sanders is not available {}. Try later.".format(tb.name))
  time.sleep(1)
  interaction_finished()
  
def begin_fighting(tb):
  global hmqtt
  warning_cnt = 0
  while warning_cnt < 3:
    print('insult ahead', warning_cnt+1)
    if warning_cnt == 0:
      hmqtt.speak('Answer Yes or No. Have I mentioned that I can call the cops?')
    elif warning_cnt == 1:
      hmqtt.speak("I am going to turn on the defenses if you don't answer correctly")
      time.sleep(1)
      hmqtt.speak('Do you want me to electrify all the metal in the house?')
    elif warning_cnt >= 2:
      hmqtt.speak('Now you have a problem, bucko. The cops are on the way.')
      time.sleep(1)
      hmqtt.speak('The only way out is the back door. The one you can in. Good Luck')
    warning_cnt += 1
    time.sleep(4)
    
# this will be an rpc in the future
def do_recog(img):
  global trumpy_bear
  print('get_face_name')
  state_machine(Event.recog, None)

def load_pict(path):
  # TODO
  print('leaving load_pict')
  return None
  
def request_picture(typ):
  global settings, hmqtt, applog
  # get a picture from the camera
  topic = "homie/%s/control/cmd/set" % settings.homie_device
  applog.debug("request_picture %s " % typ)
  payload = { "reply": topic,
              "path": "/var/www/camera/{}.jpg".format(typ) }
  applog.debug("ask %s %s" % (settings.camera_topic, json.dumps(payload)))
  hmqtt.client.publish(settings.camera_topic, 'capture='+json.dumps(payload))
  # control continues from trumpy_recieve()
    
def wakeup():
  global settings, hmqtt, applog
  global pict_count
  pict_count = 0
  applog.info("Trumpy Bear awakens")
  hmqtt.tts_unmute()
  hmqtt.speak("Trumpy Bear sees you. . Approach and face the Bear!")
  state_machine(Event.start)
  #time.sleep(2)
  hmqtt.client.publish(settings.status_topic, 'awakens')


# the command channel controls the 
def trumpy_recieve(jsonstr):
  global settings, hmqtt, applog, trumpy_bear, trumpy_state
  rargs = json.loads(jsonstr)
  cmd = rargs['cmd']
  if cmd == 'init':
    # hubitat can send an init, can override camera choice in json
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
  elif cmd == 'capture_done':
    if trumpy_state == State.waitfr:
      state_machine(Event.frpict) 
    else:
      state_machine(Event.sdpict)
  elif cmd == 'alarm':
    #my_tts(rargs['text'])
    pass
  

  
if __name__ == '__main__':
  sys.exit(main())
