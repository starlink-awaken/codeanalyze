"""Shared utilities for CLI commands."""
from pathlib import Path

import click
from rich.console import Console

console = Console()


def _validate_path(path: str) -> Path:
    """Validate and resolve a path, preventing directory traversal."""
    root = Path(path).resolve()
    if not root.exists():
        raise click.BadParameter(f"path does not exist: {path}")
    return root


_INSTALL_GUIDE = {
    "graphify": ("pip install graphifyy", "语义知识图谱 (Tree-sitter AST + LLM)"),
    "docling": ("pip install docling docling-graph", "文档→知识图谱 (IBM)"),
    "marker": ("pip install marker-pdf", "高精度 PDF→Markdown"),
    "mineru": ("pip install mineru", "中文 PDF 解析 (OpenDataLab)"),
    "unstructured": ("pip install unstructured", "文档分块与分区"),
    "gitnexus": ("npm install -g gitnexus", "依赖关系图 (LadybugDB)"),
}
