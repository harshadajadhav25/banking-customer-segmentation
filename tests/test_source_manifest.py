from pathlib import Path

import yaml


def test_source_manifest_contains_eight_tables() -> None:
    manifest_path = Path("config/source_tables.yml")
    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))

    assert manifest["delimiter"] == ";"
    assert len(manifest["tables"]) == 8
    assert "transaction" in manifest["tables"]
    assert manifest["tables"]["transaction"]["file"] == "trans.asc"
