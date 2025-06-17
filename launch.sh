#!/usr/bin/env bash
source PYENV/bin/activate
nm-online
cd /usr/local/lib/trumpybear/
node=`hostname`
uv run trumpy.py -s -c ${node}.json
