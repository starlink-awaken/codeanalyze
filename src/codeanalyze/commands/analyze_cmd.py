"""CLI commands: analyze (核心分析命令 + 废弃的 graph/deps/docs/report)"""
from pathlib import Path

import click
from rich.panel import Panel

from codeanalyze.analyzers import gitnexus, graphify
from codeanalyze.commands.common import _validate_path, console
from codeanalyze.core.registry import build_registry
from codeanalyze.core.workspace import detect_workspace
from codeanalyze.documents import pipeline as doc_pipeline
from codeanalyze.reports.generate import generate_summary, write_report


@click.command()
@click.argument("path", default=".")
@click.option("--docs", is_flag=True, help="是否分析文档文件")
@click.option("--output", "-o", default=None, help="报告输出路径")
def analyze(path: str, docs: bool, output: str | None):
    """运行全部分析工具（Graphify + GitNexus + Serena + 可选文档）。"""
    root = _validate_path(path)
    ws = detect_workspace(path)
    reg = build_registry()

    # — 打印工作区摘要 —
    console.print(Panel.fit(
        "\n".join(ws.summary_lines),
        title=f"[bold green]📁 {ws.name}[/]",
        border_style="green",
    ))

    # — Graphify —
    console.print("\n[bold cyan]▶ Graphify 语义图谱分析...[/]")
    g_tool = reg.tools.get("graphify")
    gresult = graphify.analyze(str(root), g_tool) if g_tool else {"error": "graphify not installed"}
    if gresult.get("error"):
        if gresult["error"] == "graphify not installed":
            console.print("  ⏭️ 未安装 (pip install graphifyy)")
        else:
            console.print(f"  [red]❌ {gresult['error']}[/]")
    else:
        console.print(f"  [green]✅ {len(gresult['entities'])} 实体 / {len(gresult['relations'])} 关系[/]")
        type_counts = {}
        for e in gresult.get("entities", []):
            t = e.get("type", "Unknown")
            type_counts[t] = type_counts.get(t, 0) + 1
        for t, c in sorted(type_counts.items(), key=lambda x: -x[1])[:5]:
            console.print(f"    - {t}: {c}")

    # — GitNexus —
    console.print("\n[bold cyan]▶ GitNexus 依赖图分析...[/]")
    gn_tool = reg.tools.get("gitnexus")
    gnresult = gitnexus.analyze(str(root), gn_tool) if gn_tool else {"status": "unavailable"}
    if gnresult.get("status") == "unavailable":
        console.print("  ⏭️ 未安装 (npm install -g gitnexus)")
    elif gnresult.get("status") == "ok":
        console.print("  [green]✅ 索引完成[/]")
    else:
        console.print(f"  [red]❌ {gnresult.get('error', 'failed')}[/]")

    # — Serena —
    console.print("\n[bold cyan]▶ Serena 符号级工具集...[/]")
    console.print("  ⏭️  Serena MCP 工具，在对话中直接使用\n")

    # — Doc analysis —
    doc_result = None
    if docs:
        console.print("\n[bold cyan]▶ 文档分析...[/]")
        doc_result = doc_pipeline.analyze_path(str(root), reg)
        summary = doc_pipeline.format_analysis_summary(doc_result)
        console.print(summary[:1000])
    else:
        console.print("\n[dim]📝 文档分析跳过 (使用 --docs 开启)[/]")

    # — 生成报告 —
    console.print("\n[bold cyan]▶ 生成综合分析报告...[/]")
    report_content = generate_summary(str(root), gresult, gnresult, {}, doc_result)
    report_path = write_report(str(root), report_content, output)
    console.print(f"  [green]✅ 报告已写入: {report_path}[/]")

    console.print(Panel.fit(
        "[bold green]✅ 分析完成[/]\n"
        f"报告: {report_path}\n"
        "💡 在对话中直接使用 Serena MCP 工具进行符号级查询",
        border_style="green",
    ))


# ── 废弃命令（即将移除）──


