"""报告生成与合并 — 跨工具分析结果汇总"""

from pathlib import Path


def generate_summary(
    repo_path: str,
    graphify_result: dict,
    gitnexus_result: dict,
    serena_result: dict,
    doc_result: dict = None,
) -> str:
    """生成跨工具综合分析摘要。"""
    root = Path(repo_path).resolve()
    lines = [
        f"# 代码分析报告 — {root.name}",
        f"> 生成时间: ... | 路径: {root}",
        "",
    ]

    # Graphify
    lines.append("## 📊 Graphify 语义图谱")
    if graphify_result.get("error") and graphify_result["error"] != "graphify import failed":
        lines.append(f"  ❌ {graphify_result['error']}")
    elif graphify_result.get("error"):
        lines.append("  ⏭️ 未安装")
    else:
        entities = graphify_result.get("entities", [])
        relations = graphify_result.get("relations", [])
        lines.append(f"  ✅ {len(entities)} 实体 / {len(relations)} 关系")
        # Top entities by type
        type_counts = {}
        for e in entities:
            t = e.get("type", "Unknown")
            type_counts[t] = type_counts.get(t, 0) + 1
        for t, c in sorted(type_counts.items(), key=lambda x: -x[1])[:8]:
            lines.append(f"    - {t}: {c}")
        graph_path = _find_graphify_report(root)
        if graph_path:
            lines.append(f"    📄 {graph_path.relative_to(root)}")

    # GitNexus
    lines.append("")
    lines.append("## 🔗 GitNexus 依赖图")
    if gitnexus_result.get("status") == "unavailable":
        lines.append("  ⏭️ 未安装")
    elif gitnexus_result.get("status") == "ok":
        lines.append("  ✅ 索引完成")
        if gitnexus_result.get("stdout"):
            last = gitnexus_result["stdout"].strip().split("\n")[-3:]
            for line in last:
                lines.append(f"    {line}")
    else:
        lines.append(f"  ❌ {gitnexus_result.get('error', 'unknown error')}")

    # Serena
    lines.append("")
    lines.append("## 🔍 Serena 符号级分析")
    serena_tools = serena_result.get("tools", [])
    if serena_tools:
        lines.append(f"  ✅ {len(serena_tools)} 个 MCP 工具可用")
        lines.append(f"  💡 在对话中直接使用: {', '.join(serena_tools[:5])}...")
    else:
        lines.append("  ⏭️ 未安装")

    # Doc analysis
    if doc_result and doc_result.get("total_docs", 0) > 0:
        lines.append("")
        lines.append("## 📝 文档分析")
        lines.append(f"  ✅ {doc_result['total_docs']} 文档 / {doc_result['total_words']} 字")
        for f in doc_result.get("files", [])[:5]:
            name = Path(f.get("path", "")).name
            wc = f.get("word_count", 0)
            label = "✅" if wc > 0 else "❌"
            lines.append(f"  {label} {name}: {wc}字")
        if len(doc_result.get("files", [])) > 5:
            lines.append(f"  ... 还有 {len(doc_result['files']) - 5} 个文件")

    # Recommendation
    lines.append("")
    lines.append("## 💡 建议")
    missing = []
    if graphify_result.get("error") is not None:
        pass  # available
    if gitnexus_result.get("status") == "unavailable":
        missing.append("GitNexus (npm install -g gitnexus)")
    if not serena_tools:
        missing.append("Serena MCP")
    if missing:
        lines.append(f"  建议安装: {' / '.join(missing)}")
    else:
        lines.append("  ✅ 所有推荐工具已就绪")

    return "\n".join(lines)


def _find_graphify_report(root: Path) -> Path | None:
    p = root / "graphify-out" / "GRAPH_REPORT.md"
    return p if p.exists() else None


def write_report(repo_path: str, content: str, output: str | None = None) -> str:
    """将报告写入文件。"""
    target = output or str(Path(repo_path).resolve() / "codeanalyze-report.md")
    Path(target).write_text(content, encoding="utf-8")
    return target
