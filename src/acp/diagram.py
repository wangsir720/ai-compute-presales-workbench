"""架构图 as code：生成算力集群 SVG（不依赖外部绘图库）。"""


def build_svg(scn, sku, servers, bom):
    rows = max(1, min(servers, 8))
    col_gap = 110
    x0 = 60
    y0 = 90
    boxes = []
    for i in range(rows):
        x = x0 + i * col_gap
        boxes.append(
            '<rect x="%d" y="%d" width="90" height="56" rx="6" fill="#E8F0FE" stroke="#2563EB" stroke-width="1.5"/>'
            '<text x="%d" y="%d" font-size="11" fill="#1F3864" text-anchor="middle">%s</text>'
            '<text x="%d" y="%d" font-size="9" fill="#444" text-anchor="middle">%d×%s</text>'
            % (x, y0, x + 45, y0 + 24, "%s-计算节点" % sku.accel, x + 45, y0 + 42, i + 1, sku.sku)
        )
    switch = (
        '<rect x="%d" y="%d" width="%d" height="40" rx="6" fill="#FEF3C7" stroke="#D97706"/>'
        '<text x="%d" y="%d" font-size="11" fill="#92400E" text-anchor="middle">SW-100G 汇聚交换</text>'
        % (x0, y0 + 90, rows * col_gap - 20, x0 + (rows * col_gap - 20) / 2, y0 + 114)
    )
    storage = (
        '<rect x="%d" y="%d" width="%d" height="40" rx="6" fill="#DCFCE7" stroke="#16A34A"/>'
        '<text x="%d" y="%d" font-size="11" fill="#166534" text-anchor="middle">NAS-STORAGE 模型/数据集</text>'
        % (x0, y0 + 150, rows * col_gap - 20, x0 + (rows * col_gap - 20) / 2, y0 + 174)
    )
    cooling = ""
    if scn.cooling in ("cold-plate", "immersion"):
        cooling = (
            '<rect x="%d" y="%d" width="%d" height="34" rx="6" fill="#E0F2FE" stroke="#0284C7"/>'
            '<text x="%d" y="%d" font-size="10" fill="#075985" text-anchor="middle">CDU-LIQUID 液冷（PUE %.2f）</text>'
            % (x0, y0 + 206, rows * col_gap - 20, x0 + (rows * col_gap - 20) / 2, y0 + 227, pue_label(scn.cooling))
        )
    w = x0 + rows * col_gap + 40
    h = y0 + (240 if scn.cooling in ("cold-plate", "immersion") else 206)
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" font-family="Microsoft YaHei,sans-serif">'
        '<rect width="100%%" height="100%%" fill="#FFFFFF"/>'
        '<text x="%d" y="40" font-size="15" font-weight="bold" fill="#1F3864">%s · 算力集群架构（%d 台 %s）</text>'
        % (w, h, x0, scn.name, servers, sku.sku)
        + "".join(boxes) + switch + storage + cooling +
        '</svg>'
    )
    return svg


def pue_label(cooling):
    return {"air": 1.6, "cold-plate": 1.25, "immersion": 1.1}.get(cooling, 1.6)
