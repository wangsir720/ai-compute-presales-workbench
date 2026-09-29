"""Redfish 风格离线预检。

说明：本模块**不建立任何网络连接**，仅对"符合 Redfish 响应结构"的 JSON 清单做字段与阈值校验，
用于售前阶段核对设备带外管理信息是否齐全。生产环境对接真实设备请用 DMTF 官方库
（如 python-redfish-library / Redfishtool）替换本预检的数据来源。
"""


class RedfishIssue:
    def __init__(self, node_id, field, level, message):
        self.node_id = node_id
        self.field = field
        self.level = level          # "error" / "warn"
        self.message = message

    def as_dict(self):
        return {"node": self.node_id, "field": self.field,
                "level": self.level, "message": self.message}


def _check_node(node, expected_accel_count):
    issues = []
    nid = node.get("id", "unknown")
    for req in ("id", "name", "type", "power_w", "status"):
        if req not in node:
            issues.append(RedfishIssue(nid, req, "error", "缺失必填字段 %s" % req))
    if "status" not in node or node.get("status") not in ("OK", "Enabled"):
        issues.append(RedfishIssue(nid, "status", "error", "设备状态异常或缺失：%s" % node.get("status")))
    if "power_w" in node and not (300 <= node["power_w"] <= 20000):
        issues.append(RedfishIssue(nid, "power_w", "warn",
                                   "功耗 %s W 超出常见区间(300–20000)，请核实" % node["power_w"]))
    procs = node.get("processors") or []
    if expected_accel_count and procs:
        total = sum(p.get("count", 0) for p in procs)
        if total != expected_accel_count:
            issues.append(RedfishIssue(nid, "processors", "warn",
                                       "加速卡数量 %d 与预期 %d 不一致" % (total, expected_accel_count)))
    if "memory_mb" in node and node["memory_mb"] < 131072:
        issues.append(RedfishIssue(nid, "memory_mb", "warn",
                                   "内存 %d MB 偏低，大模型推理可能不足" % node["memory_mb"]))
    return issues


def redfish_precheck(inventory, expected_accel_count=0):
    """inventory: list[dict]，字段参照 Redfish ComputerSystem/Processors/Memory。"""
    all_issues = []
    for node in inventory:
        all_issues.extend(_check_node(node, expected_accel_count))
    errors = [i for i in all_issues if i.level == "error"]
    warns = [i for i in all_issues if i.level == "warn"]
    return {
        "nodes": len(inventory),
        "errors": len(errors),
        "warns": len(warns),
        "issues": [i.as_dict() for i in all_issues],
        "ok": len(errors) == 0,
    }


def render_markdown(rep, title="Redfish 风格设备预检"):
    lines = ["# %s" % title, "",
             "- 节点数：%d" % rep["nodes"],
             "- 阻断项(error)：%d" % rep["errors"],
             "- 提醒项(warn)：%d" % rep["warns"],
             "- 结论：%s" % ("通过（无阻断项）" if rep["ok"] else "存在阻断项，需修正后入库"),
             "", "## 明细", "", "| 节点 | 字段 | 级别 | 说明 |",
             "|---|---|---|---|"]
    for i in rep["issues"]:
        lines.append("| %s | %s | %s | %s |" % (i["node"], i["field"], i["level"], i["message"]))
    return "\n".join(lines) + "\n"
