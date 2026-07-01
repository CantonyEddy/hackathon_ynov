#!/usr/bin/env python3
"""Prepare a medical conversation dataset for LoRA-style fine-tuning."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import List, Dict, Any


ROOT = Path(__file__).resolve().parents[1]
DATASET_INPUT = ROOT / "medical_dataset"
DATASET_OUTPUT = ROOT / "medical_dataset" / "prepared_medical_dataset.json"


def normalize_text(text: str) -> str:
    if not text:
        return ""
    text = re.sub(r"\s+", " ", text).strip()
    return text


def load_candidates(input_dir: Path) -> List[Dict[str, Any]]:
    examples: List[Dict[str, Any]] = []
    if not input_dir.exists():
        return examples
    for path in sorted(input_dir.glob("*.json")):
        try:
            with path.open("r", encoding="utf-8") as handle:
                payload = json.load(handle)
        except Exception:
            continue
        if isinstance(payload, dict):
            items = payload.get("data") or payload.get("samples") or payload.get("conversations") or []
            if isinstance(items, list):
                examples.extend(items)
        elif isinstance(payload, list):
            examples.extend(payload)
    return examples


def transform_example(example: Dict[str, Any]) -> Dict[str, Any] | None:
    if isinstance(example.get("conversation"), list):
        conversation = example["conversation"]
        if len(conversation) >= 2:
            user = normalize_text(conversation[0].get("content", ""))
            assistant = normalize_text(conversation[1].get("content", ""))
            if user and assistant:
                return {"instruction": user, "response": assistant}
    if example.get("question") and example.get("answer"):
        return {
            "instruction": normalize_text(str(example["question"])),
            "response": normalize_text(str(example["answer"])),
        }
    if example.get("input") and example.get("output"):
        return {
            "instruction": normalize_text(str(example["input"])),
            "response": normalize_text(str(example["output"])),
        }
    return None


def prepare_dataset() -> List[Dict[str, Any]]:
    rows = load_candidates(DATASET_INPUT)
    prepared = []
    for item in rows:
        transformed = transform_example(item)
        if transformed:
            prepared.append(transformed)
    if not prepared:
        prepared = [
            {
                "instruction": "Résumé de sécurité pour une consultation médicale générale.",
                "response": "Consultez un professionnel de santé pour toute décision clinique et vérifiez les symptômes avec prudence.",
            },
            {
                "instruction": "Quelles précautions prendre avant un traitement médical ?",
                "response": "Documentez les allergies, les traitements actuels et les symptômes. Demandez conseil à un professionnel qualifié.",
            },
        ]
    return prepared[:5000]


if __name__ == "__main__":
    prepared = prepare_dataset()
    DATASET_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with DATASET_OUTPUT.open("w", encoding="utf-8") as handle:
        json.dump(prepared, handle, ensure_ascii=False, indent=2)
    print(f"Prepared {len(prepared)} medical examples -> {DATASET_OUTPUT}")
