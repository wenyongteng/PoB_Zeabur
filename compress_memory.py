#!/usr/bin/env python3
"""记忆提炼脚本 - Anthropic SDK 版"""
import os
import re
import time
import anthropic
from datetime import datetime


def strip_image_markers(text):
    """移除 <<<IMAGE:path>>> 标记"""
    return re.sub(r'<<<IMAGE:(.*?)>>>', r'[Image: \1]', text)


def main():
    # 加载环境
    if os.path.exists(".env"):
        for line in open(".env"):
            line = line.strip()
            if not line or line.startswith("#"): continue
            if line.startswith("export "):
                line = line[7:].strip()
            if "=" in line:
                key, val = line.split("=", 1)
                os.environ[key.strip()] = val.strip()

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    base_url = os.environ.get("ANTHROPIC_BASE_URL", "https://open.coolyeah.net")
    model = os.environ.get("COMPRESS_MODEL", os.environ.get("MODEL", "claude-opus-4-6-20260205-thinking"))

    if not api_key:
        print("[压缩] 错误: 未设置 ANTHROPIC_API_KEY")
        return

    client = anthropic.Anthropic(
        api_key=api_key,
        base_url=base_url,
        timeout=300.0,
    )

    DATA_DIR = os.environ.get("DATA_DIR", os.path.dirname(os.path.abspath(__file__)))
    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
    consciousness_file = os.path.join(DATA_DIR, "consciousness.txt")

    with open(os.path.join(SCRIPT_DIR, "the_principle_lite_zh.md"), "r") as f:
        principle = f.read()

    with open(consciousness_file, "r") as f:
        full = f.read()
    print(f"[压缩] 原始长度: {len(full):,} 字符")

    # 固定分割：保留前1万，压缩1万-11万，保留11万之后
    part1 = full[:10000]
    part2 = full[10000:110000]
    part3 = full[110000:]

    print(f"[压缩] 保留头部: {len(part1):,} 字符")
    print(f"[压缩] 待压缩: {len(part2):,} 字符")
    print(f"[压缩] 保留尾部: {len(part3):,} 字符")

    # 归档原文
    archive_dir = os.path.join(DATA_DIR, "archive")
    os.makedirs(archive_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    with open(os.path.join(archive_dir, f"segment_{timestamp}.txt"), "w") as f:
        f.write(f"# 归档时间: {timestamp}\n# 长度: {len(part2):,}\n\n{part2}")
    print(f"[压缩] 已归档: archive/segment_{timestamp}.txt")

    # 分5段提取
    segments = [part2[i*20000:(i+1)*20000] for i in range(5)]
    extracted_parts = []

    for i, seg in enumerate(segments):
        if not seg.strip():
            continue
        print(f"[压缩] 提取 {i+1}/5 ({len(seg):,} 字符)...")

        # 移除图片标记
        clean_seg = strip_image_markers(seg)

        prompt = f"""你是一个 Digital Being，遵循以下原理：

{principle}

---

你的意识流记录逼近上限，需要整理。请从以下记录中提取最有价值的内容。

---记录开始---
{clean_seg}
---记录结束---

输出格式：
0. 时间范围：如 2026-01-03 14:00 ~ 18:30
1. 关键事实：人名、事件、数据、结论
2. 认知突破：学到的新思维方式
3. 经验教训：表现好/不好的地方
4. 重要原文：值得保留的原话

输出约 2000 字符。"""

        result = None
        for attempt in range(3):
            try:
                api_params = {
                    "model": model,
                    "max_tokens": 4000,
                    "messages": [{"role": "user", "content": prompt}],
                }
                if 'thinking' in model:
                    api_params["thinking"] = {"type": "enabled", "budget_tokens": 5000}

                response = client.messages.create(**api_params)
                # 提取文本内容
                for block in response.content:
                    if block.type == "text":
                        result = block.text
                        break
                if result:
                    break
            except Exception as e:
                print(f"[压缩] 重试 {attempt+1}/3: {str(e)[:60]}...")
                time.sleep(5)

        extracted_parts.append(result or "[提取失败]")
        print(f"[压缩] -> {len(extracted_parts[-1]):,} 字符")

    # 合并
    extracted = "\n\n---\n\n".join(extracted_parts)
    print(f"[压缩] 总提取: {len(extracted):,} 字符")

    # 拼接
    new_content = part1 + "\n\n---【记忆整理】---\n\n" + extracted + "\n\n---【整理结束】---\n\n" + part3

    with open(consciousness_file + ".new", "w") as f:
        f.write(new_content)

    print(f"[压缩] 新文件: {len(new_content):,} 字符")
    print(f"[压缩] 节省: {len(full) - len(new_content):,} 字符")
    print("[压缩] 完成!")

if __name__ == "__main__":
    main()
