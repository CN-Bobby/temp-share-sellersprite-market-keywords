#!/usr/bin/env python3
"""Build and verify the distributable .skill package and SHA256SUMS."""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import zipfile


SKIP_DIRS = {"__pycache__", ".pytest_cache"}
SKIP_NAMES = {"SHA256SUMS"}


def release_files(root: Path) -> list[Path]:
    result = []
    for path in sorted(root.rglob("*"), key=lambda item: item.relative_to(root).as_posix()):
        if not path.is_file():
            continue
        relative = path.relative_to(root)
        if any(part in SKIP_DIRS for part in relative.parts):
            continue
        if path.name in SKIP_NAMES or path.suffix == ".skill":
            continue
        result.append(path)
    return result


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def expected_manifest(root: Path, package: Path) -> str:
    lines = [f"{sha256_bytes(package.read_bytes())}  {package.name}"]
    for path in release_files(root):
        lines.append(f"{sha256_bytes(path.read_bytes())}  {path.relative_to(root).as_posix()}")
    return "\n".join(lines) + "\n"


def build(root: Path, package: Path) -> None:
    prefix = f"{root.name}/"
    package.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(package, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in release_files(root):
            rel = path.relative_to(root).as_posix()
            info = zipfile.ZipInfo(prefix + rel, date_time=(2020, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, path.read_bytes(), compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)


def verify(root: Path, package: Path, manifest: Path) -> None:
    if not package.is_file():
        raise SystemExit(f"缺少安装包: {package}")
    expected = {path.relative_to(root).as_posix(): path.read_bytes() for path in release_files(root)}
    with zipfile.ZipFile(package) as archive:
        actual = {}
        prefix = f"{root.name}/"
        for name in archive.namelist():
            if name.endswith("/"):
                continue
            if not name.startswith(prefix):
                raise SystemExit(f"安装包根目录错误: {name}")
            actual[name[len(prefix):]] = archive.read(name)
    if set(actual) != set(expected):
        missing = sorted(set(expected) - set(actual))
        extra = sorted(set(actual) - set(expected))
        raise SystemExit(f"安装包文件集合不一致; missing={missing}; extra={extra}")
    mismatched = [name for name in expected if actual[name] != expected[name]]
    if mismatched:
        raise SystemExit(f"安装包文件内容不一致: {mismatched}")
    content = expected_manifest(root, package)
    if not manifest.is_file() or manifest.read_text(encoding="utf-8") != content:
        raise SystemExit("SHA256SUMS 与当前源码/安装包不一致；请执行 --build。")
    print(f"PASS: {len(expected)} 个发布文件、安装包与 SHA256SUMS 一致")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--skill-dir", default=Path(__file__).resolve().parents[1], type=Path)
    parser.add_argument("--build", action="store_true", help="重建安装包和 SHA256SUMS")
    parser.add_argument("--check", action="store_true", help="仅校验现有安装包和 SHA256SUMS")
    args = parser.parse_args()
    if args.build == args.check:
        parser.error("必须且只能指定 --build 或 --check")
    root = args.skill_dir.resolve()
    version = (root / "VERSION").read_text(encoding="utf-8").strip()
    if not version:
        raise SystemExit("VERSION 不能为空")
    package = root / f"{root.name}-v{version}.skill"
    manifest = root / "SHA256SUMS"
    if args.build:
        build(root, package)
        manifest.write_text(expected_manifest(root, package), encoding="utf-8", newline="\n")
        print(f"BUILT: {package.name}")
    verify(root, package, manifest)


if __name__ == "__main__":
    main()
