Trumpy Bear is complicated enough the I have two introductions
here and a blog post with pictures and a movie. 

If you want the pictures (they are big and load slowly) then
[here you go](https://walkabout.mvmanila.com/2020/10/20/orange-mad-bad/)

There is an older [Intro.md](Intro.md) written before I really got into it. Phase One, if you will.  

The [current version](TopLevel.md) is more detailed and is Christmas 2020 current.  

Quick install
Python 3.6
	python3 -m venv create ~/tb-env
        source ~/tb-env/bin/activate
        pip install -r requirements.txt

Need to install lighttpd and modify /etc/lighttpd/lighttpd.conf to use /var/www/camera and port 7543

sudo mkdir /var/www/camera
sudo chown <your-user-name> /var/www/camera
sudo systemctl restart lighttpd

sudo apt install portaudio19-dev
sudo apt install flac 

requirements.txt:
opencv-contrib-python
imutil
zmq
paho-mqtt
websocket-client
python-vlc
websockets
pulsectl
SpeechRecognition
pipewire_python
pyaudio
