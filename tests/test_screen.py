"""tablet-screen: PIN wakes the screen, it goes off after TIMEOUT without keys."""
import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location("tablet_screen", Path(__file__).parents[1] / "tablet/files/tablet-screen.py")
ts = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ts)

K1, K2, K3, KP1, KP2, KP3, KEY_A = 2, 3, 4, 79, 80, 81, 30


class FakeScreen:
    def __init__(self):
        self.history = []

    def set(self, on):
        self.history.append(on)


class Clock:
    t = 0.0

    def __call__(self):
        return self.t


def daemon(tmp_path):
    clock, screen = Clock(), FakeScreen()
    (tmp_path / "run").mkdir()
    return ts.Daemon("123", 300, screen, root=str(tmp_path), clock=clock), screen, clock


def test_starts_off(tmp_path):
    d, screen, _ = daemon(tmp_path)
    assert d.on is False and screen.history == [False]
    assert (tmp_path / "run/tablet-screen.state").read_text() == "off\n"


def test_pin_turns_it_on(tmp_path):
    d, screen, _ = daemon(tmp_path)
    for k in (K1, K2, K3):
        d.key(k)
    assert d.on is True and screen.history[-1] is True


def test_keypad_digits_work_too(tmp_path):
    d, _, _ = daemon(tmp_path)
    for k in (KP1, KP2, KP3):
        d.key(k)
    assert d.on


def test_wrong_keys_dont_wake_it(tmp_path):
    d, _, _ = daemon(tmp_path)
    for k in (K1, K2, KEY_A, K3, K3, K2, K1):
        d.key(k)
    assert not d.on


def test_pin_after_wrong_keys_still_works(tmp_path):
    d, _, _ = daemon(tmp_path)
    for k in (KEY_A, K2, K1, K1, K2, K3):
        d.key(k)
    assert d.on


def test_goes_off_after_timeout_without_keys(tmp_path):
    d, _, clock = daemon(tmp_path)
    for k in (K1, K2, K3):
        d.key(k)
    clock.t = 299
    d.tick()
    assert d.on
    clock.t = 300
    d.tick()
    assert not d.on


def test_typing_keeps_it_on(tmp_path):
    d, _, clock = daemon(tmp_path)
    for k in (K1, K2, K3):
        d.key(k)
    clock.t = 250
    d.key(KEY_A)
    clock.t = 500
    d.tick()
    assert d.on
    clock.t = 550
    d.tick()
    assert not d.on


def test_screen_writes_backlight_and_framebuffer(tmp_path):
    bl = tmp_path / "sys/class/backlight/intel_backlight"
    fb = tmp_path / "sys/class/graphics/fb0"
    bl.mkdir(parents=True)
    fb.mkdir(parents=True)
    (bl / "bl_power").write_text("0")
    (fb / "blank").write_text("0")
    s = ts.Screen(root=str(tmp_path))
    s.set(False)
    assert (bl / "bl_power").read_text() == "4" and (fb / "blank").read_text() == "4"
    s.set(True)
    assert (bl / "bl_power").read_text() == "0" and (fb / "blank").read_text() == "0"


def test_only_devices_with_number_keys_count_as_keyboards(tmp_path):
    def dev(name, keys):
        d = tmp_path / name / "device/capabilities"
        d.mkdir(parents=True)
        (d / "key").write_text(keys + "\n")
        return str(tmp_path / name)
    assert ts.is_keyboard(dev("kbd", "1000000000007 ff9f207ac14057ff febeffdfffefffff fffffffffffffffe"))
    assert not ts.is_keyboard(dev("power", "10000000000000 0"))       # power button: KEY_POWER only
    assert not ts.is_keyboard(dev("lid", "0"))


def test_conf_defaults_and_override(tmp_path):
    assert ts.read_conf(str(tmp_path / "missing")) == ("123", 300)
    (tmp_path / "c").write_text("# comment\nPIN=4711\nTIMEOUT=60\n")
    assert ts.read_conf(str(tmp_path / "c")) == ("4711", 60)
