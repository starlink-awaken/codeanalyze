"""codeanalyze CLI — 统一代码与文档分析入口"""

import json
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from codeanalyze import __version__
from codeanalyze.core.registry import build_registry
from codeanalyze.core.workspace import detect_workspace
from codeanalyze.core.results import Entity, Relation, KnowledgeGraph
from codeanalyze.analyzers import graphify, gitnexus, serena
from codeanalyze.documents import pipeline as doc_pipeline
from codeanalyze.documents.scanner import scan_directory, analyze_wiki_structure
from codeanalyze.documents.deepwiki import (
    check_deepwiki_open,
    generate_wiki_from_analysis,
    trigger_api_wiki_generation,
)
from codeanalyze.documents.official import (
    analyze_policy_directory,
    format_policy_graph_report,
)
from codeanalyze.reports.export import policy_graph_to_kg
from codeanalyze.reports.generate import generate_summary, write_report

console = Console()

_INSTALL_GUIDE = {
    "graphify": ("pip install graphifyy", "语义知识图谱 (Tree-sitter AST + LLM)"),
    "docling": ("pip install docling docling-graph", "文档→知识图谱 (IBM)"),
    "marker": ("pip install marker-pdf", "高精度 PDF→Markdown"),
    "mineru": ("pip install mineru", "中文 PDF 解析 (OpenDataLab)"),
    "unstructured": ("pip install unstructured", "文档分块与分区"),
    "gitnexus": ("npm install -g gitnexus", "依赖关系图 (LadybugDB)"),
}


@cli.command()
@click.option("--all", "-a", "all_flag", is_flag=True, help="安装全部可选依赖")
@click.option("--minimal", is_flag=True, help="仅安装核心依赖")
@click.option("--code", is_flag=True, help="仅安装代码分析工具")
@click.option("--docs", is_flag=True, help="仅安装文档分析工具")
def install(all_flag: bool, minimal: bool, code: bool, docs: bool):
    """一键安装可选分析工具。

    探测缺失工具并打印安装命令。不会自动运行 pip/npm，
    让用户自行选择装哪些。
    """
    from codeanalyze.core.registry import build_registry
    reg = build_registry()

    mode = "all" if all_flag else "code" if code else "docs" if docs else "missing"
    if minimal:
        mode = "minimal"

    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("工具", style="white")
    table.add_column("状态", width=10)
    table.add_column("安装命令")
    table.add_column("说明")

    for name, (cmd, desc) in sorted(_INSTALL_GUIDE.items()):
        tool = reg.tools.get(name)
        installed = tool.available if tool else False
        show = (mode == "all" or mode == "missing" and not installed
                or mode == "code" and name in ("graphify", "gitnexus")
                or mode == "docs" and name in ("docling", "marker", "mineru", "unstructured"))
        if not show and mode not in ("all", "missing", "minimal"):
            continue
        if mode == "minimal" and name not in ("graphify", "docling"):
            continue
        icon = "✅" if installed else "❌"
        table.add_row(name, icon, cmd, desc)

    console.print(table)
    console.print("\n复制需要的命令到终端执行。codeanalyze 会自动检测已安装的工具。")



@click.group()
@click.version_option(version=__version__)
def cli():
    """统一代码与文档分析工具箱。

    将 Graphify、GitNexus、Serena、Docling 等工具
    统一到一个命令入口，支持代码和文档的结构化分析。
    """


@cli.command()
def status():
    """显示已安装/可用的分析工具。"""
    console.print(Panel.fit("[bold cyan]🔍 工具可用性状态[/]", border_style="cyan"))

    registry = build_registry()
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("工具", style="white")
    table.add_column("状态", width=10)
    table.add_column("版本")
    table.add_column("说明")

    for name, tool in sorted(registry.tools.items(), key=lambda x: x[0]):
        status_icon = "✅" if tool.available else "❌"
        version = tool.version or "-"
        table.add_row(name, status_icon, version, tool.description)

    console.print(table)

    available = sum(1 for t in registry.tools.values() if t.available)
    console.print(f"\n{'─' * 50}")
    console.print(f"可用: {available}/{len(registry.tools)} | 路径: {registry.tools.get('gitnexus', '').path or '(N/A)'}")
    if not available:
        console.print("[yellow]💡 建议安装:\n  pip install graphifyy docling docling-graph unstructured\n  npm install -g gitnexus\n  pip install marker-pdf[/]")


