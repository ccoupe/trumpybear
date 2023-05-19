
import os
import websocket
import json
import time
import _thread

class Skill_Conn:

  def __init__(self, settings, use_mycroft):
    self.log = settings.log
    self.active = False
    if use_mycroft == True:
      self.uri = 'ws://' + settings.mycroft_ip + ':8181/core'
      self.speak = self.mycroft_speak
      self.start_skill = self.mycroft_skill
    elif use_mycroft == False:
      self.speak = self.espeak_speak
      self.start_skill = self.null_skill
    else:
      self.speak = self.null_speak
      self.start_skill = self.null_skill
    settings.my_tts = self 
    
  def null_speak(self, msg):
    self.log.debug("quiet msg: %s" % msg)
    
  def null_skill(self, msg):
    print("quiet skill: %s" % msg)
    
  def espeak_speak(self, msg):
    cmdl = 'espeak -k20 "{}"'.format(msg)
    os.system(cmdl)
    
  def mycroft_speak(self, message):
    mycroft_type = 'recognizer_loop:utterance'
    payload = json.dumps({
      "type": mycroft_type,
      "context": "",
      "data": {
          "utterances": ["say {}".format(message)]
      }
    })
    self.log.debug("speaking %s" % payload)
    result = self.myc_conn.send(payload)  
    self.log.debug("rtn: %s" % result)
    print("Spk:", self.myc_conn.recv())
    print("Spk:", self.myc_conn.recv())
    time.sleep(1) # enough time to get in the playing queue?
    return
    
  def mycroft_query(self, msg):
    self.log.info("starting query for: %s" % msg)
    mycroft_type = 'question:query'
    mycroft_data = '{"phrase": "%s"}' % msg
    message = '{"type": "' + mycroft_type + '", "data": ' + mycroft_data + '}'
    self.myc_conn.send(message)
    print("qry:", self.myc_conn.recv())
    print("qry:", self.myc_conn.recv())
    time.sleep(1)
    print("qry:", self.myc_conn.recv())
    print("qry:", self.myc_conn.recv())
   
  def mycroft_skill(self, msg):
    self.log.info("starting skill for: %s" % msg)
    #mycroft_question = 'what time is it'
    mycroft_type = 'recognizer_loop:utterance'
    mycroft_data = '{"utterances": ["%s"]}' % msg
    message = '{"type": "' + mycroft_type + '", "data": ' + mycroft_data + '}'
    self.myc_conn.send(message)
    print("skl:", self.myc_conn.recv())
    print("Skl:", self.myc_conn.recv())

  def spinup(self):
    # start mycroft, wait a while, connect to websocket
    #os.system('~/mycroft-core/start-mycroft.sh voice')
    self.log.info("Mycroft voice started")
    time.sleep(1)
    self.myc_conn = websocket.create_connection(self.uri)
    self.active = True
  
  def spindown(self):
    self.log.info("Stopping Mycroft voice")
    os.system('~/mycroft-core/stop-mycroft.sh voice')
    self.active = False
    

    
class Settings:
  def __init__(self, log):
    self.log = log
    self.mycroft_ip = 'localhost'

   

if __name__ == '__main__':
  # test program here
  import logging
  import logging.handlers
  import paho.mqtt.client as mqtt
  applog = logging.getLogger('skill_conn')
  logging.basicConfig(level=logging.DEBUG,datefmt="%H:%M:%S",format='%(asctime)s %(levelname)-5s %(message)-40s')
  settings = Settings(applog)
  
  def got_message(client, userdata, message):
    payload = str(message.payload.decode("utf-8"))
    applog.info("You said %s" % payload)
   
  mq = mqtt.Client("mycroft_test", False)
  mq.connect('192.168.1.7', 1883)
  mq.subscribe('homie/trumpy_bear/answer')
  mq.on_message = got_message
  mq.loop_start()
  tts = Skill_Conn(settings, True)
  tts.spinup()
  #tts.speak('Can you hear me now. . How bout Now')
  #tts.start_skill('what time is it')
  tts.start_skill('awaken the trumpy bear')
  time.sleep(20)
  print('exiting')
  #tts.spindown()
