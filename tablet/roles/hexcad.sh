#!/bin/sh
# Role: HexCAD build store (hexcad serve on port 8770, store in /home/otos/hexcad-store) as a systemd service.
set -e
curl -fsSL https://raw.githubusercontent.com/mostodont01/hexcad/main/server/setup.sh -o /tmp/hexcad-setup.sh
runuser -l otos -c 'bash /tmp/hexcad-setup.sh none'
cat > /etc/systemd/system/hexcad-serve.service <<'UNIT'
[Unit]
Description=HexCAD build store
Wants=network-online.target
After=network-online.target

[Service]
User=otos
ExecStart=/home/otos/.local/bin/hexcad serve --dir /home/otos/hexcad-store
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
UNIT
systemctl daemon-reload
systemctl enable --now hexcad-serve.service
for _ in $(seq 30); do curl -fsS http://127.0.0.1:8770/keys >/dev/null 2>&1 && exit 0; sleep 1; done
echo "hexcad serve did not come up" >&2
exit 1
