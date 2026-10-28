#!/usr/bin/env python3
"""校验产品方向证据链。无假设可以通过；有假设必须可回溯。"""
import argparse
import json
import os


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workdir", required=True)
    args = ap.parse_args()
    cache = os.path.join(args.workdir, "cache")
    with open(os.path.join(cache, "keyword_labeled.json"), "r", encoding="utf-8") as f:
        labeled = json.load(f)
    with open(os.path.join(cache, "analysis.json"), "r", encoding="utf-8") as f:
        analysis = json.load(f)
    known = {r.get("keyword") for r in labeled.get("keywords") or []}
    errors = []
    for i, row in enumerate(analysis.get("product_hypotheses") or [], 1):
        sources = row.get("source_keywords") or []
        if not sources or any(k not in known for k in sources):
            errors.append(f"第{i}行证据关键词缺失或不在关键词池")
        if not isinstance(row.get("evidence"), dict) or not row.get("evidence"):
            errors.append(f"第{i}行缺数据证据")
        if row.get("confidence") not in {"high", "mid", "low"}:
            errors.append(f"第{i}行置信度非法")
        if row.get("inference_level") != "hypothesis":
            errors.append(f"第{i}行必须标记 hypothesis")
        if "假设" not in str(row.get("product_response") or ""):
            errors.append(f"第{i}行产品响应未标记假设")
        if not row.get("validation_needed"):
            errors.append(f"第{i}行缺待验证数据")
    if errors:
        print("\n".join(f"[FAIL] {e}" for e in errors))
        raise SystemExit(f"分析验收失败：{len(errors)} 项")
    print(f"OK 产品方向证据验收：{len(analysis.get('product_hypotheses') or [])} 行")


if __name__ == "__main__":
    main()
