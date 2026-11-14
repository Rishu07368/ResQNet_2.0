from __future__ import annotations

import json
import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
from PIL import Image
from docx import Document
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor


ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "docs" / "report"
GEN = OUT / "report_generation"
IMG = GEN / "figures"
SHOTS = OUT / "screenshots"
CU_LOGO = OUT / "assets" / "chandigarh-university-logo.png"
EVIDENCE = json.loads((GEN / "execution_evidence.json").read_text(encoding="utf-8"))
BLUE = "#12304a"
TEAL = "#12b8a6"
GOLD = "#efb547"
PALE = "#eaf2f6"
DARK = "#203040"
FIGURES = 0
TABLES = 0


def _style(ax, title=None):
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    if title:
        ax.set_title(title, fontsize=14, fontweight="bold", color=BLUE, pad=12)


def _box(ax, xy, wh, label, color=PALE, fontsize=9, edge=BLUE):
    x, y = xy
    w, h = wh
    patch = FancyBboxPatch(
        (x, y), w, h, boxstyle="round,pad=0.012,rounding_size=0.018",
        facecolor=color, edgecolor=edge, linewidth=1.2,
    )
    ax.add_patch(patch)
    ax.text(x + w / 2, y + h / 2, label, ha="center", va="center",
            fontsize=fontsize, color=DARK, wrap=True)


def _arrow(ax, first, second, color=TEAL, rad=0):
    ax.add_patch(FancyArrowPatch(
        first, second, arrowstyle="-|>", mutation_scale=11, linewidth=1.4,
        color=color, connectionstyle=f"arc3,rad={rad}",
    ))


