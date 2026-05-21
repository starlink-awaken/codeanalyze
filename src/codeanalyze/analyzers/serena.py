"""Serena 分析器 — 符号级代码检索 (通过 MCP / LSP)"""

from codeanalyze.core.registry import ToolInfo


def analyze(repo_path: str = ".", tool: ToolInfo = None) -> dict:
    """Serena 是 MCP 工具，不在 CLI 层面直接调用。
    此函数返回指导信息，帮助 Agent 在上下文中直接使用 Serena MCP tools。
    """
    if tool and not tool.available:
        return {"error": "serena not available", "instructions": ""}

    return {
        "note": "Serena 通过 MCP 协议在 Agent 运行时直接使用",
        "instructions": (
            "在对话中直接使用以下 Serena MCP 工具：\n"
            "  - find_symbol: 查找符号定义\n"
            "  - find_referencing_symbols: 查找谁引用了某个符号\n"
            "  - get_symbols_overview: 文件符号概览\n"
            "  - find_declaration: 查找声明位置\n"
            "  - find_implementations: 查找接口实现\n"
            "  - replace_symbol_body: 安全替换符号内容\n"
            "  - rename_symbol: 跨文件符号重命名\n"
        ),
        "tools": [
            "find_symbol", "find_referencing_symbols",
            "get_symbols_overview", "find_declaration",
            "find_implementations", "replace_symbol_body",
            "rename_symbol", "safe_delete_symbol",
        ],
    }
