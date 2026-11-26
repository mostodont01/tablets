#!/usr/bin/env python3
"""tablet-screen: keep the tablet's screen off; typing the PIN turns it on, and it goes off again after a while
without key presses.

While the screen is off the keyboards are grabbed, so the typed keys (including the PIN) never reach the console.
Config: /etc/tablet-screen.conf  (PIN=123, TIMEOUT=300 seconds).  Runs as root (systemd tablet-screen.service).

  tabscreen on | off | status      control it from SSH (on = on for TIMEOUT seconds)
"""
import fcntl
import glob
import os
import select
import signal
import struct
import sys
import time

CONF = "/etc/tablet-screen.conf"
STATE = "/run/tablet-screen.state"
EVENT = struct.Struct("llHHi")          # struct input_event: timeval, type, code, value
EV_KEY = 1
EVIOCGRAB = 0x40044590
KEY_1 = 2
DIGITS = {2: "1", 3: "2", 4: "3", 5: "4", 6: "5", 7: "6", 8: "7", 9: "8", 10: "9", 11: "0",   # top row
          79: "1", 80: "2", 81: "3", 75: "4", 76: "5", 77: "6", 71: "7", 72: "8", 73: "9", 82: "0"}  # keypad


def read_conf(path=CONF):
    conf = {"PIN": "123", "TIMEOUT": "300"}
    try:
        for line in open(path):
            if "=" in line and not line.lstrip().startswith("#"):
                k, v = line.split("=", 1)
                conf[k.strip()] = v.strip().strip('"')
    except FileNotFoundError:
        pass
    return conf["PIN"], int(conf["TIMEOUT"])


class Typed:
    """Remembers the last keys; matches when they end with the PIN. Non-digit keys count as a wrong key."""

    def __init__(self, pin):
        self.pin, self.buf = pin, ""

    def key(self, code):
        self.buf = (self.buf + DIGITS.get(code, "?"))[-len(self.pin):]
        if self.buf == self.pin:
            self.buf = ""
            return True
        return False


class Screen:
    """Backlight (bl_power) + framebuffer blanking. `root` lets tests use a fake /sys."""

    def __init__(self, root=""):
        self.root = root

    def _write(self, pattern, value):
        for f in glob.glob(self.root + pattern):
            try:
                with open(f, "w") as fh:
                    fh.write(value)
            except OSError:
                pass

    def set(self, on):
        if on:
            self._write("/sys/class/graphics/fb0/blank", "0")
            self._write("/sys/class/backlight/*/bl_power", "0")
        else:
            self._write("/sys/class/backlight/*/bl_power", "4")
            self._write("/sys/class/graphics/fb0/blank", "4")


def is_keyboard(event_dir):
    """True for input devices that have number keys (real keyboards, not the power button or the lid)."""
    try:
        words = open(os.path.join(event_dir, "device/capabilities/key")).read().split()
    except OSError:
        return False
    return bool(words) and bool(int(words[-1], 16) & (1 << KEY_1))


class Daemon:
    def __init__(self, pin, timeout, screen, root="", clock=time.monotonic):
        self.typed, self.timeout, self.screen, self.root, self.clock = Typed(pin), timeout, screen, root, clock
        self.devs = {}              # path -> fd
        self.on_until = 0.0
        self.on = None
        self.turn(False)

    def turn(self, on):
        if on == self.on:
            return
        self.on = on
        self.screen.set(on)
        for fd in self.devs.values():
            self.grab(fd, not on)
        try:
            with open(self.root + STATE, "w") as f:
                f.write("on\n" if on else "off\n")
        except OSError:
            pass

    @staticmethod
    def grab(fd, yes):
        try:
            fcntl.ioctl(fd, EVIOCGRAB, 1 if yes else 0)
        except OSError:
            pass

    def wake(self):
        self.on_until = self.clock() + self.timeout
        self.turn(True)

    def key(self, code):
        """A key was pressed. Off: only the PIN counts. On: any key keeps it on for another TIMEOUT."""
        if self.on:
            self.on_until = self.clock() + self.timeout
        elif self.typed.key(code):
            self.wake()

    def tick(self):
        if self.on and self.clock() >= self.on_until:
            self.turn(False)

    def rescan(self):
        found = {"/dev/input/" + os.path.basename(d) for d in glob.glob(self.root + "/sys/class/input/event*")
                 if is_keyboard(d)}
        for path in list(self.devs):
            if path not in found:
                os.close(self.devs.pop(path))
        for path in found - self.devs.keys():
            try:
                fd = os.open(self.root + path, os.O_RDONLY | os.O_NONBLOCK)
            except OSError:
                continue
            self.devs[path] = fd
            if not self.on:
                self.grab(fd, True)

    def read(self, fd):
        try:
            data = os.read(fd, EVENT.size * 64)
        except BlockingIOError:
            return
        except OSError:                 # unplugged
            path = next(p for p, f in self.devs.items() if f == fd)
            os.close(self.devs.pop(path))
            return
        for i in range(0, len(data) - EVENT.size + 1, EVENT.size):
            _, _, etype, code, value = EVENT.unpack_from(data, i)
            if etype == EV_KEY and value == 1:
                self.key(code)

    def run(self):
        signal.signal(signal.SIGUSR1, lambda *_: self.wake())
        signal.signal(signal.SIGUSR2, lambda *_: self.turn(False))
        signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))
        last_scan = 0.0
        try:
            while True:
                if self.clock() - last_scan > 5:      # keyboard dock attached / detached
                    self.rescan()
                    last_scan = self.clock()
                try:
                    ready, _, _ = select.select(list(self.devs.values()), [], [], 1.0)
                except InterruptedError:
                    ready = []
                for fd in ready:
                    self.read(fd)
                self.tick()
        finally:
            self.turn(True)                 # never leave a dead tablet with a black screen and grabbed keys


if __name__ == "__main__":
    pin, timeout = read_conf()
    Daemon(pin, timeout, Screen()).run()
