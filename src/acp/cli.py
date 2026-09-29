import argparse
import json
import os

from . import capacity, selection, tco, bom, diagram, redfish, reporting
from .models import load_products, load_scenario

HERE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _paths():
    return {
        "products": os.path.join(HERE, "data", "products.json"),
        "templates": os.path.join(HERE, "templates"),
    }


def _skus_by(d):
    return {s.sku: s for s in d}


def cmd_compute(args):
    products = load_products(_paths()["products"])
    scn = load_scenario(args.scenario)
    by = _skus_by(products)
    print("场景：%s（%s）" % (scn.name, scn.sid))
    print("精度=%s 并发=%d ctx=%d 冷却=%s" % (scn.precision, scn.concurrency, scn.ctx_len, scn.cooling))
    for s in products:
        if not s.is_accelerator():
            continue
        cap = capacity.plan_capacity(scn, s)
        print("  %-14s 瓶颈=%-10s 显存需求=%6.1fGB 卡数=%2d(显存)%2d(吞吐) → 服务器 %d 台"
              % (s.sku, cap["bottleneck"], cap["vram_need_gb"],
                 cap["cards_for_vram"], cap["cards_for_tput"], cap["servers"]))
    return scn


def cmd_selection(args):
    products = load_products(_paths()["products"])
    scn = load_scenario(args.scenario)
    matrix = selection.selection_matrix(scn, products)
    print("场景：%s 选型评分（降序）" % scn.name)
    for r in matrix:
        print("  %-14s 分=%.3f 服务器=%d 卡=%d 瓶颈=%s 国产=%.1f"
              % (r["sku"], r["score"], r["servers"], r["actual_cards"], r["bottleneck"], r["localization"]))
    return matrix


def cmd_tco(args):
    products = load_products(_paths()["products"])
    scn = load_scenario(args.scenario)
    by = _skus_by(products)
    sku = by[args.sku]
    servers = int(args.servers or capacity.plan_capacity(scn, sku)["servers"])
    b = bom.build_bom(scn, sku, servers)
    items = bom.power_items(b, by, scn)
    it_w = tco.it_power_w(items)
    pue = tco.pue_for(scn.cooling)
    t = tco.tco_3yr(b["total"], it_w, pue, scn.power_price, years=scn.years)
    gm = tco.gross_margin(scn.solution_price, t["total"])
    sens = tco.margin_sensitivity(scn.solution_price, t["total"])
    print("机型=%s 服务器=%d PUE=%.2f IT功率=%.0fW" % (sku.sku, servers, pue, it_w))
    print("三年TCO=%.0f（硬件成本基准%.0f + 电费%.0f + 运维%.0f）"
          % (t["total"], t["cost_basis"], t["elec_3yr"], t["opex_3yr"]))
    print("方案毛利=%.0f（报价%.0f）" % (gm, scn.solution_price))
    print("毛利敏感性(折扣→毛利)：%s" % sens)
    return {"bom": b, "tco": t, "margin": gm, "sensitivity": sens}


def cmd_redfish(args):
    import json as _json
    with open(args.inventory, "r", encoding="utf-8") as f:
        inv = _json.load(f)
    rep = redfish.redfish_precheck(inv, expected_accel_count=args.accel or 0)
    md = redfish.render_markdown(rep, title="Redfish 风格设备预检 · %s" % os.path.basename(args.inventory))
    if args.out:
        reporting.save(md, args.out)
        print("已写出：%s" % args.out)
    print(md)
    return rep


def cmd_generate(args):
    products = load_products(_paths()["products"])
    scn = load_scenario(args.scenario)
    by = _skus_by(products)
    rec, matrix = selection.recommend(scn, products)
    sku = by[args.sku] if args.sku else (by[rec["sku"]] if rec else None)
    cap = capacity.plan_capacity(scn, sku) if sku else {}
    if sku and scn.kind == "training":
        tr = capacity.plan_training(scn, sku)
        cap = dict(cap)
        cap["servers"] = tr["servers_for_target"]
        cap["actual_cards"] = tr["servers_for_target"] * sku.cards
    servers = int(args.servers or cap.get("servers", 0))
    b = bom.build_bom(scn, sku, servers) if sku else {"lines": [], "total": 0}
    items = bom.power_items(b, by, scn) if sku else []
    it_w = tco.it_power_w(items)
    pue = tco.pue_for(scn.cooling)
    t = tco.tco_3yr(b["total"], it_w, pue, scn.power_price, years=scn.years)
    gm = tco.gross_margin(scn.solution_price, t["total"])
    sens = tco.margin_sensitivity(scn.solution_price, t["total"])
    svg = diagram.build_svg(scn, sku, servers, b) if sku else ""

    out_dir = args.out or os.path.join(HERE, "outputs", scn.sid)
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "06-系统架构图.svg"), "w", encoding="utf-8") as f:
        f.write(svg)
    reporting.bom_to_csv(b, os.path.join(out_dir, "03-设备清单BOM.csv"))

    ctx = {
        "scenario": scn, "cap": cap, "bom": b, "tco": t, "margin": gm,
        "sensitivity": sens, "matrix": matrix, "recommend": rec,
        "pue": pue, "it_power_w": round(it_w, 0), "sku": sku,
    }
    reporting.render_all(_paths()["templates"], out_dir, ctx)
    summary = {
        "scenario": scn.sid, "recommend": rec["sku"] if rec else None,
        "servers": servers, "tco_3yr": t["total"], "margin": gm,
        "out_dir": out_dir,
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return summary


def main():
    ap = argparse.ArgumentParser(prog="acp", description="AI 算力售前工作台")
    sub = ap.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("compute", help="按场景测算各机型容量")
    c.add_argument("--scenario", required=True)
    c.set_defaults(func=cmd_compute)

    s = sub.add_parser("selection", help="双生态选型评分")
    s.add_argument("--scenario", required=True)
    s.set_defaults(func=cmd_selection)

    t = sub.add_parser("tco", help="液冷 PUE 与三年 TCO / 毛利测算")
    t.add_argument("--scenario", required=True)
    t.add_argument("--sku", required=True)
    t.add_argument("--servers", type=int, default=0)
    t.set_defaults(func=cmd_tco)

    r = sub.add_parser("redfish-check", help="Redfish 风格设备清单离线预检")
    r.add_argument("--inventory", required=True)
    r.add_argument("--accel", type=int, default=0)
    r.add_argument("--out", default=None)
    r.set_defaults(func=cmd_redfish)

    g = sub.add_parser("generate", help="按场景生成整套算力方案交付物")
    g.add_argument("--scenario", required=True)
    g.add_argument("--sku", default=None)
    g.add_argument("--servers", type=int, default=0)
    g.add_argument("--out", default=None)
    g.set_defaults(func=cmd_generate)

    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
