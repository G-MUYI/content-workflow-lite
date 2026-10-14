#!/usr/bin/env python3
"""Create ignored personal files from public blank templates without overwriting."""

from pathlib import Path


def initialize(root: Path) -> tuple[int, int]:
    common = root / "skills" / "_通用"
    templates = common / "初始化模板"
    created = retained = 0
    for source in sorted(templates.rglob("*.md")):
        target = common / source.relative_to(templates)
        target.parent.mkdir(parents=True, exist_ok=True)
        try:
            with target.open("x", encoding="utf-8", newline="\n") as output:
                output.write(source.read_text(encoding="utf-8"))
        except FileExistsError:
            retained += 1
            print(f"保留已有文件：{target.relative_to(root)}")
        else:
            created += 1
            print(f"创建空白档案：{target.relative_to(root)}")
    return created, retained


if __name__ == "__main__":
    created, retained = initialize(Path(__file__).resolve().parents[1])
    print(f"初始化完成：创建 {created} 个，保留 {retained} 个。")
