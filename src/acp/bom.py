"""工程量清单（BOM）推导：由选型结果换算整柜配置。"""


def build_bom(scn, sku, servers):
    """返回 {lines:[...], total}。infra 按服务器规模配比（经验规则，可复核）。"""
    lines = []
    lines.append(("计算节点", sku.sku, servers, sku.price_ref,
                  servers * sku.price_ref, "%s / %s，%d 卡/台" % (sku.cpu_arch, sku.accel, sku.cards)))
    sw = max(1, servers // 4)
    lines.append(("交换机", "SW-100G", sw, 80000, sw * 80000, "100G 接入/汇聚"))
    racks = max(1, servers // 8 + 1)
    lines.append(("机柜", "RACK-42U", racks, 30000, racks * 30000, "42U 标准机柜"))
    lines.append(("PDU", "PDU-DUAL", racks * 2, 5000, racks * 2 * 5000, "双路供电"))
    if scn.cooling in ("cold-plate", "immersion"):
        cdu = max(1, servers // 4)
        lines.append(("液冷分配单元", "CDU-LIQUID", cdu, 150000, cdu * 150000, "冷板/浸没液冷"))
    nas = max(1, servers // 8 + 1)
    lines.append(("存储", "NAS-STORAGE", nas, 300000, nas * 300000, "模型/数据集仓库"))
    out = [{"group": g, "sku": s, "qty": q, "unit": u, "subtotal": st, "note": n}
           for (g, s, q, u, st, n) in lines]
    return {"lines": out, "total": round(sum(l[4] for l in lines), 0)}


def power_items(bom, skus_by_sku, scn):
    """由 BOM 反推功耗清单，供 TCO 使用。"""
    items = []
    for l in bom["lines"]:
        sku = skus_by_sku.get(l["sku"])
        if sku and sku.tdp_w > 0:
            items.append({"power_w": sku.tdp_w, "qty": l["qty"]})
    return items
