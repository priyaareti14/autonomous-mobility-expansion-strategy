"""Load config/ingestion_sources.json and expand it into one entry per RAW table."""

from __future__ import annotations

import json
from copy import deepcopy

from .common import REPO_ROOT

REGISTRY_PATH = REPO_ROOT / "config" / "ingestion_sources.json"

REQUIRED_KEYS = ("dataset_id", "source_id", "provider", "dataset", "vintage", "feasibility",
                 "usage_category", "access_method", "grain", "required_columns")


def load_registry() -> list[dict]:
    """One dict per dataset/RAW table. ACS group entries expand to one per group."""
    data = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    out: list[dict] = []
    for entry in data["datasets"]:
        missing = [k for k in REQUIRED_KEYS if k not in entry]
        if missing:
            raise ValueError(f"registry entry {entry.get('dataset_id')} missing {missing}")
        if entry["feasibility"] != "GO":
            raise ValueError(f"{entry['dataset_id']}: only GO sources are registered for Phase 3")
        if entry["access_method"] == "census_api_group":
            for group in entry["groups"]:
                ds = deepcopy(entry)
                ds["dataset_id"] = f"{entry['dataset_id']}_{group.lower()}"
                ds["group"] = group
                ds["dataset"] = f"{entry['dataset']}: table {group}"
                ds["raw_table"] = entry["raw_table_pattern"].format(group=group)
                ds["snapshot_name"] = entry["snapshot_pattern"].format(group=group)
                out.append(ds)
        else:
            out.append(entry)
    ids = [d["dataset_id"] for d in out]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate dataset_id in registry")
    return out


def not_ingested() -> list[dict]:
    return json.loads(REGISTRY_PATH.read_text(encoding="utf-8")).get("not_ingested", [])
