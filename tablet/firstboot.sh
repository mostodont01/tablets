#!/bin/sh
# Runs once on the first boot (systemd tablet-firstboot.service) and applies the roles in /etc/tablet-roles.
# A failed role makes the service fail; systemd retries it, and finished roles are not run again.
set -e
DONE=/var/lib/tablet/done
mkdir -p $DONE
for role in $(cat /etc/tablet-roles 2>/dev/null); do
    [ -e "$DONE/$role" ] && continue
    script=/usr/local/lib/tablet/roles/$role.sh
    if [ ! -x "$script" ]; then echo "unknown role: $role" >&2; continue; fi
    echo "role $role ..."
    "$script"
    touch "$DONE/$role"
done
touch $DONE/all
