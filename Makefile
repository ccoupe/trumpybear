#
# Makefile for trumpybear
#
PRJ ?= trumpybear
DESTDIR ?= /usr/local/lib/${PRJ}
SRCDIR ?= $(HOME)/Projects/iot/${PRJ}
LAUNCH ?= ${PRJ}.sh
SERVICE ?= $(PRJ).service
PYENV ?= ${DESTDIR}/tb-env

NODE := $(shell hostname)
SHELL := /bin/bash 

${PYENV}:
	sudo mkdir -p ${PYENV}
	sudo chown ${USER} ${PYENV}
	python3 -m venv ${PYENV}
	( \
	set -e ;\
	source ${PYENV}/bin/activate; \
	pip install -r $(SRCDIR)/requirements.txt; \
	)

setup_launch:
	systemctl --user daemon-reload
	systemctl --user enable ${SERVICE}
	systemctl --user restart ${SERVICE}
	
setup_dir:
	sudo mkdir -p ${DESTDIR}
	sudo mkdir -p ${DESTDIR}/lib	
	sudo cp ${SRCDIR}/Makefile ${DESTDIR}
	sudo cp ${SRCDIR}/${NODE}.json ${DESTDIR}
	sudo cp ${SRCDIR}/requirements.txt ${DESTDIR}
	sudo cp ${SRCDIR}/${SERVICE} ${DESTDIR}
	sudo chown -R ${USER} ${DESTDIR}
	sed  s!PYENV!${PYENV}! <${SRCDIR}/launch.sh >$(DESTDIR)/$(LAUNCH)
	sudo chmod +x ${DESTDIR}/${LAUNCH}
	sudo cp ${DESTDIR}/${SERVICE} /etc/xdg/systemd/user
	
update: 
	sudo cp ${SRCDIR}/lib/Constants.py ${DESTDIR}/lib
	sudo cp ${SRCDIR}/lib/Homie_MQTT.py ${DESTDIR}/lib
	sudo cp ${SRCDIR}/lib/Settings.py ${DESTDIR}/lib
	sudo cp ${SRCDIR}/lib/Audio.py ${DESTDIR}/lib
	sudo cp ${SRCDIR}/lib/Constants.py ${DESTDIR}/lib
	sudo cp ${SRCDIR}/lib/TrumpyBear.py ${DESTDIR}/lib
	sudo cp -a ${SRCDIR}/lib/ImageZMQ ${DESTDIR}/lib
	sudo cp ${SRCDIR}/trumpy.py ${DESTDIR}
	sudo cp ${SRCDIR}/${NODE}.json ${DESTDIR}
	sudo chown -R ${USER} ${DESTDIR}

install: ${PYENV} setup_dir update setup_launch

clean: 
	sudo systemctl --user stop ${SERVICE}
	sudo systemctl --user disable ${SERVICE}
	sudo rm -f /etc/xdg/systemd/user/${SERVICE}
	sudo rm -rf ${DESTDIR}

realclean: clean
	rm -rf ${PYENV}
