#!/usr/bin/env python3
"""
prepare_medical_dataset.py — Préparation du dataset médical pour l'équipe IA.

Source : ruslanmv/ai-medical-chatbot (HuggingFace) — ~256 916 dialogues
         Patient/Docteur, colonnes : Description, Patient, Doctor.

Pipeline :
  1. Charge le parquet source.
  2. Nettoie : retire vides/trop courts/trop longs, doublons, boilerplate docteur.
  3. Reformate en instruction-tuning (instruction / input / output) type Alpaca,
     directement consommable par le notebook QLoRA de l'équipe IA.
  4. Sous-échantillonne (défaut 1000, seed 42 -> reproductible) pour tenir dans
     le temps de fine-tuning Colab (T4).
  5. Écrit un JSON prêt à l'emploi + un petit rapport de préparation.

Usage :
    python prepare_medical_dataset.py --src med.parquet --n 1000 --out medical_dataset_prepared_1000.json

Dépendances : pandas, pyarrow.
"""
from __future__ import annotations
import argparse
import json
import re
from pathlib import Path

import pandas as pd

# Boilerplate récurrent des réponses docteur, sans valeur clinique.
BOILERPLATE = [
    re.compile(r"^\s*hi\s*[\.,]?\s*", re.I),
    re.compile(r"^\s*hello\s*[\.,]?\s*", re.I),
    re.compile(r"thanks?\s+for\s+(your\s+)?(query|question)[\.,]?", re.I),
    re.compile(r"(for\s+further\s+information\s+)?consult\s+a[n]?\s+\w+\s+online\s*-*>*\s*$", re.I),
    re.compile(r"-+>+\s*$"),
    re.compile(r"\s+"),  # normalisation espaces (appliqué en dernier)
]


def clean_text(s: str) -> str:
    s = str(s).strip()
    for pat in BOILERPLATE[:-1]:
        s = pat.sub(" ", s)
    s = BOILERPLATE[-1].sub(" ", s).strip()  # espaces
    return s


def prepare(src: Path, n: int, seed: int, out: Path) -> dict:
    df = pd.read_parquet(src)
    n_raw = len(df)

    # 1) Nettoyage colonne par colonne
    for col in ("Description", "Patient", "Doctor"):
        df[col] = df[col].astype(str).map(clean_text)

    # 2) Filtres qualité
    before = len(df)
    df = df[(df["Patient"].str.len() >= 20) & (df["Doctor"].str.len() >= 20)]
    dropped_short = before - len(df)

    before = len(df)
    df = df[df["Doctor"].str.len() <= 2000]  # coupe les réponses fleuves (fine-tuning)
    dropped_long = before - len(df)

    before = len(df)
    df = df.drop_duplicates(subset=["Patient", "Doctor"])
    dropped_dupes = before - len(df)

    n_clean = len(df)

    # 3) Sous-échantillonnage reproductible
    n = min(n, n_clean)
    sample = df.sample(n=n, random_state=seed).reset_index(drop=True)

    # 4) Reformatage instruction-tuning (Alpaca)
    records = []
    for _, row in sample.iterrows():
        instruction = row["Patient"].strip()
        # Description utilisée comme contexte court si distincte du Patient
        desc = row["Description"].strip()
        context = desc if desc and desc.lower() not in instruction.lower() else ""
        records.append({
            "instruction": instruction,
            "input": context,
            "output": row["Doctor"].strip(),
        })

    out.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")

    report = {
        "source": str(src),
        "raw_dialogues": n_raw,
        "dropped_too_short": int(dropped_short),
        "dropped_too_long": int(dropped_long),
        "dropped_duplicates": int(dropped_dupes),
        "clean_pool": int(n_clean),
        "sampled": int(n),
        "seed": seed,
        "format": "instruction / input / output (Alpaca)",
        "output_file": str(out),
        "avg_output_chars": round(float(sample["Doctor"].str.len().mean()), 1),
    }
    return report


def main() -> int:
    here = Path(__file__).resolve().parent
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default=str(here / "med.parquet"))
    ap.add_argument("--n", type=int, default=1000)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--out", default=str(here / "medical_dataset_prepared_1000.json"))
    args = ap.parse_args()

    rep = prepare(Path(args.src), args.n, args.seed, Path(args.out))
    (Path(args.out).parent / "medical_prep_report.json").write_text(
        json.dumps(rep, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    for k, v in rep.items():
        print(f"  {k:22s}: {v}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