@cli.command()
@click.argument("path", default=".")
@click.option("--docs", is_flag=True, help="是否分析文档文件")
@click.option("--output", "-o", default=None, help="报告输出路径")
def analyze(path: str, docs: bool, output: Optional[str]):
    """运行全部分析工具（Graphify + GitNexus + Serena + 可选文档）。"""
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
    gresult = graphify.analyze(path, reg.tools.get("graphify"))
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
    gnresult = gitnexus.analyze(path, reg.tools.get("gitnexus"))
    if gnresult.get("status") == "unavailable":
        console.print("  ⏭️ 未安装 (npm install -g gitnexus)")
    elif gnresult.get("status") == "ok":
        console.print("  [green]✅ 索引完成[/]")
    else:
        console.print(f"  [red]❌ {gnresult.get('error', 'failed')}[/]")

    # — Serena —
    console.print("\n[bold cyan]▶ Serena 符号级工具集...[/]")
    sresult = serena.analyze(path, reg.tools.get("serena"))
    if sresult.get("tools"):
        console.print(f"  [green]✅ {len(sresult['tools'])} 个工具可用[/]")
    else:
        console.print("  ⏭️ 未安装")

    # — Doc analysis —
    doc_result = None
    if docs:
        console.print("\n[bold cyan]▶ 文档分析...[/]")
        doc_result = doc_pipeline.analyze_path(path, reg)
        summary = doc_pipeline.format_analysis_summary(doc_result)
        console.print(summary[:1000])
    else:
        console.print("\n[dim]📝 文档分析跳过 (使用 --docs 开启)[/]")

    # — 生成报告 —
    console.print("\n[bold cyan]▶ 生成综合分析报告...[/]")
    report_content = generate_summary(path, gresult, gnresult, sresult, doc_result)
    report_path = write_report(path, report_content, output)
    console.print(f"  [green]✅ 报告已写入: {report_path}[/]")

    console.print(Panel.fit(
        "[bold green]✅ 分析完成[/]\n"
        f"报告: {report_path}\n"
        "💡 在对话中直接使用 Serena MCP 工具进行符号级查询",
        border_style="green",
    ))


@cli.command()
@click.argument("path", default=".")
def graph(path: str):
    """仅运行 Graphify 语义图谱分析。"""
    reg = build_registry()
    result = graphify.analyze(path, reg.tools.get("graphify"))

    if result.get("error"):
        console.print(f"[red]❌ {result['error']}[/]")
        return

    console.print(f"[green]✅ {len(result['entities'])} 实体 / {len(result['relations'])} 关系[/]")
    report = graphify.get_report_path(path)
    html = graphify.get_graph_html(path)
    if report:
        console.print(f"📄 {report}")
    if html:
        console.print(f"🌐 {html}")


@cli.command()
@click.argument("path", default=".")
@click.option("--force", is_flag=True, help="强制重建索引")
def deps(path: str, force: bool):
    """仅运行 GitNexus 依赖图分析。"""
    reg = build_registry()
    tool = reg.tools.get("gitnexus")

    if not tool or not tool.available:
        console.print("[red]❌ GitNexus 未安装. 运行: npm install -g gitnexus[/]")
        return

    if force:
        console.print("[yellow]▶ 强制重建索引 (--force)[/]")

    result = gitnexus.analyze(path, tool)
    if result.get("status") == "ok":
        console.print("[green]✅ 索引完成[/]")
        if result.get("stdout"):
            for line in result["stdout"].strip().split("\n")[-3:]:
                console.print(f"  {line}")
    else:
        console.print(f"[red]❌ {result.get('error', 'failed')}[/]")


