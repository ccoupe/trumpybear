#!/usr/bin/env python3
import paho.mqtt.client as mqtt
import sys
import json

from datetime import datetime
import time,threading, sched

import time

class Homie_MQTT:

  def __init__(self, settings, playCb, alarmCb):
    self.settings = settings
    self.log = settings.log
    self.playCb = playCb
    self.alarmCb = alarmCb
  
    # init server connection
    self.client = mqtt.Client(settings.mqtt_client_name, False)
    #self.client.max_queued_messages_set(3)
    hdevice = self.hdevice = self.settings.homie_device  # "device_name"
    hlname = self.hlname = self.settings.homie_name     # "Display Name"
    # beware async timing with on_connect
    #self.client.loop_start()
    self.client.on_connect = self.on_connect
    self.client.on_subscribe = self.on_subscribe
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

    self.log.debug("Homie_MQTT __init__")
    self.create_topics(hdevice, hlname)
    
    rc,_ = self.client.subscribe(self.hurl_sub)
    if rc != mqtt.MQTT_ERR_SUCCESS:
      self.log.warn("Subscribe failed: %d" %rc)
    else:
      self.log.debug("Init() Subscribed to %s" % self.hurl_sub)
      
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
    self.publish_structure("homie/"+hdevice+"/$nodes", "player")
    
    # player node
    self.publish_structure("homie/"+hdevice+"/player/$name", hlname)
    self.publish_structure("homie/"+hdevice+"/player/$type", "audiosink")
    self.publish_structure("homie/"+hdevice+"/player/$properties","url")
    # url Property of 'play'
    self.publish_structure("homie/"+hdevice+"/player/url/$name", hlname)
    self.publish_structure("homie/"+hdevice+"/player/url/$datatype", "string")
    self.publish_structure("homie/"+hdevice+"/player/url/$settable", "false")
    self.publish_structure("homie/"+hdevice+"/player/url/$retained", "true")
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
      else:
        self.log.debug("on_message() unknown command %s" % message)
    except:
      self.log.error("on_message error: %s" % sys.exc_info()[0])

    
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
    log("mqtt reconnecting")
    self.client.reconnect()
      
  def set_status(self, str):
    self.client.publish(self.state_pub, str)
