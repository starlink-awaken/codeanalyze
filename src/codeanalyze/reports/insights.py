"""代码洞察分析 — 基于 CRG、GitNexus 数据生成架构洞见。"""

import re
from pathlib import Path


# SharedBrain 架构层级约束
_LAYER_RULES = [
    ("organs", "nucleus/Z-Microkernel", "器官依赖微内核"),
    ("nucleus/Z-Microkernel", "nucleus/Z-Core", "微内核依赖核心"),
    ("nucleus/Z-Core", "nucleus/Z-Spore", "核心依赖基因组"),
]

# 排除路径模式
_EXCLUDE_DIRS = {".venv", "node_modules", "__pycache__", ".git", ".worktrees",
                 ".omc", ".benchmarks", ".hypothesis", ".pytest_cache",
                 ".ruff_cache", ".mypy_cache", ".graphify", ".gitnexus",
                 ".serena", ".runtime", ".sessions", ".agent", "tmp",
                 "logs", "graphify-out", "forge-mcp"}


def _should_include(path: Path, root: Path) -> bool:
    """检查是否应该包含此路径（排除系统/生成目录）。"""
    for part in path.relative_to(root).parts:
        if part in _EXCLUDE_DIRS:
            return False
    return True


def analyze(project_path: str, crg_result: dict, gitnexus_result: dict) -> list[dict]:
    """运行所有洞察分析，返回洞察项列表。

    每项: {severity, category, title, detail}
    severity: insight | warning | critical
    """
    root = Path(project_path).resolve()
    insights = []

    insights.extend(_file_size_insights(root))
    insights.extend(_docstring_coverage(root))
    insights.extend(_layer_check(root))
    insights.extend(_import_safety(root))
    insights.extend(_dep_health(gitnexus_result))

    return insights


def _file_size_insights(root: Path) -> list[dict]:
    """找出超大文件和空文件。"""
    results = []
    large_files = []
    empty_files = []
    for f in sorted(root.rglob("*.py")):
        if not f.is_file() or not _should_include(f, root):
            continue
        try:
            size = f.stat().st_size
            if size == 0:
                empty_files.append(f)
            elif size > 100_000:
                large_files.append((f, size))
        except OSError:
            pass
        if len(large_files) >= 5 and len(empty_files) >= 3:
            break

    if large_files:
        paths = []
        for f, s in sorted(large_files, key=lambda x: -x[1])[:5]:
            rel = _relative(f, root)
            kb = s / 1024
            paths.append(f"{rel} ({kb:.0f}KB)")
        results.append({
            "severity": "warning",
            "category": "代码规模",
            "title": f"超大文件 ({len(large_files)} 个 >100KB)",
            "detail": "\n".join(paths),
        })

    if empty_files:
        paths = "\n".join(_relative(f, root) for f in empty_files[:8])
        results.append({
            "severity": "insight",
            "category": "代码异常",
            "title": f"空文件 ({len(empty_files)} 个)",
            "detail": paths,
        })
    return results


def _docstring_coverage(root: Path) -> list[dict]:
    """估算模块/函数文档覆盖率。"""
    total_modules = 0
    with_docstring = 0
    for f in sorted(root.rglob("*.py")):
        if not f.is_file() or not _should_include(f, root) or f.name == "__init__.py":
            continue
        total_modules += 1
        try:
            text = f.read_text("utf-8", errors="ignore")
            if text.strip().startswith(('"""', "'''", '# ---', '# domain:')):
                with_docstring += 1
        except OSError:
            pass
        if total_modules >= 3000:
            break

    if total_modules > 0:
        pct = with_docstring / total_modules * 100
        sev = "critical" if pct < 20 else "warning" if pct < 50 else "insight"
        results = [{
            "severity": sev,
            "category": "文档覆盖",
            "title": f"文档覆盖率: {pct:.0f}% ({with_docstring}/{total_modules})",
            "detail": (
                "文件无模块级文档" if pct < 20
                else "文档覆盖偏低" if pct < 50
                else "文档覆盖良好"
            ),
        }]
        return results
    return []


