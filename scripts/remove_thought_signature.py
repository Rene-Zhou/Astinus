#!/usr/bin/env python3
"""
删除 JSONL 文件中的 thoughtSignature 键。

用法:
    python scripts/remove_thought_signature.py <input_file> [output_file]

如果不指定 output_file，则直接覆盖原文件。
"""

import json
import sys
from pathlib import Path


def remove_key_recursive(obj: any, key_to_remove: str) -> any:
    """递归删除对象中的指定键。"""
    if isinstance(obj, dict):
        return {
            k: remove_key_recursive(v, key_to_remove)
            for k, v in obj.items()
            if k != key_to_remove
        }
    elif isinstance(obj, list):
        return [remove_key_recursive(item, key_to_remove) for item in obj]
    else:
        return obj


def process_jsonl(input_path: Path, output_path: Path | None = None) -> None:
    """处理 JSONL 文件，删除 thoughtSignature 键。"""
    if output_path is None:
        output_path = input_path

    lines = input_path.read_text(encoding="utf-8").splitlines()
    processed_lines = []

    for i, line in enumerate(lines, 1):
        if not line.strip():
            processed_lines.append(line)
            continue

        try:
            obj = json.loads(line)
            cleaned = remove_key_recursive(obj, "thoughtSignature")
            processed_lines.append(json.dumps(cleaned, ensure_ascii=False))
        except json.JSONDecodeError as e:
            print(f"警告: 第 {i} 行 JSON 解析失败: {e}", file=sys.stderr)
            processed_lines.append(line)

    output_path.write_text("\n".join(processed_lines) + "\n", encoding="utf-8")
    print(f"已处理 {len(lines)} 行，输出到: {output_path}")


def main():
    if len(sys.argv) < 2:
        print("用法: python scripts/remove_thought_signature.py <input_file> [output_file]")
        print("示例: python scripts/remove_thought_signature.py docs/tmp/debug5.jsonl")
        sys.exit(1)

    input_path = Path(sys.argv[1])
    if not input_path.exists():
        print(f"错误: 文件不存在: {input_path}", file=sys.stderr)
        sys.exit(1)

    output_path = Path(sys.argv[2]) if len(sys.argv) > 2 else None

    process_jsonl(input_path, output_path)


if __name__ == "__main__":
    main()
