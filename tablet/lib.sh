# Shared helpers for the tablet installer (POSIX sh: runs in the Debian installer's busybox and in tests).
# SYSROOT lets tests point the /sys and /dev lookups at a fake tree.

SYSROOT=${SYSROOT:-}

# True when the kernel command line asks to skip the "is this a tablet?" guard (QEMU tests).
tablet_forced() {
    grep -qw 'tablet.force=1' "${SYSROOT}/proc/cmdline" 2>/dev/null
}

# Print the internal disk to install to, or nothing when this doesn't look like a tablet.
# A tablet = a VisionBook (DMI product name) with an eMMC (mmcblkN with a bootN hardware partition).
# Disks are given as arguments (the installer's `list-devices disk`).
pick_disk() {
    product=$(cat "${SYSROOT}/sys/class/dmi/id/product_name" 2>/dev/null)
    for d in "$@"; do
        case $d in
            /dev/mmcblk[0-9]|/dev/mmcblk[0-9][0-9])
                if [ -e "${SYSROOT}${d}boot0" ]; then
                    case $product in *VisionBook*) echo "$d"; return 0 ;; esac
                fi ;;
        esac
    done
    if tablet_forced; then
        for d in "$@"; do
            case $d in /dev/sr*|/dev/loop*) continue ;; esac
            echo "$d"; return 0
        done
    fi
    return 1
}

# Print "hostname roles..." for the first network interface whose MAC is in the hosts map.
# Map lines: <mac> <hostname> [role...]   (# comments allowed).
# Unknown tablets get "tab-<last 4 hex digits of the first MAC>" and no roles.
pick_host() {
    map=$1
    first=
    for f in "${SYSROOT}"/sys/class/net/*/address; do
        [ -r "$f" ] || continue
        case $f in */lo/address) continue ;; esac
        mac=$(tr 'A-F' 'a-f' < "$f")
        [ "$mac" = "00:00:00:00:00:00" ] && continue
        [ -n "$first" ] || first=$mac
        if [ -r "$map" ]; then
            line=$(grep -v '^[[:space:]]*#' "$map" | tr 'A-F' 'a-f' | awk -v m="$mac" '$1 == m { $1 = ""; sub(/^ /, ""); print; exit }')
            if [ -n "$line" ]; then echo "$line"; return 0; fi
        fi
    done
    [ -n "$first" ] || first=00:00
    echo "tab-$(echo "$first" | tr -d ':' | tail -c 5)"
}
