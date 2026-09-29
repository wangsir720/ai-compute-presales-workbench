import os

from acp.models import load_products, load_scenario
from acp import selection

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROD = os.path.join(HERE, "data", "products.json")
SCN = lambda n: os.path.join(HERE, "config", "scenarios", n)


def test_matrix_excludes_cpu_nodes():
    products = load_products(PROD)
    scn = load_scenario(SCN("llm-inference-service.yaml"))
    m = selection.selection_matrix(scn, products)
    assert len(m) == 4
    assert all(r["servers"] >= 1 for r in m)


def test_matrix_sorted_descending():
    products = load_products(PROD)
    scn = load_scenario(SCN("llm-inference-service.yaml"))
    m = selection.selection_matrix(scn, products)
    scores = [r["score"] for r in m]
    assert scores == sorted(scores, reverse=True)


def test_recommend_is_top():
    products = load_products(PROD)
    scn = load_scenario(SCN("llm-inference-service.yaml"))
    rec, m = selection.recommend(scn, products)
    assert rec is not None
    assert rec["sku"] == m[0]["sku"]


def test_localization_present():
    products = load_products(PROD)
    scn = load_scenario(SCN("llm-inference-service.yaml"))
    m = selection.selection_matrix(scn, products)
    locs = {r["sku"]: r["localization"] for r in m}
    assert locs["KP-ASC-8U8"] == 1.0
    assert locs["X86-GPU-8U8"] == 0.6
