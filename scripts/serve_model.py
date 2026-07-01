#!/usr/bin/env python3
"""Production-ready local inference server for the financial Phi model.

The service exposes a lightweight FastAPI API and can run in two modes:
1. Full Hugging Face + PEFT mode when torch/transformers/peft are installed.
2. Fallback heuristic mode for demos and environments without GPU dependencies.
"""

from __future__ import annotations

import os
import re
from typing import Optional

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel


class ChatRequest(BaseModel):
    message: str
    system_prompt: Optional[str] = None


class ChatResponse(BaseModel):
    response: str
    mode: str
    model: str


class InferenceBackend:
    def __init__(self, model_path: str, base_model: str) -> None:
        self.model_path = model_path
        self.base_model = base_model
        self.model = None
        self.tokenizer = None
        self.backend_mode = "fallback"
        self.model_name = "phi-financial-demo"
        self.error = None
        self._loaded = False

    def load(self) -> None:
        if self._loaded:
            return
        self._loaded = True
        try:
            import torch
            from peft import PeftModel
            from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

            if not os.path.exists(self.model_path):
                raise FileNotFoundError(f"Adapter folder not found: {self.model_path}")

            tokenizer = AutoTokenizer.from_pretrained(self.base_model, trust_remote_code=True)
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

            model = AutoModelForCausalLM.from_pretrained(self.base_model, **model_kwargs)
            model = PeftModel.from_pretrained(model, self.model_path)
            model.eval()

            self.model = model
            self.tokenizer = tokenizer
            self.backend_mode = "transformers"
            self.model_name = os.path.basename(self.model_path)
            self.error = None
        except Exception as exc:  # pragma: no cover - fallback path is expected in demo envs
            self.backend_mode = "fallback"
            self.error = str(exc)
            self.model = None
            self.tokenizer = None

    def _fallback_response(self, prompt: str) -> str:
        text = prompt.strip().lower()
        if any(k in text for k in ["budget", "finance", "invest", "retire", "saving"]):
            return (
                "Pour une réponse prudente, diversifiez vos investissements, créez un budget mensuel "
                "et gardez une réserve d'urgence avant toute prise de risque."
            )
        if any(k in text for k in ["risk", "volatil", "crypt", "crypto"]):
            return (
                "Les actifs volatils demandent une allocation limitée, une compréhension claire des risques "
                "et des objectifs d'investissement précis."
            )
        if any(k in text for k in ["medical", "sante", "symptom", "diagnos"]):
            return (
                "Je peux aider à résumer des informations générales, mais toute décision clinique doit être "
                "confirmée par un professionnel de santé qualifié."
            )
        return (
            "Le modèle de démonstration est prêt. Posez une question financière, commerciale ou médicale "
            "pour obtenir une réponse structurée et prudente."
        )

    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        self.load()
        if self.backend_mode == "transformers" and self.model is not None and self.tokenizer is not None:
            import torch

            instruction = prompt.strip()
            if system_prompt:
                instruction = f"{system_prompt}\n\n{instruction}"
            formatted = f"<|user|>\n{instruction}<|end|>\n<|assistant|>\n"
            inputs = self.tokenizer(formatted, return_tensors="pt", truncation=True, max_length=512)
            if torch.cuda.is_available() and next(self.model.parameters()).is_cuda:
                inputs = {k: v.cuda() for k, v in inputs.items()}
            with torch.no_grad():
                outputs = self.model.generate(
                    input_ids=inputs["input_ids"],
                    attention_mask=inputs.get("attention_mask"),
                    max_new_tokens=180,
                    temperature=0.7,
                    top_p=0.95,
                    do_sample=True,
                    repetition_penalty=1.15,
                    pad_token_id=self.tokenizer.eos_token_id,
                    eos_token_id=self.tokenizer.eos_token_id,
                    use_cache=False,
                )
            input_length = inputs["input_ids"].shape[1]
            new_tokens = outputs[0][input_length:]
            response = self.tokenizer.decode(new_tokens, skip_special_tokens=True).strip()
            return response if response else self._fallback_response(prompt)
        return self._fallback_response(prompt)

    def health(self) -> dict:
        return {
            "status": "ok",
            "backend": self.backend_mode,
            "model": self.model_name,
            "error": self.error,
        }


backend = InferenceBackend(
    model_path=os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "models", "phi3_financial")),
    base_model="microsoft/Phi-3-mini-4k-instruct",
)

app = FastAPI(title="TechCorp AI Inference API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("ALLOWED_ORIGINS", "http://127.0.0.1:5500,http://localhost:5500").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root() -> dict:
    return {"message": "TechCorp AI API", "docs": "/docs"}


@app.get("/health")
def health() -> dict:
    return backend.health()


@app.post("/api/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    if not request.message or not request.message.strip():
        raise HTTPException(status_code=400, detail="message must not be empty")
    response_text = backend.generate(request.message, request.system_prompt)
    return ChatResponse(response=response_text, mode=backend.backend_mode, model=backend.model_name)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run the TechCorp inference server")
    parser.add_argument("--host", default=os.getenv("HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.getenv("PORT", "8001")))
    args = parser.parse_args()
    uvicorn.run(app, host=args.host, port=args.port, log_level="info")
