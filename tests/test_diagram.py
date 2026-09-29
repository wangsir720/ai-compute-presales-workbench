import os

from acp.models import load_products, load_scenario
from acp import capacity, diagram, bom

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROD = os.path.join(HERE, "data", "products.json")
SCN = lambda n: os.path.join(HERE, "config", "scenarios", n)


def test_svg_is_well_formed():
    products = load_products(PROD)
    by = {s.sku: s for s in products}
    scn = load_scenario(SCN("llm-inference-service.yaml"))
    sku = by["X86-GPU-8U8"]
    servers = capacity.plan_capacity(scn, sku)["servers"]
    b = bom.build_bom(scn, sku, servers)
    svg = diagram.build_svg(scn, sku, servers, b)
    assert svg.startswith("<svg")
    assert svg.rstrip().endswith("</svg>")
    assert scn.name in svg
    assert "PUE" in svg


def test_pue_label():
    assert diagram.pue_label("air") == 1.6
    assert diagram.pue_label("cold-plate") == 1.25
    assert diagram.pue_label("immersion") == 1.1


def test_svg_air_omits_cooling():
    products = load_products(PROD)
    by = {s.sku: s for s in products}
    scn = load_scenario(SCN("inference-appliance.yaml"))
    sku = by["X86-GPU-4U4"]
    svg = diagram.build_svg(scn, sku, 1, bom.build_bom(scn, sku, 1))
    assert "CDU-LIQUID" not in svg
