import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(HERE, "src"))

from acp.cli import cmd_generate, _paths  # noqa: E402
from acp.models import load_scenario  # noqa: E402

SCENARIOS_DIR = os.path.join(HERE, "config", "scenarios")


def main():
    for fn in sorted(os.listdir(SCENARIOS_DIR)):
        if not fn.endswith(".yaml"):
            continue
        path = os.path.join(SCENARIOS_DIR, fn)
        scn = load_scenario(path)
        print("\n=== 生成场景：%s ===" % scn.name)
        cmd_generate(type("A", (), {"scenario": path, "sku": None, "servers": 0, "out": None}))


if __name__ == "__main__":
    main()