@cli.command()
@click.argument("path", default=".")
@click.option("--output", "-o", default=None, help="输出路径")
def docs(path: str, output: Optional[str]):
    """对文档文件运行结构化分析。"""
    reg = build_registry()
    console.print(f"[bold cyan]▶ 文档分析: {path}[/]")

    result = doc_pipeline.analyze_path(path, reg)
    summary = doc_pipeline.format_analysis_summary(result)
    console.print(summary)

    # 写入文件
    target = output or str(Path(path).resolve() / "codeanalyze-docs-report.md")
    Path(target).write_text(summary, encoding="utf-8")
    console.print(f"[green]✅ 报告已写入: {target}[/]")


from pathlib import Path


@cli.command()
@click.argument("path", default=".")
@click.option("--output", "-o", default=None, help="报告输出路径")
@click.option("--docs", is_flag=True, help="包含文档分析")
def report(path: str, output: Optional[str], docs: bool):
    """仅生成综合分析报告（不重新运行分析）。"""
    ws = detect_workspace(path)
    reg = build_registry()

    # 收集已有数据
    g_result = graphify.analyze(path, reg.tools.get("graphify"))
    gn_result = gitnexus.analyze(path, reg.tools.get("gitnexus"))
    s_result = serena.analyze(path, reg.tools.get("serena"))
    doc_result = None

    if docs:
        doc_result = doc_pipeline.analyze_path(path, reg)

    content = generate_summary(path, g_result, gn_result, s_result, doc_result)
    target = write_report(path, content, output)
    console.print(f"[green]✅ 报告已写入: {target}[/]")


