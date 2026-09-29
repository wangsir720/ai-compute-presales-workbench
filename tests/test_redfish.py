import json
import os

from acp import redfish

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEMO = os.path.join(HERE, "config", "redfish-demo.json")


def _inv():
    with open(DEMO, "r", encoding="utf-8") as f:
        return json.load(f)


def test_precheck_counts_issues():
    inv = _inv()
    rep = redfish.redfish_precheck(inv, expected_accel_count=8)
    assert rep["nodes"] == 5
    assert rep["errors"] == 1   # node-03 状态异常
    assert rep["warns"] == 1    # node-05 加速卡数量不符
    assert rep["ok"] is False


def test_precheck_clean_when_fixed():
    inv = _inv()
    inv[2]["status"] = "OK"          # 修 node-03
    inv[4]["processors"] = [{"model": "GPU-x", "count": 8}]  # 修 node-05
    rep = redfish.redfish_precheck(inv, expected_accel_count=8)
    assert rep["ok"] is True
    assert rep["errors"] == 0


def test_render_markdown_has_table():
    inv = _inv()
    rep = redfish.redfish_precheck(inv, expected_accel_count=8)
    md = redfish.render_markdown(rep)
    assert "# Redfish" in md
    assert "| 节点 | 字段 | 级别 | 说明 |" in md


def test_missing_field_is_error():
    inv = [{"id": "x", "name": "x", "type": "ComputerSystem", "status": "OK"}]  # 缺 power_w
    rep = redfish.redfish_precheck(inv)
    assert rep["errors"] >= 1
