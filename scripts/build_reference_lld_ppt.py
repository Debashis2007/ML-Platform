#!/usr/bin/env python3
"""Faithful replica of AWS guidance LLD reference diagram layout.

Outputs ML_Platform_Consolidated_LLD.pptx — visual match to reference slide.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent / "lib"))

from pptx.dml.color import RGBColor
from pptx.enum.dml import MSO_LINE_DASH_STYLE
from pptx.enum.shapes import MSO_CONNECTOR, MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.oxml.ns import qn
from pptx.util import Inches, Pt

from aws_diagram_style import ABBR_TO_ICON_KEY, ICON_FILES, ICON_ROOT
from ppt_branding import (
    BLANK_LAYOUT,
    BODY,
    FONT,
    SLATE,
    WHITE,
    add_footer,
    add_title_bar,
    new_presentation,
    post_process_pptx,
)

OUT = ROOT / "assets" / "ML_Platform_Consolidated_LLD.pptx"

NAVY = RGBColor(0x1C, 0x1C, 0x1C)
BLUE = RGBColor(0x1D, 0x4E, 0xD8)
BLUE_LT = RGBColor(0xDB, 0xEA, 0xFE)
BLUE_NUM = RGBColor(0x25, 0x63, 0xEB)
TEAL_LT = RGBColor(0xCC, 0xFB, 0xF1)
PINK = RGBColor(0xFC, 0xE7, 0xF3)
GRAY = RGBColor(0xE5, 0xE7, 0xEB)
GRAY_BG = RGBColor(0xF3, 0xF4, 0xF6)
GREEN_LT = RGBColor(0xD1, 0xFA, 0xE5)
ORANGE_LT = RGBColor(0xFF, 0xED, 0xD5)
YEL = RGBColor(0xFE, 0xF3, 0xC7)
LAV = RGBColor(0xED, 0xE9, 0xFE)
CLOUD_BG = RGBColor(0xFA, 0xFB, 0xFC)
DEV_BORDER = RGBColor(0x1D, 0x4E, 0xD8)
PROD_BORDER = RGBColor(0xC2, 0x41, 0x0C)
ARROW = RGBColor(0x33, 0x41, 0x55)
INSET = 0.015
NUM_D = 0.19


def _rect(slide, l, t, w, h, fc, ec=NAVY, lw=0.8, dashed=False, rounded=False):
    sh = MSO_SHAPE.ROUNDED_RECTANGLE if rounded else MSO_SHAPE.RECTANGLE
    s = slide.shapes.add_shape(sh, Inches(l), Inches(t), Inches(w), Inches(h))
    s.fill.solid()
    s.fill.fore_color.rgb = fc
    s.line.color.rgb = ec
    s.line.width = Pt(lw)
    s.shadow.inherit = False
    if dashed:
        s.line.dash_style = MSO_LINE_DASH_STYLE.DASH
    if rounded:
        s.adjustments[0] = 0.08
    return s


def _txt(slide, l, t, w, h, text, sz=7.5, color=BODY, bold=False, align=PP_ALIGN.LEFT, valign=MSO_ANCHOR.TOP):
    b = slide.shapes.add_textbox(Inches(l), Inches(t), Inches(max(0.15, w)), Inches(max(0.10, h)))
    tf = b.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = valign
    tf.text = text
    for p in tf.paragraphs:
        p.alignment = align
        for r in p.runs:
            r.font.size = Pt(sz)
            r.font.color.rgb = color
            r.font.bold = bold
            r.font.name = FONT
    return b


def _icon(slide, l, t, size, abbr):
    key = ABBR_TO_ICON_KEY.get(abbr)
    rel = ICON_FILES.get(key) if key else None
    path = ICON_ROOT / rel if rel else None
    if path and path.exists():
        slide.shapes.add_picture(str(path), Inches(l), Inches(t), width=Inches(size), height=Inches(size))
        return size
    _rect(slide, l, t, size, size, RGBColor(0x4F, 0x00, 0xCA), RGBColor(0x4F, 0x00, 0xCA), 0.4)
    _txt(slide, l, t, size, size, abbr, sz=max(5, size * 14), color=WHITE, bold=True, align=PP_ALIGN.CENTER, valign=MSO_ANCHOR.MIDDLE)
    return size


def _chip(slide, l, t, w, h, abbr, label, fc=WHITE, fs=6.0, icon_left=False):
    _rect(slide, l, t, w, h, fc, NAVY, 0.55)
    iz = min(0.28, max(0.14, h - 0.18))
    if icon_left and w >= 0.55:
        _icon(slide, l + 0.04, t + (h - iz) / 2, iz, abbr)
        _txt(slide, l + iz + 0.06, t + 0.02, w - iz - 0.08, h - 0.04, label, sz=fs, bold=True, color=NAVY, valign=MSO_ANCHOR.MIDDLE)
    else:
        _icon(slide, l + (w - iz) / 2, t + 0.03, iz, abbr)
        _txt(slide, l + 0.02, t + iz + 0.02, w - 0.04, h - iz - 0.05, label, sz=fs, bold=True, color=NAVY, align=PP_ALIGN.CENTER, valign=MSO_ANCHOR.MIDDLE)


def _arrow(slide, x1, y1, x2, y2, dashed=False, color=ARROW, w=1.1):
    c = slide.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, Inches(x1), Inches(y1), Inches(x2), Inches(y2))
    c.line.color.rgb = color
    c.line.width = Pt(w)
    if dashed:
        c.line.dash_style = MSO_LINE_DASH_STYLE.DASH
    ln = c.line._get_or_add_ln()
    ln.append(ln.makeelement(qn("a:tailEnd"), {"type": "triangle", "w": "sm", "len": "sm"}))
    return c


def _num(slide, l, t, n):
    s = slide.shapes.add_shape(MSO_SHAPE.OVAL, Inches(l), Inches(t), Inches(NUM_D), Inches(NUM_D))
    s.fill.solid()
    s.fill.fore_color.rgb = BLUE_NUM
    s.line.fill.background()
    _txt(slide, l, t, NUM_D, NUM_D, str(n), sz=7, color=WHITE, bold=True, align=PP_ALIGN.CENTER, valign=MSO_ANCHOR.MIDDLE)


def _flow(slide, x1, y1, x2, y2, n, dashed=False):
    _arrow(slide, x1, y1, x2, y2, dashed=dashed)
    _num(slide, (x1 + x2) / 2 - NUM_D / 2, (y1 + y2) / 2 - NUM_D / 2 - 0.06, n)


def _persona(slide, l, t, label):
    s = slide.shapes.add_shape(MSO_SHAPE.OVAL, Inches(l), Inches(t), Inches(0.22), Inches(0.22))
    s.fill.solid()
    s.fill.fore_color.rgb = LAV
    s.line.color.rgb = NAVY
    s.line.width = Pt(0.6)
    _txt(slide, l - 0.05, t + 0.24, 0.32, 0.28, label, sz=5.5, color=NAVY, align=PP_ALIGN.CENTER)


def _pipe_row(slide, x, y, w, h, title, steps, nums):
    _rect(slide, x, y, w, h, WHITE, NAVY, 0.65)
    _txt(slide, x + 0.04, y + 0.01, w - 0.08, 0.12, title, sz=6.5, bold=True, color=NAVY)
    sy, sh = y + 0.14, h - 0.16
    gap = 0.06
    sw = (w - 0.10 - gap * (len(steps) - 1)) / len(steps)
    sx = x + 0.05
    mids = []
    for i, (lab, fc) in enumerate(steps):
        if lab == "◆":
            d = slide.shapes.add_shape(MSO_SHAPE.DIAMOND, Inches(sx), Inches(sy + 0.04), Inches(sw), Inches(sh - 0.08))
            d.fill.solid()
            d.fill.fore_color.rgb = ORANGE_LT
            d.line.color.rgb = NAVY
            d.line.width = Pt(0.5)
        else:
            _rect(slide, sx, sy, sw, sh, fc, NAVY, 0.5)
            _txt(slide, sx + 0.02, sy, sw - 0.04, sh, lab, sz=5.5, bold=True, color=NAVY, align=PP_ALIGN.CENTER, valign=MSO_ANCHOR.MIDDLE)
        mids.append((sx + sw / 2, sy + sh / 2, sx + sw))
        sx += sw + gap
    for i, n in enumerate(nums):
        if i + 1 < len(mids):
            _flow(slide, mids[i][2] + INSET, mids[i][1], mids[i + 1][0] - sw / 2 - INSET, mids[i + 1][1], n)


def build_reference_slide(prs, n: int) -> None:
    slide = prs.slides.add_slide(prs.slide_layouts[BLANK_LAYOUT])
    add_title_bar(slide, "LLD", "Low-Level Design — ML Platform (DEV · PROD · CI/CD)")

    # ── TOP: GitHub + GitHub Actions (reference grey bar) ──
    gy, gh = 0.76, 0.78
    _rect(slide, 0.18, gy, 12.96, gh, GRAY_BG, NAVY, 0.9)
    _txt(slide, 0.24, gy + 0.02, 0.8, 0.14, "GitHub", sz=8, bold=True, color=NAVY)

    _chip(slide, 0.24, gy + 0.18, 0.95, 0.52, "GH", "Repo\nTemplates", WHITE, fs=5.5)
    _chip(slide, 1.28, gy + 0.18, 0.88, 0.52, "GH", "Training\nRepo", WHITE, fs=5.5)
    _chip(slide, 2.22, gy + 0.18, 0.95, 0.52, "GH", "Deployment\nRepo", WHITE, fs=5.5)

    _rect(slide, 3.35, gy + 0.10, 3.85, gh - 0.20, BLUE_LT, BLUE, 0.8)
    _txt(slide, 3.42, gy + 0.12, 1.5, 0.12, "GitHub Actions", sz=7, bold=True, color=BLUE)
    _chip(slide, 3.45, gy + 0.28, 1.75, 0.38, "GH", "Training\nPipeline", BLUE_LT, fs=5.3)
    _chip(slide, 5.30, gy + 0.28, 1.75, 0.38, "GH", "Deployment\nPipeline", GREEN_LT, fs=5.3)

    _persona(slide, 7.35, gy + 0.12, "Data\nSolution\nLead")
    _persona(slide, 8.05, gy + 0.12, "Senior DS\nApprove\nPROD Train")
    _persona(slide, 8.75, gy + 0.12, "Platform\nOps Lead")

    _flow(slide, 3.10, gy + 0.44, 3.45, gy + 0.44, 1)
    _flow(slide, 5.20, gy + 0.44, 5.30, gy + 0.44, 2)
    _flow(slide, 7.05, gy + 0.44, 7.35, gy + 0.44, 3)
    _flow(slide, 7.75, gy + 0.44, 8.05, gy + 0.44, 4)

    # ── Personas left of DEV ──
    _persona(slide, 0.22, 1.72, "Data\nScientist")
    _persona(slide, 0.22, 2.35, "DS\nLead")

    # ── DEV ENV ──
    dx, dy, dw, dh = 0.48, 1.58, 6.05, 4.05
    _rect(slide, dx, dy, dw, dh, CLOUD_BG, DEV_BORDER, 1.2, dashed=True, rounded=True)
    _txt(slide, dx + 0.08, dy + 0.04, 1.5, 0.14, "DEV", sz=9, bold=True, color=DEV_BORDER)

    _chip(slide, dx + 0.12, dy + 0.22, 1.05, 0.55, "SM", "SageMaker\nProjects", WHITE, fs=5.3)

    # MLflow column (reference: large left block)
    _rect(slide, dx + 0.12, dy + 0.85, 1.15, 1.35, TEAL_LT, RGBColor(0x0F, 0x76, 0x6E), 0.7)
    _txt(slide, dx + 0.16, dy + 0.88, 1.05, 0.14, "MLflow", sz=6.5, bold=True, color=NAVY)
    _chip(slide, dx + 0.16, dy + 1.04, 1.05, 0.48, "ML", "Tracking\nServer", WHITE, fs=5.0)
    _chip(slide, dx + 0.16, dy + 1.58, 1.05, 0.55, "ML", "Model Registry\n/ Monitoring", WHITE, fs=5.0)

    # Build pipeline
    steps = [
        ("Preprocess\nprepare.py", TEAL_LT),
        ("Train\ntrain.py", TEAL_LT),
        ("Eval\nevaluate.py", TEAL_LT),
        ("◆", ORANGE_LT),
        ("Register\nModel", BLUE_LT),
    ]
    _pipe_row(slide, dx + 1.38, dy + 0.85, 4.45, 0.72,
              "SageMaker Pipeline — Export / Start", steps, [5, 6, 7, 8, 9])

    # Step Functions trigger
    _chip(slide, dx + 1.38, dy + 1.65, 1.15, 0.48, "SF", "Step Functions\nTrigger Pipeline", YEL, fs=5.0)

    # Infra row
    iy = dy + 2.22
    _chip(slide, dx + 0.12, iy, 1.05, 0.50, "SecM", "Secrets\nManager", ORANGE_LT, fs=5.0)
    _chip(slide, dx + 1.25, iy, 1.05, 0.50, "S3", "Git Artifacts\nBucket", GREEN_LT, fs=5.0)
    _chip(slide, dx + 2.38, iy, 0.95, 0.50, "ECR", "Container\nRegistry", PINK, fs=5.0)
    _chip(slide, dx + 3.43, iy, 1.15, 0.50, "S3", "Model Artifact\nBucket", GREEN_LT, fs=5.0)
    _chip(slide, dx + 4.68, iy, 1.15, 0.50, "IAM", "IAM Roles", ORANGE_LT, fs=5.0)

    # Deploy row
    dy2 = dy + 2.82
    _chip(slide, dx + 0.12, dy2, 1.35, 0.48, "SM", "Trigger\nPipeline", TEAL_LT, fs=5.0)
    _chip(slide, dx + 1.58, dy2, 1.55, 0.48, "SM", "SageMaker Pipeline\nEndpoint Config", TEAL_LT, fs=5.0)
    _chip(slide, dx + 3.25, dy2, 1.25, 0.48, "SM", "SageMaker\nEndpoint", TEAL_LT, fs=5.0)
    _chip(slide, dx + 4.58, dy2, 1.25, 0.48, "CW", "CloudWatch\nDashboard", GRAY, fs=5.0)
    _flow(slide, dx + 1.47, dy2 + 0.24, dx + 1.58, dy2 + 0.24, 10)
    _flow(slide, dx + 3.13, dy2 + 0.24, dx + 3.25, dy2 + 0.24, 11)
    _flow(slide, dx + 4.50, dy2 + 0.24, dx + 4.58, dy2 + 0.24, 12)

    # ── SRE between zones ──
    _persona(slide, 6.58, 2.85, "SRE")

    # ── PROD ENV ──
    px, py, pw, ph = 6.78, 1.58, 6.05, 4.05
    _rect(slide, px, py, pw, ph, CLOUD_BG, PROD_BORDER, 1.2, dashed=True, rounded=True)
    _txt(slide, px + 0.08, py + 0.04, 1.5, 0.14, "PROD", sz=9, bold=True, color=PROD_BORDER)

    _chip(slide, px + 0.12, py + 0.22, 1.05, 0.48, "EB", "Amazon\nEventBridge", YEL, fs=5.0)

    prod_steps = [
        ("Preprocess", TEAL_LT),
        ("Train", TEAL_LT),
        ("Eval", TEAL_LT),
        ("◆", ORANGE_LT),
        ("Register", BLUE_LT),
    ]
    _pipe_row(slide, px + 1.25, py + 0.85, 4.55, 0.72,
              "SageMaker Pipeline — Import / Start", prod_steps, [13, 14, 15, 16, 17])

    _rect(slide, px + 0.12, py + 1.65, 1.05, 0.95, TEAL_LT, RGBColor(0x0F, 0x76, 0x6E), 0.7)
    _txt(slide, px + 0.16, py + 1.68, 0.95, 0.12, "MLflow", sz=6, bold=True, color=NAVY)
    _chip(slide, px + 0.16, py + 1.82, 0.95, 0.70, "ML", "Model Registry\n(Prod)", WHITE, fs=5.0)

    piy = py + 2.22
    _chip(slide, px + 0.12, piy, 0.95, 0.50, "S3", "Prod Data\nBucket", GREEN_LT, fs=5.0)
    _chip(slide, px + 1.18, piy, 0.95, 0.50, "S3", "Artifacts\nBucket", GREEN_LT, fs=5.0)
    _chip(slide, px + 2.24, piy, 0.85, 0.50, "ECR", "ECR", PINK, fs=5.0)

    py2 = py + 2.82
    _chip(slide, px + 0.12, py2, 0.85, 0.48, "APIGW", "API\nGateway", WHITE, fs=5.0)
    _chip(slide, px + 1.05, py2, 1.35, 0.48, "SM", "SageMaker\nEndpoint", TEAL_LT, fs=5.0)
    _chip(slide, px + 2.50, py2, 1.15, 0.48, "Mon", "Model\nMonitor", GRAY, fs=5.0)
    _chip(slide, px + 3.75, py2, 1.05, 0.48, "CW", "CloudWatch\nDashboard", GRAY, fs=5.0)
    _chip(slide, px + 4.90, py2, 1.05, 0.48, "App", "Application", LAV, fs=5.0)
    _flow(slide, px + 0.97, py2 + 0.24, px + 1.05, py2 + 0.24, 18)
    _flow(slide, px + 2.40, py2 + 0.24, px + 2.50, py2 + 0.24, 19)
    _flow(slide, px + 3.65, py2 + 0.24, px + 3.75, py2 + 0.24, 20)

    # DEV → PROD promote
    _flow(slide, dx + dw - 0.05, dy + 1.20, px + 0.05, py + 1.20, 4, dashed=True)

    # GHA → DEV / PROD
    _flow(slide, 4.20, gy + gh, 3.50, dy + INSET, 1)
    _arrow(slide, 6.10, gy + gh, 8.50, py + INSET, dashed=True)
    _num(slide, 6.85, 1.35, 2)

    # ── DATA (bottom left) ──
    by = 5.78
    _chip(slide, 0.22, by, 1.05, 0.52, "API", "External\nAPIs", GRAY, fs=5.3)
    _chip(slide, 1.35, by, 1.15, 0.52, "DX", "AWS Data\nExchange", GRAY, fs=5.3)
    _chip(slide, 2.58, by, 1.25, 0.52, "S3", "Data Lake", GREEN_LT, fs=5.5)
    _flow(slide, 3.20, by + 0.26, 2.20, dy + dh + INSET, 21)
    _flow(slide, 3.20, by + 0.10, 8.00, py + ph + INSET, 22)

    # Legend
    _rect(slide, 0.18, 6.42, 12.96, 0.88, WHITE, NAVY, 0.9)
    _txt(slide, 0.26, 6.46, 12.80, 0.14,
         "Reference LLD layout — blue numbers = flow sequence · dashed = promote / cross-env · "
         "GitHub Actions + SageMaker Registry (MLflow shown per reference)",
         sz=7.5, color=SLATE)
    legend = [
        "1–4 GitHub → GHA → approvals",
        "5–9 DEV build pipeline",
        "10–12 DEV deploy → endpoint → CW",
        "13–17 PROD build pipeline",
        "18–20 PROD deploy → monitor → app",
        "21–22 Data Lake → DEV/PROD",
    ]
    for i, t in enumerate(legend):
        col, row = i % 3, i // 3
        _txt(slide, 0.28 + col * 4.25, 6.66 + row * 0.28, 4.10, 0.24, t, sz=6.5, color=BODY)

    add_footer(slide, slide_num=n)


def build() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    prs = new_presentation()
    build_reference_slide(prs, 1)
    prs.save(OUT)
    post_process_pptx(OUT)
    print(f"Saved {OUT}")


if __name__ == "__main__":
    build()
