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
        print("network missing?")
        exit()
    self.client.loop_start()
      
    # short cuts to stuff we really care about
    self.hurl_sub = "homie/"+hdevice+"/player/url/set"
    self.state_pub = "homie/"+hdevice+"/$state"

    print("Homie_MQTT __init__")
    self.create_topics(hdevice, hlname)
    
    rc,_ = self.client.subscribe(self.hurl_sub)
    if rc != mqtt.MQTT_ERR_SUCCESS:
      print("Subscribe failed: ", rc)
    else:
      print("Init() Subscribed to %s" % self.hurl_sub)
      
  def create_topics(self, hdevice, hlname):
    print("Begin topic creation")
    mqos = 1
    # create topic structure at server - these are retained! 
    #self.client.publish("homie/"+hdevice+"/$homie", "3.0.1", mqos, retain=True)
    self.publish_structure("homie/"+hdevice+"/$homie", "3.0.1")
    self.client.publish("homie/"+hdevice+"/$name", hlname, mqos, retain=True)
    self.publish_structure(self.state_pub, "ready")
    self.client.publish("homie/"+hdevice+"/$mac", self.settings.macAddr, True)
    self.client.publish("homie/"+hdevice+"/$localip", self.settings.our_IP, mqos, True)
    # could have two nodes, player and alarm
    self.client.publish("homie/"+hdevice+"/$nodes", "player", mqos, True)
    
    # motionsensor player
    self.client.publish("homie/"+hdevice+"/player/$name", hlname, mqos, True)
    self.client.publish("homie/"+hdevice+"/player/$type", "audiosink", mqos, True)
    self.client.publish("homie/"+hdevice+"/player/$properties","url", mqos, True)
    # Property of 'motion'
    self.client.publish("homie/"+hdevice+"/player/url/$name", hlname, mqos, True)
    self.client.publish("homie/"+hdevice+"/player/url/$datatype", "string", mqos, True)
    self.client.publish("homie/"+hdevice+"/player/url/$settable", "false", mqos, True)
    self.client.publish("homie/"+hdevice+"/player/url/$retained", "true", mqos, True)
   # Done with structure. 

    print("homie topics created")
    # nothing else to publish 
    
  def publish_structure(self, topic, payload):
    self.client.publish(topic, payload, qos=1, retain=True)
    
  def on_subscribe(self, client, userdata, mid, granted_qos):
    print("Subscribed to %s" % self.hurl_sub)

  def on_message(self, client, userdata, message):
    global settings
    topic = message.topic
    payload = str(message.payload.decode("utf-8"))
    print("on_message ", topic, " ", payload)
    try:
      if (topic == self.hurl_sub):
        self.playCb(payload)
      else:
        print("on_message() unknown command ", message)
    except:
      print("on_message error:", sys.exc_info()[0])

    
  def isConnected(self):
    return self.mqtt_connected

  def on_connect(self, client, userdata, flags, rc):
    print("Subscribing: ", type(rc), rc)
    if rc == 0:
      print("Connecting to %s" % self.mqtt_server_ip)
      rc,_ = self.client.subscribe(self.hurl_sub)
      if rc != mqtt.MQTT_ERR_SUCCESS:
        print("Subscribe failed: ", rc)
      else:
        print("Subscribed to %s" % self.hurl_sub)
        self.mqtt_connected = True
    else:
      print("Failed to connect:", rc)
    print("leaving on_connect")
       
  def on_disconnect(self, client, userdata, rc):
    self.mqtt_connected = False
    log("mqtt reconnecting")
    self.client.reconnect()
      
  def set_status(self, str):
    self.client.publish(self.state_pub, str)
