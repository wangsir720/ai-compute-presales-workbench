import os

from acp.models import load_products, load_scenario
from acp import capacity, bom

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROD = os.path.join(HERE, "data", "products.json")
SCN = lambda n: os.path.join(HERE, "config", "scenarios", n)


def test_bom_total_equals_sum():
    products = load_products(PROD)
    by = {s.sku: s for s in products}
    scn = load_scenario(SCN("llm-inference-service.yaml"))
    sku = by["X86-GPU-8U8"]
    servers = capacity.plan_capacity(scn, sku)["servers"]
    b = bom.build_bom(scn, sku, servers)
    assert b["total"] == sum(l["subtotal"] for l in b["lines"])
    assert b["total"] == 3170000


def test_bom_has_compute_and_infra():
    products = load_products(PROD)
    by = {s.sku: s for s in products}
    scn = load_scenario(SCN("llm-inference-service.yaml"))
    sku = by["X86-GPU-8U8"]
    b = bom.build_bom(scn, sku, 2)
    groups = {l["group"] for l in b["lines"]}
    assert "计算节点" in groups
    assert "交换机" in groups
    assert "液冷分配单元" in groups  # cold-plate → 含液冷


def test_bom_air_no_cooling():
    products = load_products(PROD)
    by = {s.sku: s for s in products}
    scn = load_scenario(SCN("inference-appliance.yaml"))  # air
    sku = by["X86-GPU-4U4"]
    b = bom.build_bom(scn, sku, 1)
    groups = {l["group"] for l in b["lines"]}
    assert "液冷分配单元" not in groups


def test_power_items_excludes_zero_tdp():
    products = load_products(PROD)
    by = {s.sku: s for s in products}
    scn = load_scenario(SCN("llm-inference-service.yaml"))
    sku = by["X86-GPU-8U8"]
    b = bom.build_bom(scn, sku, 2)
    items = bom.power_items(b, by, scn)
    assert all(i["power_w"] > 0 for i in items)
