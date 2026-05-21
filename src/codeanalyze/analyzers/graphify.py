"""Graphify 分析器 — 语义知识图谱"""

from pathlib import Path
from typing import Optional

from codeanalyze.core.registry import ToolInfo


def analyze(repo_path: str = ".", tool: ToolInfo = None) -> dict:
    """运行 Graphify，返回实体-关系字典。"""
    if tool and not tool.available:
        return {"error": "graphify not installed", "entities": [], "relations": []}

    try:
        from graphify.analyze import analyze_repo
        results = analyze_repo(repo_path)
    except ImportError:
        return {"error": "graphify import failed", "entities": [], "relations": []}
    except Exception as e:
        return {"error": f"graphify analysis failed: {e}", "entities": [], "relations": []}

    entities = []
    for node in results.get("nodes", []):
        entities.append({
            "id": f"code-{node.get('name', '')}",
            "name": node.get("name", ""),
            "type": node.get("type", "Module"),
            "properties": {
                "path": node.get("path", ""),
                "language": node.get("language", ""),
            },
        })

    relations = []
    for edge in results.get("edges", []):
        relations.append({
            "source": f"code-{edge.get('source', '')}",
            "target": f"code-{edge.get('target', '')}",
            "type": edge.get("type", "IMPORTS"),
            "confidence": edge.get("confidence", "EXTRACTED"),
        })

    return {"entities": entities, "relations": relations, "error": None}


def get_report_path(repo_path: str = ".") -> Optional[Path]:
    """返回 graphify 生成的 GRAPH_REPORT.md 路径（如果存在）。"""
    p = Path(repo_path).resolve() / "graphify-out" / "GRAPH_REPORT.md"
    return p if p.exists() else None


def get_graph_html(repo_path: str = ".") -> Optional[Path]:
    p = Path(repo_path).resolve() / "graphify-out" / "graph.html"
    return p if p.exists() else None
