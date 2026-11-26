"""Add the tablet auto-install entry (default, 5 s timeout) above the stock Debian ISO menu.
   grub_cfg.py "<installer args>" < grub.cfg > new grub.cfg"""
import sys

ENTRY = """set default=0
set timeout=5
menuentry 'Tablet auto-install (ERASES the eMMC)' {{
    set background_color=black
    linux    /install.amd/vmlinuz {args} --- quiet fbcon=rotate:1
    initrd   /install.amd/initrd.gz
}}
"""


def patch(cfg, args):
    i = cfg.find("\nmenuentry")
    if i < 0:
        raise ValueError("no menuentry in grub.cfg")
    return cfg[: i + 1] + ENTRY.format(args=args) + cfg[i + 1:]


if __name__ == "__main__":
    sys.stdout.write(patch(sys.stdin.read(), sys.argv[1]))
