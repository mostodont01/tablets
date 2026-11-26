"""tablet/lib.sh (runs in the Debian installer's busybox sh) against a fake /sys + /dev tree."""
import subprocess
from pathlib import Path

LIB = Path(__file__).parents[1] / "tablet" / "lib.sh"


def sh(root, cmd):
    r = subprocess.run(["sh", "-c", f". {LIB}; {cmd}"], env={"SYSROOT": str(root), "PATH": "/usr/bin:/bin"},
                       capture_output=True, text=True)
    return r.returncode, r.stdout.strip()


def fake(tmp_path, product="VisionBook 9Wi Pro", emmc=True, macs=(("wlan0", "C0:21:0D:DC:D7:05"),), cmdline=""):
    (tmp_path / "sys/class/dmi/id").mkdir(parents=True)
    (tmp_path / "sys/class/dmi/id/product_name").write_text(product + "\n")
    (tmp_path / "dev").mkdir()
    if emmc:
        (tmp_path / "dev/mmcblk1boot0").touch()
    for name, mac in (("lo", "00:00:00:00:00:00"),) + tuple(macs):
        d = tmp_path / "sys/class/net" / name
        d.mkdir(parents=True)
        (d / "address").write_text(mac + "\n")
    (tmp_path / "proc").mkdir()
    (tmp_path / "proc/cmdline").write_text(cmdline + "\n")
    return tmp_path


def test_tablet_emmc_is_picked(tmp_path):
    assert sh(fake(tmp_path), "pick_disk /dev/sda /dev/mmcblk1") == (0, "/dev/mmcblk1")


def test_other_computer_is_refused(tmp_path):
    rc, out = sh(fake(tmp_path, product="HP Laptop 14s-dq1xxx"), "pick_disk /dev/nvme0n1 /dev/sda /dev/mmcblk1")
    assert rc != 0 and out == ""


def test_sd_card_without_boot_partition_is_refused(tmp_path):
    rc, out = sh(fake(tmp_path, emmc=False), "pick_disk /dev/sda /dev/mmcblk1")
    assert rc != 0 and out == ""


def test_force_flag_allows_any_disk_but_not_cdrom(tmp_path):
    root = fake(tmp_path, product="QEMU", emmc=False, cmdline="auto=true tablet.force=1 --- quiet")
    assert sh(root, "pick_disk /dev/sr0 /dev/mmcblk0") == (0, "/dev/mmcblk0")


def test_known_mac_gives_name_and_roles(tmp_path):
    root = fake(tmp_path)
    (tmp_path / "hosts.map").write_text("# comment\nC0:21:0D:DC:D7:05   tab01  hexcad drums\n")
    assert sh(root, f"pick_host {tmp_path}/hosts.map") == (0, "tab01 hexcad drums")


def test_unknown_mac_gets_generated_name(tmp_path):
    root = fake(tmp_path, macs=(("wlan0", "c0:21:0d:dc:ab:cd"),))
    (tmp_path / "hosts.map").write_text("c0:21:0d:dc:d7:05 tab01 hexcad\n")
    assert sh(root, f"pick_host {tmp_path}/hosts.map") == (0, "tab-abcd")


def test_commented_mac_is_ignored(tmp_path):
    root = fake(tmp_path)
    (tmp_path / "hosts.map").write_text("# c0:21:0d:dc:d7:05 tab01 hexcad\n")
    assert sh(root, f"pick_host {tmp_path}/hosts.map") == (0, "tab-d705")
