#!/usr/bin/env python3
import paho.mqtt.client as mqtt
import sys, traceback
import json
from lib.Constants import Event
from datetime import datetime
import time,threading, sched

import time

class Homie_MQTT:

  def __init__(self, settings, playCb, alarmCb, sm):
    self.settings = settings
    self.log = settings.log
    self.playCb = playCb
    self.alarmCb = alarmCb
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

    self.log.debug("Homie_MQTT __init__")
    self.create_topics(hdevice, hlname)
    
    rc,_ = self.client.subscribe(self.hurl_sub)
    if rc != mqtt.MQTT_ERR_SUCCESS:
      self.log.warn("Subscribe failed: %d" %rc)
    else:
      self.log.debug("Init() Subscribed to %s" % self.hurl_sub)

    rc,_ = self.client.subscribe(self.hcmd_sub)
    if rc != mqtt.MQTT_ERR_SUCCESS:
      self.log.warn("Subscribe failed: %d" %rc)
    else:
      self.log.debug("Init() Subscribed to %s" % self.hcmd_sub)
      
    rc,_ = self.client.subscribe(self.hreply_sub)
    if rc != mqtt.MQTT_ERR_SUCCESS:
      self.log.warn("Subscribe failed: %d" %rc)
    else:
      self.log.debug("Init() Subscribed to %s" % self.hreply_sub)
      
  def create_topics(self, hdevice, hlname):
    self.log.debug("Begin topic creation")
    # create topic structure at server - these are retained! 
    #self.client.publish("homie/"+hdevice+"/$homie", "3.0.1", mqos, retain=True)
    self.publish_structure("homie/"+hdevice+"/$homie", "3.0.1")
    self.publish_structure("homie/"+hdevice+"/$name", hlname)
    self.publish_structure(self.state_pub, "ready")
    self.publish_structure("homie/"+hdevice+"/$mac", self.settings.macAddr)
    self.publish_structure("homie/"+hdevice+"/$localip", self.settings.our_IP)
    # could have two nodes, player and alarm
    self.publish_structure("homie/"+hdevice+"/$nodes", "player, control, speech")
    
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
    self.publish_structure("homie/"+hdevice+"/control/$properties","cmd")
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
        self.playCb(payload)
      elif topic == self.hcmd_sub:
        # payload should be json
        self.controller(payload)
      elif topic == self.hreply_sub:
        self.state_machine(Event.reply, payload)
      else:
        self.log.debug("on_message() unknown command %s" % message)
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
        
  def speak(self, str):
    self.client.publish(self.hsay_pub, str)

  def ask(self, str):
    self.client.publish(self.hask_pub, str)

  def tts_unmute(self):
    self.client.publish(self.hctl_pub, 'on')
    
  def tts_mute(self):
   self.client.publish(self.hctl_pub, 'off')
