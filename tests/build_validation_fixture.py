#!/usr/bin/env python3
"""生成一份可保留的 v1.6.0 固定样本报告，供视觉与包验收使用。"""
import argparse
from pathlib import Path

import test_v130


class KeepDirectory:
    def __init__(self, path):
        self.path = Path(path)

    def __enter__(self):
        self.path.mkdir(parents=True, exist_ok=True)
        return str(self.path)

    def __exit__(self, *_args):
        return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    out = Path(args.out).resolve()
    test_v130.tempfile.TemporaryDirectory = lambda: KeepDirectory(out)
    test_v130.V140Tests("test_report_two_matrices_and_chart_series").test_report_two_matrices_and_chart_series()
    report = next((out / "output").glob("*.xlsx"))
    print(report)


if __name__ == "__main__":
    main()
