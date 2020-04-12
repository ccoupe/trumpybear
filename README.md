# Trumpy Bear

![trumpyad](https://user-images.githubusercontent.com/222691/79056411-8bce5700-7c13-11ea-9b6f-e80180116d51.png)
TrumpyBear is Cute, Snarky and sometimes useful. It has a camera, a 
microphone and a Raspberry Pi3. Inside, it talks with an MQTT broker. 
It can do a lot of things. Interesting things because there is some AI
involved. 

TrumpyBear talks to an MQTT broker. I have a Hubitat home automation hub
and with my hubitat driver, it's a motion sensor. It's a tts device. It
could be a Burglar deterent device - that was orignal goal. Something to
scare buglars and impress friends and family and buld something fun and
explore AI and Machine Learning on a budget. 

Wait, there's more.  

It recognizes faces. It takes a picture or video clip. It asks your name. 
If your face and name isn't reqistered then you have to ask to be registered
or it goes into buglar mode (undefined at this time). If it does
recognize you then you can initiate conversations. It has the Mycroft speech
platform running (that's like Alexa but Open source). Or it could have
Alexa. 

You're probably thinking that's a lot to do for a Raspberry pi3. Yes, yes 
it is.  Of course most of time, it's just looking for motion or a mqtt command
to spring into action.  When it gets motion or something like motion, it
does a RPC to a NVidia Jetson Nano to detect a person (with a neural net)
If it's a person shape, mqtt is informed that motion occured. Hubitat is informed
via that MQTT message and runs some of its rules: If it's after bedtime or 
I'm not home and the back door was opened then it turns on a light or two.
It might turn on the TV and AV reciever and .... Lastly, Hubitat will send 
another message to mqtt which TrumpyBear (pi3) picks up. 

If it's just a person walking around in normal times, then it's just a motionsensor for
Hubitat, dressed in a costume. But, at night:

Now it does face recognition via a remote procedure call (RPC) to the Jetson Nano) and it starts
the conversation (Mycroft or Alexa) and will speak something like 
"Trumpy Bear sees you moving. Approach me and stand still so I can see you better.
What is your name?"  Assuming a name is spoken and it matches a registered
face then it can carry on a conversation, of sorts, tailored to the name/picture
pair. If the name doesn't match a known picture it can ask if it should save the
name/picture it has (register). Thats the 'normal' path. There are error paths. 
A burglar (an 'undocumented house vistor' in woke speach) probably won't 
ask to be registered so Trumpybear will tell Hubitat via MQTT to do some
'alarm' things. Maybe flash the lights or fire off a siren or ...)

The conversations are preloaded Mycroft Skills (or Alexa skills if I use Alexa)
plus any skills I or you write. Add that to the skills list!

In summary, Think of it as an echo dot activated by a motion sensor, 
protected by face recognition. In a Teddy bear with an attitude.

