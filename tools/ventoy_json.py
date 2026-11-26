"""Make an image Ventoy's default entry with a short timeout, keeping the rest of ventoy.json.
   ventoy_json.py <stick>/ventoy/ventoy.json </image.iso> [timeout s]"""
import json
import os
import sys


def set_default(cfg, image, timeout=5):
    control = [c for c in cfg.get("control", []) if not ({"VTOY_DEFAULT_IMAGE", "VTOY_MENU_TIMEOUT"} & c.keys())]
    control += [{"VTOY_DEFAULT_IMAGE": image}, {"VTOY_MENU_TIMEOUT": str(timeout)}]
    cfg["control"] = control
    return cfg


if __name__ == "__main__":
    path, image = sys.argv[1], sys.argv[2]
    cfg = json.load(open(path)) if os.path.exists(path) else {}
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(set_default(cfg, image, int(sys.argv[3]) if len(sys.argv) > 3 else 5), f, indent=4)
