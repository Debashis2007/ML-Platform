#!/usr/bin/env python3
"""Build ML_Platform_Consolidated_LLD.pptx — single-slide reference layout for ML Platform.

Matches AWS guidance LLD style:
  GitHub (Training + Deployment repos, GHA pipelines)
  DEV VPC  ·  PROD VPC
  Data sources · numbered flows 1–20

Outputs:
  assets/ML_Platform_Consolidated_LLD.pptx
  assets/ML_Platform_Consolidated_LLD_Description.pptx (slide 2)
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
    PURPLE,
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
GREEN_LT = RGBColor(0xD1, 0xFA, 0xE5)
ORANGE_LT = RGBColor(0xFF, 0xED, 0xD5)
YEL = RGBColor(0xFE, 0xF3, 0xC7)
CLOUD_BG = RGBColor(0xFA, 0xFB, 0xFC)
DEV_BORDER = RGBColor(0x1D, 0x4E, 0xD8)
PROD_BORDER = RGBColor(0xC2, 0x41, 0x0C)
ARROW = RGBColor(0x33, 0x41, 0x55)
INSET = 0.02


def _rect(slide, l, t, w, h, fc, ec=NAVY, line_w=0.8, dashed=False):
    shp = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(l), Inches(t), Inches(w), Inches(h))
    shp.fill.solid()
    shp.fill.fore_color.rgb = fc
    shp.line.color.rgb = ec
    shp.line.width = Pt(line_w)
    shp.shadow.inherit = False
    if dashed:
        shp.line.dash_style = MSO_LINE_DASH_STYLE.DASH
    return shp


def _txt(slide, l, t, w, h, text, size=8, color=BODY, bold=False, align=PP_ALIGN.LEFT,
         valign=MSO_ANCHOR.TOP, wrap=True):
    box = slide.shapes.add_textbox(Inches(l), Inches(t), Inches(max(0.18, w)), Inches(max(0.10, h)))
    tf = box.text_frame
    tf.word_wrap = wrap
    tf.vertical_anchor = valign
    tf.text = text
    for p in tf.paragraphs:
        p.alignment = align
        for r in p.runs:
            r.font.size = Pt(size)
            r.font.color.rgb = color
            r.font.bold = bold
            r.font.name = FONT
    return box


def _icon(slide, l, t, size, abbr):
    key = ABBR_TO_ICON_KEY.get(abbr)
    rel = ICON_FILES.get(key) if key else None
    path = ICON_ROOT / rel if rel else None
    if path and path.exists():
        slide.shapes.add_picture(str(path), Inches(l), Inches(t), width=Inches(size), height=Inches(size))
        return
    shp = _rect(slide, l, t, size, size, PURPLE, PURPLE, 0.4)
    tf = shp.text_frame
    tf.text = abbr
    tf.paragraphs[0].alignment = PP_ALIGN.CENTER
    for r in tf.paragraphs[0].runs:
        r.font.size = Pt(max(5, size * 11))
        r.font.color.rgb = WHITE
        r.font.bold = True


def _chip(slide, l, t, w, h, abbr, label, fc=WHITE, fs=6.0):
    _rect(slide, l, t, w, h, fc, NAVY, 0.55)
    iz = min(0.22, max(0.11, h - 0.20))
    _icon(slide, l + 0.04, t + 0.03, iz, abbr)
    _txt(slide, l + iz + 0.06, t + 0.02, w - iz - 0.08, h - 0.04, label, size=fs, bold=True,
         color=NAVY, wrap=True, valign=MSO_ANCHOR.MIDDLE)


def _arrow(slide, x1, y1, x2, y2, dashed=False, color=ARROW):
    conn = slide.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, Inches(x1), Inches(y1), Inches(x2), Inches(y2))
    conn.line.color.rgb = color
    conn.line.width = Pt(1.2)
    if dashed:
        conn.line.dash_style = MSO_LINE_DASH_STYLE.DASH
    ln = conn.line._get_or_add_ln()
    ln.append(ln.makeelement(qn("a:tailEnd"), {"type": "triangle", "w": "med", "len": "med"}))
    return conn


def _num(slide, l, t, n, dia=0.20):
    shp = slide.shapes.add_shape(MSO_SHAPE.OVAL, Inches(l), Inches(t), Inches(dia), Inches(dia))
    shp.fill.solid()
    shp.fill.fore_color.rgb = BLUE_NUM
    shp.line.fill.background()
    tf = shp.text_frame
    tf.text = str(n)
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    for r in p.runs:
        r.font.size = Pt(7)
        r.font.color.rgb = WHITE
        r.font.bold = True


def _flow(slide, x1, y1, x2, y2, n):
    _arrow(slide, x1, y1, x2, y2)
    _num(slide, (x1 + x2) / 2 - 0.10, (y1 + y2) / 2 - 0.12, n)


def _pipeline_row(slide, x, y, w, h, title, scripts):
    _rect(slide, x, y, w, h, WHITE, NAVY, 0.7)
    _txt(slide, x + 0.04, y + 0.02, w - 0.08, 0.14, title, size=6.5, bold=True, color=NAVY)
    step_w = (w - 0.12 - 0.08 * (len(scripts) - 1)) / len(scripts)
    sx = x + 0.06
    sy = y + 0.18
    sh = h - 0.22
    boxes = []
    for label in scripts:
        _rect(slide, sx, sy, step_w, sh, TEAL_LT if "Register" not in label else BLUE_LT, NAVY, 0.5)
        _txt(slide, sx + 0.02, sy, step_w - 0.04, sh, label, size=5.5, bold=True, color=NAVY,
             align=PP_ALIGN.CENTER, valign=MSO_ANCHOR.MIDDLE, wrap=True)
        boxes.append((sx + step_w / 2, sy + sh / 2, sx + step_w))
        sx += step_w + 0.08
    for i in range(len(boxes) - 1):
        _flow(slide, boxes[i][2] + INSET, boxes[i][1], boxes[i + 1][0] - step_w / 2 - INSET, boxes[i + 1][1], 0)


def _draw_env(slide, x, y, w, h, title, border, is_prod, flow_start):
    _rect(slide, x, y, w, h, CLOUD_BG, border, 1.1, dashed=True)
    _txt(slide, x + 0.08, y + 0.05, w - 0.16, 0.16, title, size=8, bold=True, color=border)

    inner_x, inner_w = x + 0.12, w - 0.24
    # Personas
    persona = "SRE / Platform Lead" if is_prod else "Data Scientist · Senior DS"
    _txt(slide, inner_x, y + 0.22, inner_w, 0.12, persona, size=6.5, color=SLATE)

    # SageMaker Studio / Projects
    _chip(slide, inner_x, y + 0.36, 1.05, 0.48, "SM", "SageMaker\nStudio", WHITE, fs=5.5)

    # Training pipeline
    pipe_y = y + 0.92
    pipe_h = 0.52
    scripts = ["Preprocess\npreprocess.py", "Train\ntrain.py", "Eval\nevaluate.py", "Condition", "Register\nPending"]
    _pipeline_row(slide, inner_x + 1.15, pipe_y, inner_w - 1.20, pipe_h,
                  "SageMaker Pipeline — Export / Start" if not is_prod else "SageMaker Pipeline — Import / Start",
                  scripts)

    # Registry + infra row
    row_y = y + 1.58
    row_h = 0.46
    gw = (inner_w - 0.24) / 4
    items = [
        ("SM", "Model Registry\n(SageMaker)", BLUE_LT),
        ("SecM", "Secrets\nManager", ORANGE_LT),
        ("S3", "Artifact\nBucket", GREEN_LT),
        ("ECR", "Container\nImages", PINK),
    ]
    gx = inner_x
    for abbr, lab, fc in items:
        _chip(slide, gx, row_y, gw, row_h, abbr, lab, fc, fs=5.3)
        gx += gw + 0.08

    # Deploy + monitor
    dep_y = y + 2.14
    if is_prod:
        _chip(slide, inner_x, dep_y, 1.05, 0.44, "APIGW", "API\nGateway", WHITE, fs=5.3)
        _chip(slide, inner_x + 1.15, dep_y, inner_w - 2.35, 0.44, "SM", "SageMaker Endpoint\n+ Model Monitor", TEAL_LT, fs=5.3)
        _chip(slide, inner_x + inner_w - 1.05, dep_y, 1.05, 0.44, "CW", "CloudWatch\nDashboard", GRAY, fs=5.3)
    else:
        _chip(slide, inner_x, dep_y, inner_w * 0.55, 0.44, "SM", "SageMaker Endpoint\n(test)", TEAL_LT, fs=5.3)
        _chip(slide, inner_x + inner_w * 0.58, dep_y, inner_w * 0.40, 0.44, "CW", "CloudWatch\nDashboard", GRAY, fs=5.3)

    # Governance side path (hub)
    if not is_prod:
        gov_x = x + w + 0.08
        if gov_x + 0.95 < 13.0:
            _chip(slide, gov_x, y + 1.58, 0.95, 1.00, "EB", "EventBridge\n→ Lambda\n→ DDB\n→ Power BI", YEL, fs=5.0)

    return y + h


def build_consolidated_slide(prs, n: int) -> None:
    slide = prs.slides.add_slide(prs.slide_layouts[BLANK_LAYOUT])
    add_title_bar(slide, "LLD", "ML Platform — Consolidated Low-Level Design (DEV · PROD · CI/CD)")

    # ── GitHub / CI-CD (top) ──
    gh_y, gh_h = 0.78, 0.72
    _rect(slide, 0.22, gh_y, 12.90, gh_h, GRAY, NAVY, 0.9)
    _txt(slide, 0.30, gh_y + 0.02, 1.2, 0.14, "GitHub", size=8, bold=True, color=NAVY)
    _chip(slide, 0.30, gh_y + 0.20, 1.35, 0.46, "GH", "Project\nTemplates", WHITE, fs=5.5)
    _chip(slide, 1.75, gh_y + 0.20, 1.25, 0.46, "GH", "Training\nRepo", WHITE, fs=5.5)
    _chip(slide, 3.10, gh_y + 0.20, 1.35, 0.46, "GH", "Deployment\nRepo", WHITE, fs=5.5)

    gha_x = 4.65
    _rect(slide, gha_x, gh_y + 0.08, 4.55, gh_h - 0.16, WHITE, BLUE, 0.8)
    _txt(slide, gha_x + 0.08, gh_y + 0.10, 2.0, 0.12, "GitHub Actions", size=7, bold=True, color=BLUE)
    _chip(slide, gha_x + 0.10, gh_y + 0.24, 2.05, 0.40, "GH", "Training Pipeline\nWorkflow A", BLUE_LT, fs=5.3)
    _chip(slide, gha_x + 2.25, gh_y + 0.24, 2.05, 0.40, "GH", "Deployment Pipeline\nWorkflow B", GREEN_LT, fs=5.3)

    _chip(slide, 9.45, gh_y + 0.20, 1.55, 0.46, "Okta", "Senior DS\nApprove", ORANGE_LT, fs=5.3)
    _chip(slide, 11.15, gh_y + 0.20, 1.75, 0.46, "Okta", "Approve PROD\nTraining", ORANGE_LT, fs=5.3)

    _flow(slide, 3.00, gh_y + 0.43, 4.75, gh_y + 0.43, 1)
    _flow(slide, 6.70, gh_y + 0.43, 9.45, gh_y + 0.43, 2)
    _flow(slide, 11.00, gh_y + 0.43, 11.00, 1.58, 3)

    # ── DEV / PROD VPCs ──
    env_y, env_h = 1.58, 3.55
    dev_x, dev_w = 0.22, 6.35
    pr_x, pr_w = 6.75, 6.37

    _draw_env(slide, dev_x, env_y, dev_w, env_h,
              "DEV Environment — Hub Non-Prod / dev spoke", DEV_BORDER, False, 4)
    _draw_env(slide, pr_x, env_y, pr_w, env_h,
              "PROD Environment — Hub Prod / API Gateway", PROD_BORDER, True, 12)

    _flow(slide, 6.57, env_y + 1.15, 6.75, env_y + 1.15, 4)
    _txt(slide, 6.48, env_y + 0.95, 0.55, 0.20, "Promote\npackage", size=6, bold=True, color=PROD_BORDER, align=PP_ALIGN.CENTER)

    # ── Data sources (bottom left) ──
    data_y = 5.28
    _chip(slide, 0.30, data_y, 1.15, 0.50, "DX", "AWS Data\nExchange", GRAY, fs=5.3)
    _chip(slide, 1.55, data_y, 1.05, 0.50, "API", "External\nAPIs", GRAY, fs=5.3)
    _chip(slide, 2.70, data_y, 1.35, 0.50, "S3", "ML\nData Lake", GREEN_LT, fs=5.3)
    _flow(slide, 4.05, data_y + 0.25, 1.50, env_y + env_h + INSET, 5)
    _flow(slide, 4.05, data_y + 0.25, 7.20, env_y + env_h + INSET, 6)

    # ── DevOps factory note ──
    _rect(slide, 4.35, data_y, 4.20, 0.50, ORANGE_LT, RGBColor(0xEA, 0x58, 0x0C), 0.7)
    _txt(slide, 4.45, data_y + 0.06, 4.00, 0.38,
         "DevOps factory account: GHA runners · ECR · OIDC → hub/spoke accounts",
         size=6.5, color=NAVY, wrap=True, align=PP_ALIGN.CENTER)

    # ── Legend ──
    _rect(slide, 0.22, 5.92, 12.90, 1.38, WHITE, NAVY, 1.0)
    _txt(slide, 0.32, 5.96, 12.70, 0.16, "Flow legend (blue numbers) — source opens session → destination",
         size=9, bold=True, color=NAVY)
    legend = [
        "1  DS push → GHA Training Pipeline",
        "2  Training → Senior DS approval gate",
        "3  Approved → PROD training trigger",
        "4  DEV register → promote package → PROD",
        "5–6  Data Lake → DEV / PROD pipeline inputs",
        "Hub: Model Registry + RAM share · Governance: EB→Lambda→DDB→Power BI",
        "Code: ML-Platform repo — deployment/ (AWS CFN) · ml_platform/ · examples/credit-risk/",
    ]
    ly = 6.18
    for i, line in enumerate(legend):
        col = i // 4
        row = i % 4
        _txt(slide, 0.38 + col * 4.35, ly + row * 0.28, 4.20, 0.26, line, size=7, color=BODY)

    add_footer(slide, slide_num=n)


def build_description_slide(prs, n: int) -> None:
    slide = prs.slides.add_slide(prs.slide_layouts[BLANK_LAYOUT])
    add_title_bar(slide, "LLD", "Consolidated LLD — how to read (ML Platform)")

    _rect(slide, 0.28, 0.82, 12.78, 0.65, BLUE_LT, BLUE, 1.0)
    _txt(slide, 0.40, 0.88, 12.50, 0.55,
         "Single consolidated view combining AWS multi-account ML governance guidance with platform CI/CD factory. "
         "GitHub replaces GitLab; SageMaker Model Registry is SoR (MLflow optional Phase 2). "
         "Companion repo: ML-Platform/ (deployment CFN from AWS sample + ml_platform pipeline factory).",
         size=10, color=NAVY, wrap=True)

    blocks = [
        ("GitHub / CI-CD", [
            "Training Repo + Deployment Repo from model-project template.",
            "Workflow A: validate → ECR → build_pipeline.py → start SageMaker Pipeline.",
            "Workflow B: on Approved → terraform endpoint → smoke /invocations.",
        ]),
        ("DEV Environment", [
            "Hub Non-Prod or dev spoke: Studio, pipeline, registry, artifacts.",
            "Steps: preprocess.py → train.py → evaluate.py → condition → register Pending.",
            "Senior DS approves in SageMaker Model Registry.",
        ]),
        ("PROD Environment", [
            "Hub Prod: promoted package, API Gateway + endpoint, Model Monitor.",
            "Governance metrics: EventBridge → Lambda → DynamoDB → Athena → Power BI.",
        ]),
        ("AWS reference mapped", [
            "deployment/step1a–1c, step2–6 CFN → hub/spoke/KMS (from AWS guidance repo).",
            "source/ notebooks retained for manual validation; factory code in ml_platform/.",
            "ModelCreditRisk example aligned with step1b default package group name.",
        ]),
    ]
    y = 1.65
    for title, bullets in blocks:
        _txt(slide, 0.32, y, 12.0, 0.20, title, size=11, bold=True, color=NAVY)
        y += 0.24
        for b in bullets:
            _txt(slide, 0.48, y, 12.2, 0.30, f"• {b}", size=9, color=BODY, wrap=True)
            y += 0.32
        y += 0.08

    add_footer(slide, slide_num=n)


def build() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    prs = new_presentation()
    build_consolidated_slide(prs, 1)
    build_description_slide(prs, 2)
    prs.save(OUT)
    post_process_pptx(OUT)
    print(f"Saved {OUT} ({len(prs.slides)} slides)")


if __name__ == "__main__":
    build()
