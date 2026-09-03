#!/usr/bin/env python3
"""Generate editable draw.io LLD matching AWS reference layout.

Outputs:
  assets/ML_Platform_LLD.drawio
  assets/ML_Platform_Consolidated_LLD.drawio
"""

from __future__ import annotations

import html
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "assets" / "ML_Platform_LLD.drawio"
OUT_LEGACY = ROOT / "assets" / "ML_Platform_Consolidated_LLD.drawio"

W, H = 1800, 1020
_c = 0


def nid() -> str:
    global _c
    _c += 1
    return f"c{_c}"


def esc(s: str) -> str:
    return html.escape(s).replace("\n", "&#xa;")


# AWS4 resource icon base style (renders in diagrams.net with AWS library)
AWS = (
    "sketch=0;outlineConnect=0;fontColor=#232F3E;gradientColor=none;"
    "strokeColor=#232F3E;fillColor=#FFFFFF;dashed=0;verticalLabelPosition=bottom;"
    "verticalAlign=top;align=center;html=1;whiteSpace=wrap;fontSize=9;fontStyle=0;"
    "aspect=fixed;shape=mxgraph.aws4.resourceIcon;resIcon=mxgraph.aws4.{icon};"
)


def aws_cell(i: str, icon: str, label: str, x: float, y: float, w: float = 78, h: float = 78) -> str:
    val = f"{label}"
    return (
        f'<mxCell id="{i}" value="{esc(val)}" style="{AWS.format(icon=icon)}" '
        f'vertex="1" parent="1"><mxGeometry x="{x}" y="{y}" width="{w}" height="{h}" as="geometry"/></mxCell>'
    )


def box(i: str, label: str, x: float, y: float, w: float, h: float, fill: str = "#FFFFFF", stroke: str = "#1C1C1C", rounded: bool = True) -> str:
    r = "rounded=1;" if rounded else ""
    return (
        f'<mxCell id="{i}" value="{esc(label)}" style="{r}whiteSpace=wrap;html=1;fillColor={fill};'
        f'strokeColor={stroke};fontSize=9;fontStyle=0;align=center;verticalAlign=middle;" '
        f'vertex="1" parent="1"><mxGeometry x="{x}" y="{y}" width="{w}" height="{h}" as="geometry"/></mxCell>'
    )


def swim(i: str, title: str, x: float, y: float, w: float, h: float, fill: str, stroke: str) -> str:
    return (
        f'<mxCell id="{i}" value="{esc(title)}" style="swimlane;startSize=28;fillColor={fill};'
        f'strokeColor={stroke};strokeWidth=2;fontStyle=1;fontSize=12;rounded=1;" '
        f'vertex="1" parent="1"><mxGeometry x="{x}" y="{y}" width="{w}" height="{h}" as="geometry"/></mxCell>'
    )


def lane_box(i: str, parent: str, label: str, x: float, y: float, w: float, h: float, fill: str = "#FFFFFF", stroke: str = "#1C1C1C") -> str:
    return (
        f'<mxCell id="{i}" value="{esc(label)}" style="rounded=1;whiteSpace=wrap;html=1;fillColor={fill};'
        f'strokeColor={stroke};fontSize=8;align=center;verticalAlign=middle;" '
        f'vertex="1" parent="{parent}"><mxGeometry x="{x}" y="{y}" width="{w}" height="{h}" as="geometry"/></mxCell>'
    )


def diamond(i: str, parent: str, x: float, y: float, w: float, h: float) -> str:
    return (
        f'<mxCell id="{i}" value="" style="rhombus;whiteSpace=wrap;html=1;fillColor=#FFEDD5;strokeColor=#EA580C;" '
        f'vertex="1" parent="{parent}"><mxGeometry x="{x}" y="{y}" width="{w}" height="{h}" as="geometry"/></mxCell>'
    )


def actor(i: str, label: str, x: float, y: float, parent: str = "1") -> str:
    return (
        f'<mxCell id="{i}" value="{esc(label)}" style="shape=umlActor;verticalLabelPosition=bottom;'
        f'verticalAlign=top;html=1;outlineConnect=0;fontSize=8;" vertex="1" parent="{parent}">'
        f'<mxGeometry x="{x}" y="{y}" width="24" height="48" as="geometry"/></mxCell>'
    )


def circle_node(i: str, parent: str, label: str, x: float, y: float, d: float = 72) -> str:
    return (
        f'<mxCell id="{i}" value="{esc(label)}" style="ellipse;whiteSpace=wrap;html=1;fillColor=#CCFBF1;'
        f'strokeColor=#0F766E;fontSize=7;align=center;" vertex="1" parent="{parent}">'
        f'<mxGeometry x="{x}" y="{y}" width="{d}" height="{d}" as="geometry"/></mxCell>'
    )