@cli.command()
@click.argument("path", default=".")
@click.option("--wiki", is_flag=True, help="详细分析 wiki 结构完整性")
@click.option("--versions", is_flag=True, help="列出版本链")
@click.option("--output", "-o", default=None, help="报告输出路径")
def docscan(path: str, wiki: bool, versions: bool, output: Optional[str]):
    """扫描文档项目（如国转中心）的结构并生成分析报告。

    自动识别文件类型、分类目录、版本链、wiki 结构完整性.
    适合既有代码又有文档的混合项目.
    """
    root = Path(path).resolve()
    console.print(Panel.fit(f"[bold cyan]📋 文档项目扫描: {root.name}[/]", border_style="cyan"))

    # — 目录扫描 —
    console.print("\n[bold]▶ 扫描目录结构...[/]")
    dm = scan_directory(str(root))
    console.print(dm.summary)

    # — Wiki 结构 —
    wiki_info = None
    if wiki or (root / "_工作机制" / "wiki").is_dir():
        console.print("\n[bold]▶ 分析 Wiki 知识库完整性...[/]")
        wiki_info = analyze_wiki_structure(str(root))
        if wiki_info.get("available"):
            req = wiki_info["required_files"]
            meta = wiki_info["meta_files"]
            console.print(f"  ✅ Wiki 根: {wiki_info['wiki_root']}")
            console.print(f"  核心文件: {req['found']}/{req['total']}")
            if req["missing"]:
                console.print(f"  [yellow]  缺失: {', '.join(req['missing'])}[/]")
            console.print(f"  元文件: {meta['found']}/{meta['total']}")
            console.print(f"  板块: {wiki_info['section_count']} 个")
            if wiki_info["sections"]:
                for s in wiki_info["sections"]:
                    console.print(f"    - {s}")
        else:
            console.print("  ⏭️ 无 _工作机制/wiki 目录")

    # — 版本链 —
    if versions and dm.version_chains:
        console.print(f"\n[bold]▶ 版本链 ({len(dm.version_chains)} 组)[/]")
        for chain in dm.version_chains[:10]:
            base = Path(chain[0].path).stem
            # strip version info for display
            clean_name = base.rsplit("v", 1)[0] if "v" in base else base
            console.print(f"  📎 {clean_name}")
            for doc in chain:
                rel = Path(doc.path).relative_to(root)
                console.print(f"    v{doc.version}: {rel}")
    elif versions:
        console.print("\n[bold]▶ 版本链: 未发现[/]")

    # — 生成完整报告 —
    lines = [
        f"# 文档项目扫描报告 — {root.name}",
        f"> 生成时间: ... | 路径: {root}",
        "",
        "## 目录概览",
        f"- 总文件: {dm.total_files}",
        f"- Wiki 文件: {dm.wiki_files}",
        f"- 原始文档 (PDF/DOCX/DOC): {dm.raw_docs}",
        f"- 表格 (XLSX/XLS): {dm.spreadsheets}",
        f"- 文本 (MD/TXT): {dm.text_files}",
        "",
        "## 分类分布",
    ]
    for cat, files in sorted(dm.categories.items()):
        lines.append(f"- **{cat}**: {len(files)} 文件")
    lines.append("")

    if wiki_info and wiki_info.get("available"):
        lines.extend([
            "## Wiki 知识库",
            f"- 核心文件: {wiki_info['required_files']['found']}/{wiki_info['required_files']['total']}",
            f"- 元文件: {wiki_info['meta_files']['found']}/{wiki_info['meta_files']['total']}",
            f"- 板块数: {wiki_info['section_count']}",
            "",
        ])

    if dm.version_chains:
        lines.append("## 版本链")
        for chain in dm.version_chains[:10]:
            base = Path(chain[0].path).stem
            clean_name = base.rsplit("v", 1)[0] if "v" in base else base
            lines.append(f"- {clean_name}: {' → '.join(f'v{d.version}' for d in chain)}")
        lines.append("")

    # 建议
    lines.extend([
        "## 分析建议",
    ])
    if dm.raw_docs > 0:
        lines.append("- 安装 Docling 将原始文档转为 Markdown: `pip install docling`")
    if dm.spreadsheets > 0:
        lines.append("- XLSX 文件可转为结构化数据，建议用 WPS MCP 或 pandas 抽取")
    if versions and dm.version_chains:
        lines.append("- 版本链较多，建议清理冗余版本或统一版本号规范")
    lines.append("")

    content = "\n".join(lines)
    target = output or str(root / "codeanalyze-docscan-report.md")
    Path(target).write_text(content, encoding="utf-8")
    console.print(f"\n[green]✅ 扫描报告已写入: {target}[/]")

    # 路由建议
    if dm.code_files > 0 and dm.raw_docs > 0:
        console.print(Panel.fit(
            "[bold yellow]🔀 混合项目检测[/]\n"
            "既有代码又有文档，推荐: codeanalyze analyze --docs .\n"
            "先装依赖: pip install graphifyy docling && npm install -g gitnexus",
            border_style="yellow",
        ))
    elif dm.raw_docs > 0:
        console.print(Panel.fit(
            "[bold cyan]💡 文档项目分析建议[/]\n"
            "安装 Docling-Graph 做文档→知识图谱抽取:\n"
            "  pip install docling docling-graph\n"
            "然后: codeanalyze docs .",
            border_style="cyan",
        ))
    elif dm.code_files > 0:
        console.print(Panel.fit(
            "[bold green]💡 代码项目分析建议[/]\n"
            "安装 Graphify + GitNexus 做全链路分析:\n"
            "  pip install graphifyy && npm install -g gitnexus\n"
            "然后: codeanalyze analyze .",
            border_style="green",
        ))


