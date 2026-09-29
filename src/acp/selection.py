"""双生态选型评分矩阵：x86(NVIDIA) vs 鲲鹏+昇腾。"""

from .capacity import plan_capacity


def selection_matrix(scn, skus):
    """对每条加速卡机型做评分，返回按分数降序的明细列表。"""
    rows = []
    for s in skus:
        if not s.is_accelerator():
            continue
        cap = plan_capacity(scn, s)
        if cap["raw_cards"] == 0:
            continue
        vram_fit = 1.0 if cap["bottleneck"] == "throughput" else min(1.0, s.cards / cap["raw_cards"])
        tput_fit = 1.0 if cap["bottleneck"] == "vram" else min(1.0, cap["raw_cards"] / (cap["cards_for_tput"] or 1))
        cost_per_card = s.price_ref / max(s.cards, 1)
        rows.append({
            "sku": s.sku,
            "arch": s.cpu_arch,
            "accel": s.accel,
            "localization": s.localization,
            "servers": cap["servers"],
            "actual_cards": cap["actual_cards"],
            "vram_fit": round(vram_fit, 3),
            "tput_fit": round(tput_fit, 3),
            "cost_per_card_w": round(cost_per_card / 1e4, 1),
            "_cost_per_card": cost_per_card,
            "bottleneck": cap["bottleneck"],
        })
    if not rows:
        return rows
    min_c = min(r["_cost_per_card"] for r in rows)
    max_c = max(r["_cost_per_card"] for r in rows)
    for r in rows:
        # 成本分：越便宜越高（最低价=1.0，最高价=0.0）
        if max_c == min_c:
            cost_score = 1.0
        else:
            cost_score = (max_c - r["_cost_per_card"]) / (max_c - min_c)
        score = round(0.30 * r["vram_fit"] + 0.25 * r["tput_fit"]
                      + 0.20 * r["localization"] + 0.25 * cost_score, 3)
        r["cost_score"] = round(cost_score, 3)
        r["score"] = score
    rows.sort(key=lambda r: r["score"], reverse=True)
    return rows


def recommend(scn, skus):
    """返回 (推荐机型, 明细列表)。"""
    matrix = selection_matrix(scn, skus)
    return (matrix[0] if matrix else None, matrix)