@click.command()
@click.argument("path", default=".")
def graph(path: str):
    """仅运行 Graphify 语义图谱分析。

    注意: 此命令是 'codeanalyze analyze' 的子集，即将废弃。
    """
    console.print("[yellow]⚠️ 'codeanalyze graph' 即将废弃，请使用 'codeanalyze analyze'[/]")
    root = _validate_path(path)
    reg = build_registry()
    g_tool = reg.tools.get("graphify")
    result = graphify.analyze(str(root), g_tool) if g_tool else {"error": "graphify not installed"}

    if result.get("error"):
        console.print(f"[red]❌ {result['error']}[/]")
        return

    console.print(f"[green]✅ {len(result['entities'])} 实体 / {len(result['relations'])} 关系[/]")
    report = graphify.get_report_path(str(root))
    html = graphify.get_graph_html(str(root))
    if report:
        console.print(f"📄 {report}")
    if html:
        console.print(f"🌐 {html}")


@click.command()
@click.argument("path", default=".")
@click.option("--force", is_flag=True, help="强制重建索引")
def deps(path: str, force: bool):
    """仅运行 GitNexus 依赖图分析。

    注意: 此命令是 'codeanalyze analyze' 的子集，即将废弃。
    """
    console.print("[yellow]⚠️ 'codeanalyze deps' 即将废弃，请使用 'codeanalyze analyze'[/]")
    root = _validate_path(path)
    reg = build_registry()
    tool = reg.tools.get("gitnexus")

    if not tool or not tool.available:
        console.print("[red]❌ GitNexus 未安装. 运行: npm install -g gitnexus[/]")
        return

    if force:
        console.print("[yellow]▶ 强制重建索引 (--force)[/]")

    result = gitnexus.analyze(str(root), tool)
    if result.get("status") == "ok":
        console.print("[green]✅ 索引完成[/]")
        if result.get("stdout"):
            for line in result["stdout"].strip().split("\n")[-3:]:
                console.print(f"  {line}")
    else:
        console.print(f"[red]❌ {result.get('error', 'failed')}[/]")


@click.command()
@click.argument("path", default=".")
@click.option("--output", "-o", default=None, help="输出路径")
def docs(path: str, output: str | None):
    """对文档文件运行结构化分析。

    注意: 此命令是 'codeanalyze analyze --docs' 的子集，即将废弃。
    """
    console.print("[yellow]⚠️ 'codeanalyze docs' 即将废弃，请使用 'codeanalyze analyze --docs'[/]")
    root = _validate_path(path)
    reg = build_registry()
    console.print(f"[bold cyan]▶ 文档分析: {root}[/]")

    result = doc_pipeline.analyze_path(str(root), reg)
    summary = doc_pipeline.format_analysis_summary(result)
    console.print(summary)

    target = output or str(root / "codeanalyze-docs-report.md")
    Path(target).write_text(summary, encoding="utf-8")
    console.print(f"[green]✅ 报告已写入: {target}[/]")


@click.command()
@click.argument("path", default=".")
@click.option("--output", "-o", default=None, help="报告输出路径")
@click.option("--docs", is_flag=True, help="包含文档分析")
def report(path: str, output: str | None, docs: bool):
    """仅生成综合分析报告（不重新运行分析）。"""
    root = _validate_path(path)
    detect_workspace(path)
    reg = build_registry()

    g_tool = reg.tools.get("graphify")
    gn_tool = reg.tools.get("gitnexus")
    g_result = graphify.analyze(str(root), g_tool) if g_tool else {}
    gn_result = gitnexus.analyze(str(root), gn_tool) if gn_tool else {}
    console.print("  ⏭️  Serena MCP 工具，在对话中直接使用\n")
    doc_result = None

    if docs:
        doc_result = doc_pipeline.analyze_path(path, reg)

    content = generate_summary(str(root), g_result, gn_result, {}, doc_result)
    target = write_report(str(root), content, output)
    console.print(f"[green]✅ 报告已写入: {target}[/]")
