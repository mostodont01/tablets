#!/bin/sh
# Role: Tailscale. Installs it (official script) and joins the tailnet as this tablet's hostname.
# Joining without anyone clicking needs an auth key: TS_AUTHKEY in site.conf (build.sh puts it in
# /usr/local/lib/tablet/files/ts-authkey). Without one it is installed but not joined: run `sudo tailscale up` once.
# Runs before the other roles that use `tailscale serve` (list it first in hosts.map).
set -e
command -v tailscale >/dev/null || curl -fsSL https://tailscale.com/install.sh | sh
systemctl enable --now tailscaled
KEY=/usr/local/lib/tablet/files/ts-authkey
if tailscale status >/dev/null 2>&1; then
    echo "tailscale: already joined"
elif [ -s "$KEY" ]; then
    tailscale up --authkey "file:$KEY" --hostname "$(hostname)"
    rm -f "$KEY"                       # one use is enough; don't leave the key on the disk
else
    echo "tailscale: installed, not joined (no TS_AUTHKEY in site.conf): run 'sudo tailscale up' once"
fi
