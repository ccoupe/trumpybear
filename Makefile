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

${PYENV}: ${SRCDIR}/requirements.txt
	sudo mkdir -p ${DESTDIR}
	sudo chown ${USER} ${DESTDIR}
	sudo cp ${SRCDIR}/pyproject.toml ${DESTDIR}
	uv python pin 3.11.2
	uv venv --system-site-packages ${PYENV}
	source ${PYENV}/bin/activate
	uv python pin 3.11.2
	uv add -r $(SRCDIR)/requirements.txt

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
	sudo cp ${SRCDIR}/Constants.py ${DESTDIR}
	sudo cp ${SRCDIR}/Homie_MQTT.py ${DESTDIR}
	sudo cp ${SRCDIR}/Settings.py ${DESTDIR}
	sudo cp ${SRCDIR}/TrumpyBear.py ${DESTDIR}
	sudo cp -a ${SRCDIR}/ImageZMQ ${DESTDIR}
	sudo cp ${SRCDIR}/trumpy.py ${DESTDIR}
	sudo cp ${SRCDIR}/${NODE}.json ${DESTDIR}
	sudo chown -R ${USER} ${DESTDIR}

install: ${PYENV} setup_dir update setup_launch

lint:
	 flake8 --indent-size 2 --max-line-length 90 --ignore=W293,F824 \
--exclude .venv,${PYENV}

clean: 
	sudo systemctl --user stop ${SERVICE}
	sudo systemctl --user disable ${SERVICE}
	sudo rm -f /etc/xdg/systemd/user/${SERVICE}
	sudo rm -rf ${DESTDIR}

realclean: clean
	rm -rf ${PYENV}
