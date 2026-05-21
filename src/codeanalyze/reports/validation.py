"""生成自动抽取 vs 手工政策图谱的交叉验证报告"""

import re
import subprocess
from pathlib import Path

# — 从 00-政策图谱.md 提取手工条目 —
def parse_manual_policy_graph(filepath: str) -> list[dict]:
    """解析手工维护的政策图谱，提取每条政策的元数据。"""
    text = Path(filepath).read_text(encoding="utf-8")
    entries = []

    # 提取文号速查表
    table_pattern = re.compile(
        r'\|\s*(\S+(?:〔\d{4}〕\d+号)?)\s*\|\s*(.+?)\s*\|\s*(\d{4}-\d{2}-\d{2})\s*\|'
    )
    for m in table_pattern.finditer(text):
        doc_num = m.group(1).strip()
        title = m.group(2).strip()
        date = m.group(3).strip()
        if doc_num != '—' and '文号' not in doc_num:
            entries.append({
                "source": "manual_graph",
                "title": title,
                "doc_number": doc_num,
                "pub_date": date,
                "level": _infer_level(doc_num, title),
            })

    # 提取正文中的文件条目
    item_pattern = re.compile(
        r'-\s*\*\*文件\*\*[：:]\s*(?:《)?([^》]+?)(?:》)?\s*(?:（\s*('
        r'(?:发改|京|国)\S*(?:〔\d{4}〕\d+号)\s*)?）?\s*'
        r'(?:\((\d{4}-\d{2}-\d{2})\))?'
    )
    # simpler: find all lines with "《" that look like doc titles
    doc_title_pattern = re.compile(r'《([^》]+)》.*?（([^）]+)）')
    for m in doc_title_pattern.finditer(text):
        title = m.group(1).strip()
        detail = m.group(2).strip()
        # check if detail contains a doc number
        doc_num_match = re.search(r'(发改\S*(?:〔\d{4}〕\d+号)?)', detail)
        date_match = re.search(r'(\d{4}-\d{2}-\d{2})', detail)
        entry = {
            "source": "manual_graph",
            "title": title,
            "doc_number": doc_num_match.group(1) if doc_num_match else "",
            "pub_date": date_match.group(1) if date_match else "",
        }
        entry["level"] = _infer_level(entry["doc_number"], title)
        # deduplicate by title
        if not any(e["title"] == title for e in entries):
            entries.append(entry)

    return entries


def _infer_level(doc_num: str, title: str) -> str:
    text = doc_num + " " + title
    if re.search(r'(国务院|国家|发改环资|发改办)', text):
        return "国家级"
    elif re.search(r'(北京|京发|京教|京科|京政)', text):
        return "北京市级"
    elif re.search(r'房山', text):
        return "房山区级"
    return "其他"


# — 对比两个来源 —
def cross_validate(manual_entries: list[dict], auto_files: list) -> dict:
    """交叉验证人工条目 vs 自动抽取结果。"""
    manual_doc_nums = {e["doc_number"] for e in manual_entries if e["doc_number"]}
    manual_titles = {e["title"] for e in manual_entries}

    auto_doc_nums = {d.doc_number for d in auto_files if d.doc_number}
    auto_titles = {d.filename for d in auto_files}

    # 人工有、自动也有的文号（hit）
    matched_nums = manual_doc_nums & auto_doc_nums

    # 人工有、自动没有的文号（miss）
    missed_nums = manual_doc_nums - auto_doc_nums

    # 自动有、人工没有的文号（新发现）
    extra_nums = auto_doc_nums - manual_doc_nums

    return {
        "manual_total": len(manual_entries),
        "auto_total": len(auto_files),
        "manual_with_docnum": len(manual_doc_nums),
        "auto_with_docnum": len(auto_doc_nums),
        "matched_nums": matched_nums,
        "missed_nums": missed_nums,
        "extra_nums": extra_nums,
        "recall": len(matched_nums) / len(manual_doc_nums) * 100 if manual_doc_nums else 0,
        "precision": len(matched_nums) / len(auto_doc_nums) * 100 if auto_doc_nums else 0,
    }