def flow_num(i: str, n: int, x: float, y: float) -> str:
    return (
        f'<mxCell id="{i}" value="{n}" style="ellipse;whiteSpace=wrap;html=1;aspect=fixed;fillColor=#2563EB;'
        f'fontColor=#FFFFFF;fontStyle=1;fontSize=9;align=center;" vertex="1" parent="1">'
        f'<mxGeometry x="{x}" y="{y}" width="22" height="22" as="geometry"/></mxCell>'
    )


def edge(i: str, src: str, tgt: str, dashed: bool = False, label: str = "") -> str:
    dash = "dashed=1;" if dashed else ""
    return (
        f'<mxCell id="{i}" value="{esc(label)}" style="edgeStyle=orthogonalEdgeStyle;rounded=0;'
        f'orthogonalLoop=1;jettySize=auto;html=1;strokeColor=#334155;strokeWidth=1;endArrow=classic;{dash}" '
        f'edge="1" parent="1" source="{src}" target="{tgt}"><mxGeometry relative="1" as="geometry"/></mxCell>'
    )


def pipe_row(parent: str, title_id: str, x: float, y: float, w: float, h: float, title: str, steps: list[str], step_ids: list[str]) -> list[str]:
    cells = []
    cells.append(lane_box(title_id, parent, title, x, y, w, 22, "#FFFFFF", "#1C1C1C"))
    sy = y + 26
    sh = h - 28
    gap = 8
    sw = (w - gap * (len(steps) - 1)) / len(steps)
    sx = x
    for sid, step in zip(step_ids, steps):
        if step == "◆":
            cells.append(diamond(sid, parent, sx + sw * 0.25, sy + sh * 0.15, sw * 0.5, sh * 0.7))
        else:
            cells.append(lane_box(sid, parent, step, sx, sy, sw, sh, "#CCFBF1", "#0F766E"))
        sx += sw + gap
    return cells


