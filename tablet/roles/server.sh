#!/bin/sh
# Role: always-on server tablet.
#  - never sleeps or powers off by itself (lid, buttons, idle)
#  - Wi-Fi power saving off
#  - screen off (tablet-screen): type the PIN (default 123) to turn it on, off again after 5 min without keys
set -e
F=/usr/local/lib/tablet/files

# 1. Never sleep / power off
install -D -m 644 $F/logind-server.conf /etc/systemd/logind.conf.d/50-server.conf
systemctl mask sleep.target suspend.target hibernate.target hybrid-sleep.target suspend-then-hibernate.target
systemctl kill -s HUP systemd-logind          # reload logind's settings

# 2. Wi-Fi power saving off
install -m 644 $F/wifi-powersave-off.service /etc/systemd/system/

# 3. Screen off + PIN
install -m 755 $F/tablet-screen.py /usr/local/lib/tablet/tablet-screen.py
install -m 755 $F/tabscreen /usr/local/bin/tabscreen
[ -e /etc/tablet-screen.conf ] || install -m 644 $F/tablet-screen.conf /etc/tablet-screen.conf
install -m 644 $F/tablet-screen.service /etc/systemd/system/

systemctl daemon-reload
systemctl enable --now wifi-powersave-off.service tablet-screen.service
