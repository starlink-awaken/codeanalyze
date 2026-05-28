"""codeanalyze MCP Server — exposes all analysis tools via Model Context Protocol.

Register with Agora:
  agora proxy add codeanalyze --command "python3" --args "-m codeanalyze.mcp"
Or manually via Agora's MCP:
  proxy_add_service(name="codeanalyze", command="python3", args="-m codeanalyze.mcp")
"""

from pathlib import Path

from codeanalyze import __version__
from codeanalyze.integrations.forge import guardrail

try:
    from fastmcp import FastMCP

    mcp = FastMCP(
        f"codeanalyze v{__version__} — Unified Code & Document Analysis",
        mask_error_details=True,
    )
except ImportError:
    raise RuntimeError("fastmcp required: pip install fastmcp")

# Lazy-loaded CRG graph query
from codeanalyze.analyzers.crg_graph import (
    callees as _crg_callees,
)
from codeanalyze.analyzers.crg_graph import (
    callers as _crg_callers,
)
from codeanalyze.analyzers.crg_graph import (
    context as _crg_context,
)
from codeanalyze.analyzers.crg_graph import (
    search as _crg_search,
)


def _resolve(path: str) -> str:
    """Resolve and validate path."""
    return str(Path(path).resolve())


FORMAT_VERSION = "codeanalyze-v1"


def _error(msg: str) -> dict:
    """返回标准错误响应（内建 format_version）。"""
    return {"status": "error", "error": msg, "format_version": FORMAT_VERSION}


def _ok(data: dict) -> dict:
    """返回标准成功响应。data 中应包含 format_version 字段。"""
    return {"status": "ok", **data}


# ── Tools ──


@guardrail(required_steps=["analyze", "export"], max_retries=2)
@mcp.tool()
def analyze_project(path: str = ".") -> dict:
    """Run full analysis pipeline on a project (code + documents).

    Detects project type, runs available analyzers, returns entity-relation graph.

    Args:
        path: Path to the project root directory
    """
    try:
        from codeanalyze.documents.official import analyze_policy_directory
        from codeanalyze.reports.export import policy_graph_to_kg

        root = _resolve(path)
        pg = analyze_policy_directory(root)
        kg = policy_graph_to_kg(pg)

        return _ok({
            "project": Path(root).name,
            "format_version": FORMAT_VERSION,
            "entities": kg.entity_count,
            "relations": kg.relation_count,
            "source_files": len(kg.source_files),
            "summary": {
                "entity_count": kg.entity_count,
                "relation_count": kg.relation_count,
            },
        })
    except Exception as e:
        return _error(str(e))


@guardrail(required_steps=["analyze", "validate"], max_retries=2)
@mcp.tool()
async def export_graph(path: str = ".", output_format: str = "json", code: bool = False) -> dict:
    """Export project knowledge graph in structured format.

    Args:
        path: Project root path
        output_format: json | json-ld | cypher | md
        code: Include code analysis entities (requires graphify)
    """
    try:
        from codeanalyze.reports.export import export_graph as _export

        target = _export(path, output_format, include_code=code)
        return _ok({
            "output_path": target,
            "format_version": FORMAT_VERSION,
            "format": output_format,
        })
    except Exception as e:
        return _error(str(e))


@mcp.tool()
def audit_project(path: str = ".") -> dict:
    """Run knowledge audit — cross-validate raw documents against wiki knowledge base.

    Checks 5 dimensions: policy docs vs policy graph, architecture docs vs knowledge base,
    org files vs ENTITIES.md, platform data vs platform overview, wiki structural integrity.

    Args:
        path: Project root path (must contain _工作机制/wiki directory)
    """
    try:
        from codeanalyze.reports.audit import run_audit

        root = _resolve(path)
        report = run_audit(root)

        return _ok({
            "project": Path(root).name,
            "format_version": FORMAT_VERSION,
            "groups": len(report.groups),
            "total_checks": report.total_checks,
            "passed": report.total_passed,
            "failed": report.total_failed,
            "score": f"{report.score:.0f}%",
            "details": report.to_markdown(),
        })
    except Exception as e:
        return _error(str(e))