def build_xml() -> str:
    global _c
    _c = 0
    cells: list[str] = ['<mxCell id="0"/>', '<mxCell id="1" parent="0"/>']

    # Title
    cells.append(
        box(nid(), "ML Platform — Low-Level Design (LLD)\nDEV · PROD · GitHub CI/CD · SageMaker · MLflow", 40, 8, 1720, 42, "#F4F2FA", "#4F00CA")
    )

    # ── GITHUB ──
    gh = nid()
    cells.append(swim(gh, "GITHUB", 40, 58, 1720, 148, "#E5E7EB", "#1C1C1C"))
    cells.append(lane_box(nid(), gh, "Repo Templates", 20, 40, 110, 88, "#FFFFFF"))
    cells.append(lane_box(nid(), gh, "Training Repo", 145, 40, 105, 88, "#FFFFFF"))
    cells.append(lane_box(nid(), gh, "Deployment Repo", 265, 40, 115, 88, "#FFFFFF"))

    gha = nid()
    cells.append(
        f'<mxCell id="{gha}" value="GitHub Actions" style="swimlane;startSize=22;fillColor=#DBEAFE;strokeColor=#1D4ED8;fontStyle=1;fontSize=10;" '
        f'vertex="1" parent="{gh}"><mxGeometry x="400" y="32" width="420" height="100" as="geometry"/></mxCell>'
    )
    tr_pipe, dp_pipe = nid(), nid()
    cells.append(lane_box(tr_pipe, gha, "Training Pipeline", 12, 30, 185, 58, "#DBEAFE", "#1D4ED8"))
    cells.append(lane_box(dp_pipe, gha, "Deployment Pipeline", 210, 30, 195, 58, "#D1FAE5", "#059669"))

    ds_lead_gh = nid()
    cells.append(actor(ds_lead_gh, "Data Selection Lead\nApprove PROD Training", 900, 42, gh))

    # ── DEV ──
    dev = nid()
    cells.append(swim(dev, "DEV", 40, 220, 820, 500, "#FAFBFC", "#1D4ED8"))

    cells.append(actor(nid(), "Data Scientist", 8, 48, dev))
    cells.append(actor(nid(), "Data Scientist Lead", 8, 120, dev))

    sm_dev = nid()
    cells.append(lane_box(sm_dev, dev, "SageMaker Training Instance", 50, 38, 130, 70, "#FFFFFF"))

    mlflow_dev = nid()
    cells.append(
        f'<mxCell id="{mlflow_dev}" value="MLflow" style="swimlane;startSize=20;fillColor=#CCFBF1;strokeColor=#0F766E;fontSize=9;fontStyle=1;" '
        f'vertex="1" parent="{dev}"><mxGeometry x="50" y="120" width="130" height="150" as="geometry"/></mxCell>'
    )
    cells.append(lane_box(nid(), mlflow_dev, "Registry Store", 8, 28, 114, 48, "#FFFFFF"))
    cells.append(lane_box(nid(), mlflow_dev, "Experiment Tracking", 8, 82, 114, 48, "#FFFFFF"))

    pipe_dev = nid()
    psteps = ["Preprocess\npreprocess.py", "Train\ntrain.py", "Eval\nevaluate.py", "◆", "Register Model"]
    pids = [nid() for _ in psteps]
    cells.extend(pipe_row(dev, pipe_dev, 200, 38, 580, 78, "SageMaker Pipeline — Dataset / Build", psteps, pids))

    ml_mon = nid()
    cells.append(lane_box(ml_mon, dev, "MLflow Model Registry\nTraining Monitoring", 200, 130, 200, 55, "#CCFBF1", "#0F766E"))
    trig = nid()
    cells.append(lane_box(trig, dev, "Trigger Pipeline", 420, 130, 100, 55, "#FEF3C7", "#D97706"))

    ep_cfg, ep_pipe = nid(), nid()
    cells.append(circle_node(ep_cfg, dev, "Endpoint Config\nPipeline", 540, 118))
    cells.append(circle_node(ep_pipe, dev, "Endpoint\nPipeline", 640, 118))

    cw_dev = nid()
    cells.append(lane_box(cw_dev, dev, "CloudWatch Dashboard", 740, 130, 65, 55, "#E5E7EB"))

    # DEV infra
    sec_d, s3_d1, ecr_d, s3_d2 = nid(), nid(), nid(), nid()
    cells.append(lane_box(sec_d, dev, "AWS Secrets Manager", 50, 210, 120, 55, "#FFEDD5", "#EA580C"))
    cells.append(lane_box(s3_d1, dev, "Dev Artifacts Bucket", 185, 210, 120, 55, "#D1FAE5", "#059669"))
    cells.append(lane_box(ecr_d, dev, "Elastic Container Registry", 320, 210, 130, 55, "#FCE7F3", "#BE185D"))
    cells.append(lane_box(s3_d2, dev, "Model Artifact Bucket", 465, 210, 130, 55, "#D1FAE5", "#059669"))

    fs_dev = nid()
    cells.append(lane_box(fs_dev, dev, "Feature Store\n(Phase 2)", 610, 210, 100, 55, "#E5E7EB"))

    # DEV deploy bottom
    cells.append(lane_box(nid(), dev, "SageMaker Endpoint (test)", 50, 290, 140, 55, "#CCFBF1", "#0F766E"))
    cells.append(lane_box(nid(), dev, "CloudWatch Logs", 210, 290, 110, 55, "#E5E7EB"))

    # ── APPROVAL GATE ──
    lead_mid = nid()
    cells.append(actor(lead_mid, "Lead\nApprove manual\ndeployment", 870, 380))

    # ── PROD ──
    prod = nid()
    cells.append(swim(prod, "PROD", 940, 220, 820, 500, "#FAFBFC", "#C2410C"))

    cells.append(actor(nid(), "SRE", 8, 38, prod))
    cells.append(actor(nid(), "DS Lead\nApprove PROD deploy", 8, 110, prod))

    pipe_prod = nid()
    psteps_p = ["Preprocess\npreprocess.py", "Train\ntrain.py", "Eval\nevaluate.py", "◆", "Register Model"]
    pids_p = [nid() for _ in psteps_p]
    cells.extend(pipe_row(prod, pipe_prod, 50, 38, 580, 78, "SageMaker Pipeline — Shared / Prod", psteps_p, pids_p))

    ml_prod = nid()
    cells.append(lane_box(ml_prod, prod, "MLflow Model Registry\nTraining Monitoring", 50, 130, 200, 55, "#CCFBF1", "#0F766E"))
    trig_p = nid()
    cells.append(lane_box(trig_p, prod, "Trigger Deployment", 270, 130, 115, 55, "#FEF3C7", "#D97706"))

    ep_cfg_p, ep_pipe_p = nid(), nid()
    cells.append(circle_node(ep_cfg_p, prod, "Endpoint Config\nPipeline", 400, 118))
    cells.append(circle_node(ep_pipe_p, prod, "Endpoint\nPipeline", 500, 118))

    app_p = nid()
    cells.append(lane_box(app_p, prod, "Application", 620, 130, 90, 55, "#EDE9FE", "#4F00CA"))

    s3_p1, sec_p, cw_p, mon_p, sns_p = nid(), nid(), nid(), nid(), nid()
    cells.append(lane_box(s3_p1, prod, "Prod Data Bucket", 50, 210, 115, 55, "#D1FAE5", "#059669"))
    cells.append(lane_box(nid(), prod, "Artifacts Bucket", 180, 210, 115, 55, "#D1FAE5", "#059669"))
    cells.append(lane_box(sec_p, prod, "Secrets Manager", 310, 210, 105, 55, "#FFEDD5", "#EA580C"))
    cells.append(lane_box(cw_p, prod, "CloudWatch Dashboard", 430, 210, 120, 55, "#E5E7EB"))
    cells.append(lane_box(mon_p, prod, "SageMaker Model Monitoring", 565, 210, 140, 55, "#E5E7EB"))
    cells.append(lane_box(sns_p, prod, "Amazon SNS", 720, 210, 80, 55, "#FFEDD5", "#EA580C"))

    cells.append(lane_box(nid(), prod, "API Gateway", 50, 290, 100, 55, "#FFFFFF"))
    cells.append(lane_box(nid(), prod, "SageMaker Endpoint", 165, 290, 130, 55, "#CCFBF1", "#0F766E"))

    # ── DATA ──
    data = nid()
    cells.append(swim(data, "Data Sources", 40, 740, 420, 110, "#F4F2FA", "#4F00CA"))
    api_d, dx_d, lake = nid(), nid(), nid()
    cells.append(lane_box(api_d, data, "External APIs", 15, 35, 105, 60, "#E5E7EB"))
    cells.append(lane_box(dx_d, data, "AWS Data Exchange", 130, 35, 115, 60, "#E5E7EB"))
    cells.append(lane_box(lake, data, "Data Lake", 260, 30, 130, 68, "#D1FAE5", "#059669"))

    # ── LEGEND ──
    cells.append(
        box(nid(), "Blue numbers = flow sequence (1–15) · Solid = data/control · Dashed = promote/trigger\n"
             "Reference: AWS ML governance guidance · GitHub Actions, hub/spoke, BI governance dashboard",
             500, 740, 1260, 110, "#FFFFFF", "#1C1C1C")
    )

    # Flow numbers
    nums = [(320, 118, 1), (520, 118, 2), (960, 118, 3), (1080, 118, 4), (380, 680, 5), (380, 640, 6),
            (300, 300, 7), (450, 300, 8), (580, 300, 9), (680, 300, 10), (860, 400, 11), (1100, 300, 12),
            (1250, 300, 13), (1400, 300, 14), (1550, 300, 15)]
    for x, y, n in nums:
        cells.append(flow_num(nid(), n, x, y))

    # ── EDGES ──
    edges = [
        edge(nid(), tr_pipe, pids[0], label=""),
        edge(nid(), dp_pipe, ep_cfg, dashed=True),
        edge(nid(), lake, pids[0]),
        edge(nid(), lake, pids_p[0], dashed=True),
        edge(nid(), pids[-1], ml_mon),
        edge(nid(), ml_mon, trig),
        edge(nid(), trig, ep_cfg),
        edge(nid(), ep_cfg, ep_pipe),
        edge(nid(), ep_pipe, cw_dev),
        edge(nid(), pids_p[-1], ml_prod),
        edge(nid(), ml_prod, trig_p),
        edge(nid(), trig_p, ep_cfg_p),
        edge(nid(), ep_cfg_p, ep_pipe_p),
        edge(nid(), ep_pipe_p, app_p),
        edge(nid(), pids[-1], lead_mid, dashed=True),
        edge(nid(), lead_mid, pids_p[0], dashed=True),
        edge(nid(), tr_pipe, sm_dev, dashed=True),
    ]
    cells.extend(edges)

    body = "\n        ".join(cells)
    return f'''<mxfile host="app.diagrams.net" modified="2026-09-03T00:00:00.000Z" agent="ML-Platform" version="24.7.0" type="device">
  <diagram id="ml-platform-lld" name="ML Platform LLD">
    <mxGraphModel dx="{W}" dy="{H}" grid="1" gridSize="10" guides="1" tooltips="1" connect="1" arrows="1" fold="1" page="1" pageScale="1" pageWidth="{W}" pageHeight="{H}" background="#ffffff" math="0" shadow="0">
      <root>
        {body}
      </root>
    </mxGraphModel>
  </diagram>
</mxfile>'''


def main() -> None:
    xml = build_xml()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(xml, encoding="utf-8")
    OUT_LEGACY.write_text(xml, encoding="utf-8")
    print(f"Saved {OUT}")
    print(f"Saved {OUT_LEGACY}")


if __name__ == "__main__":
    main()
