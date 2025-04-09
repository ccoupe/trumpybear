#!/usr/bin/env bash
source PYENV/bin/activate
nm-online
cd /usr/local/lib/trumpybear/
node=`hostname`
python3 trumpy.py -s -c ${node}.json