## Bill of Materials
1. [Trumpy Bear (TM)](https://gettrumpybear.com)
2. [Raspberry Pi3](https://www.amazon.com/CanaKit-Raspberry-Starter-Premium-Black/dp/B07BCC8PK7/ref=sr_1_1_sspa?crid=36UGB73QFQI2N&dchild=1&keywords=raspberry+pi+3&qid=1586629688&sprefix=raspb%2Caps%2C233&sr=8-1-spons&psc=1&spLa=ZW5jcnlwdGVkUXVhbGlmaWVyPUFJS1hEN1AwNzRGRTQmZW5jcnlwdGVkSWQ9QTA2NzU5ODIxUUdGUUROVllKOFZRJmVuY3J5cHRlZEFkSWQ9QTA3NjE5OTJMWjk0Q1lURVJZMVomd2lkZ2V0TmFtZT1zcF9hdGYmYWN0aW9uPWNsaWNrUmVkaXJlY3QmZG9Ob3RMb2dDbGljaz10cnVl) (pi4 might be too hot, pi0 doesn't have needed punch)
3. [Raspberry camera](https://www.amazon.com/gp/product/B07QKCGX1Z?ref=ppx_pt2_dt_b_prod_image) with day and night capabilities
4. [USB headphone dongle](https://www.amazon.com/Sabrent-External-Adapter-Windows-AU-MMSA/dp/B00IRVQ0F8/ref=sr_1_3?crid=VPIDSAG2OKQ4&dchild=1&keywords=usb+headphone+adapter&qid=1586631203&sprefix=usb+headphone%2Cundefined%2C225&sr=8-3)
5. [Lapel (clip on) Microphone](https://www.amazon.com/gp/product/B075VQ7VG7?ref=ppx_pt2_dt_b_prod_image) - attaches to headphone dongle
6. [Bluetooth speaker](https://www.amazon.com/gp/product/B010OYASRG?ref=ppx_pt2_dt_b_prod_image) (the raspberry speaker jack is crap). Pick one
that is USB powered and doesn't disconnect if there is no activity.
7. [Nvidia Jetson Nano](https://www.amazon.com/Seeed-Studio-NVIDIA-Jetson-Developer/dp/B07SGBHDCZ/ref=sr_1_1_sspa?crid=3NQA143FHEASQ&dchild=1&keywords=jetson+nano&qid=1586631097&sprefix=jetson+nan%2Caps%2C235&sr=8-1-spons&psc=1&spLa=ZW5jcnlwdGVkUXVhbGlmaWVyPUFBME1KV1lDVzJUSksmZW5jcnlwdGVkSWQ9QTA5NzAxNjcxS0NVNTZET1A3MldRJmVuY3J5cHRlZEFkSWQ9QTA1NzE4MTBFRUZRVU05RFFWWVYmd2lkZ2V0TmFtZT1zcF9hdGYmYWN0aW9uPWNsaWNrUmVkaXJlY3QmZG9Ob3RMb2dDbGljaz10cnVl) and
the larger power supply.
8. Mqtt broker (could be the jetson or the pi3 but an extra Pi won't hurt anyone).
9. Cables, wires, Pi power supply and case... and stuff.
10. HDMI Monitor, keyboard, mouse to setup Pi and Jetson
11. [Hubitat]() hub - leads to a deep money pit. Beware. It could be anything
that talks to MQTT but you'll be writing more code.
12. An full time internet connection. There is a limit what TrumpyBear can
do without some Cloud servers.

A note about using the Nvidia Jetson. This is not an absolute requirement
but it will be cheaper than the alternatives. Why? Neural nets are computation
hogs. A dedicated i5 won't have the oopmh. An i7 might but either one of those
is serious money with electrical power and space issues. You could put an expensive
NVidia graphics card in a machine and use that. If you already have one of
those cards then odds are your running Windows and Games or a bitcoin miner. 
I use Linux and can't help you with Windows or Crypto Currency/.
Could you use a Coral accelerator on the pi3 or a pi4 instead and run everything on one
box? Probably. Try it and let me know. Most of those options are more expensive. Yes,
You could run everything on the Jetson if you have enough usb ports but it
would be clumsy - it can get hot. 

Finally, the Jetson is 'damn cool' and you wanted a reason to get one. You're Welcome.

## Required Skills
1. Must have moderate skill in Linux admin. There's a lot to do and I won't
spell it out for a quick copy and paste.
2. Python programming if you want to modify anything. You probably will.
3. Groovy programming if you want to modify the Hubitat driver.
4. Hubitat admin (or you hub of choice) and some networking skills.
5. Understanding of MQTT. Hint: it's not a database.
5. Patience and a sense of humor. 
6. Lots of time and a fair bit of money. You have to really want this.

### Names
Everything needs a name. They all need static IP address.  I use 192.168.1.nn
I'm going to use my names below so you'll need to subsitute your names.
1. bronco - my main linux box with a nice big monitor, an Intel i7 with lots of
memory and a SSD. It runs Mint 19.1 (for now). Also known as bronco.local
2. trumpypi (trumpypi.local). This is the pi3 that goes in the bear.
3. nano (nano.local). Ah, it's the Jetson nano.
4. pi4 (pi4.local)  - it runs the MQTT broker. It runs some other things
unrelated to TrumpyBear. You could put the MQTT broker on your Jetson. I might
move MQTT over to my Nano someday. It's a pain to move MQTT because so many
of my home automation things can depend on it. I'll call it mqtt.local when I do.

### File Sharing
I provide an NFS server (/Projects) on my main machine and mount it on the Pi3 and 
the Jetson Nano and the MQTT broker. That make it easy to move files around.
I can ssh into any of them from my main system. If you do not want to do that 
then you either lack the needed Linux skills or you know of a better way 
(aka your way).

## Overview of Work.
1. Install Hubitat. 
2. Install MQTT broker (another pi or use Jetson Nano)
3. Assemble pi3, camera, microphone. build opencv for Python.
   We're building a motionsensor for Hubitat.
4. Install Jetson Nano (opencv + cuda), Enable AI for motionsensor
5. Setup the Conversation stuff -  Mycroft and or Alexa
6. Install pi3 in Trumpy Bear
7. Create marketing plan.
8
9. Profit!

## Home Automation setup.
This is easy to write about because the instructions and tasks are somewhere else.
It's a challenging effort and doesn't really end. There is a whole other world
of resources to help you. 

## Install MQTT broker. 
I use Mosquitto running on a Pi4 running Raspbian 'Buster'. 
`sudo apt install mosquitto mosquitto-clients`
You are advised to get a copy of the free [MQTT Explorer](). Mine runs on bronco, 
the main box in my home.
It's handy to install the mosquitto-clients on you other linux systems too.

## TrumpyPi
### Burn Buster.
Use balenaEtcher to burn the SDHC card with Raspbian Buster (Full)
### Assemble
Hookup monitor, keyboard, mouse and boot. Add the camera and microphone
later. 
### Networking
1. Setup wifi.
2. Assign static IP on your router.
3. Setup host/etc/hosts and /etc/hostname 
4. get ssh working.
5. mount the nfs share with /etc/fstab
6. You no longer need the Monitor, keyboard and mouse. We can ssh in and work
from a terminal.
### Speaker
Uses the built in bluetooth on the Pi. TrumpyBear wants to use pulseaudio which will conflict 
with how Raspberry.org thinks things should be done - they like Alsa. DO NOT
follow internet instructions for ALSA or asoundrc. You'll waste hours and hours if you do.
`sudo apt install pulseaudio pulseaudio-module-bluetooth mpg123`
Attach a usb cable for powering the speaker to the pi3. reboot `sudo reboot now`
```sh
bluetoothctl
agent on
power on
scan on
trust XX
pair XX
connect XX
quit
```
Get and mp3 file and play it. I copied the Talking Head "Stop making Sense" 
from the album of that name to 'song.mp3'. Now try `mpg123 song.mp3` Odds are high it won't work.
If it doesn't, `sudo killall bluealsa` which will disconnect from the speaker so
bluetoothctl again and connect back to the speaker. While you're there copy that 12:34:56:78 
device address. You'll need it. Now try the `mpg123 song.mp3` again. 
If you hear the song properly we can move on to something that might be useful

### TTS (Text to Speach)
TrumpyBear is a Hubitat compatible TTS speaker. That's fun. And useful.
It tests our MQTT setup, PI and Hubitat and right about now, you need
something that says, "I'm on track and having fun!"

Clone the TrumpyBear repository. `git clone https://github.com/ccoupe/trumpybear.git`
and then `cd trumpybear` look around inside. It would be wise to do this in your
networked directory, so it's ~/Projects/iot/trumpybear for me. 

Next, grab a copy of [this hubitat driver ](https://raw.githubusercontent.com/ccoupe/hubitat/master/mqtt-alarm.groovy)
and install it as a Hubitat user device. You want to configure the device in
Hubitat for the IP address of your MQTT broker. In the "Topic to Publish", type in
`homie/trumpy_play`. You can play with the different voices later. Enable logging and
Save Preferences. You should see some info on the Hubitat log files and MQTT Explorer
should show a homie/trumpy_play topic. Now we need to connect something thats going to
respond to commands from Hubitat via MQTT. That is the cloned code in your trumpybear directory.

Note: The trumpy bear code is derived from [one of my other projects](https://github.com/ccoupe/mqtt-alarm) 
which is Hubitat TTS for OSX and 'Normal Linux' systems. Raspbian is not normal linux when dealing with 
pulseaudio. We will overcome! Take a moment to reflect about our device. It's
not going to be a general purpose computer. It's purpose built. We're going to put
it in a Teddy Bear. It's not normal. We can take short cuts. We don't have to be
professional Linux administrators and programmers. It's a Teddy Bear for crying out
loud. We're hackers!

I digress. Where was I going?  alarm.py and getting things to live after a reboot.
Yeah. We want to do that.

Like I've said, too many times, Raspbian and pulseaudio don't play well. 
Truth be told, pulse audio and headless devices don't play well either. But,
a disconnected monitor is not headless - it's just missing it's head for a
while. All the GUI code is loaded and running, waiting for a monitor or
a VNC connection if you enabled it in raspi-config (go ahead and do the VNC dance
if you like. I did but it's mostly optional)

So, when it boots, user 'pi' will be logged in and only then will the pi connect
to the bluetooth speaker. we can't do the `sudo killall bluealsa` and reconect until
then. We can't use systemd to do that at boot time. I didn't write those rules but they are rules
we must live with. We use an lxsession autostart script. Before we get to that lets
get the TTS code working with hubitat. So get back to the pi3 and the trumpybear
directory. 

#### pip3 

```sh
sudo -H pip3 install paho-mqtt
```
Caution: You may have several python3 library locations. We want a python3
that is available at boot time. We are NOT following best practices by setting
up a python environment picker. Why? It just complicates things for a purpose
build device and we don't need that. We're hackers! The '-H' flag on sudo is
often needed with pip3.

#### trumpy.json
```
{
  "mqtt_server_ip": "192.168.1.7",
  "mqtt_port": 1883,
  "mqtt_client_name": "trumpy_play1",
  "homie_device": "trumpy_play",
  "homie_name": "TrumpyBear Mp3 Play"
}
```
Replace the ip number with your MQTT broker ip address.

#### Launch. Test. Play
Run this command:
```sh
/usr/bin/python3 alarm.py -d2 -c trumpy.json
```
You should see some messages showing your trumpy.json settings and it waits.
It waits for you to got to Your web browser with the Trumpy Bear device page.
You can type in a message inthe little 'Speak' box. Perhaps "Can you hear me now?"
Then ..., wait for it. You push the speak button! As Dave Barry might say, 
"and in a few seconds or less you get an error message. Sometimes, if you are lucky
the device speaks to you, a mere mortal". It's a good thing that Dave doesn't write
documentation otherwise you'd have too much fun.

If it works, you can change the voice and Save Preferences in Hubitat. Type in naughty words
and phrases. Type ^C to kill the process and get back to your prompt.


#### Autostart.
We need a shell script to run at boot time to load the code and start it.
You have to modify that script, trumpybear.sh to use your Bluetooth Speakers
mac code. Remember when I told you to write it down because you'd need it later?

Note that it 'cd's to the directory. Modify it for where you put the code.

You should comment out the microphone line. Later, you'll change that 
line when we get to that bit of joy (way, way down below - days from now).
You also need to copy the autostart file. 
```sh
mkdir -p ~/.trumpybear
cp trumpybear.sh ~/.trumpybear
mkdir -p ~/.config/lxsession/LXDE-pi
cp autostart ~/.config/lxsession/LXDE-pi
```
Now we reboot `sudo reboot now`. Wait a minute or two and ssh back in. 
Lets check and make sure everything is good.
`ps ax | grep python` You should see that alarm.py is running.
`ps ax | grep bluealsa` should NOT be running and the speaker paired up.

Play your inspirational song.mp3. If everything is OK. Go back to
Hubitat and the device page. Speak a new phrase like "This is freaking awesome!
Thank you Trumpy Bear!" 

You could write some RM rules that send text to the device or use it
in Notifications. It's a little boring frankly but it's just a stopping
point in a long journey. You should look at the python code. It's pretty
simple except for the parts about telling 'self' what to do. Take a look
at the .groovy code. As hubitat drivers go, it's pretty easy.  Now think about
what MQTT is doing and how both sides use it to communicate. We are going
to be doing a lot more. You might also reflect that neither side, Hubitat
or alarm.py knows who or what is on the other side. There's no guarantee that
either side is working or how fast it's working or when it's done. Embrace that.
Those are not important things.  It's going in a Teddy Bear. It's not sighting in a
weapon. That's a future enhancement.

I'll also note that the autostart file is very dependent on Raspbian not
changing the startup process. Again. We'll probably be back at some date in the
future to change that to whatever the next better way is. 

### Camera and motion detector
TrumpyBear usea a camera as a motionsensor as well as take picture and
video clips. As a motionsensor it has some percularities. It can get
confused by lights going off and on. It can be very chatty, constantly
finding motion and not finding it and telling Hubitat all about it.
There is a whole lot of 'it works for me' in the code as I tamed those issues. 

[It's another project of mine](https://github.com/ccoupe/mqtt-camera-motion)
and I have two of them in my house, not counting TrumpyBear. They will keep 
the lights on as long as they identify a person. That can be multiple hours long
sitting in my comfy chair or working in my office.

#### Install camera. 
I chose a raspberry (CSI) camera that claims to work in both day and night.
Connect it to the raspberry. Be very careful with the clip on the connector.
I can break and you will curse loadly if you fat finger it.

The interwebs are full of instructions on installing and testing the camera.
Find one and follow it.

#### Motionsenor Code
You need a different directory, next to trumpybear, not below it, not above it, 
Next to it. Sadly, I called mine 'mqtt-vision'. You can do better and rename
it after `git clone https://github.com/ccoupe/mqtt-camera-motion.git`

It is a separate device from the TTS alarm thing. MQTT thinks they are
different, Hubitat thinks they are different and they are two different
programs on the pi. Not dependent on each other. Yet.
 
[Follow those instructions](https://github.com/ccoupe/mqtt-camera-motion)
It should go without saying that you want to test the motionsenor with
Hubitat. That could take several days, a few minutes per day it all it takes.
Without the AI/ML enabled it's a chatty device.

It works much better when you turn on the AI. I like Cnn_Shapes but there
are situations where the other algorithms will work better.  It all depends
on where the bear sits and what it can 'see'


## Jetson Nano or GPU or Coral
[Refer back](https://github.com/ccoupe/mqtt-camera-motion) to the discussion
on shape_server as a remote process. We can run shape_server on an optimized
system. I'm using a Jetson Nano
### Setup
You want to do all the network and setup things you did for the Pi setup,
ssh and nfs and ...
### Opencv with CUDA support.
Refer to any number of youtube and/or internet sites about building
Opencv 4.1.2 with CUDA support for Python 3.6. Versions matter since I'm unsure
of important differences I'm sticking to very current releases. 

### Our RPC servers
### Turn on Shape Detection in Hubitat. Test

### Conversation Street
Here is the reason we need pulseaudio: Mycroft wants its. Alexa Wants it.
When you have pulseaudio it pretends to hide ALSA. You can use alsa apps like
aplay and arecord because pulseaudio "wraps" it. It does not wrap alsamixer
and all the setting you made in .asoundrc. I believe it ignores them but won't
know that until somebody tells that. You use pacmd and pactl to set things up. If
you have a monitor hooked up to the Pi then you can play with pauvcontrol but it's
lame. Pretty, but lame. So, scan the man pages for pacmd and pactl to get feel for
what is available. 

You are going to get some background noise with a microphone. Some mic's are
better than others and some are cheaper than others by orders of magnitude. I'm not
going to sing to Trumpy Bear and record my song. But a little mic, clipped to
his tie would be in character and doesn't cost that much. I also have a little usb dongle mic
and it does NOT work well with a Pi - it's fine on my big Linux x86_64 box but not the
Pi.  You are going to have to experiment with setting the gain of your mic for the distance
you expect people to interact from. You can spend a lot of money chasing perfection.

Headphones eliminate a lot of these issues but you don't want people to wear them 
just to talk with Trumpy. A USB headphone dongle is good for hooking up the mic but
don't try using the speaker jack on it and connecting to the bluetooth speaker. 
I had a lot some hum that way and I can hear hum and fans. I can hear fans and 
I don't like the hear them. Perhaps that's just me.

#### Setup Microphone

`pactl list short sinks` will list your output devices - you want the index number
of the one you want to use. Likewise `pactl list short sources` will list the 
mic's available. Don't pick one that says 'monitor' unless you really know all this
stuff and can pretend you didn't hear my warning. You can alway fart around with those
later when you have nothing better to do. 

Lets record something and play it back.
```sh
arecord foo.wav
```
Speak normally for a few seconds and then ^C to quit. Yes, there are command line switches
but why bother? Now play it back with `aplay foo.wav`. If you are extremely lucky the volume
be good enough. Odds are you are going to need to adjust the gain
```sh
pactl set-source-volume 1 120%
```
Obviously 120% is the number for my mic. Yours will be different. Don't adjust the speaker (sink)
volume to make it better. Yours might need 80% or 250%.  Repeat until it seems OK to your.
Now uncomment and edit that line in ~/.trumpybear/trumpybear.sh. It's a good time to
reboot to redo the record/play one more time to make sure the setting sticks.

#### Mycroft or Alexa
I'd prefer to use Alexa but if you've ever built it as part of their developer
program you'd know how hard it is to build and work with and how it's not really setup
to be used for casual things. You have to learn a whole lot of stuff In C++. That is
more work than I want. If I have to, maybe someday or maybe never again. I haven't tried 
the google kit but from what I've seen it's not going to be much fun either.

[Mycroft](https://mycroft.ai/) has the advantage of being Free and Open Source
and mostly uses Python and it has a Community you can hang around it a learn from.
Of course there are tradeoff with maturity and completeness. I think for 
talking Teddy Bear it may be good enough.
