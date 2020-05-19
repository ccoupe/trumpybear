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


waitcnt = 0

# The state machine controls the interaction with mycroft(replys),
# mqttcamera and other events. 
def state_machine(evt, arg=None):
  global applog, settings, hmqtt, trumpy_state, trumpy_bear
  global sm_lock, waitcnt
  applog.debug("Sm entry {} {}".format(trumpy_state, evt))
  cur_state = trumpy_state
  # lock machine
  sm_lock.acquire()
  next_state = None
  if evt == Event.start:
    trumpy_state = State.starting
    next_state = State.waitname
    waitcnt = 0
    hmqtt.display_text('Trumpy Bear is awake. I see you.')
    hmqtt.ask('awaken the trumpy bear')
  elif evt == Event.reply:
    if trumpy_state == State.waitname:
      # have a name. Maybe. What role matches? 
      if arg == None or arg == '':
        if waitcnt < 2:
          next_state = State.waitname  # do over
          hmqtt.speak("I didn't catch that. Move closer and wait for the tone")
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
        role = Role.unknown
        if role == Role.owner:
          next_state = State.mycroft 
        else:
          hmqtt.speak("I'm going to take your picture. Face the bear and stand up straight")
          time.sleep(1)
          request_picture('face')
          next_state = State.waitface
          
    elif trumpy_state == State.q1ans:
      trumpy_bear.ans1 = arg
      next_state = State.q2ans
      hmqtt.ask("arm defenses")
      hmqtt.display_text('dialing.. dialing..')
    elif trumpy_state == State.q2ans:
      trumpy_bear.ans2 = arg
      next_state = State.q3ans
      hmqtt.ask('do the last chance')
      hmqtt.display_text("Arming Defenses It's On")
    elif trumpy_state == State.q3ans:
      trumpy_bear.ans3 = arg
      next_state == State.role_dispatch
      hmqtt.speak("What a Loos-er! Go out the way you came in and Don't touch anything metal!")
    else:
      applog.debug('no handler in {} for {}'.format(trumpy_state, evt))
  elif evt == Event.pict:
    if trumpy_state == State.waitface:
      trumpy_bear.front_path = "/var/www/camera/face.jpg"
      # recognition is synchronous, not an event
      name = do_recog(trumpy_bear)
      # if name != None and Role != unknown then skip other pictures and the like
      time.sleep(1) # TODO: turn on buzzer? flash an led? Or in request_picture?
      hmqtt.speak('Click. Done. Please turn right 90 degrees for a side picture.')
      time.sleep(10)
      next_state = State.waitside
      request_picture('side')
    elif trumpy_state == State.waitside:
      trumpy_bear.side_path = "/var/www/camera/side.jpg"
      trumpy_bear.save_user()
      hmqtt.speak('Click Got it ')
      # wait for speech to finish
      time.sleep(3)
      if trumpy_bear.role == Role.unknown:
        time.sleep(1)
        next_state = State.q1ans 
        hmqtt.display_text('You are found wanting')
        hmqtt.ask('call the cops')
      else:
        next_state = State.role_dispatch
        hmqtt.speak('Saved. You are being judged {}'.format(trumpy_bear.name))
        hmqtt.display_text('Hi {}'.format(trumpy_bear.name))
    else:
      applog.debug('no handler in {} for {}'.format(trumpy_state, evt))
      
  elif evt == Event.ranger:
    pass
  elif evt == Event.watchdog:
    applog.debug('no handler in {} for {}'.format(trumpy_state, evt))

  else:
    applog.warn("Unhandled event: %s" % evt)
    
  # end the pass through the state machine
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
  if role == Role.player:
    begin_rasa(trumpy_bear)
  elif role == Role.friend or role == Role.aquaintance or role == Role.relative:
    begin_mycroft()
  elif role == Role.owner:
    hmqtt.speak("You are very annoying {}. Are you with the failing New York Times?".format(trumpy_bear.name))
    time.sleep(4)
    hmqtt.ask('What does tronald dump think about hilary clinton')
    interaction_finished()
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

def interaction_finished():
  global hmqtt, warning_level 
  print('closing interaction')
  hmqtt.speak("Thanks for playing")
  time.sleep(1)
  hmqtt.tts_mute()
  hmqtt.display_cmd('off')


def begin_mycroft():
  global hmqtt
  print('starting mycroft')
  long_timer(5)
  hmqtt.speak("You can ask questions by saying hey mycroft")


def begin_rasa(tb):
  global hmqtt
  print('starting rasa')
  #hmqtt.speak("Mister Sanders is not available {}. Try later.".format(tb.name))
  hmqtt.ask('Mister Sanders, {} is here'.format(tb.name))
  time.sleep(1)
  interaction_finished()
      
# TODO This will be an rpc in the future that returns the matching
# name string or None.
def do_recog(sb):
  print('get_face_name')
  return None


def load_pict(path):
  # TODO
  print('leaving load_pict')
  return None
  
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
    state_machine(Event.pict)
  elif cmd == 'alarm':
    #my_tts(rargs['text'])
    pass
  

  
if __name__ == '__main__':
  sys.exit(main())
