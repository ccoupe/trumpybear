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


# The state machine 
def state_machine(evt, arg=None):
  global applog, settings, hmqtt, trumpy_state, trumpy_bear
  global sm_lock
  print("Sm entry", trumpy_state, evt)
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
      trumpy_bear = TrumpyBear(settings, arg)
      if trumpy_bear.role == Role.owner:
        next_state = State.mycroft 
      else:
        trumpy_bear.role = Role.unknown
        hmqtt.speak("I'm going to take your picture. Face the bear and stand up straight")
        time.sleep(1)
        request_picture('face')
        print('back from request face')
        next_state = State.waitfr
    
  elif evt == Event.frpict:
    if trumpy_state == State.waitfr:
      img = load_pict("/var/www/camera/face.jpg")
      trumpy_bear.front = img
      # TODO - thread the call to do_recog so we don't re-enter sm
      #next_state = State.waitrecog
      #do_recog(img)
      # until then, 
      hmqtt.speak('Turn Right 90 degrees')
      time.sleep(1)
      request_picture('side')
      next_state = State.waitsd
    else:
      # error. 
      pass
  elif evt == Event.sdpict:
    if trumpy_state == State.waitsd:
      img = load_pict("/var/www/camera/left.jpg")
      trumpy_bear.side = img
      print('calling save user')
      trumpy_bear.save_user()
      if trumpy_bear.role == Role.unknown:
        next_state = State.insult
        hmqtt.ask("insult the wonderdog")
      else:
        next_state = State.mycroft
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
        role = trumpy_bear.check(name)
        if role == Role.player:
          next_state = State.rasa
        elif role == Role.friend or role == Role.aquaintance:
          next_state = State.mycroft
        else: 
          next_state = State.alarm
    pass
  elif evt == Event.timer5s:
    pass
  elif evt == Event.timer5m:
    pass
  else:
    applog.warn("Unhandled event: %s" % evt)
    
  trumpy_state = next_state
  # unlock machine
  sm_lock.release()
  
    
# this will be an rpc in the future
def do_recog(img):
  global trumpy_bear
  print('get_face_name')
  state_machine(Event.recog, None)

def load_pict(path):
  # TODO
  print('leaving load_pict')
  return None

def get_side_assessment(path):
  print('get_side_assessment')
  return True
  
def request_picture(typ):
  global settings, hmqtt, applog
  # get a picture from the camera
  topic = "homie/%s/control/cmd/set" % settings.homie_device
  applog.debug("request_picture %s " % typ)
  payload = { "reply": topic,
              "path": "/var/www/camera/{}.jpg".format(typ) }
  #print(json.dumps(payload))
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



detect_fail = 0
person = None

# TODO: only allow this to be called 3 times. Ugly?
def authenticate():
  global settings, hmqtt, applog, trumpy_state, trumpybear
  global detect_fail 
  try:
    if detect_fail >= 3:
      trumpybear = TrumpyBear(settings, 'Evil Do-er', Role.unwanted)
      trumpy_state = State.unauthorized
    applog.info("authenticate state %s" % trumpy_state)
    if trumpy_state == State.awakens:
      hmqtt.client.publish(settings.status_topic, 'got_face')
      name = get_face_name("/var/www/camera/face.jpg")
      if name == 'linda':
        trumpy_state = State.get_side
        settings.my_tts.speak("Turn Right, Please")
        time.sleep(2)
        request_picture('left')
      elif name != None:
        trumpybear = TrumpyBear(settings, 'Friend', Role.friend) 
        trumpy_state = State.authorized
      else:
        detect_fail += 1
        settings.my_tts.speak("You are unknown. We will try again. Face Trumpy Bear")
        request_picture('face')
    elif trumpy_state == State.get_side:
      tees = get_side_assessment("/var/www/camera/left.jpg")
      if tees == True:
        trumpybear = TrumpyBear(settings, 'Linda', Role.player)
      else:
        trumpybear = TrumpyBear(settings, 'Cecil', Role.owner)
      trumpy_state = State.authorized
    else:
      settings.my_tts.speak("Unknown State. Time to panic")
  except e:
    print(e)

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