@mcp.tool()
def extract_policy_docs(path: str = ".") -> dict:
    """Extract policy document metadata (doc numbers, issuing orgs, dates, levels).

    Scans PDF/DOCX/DOC files and extracts structured metadata using
    regex patterns and pdftotext.

    Args:
        path: Path to policy document directory (e.g. 40-政策法规)
    """
    try:
        from codeanalyze.documents.official import analyze_policy_directory, format_policy_graph_report

        root = _resolve(path)
        graph = analyze_policy_directory(root)

        return _ok({
            "total_docs": graph.total_count,
            "format_version": FORMAT_VERSION,
            "levels": {k: len(v) for k, v in graph.level_groups.items()},
            "domains": {k: len(v) for k, v in graph.domain_groups.items()},
            "report": format_policy_graph_report(graph),
        })
    except Exception as e:
        return _error(str(e))


@mcp.tool()
def status() -> dict:
    """Show installed code analysis and document processing tools."""
    from codeanalyze.core.registry import build_registry

    reg = build_registry()
    tools = {}
    for name, tool in sorted(reg.tools.items()):
        tools[name] = {
            "available": tool.available,
            "version": tool.version or "-",
            "description": tool.description,
        }
    return _ok({
        "version": __version__,
        "format_version": FORMAT_VERSION,
        "tools": tools,
        "available": sum(1 for t in reg.tools.values() if t.available),
        "total": len(reg.tools),
    })


@mcp.tool()
def scan_directory(path: str = ".") -> dict:
    """Scan and analyze a document project directory structure.

    Detects file types, categories (by 00-99 prefix), version chains,
    and wiki structural integrity.

    Args:
        path: Project root path
    """
    try:
        from codeanalyze.documents.scanner import analyze_wiki_structure
        from codeanalyze.documents.scanner import scan_directory as _scan

        root = _resolve(path)
        dm = _scan(root)
        wiki_info = analyze_wiki_structure(root)

        return _ok({
            "project": Path(root).name,
            "format_version": FORMAT_VERSION,
            "total_files": dm.total_files,
            "code_files": dm.code_files,
            "raw_docs": dm.raw_docs,
            "spreadsheets": dm.spreadsheets,
            "wiki_files": dm.wiki_files,
            "version_chains": len(dm.version_chains),
            "wiki_available": wiki_info.get("available", False),
        })
    except Exception as e:
        return _error(str(e))


@mcp.tool()
def crg_status(path: str = ".") -> dict:
    """Get code-review-graph stats (Tree-sitter persistent KG).

    Returns file/node/edge counts from the local SQLite database.
    Zero LLM cost - pure Tree-sitter AST parsing.

    Args:
        path: Project root path
    """
    try:
        from codeanalyze.analyzers import codereviewgraph as crg

        stats = crg.status(path)
        if stats.error:
            # Not installed - return empty
            data = crg.CrgStats()
            return _ok({
                "format_version": FORMAT_VERSION,
                "available": False,
                "error": stats.error,
            })

        return _ok({
            "format_version": FORMAT_VERSION,
            "available": True,
            "total_files": stats.total_files,
            "total_nodes": stats.total_nodes,
            "total_edges": stats.total_edges,
        })
    except Exception as e:
        return _error(str(e))


@mcp.tool()
def crg_build(path: str = ".", force: bool = False) -> dict:
    """Build or rebuild Tree-sitter knowledge graph.

    Parses all code files with Tree-sitter, extracts AST nodes and edges,
    stores result in local SQLite. Supports incremental updates.

    Args:
        path: Project root path
        force: Force full rebuild
    """
    try:
        from codeanalyze.analyzers import codereviewgraph as crg

        stats = crg.build(path, force=force)
        if stats.error:
            return _error(stats.error)

        return _ok({
            "format_version": FORMAT_VERSION,
            "total_files": stats.total_files,
            "total_nodes": stats.total_nodes,
            "total_edges": stats.total_edges,
        })
    except Exception as e:
        return _error(str(e))


@mcp.tool()
def codegraph_search(pattern: str, kind: str | None = None, path: str = ".", limit: int = 20) -> dict:
    """搜索代码符号。从 CRG Tree-sitter 知识图谱中查询，零文件读取。

    类似 CodeGraph 的 codegraph_search 命令。
    比 grep 快，因为有预索引的 SQLite 数据库。

    Args:
        pattern: 符号名称模式（支持 LIKE 通配符）
        kind: 可选，符号类型过滤 (function, class, method, variable 等)
        path: 项目路径
        limit: 最大返回数
    """
    try:
        results = _crg_search(pattern, kind=kind, repo_path=path, limit=limit)
        if results and "error" in results[0]:
            return _error(results[0]["error"])
        return _ok({
            "format_version": FORMAT_VERSION,
            "pattern": pattern,
            "results": results,
            "count": len(results),
        })
    except Exception as e:
        return _error(str(e))


