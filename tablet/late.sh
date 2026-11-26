#!/bin/sh
# preseed/late_command: turn the fresh Debian into a tablet like tab01. Runs in the installer, system at /target.
set -e
T=/target
S=/cdrom/tablet
. $S/lib.sh

set -- $(pick_host $S/hosts.map)
name=$1; shift
roles="$*"
logger -t tablet "hostname $name, roles: ${roles:-none}"
echo "$name" > $T/etc/hostname
sed -i "s/^127\.0\.1\.1.*/127.0.1.1\t$name/" $T/etc/hosts
echo "$roles" > $T/etc/tablet-roles

# SSH: key only, no root login.
install -d -m 700 -o 1000 -g 1000 $T/home/otos/.ssh
install -m 600 -o 1000 -g 1000 $S/authorized_keys $T/home/otos/.ssh/authorized_keys
printf 'PasswordAuthentication no\nKbdInteractiveAuthentication no\nPermitRootLogin no\n' > $T/etc/ssh/sshd_config.d/10-keyonly.conf

# sudo without a password; the user's password is locked (console auto-login + SSH key are the ways in).
echo 'otos ALL=(ALL) NOPASSWD:ALL' > $T/etc/sudoers.d/otos
chmod 440 $T/etc/sudoers.d/otos
chroot $T usermod -p "!" otos

# Console auto-login on tty1.
mkdir -p $T/etc/systemd/system/getty@tty1.service.d
printf '[Service]\nExecStart=\nExecStart=-/sbin/agetty --autologin otos --noclear %%I $TERM\n' \
    > $T/etc/systemd/system/getty@tty1.service.d/autologin.conf

# First boot: run the roles (they need the network, which the installer's chroot doesn't have reliably).
install -d $T/usr/local/lib/tablet/roles
install -m 755 $S/roles/*.sh $T/usr/local/lib/tablet/roles/
cp -r $S/files $T/usr/local/lib/tablet/files          # config files and services the roles install
install -m 755 $S/firstboot.sh $T/usr/local/sbin/tablet-firstboot
install -m 644 $S/tablet-firstboot.service $T/etc/systemd/system/
in-target systemctl enable tablet-firstboot.service
