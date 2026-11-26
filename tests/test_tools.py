import json
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parents[1] / "tools"))
from grub_cfg import patch  # noqa: E402
from site_cfg import site_cfg  # noqa: E402
from ventoy_json import set_default  # noqa: E402

ROOT = Path(__file__).parents[1]


def test_open_wifi():
    out = site_cfg("home")
    assert "wireless_essid string home" in out and "select wep/open" in out and "wpa" not in out


def test_wpa_wifi():
    out = site_cfg("home", "secret123")
    assert "select wpa" in out and "wireless_wpa string secret123" in out


@pytest.mark.parametrize("ssid,psk", [("a\nd-i x", ""), ("home", "short")])
def test_bad_wifi_rejected(ssid, psk):
    with pytest.raises(ValueError):
        site_cfg(ssid, psk)


def test_grub_auto_entry_is_first_and_default():
    cfg = "set theme=x\nmenuentry 'Graphical install' {\n}\nmenuentry 'Install' {\n}\n"
    out = patch(cfg, "auto=true file=/cdrom/tablet/preseed.cfg")
    assert out.index("Tablet auto-install") < out.index("Graphical install")
    assert "set default=0" in out and "set timeout=5" in out
    assert "file=/cdrom/tablet/preseed.cfg --- quiet fbcon=rotate:1" in out


def test_ventoy_default_keeps_other_settings():
    cfg = {"persistence": [{"image": "/kali.iso"}], "control": [{"VTOY_MENU_TIMEOUT": "30"}, {"VTOY_X": "1"}]}
    out = set_default(cfg, "/tablet-installer.iso")
    assert out["persistence"] == [{"image": "/kali.iso"}]
    assert {"VTOY_X": "1"} in out["control"]
    assert {"VTOY_DEFAULT_IMAGE": "/tablet-installer.iso"} in out["control"]
    assert [c for c in out["control"] if "VTOY_MENU_TIMEOUT" in c] == [{"VTOY_MENU_TIMEOUT": "5"}]


def test_preseed_references_existing_files():
    pre = (ROOT / "tablet/preseed.cfg").read_text()
    for line in pre.splitlines():
        if "/cdrom/tablet/" in line and not line.startswith("#"):
            name = line.split("/cdrom/tablet/")[1].split()[0]
            assert (ROOT / "tablet" / name).exists(), name
    assert "partman/early_command" in pre and "late_command" in pre


def test_late_sh_installs_what_firstboot_needs():
    late = (ROOT / "tablet/late.sh").read_text()
    for f in ["firstboot.sh", "tablet-firstboot.service", "roles/", "authorized_keys", "hosts.map"]:
        assert f in late, f


def test_shell_scripts_parse():
    for f in list((ROOT / "tablet").rglob("*.sh")) + [ROOT / "build.sh", ROOT / "tests/qemu-install.sh"]:
        shell = "bash" if f.read_text().startswith("#!/usr/bin/env bash") else "sh"
        subprocess.run([shell, "-n", str(f)], check=True)


def test_build_without_test_flag_gets_past_the_output_name(tmp_path):
    """Regression: `OUT=...$([ $TEST = 1 ] && ...)` aborted under set -e when not testing."""
    script = (ROOT / "build.sh").read_text()
    line = next(l for l in script.splitlines() if l.startswith("[ $TEST = 1 ] && OUT="))
    r = subprocess.run(["bash", "-c", f"set -euo pipefail; TEST=0; OUT=out/tablet-installer.iso\n{line}\necho $OUT"],
                       capture_output=True, text=True)
    assert r.stdout.strip() == "out/tablet-installer.iso"


def test_ventoy_menu_alias_added_once():
    cfg = {"menu_alias": [{"image": "/win11.vhd", "alias": "Windows"}]}
    out = set_default(set_default(cfg, "/tablet-installer.iso"), "/tablet-installer.iso")
    assert out["menu_alias"][0] == {"image": "/win11.vhd", "alias": "Windows"}
    assert [a["image"] for a in out["menu_alias"]].count("/tablet-installer.iso") == 1
