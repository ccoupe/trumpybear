# Trumpy Bear
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
4. [USB headphone dongle]()
5. [Lapel (clip on) Microphone](https://www.amazon.com/gp/product/B075VQ7VG7?ref=ppx_pt2_dt_b_prod_image) - attaches to headphone dongle
6. [Bluetooth speaker](https://www.amazon.com/gp/product/B010OYASRG?ref=ppx_pt2_dt_b_prod_image) (the raspberry speaker jack is crap). Pick one
that is USB powered and doesn't disconnect if there is no activity.
7. [Nvidia Jetson Nano]()
8. Mqtt broker (could be the jetson or the pi3 but extra Pi won't hurt).
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
those cards then odds are your running Windows and Games -- I use is linux and can't help you.
Could you use a Coral accelerator on the pi3 or a pi4 instead and run everything on one
box? Probably. Try it and let me know. Most of those options are more expensive. 

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

## 
