"""Fuse (merge LoRA into base) or evaluate held-out loss on CUDA machines."""

import argparse


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["fuse", "eval"])
    parser.add_argument("--model", required=True)
    parser.add_argument("--adapter", default=None)
    parser.add_argument("--data", default=None)
    parser.add_argument("--output", default=None)
    parser.add_argument("--batch-size", type=int, default=4)
    args = parser.parse_args()

    import torch
    from peft import PeftModel
    from transformers import AutoModelForCausalLM, AutoTokenizer

    kwargs = {"torch_dtype": torch.bfloat16, "device_map": "cuda"}
    model = AutoModelForCausalLM.from_pretrained(args.model, **kwargs)
    if args.adapter:
        model = PeftModel.from_pretrained(model, args.adapter)

    tokenizer = AutoTokenizer.from_pretrained(args.model)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    if args.mode == "fuse":
        model = model.merge_and_unload()
        model.save_pretrained(args.output)
        tokenizer.save_pretrained(args.output)
        print(f"Saved merged model to {args.output}", flush=True)
        return

    with open(f"{args.data}/valid.jsonl") as f:
        texts = [json.loads(l)["text"] for l in f if l.strip()]

    model.eval()
    total_loss, total_tokens = 0.0, 0
    with torch.no_grad():
        for i in range(0, len(texts), args.batch_size):
            batch = texts[i : i + args.batch_size]
            enc = tokenizer(batch, truncation=True, max_length=1024, padding=True,
                            return_tensors="pt").to("cuda")
            labels = enc["input_ids"].masked_fill(
                enc["input_ids"] == tokenizer.pad_token_id, -100
            )
            out = model(**enc, labels=labels)
            n = (labels != -100).sum().item()
            total_loss += out.loss.item() * n
            total_tokens += n
    ppl = math.exp(total_loss / max(total_tokens, 1))
    print(f"Test loss {total_loss / max(total_tokens, 1):.4f}, Test ppl {ppl:.3f}.", flush=True)


if __name__ == "__main__":
    import json
    import math

    main()
