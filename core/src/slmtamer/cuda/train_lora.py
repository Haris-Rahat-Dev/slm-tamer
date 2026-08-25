"""Minimal LoRA trainer for CUDA machines using transformers + peft.

Reads a dataset dir with train.jsonl ({"text": ...} lines), trains a LoRA
adapter, and saves it in PEFT format to the output dir.
"""

import argparse
import json
import math


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True)
    parser.add_argument("--data", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--iters", type=int, default=600)
    parser.add_argument("--batch-size", type=int, default=4)
    parser.add_argument("--learning-rate", type=float, default=5e-5)
    parser.add_argument("--rank", type=int, default=16)
    parser.add_argument("--max-len", type=int, default=1024)
    args = parser.parse_args()

    import torch
    from peft import LoraConfig, get_peft_model
    from transformers import AutoModelForCausalLM, AutoTokenizer

    with open(f"{args.data}/train.jsonl") as f:
        texts = [json.loads(l)["text"] for l in f if l.strip()]

    tokenizer = AutoTokenizer.from_pretrained(args.model)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    model = AutoModelForCausalLM.from_pretrained(
        args.model, torch_dtype=torch.bfloat16, device_map="cuda"
    )
    model.config.use_cache = False
    lconf = LoraConfig(
        r=args.rank,
        lora_alpha=args.rank * 2,
        lora_dropout=0.05,
        task_type="CAUSAL_LM",
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],
    )
    model = get_peft_model(model, lconf)
    model.print_trainable_parameters()

    def encode(batch):
        out = tokenizer(batch, truncation=True, max_length=args.max_len, padding=True)
        out["labels"] = [
            [(t if t != tokenizer.pad_token_id else -100) for t in ids]
            for ids in out["input_ids"]
        ]
        return out

    optimizer = torch.optim.AdamW(
        [p for p in model.parameters() if p.requires_grad], lr=args.learning_rate
    )
    scaler_dtype = torch.autocast(device_type="cuda", dtype=torch.bfloat16)
    step = 0
    total_steps = args.iters
    model.train()
    while step < total_steps:
        start = (step * args.batch_size) % len(texts)
        batch_texts = [texts[(start + i) % len(texts)] for i in range(args.batch_size)]
        enc = encode(batch_texts)
        enc = {k: torch.tensor(v).cuda() for k, v in enc.items()}
        with scaler_dtype:
            loss = model(**enc).loss
        loss.backward()
        torch.nn.utils.clip_grad_norm_([p for p in model.parameters() if p.requires_grad], 1.0)
        optimizer.step()
        optimizer.zero_grad()
        if step % 10 == 0 or step == total_steps - 1:
            print(f"Iter {step}: Train loss {loss.item():.4f}", flush=True)
        step += 1

    model.save_pretrained(args.output)
    print(f"Saved adapter to {args.output}", flush=True)


if __name__ == "__main__":
    main()
