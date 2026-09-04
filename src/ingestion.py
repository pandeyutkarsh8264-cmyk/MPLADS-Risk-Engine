"""Data Ingestion & Manifest Generation module.
Strictly compliant with locked specification section 3, 4.1, and 23.
"""

import os
import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

LOCKED_SOURCES = {
    "22567": {
        "dataset_id": "22567",
        "title": "18th Lok Sabha MPLADS: Recommended Works",
        "role": "PRIMARY work-level base",
        "source_url": "https://dataful.in/datasets/22567/"
    },
    "22566": {
        "dataset_id": "22566",
        "title": "18th Lok Sabha MPLADS: Completed Works",
        "role": "ENRICHMENT; completion evidence",
        "source_url": "https://dataful.in/datasets/22566/"
    },
    "18533": {
        "dataset_id": "18533",
        "title": "17th Lok Sabha MPLADS: Works & Funds Sanctioned",
        "role": "HISTORICAL / cross-year context",
        "source_url": "https://dataful.in/datasets/18533/"
    },
    "22565": {
        "dataset_id": "22565",
        "title": "18th Lok Sabha MPLADS: Vendor-level Expenditure",
        "role": "OPTIONAL CONTEXT ONLY",
        "source_url": "https://dataful.in/datasets/22565/"
    }
}

def compute_checksum(file_path: Path, algorithm: str = "sha256") -> str:
    """Computes checksum for a raw data file without loading entire file to memory."""
    h = hashlib.new(algorithm)
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()

def find_raw_dataset_files(raw_dir: Path) -> Dict[str, Path]:
    """Finds raw dataset files in raw_dir matching locked dataset IDs."""
    found = {}
    if not raw_dir.exists():
        return found

    for file_path in raw_dir.iterdir():
        if file_path.is_file() and not file_path.name.startswith("."):
            name = file_path.name
            for ds_id in LOCKED_SOURCES:
                if ds_id in name:
                    found[ds_id] = file_path
                    break
    return found

def generate_source_manifest(raw_dir: Path, manifest_path: Optional[Path] = None) -> Dict[str, Any]:
    """Generates source manifest for acquired datasets in data/raw/."""
    dataset_files = find_raw_dataset_files(raw_dir)
    manifest = {
        "generated_at": datetime.now().isoformat(),
        "datasets": {}
    }

    for ds_id, meta in LOCKED_SOURCES.items():
        if ds_id in dataset_files:
            file_path = dataset_files[ds_id]
            checksum = compute_checksum(file_path)
            file_size = file_path.stat().st_size
            retrieval_date = datetime.fromtimestamp(file_path.stat().st_mtime).strftime("%Y-%m-%d")

            manifest["datasets"][ds_id] = {
                "dataset_id": ds_id,
                "role": meta["role"],
                "source_url": meta["source_url"],
                "retrieval_date": retrieval_date,
                "original_filename": file_path.name,
                "file_path": str(file_path),
                "file_size_bytes": file_size,
                "checksum_sha256": checksum,
                "status": "present"
            }
        else:
            manifest["datasets"][ds_id] = {
                "dataset_id": ds_id,
                "role": meta["role"],
                "source_url": meta["source_url"],
                "status": "missing",
                "instructions": f"Place original download from {meta['source_url']} into data/raw/"
            }

    if manifest_path:
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2)

    return manifest