@cli.command()
@click.argument("path", default=".")
@click.option("--output", "-o", default=None, help="Wiki 输出路径")
@click.option("--api", is_flag=True, help="强制使用 DeepWiki-Open API（需设置 DEEPWIKI_OPEN_URL）")
def wiki(path: str, output: Optional[str], api: bool):
    """生成项目 Wiki 文档。

    优先使用 DeepWiki-Open（如已部署），否则基于 Graphify/GitNexus 分析结果
    生成静态 Wiki Markdown。
    """
    reg = build_registry()
    root = Path(path).resolve()
    output_path = Path(output) if output else root / "codeanalyze-wiki.md"

    console.print(Panel.fit(f"[bold cyan]📖 生成项目 Wiki: {root.name}[/]", border_style="cyan"))

    # 检查 DeepWiki-Open
    dw_info = check_deepwiki_open()
    used_deepwiki = False

    if dw_info["available"] and dw_info["mode"] == "api" and api:
        console.print("[green]✅ DeepWiki-Open API 可用[/]")
        console.print("[bold cyan]▶ 调用 API 生成 Wiki...[/]")
        repo_url = f"file://{root}" if not root.name.startswith("http") else str(root)
        result = trigger_api_wiki_generation(repo_url, str(output_path.parent))
        if result.get("status") == "ok":
            console.print(f"[green]✅ Wiki 已生成: {result['output']}[/]")
            return
        else:
            console.print(f"[yellow]⚠️ API 调用失败: {result.get('error', 'unknown')}[/]")
            console.print("[dim]降级到本地生成模式...[/]")
    elif dw_info.get("available"):
        console.print(f"[dim]DeepWiki-Open 已检测到 ({dw_info['mode']}), 使用 --api 调用[/]")

    # 本地生成模式（默认）
    console.print("\n[bold cyan]▶ 收集分析数据...[/]")
    g_result = graphify.analyze(str(root), reg.tools.get("graphify"))
    gn_result = gitnexus.analyze(str(root), reg.tools.get("gitnexus"))

    if g_result.get("error") and g_result["error"] != "graphify not installed":
        console.print(f"  [yellow]Graphify: {g_result['error']}[/]")

    console.print("  [green]✅ 数据收集完成[/]")

    console.print("\n[bold cyan]▶ 生成 Wiki 文档...[/]")
    wiki_content = generate_wiki_from_analysis(
        str(root), graphify_result=g_result, gitnexus_result=gn_result,
    )
    output_path.write_text(wiki_content, encoding="utf-8")
    console.print(f"[green]✅ Wiki 已生成: {output_path}[/]")

    console.print(Panel.fit(
        "[bold green]✅ Wiki 生成完成[/]\n"
        f"输出: {output_path}\n"
        "💡 安装 DeepWiki-Open 可获取 AI 增强版文档:\n"
        "   git clone https://github.com/AsyncFuncAI/deepwiki-open\n"
        "   cd deepwiki-open && docker-compose up\n"
        "   然后: export DEEPWIKI_OPEN_URL=http://localhost:3000\n"
        "   codeanalyze wiki --api .",
        border_style="green",
    ))


@cli.command()
@click.argument("path", default=".")
@click.option("--output", "-o", default=None, help="报告输出路径")
@click.option("--levels", is_flag=True, help="按政策层级分类展示")
def documents(path: str, output: Optional[str], levels: bool):
    """分析公文/政策文档项目（如国转中心政策法规目录）。

    自动提取：
    - 政策元数据（文号/发文机关/日期/层级）
    - 政策层级归类（国家/部委/北京市/房山区）
    - 业务领域分类
    - 政策间关系
    - 与现有政策图谱结构对齐
    """
    root = Path(path).resolve()
    console.print(Panel.fit(f"[bold cyan]📜 公文/政策分析: {root.name}[/]", border_style="cyan"))

    if not root.is_dir():
        console.print("[red]❌ 路径不是目录[/]")
        return

    # 检查是否为政策文档目录
    policy_files = list(root.rglob("*.pdf")) + list(root.rglob("*.docx")) + list(root.rglob("*.doc"))
    if not policy_files:
        console.print("[yellow]⚠️ 未找到政策文档（PDF/DOCX/DOC）。确认路径是否正确？[/]")
        console.print("  建议: codeanalyze documents /Users/xiamingxing/Documents/国转中心/40-政策法规")
        return

    console.print(f"  📄 发现 {len(policy_files)} 个政策文档文件")

    # 运行分析
    console.print("\n[bold cyan]▶ 提取政策元数据...[/]")
    graph = analyze_policy_directory(str(root))
    console.print(graph.summary)

    # 按层级展示
    if levels and "房山区级" in graph.level_groups:
        console.print("\n[bold]按层级分布:[/]")
        for level in ["国家级", "部委级", "北京市级", "房山区级", "其他"]:
            docs = graph.level_groups.get(level, [])
            if docs:
                console.print(f"\n  [underline]{level}[/] ({len(docs)})")
                for doc in docs[:6]:
                    dn = f" | {doc.doc_number}" if doc.doc_number else ""
                    console.print(f"    - {doc.title}{dn}")

    # 生成报告
    report_content = format_policy_graph_report(graph)
    target = output or str(root / "codeanalyze-policy-report.md")
    Path(target).write_text(report_content, encoding="utf-8")
    console.print(f"\n[green]✅ 报告已写入: {target}[/]")

    # 建议
    console.print(Panel.fit(
        "[bold cyan]💡 公文项目分析建议[/]\n"
        "1. 安装 MinerU 提升中文 PDF 解析精度: pip install mineru\n"
        "2. 已有政策图谱(_工作机制/wiki/30-政策与申报/00-政策图谱.md)\n"
        "   可与自动提取结果交叉验证，更新图谱\n"
        "3. Docling-Graph 可用于提取政策实体间深层关系:\n"
        "   pip install docling-graph && codeanalyze docs .",
        border_style="cyan",
    ))


