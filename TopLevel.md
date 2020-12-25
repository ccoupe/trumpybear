# Trumpy Bear BAD
## Purpose
The meme says "Orange Man Bad". So I built Trumpy Bear BAD (Burglar Alarm and Distraction)

Burglar Alarm and Distraction? Rube Goldberg machine or performance art?
Tied into Home Automation as an Alarm System but it's more than that.
Still, an 'Alarm' System is a decent metaphor for how the system works from a
Home automation perspective. You 'arm' and 'disarm' and 'cancel' and if
needed the Alarm goes off (fires or 'you're fired'), say when the patio door is opened when 
the 'system' is armed. 

Trumpy Bear is also a sort of entertainment device. It gives the bulglar an
interactive multimedia experience. It pleases me to develop it. It's a show
case of interesting technologies like facial recognition, text to voice, 
voice to text, MQTT, Python, Arduino and the Hubitat Elevation home automation
hub. I've never counted the number of computers involed but it's probably 6 or
more, each running it's little piece of whole.

### Hubitat, MQTT and HSM
Hubitat Elevation (or HE) is a home automation product, (a hub) to control
lights, switches, and more. It allows user written device drivers and 'apps' so
it can be used to integrate odd devices. Trumpy Bear is an odd device. Actually
it is a collection of devices.

#### HE Concepts: Events, Triggers, Commands and Rules.
Drivers listen to device activity and 'commands' When the device does
something the driver (say motion detected) creates an 'Event' and sends it to the Hubitat internals
where it triggers 'Apps' listening for that event. There can be multiple
apps waiting for that trigger. One app is 'Rule Machine' which is a Domain
Specific Language (DSL) for writing automations. Other apps are written
in Groovy - some are included with Hubitat and some are 'community' written.
Drivers and apps are written in a sandbox constrained Groovy.

Rules and Apps can also call 'commands' in drivers. For example if the
driver tells hubitat that it is a 'switch' then it has to provide on() and
off() functions that apps and rules can call.

#### HE Concepts: Mode
Hubitat can have a 'Mode' like day,evening,night. And 'away'

#### HE Concepts: Presence
Certain devices, like a cell phone can be a presence device. Typically
something like the Geofence capabilities in the Hubitat phone app. This is
typically used to trigger away mode.

#### HE Concepts: HSM
Hubitat Security Monitor is not an alarm system although it lind of looks like
one and smells like one. 

## Communication. 
MQTT is used to communicate between devices and processes and sometimes 
intra-process. From the Hubitat point of view, integration could be done
with a REST or websocket style interface or MQTT. I choose MQTT because
it's a centralized interface that allows either side (client or server) to
disappear and reappear (think of reboots and code changes). It's much simpler
to use than HTTP and more structured than websockets. Structure is good
until it isn't. 

There are only a few places where synchronization primitives are used because most
things that happen are kind of 'any time after now is fine' for scheduling and events move 
slow enough that it's not a big deal if a video frame is dropped for example.

## Components
As mentioned above, Trumpy Bear is large collection of devices, rules, events,
and technologies. These will not be described in great detail - they are
'projects' of their own. The main parts of Trumpy Bear runs on a Raspberry
pi 4  with a Touch Panel screen. Note: It does not work well on a Pi 3 - it needs
the speed and memory of a pi4.

### Audio
We have to use Pulse Audio. This is not an easy fit on a Pi before the Dec 2020 update, 
but it can be done. 

#### Speaker 
I use a decent Bluetooth speaker. The built in audio jack of a Pi is
not decent so bluetooth was the next easist (I thought). Decent has a personal price point. Mine was at $30.

#### Microphone
I use a Lapel 'clip on' microphone. It's quality is 'good' enough for
this purpose - voice recording. I connect it to the Pi4 with usb adapter because
the pi audio system hardware is crap. Note the mic is clipped to Trumpy Bear's necktie.

#### Mycroft
Mycroft is a Voice Assistant like Amazon Alexa or Google Home or Apple's Siri, One
important difference is the source code (python) is available and integration points are
mostly documented. It listens for the phrase 'Hey Mycroft' and grabs the audio after 
that phrase, does a Speech to Text conversion (STT) via a cloud or two and then matches
the text to a 'skill' to play locally. The skill can send text to the cloud which 
returns audio to play on the speaker (TTS). Skills can do much more than tell the time.

Trumpy Bear uses Mycroft's STT, TTS and skill capabilities to converse in a 'guided'
conversion. 

Mycroft does not run well on a Pi3, IMO. A Pi 4 provides a lot more headroom.

### Vision
There is a camera attatched to the Pi4. In my case it's one that will switch to
night mode/infra red automatticaly. That might be overkill ($) now but at the time, night
vision was deemed worthy of trying. The camera is used to take a picture of the intruder and it
matchs the picture to a list of known, trusted names and pictures. Unknown pictures
are considered 'intruders'  The recognition or matching code is slow on a Pi4 that is also running Mycroft 
so Trumpy Bear sends it to a Nvidia Jetson Nano (which uses the CUDA cores). 

### Defenses
What's the point of a talking alarm if it can't do anything more that make noise.
I decided to build Laser Turrets. A turrent is a pan and tilt mechanism with a laser diode. 
Low power diodes just draw a red dot.  It would be possible to use higher powered lasers
if you wanted to do real damage to your walls and ceiling and figured out the power supply.

I use a separate Pi Zero/W to run the pan/tilt/firing code, taking commands from MQTT
topics and payloads. I also invested in a 3D printer because there are multiple speciality
cases required so all Laser parts look like something interesting. I'm working towards 
looking menacing.

### Display and Control
#### Ranger
I build a 'ranger' device from an ESP32 and Arduino Sketch (C++) that uses
an ultra sonic sensor to measure how close the 'subject' is from the camera and
since I had one in the parts bin, a two line LCD display for messages from
Trumpybear. It communcates via MQTT and is a separate project usable for
different purposes. Part of the performance. 

#### Panel
This was a late edition to the 'experience' and greatly simplified some
complex interactions. If you think they are complex now, you should see
the older ones. It's a touch screen HDMI monitor for the Pi4 running a
GUI Kiosk like application I wrote. Of course I used my Shoes project for
the GUI code because it was easy and on hand. The Panel is like an Alarm
Control panel. Instead of entering your PIN code it takes your picture, compares
it to the list and if it matches you are allowed to use it to turn on/off the
alarm 'system' and you can play with the lasers too which helps with debugging and
testing turret problems. 

### AV system (Harmony, Yamaha Reciever)
My HE automations include Turn on/off the TV and volume control and selecting 
Harmony 'Activities' so it's part of the performance.

### Chimes, Siren, TTS
The Hubitat automations also use Chimes and Sirens. I wrote some python code to
play mp3 files on a Mac (OSX) and Linux (Ubuntu/Mint) using the attached speakers.
Part of the performance. There is an old Pi2 I found in a drawer that run the code and
attached to the TV (a Harmony Activity is required)

They are also Hubitat TTS devices. No need for a Sonos if you have speakers
connected to a computer.
 
## States and Trumpy Modes. 
If you are thinking that there are a lot of messages flying back and forth 
from the devices, processes and mqtt and hubitat and it's hard to keep track
of what's going on - you are correct. It is hard. Everything is event driven 
and no one device knows what the 'total' state is - because there isn't a 'total'

However, the TrumpyBear code in trumpy.py does have a state machine because some
of it's actions require state. Actually there are 3 state machines only one of
which is in use at a time. I call them modes sometimes but these are NOT
Hubitat modes. Tame mode (tame state machine) basically does nothing. It
just ignores any events that (mistakanly) arrive.

### Mean Mode
The mean mode state machine does all the questions and answers via mycroft
and various message displays to 'identify' and 'scare' or amuse the intruder.

### Register Mode
Some people are not intruders. Me for one. My house cleaner is not an intruder.
Friends and family are not intruders. I need a way to 'register' them and move
their picture and name over to the Jetson Nano that does the facial recognition
so they can login. 

Yes, a smart burglar could read this documentation and ask Alexa to register
him and then turn off the alarm. There is always a weak spot. It's even
easier to just tell alexa to turn on housekeeping. 

### Login Mode
This mode does some initialization for the 'Control Panel', the touch scree
on the Pi. Trumpybear can run without the control panel but it makes debugging
and testing so much nicer. It has very little state tracking which I consider a
good thing.


### Login
Login is not really a mode - Trumpy Bear doesn't really know or care.
What can be done is via Hubitat rules and the housekeeping switch

### Notifcations

### Cancelling
Cancelling an alarm is difficult because there is no central state. There
is an attempt to skip certain noisy steps if the housekeeping switch is on.

## Node/Devices/Process/Topics
### TrumpyBear Device
#### Node: trumpy4 aka trumpy4.local
      Pi4 4GB. 128GB SSD, HMDI Touch Screen, USB sound dongle.
(HE Driver: Mqtt Trumpy V2)[https://github.com/ccoupe/hubitat/blob/master/mqtt-trumpy.groovy]
(Python Github:)[https://github.com/ccoupe/trumpybear] 
#### MQTT:  /homie/trumpy_bear/<seven devices>
#### Startup
This is complicated. TrumpyBear is a user process but `systemd --user enable`
is troublesome for me and my Raspberry OS. It's probably me. It's also
related to the Raspbian PulseAudio problem. TB launches when the 'pi' user has
auto-logged in to the GUI. For consistency we do use .services files.

The systemd --user .service files are in /home/pi/.config/systemd/user but
the real magic occurs in /etc/xdg/lxsession/LXDE-pi/autostart:
```sh
@lxpanel --profile LXDE-pi
@pcmanfm --desktop --profile LXDE-pi
@xscreensaver -no-splash
systemctl --user start mqttmycroft
systemctl --user start mycroft
systemctl --user start tblogin
systemctl --user start trumpy
```
NOTE: /usr/local/lib/mqttmycroft/mqttmycroft.sh loads first and it runs 
first so it can manipulate the bluetooth settings before loading the 
mycroft-bridge. 

#### trumpy.json
'''json
{
  "mqtt_server_ip": "192.168.1.7",
  "mqtt_port": 1883,
  "mqtt_client_name": "trumpy_bear1",
  "homie_device": "trumpy_bear",
  "homie_name": "Trumpy Bear Pi3",
  "camera_number": 0,
  "camera_topic": "trumpy_cam",
  "mycroft_ip": "192.168.1.10",
  "ranger_mode": "once",
  "face_server_ip": "192.168.1.4",
  "face_port": 4774,
  "ml_algo": "Cnn_Shapes",
  "confidence": 0.4,
  "ml_server_ip": "192.168.1.2",
  "ml_port": 4783,
  "use_ml": "remote_zmq",
  "turrets": [
    {
	"name": "Front Center",
	"topic": "homie/turret_front/turret_1/control",
    "front": true,
	"pan_min": 51,
	"pan_max": 150,
	"tilt_min": 70,
    "tilt_max": 120
    },
    {
	"name": "Left Back",
	"topic": "homie/turret_back/turret_1/control",
    "front": false,
	"pan_min": 60,
	"pan_max": 180,
	"tilt_min": 80,
	"tilt_max": 120
    }
  ]
}
'''
NOTE: the `turrets` list of hashes is sent to the Front Panel (login.rb)
where the min and max values are used.

### mycroft
Mycroft is an open source digital assistant like Alexa, Google Home or Siri.
It has skills similar to the others to extend what it can respond to. It't also
has a REST and/or Websocket API. In our case, the Trumpybear skill constrains
what mycroft can do - we want the text to speech and speech to text and limited
skill matching but not the 'general' purpose skill matching. Until we want the 
general.
### /home/pi/mycroft-core
This is where I `git clone`d mycroft. Git is not the optimal choice because
mycroft has a way of unwanted changing on us because its startup checks
git. '''/opt/mycroft/skills'' in particular need locking down or it will delete our
special sauce. 
### Github
### mycroft.service
Like the bridge and Trumpybear the launch is for user space. See trumpybear
for the description.

### mycroft-bridge
(Python Github)[https://github.com/ccoupe/trumpy_mycroft]
#### MQTT:  homie/trumpy_bear/speech
There are 'ctl', 'ask', 'reply', 'say' subtopics. 
### mqttmycroft.service
Like the mycroft and Trumpybear the launch is for user space. See trumpybear
for the description.
### mqttmycroft.sh
### trumpy.json
'''json
{
  "mqtt_server_ip": "192.168.1.7",
  "mqtt_port": 1883,
  "mqtt_client_name": "trumpy_bridge",
  "homie_device": "trumpy_bear",
  "bridge_ip": "192.168.1.8",
  "bridge_port": 8281
}
'''

### trumpy_ranger
#### Node: esp32 192.168.1.xx
(Arduino C++ Github)[https://github.com/ccoupe/arduino/tree/master/ranger]
#### MQTT: 
1. /homie/trumpy_ranger/autoranger
2. /homie/trumpy_ranger/display

### Turrets
#### Node: pi0fr.local,  pinoir.local
    Pi Zero W. 512MB, 16GB sdhc. PCA9685 Servo controler + servos, lasers.
(Python github:)[https://github.com/ccoupe/mqtt-turret]
#### MQTT:
1. /homie/turret_front/turret_1
2. /homie/turret_back/turret_1
#### pi0fr.json
'''json
{
  "mqtt_server_ip": "192.168.1.7",
  "mqtt_port": 1883,
  "mqtt_client_name": "turret_front",
  "homie_device": "turret_front",
  "homie_name": "Pi 0w Front Laser Turrets",
  "turrets": [
    {
	"position": "fc",
        "hw": true,
        "laser_pin" : 17,
        "pan_pin": 0,
        "tilt_pin": 1,
	"delay": 0.25,
	"pan_min": 45,
	"pan_max": 140,
	"tilt_min": 70,
	"tilt_max": 120,
	"pant_min": 51,
	"pant_max": 150,
	"tiltt_min": 70,
	"tiltt_max": 120
    }
  ]
}
'''
#### pinoir.json
'''json
{
  "mqtt_server_ip": "192.168.1.7",
  "mqtt_port": 1883,
  "mqtt_client_name": "turret_back",
  "homie_device": "turret_back",
  "homie_name": "Pi 0w Laser Turrets",
  "turrets": [
    {
	"position": "br",
        "hw": true,
        "laser_pin" : 17,
        "pan_pin": 0,
        "tilt_pin": 1,
	"delay": 0.25,
	"pan_min": 40,
	"pan_max": 180,
	"tilt_min": 90,
	"tilt_max": 140
    }
  ]
}
'''
### Tracker
#### Node: bronco, [opt nano]
    Dell i7. 
(Python github:)[https://github.com/ccoupe/tracker] ImageZMQ
(Python github:)[https://github.com/ccoupe/target] rpyc, not used
#### MQTT:
1. /homie/turret_tracker/track/
#### bronco.json
'''json
{
  "mqtt_server_ip": "192.168.1.7",
  "mqtt_port": 1883,
  "mqtt_client_name": "tracker_1",
  "homie_device": "turret_tracker",
  "homie_name": "Shape tracker for turrets",
  "image_port": 4783,
  "confidence": 0.40,
  "provide_rtsp": false,
  "http_port": 5000,
  "turrets": ["homie/turret_front/turret_1/control/set",
              "homie/turret_back/turret_1/control/set"]
}
'''
### Facial Recognition
rpyc call from trumpybear to rpc server process on port 4774
#### Node: nano
      Nvidia Jetson Nano. 4GB, SSD.
(Python github:)[https://github.com/ccoupe/fcrecog]
#### mlface.service
#### mlface.sh

### Chimes, Siren, TTS MP3 players
(Python gitub)[https://github.com/ccoupe/mqtt-alarm]
(HE Chime driver)[https://github.com/ccoupe/hubitat/blob/master/mqtt-chime.groovy]
(HE Siren driver)[https://github.com/ccoupe/hubitat/blob/master/mqtt-siren.groovy]
(HE TTS driver)[https://github.com/ccoupe/hubitat/blob/master/mqtt-tts.groovy]
(HE Alarm v2.1)[https://github.com/ccoupe/hubitat/blob/master/mqtt-alarm2.groovy]
#### Nodes: 
1. kodi.local Raspberry Pi 4. 4GB (Chime only)
2. mini.local - Mac Mini 8GB, 1.5TB - Catalina. 
3. bronco.local - Dell i7 16GB, 1,5TB - Mint 19.1
4. trumpy4.local Raspberry Pi 4 4GB.
#### MQTT:
1. homie/kodi_player/player|chime|siren|strobe
2. homie/mini_player/player|chime|siren|strobe
3. homie/bronco_player/player|chime|siren|strobe
4. homie/trumpybear/player|chime|siren
#### json example
'''json
{
  "mqtt_server_ip": "192.168.1.7",
  "mqtt_port": 1883,
  "mqtt_client_name": "mini_play1",
  "homie_device": "mini_play",
  "homie_name": "Mac mini Mp3 Play"
}
'''
### Login Panel aka Front Panel
This is a 10" hdmi touch screen on the trumpybear pi4. Trumpybear can
amuse or scare burglars without the touchscreen The screen app is
a different process that communicated with the other devices and processes
via MQTT. 

So while it's optional it's really nice for testing and debugging because
it knows how to talk to some internal connections. 

Unlike everything else which was written in Python or Ardinuo C++, `login.rb`
is a Shoes Ruby script. Which means you need a version of Shoes for Raspberry.
Not a problem for me. I maintain Shoes - get your copy at walkabout.mvmanila.com
You'll also need to install VLC.

#### (Gitbub)[https://github.com/ccoupe/front_panel]
#### Nodes
trumpy4.local
#### MQTT
1. "homie/trumpy_bear/screen/control/set"
2. "homie/trumpy_bear/screen/control"
3. "homie/trumpy_bear/control/cmd/set"
4. 'homie/trumpy_ranger/display/mode/set' 
5. 'homie/trumpy_ranger/display/text/set'
6. 'homie/turret_front/turret_1/control/set'
7. 'homie/turret_back/turret_1/control/set'
8. 'homie/turret_font/turret_1/control'
9. 'homie/turret_back/turret_1/control'
10. 'homie/housekeeping/switch/state' 
#### tblogin.service
See startup for TrumpyBear.

## Hubitat Rules
You are correct if you think the tangle mess of Hubitat rules, virtual switches,
custom drivers, mqtt topics and json is barely coherent. Sometimes you just do
what has to be done.
### HSM -> "You're Fired" Switch -> {"cmd": "begin"}
HE Virtual switch - Used by Dashboard and HSM.
Rule: `Run Trumpy Bear`
Trigger: `Your Fired(off) turns *changed*`
```
IF (Your Fired(off) is on(F) [FALSE]) THEN
	Off: Kitchen Lights Switch, Counter Lights
	On: PowerOff
	exec({"exec": "hzig", "lines": 8,  "count": 4, "time": 4}) on Laser One
	exec({"exec": "vzig", "count":4, "lines":8, "time":4}) on Laser Two
	Delay 0:00:15
	On: Trumpy Lamp
	On: Trumpy Bear
	Notify Cecil’s iPhone: 'Trumpy Bear was activated on %date% %time%'
ELSE
	Unmute Yamaha RCVR - Zone Main_Zone
	Off: Trumpy Lamp
	Off: Trumpy Bear
END-IF
```
### Trumpy Bear 'talk or music' -> music, set Trumpy Enable Alarm 
MQTT: homie/trumpy_enable/switch/state = 'on'|'off'
  set by trumpy.py mean mode state machine: Event.reply and State.four_qs
  begin_intruder()
```
IF (Trumpy Enable Alarm(off) is on(F)  AND 
Housekeeping Switch(off) is off(T) [FALSE]) THEN
	On: Lostpi
	Delay 0:00:10
	Unmute Yamaha RCVR - Zone Main_Zone
	Set Volume on Yamaha RCVR - Zone Main_Zone to 70
	Off: Trumpy Lamp
	Chime: Play Sound on Lostpi Chimes sound number 11
	Delay 0:01:00 (cancelable)
	Set Volume on Yamaha RCVR - Zone Main_Zone to 50
	Chime: Stop Sound on Lostpi Chimes
	On: Cops Arrive Switch
ELSE-IF (Trumpy Enable Alarm(off) is off(T)  AND 
	Mode is Away(T) [TRUE]) THEN
	Off: Trumpy Lamp, Cops Arrive Switch
	Chime: Stop Sound on Mac Mini Chime, Lostpi Chimes
	On: Housekeeping Switch
ELSE
	Off: Cops Arrive Switch
	Chime: Stop Sound on Lostpi Chimes
	Chime: Stop Sound on Mac Mini Chime
	On: Trumpy Lamp
	Set Volume on Yamaha RCVR - Zone Main_Zone to 50
END-IF
```
### Cops Arrive Switch
MQTT: homie/trumpy_cops/switch/state = 'on'|'off'
```
IF (Cops Arrive Switch(off) is on(F) [FALSE]) THEN
	IF (Housekeeping Switch(off) is off(T) [TRUE]) THEN
		Speak on Trumpy Bear: 'Do you hear that?'
		Set color: Alarm Lights ->Red  ->Level: 90
		Off: Trumpy Lamp
		Chime: Play Sound on Mac Mini Chime sound number 10
	ELSE
		Hubitat® Safety Monitor: Disarm All
		Chime: Stop Sound on Mac Mini Chime
		Off: Trumpy Lamp, Your Fired, Alarm Lights, Trumpy Enable Alarm
	END-IF
	Off: Cops Arrive Switch
END-IF
```
### Trumpy Active Switch
MQTT: homie/trumpy_active/switch/state = 'on'|'off'
Used by Panel (login => on, logout => off)
```
F (Trumpy Active(off) is on(F) [FALSE]) THEN
	On: Trumpy Lamp
	Mute Yamaha RCVR - Zone Main_Zone
ELSE
	Unmute Yamaha RCVR - Zone Main_Zone
	Off: Trumpy Lamp
END-IF
```
### Housekeeping Switch
Purpose: Acts as an Alarm on/off/cancel. 
1.Sets HE mode to 'cleaning' (from Armed-Away for example)
2.Prevents HSM from starting Trumpy Bear. 
3.Cancels any Trumpy Bear sequences in progress.
  
MQTT: homie/housekeeping/switch/state = 'on'|'off'
Set by Panel->Login->Alarm->Turn OFF (set switch on via MQTT) or Alexa
or Dashboard

Cleared by Alexa or Dashboard or 18:00 and mode == 'cleaning' or 
Panel->Login->Alarm->Turn On.

Rule `Set Cleaning Mode`
Trigger: `Housekeeping Switch(off) turns *changed*`
```
IF (Housekeeping Switch(off) is on(F) [FALSE]) THEN
	Mode: Cleaning
	Hubitat® Safety Monitor: Disarm All
ELSE
	Mode: Away
	Hubitat® Safety Monitor: Arm Away
END-IF
```
Rule: `Cancel Alarms`
Trigger: `Mode becomes *changed*`
```
IF (Mode is Cleaning(F) [FALSE]) THEN
	IF (Cops Arrive Switch(off) is on(F) [FALSE]) THEN
		Off: Cops Arrive Switch
	END-IF
	IF (Trumpy Enable Alarm(off) is on(F) [FALSE]) THEN
		Off: Trumpy Enable Alarm
	END-IF
	IF (Trumpy Active(off) is on(F) [FALSE]) THEN
		Off: Your Fired, Trumpy Active, Trumpy Bear
	END-IF
END-IF
```
### Registering
To register someone new, From alexa or the dashboard turn on the
'Trumpy Register' switch. This sends a {"cmd": "register"} message
to trumpy.py . Causes this rule to fire. Which turns on a switch
which causes another rule to fire.  Note: these chained Hubitat automations
are running while the `cmd: register` is running.

MQTT: homie/trumpy_bear/control/
Rule: `Trumpy Register Lamp`
Trigger: `Trumpy Register(off) turns on`
```
On: Trumpy Active
```
### Mycroft bridge
### Touch Screen Login
This code is a separate process from trumpy bear,  mycroft and the bridge.
The operations allowed depend on the particular GUI panel being displayed.
It uses a lot of MQTT interactions. It listens on these topics:
MQTT:
1. "homie/trumpy_bear/screen/control/set" This is only for the touch screen
2. 'homie/trumpy_ranger/display/mode/set'
3. 'homie/trumpy_ranger/display/text/set'
4. 'homie/turret_back/turret_1/control'
5. 'homie/turret_back/turret_2/control'
When the login button is pushed (touched) the code publishs `awake` on
`homie/trumpy_bear/screen/control` . That causes the 
