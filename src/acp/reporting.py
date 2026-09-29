"""模板渲染与 CSV 输出。"""

import csv
import os

from jinja2 import Environment, FileSystemLoader, select_autoescape


def _env(templates_dir):
    return Environment(
        loader=FileSystemLoader(templates_dir),
        autoescape=select_autoescape(["html"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )


def render_all(templates_dir, out_dir, ctx):
    os.makedirs(out_dir, exist_ok=True)
    env = _env(templates_dir)
    for name in env.list_templates():
        if not name.endswith(".j2"):
            continue
        tpl = env.get_template(name)
        out_name = name[:-3]
        with open(os.path.join(out_dir, out_name), "w", encoding="utf-8") as f:
            f.write(tpl.render(**ctx))
    return out_dir


def bom_to_csv(bom, path):
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["分组", "型号", "数量", "单价(元)", "小计(元)", "说明"])
        for l in bom["lines"]:
            w.writerow([l["group"], l["sku"], l["qty"], l["unit"], l["subtotal"], l["note"]])
        w.writerow(["", "", "", "", bom["total"], "合计"])


def save(text, path):
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
