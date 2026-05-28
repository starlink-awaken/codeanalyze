"""Commands package — register all CLI commands for codeanalyze (code-focused)."""
from .analyze_cmd import analyze, deps, docs, graph, report
from .crg_cmd import crg
from .dashboard_cmd import dashboard
from .export_cmd import export
from .install_cmd import install
from .search_cmd import search
from .serve_cmd import serve
from .status_cmd import status


def register_commands(cli):
    """Register all commands on the Click group."""
    cli.add_command(status, "status")
    cli.add_command(analyze, "analyze")
    cli.add_command(graph, "graph")
    cli.add_command(deps, "deps")
    cli.add_command(docs, "docs")
    cli.add_command(report, "report")
    cli.add_command(export, "export")
    cli.add_command(crg, "crg")
    cli.add_command(dashboard, "dashboard")
    cli.add_command(install, "install")
    cli.add_command(search, "search")
    cli.add_command(serve, "serve")
