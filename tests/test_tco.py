import os

from acp.models import load_products, load_scenario
from acp import capacity, tco, bom

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROD = os.path.join(HERE, "data", "products.json")
SCN = lambda n: os.path.join(HERE, "config", "scenarios", n + ".yaml")


def _bom_for(sid, sku_s="X86-GPU-8U8"):
    products = load_products(PROD)
    by = {s.sku: s for s in products}
    scn = load_scenario(SCN(sid))
    sku = by[sku_s]
    servers = capacity.plan_capacity(scn, sku)["servers"]
    b = bom.build_bom(scn, sku, servers)
    items = bom.power_items(b, by, scn)
    return scn, sku, b, items


def test_pue_mapping():
    assert tco.pue_for("air") == 1.6
    assert tco.pue_for("cold-plate") == 1.25
    assert tco.pue_for("immersion") == 1.1
    assert tco.pue_for("unknown") == 1.6


def test_it_power_sum():
    scn, sku, b, items = _bom_for("llm-inference-service")
    # 2 台 X86-GPU-8U8: 6500*2 + 交换机300 + CDU200 + NAS800 = 14300
    assert tco.it_power_w(items) == 14300


def test_tco_three_year_positive_margin():
    scn, sku, b, items = _bom_for("llm-inference-service")
    it_w = tco.it_power_w(items)
    t = tco.tco_3yr(b["total"], it_w, tco.pue_for(scn.cooling), scn.power_price, years=3)
    assert t["total"] == 3127364
    gm = tco.gross_margin(scn.solution_price, t["total"])
    assert gm > 0
    assert gm == tco.margin_sensitivity(scn.solution_price, t["total"])[0.0]


def test_margin_sensitivity_decreases_with_discount():
    scn, sku, b, items = _bom_for("llm-inference-service")
    it_w = tco.it_power_w(items)
    t = tco.tco_3yr(b["total"], it_w, tco.pue_for(scn.cooling), scn.power_price)
    sens = tco.margin_sensitivity(scn.solution_price, t["total"])
    assert sens[0.0] > sens[0.05] > sens[0.10] > sens[0.15]


def test_immersion_lower_energy_than_air():
    scn, sku, b, items = _bom_for("training-cluster")
    it_w = tco.it_power_w(items)
    e_air = tco.annual_energy_kwh(it_w, tco.pue_for("air"))
    e_imm = tco.annual_energy_kwh(it_w, tco.pue_for("immersion"))
    assert e_imm < e_air
