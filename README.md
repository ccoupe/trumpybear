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

The conversions are preloaded Mycroft Skills (or Alexa skills if I use Alexa)
plus any skills I write. 

In summary, Think of it as an echo dot activated by a motion sensor, 
protected by face recognition. In a Teddy bear.

## Bill of Materials
1. (https://gettrumpybear.com/)[Trumpy Bear (TM)]
2. Raspberry Pi3 (pi4 might be too hot, pi0 doesn't have needed punch)
3. Raspberry camera with day and night capabilities
4. USB headphone dongle
5. Lapel (clip on) Microphone - attaches to headphone dongle
6. Bluetooth speaker (the raspberry speaker jack is crap)
7. Nvidia Jetson Nano
8. Mqtt broker (could be the jetson or the pi3 but extra Pi won't hurt).
9. Cables, wires, Pi power supply and case... and stuff.
10. HDMI Monitor, keyboard, mouse to setup Pi and Jetson
11. Hubitat hub - leads to a deep money pit. Beware. Could be anything
that talks to MQTT but you'll be busy modifing code.

A note about using the Nvidia Jetson. This is not an absolute requirement
but it will be cheaper than the alternatives. Why? Neural nets are computation
hogs. A dedicated i5 won't have the oopmh. An i7 might but either one of those
is serious money with electrical power and space issues. You could put an expensive
NVidia graphics card in a machine and use that. If you already have one of
those cards then odds are your running Windows and Games -- I use is linux and can't help you.
Could you use a Coral accelerator on the pi3 or a pi4 instead and run everything on one
box? Probably. Try it and let me know. None of those options are cheap. 

Finally, the Jetson is 'damn cool' and you want a reason to get one. You're Welcome.

## Required Skills
1. Must have moderate skill in Linux admin. There's a lot to do and I won't
spell it out for a quick copy and paste.
2. Python programming if you want to modify anything. You probably will.
3. Groovy programming if you want to modify the Hubitat driver.
4. Hubitat admin (or you hub of choice)
5. Understanding of MQTT. Hint: it's not a database.
5. Patience and a sense of humor. 
6. Lots of time and a fair bit of money. You have to want this.

## Overview of Work.
1. Install Hubitat. 
2. Install Jetson Nano (opencv + cuda)
3. Install MQTT broker (another pi or use Jetson Nano)
4. Assemble pi3, camera, microphone.
5. Test, test, and more tests.
6. Install pi3 in Trumpy Bear
7. Tune system - this may never end if it's fun.