@cli.command()
@click.argument("path", default=".")
@click.option("--format", "-f", "output_format", default="json",
              type=click.Choice(["json", "json-ld", "cypher", "md"]),
              help="输出格式: json(Agent), json-ld(本体), cypher(Neo4j), md(摘要)")
@click.option("--output", "-o", default=None, help="输出文件路径")
@click.option("--code", is_flag=True, default=False, help="包含代码分析引擎数据(Graphify)")
@click.option("--eidos", is_flag=True, default=False, help="转换为 Eidos 兼容格式 + 校验")
@click.option("--pretty", is_flag=True, default=True, help="格式化输出")
def export(path: str, output_format: str, output: Optional[str], code: bool, eidos: bool, pretty: bool):
    """导出结构化知识图谱（JSON/JSON-LD/Cypher/Markdown）。

    将所有分析结果转为统一的 Entity-Relation 模型，
    每个实体带溯源信息（来源文件、提取方法、置信度），
    支持图数据库导入和 Agent 直接消费。

    溯源示例：实体从哪个文件来、用什么方法提取的、置信度多少，
    都在 provenance 字段中可追踪。
    """
    root = Path(path).resolve()
    console.print(Panel.fit(
        f"[bold cyan]📦 导出知识图谱: {root.name}[/]",
        border_style="cyan",
    ))

    from codeanalyze.reports.export import export_graph, policy_graph_to_kg, merge_code_kg
    from codeanalyze.documents.official import analyze_policy_directory

    # 文档引擎
    console.print("  [cyan]▶ 文档分析引擎...[/]")
    pg = analyze_policy_directory(str(root))
    kg = policy_graph_to_kg(pg)
    console.print(f"    ✅ {kg.entity_count} 实体 / {kg.relation_count} 关系 / {len(kg.source_files)} 追溯源文件")

    # 代码引擎（可选）
    if code:
        console.print("  [cyan]▶ 代码分析引擎 (Graphify)...[/]")
        old_count = kg.entity_count
        kg = merge_code_kg(kg, str(root))
        added = kg.entity_count - old_count
        console.print(f"    ✅ 新增 {added} 个代码实体")
        tags = []
        if added > 0:
            tags.append(f"代码分析")
    else:
        tags = []

    tags.append(f"来源文件可追溯: {len(kg.source_files)} 个")
    tags.append(f"关系已语义化: {kg.relation_count} 条")

    # 序列化
    import json
    suffix_map = {"json": ".json", "json-ld": ".jsonld", "cypher": ".cypher", "md": ".md"}
    serializers = {
        "json": lambda: kg.to_json(),
        "json-ld": lambda: json.dumps(kg.to_json_ld(), ensure_ascii=False, indent=2 if pretty else None),
        "cypher": lambda: kg.to_cypher(),
        "md": lambda: _md_summary(kg),
    }

    content = serializers[output_format]()
    suffix = suffix_map[output_format]

    format_labels = {
        "json": "JSON 知识图谱（Agent 消费）",
        "json-ld": "JSON-LD 语义图谱（本体建模）",
        "cypher": "Cypher 导入脚本（Neo4j）",
        "md": "图谱摘要报告（人工阅读）",
    }

    target = output or str(root / f"codeanalyze-export{suffix}")
    Path(target).write_text(content, encoding="utf-8")

    console.print(f"\n  ✅ {format_labels[output_format]}")
    console.print(f"  📄 {target}")
    console.print(f"  📊 {kg.entity_count} 实体 / {kg.relation_count} 关系 / {len(kg.source_files)} 来源文件")

    # Eidos 集成（可选）
    if eidos:
        console.print("\n  [cyan]▶ Eidos 格式转换 + Schema 校验...[/]")
        from codeanalyze.integrations.eidos_adapter import (
            convert_kg, try_eidos_validate, kg_to_eidos_nodes,
            kg_to_eidos_relations, kg_to_eidos_facts, kg_to_eidos_cards,
        )

        eidos_data = convert_kg(kg)
        eidos_target = output or str(root / "codeanalyze-eidos.json")
        import json as _json
        Path(eidos_target).write_text(
            _json.dumps(eidos_data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        console.print(f"  📄 Eidos 输出: {eidos_target}")
        console.print(f"     OntologyNode: {len(eidos_data['ontology_nodes'])}")
        console.print(f"     Relation:     {len(eidos_data['relations'])}")
        console.print(f"     Fact:         {len(eidos_data['facts'])}")
        console.print(f"     KnowledgeCard: {len(eidos_data['cards'])}")

        # 尝试校验
        validation = try_eidos_validate(eidos_data)
        if validation.get("available"):
            console.print("  ✅ Eidos 校验: Schema 可用")
        else:
            console.print(f"  ⏭️  Eidos 校验跳过({validation.get('note', validation.get('error', 'unknown'))})")

        console.print(Panel.fit(
            "[bold green]✅ Eidos 集成完成[/]\n"
            "  集成路径: codeanalyze → Eidos → KOS → OntoDerive\n"
            "  执行: eidos validate codeanalyze-eidos.json --type node",
            border_style="green",
        ))

    # 溯源统计
    with_prov = sum(1 for e in kg.entities.values() if e.provenance)
    console.print(f"  📋 带溯源实体: {with_prov}/{kg.entity_count}")

    console.print(Panel.fit(
        "[bold green]✅ 导出完成[/]\n"
        "  Agent: JSON 格式直接注入 context\n"
        "  本体建模: JSON-LD 兼容语义网工具\n"
        "  图数据库: Cypher 直接导入 Neo4j\n"
        "  溯源追踪: 每个实体标注来源文件和提取方法",
        border_style="green",
    ))


def _md_summary(kg) -> str:
    lines = [
        "# 知识图谱导出报告",
        "## 概览",
        f"- 实体: {kg.entity_count} 个",
        f"- 关系: {kg.relation_count} 条",
        f"- 来源文件: {len(kg.source_files)} 个",
        "",
        "## 实体列表",
    ]
    for e in kg.entities.values():
        prov = f" [来源: {e.provenance.source_file.split('/')[-1] if e.provenance else '-'}]"
        lines.append(f"- [{e.type}] **{e.name}** (域: {e.domain}, 置信: {e.confidence}){prov}")
    lines.extend(["", "## 关系列表"])
    for i, r in enumerate(kg.relations):
        if i >= 60:
            lines.append(f"  ... 还有 {len(kg.relations) - 60} 条")
            break
        src = kg.entities.get(r.source_id)
        tgt = kg.entities.get(r.target_id)
        sn = src.name if src else r.source_id[:30]
        tn = tgt.name if tgt else r.target_id[:30]
        lines.append(f"- {sn} --[{r.type}]--> {tn}")
    lines.extend(["", "## 来源文件"])
    for sf_path, info in kg.source_files.items():
        name = sf_path.split("/")[-1]
        lines.append(f"- {name} (分析器: {info['analyzer']})")
    return "\n".join(lines)


if __name__ == "__main__":
    cli()
