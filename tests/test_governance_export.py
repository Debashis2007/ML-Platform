"""Unit tests for Stage Governance Athena export Lambda."""

from __future__ import annotations

import importlib.util
from decimal import Decimal
from pathlib import Path
from unittest.mock import MagicMock, patch


def _load():
    path = Path("infra/terraform/modules/stage_analytics/lambda/export_governance.py")
    spec = importlib.util.spec_from_file_location("export_governance", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_export_writes_ndjson(monkeypatch):
    mod = _load()
    monkeypatch.setenv("GOVERNANCE_TABLE", "gov")
    monkeypatch.setenv("EXPORT_BUCKET", "spill-bucket")
    monkeypatch.setenv("EXPORT_PREFIX", "governance-export")

    table = MagicMock()
    table.scan.return_value = {
        "Items": [
            {"pk": "ModelCreditRisk", "sk": "1", "approval_status": "Approved", "rows": Decimal("2")},
        ]
    }
    ddb = MagicMock()
    ddb.Table.return_value = table
    s3 = MagicMock()

    with patch.object(mod, "_ddb", return_value=ddb), patch.object(mod, "_s3", return_value=s3):
        result = mod.handler({}, None)

    assert result["statusCode"] == 200
    assert result["exported"] == 1
    assert result["s3_uri"].startswith("s3://spill-bucket/governance-export/")
    s3.put_object.assert_called_once()
    body = s3.put_object.call_args.kwargs["Body"].decode()
    assert "ModelCreditRisk" in body
    assert "Approved" in body
