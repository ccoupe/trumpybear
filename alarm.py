#!/usr/bin/env python3
import paho.mqtt.client as mqtt
import sys
import json
import argparse
import warnings
from datetime import datetime
import time,threading, sched
import socket
import os
from lib.Settings import Settings
from lib.Homie_MQTT import Homie_MQTT
import urllib.request
from playsound import playsound


# globals
settings = None
hmqtt = None
debug_level = 1
use_syslog = False
isPi = False

def playUrl(url):
  global hmqtt, isPi
  #log(url)
  print("playUrl: ",url)
  if True:
    try:
      urllib.request.urlretrieve(url, "tmp.mp3")
    except:
      print("Failed download")
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
 
  
# process cmdline arguments
ap = argparse.ArgumentParser()
ap.add_argument("-c", "--conf", required=True, type=str,
	help="path and name of the json configuration file")
ap.add_argument("-d", "--debug", action='store', type=int, default='3',
  nargs='?', help="debug level, default is 3")
args = vars(ap.parse_args())

isPi = os.uname()[4].startswith("arm")

settings = Settings(args["conf"], 
                    None,
                    log)
hmqtt = Homie_MQTT(settings, 
                  playUrl,
                  alarmUrl)
settings.print()

# fix debug levels
if args['debug'] == None:
  debug_level = 3
else:
  debug_level = args['debug']
  
# All we do now is loop over a 5 minute delay
while True:
  time.sleep(5*60)
  
