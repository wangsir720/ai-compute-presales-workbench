import csv
import os

from acp import reporting

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TPL = os.path.join(HERE, "templates")


def test_bom_to_csv_writes_header_and_total(tmp_path):
    bom = {"lines": [
        {"group": "计算节点", "sku": "X86-GPU-8U8", "qty": 2, "unit": 1300000,
         "subtotal": 2600000, "note": "x86"},
        {"group": "交换机", "sku": "SW-100G", "qty": 1, "unit": 80000,
         "subtotal": 80000, "note": "100G"},
    ], "total": 2680000}
    path = tmp_path / "bom.csv"
    reporting.bom_to_csv(bom, str(path))
    with open(path, "r", encoding="utf-8-sig") as f:
        rows = list(csv.reader(f))
    assert rows[0][0] == "分组"
    assert rows[-1][-1] == "合计"
    assert rows[-1][-2] == "2680000"


def test_render_template_requires_ctx_keys():
    env = reporting._env(TPL)
    tpl = env.get_template("01-需求调研表.md.j2")
    out = tpl.render(scenario=type("S", (), {
        "name": "测试", "sid": "t1", "kind": "inference", "precision": "bf16",
        "models": [type("M", (), {"name": "7B", "params_b": 7})()],
        "concurrency": 10, "latency_target_s": 3.0, "ctx_len": 4096,
        "cooling": "air", "power_price": 0.8, "solution_price": 1000000, "years": 3,
    })())
    assert "测试" in out
    assert "7B" in out


def test_render_all_runs_on_scenario(tmp_path):
    from acp.models import load_scenario
    from acp import capacity, selection, tco, bom
    scn = load_scenario(os.path.join(HERE, "config", "scenarios", "llm-inference-service.yaml"))
    from acp.models import load_products
    products = load_products(os.path.join(HERE, "data", "products.json"))
    by = {s.sku: s for s in products}
    rec, matrix = selection.recommend(scn, products)
    sku = by[rec["sku"]]
    cap = capacity.plan_capacity(scn, sku)
    b = bom.build_bom(scn, sku, cap["servers"])
    items = bom.power_items(b, by, scn)
    it_w = tco.it_power_w(items)
    t = tco.tco_3yr(b["total"], it_w, tco.pue_for(scn.cooling), scn.power_price, years=scn.years)
    gm = tco.gross_margin(scn.solution_price, t["total"])
    ctx = {"scenario": scn, "cap": cap, "bom": b, "tco": t, "margin": gm,
           "sensitivity": tco.margin_sensitivity(scn.solution_price, t["total"]),
           "matrix": matrix, "recommend": rec, "pue": tco.pue_for(scn.cooling),
           "it_power_w": it_w, "sku": sku}
    reporting.render_all(TPL, str(tmp_path), ctx)
    assert os.path.exists(os.path.join(str(tmp_path), "02-算力技术方案书.md"))
    assert os.path.exists(os.path.join(str(tmp_path), "04-TCO测算.md"))