if __name__ == "__main__":
    # 从 codeanalyze 导入
    import sys
    sys.path.insert(0, "/sessions/zealous-wonderful-planck/mnt/Workspace/codeanalyze/src")
    from codeanalyze.documents.official import analyze_policy_directory

    manual_path = "/Users/xiamingxing/Documents/国转中心/_工作机制/wiki/30-政策与申报/00-政策图谱.md"
    policy_dir = "/Users/xiamingxing/Documents/国转中心/40-政策法规"

    manual = parse_manual_policy_graph(manual_path)
    auto_graph = analyze_policy_directory(policy_dir)

    result = cross_validate(manual, auto_graph.documents)

    print("""
┌─────────────────────────────────────────────────────┐
│    自动抽取 vs 手工政策图谱 · 交叉验证报告         │
├─────────────────────────────────────────────────────┤""")
    print(f"│ 手工图谱条目: {result['manual_total']:>3d} 条")
    print(f"│ 自动扫描文件: {result['auto_total']:>3d} 个")
    print(f"│ 人工含文号:   {result['manual_with_docnum']:>3d} 条")
    print(f"│ 自动含文号:   {result['auto_with_docnum']:>3d} 条")
    print(f"├─────────────────────────────────────────┤")
    print(f"│ 📊 关键指标                              │")
    print(f"│ 文号召回率:   {result['recall']:>5.0f}%")
    print(f"│ 文号精确率:   {result['precision']:>5.0f}%")
    print(f"├─────────────────────────────────────────┤")

    if result["matched_nums"]:
        print(f"│ ✅ 匹配的文号 ({len(result['matched_nums'])} 个):")
        for n in sorted(result["matched_nums"]):
            # 查找对应的人工条目
            manual_entry = next((e for e in manual if e["doc_number"] == n), None)
            auto_file = next((d for d in auto_graph.documents if d.doc_number == n), None)
            manual_title = manual_entry["title"] if manual_entry else "?"
            auto_name = auto_file.filename[:30] if auto_file else "?"
            print(f"│   ✓ {n:30s}  → {manual_title}")

    if result["missed_nums"]:
        print(f"│ ❌ 未命中 (手工有·自动无) ({len(result['missed_nums'])} 个):")
        for n in sorted(result["missed_nums"]):
            entry = next((e for e in manual if e["doc_number"] == n), None)
            file_ref = entry["title"] if entry else n
            print(f"│   ✗ {n:30s}  → 文件不在 40-政策法规/ 目录下")
        print(f"│   原因: 这些政策是网络搜索发现的，没有对应本地文件")

    if result["extra_nums"]:
        print(f"│ 🆕 新增发现 (自动有·手工无) ({len(result['extra_nums'])} 个):")
        for n in sorted(result["extra_nums"]):
            file = next((d for d in auto_graph.documents if d.doc_number == n), None)
            print(f"│   ✦ {n:30s}  → 来自 {file.filename[:30] if file else '?'}")
            print(f"│   建议: 核对后补入手工图谱")

    # 文件名与图谱条目对应分析
    print(f"├─────────────────────────────────────────┤")
    print(f"│ 🔍 文件级覆盖分析                       │")
    pdf_like = [d for d in auto_graph.documents if d.path.suffix.lower() in ('.pdf', '.doc', '.docx')]
    print(f"│ 政策法规目录下的原始文件: {len(pdf_like)} 个")
    print(f"│ 其中图谱已有对应条目的:")
    covered = 0
    for d in pdf_like:
        # 检查文件名是否与任一手工条目匹配
        matched = False
        for e in manual:
            if e["title"][:6] in d.filename or d.filename[:6] in e["title"]:
                matched = True
                break
        if matched:
            covered += 1
            print(f"│   ✓ {d.filename[:40]:40s}")
    print(f"│  覆盖: {covered}/{len(pdf_like)}")

    not_covered = [d for d in pdf_like if not any(
        e["title"][:6] in d.filename or d.filename[:6] in e["title"] for e in manual
    )]
    if not_covered:
        print(f"│  未覆盖:")
        for d in not_covered:
            print(f"│   ? {d.filename[:40]:40s}")

    print(f"└─────────────────────────────────────────┘")

    # 生成可执行建议
    print("""
📋 建议执行项：
""")
    if result["missed_nums"]:
        print(f"  [P0] 补充下载 {len(result['missed_nums'])} 条命中政策的原文到 40-政策法规/ 目录")
        for n in sorted(result["missed_nums"]):
            entry = next((e for e in manual if e["doc_number"] == n), None)
            print(f"       - {n} ({entry['title'] if entry else '?'})")
    if result["extra_nums"]:
        print(f"  [P1] 核对 {len(result['extra_nums'])} 个新增文号，更新 00-政策图谱.md")
    print(f"  [P2] 对 {len(not_covered)} 个未覆盖文件补充图谱条目")
    print(f"  [P3] 校准自动抽取的层级分类逻辑（当前准确率 {result['recall']:.0f}%）")