def flow_image(name, title, labels, direction="vertical"):
    fig, ax = plt.subplots(figsize=(10, 4.5), dpi=180)
    _style(ax, title)
    if direction == "horizontal":
        n = len(labels)
        width = min(0.17, 0.78 / n)
        gap = (0.78 - n * width) / max(1, n - 1)
        y = 0.43
        starts = []
        for i, label in enumerate(labels):
            x = 0.08 + i * (width + gap)
            _box(ax, (x, y), (width, 0.18), label, PALE if i % 2 == 0 else "#d7f0ec", 8)
            starts.append((x, width))
        for (x, w), (nx, _) in zip(starts, starts[1:]):
            _arrow(ax, (x + w + 0.004, y + 0.09), (nx - 0.004, y + 0.09))
    else:
        n = len(labels)
        height = min(0.12, 0.76 / n)
        gap = (0.76 - n * height) / max(1, n - 1)
        positions = []
        for i, label in enumerate(labels):
            y = 0.88 - i * (height + gap)
            x = 0.22 + (0.09 if i % 2 else 0)
            _box(ax, (x, y - height), (0.56, height), label,
                 "#d7f0ec" if i % 2 else PALE, 8)
            positions.append((x, y - height, height))
        for (_, y, h), (nx, ny, _) in zip(positions, positions[1:]):
            _arrow(ax, (0.5, y - 0.005), (0.5, ny + h + 0.005))
    path = IMG / f"{name}.png"
    fig.savefig(path, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return path


def architecture_image(name, title, layers, columns=1):
    fig, ax = plt.subplots(figsize=(10, 4.2), dpi=180)
    _style(ax, title)
    if columns == 1:
        n = len(layers)
        h = min(0.14, 0.78 / n)
        gap = (0.78 - n * h) / max(1, n - 1)
        locs = []
        for i, (head, detail) in enumerate(layers):
            y = 0.88 - i * (h + gap)
            _box(ax, (0.13, y - h), (0.74, h), f"{head}\n{detail}",
                 "#d7f0ec" if i in (0, n - 1) else PALE, 8)
            locs.append(y - h)
        for y1, y2 in zip(locs, locs[1:]):
            _arrow(ax, (0.5, y1 - 0.003), (0.5, y2 + h + 0.003))
    else:
        rows = math.ceil(len(layers) / columns)
        w = 0.84 / columns
        h = 0.66 / rows
        for i, (head, detail) in enumerate(layers):
            col, row = i % columns, i // columns
            x, y = 0.08 + col * w, 0.82 - row * h
            _box(ax, (x, y - h + 0.025), (w - 0.035, h - 0.05),
                 f"{head}\n{detail}", "#d7f0ec" if i % 2 else PALE, 8)
            if col < columns - 1 and row == 0:
                _arrow(ax, (x + w - 0.04, y - h / 2), (x + w - 0.005, y - h / 2))
    path = IMG / f"{name}.png"
    fig.savefig(path, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return path


def graph_image():
    fig, ax = plt.subplots(figsize=(8, 4.2), dpi=180)
    _style(ax, "Metroville's deterministic 6 x 6 location grid (schematic)")
    for r in range(6):
        for c in range(6):
            x = 0.12 + c * 0.15
            y = 0.14 + (5 - r) * 0.145
            idx = r * 6 + c + 1
            loc = f"M{idx:02d}"
            if c < 5:
                _arrow(ax, (x + 0.025, y), (x + 0.125, y), "#82a6b8")
                _arrow(ax, (x + 0.125, y - 0.012), (x + 0.025, y - 0.012), "#c3d0d7")
            if r < 5:
                _arrow(ax, (x, y - 0.02), (x, y - 0.105), "#82a6b8")
                _arrow(ax, (x + 0.012, y - 0.105), (x + 0.012, y - 0.02), "#c3d0d7")
            ax.scatter([x], [y], s=170, color=TEAL if idx in (2, 14, 26) else BLUE,
                       edgecolors="white", linewidths=1.0, zorder=3)
            ax.text(x, y, loc, color="white", ha="center", va="center", fontsize=6, zorder=4)
    ax.text(0.88, 0.76, "Teal: selected hospitals", color=TEAL, fontsize=8)
    ax.text(0.88, 0.68, "Directed reciprocal roads", color=DARK, fontsize=8)
    ax.text(0.88, 0.60, "Each road has its own\nweight and capacity", color=DARK, fontsize=8)
    path = IMG / "city_graph.png"
    fig.savefig(path, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return path


def er_image():
    entities = [
        ("locations", "id PK\nname, kind\nlatitude, longitude"),
        ("roads", "id PK\nsource_id FK\n target_id FK\ndistance, time,\ncapacity, is_open"),
        ("ambulances", "id PK\nlocation_id FK\nstatus, capability"),
        ("hospitals", "id PK\nlocation_id FK\nbeds, specialty"),
        ("shelters", "id PK\nlocation_id FK\ncapacity"),
        ("incidents", "id PK\nlocation_id FK\nassigned_ambulance\nhospital_id"),
        ("dispatch_records", "id PK\nincident_id FK\nambulance_id FK\nroute, ETA"),
        ("hospital_allocations", "id PK\nincident_id FK\nhospital_id FK\nbeds_reserved"),
        ("simulation_runs", "evacuation_runs\nbenchmark_runs\nalgorithm_runs"),
    ]
    fig, ax = plt.subplots(figsize=(10, 6), dpi=180)
    _style(ax, "SQLite entity model (selected fields)")
    coords = {
        "locations": (0.04, 0.67), "roads": (0.36, 0.67), "ambulances": (0.04, 0.35),
        "hospitals": (0.36, 0.35), "shelters": (0.68, 0.67), "incidents": (0.68, 0.35),
        "dispatch_records": (0.04, 0.04), "hospital_allocations": (0.36, 0.04),
        "simulation_runs": (0.68, 0.04),
    }
    for name, body in entities:
        x, y = coords[name]
        _box(ax, (x, y), (0.27, 0.23), f"{name}\n{body}", PALE, 7)
    links = [
        ((0.31, .76), (.36, .76)), ((.31, .72), (.68, .47)),
        ((.31, .44), (.68, .44)), ((.63, .44), (.68, .44)),
        ((.31, .44), (.36, .15)), ((.63, .44), (.36, .15)),
        ((.175, .67), (.175, .58)), ((.495, .67), (.495, .58)),
        ((.815, .67), (.815, .58)),
    ]
    for a, b in links:
        _arrow(ax, a, b, "#7995a5")
    path = IMG / "erd.png"
    fig.savefig(path, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return path


def benchmark_image():
    data = {
        item["size"]: item
        for item in EVIDENCE["benchmark_growth"]["growth_results"]
    }
    sizes = sorted(data)
    fig, ax = plt.subplots(figsize=(8.5, 4), dpi=180)
    for alg, label, color in [
        ("dijkstra_heap", "Dijkstra heap", BLUE),
        ("dijkstra_array", "Dijkstra array", TEAL),
        ("astar", "A*", GOLD),
        ("bellman_ford", "Bellman-Ford", "#ab6688"),
    ]:
        values = [data[n]["algorithms"][alg]["median_ms"] for n in sizes]
        ax.plot(sizes, values, marker="o", linewidth=1.8, label=label, color=color)
    ax.set_title("Measured growth sweep (seed 42, average degree 4, 3 repetitions)", color=BLUE, weight="bold")
    ax.set_xlabel("Vertices")
    ax.set_ylabel("Median execution time (ms; log scale)")
    ax.set_yscale("log")
    ax.grid(True, alpha=.25)
    ax.legend(frameon=False, ncol=2)
    fig.tight_layout()
    path = IMG / "benchmark_growth.png"
    fig.savefig(path, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return path, data


def gantt_image():
    tasks = [
        ("Research and requirements", 1, 2),
        ("Graph, schema and seed", 2, 2),
        ("Algorithms and services", 3, 2),
        ("API and user interface", 4, 2),
        ("Integration and validation", 5, 2),
        ("Report and final review", 6, 1),
    ]
    fig, ax = plt.subplots(figsize=(8.5, 3.2), dpi=180)
    colors = [BLUE, TEAL, GOLD, "#6383a0", "#69a897", "#d18b53"]
    for i, (name, start, duration) in enumerate(tasks):
        ax.barh(i, duration, left=start - 1, color=colors[i], height=.58)
        ax.text(start - .82, i, name, va="center", ha="right", fontsize=8, color=DARK)
    ax.set_yticks([])
    ax.set_xticks(range(6), [f"Week {i}" for i in range(1, 7)])
    ax.set_xlim(-2.8, 6)
    ax.invert_yaxis()
    ax.grid(axis="x", alpha=.2)
    ax.set_title("Estimated project schedule (not historical dates)", color=BLUE, weight="bold")
    fig.tight_layout()
    path = IMG / "estimated_gantt.png"
    fig.savefig(path, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return path


def prepare_diagrams():
    IMG.mkdir(parents=True, exist_ok=True)
    cropped = SHOTS / "cropped"
    cropped.mkdir(parents=True, exist_ok=True)
    for source in SHOTS.glob("*.jpg"):
        with Image.open(source) as image:
            image.crop((0, 0, min(830, image.width), min(515, image.height))).save(
                cropped / source.name, quality=92
            )
    paths = {
        "graphical": flow_image("graphical_abstract", "ResQNet graphical abstract",
                                ["Incident", "City graph", "Algorithm selection",
                                 "Dispatch / routing", "Hospital / evacuation", "Analysis"],
                                "horizontal"),
        "timeline": flow_image("problem_timeline", "Selected milestones in graph optimization and emergency management",
                               ["1956-59: MST, shortest paths, and Bellman-Ford",
                                "1968-72: A* and augmenting-path maximum flow",
                                "1990s-2000s: GPS / intelligent transport systems expand",
                                "2010s: dynamic routing and multi-criteria dispatch research",
                                "2020s: resilient, interoperable emergency coordination guidance"]),
        "gantt": gantt_image(),
        "monolithic": architecture_image("alternative_monolithic", "Alternative 1 - monolithic application",
                                         [("Single Flask module", "UI routes, business rules, algorithms, SQL in one unit"),
                                          ("Shared database", "All workflows coupled to one module"),
                                          ("User interface", "Templates and request handling")]),
        "modular": architecture_image("alternative_modular", "Alternative 2 - layered modular architecture",
                                      [("Vanilla JS + SVG", "API client, panels, map and charts"),
                                       ("Flask API", "HTTP validation, JSON errors and route handlers"),
                                       ("Domain services", "Dispatch, routing, hospitals, evacuation, analytics"),
                                       ("Independent algorithms", "Pure graph functions and counters"),
                                       ("SQLite repository", "Schema, transactions and deterministic seed")]),
        "architecture": architecture_image("resqnet_architecture", "Implemented ResQNet architecture",
                                           [("Browser UI", "HTML / CSS / ES modules / SVG"),
                                            ("REST-style Flask API", "Validation + JSON serialization"),
                                            ("Service layer", "Workflow rules + graph snapshots"),
                                            ("Algorithm layer", "Dijkstra, A*, BFS/DFS, Kruskal, flow, Bellman-Ford"),
                                            ("SQLite", "Persistent simulation state and run history")]),
        "usecase": architecture_image("usecase", "Use-case view (simulation operator)",
                                      [("Manage network", "Inspect graph; open / close roads"),
                                       ("Plan response", "Create incident; dispatch available ambulance"),
                                       ("Coordinate care", "Recommend suitable hospital; reserve bed"),
                                       ("Plan evacuation", "Select zones / shelters; calculate capacity flow"),
                                       ("Study algorithms", "Trace, compare, benchmark and inspect analytics")]),
        "workflow": flow_image("workflow", "Request-to-result workflow",
                               ["Operator action in browser", "HTTP JSON request",
                                "Input validation / API handler", "Service loads SQLite snapshot",
                                "Pure algorithm computes result", "Service persists state if requested",
                                "JSON response and SVG / UI update"]),
        "graph": graph_image(),
        "erd": er_image(),
        "api": flow_image("api_lifecycle", "API request lifecycle",
                          ["Browser serializes JSON", "Flask route validates fields and types",
                           "Service checks domain constraints", "Graph snapshot / repository query",
                           "Algorithm returns result and counters", "Transaction commits, when applicable",
                           "JSON response or explicit error code"]),
        "dispatch": flow_image("dispatch_flow", "Ambulance dispatch selection",
                               ["Read pending incident", "Filter available ambulances by capability",
                                "Run time-weighted Dijkstra for each candidate", "Discard unreachable candidates",
                                "Rank by ETA, then ambulance ID", "Conditional transaction assigns unit and records route",
                                "Progress incident; release ambulance on resolution / cancellation"]),
        "routing": flow_image("routing_flow", "Route calculation and reconstruction",
                              ["Build graph snapshot from open directed roads", "Select time or distance weight",
                               "Run chosen shortest-path algorithm", "Track predecessor on successful relaxation",
                               "Reconstruct source-to-target path", "Sum road attributes and return trace / counters"]),
        "dijkstra": flow_image("dijkstra_flow", "Dijkstra (binary heap) flow",
                               ["Initialize distances and predecessor map", "Push source with distance zero",
                                "Pop minimum; skip stale heap entry", "If target: stop; else inspect outgoing edges",
                                "Relax lower-cost neighbors and push updated keys", "Reconstruct route and return statistics"]),
        "astar": flow_image("astar_flow", "A* search flow",
                            ["Initialize g(source)=0 and f=g+h", "Pop lowest f from priority queue",
                             "Skip stale / already closed node", "Stop when target is removed from queue",
                             "Relax neighbors using g + edge cost; push g+h", "Reconstruct route; heuristic is geographic lower bound"]),
        "traversal": flow_image("traversal_flow", "BFS and DFS reachability",
                                ["Start from selected location", "BFS uses FIFO queue; DFS uses LIFO stack",
                                 "Mark each newly discovered neighbor", "Continue until frontier is empty",
                                 "Return visitation order and unreachable locations",
                                 "Connectivity components use undirected projection"]),
        "kruskal": flow_image("kruskal_flow", "Kruskal minimum spanning forest",
                              ["Normalize reciprocal roads as undirected candidates", "Sort unique pairs by selected weight",
                               "Initialize disjoint-set representatives", "Scan edges in ascending order",
                               "Union endpoints only when roots differ", "Return forest, total weight, and components"]),
        "flow": flow_image("edmonds_karp_flow", "Edmonds-Karp maximum-flow calculation",
                           ["Build residual capacity matrix and adjacency", "BFS finds source-to-sink residual path",
                            "No path remains: terminate", "Bottleneck = minimum residual on path",
                            "Update forward and reverse residual capacities", "Add bottleneck and repeat",
                            "Residual reachability yields a minimum cut"]),
        "hospital": flow_image("hospital_flow", "Hospital recommendation and bed reservation",
                               ["Load incident, hospital, and open-road graph", "Reject closed, full, specialty-incompatible, or unreachable facilities",
                                "Compute route ETA to every eligible hospital", "Rank by ETA; tie-break by beds then ID",
                                "Operator confirms recommendation", "Transaction reserves one bed and links allocation"]),
        "evacuation": flow_image("evacuation_flow", "Evacuation network construction",
                                 ["Add super-source to each zone (population demand)", "Use open directed roads as capacity arcs",
                                  "Connect selected shelters to super-sink (shelter limit)", "Run Edmonds-Karp",
                                  "Report maximum flow and unserved demand", "Return augmenting paths, utilization and minimum cut"]),
        "closure": flow_image("road_closure_flow", "Road closure and rerouting",
                              ["Choose a directed road", "Persist is_open = 0",
                               "Next graph snapshot omits closed arc", "Recompute route on remaining roads",
                               "Show changed path and ETA, or report unreachable", "Reopen road to restore it"]),
    }
    paths["benchmark"], data = benchmark_image()
    return paths, data


def shade(cell, fill):
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:fill"), fill)
    tc_pr.append(shd)


def set_cell_text(cell, text, bold=False, color=None, size=8.5):
    cell.text = ""
    p = cell.paragraphs[0]
    p.paragraph_format.space_after = Pt(0)
    run = p.add_run(str(text))
    run.bold = bold
    run.font.name = "Times New Roman"
    run.font.size = Pt(size)
    if color:
        run.font.color.rgb = RGBColor.from_string(color)
    cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER


def set_repeat_table_header(row):
    tr_pr = row._tr.get_or_add_trPr()
    tbl_header = OxmlElement("w:tblHeader")
    tbl_header.set(qn("w:val"), "true")
    tr_pr.append(tbl_header)


def add_page_field(paragraph):
    run = paragraph.add_run()
    begin = OxmlElement("w:fldChar")
    begin.set(qn("w:fldCharType"), "begin")
    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = " PAGE "
    separate = OxmlElement("w:fldChar")
    separate.set(qn("w:fldCharType"), "separate")
    text = OxmlElement("w:t")
    text.text = "1"
    end = OxmlElement("w:fldChar")
    end.set(qn("w:fldCharType"), "end")
    for item in (begin, instr, separate, text, end):
        run._r.append(item)


def add_word_field(paragraph, instruction):
    run = paragraph.add_run()
    for kind, value in (("begin", None), ("instrText", instruction), ("separate", None)):
        if kind == "begin":
            element = OxmlElement("w:fldChar")
            element.set(qn("w:fldCharType"), "begin")
        elif kind == "instrText":
            element = OxmlElement("w:instrText")
            element.set(qn("xml:space"), "preserve")
            element.text = value
        else:
            element = OxmlElement("w:fldChar")
            element.set(qn("w:fldCharType"), "separate")
        run._r.append(element)
    result = OxmlElement("w:t")
    result.text = "Update field in Word"
    run._r.append(result)
    end = OxmlElement("w:fldChar")
    end.set(qn("w:fldCharType"), "end")
    run._r.append(end)


def add_seq(paragraph, category):
    run = paragraph.add_run()
    begin = OxmlElement("w:fldChar")
    begin.set(qn("w:fldCharType"), "begin")
    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = f" SEQ {category} \\* ARABIC "
    separate = OxmlElement("w:fldChar")
    separate.set(qn("w:fldCharType"), "separate")
    text = OxmlElement("w:t")
    text.text = "1"
    end = OxmlElement("w:fldChar")
    end.set(qn("w:fldCharType"), "end")
    for item in (begin, instr, separate, text, end):
        run._r.append(item)


def set_repeat_header(row):
    set_repeat_table_header(row)


def build():
    global FIGURES, TABLES
    OUT.mkdir(parents=True, exist_ok=True)
    paths, benchmark_data = prepare_diagrams()
    doc = Document()
    sec = doc.sections[0]
    sec.top_margin, sec.bottom_margin = Inches(.72), Inches(.72)
    sec.left_margin, sec.right_margin = Inches(.82), Inches(.82)
    sec.page_width, sec.page_height = Inches(8.27), Inches(11.69)
    styles = doc.styles
    normal = styles["Normal"]
    normal.font.name = "Times New Roman"
    normal.font.size = Pt(10.5)
    normal.paragraph_format.space_after = Pt(5)
    normal.paragraph_format.line_spacing = 1.08
    for name, size, color in [("Heading 1", 16, BLUE), ("Heading 2", 12.5, BLUE), ("Heading 3", 11, TEAL)]:
        style = styles[name]
        style.font.name = "Times New Roman"
        style.font.size = Pt(size)
        style.font.bold = True
        style.font.color.rgb = RGBColor.from_string(color.replace("#", "").upper())
        style.paragraph_format.space_before = Pt(10)
        style.paragraph_format.space_after = Pt(5)
        style.paragraph_format.keep_with_next = True
    styles["Caption"].font.name = "Times New Roman"
    styles["Caption"].font.size = Pt(9)
    styles["Caption"].font.italic = True

    footer = sec.footer.paragraphs[0]
    footer.alignment = WD_ALIGN_PARAGRAPH.CENTER
    footer.add_run("Chandigarh University  |  ")
    add_page_field(footer)

    def para(text="", bold_lead=None, align=None, italic=False):
        p = doc.add_paragraph()
        if align is not None:
            p.alignment = align
        if bold_lead and text.startswith(bold_lead):
            p.add_run(bold_lead).bold = True
            p.add_run(text[len(bold_lead):])
        else:
            r = p.add_run(text)
            r.italic = italic
        return p

    def heading(text, level=2):
        return doc.add_heading(text, level=level)

    def chapter(number, title):
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.style = "Heading 1"
        p.paragraph_format.page_break_before = True
        p.paragraph_format.space_before = Pt(45)
        r = p.add_run(f"CHAPTER {number}\n{title.upper()}")
        r.bold = True
        r.font.name = "Times New Roman"
        r.font.size = Pt(18)
        r.font.color.rgb = RGBColor.from_string(BLUE.replace("#", ""))
        p.paragraph_format.space_after = Pt(24)
        return p

    def table(headers, rows, widths=None, font=8.2, title="Report data"):
        global TABLES
        TABLES += 1
        t = doc.add_table(rows=1, cols=len(headers))
        t.style = "Table Grid"
        t.alignment = WD_TABLE_ALIGNMENT.CENTER
        t.autofit = True
        header_row = t.rows[0]
        set_repeat_header(header_row)
        for i, value in enumerate(headers):
            set_cell_text(header_row.cells[i], value, True, "FFFFFF", font)
            shade(header_row.cells[i], BLUE.replace("#", ""))
        for row in rows:
            cells = t.add_row().cells
            for i, value in enumerate(row):
                set_cell_text(cells[i], value, False, None, font)
                if len(t.rows) % 2 == 0:
                    shade(cells[i], "F2F6F8")
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_before = Pt(2)
        p.paragraph_format.space_after = Pt(8)
        p.style = "Caption"
        p.add_run("Table ")
        add_seq(p, "Table")
        p.add_run(f". {title}")
        return t

    def figure(path, title, width=6.15):
        global FIGURES
        FIGURES += 1
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_after = Pt(0)
        p.add_run().add_picture(str(path), width=Inches(width))
        cap = doc.add_paragraph()
        cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
        cap.paragraph_format.space_after = Pt(8)
        cap.style = "Caption"
        cap.add_run("Figure ")
        add_seq(cap, "Figure")
        cap.add_run(f". {title}")

    def subsection(title, body):
        heading(title, 2)
        for item in body:
            para(item)

    def bullet(text):
        p = doc.add_paragraph(style="List Bullet")
        p.paragraph_format.space_after = Pt(2)
        p.add_run(text)

    # Formal title page follows the sample's hierarchy and lower-page logo placement.
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(8)
    r = p.add_run("RESQNET\nINTELLIGENT EMERGENCY RESPONSE &\nDISASTER EVACUATION OPTIMIZATION SYSTEM")
    r.bold = True
    r.font.name = "Times New Roman"
    r.font.size = Pt(14)
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(25)
    r = p.add_run("A PROJECT REPORT")
    r.bold = True
    r.font.size = Pt(14)
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(35)
    r = p.add_run("Submitted by")
    r.bold = True
    r.italic = True
    r.font.size = Pt(14)
    p = para("J SRIKAR\nUID: 25BCS12640", align=WD_ALIGN_PARAGRAPH.CENTER)
    p.runs[0].bold = True
    p.runs[0].font.size = Pt(16)
    p.paragraph_format.space_before = Pt(24)
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(26)
    r = p.add_run("in partial fulfillment for the award of the degree of")
    r.bold = True
    r.italic = True
    r.font.size = Pt(14)
    p = para("BACHELOR OF ENGINEERING\nIN\nCOMPUTER SCIENCE AND ENGINEERING",
             align=WD_ALIGN_PARAGRAPH.CENTER)
    p.runs[0].bold = True
    p.runs[0].font.size = Pt(16)
    p.paragraph_format.space_before = Pt(22)
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(205)
    p.add_run().add_picture(str(CU_LOGO), width=Inches(2.6))
    p = para("Chandigarh University", align=WD_ALIGN_PARAGRAPH.CENTER)
    p.runs[0].bold = True
    p.runs[0].font.size = Pt(14)
    p.paragraph_format.space_before = Pt(4)
    para("NOVEMBER 2026", align=WD_ALIGN_PARAGRAPH.CENTER)

    # Bonafide certificate
    doc.add_page_break()
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(8)
    p.add_run().add_picture(str(CU_LOGO), width=Inches(2.6))
    heading("BONAFIDE CERTIFICATE", 1)
    para("This is to certify that the project report entitled “ResQNet — Intelligent Emergency Response & Disaster Evacuation Optimization System” is a bonafide work carried out by J Srikar (UID: 25BCS12640), a student of Bachelor of Engineering in Computer Science and Engineering at Chandigarh University, in partial fulfillment of the requirements for the Analysis and Design of Algorithms (ADSA) subject.")
    para("The work is an academic simulation developed and documented for educational purposes. The certificate is provided as a blank institutional form for review; no approval or signature is implied.")
    doc.add_paragraph("\n\n")
    table(["Project Supervisor", "Head of Department"], [
        ("Signature: __________________________", "Signature: __________________________"),
        ("Name / designation: [To be completed by university]", "Name / designation: [To be completed by university]"),
        ("Date: ______________________________", "Date: ______________________________"),
    ], title="Signature and academic designation placeholders")
    doc.add_paragraph("\n")
    table(["Internal Examiner", "External Examiner"], [
        ("Signature: __________________________", "Signature: __________________________"),
        ("Name: [To be completed]", "Name: [To be completed]"),
    ], title="Examiner signature placeholders")
    para("Viva-voce examination date: __________________________")

    # TOC and lists
    for title, field in [
        ("TABLE OF CONTENTS", 'TOC \\o "1-3" \\h \\z \\u'),
        ("LIST OF FIGURES", 'TOC \\h \\z \\c "Figure"'),
        ("LIST OF TABLES", 'TOC \\h \\z \\c "Table"'),
    ]:
        doc.add_page_break()
        heading(title, 1)
        add_word_field(doc.add_paragraph(), field)

    # Standards
    doc.add_page_break()
    heading("LIST OF STANDARDS", 1)
    para("The standards below were considered as design and terminology guidance. This project has not undergone a formal conformity assessment and does not claim certification or compliance.")
    table(["Standard", "Publishing agency", "About the standard", "Page Number"], [
        ("ISO/IEC 25010:2023, Systems and software engineering — SQuaRE — Product quality model (2023 edition)",
         "ISO / IEC", "Quality-model vocabulary used to discuss functional suitability, usability, reliability, performance efficiency, maintainability and security. Guidance only; no conformance test was performed.", "8"),
        ("ISO/IEC/IEEE 29148:2018, Systems and software engineering — Life cycle processes — Requirements engineering",
         "ISO / IEC / IEEE", "Requirements-engineering guidance considered when organizing functional and quality requirements. No formal process compliance is asserted.", "8"),
        ("ISO 22320:2018, Security and resilience — Emergency management — Guidelines for incident management",
         "ISO", "Incident-management concepts provide background for the simulated incident workflow. ResQNet is not an operational incident-management system.", "8"),
    ], title="Standards considered as design guidance")

    # Abstract
    doc.add_page_break()
    heading("ABSTRACT", 1)
    para("Emergency response and evacuation planning require decisions across a road network whose routes, facility constraints and movement capacities may change. ResQNet is an academic, offline simulation that models the fictional city of Metroville as a weighted directed graph and demonstrates the application of graph algorithms to routing, ambulance selection, hospital recommendation, road closure analysis and capacity-limited evacuation.")
    para("The deterministic seed contains 36 locations and 120 directed roads, alongside simulated ambulances, hospitals, shelters and training incidents. Each directed road stores distance, travel time, evacuation capacity, open/closed state and an infrastructure-cost value. The Flask application separates pure algorithms from service logic, HTTP validation and SQLite persistence. Its browser interface is implemented with HTML, CSS, vanilla JavaScript and SVG.")
    para("The implemented algorithms include binary-heap and array-selection Dijkstra, A* with a geographic lower-bound heuristic, BFS, DFS, Kruskal with a disjoint-set structure, Edmonds-Karp maximum flow, and Bellman-Ford in an isolated educational sandbox. Representative measured results include a 20.5-minute Dijkstra route from M01 to M36, a simulated dispatch choice of AMB-07 for incident 1, and an evacuation maximum flow of 480 against a demand of 550 in the captured test scenario. The automated test suite completed with 16 passed tests.")
    para("The results demonstrate how algorithmic models and instrumented counters can be connected to interactive workflows. Because the network, traffic and operational data are simulated, and because no real dispatch integration, live traffic or validated safety model exists, ResQNet must not be used for real emergency decisions.")

    doc.add_page_break()
    heading("GRAPHICAL ABSTRACT", 1)
    figure(paths["graphical"], "Graphical abstract: incident-to-analysis simulation workflow", 6.5)
    para("The application turns a simulated incident into a graph problem, selects a relevant algorithm, and returns a route, allocation or capacity result with observable statistics.")

    # Abbreviations and symbols
    doc.add_page_break()
    heading("ABBREVIATIONS", 1)
    table(["Abbreviation", "Meaning"], [
        ("ADSA", "Analysis and Design of Algorithms"), ("A*", "A-star search"),
        ("API", "Application Programming Interface"), ("BFS", "Breadth-First Search"),
        ("CRUD", "Create, Read, Update, Delete"), ("DFS", "Depth-First Search"),
        ("DSU", "Disjoint-Set Union"), ("ETA", "Estimated Time of Arrival (simulated)"),
        ("HTTP", "Hypertext Transfer Protocol"), ("MST", "Minimum Spanning Tree"),
        ("REST", "Representational State Transfer"), ("SVG", "Scalable Vector Graphics"),
        ("UI", "User Interface"), ("UX", "User Experience"), ("V", "Vertex set"),
        ("E", "Edge set"),
    ], title="Abbreviations used in this report")
    heading("SYMBOLS", 1)
    table(["Symbol", "Definition"], [
        ("G = (V, E)", "A graph with vertex set V and directed edge set E"),
        ("u, v", "Vertices / locations in a graph"),
        ("w(u,v)", "Non-negative route cost on directed edge (u,v), e.g. time or distance"),
        ("d(v)", "Current tentative shortest-path distance from the source to v"),
        ("g(n)", "Known path cost from the source to node n in A*"),
        ("h(n)", "Admissible lower-bound estimate from n to the target in A*"),
        ("f(n) = g(n) + h(n)", "A* priority value"),
        ("C(u,v)", "Capacity of directed edge (u,v), expressed as simulated people per configured period"),
        ("F", "Maximum feasible source-to-sink flow"),
        ("O(·)", "Asymptotic upper-bound notation for algorithmic complexity"),
        ("V, E", "Number of vertices and edges, respectively, in complexity expressions"),
    ], title="Mathematical symbols used in this report")

    # Chapter 1
    chapter(1, "Introduction")
    subsection("1.1 Identification of Client / Need / Relevant Contemporary Issue", [
        "ResQNet has no external client or commissioning emergency agency. It is an academic simulation for the ADSA subject. The broader need it examines is the coordination challenge of moving response vehicles, patients and evacuees through a constrained, potentially disrupted transport network.",
        "A response plan can be affected by road accessibility, facility capacity, specialty requirements, directional closures and the distinction between travel cost and movement throughput. The World Health Organization's Global Status Report on Road Safety 2023 estimates approximately 1.19 million road-traffic deaths annually worldwide [1]. This statistic establishes the public-health significance of road safety; it is not an estimate of ambulance delay or a direct evaluation of ResQNet.",
        "For Indian context, the National Disaster Management Plan (2019) is a national planning reference for disaster preparedness and response coordination [13]. ResQNet does not implement that plan or represent any Indian agency; the reference only situates the academic topic within the country's documented disaster-management planning framework.",
        "Graph models offer a disciplined way to express locations, one-way connectivity, route weights and capacities. Shortest-path algorithms can compare candidate routes under a stated metric; matching and ranking rules can help demonstrate dispatch and facility selection; max-flow algorithms can reason about throughput under explicit capacity assumptions. These are decision-support models, not substitutes for trained emergency managers, live situational awareness or validated operational protocols.",
        "The project uses fictional Metroville data and makes no claim that its topology, capacity assumptions or results correspond to Chandigarh, India, or any real emergency service."
    ])
    subsection("1.2 Identification of Problem", [
        "The problem addressed is the difficulty of coordinating simulated emergency movements across a city network when routes and destinations have different costs and constraints. The problem includes identifying reachable places, comparing travel options, selecting available response resources, considering medical eligibility and estimating how much evacuation demand can traverse constrained roads and shelters.",
        "A road closure may disconnect a location or increase route cost. A hospital may be geographically close but unsuitable because it lacks the required specialty, is not accepting patients or has no available bed. Evacuation throughput is constrained by road and shelter capacities and may not meet the total demand. These interacting constraints make manual comparison difficult and require clear, reproducible representations."
    ])
    subsection("1.3 Identification of Tasks", [
        "Development activities: investigate the problem and related literature; define requirements; model the directed graph and domain entities; select algorithms; implement independent algorithm modules; design the SQLite schema and deterministic seed; build Flask services and API routes; develop the browser interface and SVG visualizations; integrate and document deployment configuration.",
        "Verification activities: write unit tests for graph algorithms and edge cases; use Flask's test client for API behavior; exercise representative dispatch, route, hospital, road-closure and evacuation workflows; run the complete pytest suite; inspect the local application and screenshots; report observed limitations separately from completed features."
    ])
    table(["Work package", "Week 1", "Week 2", "Week 3", "Week 4", "Week 5", "Week 6"], [
        ("Research and requirements", "●", "●", "", "", "", ""),
        ("Graph / schema / seed design", "", "●", "●", "", "", ""),
        ("Algorithms and services", "", "", "●", "●", "", ""),
        ("API and user interface", "", "", "", "●", "●", ""),
        ("Integration and validation", "", "", "", "", "●", "●"),
        ("Report and final review", "", "", "", "", "", "●"),
    ], title="Estimated project work plan")
    figure(paths["gantt"], "Estimated project development Gantt chart (not historical)", 6.1)
    figure(paths["timeline"], "Selected milestones in algorithms and emergency coordination", 6.2)
    para("The repository history does not provide a reliable multi-week development chronology. Therefore, the schedule above is an estimated work plan, not a reconstruction of actual completion dates.")
    subsection("1.4 Timeline", [
        "Algorithmic milestones relevant to the project are presented in Figure 2. The report's development schedule is intentionally labeled estimated because the available Git history contains only a single dated repository commit and does not establish a detailed task-by-task chronology.",
        "The chosen milestones are historical context rather than a quantitative bibliometric analysis. Sources are listed in References [2]-[8]."
    ])
    subsection("1.5 Organization of the Report", [
        "Chapter 1 introduces the need, problem, tasks and schedule. Chapter 2 reviews foundational work, existing approaches and the technical problem definition. Chapter 3 documents requirements, constraints, alternative designs and the selected implementation process. Chapter 4 presents actual implementation details, algorithm examples, interface captures, measurements and test outcomes. Chapter 5 summarizes achieved work and proposes future enhancements. References, an implementation appendix and an operator-oriented user manual follow."
    ])

    # Chapter 2
    chapter(2, "Literature Review / Background Study")
    subsection("2.1 Timeline of the Reported Problem", [
        "Graph optimization has developed through several foundational strands. Kruskal's 1956 minimum-spanning-tree method formalized a greedy edge-selection approach [2]. Bellman (1958) and Ford (1956) independently developed dynamic-programming / relaxation foundations for shortest paths with negative edge costs [3, 4]. Dijkstra's 1959 shortest-path algorithm established a label-setting method for non-negative weights [5].",
        "Hart, Nilsson and Raphael introduced A* as a best-first search guided by accumulated cost and heuristic estimate in 1968 [6]. Edmonds and Karp proved a polynomial-time augmenting-path maximum-flow algorithm in 1972 [7]. Later work on intelligent transportation systems, vehicle navigation, dynamic travel costs and emergency logistics extended these graph foundations to changing, multi-criteria settings.",
        "Emergency management guidance increasingly emphasizes coordination, information exchange and incident management. ISO 22320:2018 provides incident-management guidelines [11]. This report uses it as a vocabulary reference, not as evidence of operational compliance."
    ])
    figure(paths["timeline"], "Chronological overview of selected algorithm and emergency-management milestones", 6.2)
    subsection("2.2 Existing Solutions", [
        "Static shortest-path algorithms optimize a fixed graph and non-negative weights; their results are deterministic but only as current as the supplied data. ResQNet routes by simulated time or distance.",
        "Commercial navigation combines maps, positioning and traffic feeds to adapt routes, but depends on external coverage and services. ResQNet uses no live GPS, traffic or paid routing API.",
        "Dispatch methods may jointly consider availability, travel time, coverage and workload. ResQNet instead filters its simulated fleet by capability, computes each eligible unit's ETA and selects the lowest, with ID tie-breaking.",
        "Hospital allocation can use multi-constraint ranking or global optimization. ResQNet filters one incident's options by acceptance, beds, specialty and reachability, then ranks by ETA; its severity-ordered queue remains greedy.",
        "Network-flow models represent evacuation capacity between origins and destinations. ResQNet applies Edmonds-Karp to directed road and shelter capacities, without time-expanded flow, congestion or behavioral modelling."
    ])
    subsection("2.3 Bibliometric Analysis", [
        "A citation-index dataset and publication-count extraction were not assembled. Accordingly, this section is a qualitative comparative literature analysis, not a quantitative bibliometric study. The following comparison summarizes canonical algorithm families and system approaches without inventing citation counts or claiming comparative field-wide effectiveness."
    ])
    table(["Approach", "Core technique", "Strength", "Limitation / ResQNet relevance"], [
        ("Static shortest path", "Dijkstra / A* on fixed non-negative weights", "Clear optimality under stated graph assumptions", "Needs current graph and cost; does not itself assign vehicles"),
        ("Negative-weight shortest paths", "Bellman-Ford edge relaxation", "Supports negative weights and detects reachable negative cycles", "Slower; negative travel times are not physically meaningful for the road workflow"),
        ("Dispatch optimization", "Eligibility filtering + route ETA ranking", "Operationally interpretable candidate ranking", "Single-incident greedy rule; no fleet-wide optimization"),
        ("Facility matching", "Capacity / specialty / ETA constraints", "Rejects unsuitable destinations explicitly", "No multi-patient global assignment or clinical triage model"),
        ("Evacuation network flow", "Augmenting paths / max flow", "Identifies throughput bottlenecks under capacities", "Static capacity abstraction; no time-varying demand or behavioral model"),
        ("Live navigation", "Traffic feeds + route algorithms", "Can adapt to observed conditions", "External data/services and operational validation required; outside project scope"),
    ], title="Qualitative comparison of related approaches")
    subsection("2.4 Review Summary", [
        "The literature provides robust algorithmic building blocks, but algorithmic optimality is conditional on model quality. A shortest route is optimal only for the chosen edge weights; maximum flow is optimal only for the supplied capacities and network. Real emergency coordination additionally requires reliable current data, clinical and operational protocols, resilient communications and human oversight.",
        "ResQNet contributes an educational environment in which different graph problems can be separated, visualized and tested on a reproducible city network. The comparison of Dijkstra variants, A*, traversals, spanning forests, flow and Bellman-Ford makes their assumptions and measured counters inspectable."
    ])
    subsection("2.5 Problem Definition", [
        "Let G = (V, E) be Metroville's directed graph. A vertex v ∈ V represents a location, intersection or facility. A directed edge (u,v) ∈ E represents one road direction and stores non-negative distance d(u,v), travel time t(u,v), evacuation capacity c(u,v), infrastructure cost k(u,v), and an open/closed flag. Reciprocal streets are represented by two independent directed edges; closing one direction does not implicitly close the other.",
        "Routing seeks a path P from source s to target t minimizing either Σt(u,v) or Σd(u,v), over currently open edges. Dispatch selects an available, capability-compatible ambulance with a reachable minimum-time path to an incident. Hospital recommendation filters accepting facilities with a free bed, matching specialty and reachable path, then ranks by ETA. Evacuation augments G with super-source S and sink T; zone demand arcs enter the network and shelter-capacity arcs leave it. The objective is to maximize feasible flow F from S to T.",
        "Scope excludes live traffic, GPS positioning, actual emergency dispatch, real patient data, verified clinical triage, uncertainty, time-expanded flow, and proof that model capacities correspond to real throughput. Infrastructure planning uses Kruskal on an undirected projection of open roads; it is a connectivity planning illustration, not a validated construction plan."
    ])
    subsection("2.6 Goals / Objectives", [
        "Implemented objectives include a reproducible SQLite city graph; route calculation and comparison using heap Dijkstra, array Dijkstra and A*; eligible ambulance dispatch; hospital ranking and bed reservation; road-closure rerouting; reachability and Kruskal analysis; Edmonds-Karp evacuation flow with minimum cut; trace visualization; and seeded performance benchmarks. The 16-test suite validates core algorithms and APIs. Live emergency response and real-world safety certification are out of scope."
    ])

    # Chapter 3
    chapter(3, "Design Flow / Process")
    subsection("3.1 Evaluation and Selection of Specifications / Features", [
        "Requirements were evaluated for academic algorithm coverage, reproducibility, safety boundaries, implementability without external services and observable user workflows. Status refers to the inspected implementation and browser/test evidence."
    ])
    table(["ID", "Requirement", "Priority", "Status / evidence"], [
        ("FR-01", "Seed deterministic city locations, directed roads, facilities and scenarios", "High", "Implemented; 36 locations / 120 roads"),
        ("FR-02", "Compute route by time or distance with Dijkstra heap / array or A*", "High", "Implemented and tested"),
        ("FR-03", "Dispatch available capable ambulance by ETA", "High", "Implemented; transactional persistence"),
        ("FR-04", "Recommend hospital by eligibility and route ETA", "High", "Implemented; bed reservation workflow"),
        ("FR-05", "Close / reopen road and use updated graph snapshots", "High", "Backend and route workflow implemented"),
        ("FR-06", "Evacuation max flow with capacities and min cut", "High", "Implemented and tested"),
        ("FR-07", "Traversal / connectivity / infrastructure analysis", "Medium", "Algorithms and API implemented; form submission issue observed"),
        ("FR-08", "Trace algorithm and show counters", "Medium", "Implemented for supported algorithms"),
        ("FR-09", "Benchmark repeated runs on seeded graphs", "Medium", "Implemented; measured growth sweep"),
        ("NFR-01", "Run locally without external APIs or keys", "High", "Implemented"),
        ("NFR-02", "Use persistent SQLite with consistency checks", "High", "Implemented"),
        ("NFR-03", "Be safe to interpret as real emergency guidance", "High", "Simulation disclaimer present; never operationally certified"),
        ("NFR-04", "Usable interactive visual interface", "Medium", "Implemented; UI form defect in connectivity source selector"),
    ], title="Requirements and implementation status")
    subsection("3.2 Design Constraints", [
        "Technical: a single-process Flask application and SQLite database suit a compact academic demonstration but are not designed for high concurrency, multi-region failover or large-scale real-time routing. A directed edge snapshot is in-memory for each service calculation. Benchmark times are machine/runtime-specific.",
        "Economic and environmental: Python, Flask, SQLite and browser-native technologies minimize license and infrastructure costs. The application has no external mapping or AI API dependency. No claim is made about measured energy consumption or environmental benefit.",
        "Health, safety and ethical: this is a simulation, not a certified emergency-dispatch or navigation system. Results must not guide a real incident. The fictional network and capacities are not safety-calibrated. No actual patient-identifying information is needed or included.",
        "Social and operational: simulated resources do not represent actual service availability, local language requirements, accessibility needs or institutional command structures. Human oversight and local emergency protocols would be indispensable in any real deployment.",
        "Security and privacy: the project uses local simulation data and avoids live personal records. It is not a security-certified system; deployment would need authentication, authorization, transport security, logging policy, threat analysis and data retention controls.",
        "Deployment and persistence: Render configuration specifies a persistent-disk mount for SQLite. A local demo is persistent on disk, but deploy platform behavior and operational backup/recovery require separate validation. The app has no external service-level guarantee."
    ])
    subsection("3.3 Analysis of Features and Finalization Subject to Constraints", [
        "Features were retained when they demonstrated a distinct algorithmic problem with measurable inputs and outputs. A* and Dijkstra use travel-time/distance weights; maximum flow uses capacity and is not conflated with route cost. Bellman-Ford is kept in an educational sandbox rather than applying negative weights to physical travel. Dynamic road changes are modeled as open/closed edge state, not as live traffic.",
        "Live maps, traffic, GPS, real dispatch integrations, clinical decision rules and AI prediction were excluded because they would require external data, safety validation and privacy/operational governance beyond this academic scope. The connectivity form's missing `source` field name was discovered during manual UI verification and is disclosed as an implementation defect."
    ])
    table(["Feature", "Decision", "Reason / status"], [
        ("Deterministic grid dataset", "Include", "Reproducible algorithm demonstrations"),
        ("Actual dispatch and bed reservation", "Include", "Shows business rules plus transactional state"),
        ("Road closure rerouting", "Include", "Tests graph snapshot changes"),
        ("Maximum-flow evacuation", "Include", "Distinct capacity optimization problem"),
        ("Live maps and traffic", "Exclude", "No external APIs; no real-world feeds"),
        ("Global hospital queue optimization", "Defer", "Current algorithm is greedy, not globally optimal"),
        ("Connectivity user form", "Partial", "Backend works; UI source selector missing submitted name"),
        ("Real emergency deployment", "Exclude", "Not certified or validated for operational use"),
    ], title="Feature evaluation and scope decisions")
    subsection("3.4 Design Flow", [
        "Two alternatives were considered. Alternative 1 places UI handling, rules, graph algorithms and persistence in a monolithic application unit. It reduces initial scaffolding but makes algorithm isolation, testing and change-impact control more difficult. Alternative 2 separates the browser, API, services, pure algorithms and SQLite repository. The latter introduces modest module boundaries but matches the project's need to demonstrate algorithms independently and connect each algorithm to a business workflow."
    ])
    figure(paths["monolithic"], "Alternative 1: monolithic application structure", 6.0)
    figure(paths["modular"], "Alternative 2: modular Flask architecture", 6.0)
    subsection("3.5 Design Selection", [
        "The implemented application follows the modular alternative: algorithm functions accept in-memory inputs; services load graph snapshots and coordinate domain workflows; database modules own schema and repository operations; Flask routes validate and serialize; browser code renders returned data. This choice supports unit testing of algorithms, explicit workflow rules and traceable API behavior."
    ])
    table(["Criterion", "Monolithic", "Modular implementation"], [
        ("Modularity", "Low; concerns tightly coupled", "High; algorithms, services, API and persistence separated"),
        ("Testing", "More setup for isolated algorithms", "Pure algorithms independently testable"),
        ("Maintainability", "Changes have broad impact", "Boundaries localize changes"),
        ("Initial effort", "Lower", "Moderate"),
        ("Scale-out", "Limited", "Still a compact monolith at deployment; boundaries ease later extraction"),
        ("ADSA suitability", "Algorithm internals harder to isolate", "Strong; algorithms are directly inspectable and measurable"),
    ], title="Architecture alternatives comparison")
    subsection("3.6 Implementation Plan / Methodology", [
        "Overall architecture and API workflow are shown in Figures 6 and 7. A service reads a consistent SQLite snapshot, constructs an adjacency mapping of open edges, calls an independent algorithm and returns JSON. State-changing workflows use transaction boundaries and conditional updates where necessary."
    ])
    figure(paths["architecture"], "Overall implemented ResQNet architecture", 6.1)
    figure(paths["usecase"], "Use-case view for a simulation operator", 6.1)
    figure(paths["workflow"], "System request and result workflow", 6.1)
    figure(paths["graph"], "Seed graph and directed road representation", 6.0)
    figure(paths["erd"], "SQLite entity model (selected fields and relationships)", 6.4)
    figure(paths["api"], "API request lifecycle and validation path", 6.1)
    heading("Graph and database model", 3)
    para("The `locations` table stores stable IDs, location types and coordinates. `roads` references source and target locations and enforces positive distance/travel time, non-negative capacity and unique direction pairs. Operational tables include ambulances, hospitals, shelters and incidents; dispatch records and hospital allocations capture workflow outcomes. Evacuation, benchmark and algorithm runs store JSON result payloads. Foreign keys, indexes and transaction helpers support consistency. Bidirectional streets are two rows.")
    heading("Dispatch and care workflow", 3)
    figure(paths["dispatch"], "Dispatch eligibility, route ranking and assignment flow", 5.9)
    figure(paths["hospital"], "Hospital recommendation and reservation flow", 5.9)
    para("Dispatch filters to available ambulances with no assigned incident, checks requested capabilities, runs time-weighted Dijkstra from each unit to the incident, removes unreachable candidates and orders by ETA then ID. Confirmation conditionally updates both incident and unit, records the route and commits. Hospital recommendations filter accepting status, bed availability, specialty and reachability, then rank by ETA, available beds descending and ID. Reservation checks capacity and incident allocation within a transaction. The batch queue orders incidents by severity and time but uses a greedy per-incident choice.")
    heading("Routing, evacuation and infrastructure methodology", 3)
    figure(paths["routing"], "Shortest-path service and route reconstruction", 5.9)
    figure(paths["evacuation"], "Evacuation network construction and max-flow workflow", 5.9)
    figure(paths["closure"], "Road closure and subsequent route recalculation", 5.9)
    para("The evacuation service adds a super-source edge to each zone with capacity equal to population demand, uses each currently open directed road's evacuation capacity, and adds a shelter-to-super-sink edge bounded by shelter capacity. Edmonds-Karp returns maximum flow, augmenting paths, used capacities and residual-reachability minimum cut. The capacities are simulated people per configured period, not measured road throughput.")
    heading("Testing and deployment methodology", 3)
    para("Unit tests cover algorithm outputs, invalid inputs, disconnected graphs, negative weights/cycles, residual reverse edges, min-cut equality and boundary cases. Flask test-client tests exercise API validation and service integration. Browser workflows were manually captured. The WSGI entry point uses Flask and the deployment manifest configures Gunicorn and persistent storage; local testing does not establish production reliability.")

    # Chapter 4
    chapter(4, "Results Analysis and Validation")
    subsection("4.1 Implementation of Solution", [
        "This chapter reports results from the inspected source, local test suite, test-client workflows, and authentic captures of the running interface. Execution evidence is machine-specific, and all incident/transport data are simulated."
    ])
    heading("4.1.1 Development Environment", 2)
    para("The verified local environment used Python 3.14.3, Flask 3.1.3, pytest 8.4.2, SQLite, Windows, and Microsoft Word 16 for document rendering. The source targets Python 3.10+ and uses Flask, SQLite, Gunicorn, pytest, HTML, CSS, vanilla JavaScript and SVG. No external API key or frontend build system is required.")
    heading("4.1.2 Graph Representation", 2)
    para("The seed generator creates a 6-by-6 grid of M01–M36. Each adjacent horizontal or vertical pair becomes two separate directed roads, producing 120 edge rows. Coordinates are deterministic. For the captured route query M01→M36, heap Dijkstra returned M01 → M02 → M08 → M09 → M15 → M21 → M22 → M28 → M29 → M35 → M36, with total 20.5 minutes and 14.2 km. The route has 10 segments.")
    table(["Entity", "Count", "Representation / note"], [
        ("Locations", "36", "Stable IDs M01-M36; 6 x 6 grid"),
        ("Directed roads", "120", "Two directions stored independently"),
        ("Ambulances", "8", "Availability and capabilities"),
        ("Hospitals", "6", "Beds, specialties, acceptance status"),
        ("Shelters", "6", "Configured capacity"),
        ("Training incidents", "2", "Fictional seed scenarios"),
    ], title="Deterministic Metroville seed inventory")
    heading("4.1.3 Database Implementation", 2)
    para("SQLite schema uses locations, roads, ambulances, hospitals, shelters, incidents, dispatch_records, hospital_allocations, evacuation_runs, benchmark_runs, algorithm_runs and simulation_events. Constraints include foreign keys, enumerated unit states, non-negative capacities, valid occupied-bed bounds and unique directed road pairs. The application factory initializes the schema and deterministic seed when empty.")
    heading("4.1.4 Algorithm Implementations", 2)
    heading("Dijkstra with binary heap", 3)
    para("Input is an adjacency mapping from vertex IDs to Edge values containing target, time, distance and capacity. The algorithm initializes distance to infinity, predecessor to null and a min-heap with the source. It discards stale queue entries, settles the minimum-cost node, relaxes outgoing edges and reconstructs the path through predecessors. Non-negative selected weights are required. Complexity is O((V + E) log V) with a binary heap and adjacency lists; auxiliary state is O(V + E). It is used by route, dispatch and hospital services.")
    para("Example: for M01→M36 using time weights, the path and cost are given in §4.1.2. In one captured run, 118 edge checks, 35 successful relaxations, 36 settled nodes and 71 heap operations were reported; measured execution was 0.0653 ms. This timing is an observation, not a guarantee.")
    heading("Dijkstra with array minimum selection", 3)
    para("The array variant maintains a set of unvisited vertices and selects the minimum tentative distance by scanning it each iteration. Relaxation and predecessor reconstruction match the heap variant. Its time complexity is O(V² + E), commonly O(V²) for adjacency-list use with linear minimum selection, with O(V + E) storage. It is useful for independent comparison and can be competitive for dense/small graphs. The Metroville comparison returned the same cost 20.5 as heap Dijkstra.")
    heading("A* Search", 3)
    para("A* orders its heap by f(n)=g(n)+h(n). The implementation computes great-circle distance using Haversine coordinates. For distance mode, its heuristic uses the minimum observed road-distance / straight-line ratio; for time mode, it uses straight-line distance divided by maximum observed geometric road speed. This scales the geographic lower bound to remain admissible for the edge attributes. If coordinates or non-negative weights are absent, it rejects the input. Worst-case search can be exponential in general; performance depends on graph and heuristic, with O(V+E) memory in this implementation. It is validated against Dijkstra on fixtures.")
    heading("BFS and DFS", 3)
    para("BFS uses a FIFO deque and DFS an explicit LIFO stack to enumerate vertices reachable along directed outgoing edges. Both return visitation order and sorted unreachable locations in O(V+E) time and O(V) auxiliary memory. `connected_components` separately constructs an undirected projection and traverses it, so it reports weak-style connectivity for a directed road dataset rather than strongly connected components. From M01, BFS reached all 36 seeded locations.")
    heading("Kruskal minimum spanning forest", 3)
    para("The implementation normalizes reciprocal road directions into unordered endpoint pairs, retains the lowest-weight direction for each pair, sorts candidates, and uses a disjoint-set structure with path halving and union by size. It returns a forest, excluded edges, total selected weight and component sets. Complexity is O(E log E) for sorting plus near-constant amortized DSU operations; storage is O(V+E). Open seeded roads produced 35 edges, one component and total distance 47.4 km in the evidence run. It is an undirected connectivity abstraction, not a route or construction recommendation.")
    heading("Edmonds-Karp maximum flow", 3)
    para("The flow algorithm accepts a node list, directed capacity edges, source and sink. It aggregates capacities into a residual matrix and maintains adjacency including reverse residual edges. BFS searches a shortest-in-edges augmenting path; the bottleneck is subtracted from forward residual capacity and added to reverse capacity. When no path remains, residual reachability partitions a minimum cut. Time complexity is O(VE²); this matrix implementation uses O(V²+E) memory. The result includes augmentations, edge checks, used capacities, maximum flow and minimum cut.")
    para("The canonical unit-test network returned a maximum flow of 23 and a minimum-cut capacity of 23. In the actual Metroville test-client scenario, demand was 550, maximum flow 480, and unserved demand 70. Four augmentations had bottlenecks 165, 135, 125 and 55; the reported minimum cut consisted of 220- and 260-capacity shelter arcs, totaling 480. The service explicitly labels this as simulated throughput.")
    heading("Bellman-Ford", 3)
    para("Bellman-Ford is implemented in a separate educational graph sandbox. It repeatedly relaxes each edge for up to V−1 rounds, stops early if unchanged, then checks for a source-reachable negative cycle and marks downstream affected distances as negative infinity. It runs in O(VE) time and O(V+E) storage. Tests validate a negative-edge shortest path and a reachable negative cycle. It is not used for physical road travel, because negative travel time/distance is invalid.")
    heading("4.1.5 Emergency Dispatch Implementation", 2)
    para("The captured dispatch for incident 1 selected AMB-07 with ETA 10.4 minutes and 7.2 km over route M33 → M27 → M21 → M22 → M16 → M17. Eligibility and routing are recomputed from currently available units and open roads. The captured interface workflow persisted the dispatch, leaving one ambulance assigned in that test database. Completion or cancellation releases the assigned unit; transitions are explicitly checked.")
    heading("4.1.6 Route Optimization Implementation", 2)
    para("For M01→M36, Dijkstra heap chose M01 → M02 → M08 → M09 → M15 → M21 → M22 → M28 → M29 → M35 → M36. Cost was 20.5 minutes with 14.2 km total distance. The heap, array and A* comparison returned the same 20.5-minute cost in the recorded comparison. The algorithms use a consistent graph snapshot; route segments are reconstructed from predecessor links and their road attributes are summed.")
    heading("4.1.7 Hospital Allocation Implementation", 2)
    para("For the captured trauma incident at M17, H-03 (Metroville Medical Center 3 at M14) was recommended at 6.7 minutes with 56 beds available. H-02, H-04 and H-06 were rejected for missing trauma specialty. H-05 and H-01 remained eligible but had longer ETAs. The browser workflow reserved one bed at H-03. Recommendation is not clinical triage, and queue assignment is greedy.")
    heading("4.1.8 Dynamic Road Management", 2)
    para("Closing directed road 1 changed the M01→M06 route from M01-M02-M03-M04-M05-M06 (11.5 minutes) to M01-M07-M08-M09-M10-M11-M12-M06 (15.9 minutes). Routing snapshots omit closed roads while the network view can show them blocked. The reciprocal direction remains independent. A UI defect was found during manual inspection: the Network Manager connectivity form's source selector lacks the submitted field name, causing its connectivity request to fail with HTTP 400 ('Missing required field(s): source'). The underlying connectivity service and API test pass when valid input is sent directly.")
    heading("4.1.9 Evacuation Simulation", 2)
    para("In the recorded test-client configuration, zones at M03 and M17 supplied total demand 550 and selected shelter capacities formed the sink arcs. The maximum flow was 480, leaving 70 unserved under the configured capacities. The min-cut capacity also equaled 480, validating max-flow/min-cut equality for this execution. Reported selected augmenting paths and cut are model results, not evacuation guidance.")
    heading("4.1.10 Algorithm Visualization", 2)
    para("The frontend receives trace events produced by backend algorithms and animates visited nodes and distance updates on the SVG graph. For a Dijkstra trace the evidence contained 71 events; the first events visited M01 and updated M02 and M07. The visual layer does not independently compute routes. Screenshots in §4.1.12 are authentic captures of the running interface.")
    heading("4.1.11 Performance Analysis", 2)
    para("A seeded benchmark growth sweep used graph sizes 25, 50, 100, 250 and 500, average degree 4, random seed 42 and three repetitions. Each algorithm was warmed up; timings are medians, tracing disabled. The generated undirected pairs are represented as directed edges. The following are captured local measurements in milliseconds and edge checks.")
    benchmark_rows = []
    for n in sorted(benchmark_data):
        d = benchmark_data[n]
        a = d["algorithms"]
        benchmark_rows.append((n, d["edge_count"],
                               f"{a['dijkstra_heap']['median_ms']:.4f} / {a['dijkstra_heap']['edge_checks']}",
                               f"{a['dijkstra_array']['median_ms']:.4f} / {a['dijkstra_array']['edge_checks']}",
                               f"{a['astar']['median_ms']:.4f} / {a['astar']['edge_checks']}",
                               f"{a['bellman_ford']['median_ms']:.4f} / {a['bellman_ford']['edge_checks']}"))
    table(["Vertices", "Directed edges", "Dijkstra heap", "Dijkstra array", "A*", "Bellman-Ford"],
          benchmark_rows, font=7.6, title="Benchmark medians (milliseconds / edge checks)")
    figure(paths["benchmark"], "Measured benchmark growth sweep (log scale)", 6.1)
    para("The data show the array implementation's selection overhead becoming more visible at larger sizes, while Bellman-Ford's edge checks grow across repeated relaxations. Heap and array Dijkstra have identical edge-check counts on these cases because the shortest-path instances share the same graph and route target; A* does not necessarily reduce work when its heuristic is weak. Results vary with CPU, Python build, process load, graph generation and seed; the chart is not a cross-hardware performance claim.")
    heading("4.1.12 Testing and Validation", 2)
    para("The complete pytest run executed 16 tests and passed all 16 (0 failures) in 2.07 seconds. The tests cover heap/array Dijkstra path agreement and unreachable/negative cases; A* agreement and lower bounds; BFS/DFS and components; Kruskal forest and DSU; Edmonds-Karp known flow, reverse residual edges and min cut; Bellman-Ford negative edges/cycles; and API/service workflows in the API test module.")
    table(["Verification level", "Observed result", "Evidence / note"], [
        ("Algorithm unit tests", "Passed", "Shortest paths, traversal, DSU/MST, flow, Bellman-Ford"),
        ("API / integration tests", "Passed within suite", "Flask test client; input and workflow checks"),
        ("Full automated suite", "16 passed, 0 failed", "pytest -q; 2.07 seconds"),
        ("Manual browser workflows", "Representative workflows completed", "Dispatch, hospital reservation, evacuation, Dijkstra trace and benchmarks"),
        ("Connectivity UI form", "Failed in manual UI check", "Missing source field name; HTTP 400"),
    ], title="Verification summary")
    heading("4.1.13 Application Interface Screenshots", 2)
    para("The following ten images are authentic captures from the locally running application. They were cropped to the application viewport for legibility; no interface content was fabricated.")
    screenshot_data = [
        ("overview.jpg", "Command overview and simulated network KPIs"),
        ("map.jpg", "Metroville SVG city network"),
        ("dispatch.jpg", "Simulated incident dispatch center"),
        ("routes.jpg", "Route optimization panel"),
        ("hospitals.jpg", "Hospital recommendation and allocation panel"),
        ("evacuation.jpg", "Capacity-based evacuation planner"),
        ("lab.jpg", "Algorithm trace and visualization lab"),
        ("benchmark.jpg", "Algorithm benchmarking interface"),
        ("network.jpg", "Network management interface"),
        ("analytics.jpg", "Simulation analytics"),
    ]
    for filename, title in screenshot_data:
        source = SHOTS / "cropped" / filename
        if source.exists():
            figure(source, title, 5.65)

    # Chapter 5
    chapter(5, "Conclusion and Future Work")
    subsection("5.1 Conclusion", [
        "ResQNet demonstrates how fundamental graph algorithms can be connected to recognizable emergency-response and evacuation-planning workflows in a self-contained academic application. It models a deterministic fictional city as a directed weighted graph, persists simulated resources and events in SQLite, exposes workflows through Flask, and visualizes returned results in a vanilla JavaScript/SVG interface.",
        "Implemented algorithms include two Dijkstra variants, A*, BFS, DFS, Kruskal with DSU, Edmonds-Karp and Bellman-Ford. The service layer uses them for route calculation, ambulance ETA ranking, hospital recommendations, road-closure rerouting, connectivity analysis, infrastructure connectivity planning and capacity-limited evacuation. The local automated suite passed 16 tests. Captured executions demonstrated matching shortest-path costs, a dispatch selection, an eligible hospital recommendation, a 480-unit maximum flow against demand 550, and measured growth trends.",
        "These outcomes meet the academic objectives of implementing, instrumenting and validating multiple algorithmic techniques in an integrated application. They do not establish better real-world emergency outcomes. Expected outcomes were interactive, reproducible demonstrations; actual outcomes include those workflows and a manual connectivity-form defect. All measurements are simulation-specific and hardware-dependent."
    ])
    subsection("5.2 Future Work", [
        "Correct the Network Manager connectivity selector field name and add a browser regression test for the submitted source and algorithm fields.",
        "Expand tests for transaction rollback, concurrent dispatch races, hospital capacity races, directed disconnection and invalid flow networks.",
        "Improve benchmark methodology with repeated independent seeds, warm-up disclosure, confidence intervals, larger graph profiles and exportable raw measurements; keep machine/runtime metadata with every run.",
        "Add globally optimized multi-incident hospital assignment (for example, a clearly specified matching/min-cost-flow model), while retaining the current greedy workflow as a baseline.",
        "Explore time-dependent routing and time-expanded evacuation models, uncertainty and risk costs; explicitly validate assumptions before interpreting results.",
        "For any real-world research adaptation, obtain domain-expert review, validated geographic/traffic/capacity data, threat and privacy assessment, accessibility requirements, human-factors studies, and formal safety, security and operational validation. Such work would be a separate project, not a configuration change."
    ])

    # References
    doc.add_page_break()
    heading("REFERENCES", 1)
    references = [
        "[1] World Health Organization, Global Status Report on Road Safety 2023, Geneva: WHO, 2023. https://www.who.int/publications/i/item/9789240086517",
        "[2] J. B. Kruskal, “On the Shortest Spanning Subtree of a Graph and the Traveling Salesman Problem,” Proceedings of the American Mathematical Society, vol. 7, no. 1, pp. 48–50, 1956. doi:10.1090/S0002-9939-1956-0078686-7.",
        "[3] R. Bellman, “On a Routing Problem,” Quarterly of Applied Mathematics, vol. 16, no. 1, pp. 87–90, 1958. doi:10.1090/qam/102435.",
        "[4] L. R. Ford Jr., Network Flow Theory, RAND Corporation Paper P-923, 1956.",
        "[5] E. W. Dijkstra, “A Note on Two Problems in Connexion with Graphs,” Numerische Mathematik, vol. 1, pp. 269–271, 1959. doi:10.1007/BF01386390.",
        "[6] P. E. Hart, N. J. Nilsson, and B. Raphael, “A Formal Basis for the Heuristic Determination of Minimum Cost Paths,” IEEE Transactions on Systems Science and Cybernetics, vol. 4, no. 2, pp. 100–107, 1968. doi:10.1109/TSSC.1968.300136.",
        "[7] J. Edmonds and R. M. Karp, “Theoretical Improvements in Algorithmic Efficiency for Network Flow Problems,” Journal of the ACM, vol. 19, no. 2, pp. 248–264, 1972. doi:10.1145/321694.321699.",
        "[8] T. H. Cormen, C. E. Leiserson, R. L. Rivest, and C. Stein, Introduction to Algorithms, 4th ed., MIT Press, 2022.",
        "[9] ISO/IEC 25010:2023, Systems and software engineering — Systems and software Quality Requirements and Evaluation (SQuaRE) — Product quality model, International Organization for Standardization, 2023. https://www.iso.org/standard/78176.html",
        "[10] ISO/IEC/IEEE 29148:2018, Systems and software engineering — Life cycle processes — Requirements engineering, ISO, 2018. https://www.iso.org/standard/72089.html",
        "[11] ISO 22320:2018, Security and resilience — Emergency management — Guidelines for incident management, ISO, 2018. https://www.iso.org/standard/67851.html",
        "[12] ResQNet source code, deterministic database seed, tests and execution evidence, inspected locally for this report, November 2026.",
        "[13] National Disaster Management Authority, Government of India, National Disaster Management Plan, 2019. https://ndma.gov.in/sites/default/files/PDF/ndmp-2019.pdf",
        "[14] Chandigarh University, official website branding asset, https://www.cuchd.in/home-assets/img/logo.png (accessed 14 November 2026).",
    ]
    for item in references:
        p = doc.add_paragraph(item)
        p.paragraph_format.left_indent = Inches(.25)
        p.paragraph_format.first_line_indent = Inches(-.25)
        p.paragraph_format.space_after = Pt(5)

    # Appendices / manual
    doc.add_page_break()
    heading("APPENDIX A — IMPLEMENTATION AND TEST EVIDENCE", 1)
    para("The report's primary implementation evidence consists of the algorithm source modules under backend/algorithms/, services under backend/services/, SQLite schema and deterministic seed under backend/database/ and backend/data/, Flask API routes, frontend JavaScript/SVG panels, test modules and the captured execution_evidence.json in docs/report/report_generation/.")
    table(["Module", "Responsibility"], [
        ("backend/algorithms/dijkstra.py", "Heap and array shortest-path variants"),
        ("backend/algorithms/astar.py", "A* and Haversine lower-bound heuristic"),
        ("backend/algorithms/traversal.py", "BFS, DFS and undirected connectivity components"),
        ("backend/algorithms/kruskal.py", "Kruskal minimum spanning forest and DSU"),
        ("backend/algorithms/edmonds_karp.py", "Residual matrix, max flow and minimum cut"),
        ("backend/algorithms/bellman_ford.py", "Educational negative-weight shortest paths"),
        ("backend/services/", "Routing, dispatch, hospital, network, evacuation, analytics"),
        ("backend/database/database.py", "SQLite schema and connection lifecycle"),
        ("backend/data/seed.py", "Deterministic Metroville seed and reset"),
        ("tests/", "Algorithm and Flask API tests"),
    ], title="Key source modules and responsibilities")
    heading("APPENDIX B — USER MANUAL", 1)
    heading("B.1 Installation and startup", 2)
    para("Install Python 3.10 or later. From the project root, create and activate a virtual environment, install requirements.txt, then run `python run.py`. Open the local URL printed by Flask. The app initializes SQLite and seeds Metroville on first start. `RESQNET_DATABASE` can be set to choose a database location.")
    heading("B.2 Dashboard and map", 2)
    para("Use the overview to inspect simulated counts and recent activity. Open City Map to view locations, facility markers, directed roads and closed-road styling. The schematic map is not geographic navigation.")
    heading("B.3 Dispatch and incident status", 2)
    para("Select or create a simulated incident, request dispatch options, inspect ranked ambulance ETA choices, then confirm dispatch. Use permitted status transitions to progress the incident. Resolve or cancel to release the simulated unit. No real emergency response is contacted.")
    heading("B.4 Routing and algorithm lab", 2)
    para("Choose source, destination, metric (time/distance) and algorithm. Compare Dijkstra heap, Dijkstra array and A*. Inspect route, cost, edge checks and relaxations. Enable trace in the lab to review the returned event sequence. Bellman-Ford examples belong to the educational graph sandbox and do not alter road travel data.")
    heading("B.5 Hospital recommendation", 2)
    para("Request recommendations for a simulated incident. The system filters for acceptance, open-road reachability, free beds and any required specialty. Confirm an eligible facility to reserve a bed. The ranking is algorithmic and not clinical advice.")
    heading("B.6 Evacuation", 2)
    para("Select at least one evacuation zone and one shelter, enter positive integer zone populations and optional non-negative selected-shelter capacity overrides, then run the simulation. Review maximum flow, unserved demand, augmenting paths, capacity use and min cut. Values are hypothetical.")
    heading("B.7 Network, analytics, reset and safety", 2)
    para("The Network Manager edits roads, closes/reopens links, and exposes connectivity and infrastructure analysis. Its connectivity form omits the required source field and returns HTTP 400; valid API calls work. Analytics show simulated history. Reset demo data to restore the seed. Never enter patient data or use output for real emergencies.")

    # Metadata, table captions sequence categories and save.
    doc.core_properties.title = "ResQNet — Intelligent Emergency Response & Disaster Evacuation Optimization System"
    doc.core_properties.subject = "ADSA academic project report"
    doc.core_properties.author = "J Srikar"
    doc.core_properties.keywords = "ResQNet, graph algorithms, ADSA, emergency simulation"
    out = OUT / "ResQNet_Project_Report.docx"
    doc.save(out)
    print(f"Saved {out}")
    print(f"Figures: {FIGURES}; tables: {TABLES}; benchmark sizes: {sorted(benchmark_data)}")


if __name__ == "__main__":
    build()
