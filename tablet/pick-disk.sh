#!/bin/sh
# partman/early_command: choose the eMMC, or stop the install when this isn't a tablet.
# A failing preseeded command makes the installer stop with an error dialog, so nothing gets erased.
. /cdrom/tablet/lib.sh
disk=$(pick_disk $(list-devices disk))
if [ -z "$disk" ]; then
    logger -t tablet "Not a VisionBook with an eMMC: refusing to erase anything."
    echo "TABLET INSTALLER: this is not a VisionBook tablet, nothing was erased." > /dev/console
    exit 1
fi
logger -t tablet "Installing to $disk"
debconf-set partman-auto/disk "$disk"
debconf-set grub-installer/bootdev "$disk"
