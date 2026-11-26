"""Print the site part of the preseed (Wi-Fi) from site.conf values:  site_cfg.py <ssid> [<wpa password>]"""
import sys


def site_cfg(ssid, psk=""):
    for v in (ssid, psk):
        if "\n" in v or "\r" in v:
            raise ValueError("Wi-Fi settings must be a single line")
    lines = [f"d-i netcfg/wireless_essid string {ssid}", f"d-i netcfg/wireless_essid_again string {ssid}"]
    if psk:
        if not 8 <= len(psk) <= 63:
            raise ValueError("a WPA password has 8-63 characters")
        lines += ["d-i netcfg/wireless_security_type select wpa", f"d-i netcfg/wireless_wpa string {psk}"]
    else:
        lines += ["d-i netcfg/wireless_security_type select wep/open"]
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    sys.stdout.write(site_cfg(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else ""))
