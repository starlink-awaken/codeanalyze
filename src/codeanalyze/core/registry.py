"""工具可用性注册中心 — 探测本地安装了哪些分析工具"""

import importlib
import os
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class ToolInfo:
    name: str
    description: str
    available: bool = False
    version: Optional[str] = None
    path: Optional[str] = None
    error: Optional[str] = None


@dataclass
class Registry:
    tools: dict[str, ToolInfo] = field(default_factory=dict)

    def __bool__(self) -> bool:
        return any(t.available for t in self.tools.values())


def _check_python_module(mod: str, name: str, desc: str) -> ToolInfo:
    info = ToolInfo(name=name, description=desc)
    try:
        m = importlib.import_module(mod)
        info.available = True
        info.version = getattr(m, "__version__", None)
    except ImportError as e:
        info.error = str(e)
    return info


def _check_cli(cmd: str, name: str, desc: str, version_flag: str = "--version") -> ToolInfo:
    info = ToolInfo(name=name, description=desc)
    cli_path = shutil.which(cmd)
    if not cli_path:
        info.error = f"`{cmd}` not found on PATH"
        return info
    info.path = cli_path
    info.available = True
    try:
        result = subprocess.run(
            [cli_path, version_flag], capture_output=True, text=True, timeout=10
        )
        info.version = result.stdout.strip() or result.stderr.strip() or None
    except Exception:
        pass
    return info


def build_registry() -> Registry:
    """扫描并注册所有可用工具。"""

    reg = Registry()

    # ——— Graphify ———
    reg.tools["graphify"] = _check_python_module(
        "graphify", "graphify", "Semantic code knowledge graph (Tree-sitter AST + LLM)"
    )

    # ——— GitNexus ———
    reg.tools["gitnexus"] = _check_cli(
        "gitnexus", "gitnexus", "Repo dependency graph & call-chain analysis (LadybugDB)"
    )

    # ——— Serena (MCP via CLI) ———
    serena = _check_cli("serena", "serena", "Symbol-level code retrieval & editing (LSP-based MCP)")
    if not serena.available:
        serena2 = _check_python_module("serena_agent", "serena", "Symbol-level code retrieval & editing")
        if serena2.available:
            serena = serena2
    reg.tools["serena"] = serena

    # ——— Docling ———
    reg.tools["docling"] = _check_python_module(
        "docling", "docling", "IBM document → structured data (PDF/Word/HTML)"
    )
    reg.tools["docling_graph"] = _check_python_module(
        "docling_graph", "docling-graph", "IBM Docling → Pydantic → Knowledge Graph (NetworkX)"
    )

    # ——— Marker ———
    reg.tools["marker"] = _check_cli(
        "marker_single", "marker", "PDF → Markdown/JSON/HTML (high accuracy)"
    )

    # ——— Unstructured ———
    reg.tools["unstructured"] = _check_python_module(
        "unstructured", "unstructured", "Document chunking & partition (PDF/HTML/DOCX)"
    )

    # ——— MinerU ———
    reg.tools["mineru"] = _check_python_module(
        "magic_pdf", "mineru", "中文PDF→Markdown/JSON (OpenDataLab, 中文最优)"
    )
    if not reg.tools["mineru"].available:
        reg.tools["mineru"] = _check_cli(
            "magic_pdf", "mineru", "中文PDF→Markdown/JSON (OpenDataLab)"
        )

    # ——— DeepWiki-Open (轻量检测，非 CLI) ———
    dw_url = os.environ.get("DEEPWIKI_OPEN_URL", "")
    if dw_url:
        reg.tools["deepwiki_open"] = ToolInfo(
            name="deepwiki-open",
            description=f"Self-hosted AI Wiki generator (API: {dw_url})",
            available=True,
            version="api",
        )
    else:
        # Check local paths
        for p in [os.path.expanduser("~/Workspace/deepwiki-open"),
                  os.path.expanduser("~/deepwiki-open"),
                  "/opt/deepwiki-open"]:
            if Path(p).joinpath("docker-compose.yml").exists():
                reg.tools["deepwiki_open"] = ToolInfo(
                    name="deepwiki-open",
                    description=f"Self-hosted AI Wiki generator (local: {p})",
                    available=True,
                    version="local",
                    path=p,
                )
                break

    return reg
