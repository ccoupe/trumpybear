#!/bin/bash
#
# run by autostart when user 'pi' logs in via GUI - may not have a monitor
# but we might. We need pulseaudio and dbus, they need the gui running. 
#
cd $HOME/trumpybear
# configure pulseaudio streams. 
# 1. Stop alsa from interfering 
# 2. (re)connect to the bluetooth speaker
# 3. configure the microphone gain (source volume)
sudo killall bluealsa
echo -e "connect DE:B0:D2:C5:0B:7C" | bluetoothctl
# usb mic is source 0 - needs a lot of boost - it's noisy, low quality
# pactl set-source-volume 0 300%
# the usb headset dongle is source 1 (mono)  (if the usb mic is missing)
# and need a reduction in gain if worn on the head and increase
# for stand alone. 
pactl set-source-volume 1 120% 
# Start the tts program.
/usr/bin/python3 trumpy.py -s -c trumpy.json
