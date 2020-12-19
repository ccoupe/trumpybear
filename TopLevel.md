# Trumpy Bear BAD
## Purpose
The meme says "Orange Man Bad". So I built Trumpy Bear Burglar Alarm  and Distraction

Burglar Alarm or Distraction? Rube Goldberg or performance art?
Tied into Home Automation as an Alarm System but it's more than that.
Still, an 'Alarm' System is a decent metaphor for how the system works from a
Home automation perspective. You 'arm' and 'disarm' and 'cancel' and if
needed the Alarm (device) goes off, say when the patio door is opened when 
the 'system' is armed. 

Trumpy Bear is also a sort of entertainment device. It gives the bulglar an
interactive multimedia experience. It pleases me to develop it. It's a show
case of interesting tehnical things.

### Hubitat, MQTT and HSM
Hubitat Elevation (or HE) is a home automation product, (a hub) to control
lights, switches, and more. It allows user written device drivers and 'apps' so
it can be used to integrate odd devices. Trumpy Bear is an odd device. Actually
it is a collection of devices.

#### HE Concepts: Events, Triggers, Commands and Rules.
Drivers listen to device activity and 'commands' When the device does
something the driver (say motion detected) itcreates an 'Event' and sends it to the Hubitat internals
where it triggers 'Apps' listening for that event. There can be multiple
apps waiting for that trigger. One app is 'Rule Machine' which is a Domain
Specific Language (DSL) for writing automations. Other apps are written
in Groovy - some are included with Hubitat and some are 'community' written.
Drivers and apps are written in constrained Groovy for a sandbox.

Rules and Apps can also call 'commands' in drivers. For example if the
driver tells hubitat that it is a 'switch' then it has to provide on() and
off() functions. 

#### HE Concepts: Mode
Hubitat can have a 'Mode' like day,evening,night. 
#### HE Concepts: Presence
#### HE Concepts: HSM

MQTT is used to communicate between devices and processes and sometimes 
intra-process. From the Hubitat point of view intrgration could be done
with a REST or websocket style interface or MQTT. I choose MQTT because
it's a centralized interface that allows either side (client or server) to
disappear and reappear (think reboots and code changes). It's much simpler
to use than HTTP and more structured than websockets. Structure is good
until it isn't. 

## Components
As mentioned above, Trumpy Bear is a collection of devices, rules, events,
and technologies. These will not be described in great detail - they are
'projects' of their own. The main parts of Trumpy Bear runs on a Raspberry
pi 4  with a Touch Panel screen. It does not work well on a Pi 3 - it needs
the speed and memory of a pi4.

### Audio
We have to use Pulse Audio. This is not an easy fit on a Pi but it can be
done. 
#### Speaker 
I choose to use a decent Bluetooth speaker. The built in audio jack of a Pi is
not decent so bluetooth was the next easist (I thought). Decent has a personal price point. Mine was at $30.

#### Microphone
I use a Lapel 'clip on' microphone. It's quality is 'good' enough for
this purpose - voice recording. I connect it to the Pi4 with usb adapter because
the pi audio system is crap. Note the mic is clipped to Trumpy Bear's necktie.

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
easier to just tell alexa to turn on housekeeping. Yes, these holes will
vanish in the future.

### Login
Login is not really a mode - Trumpy Bear doesn't really know or care.
What can be done is via Hubitat rules and the housekeeping switch

### Notifcations
### Cancelling

## Node/Devices/Process/Topics
### TrumpyBear Device
Node: trumpy4 aka trumpy4.local
      Pi4 4GB. 128GB SSD, HMDI Touch Screen, USB sound dongle.
HE Driver: Mqtt Trumpy V2. Gitub:
Python Github: 
MQTT:  /homie/trumpy_bear/<seven devices>

mycroft-bridge
Python Github: 
MQTT: 

mycroft
Python github:

### trumpy_ranger
Node: esp32 192.168.1.xx
Arduino C++ Github: 
MQTT: 
1. /homie/trumpy_ranger/autoranger
2. /homie/trumpy_ranger/display

### Turrets
Node: pinoir (pinoir.local)
    Pi Zero W. 512MB, 16GB sdhc. PCA9685 Servo controler + servos, lasers.
Python github: 
MQTT:
1. /homie/turret_back/turret_1
2. /homie/turret_back/turret_2

### Chimes, Siren, TTS MP3 players
Python gitub:
Nodes: 
1. lostpi.local Raspberry Pi 2. 1GB
2. mini.local - Mac Mini 8GB, 1.5TB - Catalina. 
3. bronco.local - Dell i7 8GB, 1,5TB - Mint 19.1
MQTT:
1. homie/lostpi/player|chime|siren|strobe
2. homie/mini_play/player|chime|siren|strobe
3. homie/bronco_play/player|chime|siren|strobe
## Sequences

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
