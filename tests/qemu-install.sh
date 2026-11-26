#!/usr/bin/env bash
# End-to-end test: install out/tablet-installer-test.iso in QEMU (UEFI, SD card = mmcblk like the eMMC) with no input,
# boot the result and check it over SSH (hostname from hosts.map, key login, sudo, first-boot roles).
# Needs KVM, the laptop's SSH key in site.conf, and 52:54:00:12:34:56 -> tabtest hexcad in hosts.map.
#   tests/qemu-install.sh [workdir]
set -euo pipefail
cd "$(dirname "$0")/.."
W=${1:-$(mktemp -d)}; mkdir -p "$W"
ISO=out/tablet-installer-test.iso
[ -f "$ISO" ] || ./build.sh --test
cp /usr/share/OVMF/OVMF_VARS_4M.fd "$W/vars.fd"
rm -f "$W/disk.img"; truncate -s 8G "$W/disk.img"
Q=(qemu-system-x86_64 -enable-kvm -m 2048 -smp 2 -machine q35
   -drive if=pflash,format=raw,readonly=on,file=/usr/share/OVMF/OVMF_CODE_4M.fd
   -drive if=pflash,format=raw,file="$W/vars.fd"
   -device sdhci-pci -drive if=none,id=sd,format=raw,file="$W/disk.img" -device sd-card,drive=sd
   -netdev user,id=n0,hostfwd=tcp:127.0.0.1:2222-:22 -device virtio-net-pci,netdev=n0,mac=52:54:00:12:34:56
   -display none -monitor unix:"$W/mon.sock",server,nowait)

echo "== install (unattended; QEMU exits when the installer reboots)"
progress set tabinst - "tablet install in QEMU" 2>/dev/null || true
timeout 3600 "${Q[@]}" -cdrom "$ISO" -no-reboot
echo "== first boot"
"${Q[@]}" &
QPID=$!
trap 'kill $QPID 2>/dev/null || true' EXIT
SSH=(ssh -p 2222 -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o ConnectTimeout=5 -o LogLevel=ERROR otos@127.0.0.1)
for _ in $(seq 60); do "${SSH[@]}" true 2>/dev/null && break; sleep 5; done
"${SSH[@]}" 'set -e
  echo "hostname: $(hostname)"; test "$(hostname)" = tabtest
  sudo -n true && echo "sudo: ok"
  test "$(cat /etc/tablet-roles)" = hexcad && echo "roles: hexcad"
  grep -q "^PasswordAuthentication no" /etc/ssh/sshd_config.d/10-keyonly.conf && echo "ssh: key only"
  grep -q "fbcon=rotate:1" /proc/cmdline && echo "cmdline: fbcon=rotate:1"
  test -e /etc/systemd/system/getty@tty1.service.d/autologin.conf && echo "autologin: ok"
  timedatectl show -p Timezone --value
  echo "waiting for the first-boot roles ..."
  for i in $(seq 120); do test -e /var/lib/tablet/done/all && break; sleep 10; done
  systemctl status tablet-firstboot --no-pager | head -3
  test -e /var/lib/tablet/done/all
  curl -fsS http://127.0.0.1:8770/keys && echo && echo "hexcad serve: ok"'
progress done tabinst 2>/dev/null || true
echo "== PASS"
"${SSH[@]}" 'sudo -n poweroff' || true
