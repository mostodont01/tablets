# tablets

Unattended Debian 13 installer for the old **Umax VisionBook 9Wi Pro** tablets (Atom x5-Z8350, 2 GB RAM, 32 GB eMMC,
32-bit UEFI, Realtek rtl8723bs SDIO Wi-Fi). Boot it from the Ventoy stick and walk away: it erases the eMMC, installs
Debian, sets the tablet up like `tab01` and reboots into the finished system, then the first boot installs the
tablet's roles (e.g. the HexCAD build store).

## What a tablet gets

- Debian 13 (console only), `en_US.UTF-8`, Czech keyboard, `Europe/Prague`, NTP
- Partitions like tab01 (own recipe): 1 GB EFI system partition, ext4 root, 1.5 GB swap; GRUB for 32-bit UEFI, also installed
  as `EFI/BOOT/BOOTIA32.EFI`
- Console turned for the portrait panel (`fbcon=rotate:1`), auto-login of `otos` on tty1
- User `otos` (uid 1000) with a locked password: SSH key only (no passwords, no root login), `sudo` without a password
- Wi-Fi from `site.conf`, Realtek/Intel firmware, `sudo curl git htop wireless-tools`
- Hostname + roles from `hosts.map` by the Wi-Fi MAC (unknown tablets: `tab-<last 4 hex of the MAC>`)
- Roles (`tablet/roles/<role>.sh`) run once on the first boot with network (`tablet-firstboot.service`, retried every
  minute until they succeed):
  - `hexcad`: HexCAD build store, `hexcad serve` on port 8770 as the systemd service `hexcad-serve`

## Safety

The installer only erases a disk when the machine is a **VisionBook** (DMI product name) and the disk is an **eMMC**
(`mmcblkN` with a `bootN` hardware partition). Anywhere else, `tablet/pick-disk.sh` stops it before partitioning with
an error, so booting the stick on another computer erases nothing. (The QEMU test ISO lifts this with `tablet.force=1`.)

## Build

```sh
cp site.conf.example site.conf      # Wi-Fi name / password, SSH key   (not committed)
cp hosts.map.example hosts.map      # MAC -> hostname + roles          (not committed)
./build.sh                          # -> out/tablet-installer.iso
./build.sh --ventoy /media/$USER/Ventoy   # also copy it to the stick and make it Ventoy's default entry (5 s)
```

`build.sh` remasters the stock netinst ISO (`~/Downloads/tablet-boot/debian-13.8.0-amd64-netinst.iso` by default):
it adds `/tablet` (preseed + scripts) and puts a **Tablet auto-install** entry on top of the ISO's GRUB menu with a 5 s
timeout. The stock entries stay below it.

With `--ventoy` the stick boots the tablet installer by itself after 5 s, so nothing has to be pressed on the tablet.
On other computers press a key in Ventoy's menu to pick something else (and the guard above stops the installer
anyway).

Find a tablet's Wi-Fi MAC: `cat /sys/class/net/wlan0/address` (or the installer's log).

## Tests

```sh
uv run --with pytest pytest -q tests      # unit tests: disk guard, hostname map, GRUB/Ventoy/Wi-Fi config (CI)
tests/qemu-install.sh ~/.cache/tablets-qemu   # end to end: unattended install in QEMU (UEFI, virtio disk),
                                              # then boots it and checks SSH, sudo, hostname and the hexcad role
```

The QEMU test needs KVM, `52:54:00:12:34:56 tabtest hexcad` in `hosts.map`, and takes ~15-25 min (downloads packages). Last run: PASS, 2026-11-26.
It runs the 64-bit UEFI path; the tablets' 32-bit UEFI was only tested by hand with the stock installer.

## Add a role

Write `tablet/roles/<name>.sh` (runs as root on the first boot, network up; exit non-zero to be retried), add the
name after the tablet's hostname in `hosts.map`, rebuild. On an installed tablet: add it to `/etc/tablet-roles` and
`sudo systemctl start tablet-firstboot` (after removing `/var/lib/tablet/done/all`).