def _layer_check(root: Path) -> list[dict]:
    """检查架构层级依赖是否违规。

    层级顺序（从底到顶）：Spore → Core → Microkernel → organs
    违规 = 高层引用了低层（即反向依赖）。
    """
    import re
    results = []
    violations = []

    # 每条规则表示：low → high 是允许的
    # 违规判断：high 中的文件引用了 low 的内容
    for f in sorted(root.rglob("*.py")):
        if not f.is_file() or not _should_include(f, root):
            continue
        try:
            text = f.read_text("utf-8", errors="ignore")
        except OSError:
            continue
        rel = _relative(f, parent=root)
        if not rel:
            continue

        for low, high, desc in _LAYER_RULES:
            # 如果文件在高层，检查是否引用了低层
            if high not in rel:
                continue
            # 找 import 引用了低层路径
            low_dotted = low.replace("/", ".")
            low_slashed = low.replace("/", "/")
            if low_dotted in text or low_slashed in text:
                violations.append(f"{rel} 反向依赖: {desc} ({high} → {low})")
                break
        if len(violations) >= 5:
            break

    if violations:
        results.append({
            "severity": "critical",
            "category": "架构",
            "title": f"层级依赖违规 ({len(violations)} 处)",
            "detail": "\n".join(violations[:5]),
        })
    return results


def _import_safety(root: Path) -> list[dict]:
    """检查不安全导入模式。"""
    results = []
    unsafe = []

    import re
    for f in sorted(root.rglob("*.py")):
        if not f.is_file() or not _should_include(f, root):
            continue
        try:
            text = f.read_text("utf-8", errors="ignore")
        except OSError:
            continue
        # sys.path.insert/modification
        if re.search(r'sys\.path\.(insert|append)', text):
            unsafe.append(f"sys.path 修改: {_relative(f, root)}")
        # except: pass (bare except)
        bare = re.findall(r'^except\s*:', text, re.MULTILINE)
        if bare:
            unsafe.append(f"裸 except: {_relative(f, root)} ({len(bare)} 处)")
        if len(unsafe) >= 5:
            break

    if unsafe:
        results.append({
            "severity": "warning",
            "category": "代码安全",
            "title": f"不安全模式 ({len(unsafe)} 处)",
            "detail": "\n".join(unsafe[:5]),
        })
    return results


def _dep_health(gitnexus_result: dict) -> list[dict]:
    """基于 GitNexus 数据判断依赖健康度。"""
    results = []
    stdout = gitnexus_result.get("stdout", "")
    if not stdout:
        return results

    m_nodes = re.search(r"([\d,]+)\s*nodes?", stdout)
    m_edges = re.search(r"([\d,]+)\s*edges?", stdout)
    m_clusters = re.search(r"([\d,]+)\s*clusters?", stdout)

    nodes = int(m_nodes.group(1).replace(",", "")) if m_nodes else 0
    edges = int(m_edges.group(1).replace(",", "")) if m_edges else 0
    clusters = int(m_clusters.group(1).replace(",", "")) if m_clusters else 0

    if nodes > 0:
        density = edges / nodes if nodes else 0
        detail = f"边/节点比: {density:.2f}"
        sev = "insight"
        if density > 5:
            sev = "warning"
            detail += " — 依赖密度偏高，模块间耦合可能过紧"
        elif density < 1:
            sev = "insight"
            detail += " — 依赖稀疏，模块相对独立"
        results.append({
            "severity": sev,
            "category": "依赖健康",
            "title": f"依赖密度: {density:.2f} ({edges} 边/{nodes} 节点)",
            "detail": detail,
        })

    if clusters > 100:
        results.append({
            "severity": "insight",
            "category": "模块分析",
            "title": f"社区数: {clusters}",
            "detail": f"{clusters} 个功能模块/社区，平均 {nodes//clusters if clusters else 0} 节点/社区",
        })

    return results


def _relative(path: Path, parent: Path) -> str:
    """获取相对路径字符串。"""
    try:
        return str(path.relative_to(parent))
    except ValueError:
        return path.name


def format_insights(insights: list[dict]) -> str:
    """格式化洞察为 Markdown。"""
    lines = []
    for ins in insights:
        icon = {"insight": "💡", "warning": "⚠️", "critical": "🔴"}.get(ins["severity"], "💡")
        lines.append(f"  {icon} **[{ins['category']}]** {ins['title']}")
        if ins.get("detail"):
            for d in ins["detail"].split("\n")[:3]:
                lines.append(f"    {d}")
    return "\n".join(lines)
