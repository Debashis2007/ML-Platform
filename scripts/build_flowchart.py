#!/usr/bin/env python3
"""Render end-to-end ML platform flowchart PNG for docs and README."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "assets" / "ML_Platform_Flowchart.png"


def generate_flowchart_png(path: Path) -> Path:
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches
    from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

    path.parent.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(13.5, 8.5))
    ax.set_xlim(0, 13.5)
    ax.set_ylim(0, 8.5)
    ax.axis("off")
    ax.set_title("ML Platform — End-to-End Flow", fontsize=14, fontweight="bold", color="#20113D", pad=12)

    def box(x, y, w, h, text, fc, ec="#1C1C1C", fs=7.5):
        p = FancyBboxPatch(
            (x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.08",
            linewidth=1.0, edgecolor=ec, facecolor=fc,
        )
        ax.add_patch(p)
        ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fs, color="#1C1C1C", wrap=True)

    def diamond(x, y, size, fc="#FFEDD5"):
        d = mpatches.RegularPolygon((x, y), 4, radius=size, orientation=0.785, fc=fc, ec="#EA580C", lw=1)
        ax.add_patch(d)
        ax.text(x, y, "Metric\nOK?", ha="center", va="center", fontsize=6.5)

    def arrow(x1, y1, x2, y2, dashed=False):
        style = "dashed" if dashed else "-"
        ax.add_patch(FancyArrowPatch(
            (x1, y1), (x2, y2), arrowstyle="-|>", mutation_scale=10,
            linewidth=1.2, color="#334155", linestyle=style,
        ))

    def lane(y, h, label, color):
        ax.add_patch(FancyBboxPatch(
            (0.15, y), 13.2, h, boxstyle="round,pad=0.01,rounding_size=0.05",
            linewidth=1.2, edgecolor=color, facecolor="#FAFBFC", linestyle="--", alpha=0.35,
        ))
        ax.text(0.25, y + h - 0.18, label, fontsize=9, fontweight="bold", color=color)

    lane(6.55, 1.85, "① GitHub CI/CD (Workflow A · Training)", "#1D4ED8")
    lane(3.55, 2.85, "② SageMaker Pipeline (DEV / Hub Non-Prod)", "#0F766E")
    lane(1.55, 1.85, "③ Governance & Approval", "#D97706")
    lane(0.25, 1.15, "④ Deploy & Operate (Workflow B · PROD path)", "#059669")

    box(0.4, 6.85, 1.5, 0.55, "DS push code\n+ pipeline.yaml", "#E5E7EB")
    box(2.1, 6.85, 1.4, 0.55, "GHA validate\n+ build image", "#DBEAFE", "#1D4ED8")
    box(3.7, 6.85, 1.5, 0.55, "Push ECR\nml-platform-models", "#DBEAFE", "#1D4ED8")
    box(5.4, 6.85, 1.7, 0.55, "build_pipeline.py\nupsert pipeline", "#DBEAFE", "#1D4ED8")
    box(7.3, 6.85, 1.5, 0.55, "Start pipeline\nexecution", "#DBEAFE", "#1D4ED8")
    box(9.0, 6.85, 1.6, 0.55, "Data Lake\n→ preprocess input", "#D1FAE5", "#059669")
    for x1, x2 in [(1.9, 2.1), (3.5, 3.7), (5.2, 5.4), (7.0, 7.3)]:
        arrow(x1, 7.12, x2, 7.12)
    arrow(8.8, 7.12, 9.0, 7.12)
    arrow(9.8, 6.85, 9.8, 6.35, dashed=True)

    box(0.4, 5.55, 1.2, 0.5, "Preprocess\npreprocess.py", "#CCFBF1", "#0F766E")
    box(1.8, 5.55, 1.0, 0.5, "Train\ntrain.py", "#CCFBF1", "#0F766E")
    box(3.0, 5.55, 1.0, 0.5, "Eval\nevaluate.py", "#CCFBF1", "#0F766E")
    diamond(4.55, 5.8, 0.28)
    box(5.2, 5.55, 1.3, 0.5, "Register\nPending Approval", "#DBEAFE", "#1D4ED8")
    box(6.7, 5.55, 1.2, 0.5, "S3 artifacts\n+ metrics.json", "#D1FAE5", "#059669")
    for (x1, x2) in [(1.6, 1.8), (2.8, 3.0), (4.0, 4.25), (4.85, 5.2), (6.5, 6.7)]:
        arrow(x1, 5.8, x2, 5.8)
    arrow(7.8, 6.35, 7.8, 5.8, dashed=True)
    ax.text(4.55, 5.35, "No → stop\n(fail closed)", ha="center", fontsize=6, color="#C2410C")

    box(0.4, 3.55, 1.5, 0.5, "Senior DS\nreview metrics", "#FFEDD5", "#EA580C")
    box(2.1, 3.55, 1.2, 0.5, "Approve /\nReject", "#FFEDD5", "#EA580C")
    box(3.5, 3.55, 1.4, 0.5, "EventBridge\nevent", "#FEF3C7", "#D97706")
    box(5.1, 3.55, 1.2, 0.5, "Lambda\ncapture", "#FEF3C7", "#D97706")
    box(6.5, 3.55, 1.1, 0.5, "DynamoDB\naudit", "#FEF3C7", "#D97706")
    box(7.8, 3.55, 1.1, 0.5, "Athena\nquery", "#FEF3C7", "#D97706")
    box(9.1, 3.55, 1.2, 0.5, "BI\ndashboard", "#FEF3C7", "#D97706")
    arrow(6.5, 5.55, 1.15, 4.05)
    for (x1, x2) in [(1.9, 2.1), (3.3, 3.5), (4.9, 5.1), (6.3, 6.5), (7.6, 7.8), (8.9, 9.1)]:
        arrow(x1, 3.8, x2, 3.8)

    box(0.4, 1.55, 1.5, 0.5, "GHA Workflow B\ndeploy trigger", "#D1FAE5", "#059669")
    box(2.1, 1.55, 1.4, 0.5, "Terraform\nendpoint module", "#D1FAE5", "#059669")
    box(3.7, 1.55, 1.3, 0.5, "SageMaker\nEndpoint", "#CCFBF1", "#0F766E")
    box(5.2, 1.55, 1.2, 0.5, "Smoke test\n/invocations", "#CCFBF1", "#0F766E")
    box(6.6, 1.55, 1.3, 0.5, "Model Monitor\nbaseline", "#E5E7EB")
    box(8.1, 1.55, 1.3, 0.5, "CloudWatch\n+ SNS alarms", "#E5E7EB")
    box(9.6, 1.55, 1.5, 0.5, "AgentCore MCP\ntool (optional)", "#EDE9FE", "#4F00CA")
    arrow(3.3, 3.55, 1.15, 2.05, dashed=True)
    for (x1, x2) in [(1.9, 2.1), (3.5, 3.7), (5.0, 5.2), (6.4, 6.6), (7.9, 8.1), (9.4, 9.6)]:
        arrow(x1, 1.8, x2, 1.8)

    box(10.8, 5.55, 2.3, 0.55, "PROD promote\n(approved package)", "#EDE9FE", "#4F00CA")
    arrow(6.5, 5.55, 10.8, 5.82, dashed=True)
    arrow(11.95, 5.55, 11.95, 2.05, dashed=True)

    fig.tight_layout()
    fig.savefig(path, dpi=180, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return path


def main() -> None:
    generate_flowchart_png(OUT)
    print(f"Saved {OUT}")


if __name__ == "__main__":
    main()
