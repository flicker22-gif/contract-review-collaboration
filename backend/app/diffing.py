"""合同两版之间的段落级 + 字符级 diff。

段落级对齐用 SequenceMatcher 的 opcodes；`replace` 块内按位置配对为
「修改」段落（一旧对一新），多出来的段落分别记为删除 / 新增。
修改的段落内部再做一次字符级 diff，用于内联高亮，效果接近 Word 修订。
"""

import re
from difflib import SequenceMatcher
from typing import Any

# 英文单词/数字作为一个整体 token，空白单独成 token，其余（如中文）逐字成 token
_TOKEN_RE = re.compile(r"[A-Za-z0-9]+(?:[.][0-9]+)?|\s|[^\sA-Za-z0-9]")


def _tokenize(text: str) -> list[str]:
    return _TOKEN_RE.findall(text)


def _merge(tokens: list[dict[str, str]]) -> list[dict[str, str]]:
    """合并相邻同操作的 token，减少渲染碎片。"""
    merged: list[dict[str, str]] = []
    for tok in tokens:
        if merged and merged[-1]["op"] == tok["op"]:
            merged[-1]["v"] += tok["v"]
        else:
            merged.append({**tok})
    return merged


def inline_diff(old_text: str, new_text: str) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    """返回 (旧版 token 序列, 新版 token 序列)，op ∈ equal/delete/insert。"""
    old_tokens = _tokenize(old_text)
    new_tokens = _tokenize(new_text)
    matcher = SequenceMatcher(None, old_tokens, new_tokens, autojunk=False)

    old_out: list[dict[str, str]] = []
    new_out: list[dict[str, str]] = []
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            value = "".join(old_tokens[i1:i2])
            old_out.append({"op": "equal", "v": value})
            new_out.append({"op": "equal", "v": value})
        elif tag == "delete":
            old_out.append({"op": "delete", "v": "".join(old_tokens[i1:i2])})
        elif tag == "insert":
            new_out.append({"op": "insert", "v": "".join(new_tokens[j1:j2])})
        else:  # replace
            old_out.append({"op": "delete", "v": "".join(old_tokens[i1:i2])})
            new_out.append({"op": "insert", "v": "".join(new_tokens[j1:j2])})

    return _merge(old_out), _merge(new_out)


def diff_paragraphs(
    old_paragraphs: list[str], new_paragraphs: list[str]
) -> dict[str, Any]:
    """对两版段落列表做结构化 diff。

    row 类型：
      - equal:    两版完全一致
      - modified: 一旧对一新，文本不同，带内联 token
      - deleted:  仅旧版存在
      - added:    仅新版存在
    """
    matcher = SequenceMatcher(
        None, old_paragraphs, new_paragraphs, autojunk=False
    )

    rows: list[dict[str, Any]] = []
    stats = {
        "added": 0,
        "deleted": 0,
        "modified": 0,
        "unchanged": 0,
        "added_chars": 0,
        "deleted_chars": 0,
    }

    def add_added(j: int) -> None:
        text = new_paragraphs[j]
        rows.append({"type": "added", "old_idx": None, "new_idx": j, "text": text})
        stats["added"] += 1
        stats["added_chars"] += len(text)

    def add_deleted(i: int) -> None:
        text = old_paragraphs[i]
        rows.append({"type": "deleted", "old_idx": i, "new_idx": None, "text": text})
        stats["deleted"] += 1
        stats["deleted_chars"] += len(text)

    def add_modified(i: int, j: int) -> None:
        old_text = old_paragraphs[i]
        new_text = new_paragraphs[j]
        old_tokens, new_tokens = inline_diff(old_text, new_text)
        rows.append(
            {
                "type": "modified",
                "old_idx": i,
                "new_idx": j,
                "old_text": old_text,
                "new_text": new_text,
                "old_tokens": old_tokens,
                "new_tokens": new_tokens,
            }
        )
        stats["modified"] += 1
        stats["deleted_chars"] += sum(
            len(t["v"]) for t in old_tokens if t["op"] == "delete"
        )
        stats["added_chars"] += sum(
            len(t["v"]) for t in new_tokens if t["op"] == "insert"
        )

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            for k in range(i2 - i1):
                rows.append(
                    {
                        "type": "equal",
                        "old_idx": i1 + k,
                        "new_idx": j1 + k,
                        "text": old_paragraphs[i1 + k],
                    }
                )
                stats["unchanged"] += 1
        elif tag == "insert":
            for j in range(j1, j2):
                add_added(j)
        elif tag == "delete":
            for i in range(i1, i2):
                add_deleted(i)
        else:  # replace：块内按文本相似度配对修改段，其余记增 / 删
            old_range = list(range(i1, i2))
            new_range = list(range(j1, j2))
            sm = SequenceMatcher(autojunk=False)
            scored: list[tuple[float, int, int]] = []
            for i in old_range:
                for j in new_range:
                    sm.set_seqs(old_paragraphs[i], new_paragraphs[j])
                    ratio = sm.ratio()
                    if ratio >= 0.45:  # 低于阈值视为整段删除 + 整段新增
                        scored.append((ratio, i, j))
            # 按相似度从高到低贪心配对，每个旧段 / 新段最多使用一次
            matched_old: set[int] = set()
            matched_new: set[int] = set()
            pairs: list[tuple[int, int]] = []
            for _, i, j in sorted(scored, key=lambda x: x[0], reverse=True):
                if i in matched_old or j in matched_new:
                    continue
                matched_old.add(i)
                matched_new.add(j)
                pairs.append((i, j))
            # 修改段按旧版位置输出，保持阅读顺序
            for i, j in sorted(pairs, key=lambda p: p[0]):
                add_modified(i, j)
            for i in old_range:
                if i not in matched_old:
                    add_deleted(i)
            for j in new_range:
                if j not in matched_new:
                    add_added(j)

    return {"rows": rows, "stats": stats}
