#!/usr/bin/env python3
"""Regenerate draw.io from PPT export PNG (visual match to reference LLD)."""

from __future__ import annotations

import base64
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
PPT = ASSETS / "ML_Platform_Consolidated_LLD.pptx"
PNG = ASSETS / "ML_Platform_Consolidated_LLD.pptx.png"
DRAWIO = ASSETS / "ML_Platform_Consolidated_LLD.drawio"


def export_png() -> None:
    subprocess.run(
        ["qlmanage", "-t", "-s", "2400", "-o", str(ASSETS), str(PPT)],
        check=True,
        capture_output=True,
    )
    if not PNG.exists():
        raise SystemExit(f"PNG not created: {PNG}")


def write_drawio() -> None:
    b64 = base64.b64encode(PNG.read_bytes()).decode("ascii")
    content = f'''<mxfile host="app.diagrams.net" modified="2026-09-03T00:00:00.000Z" agent="ML-Platform" version="24.7.0" type="device">
  <diagram id="reference-lld" name="LLD — Reference layout (ML Platform)">
    <mxGraphModel dx="1600" dy="900" grid="0" guides="0" tooltips="1" connect="0" arrows="0" fold="1" page="1" pageScale="1" pageWidth="1600" pageHeight="900" background="#ffffff" math="0" shadow="0">
      <root>
        <mxCell id="0" />
        <mxCell id="1" parent="0" />
        <mxCell id="bg" value="" style="shape=image;verticalLabelPosition=bottom;labelBackgroundColor=default;verticalAlign=top;aspect=fixed;imageAspect=0;image=data:image/png,{b64};" vertex="1" parent="1">
          <mxGeometry width="1600" height="900" as="geometry" />
        </mxCell>
      </root>
    </mxGraphModel>
  </diagram>
</mxfile>'''
    DRAWIO.write_text(content)
    print(f"Saved {DRAWIO}")


def main() -> None:
    if "--skip-png" not in sys.argv:
        export_png()
    write_drawio()


if __name__ == "__main__":
    main()
