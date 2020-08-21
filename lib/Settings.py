#!/usr/bin/env python3
import json
import socket
from uuid import getnode as get_mac
import os 
import sys

class Settings:

  def __init__(self, etcf, adev, log):
    self.etcfname = etcf
    self.audiodev = adev
    self.log = log
    self.mqtt_server = "192.168.1.7"   # From json
    self.mqtt_port = 1883              # From json
    self.mqtt_client_name = "detection_1"   # From json
    self.homie_device = None            # From json
    self.homie_name = None              # From json
    # IP and MacAddr are not important (should not be important).
    if sys.platform.startswith('linux'):
      s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
      s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
      s.connect(('<broadcast>', 0))
      self.our_IP =  s.getsockname()[0]
      # from stackoverflow (of course):
      self.macAddr = ':'.join(("%012x" % get_mac())[i:i+2] for i in range(0, 12, 2))
    elif sys.platform.startswith('darwin'):
      host_name = socket.gethostname() 
      self.our_IP = socket.gethostbyname(host_name) 
      self.macAddr = ':'.join(("%012x" % get_mac())[i:i+2] for i in range(0, 12, 2))
    else:
      self.our_IP = "192.168.1.255"
      self.macAddr = "de:ad:be:ef"
    self.macAddr = self.macAddr.upper()
    # default config  ~/.trumpybear
    self.db_path = os.path.join(os.getenv('HOME'),'.trumpybear')
    self.load_settings(self.etcfname)
    self.status_topic = 'homie/'+self.homie_device+'/control/cmd'
    # expand camera_topic
    self.camera_topic = 'homie/'+self.camera_topic+'/motionsensor/control/set'
    self.log.info("Settings from %s" % self.etcfname)
    self.player_vol_default = self.audiodev.sink_volume
    self.chime_vol_default = self.audiodev.sink_volume
    self.siren_vol_default = self.audiodev.sink_volume
    self.player_vol = self.audiodev.sink_volume
    self.chime_vol = self.audiodev.sink_volume
    self.siren_vol = self.audiodev.sink_volume
    
  def load_settings(self, fn):
    conf = json.load(open(fn))

    self.mqtt_server = conf.get("mqtt_server_ip", "192.168.1.7")
    self.mqtt_port = conf.get("mqtt_port", 1883)
    self.mqtt_client_name = conf.get("mqtt_client_name", "trumpy_12")
    self.homie_device = conf.get('homie_device', "trumpy_bear")
    self.homie_name = conf.get('homie_name', 'Trumpy Bear Pi3')
    self.camera_topic = conf.get('camera_topic', 'trumpy_cam')
    self.mycroft_ip = conf.get('mycroft_ip', '192.168.1.2')
    self.face_server_ip = conf.get('face_server_ip', '192.168.1.4')
    self.face_port = conf.get('face_port', 4774)
    self.db_path = conf.get('db_path', self.db_path)
    self.ranger_mode = conf.get('ranger_mode', None)


  def print(self):
    self.log.info("==== Settings ====")
    self.log.info(self.settings_serialize())
  
  def settings_serialize(self):
    st = {}
    st['mqtt_server_ip'] = self.mqtt_server
    st['mqtt_port'] = self.mqtt_port
    st['mqtt_client_name'] = self.mqtt_client_name
    st['homie_device'] = self.homie_device 
    st['homie_name'] = self.homie_name
    st['camera_topic'] = self.camera_topic
    st['status_topic'] = self.status_topic
    st['mycroft_ip'] = self.mycroft_ip
    st['face_server_ip'] = self.face_server_ip
    st['face_port'] = self.face_port
    st['db_path'] = self.db_path
    st['ranger_mode'] = self.ranger_mode

    str = json.dumps(st)
    return str

  def settings_deserialize(self, jsonstr):
    st = json.loads(jsonstr)
