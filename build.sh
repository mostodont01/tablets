#!/usr/bin/env bash
# Build the unattended tablet installer ISO from the stock Debian netinst ISO.
#   ./build.sh [--test] [--ventoy <stick mount>] [debian-netinst.iso]
# Reads site.conf (Wi-Fi, SSH key, hosts map; see site.conf.example). Output: out/tablet-installer.iso.
#   --test     the auto entry also runs off-tablet (tablet.force=1), for QEMU; output out/tablet-installer-test.iso
#   --ventoy   copy the ISO to the stick and make it Ventoy's default entry (boots by itself after a few seconds)
set -euo pipefail
cd "$(dirname "$0")"
TEST=0; VENTOY=
while [ $# -gt 0 ]; do
    case $1 in
        --test) TEST=1 ;;
        --ventoy) VENTOY=$2; shift ;;
        *) ISO=$1 ;;
    esac
    shift
done
ISO=${ISO:-$HOME/Downloads/tablet-boot/debian-13.8.0-amd64-netinst.iso}
[ -f site.conf ] || { echo "site.conf missing (copy site.conf.example)" >&2; exit 1; }
# shellcheck source=site.conf.example
. ./site.conf
OUT=out/tablet-installer.iso
[ $TEST = 1 ] && OUT=out/tablet-installer-test.iso
STAGE=$(mktemp -d); trap 'rm -rf "$STAGE"' EXIT
mkdir -p out "$STAGE/tablet/roles"

# Installer files under /tablet on the ISO
cp tablet/*.sh tablet/preseed.cfg tablet/tablet-firstboot.service "$STAGE/tablet/"
cp tablet/roles/*.sh "$STAGE/tablet/roles/"
cp -r tablet/files "$STAGE/tablet/files"
cp "${SSH_KEY/#\~/$HOME}" "$STAGE/tablet/authorized_keys"
cp "${HOSTS_MAP:-hosts.map}" "$STAGE/tablet/hosts.map"
python3 tools/site_cfg.py "$WIFI_SSID" "${WIFI_PSK:-}" > "$STAGE/tablet/site.cfg"

# Boot menu: auto entry first, 5 s timeout; the stock entries stay below it.
ARGS="auto=true priority=critical file=/cdrom/tablet/preseed.cfg locale=en_US.UTF-8 keymap=cz"
[ $TEST = 1 ] && ARGS="$ARGS tablet.force=1"
mkdir -p "$STAGE/boot/grub"
xorriso -osirrox on -indev "$ISO" -extract /boot/grub/grub.cfg "$STAGE/grub.orig" 2>/dev/null
chmod u+w "$STAGE/grub.orig"
python3 tools/grub_cfg.py "$ARGS" < "$STAGE/grub.orig" > "$STAGE/boot/grub/grub.cfg"

rm -f "$OUT"
xorriso -indev "$ISO" -outdev "$OUT" \
    -map "$STAGE/tablet" /tablet \
    -map "$STAGE/boot/grub/grub.cfg" /boot/grub/grub.cfg \
    -boot_image any replay 2>&1 | grep -iE "error|fail" || true
echo "built $OUT"

if [ -n "$VENTOY" ]; then
    cp "$OUT" "$VENTOY/"
    python3 tools/ventoy_json.py "$VENTOY/ventoy/ventoy.json" "/$(basename "$OUT")"
    sync
    echo "copied to $VENTOY and set as Ventoy's default entry"
fi
