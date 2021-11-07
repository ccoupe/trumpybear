#!/usr/bin/env python3
import paho.mqtt.client as mqtt
import sys, traceback
import json
from lib.Constants import Event
from datetime import datetime
import time
from threading import Thread

import time

class Homie_MQTT:

  def __init__(self, settings, playCb, chimeCb, sirenCb, strobeCb, sm):
    self.settings = settings
    self.log = settings.log
    self.playCb = playCb
    self.chimeCb = chimeCb
    self.sirenCb = sirenCb
    self.strobeCb = strobeCb
    self.controller = None
    self.state_machine = sm
    
    # init server connection
    self.client = mqtt.Client(settings.mqtt_client_name, False)
    #self.client.max_queued_messages_set(3)
    hdevice = self.hdevice = self.settings.homie_device  # "device_name"
    hlname = self.hlname = self.settings.homie_name     # "Display Name"
    # beware async timing with on_connect
    #self.client.loop_start()
    #self.client.on_connect = self.on_connect
    #self.client.on_subscribe = self.on_subscribe
    self.client.on_message = self.on_message
    self.client.on_disconnect = self.on_disconnect
    rc = self.client.connect(settings.mqtt_server, settings.mqtt_port)
    if rc != mqtt.MQTT_ERR_SUCCESS:
        self.log.warn("network missing?")
        exit()
    self.client.loop_start()
      
    # short cuts to stuff we really care about
    self.hurl_sub = "homie/"+hdevice+"/player/url/set"
    self.state_pub = "homie/"+hdevice+"/$state"
    self.hcmd_sub = "homie/"+hdevice+"/control/cmd/set"
    self.hreply_sub = "homie/"+hdevice+"/speech/reply/set"
    self.hsay_pub = "homie/"+hdevice+"/speech/say/set"
    self.hask_pub = "homie/"+hdevice+"/speech/ask/set"
    self.hctl_pub = "homie/"+hdevice+"/speech/ctl/set"
    # TODO: HARD CODED is evil and it's not Homie compat:
    self.hEnbl_pub = "homie/trumpy_enable/switch/state"
    self.hCops_pub = 'homie/trumpy_cops/switch/state'
    # newer device nodes to listen on
    self.hchime_sub = "homie/"+hdevice+"/chime/state/set"
    self.hsiren_sub = "homie/"+hdevice+"/siren/state/set"
    self.hstrobe_sub = "homie/"+hdevice+"/strobe/state/set"
    # esp32 with display and autoranger
    self.hrgrsub = 'homie/trumpy_ranger/autoranger/distance'
    sublist = [self.hurl_sub, self.hcmd_sub, self.hreply_sub, self.hchime_sub,
        self.hsiren_sub, self.hstrobe_sub, self.hrgrsub]
    # camera motion detector
    if settings.local_cam is None:
      flds = settings.camera_topic.split('/')
      flds[3] = 'motion'
      flds.pop()
      self.hmotsub = '/'.join(flds)
      sublist.append(self.hmotsub)
    else:
      self.hmotsub = ''
    
    # Shoes app listens for login/registation info at:
    self.hscn_pub = f'homie/{hdevice}/screen/control/set'
    
    self.log.debug("Homie_MQTT __init__")
    self.create_topics(hdevice, hlname)
    for sub in sublist:
      rc,_ = self.client.subscribe(sub)
      if rc != mqtt.MQTT_ERR_SUCCESS:
        self.log.warn(f"Subscribe to {sub} failed: {rc}")
      else:
        self.log.debug(f"Init() Subscribed to {sub}") 

    self.hrgrdist = 'homie/trumpy_ranger/autoranger/distance/set'
    self.hrgrmode = 'homie/trumpy_ranger/autoranger/mode/set'
    self.hdspcmd = 'homie/trumpy_ranger/display/mode/set'
    self.hdsptxt = 'homie/trumpy_ranger/display/text/set'
    
      
  def create_topics(self, hdevice, hlname):
    self.log.debug("Begin topic creation")
    # create topic structure at server - these are retained! 
    #self.client.publish("homie/"+hdevice+"/$homie", "3.0.1", mqos, retain=True)
    self.publish_structure("homie/"+hdevice+"/$homie", "3.0.1")
    self.publish_structure("homie/"+hdevice+"/$name", hlname)
    self.publish_structure(self.state_pub, "idle")
    self.publish_structure("homie/"+hdevice+"/$mac", self.settings.macAddr)
    self.publish_structure("homie/"+hdevice+"/$localip", self.settings.our_IP)
    # could have two nodes, player and alarm
    self.publish_structure("homie/"+hdevice+"/$nodes", "player, control, speech, chime, siren, strobe, screen")
    
    # player node
    self.publish_structure("homie/"+hdevice+"/player/$name", hlname)
    self.publish_structure("homie/"+hdevice+"/player/$type", "player")
    self.publish_structure("homie/"+hdevice+"/player/$properties","url")
    # url Property of 'play'
    self.publish_structure("homie/"+hdevice+"/player/url/$name", hlname)
    self.publish_structure("homie/"+hdevice+"/player/url/$datatype", "string")
    self.publish_structure("homie/"+hdevice+"/player/url/$settable", "false")
    self.publish_structure("homie/"+hdevice+"/player/url/$retained", "true")
    
    # control node
    self.publish_structure("homie/"+hdevice+"/control/$name", hlname)
    self.publish_structure("homie/"+hdevice+"/control/$type", "controller")
    #self.publish_structure("homie/"+hdevice+"/control/$properties","cmd")
    self.client.publish("homie/"+hdevice+"/control/$properties","cmd", qos=1, retain=False)
    
    #  cmd Property of 'control'
    self.publish_structure("homie/"+hdevice+"/control/cmd/$name", hlname)
    self.publish_structure("homie/"+hdevice+"/control/cmd/$datatype", "string")
    self.publish_structure("homie/"+hdevice+"/control/cmd/$settable", "true")
    self.publish_structure("homie/"+hdevice+"/control/cmd/$retained", "true")

    # speech node
    self.publish_structure("homie/"+hdevice+"/speech/$name", hlname)
    self.publish_structure("homie/"+hdevice+"/speech/$type", "speech")
    self.publish_structure("homie/"+hdevice+"/speech/$properties","say,ask,reply,ctl")
    #  'say' Property of 'speech'
    self.publish_structure("homie/"+hdevice+"/speech/say/$name", hlname)
    self.publish_structure("homie/"+hdevice+"/speech/say/$datatype", "string")
    self.publish_structure("homie/"+hdevice+"/speech/say/$settable", "true")
    self.publish_structure("homie/"+hdevice+"/speech/say/$retained", "true")
    #  'ask' Property of 'speech'
    self.publish_structure("homie/"+hdevice+"/speech/ask/$name", hlname)
    self.publish_structure("homie/"+hdevice+"/speech/ask/$datatype", "string")
    self.publish_structure("homie/"+hdevice+"/speech/ask/$settable", "true")
    self.publish_structure("homie/"+hdevice+"/speech/ask/$retained", "true")
    #  'reply' Property of 'speech'
    self.publish_structure("homie/"+hdevice+"/speech/reply/$name", hlname)
    self.publish_structure("homie/"+hdevice+"/speech/reply/$datatype", "string")
    self.publish_structure("homie/"+hdevice+"/speech/reply/$settable", "true")
    self.publish_structure("homie/"+hdevice+"/speech/reply/$retained", "true")
    #  'ctl' Property of 'speech'
    self.publish_structure("homie/"+hdevice+"/speech/ctl/$name", hlname)
    self.publish_structure("homie/"+hdevice+"/speech/ctl/$datatype", "string")
    self.publish_structure("homie/"+hdevice+"/speech/ctl/$settable", "true")
    self.publish_structure("homie/"+hdevice+"/speech/ctl/$retained", "true")

    # siren node
    self.publish_structure("homie/"+hdevice+"/siren/$name", hlname)
    self.publish_structure("homie/"+hdevice+"/siren/$type", "siren")
    self.publish_structure("homie/"+hdevice+"/siren/$properties","state")
    #  'state' Property of 'siren'
    self.publish_structure("homie/"+hdevice+"/siren/state/$name", hlname)
    self.publish_structure("homie/"+hdevice+"/siren/state/$datatype", "string")
    self.publish_structure("homie/"+hdevice+"/siren/state/$settable", "true")
    self.publish_structure("homie/"+hdevice+"/siren/state/$retained", "true")
    
    # chime node
    self.publish_structure("homie/"+hdevice+"/chime/$name", hlname)
    self.publish_structure("homie/"+hdevice+"/chime/$type", "chime")
    self.publish_structure("homie/"+hdevice+"/chime/$properties","state")
    #  'state' Property of 'siren'
    self.publish_structure("homie/"+hdevice+"/chime/state/$name", hlname)
    self.publish_structure("homie/"+hdevice+"/chime/state/$datatype", "string")
    self.publish_structure("homie/"+hdevice+"/chime/state/$settable", "true")
    self.publish_structure("homie/"+hdevice+"/chime/state/$retained", "true")

    # strobe node
    self.publish_structure("homie/"+hdevice+"/strobe/$name", hlname)
    self.publish_structure("homie/"+hdevice+"/strobe/$type", "strobe")
    self.publish_structure("homie/"+hdevice+"/strobe/$properties","state")
    #  'state' Property of 'strobe'
    self.publish_structure("homie/"+hdevice+"/strobe/state/$name", hlname)
    self.publish_structure("homie/"+hdevice+"/strobe/state/$datatype", "string")
    self.publish_structure("homie/"+hdevice+"/strobe/state/$settable", "true")
    self.publish_structure("homie/"+hdevice+"/strobe/state/$retained", "true")

    # screen node
    self.publish_structure("homie/"+hdevice+"/screen/$name", hlname)
    self.publish_structure("homie/"+hdevice+"/screen/$type", "strobe")
    self.publish_structure("homie/"+hdevice+"/screen/$properties","state")
    #  'state' Property of 'strobe'
    self.publish_structure("homie/"+hdevice+"/screen/state/$name", hlname)
    self.publish_structure("homie/"+hdevice+"/screen/state/$datatype", "string")
    self.publish_structure("homie/"+hdevice+"/screen/state/$settable", "true")
    self.publish_structure("homie/"+hdevice+"/screen/state/$retained", "true")

   # Done with structure. 

    self.log.debug("homie topics created")
    # nothing else to publish 
    
  def publish_structure(self, topic, payload):
    self.client.publish(topic, payload, qos=1, retain=True)
    
  def on_subscribe(self, client, userdata, mid, granted_qos):
    self.log.debug("Subscribed to %s" % self.hurl_sub)

  def on_message(self, client, userdata, message):
    global settings
    topic = message.topic
    payload = str(message.payload.decode("utf-8"))
    self.log.debug("on_message %s %s" % (topic, payload))
    try:
      if (topic == self.hurl_sub):
        #ply_thr = Thread(target=self.playCb, args=(payload,))
        #ply_thr.start()
        self.playCb(payload)
      elif topic == self.hcmd_sub:
        # payload should be json. Fires up Trumpy Bear state_machice
        tb_thr = Thread(target=self.controller, args=(payload,))
        tb_thr.start()
        #self.controller(payload)
      elif topic == self.hreply_sub:
        rp_thr = Thread(target=self.state_machine, args=(Event.reply, payload))
        rp_thr.start()
        #self.state_machine(Event.reply, payload)
      elif topic == self.hrgrsub:
        rg_thr = Thread(target=self.state_machine, args=(Event.ranger, payload))
        rg_thr.start()
        #self.state_machine(Event.ranger, payload)
      elif topic == self.hchime_sub:
        chime_thr = Thread(target=self.chimeCb, args=(payload,))
        chime_thr.start()
        #self.chimeCb(payload)
      elif topic == self.hsiren_sub:
        siren_thr = Thread(target=self.sirenCb, args=(payload,))
        siren_thr.start()
        #self.sirenCb(payload)
      elif topic == self.hstrobe_sub:
        strobe_thr = Thread(target=self.strobeCb, args=(payload,))
        strobe_thr.start()
        #self.strobeCb(payload)
      elif topic == self.hmotsub:
        motion_thr = Thread(target=self.state_machine, args=(Event.motion, payload))
        motion_thr.start()
      else:
        self.log.debug(f"on_message() unknown command {topic} {payload}")
    except :
      traceback.print_exc()
      #self.log.error("on_message error: %s" % sys.exc_info()[0])

    
  def isConnected(self):
    return self.mqtt_connected

  def on_connect(self, client, userdata, flags, rc):
    self.log.debug("Subscribing: %s %d" (type(rc), rc))
    if rc == 0:
      self.log.debug("Connecting to %s" % self.mqtt_server_ip)
      rc,_ = self.client.subscribe(self.hurl_sub)
      if rc != mqtt.MQTT_ERR_SUCCESS:
        self.log.debug("Subscribe failed: ", rc)
      else:
        self.log.debug("Subscribed to %s" % self.hurl_sub)
        self.mqtt_connected = True
    else:
      self.log.debug("Failed to connect: %d" %rc)
    self.log.debug("leaving on_connect")
       
  def on_disconnect(self, client, userdata, rc):
    self.mqtt_connected = False
    self.log.debug("mqtt reconnecting")
    self.client.reconnect()
      
  # ------- usable to the outside -----------
  def set_status(self, str):
    self.client.publish(self.state_pub, str)
        
  # These use the bridge to talk to mycroft
  def speak(self, str):
    self.client.publish(self.hsay_pub, str)

  def ask(self, str):
    self.client.publish(self.hask_pub, str)

  def tts_unmute(self):
    self.client.publish(self.hctl_pub, 'on')
    
  def tts_mute(self):
    self.client.publish(self.hctl_pub, 'off')
      
  # These talk to the trumpy_ranger device/node
  def display_cmd(self, st):
    self.client.publish(self.hdspcmd, st)
    
  def display_text(self, txt):
    self.client.publish(self.hdsptxt, txt)

  def start_ranger(self, cm):
    self.client.publish(self.hrgrdist, cm)
    
  def ranger_mode(self, str):
    self.client.publish(self.hrgrmode, str)
  
  # Hubitat Device(s) are listening on these topics
  def start_music_alarm(self):
    # self.hEnbl_pub = "homie/trumpy_enable/switch/state"
    # It's 'Trumpy Enable Alarm', a Virtual Switch which
    # triggers the 'Trumpy Music' rule
    self.client.publish(self.hEnbl_pub, "on")
      
  def login(self, json):
    # self.hscn_pub = 'homie/trumpy_bear/screen/control/set'
    self.client.publish(self.hscn_pub,json) 
    
  def cops_arrive(self):
    # self.hCops_pub = 'homie/trumpy_cops/switch/state'
    self.client.publish(self.hCops_pub, 'on')
    
  # Yet another thing to talk to. Target Tracker.
  def tracker(self, json):
    self.client.publish('homie/turret_tracker/track/control/set', json)