@mcp.tool()
def codegraph_callers(qualified_name: str, path: str = ".", limit: int = 20) -> dict:
    """查询谁调用了指定符号。类似 CodeGraph 的 codegraph_callers。

    从 CRG 知识图谱中追踪上游调用链。
    适用于理解依赖关系和变更影响范围。

    Args:
        qualified_name: 完全限定符号名 (e.g. "module.function_name")
        path: 项目路径
        limit: 最大返回数
    """
    try:
        results = _crg_callers(qualified_name, repo_path=path, limit=limit)
        if results and "error" in results[0]:
            return _error(results[0]["error"])
        return _ok({
            "format_version": FORMAT_VERSION,
            "symbol": qualified_name,
            "callers": results,
            "count": len(results),
        })
    except Exception as e:
        return _error(str(e))


@mcp.tool()
def codegraph_callees(qualified_name: str, path: str = ".", limit: int = 20) -> dict:
    """查询指定符号调用了什么。类似 CodeGraph 的 codegraph_callees。

    从 CRG 知识图谱中追踪下游调用链。
    适用于影响分析、重构前评估。

    Args:
        qualified_name: 完全限定符号名
        path: 项目路径
        limit: 最大返回数
    """
    try:
        results = _crg_callees(qualified_name, repo_path=path, limit=limit)
        if results and "error" in results[0]:
            return _error(results[0]["error"])
        return _ok({
            "format_version": FORMAT_VERSION,
            "symbol": qualified_name,
            "callees": results,
            "count": len(results),
        })
    except Exception as e:
        return _error(str(e))


@mcp.tool()
def codegraph_context(file_path: str, path: str = ".") -> dict:
    """获取文件的完整上下文：符号列表 + 调用关系。

    类似 CodeGraph 的 codegraph_context 命令。
    一次性返回 entry points、相关符号和代码片段。

    Args:
        file_path: 文件路径（支持模糊匹配）
        path: 项目路径
    """
    try:
        results = _crg_context(file_path, repo_path=path)
        if "error" in results:
            return _error(results["error"])
        return _ok({
            "format_version": FORMAT_VERSION,
            "file": file_path,
            "nodes": results.get("nodes", []),
            "callers": results.get("callers", []),
            "callees": results.get("callees", []),
        })
    except Exception as e:
        return _error(str(e))


@mcp.tool()
def rg_search(
    pattern: str,
    path: str = ".",
    fixed_strings: bool = False,
    ignore_case: bool = False,
    max_count: int = 50,
    glob: str | None = None,
) -> dict:
    """Search codebase using ripgrep (fast, structured search).

    Returns structured matches with file paths, line numbers, and context.
    10x faster than grep, respects .gitignore.

    Args:
        pattern: Search pattern (regex or literal)
        path: Search root path
        fixed_strings: Treat pattern as literal string (not regex)
        ignore_case: Case-insensitive search
        max_count: Maximum matches to return
        glob: File glob filter (e.g. "*.py" for Python files)
    """
    try:
        from codeanalyze.analyzers import ripgrep as rg

        result = rg.search(
            pattern=pattern,
            path=path,
            regex=not fixed_strings,
            fixed_strings=fixed_strings,
            ignore_case=ignore_case,
            max_count=max_count,
            glob=glob,
            json_output=True,
        )

        if result.error:
            return _error(result.error)

        return _ok({
            "format_version": FORMAT_VERSION,
            "pattern": result.pattern,
            "total": result.total,
            "elapsed_ms": result.elapsed_ms,
            "matches": [
                {
                    "path": m.path,
                    "line_number": m.line_number,
                    "text": m.text[:200],
                }
                for m in result.matches[:max_count]
            ],
        })
    except Exception as e:
        return _error(str(e))


def main():
    """Run the MCP server in stdio mode (for Agora integration)."""
    mcp.run()


def http_main():
    """Run the MCP server in HTTP mode."""
    import asyncio
    asyncio.run(mcp.run_http_async(host="127.0.0.1", port=8765))


if __name__ == "__main__":
    main()
