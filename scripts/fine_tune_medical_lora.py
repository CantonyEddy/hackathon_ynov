#!/usr/bin/env python3
"""LoRA fine-tuning script for a medical assistant using Phi-3-mini.

This file is designed for a GPU-enabled environment such as Colab Pro.
It writes a lightweight adapter to the models/medical_phi_lora directory.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import torch
from datasets import Dataset
from peft import LoraConfig, PeftModel, TaskType, get_peft_model, prepare_model_for_kbit_training
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig, TrainingArguments, Trainer, DataCollatorForLanguageModeling


ROOT = Path(__file__).resolve().parents[1]
DATASET_PATH = ROOT / "medical_dataset" / "prepared_medical_dataset.json"
OUTPUT_DIR = ROOT / "models" / "medical_phi_lora"
MODEL_NAME = "microsoft/Phi-3-mini-4k-instruct"


def load_dataset(path: Path):
    if not path.exists():
        raise FileNotFoundError(f"Dataset not found: {path}")
    with path.open("r", encoding="utf-8") as handle:
        rows = json.load(handle)
    return Dataset.from_list(rows)


def format_example(example: dict) -> str:
    return f"<|user|>\n{example['instruction']}<|end|>\n<|assistant|>\n{example['response']}<|end|>"


def tokenize(batch, tokenizer):
    texts = [format_example(example) for example in batch]
    tokenized = tokenizer(texts, truncation=True, padding="max_length", max_length=512, return_tensors="pt")
    tokenized["labels"] = tokenized["input_ids"].clone()
    return tokenized


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    tokenizer.padding_side = "right"

    quantization_config = None
    if torch.cuda.is_available():
        quantization_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_compute_dtype=torch.float16,
            bnb_4bit_use_double_quant=True,
            bnb_4bit_quant_type="nf4",
        )
    model_kwargs = {
        "torch_dtype": torch.float16 if torch.cuda.is_available() else torch.float32,
        "trust_remote_code": True,
        "low_cpu_mem_usage": True,
    }
    if quantization_config:
        model_kwargs["quantization_config"] = quantization_config
        model_kwargs["device_map"] = "auto"

    model = AutoModelForCausalLM.from_pretrained(MODEL_NAME, **model_kwargs)
    if quantization_config:
        model = prepare_model_for_kbit_training(model)
    lora_config = LoraConfig(
        r=16,
        lora_alpha=32,
        target_modules=["qkv_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
        lora_dropout=0.05,
        bias="none",
        task_type=TaskType.CAUSAL_LM,
    )
    model = get_peft_model(model, lora_config)

    dataset = load_dataset(DATASET_PATH)
    tokenized_dataset = dataset.map(lambda batch: tokenize(batch, tokenizer), batched=True, remove_columns=dataset.column_names)

    training_args = TrainingArguments(
        output_dir=str(OUTPUT_DIR),
        per_device_train_batch_size=2,
        gradient_accumulation_steps=4,
        learning_rate=2e-4,
        num_train_epochs=1,
        logging_steps=10,
        save_steps=50,
        save_total_limit=2,
        remove_unused_columns=False,
        fp16=torch.cuda.is_available(),
        report_to="none",
    )
    data_collator = DataCollatorForLanguageModeling(tokenizer=tokenizer, mlm=False)
    trainer = Trainer(model=model, args=training_args, train_dataset=tokenized_dataset, data_collator=data_collator)
    trainer.train()
    trainer.save_model()
    tokenizer.save_pretrained(OUTPUT_DIR)
    print(f"Saved medical LoRA adapter to {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
