"""公文/政策文档分析器 — 针对中国公文项目的专用分析管线

核心能力：
  1. 政策文档元数据提取（文号/发文机关/层级/日期）
  2. 政策层级归类（国家/部委/北京市/房山区）
  3. 政策间关系发现（引用/隶属/补充）
  4. 与现有 ENTITIES.md / TIMELINE.md / 政策图谱 对接
"""

import re
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


# 政策层级模式
_POLICY_LEVEL_PATTERNS = [
    (r"(?i)(国务院|中共中央|全国人大|国家发改委|教育部|科技部|工信部)", "国家级"),
    (r"(?i)(北京市|京发改|京教科|京政)", "北京市级"),
    (r"(?i)(房山区)", "房山区级"),
]
_POLICY_LEVEL_DEFAULT = "其他"

# 文号模式：京发改规〔2026〕1号 / 发改环资〔2025〕910号 / (2025)910号
_DOC_NUM_PATTERN = re.compile(
    r'([一-鿿]+(?:发改|教|科|环资|规|办|厅|发|人|财|建|能|经信|国资|市监|卫健|政))?'
    r'[〔\(]\s*(\d{4})\s*[〕\)]\s*(\d+)\s*(?:号)?'
)

# 发文日期模式
_DATE_PATTERN = re.compile(
    r"(\d{4})\s*[-年]\s*(\d{1,2})\s*[-月]\s*(\d{1,2})"
)

# 文号在文件名中的模式：〔2026〕2号
_DOC_NUM_FILE_PATTERN = re.compile(
    '〔(\d{4})〕\s*(\d+)\s*号'
)


@dataclass
class PolicyDocument:
    """政策文档的元数据结构"""
    path: Path
    filename: str
    title: str = ""
    doc_number: str = ""  # 文号
    issuing_org: str = ""  # 发文机关
    level: str = _POLICY_LEVEL_DEFAULT
    pub_date: str = ""  # 发布日期
    domain: str = ""  # 业务领域
    keywords: list[str] = field(default_factory=list)
    byte_size: int = 0
    related_policies: list[str] = field(default_factory=list)  # 关联政策
    content_preview: str = ""  # 内容预览（前500字）

    @property
    def full_id(self) -> str:
        return f"doc-{self.filename}"


@dataclass
class PolicyGraph:
    """政策关系图谱"""
    documents: list[PolicyDocument] = field(default_factory=list)
    level_groups: dict[str, list[PolicyDocument]] = field(default_factory=dict)
    domain_groups: dict[str, list[PolicyDocument]] = field(default_factory=dict)
    relationships: list[dict] = field(default_factory=list)  # {source, target, type}
    total_count: int = 0

    @property
    def summary(self) -> str:
        lines = [
            f"📜 政策文档分析报告",
            f"   总文档: {self.total_count}",
        ]
        if self.level_groups:
            lines.append(f"   层级分布:")
            for level, docs in sorted(self.level_groups.items()):
                lines.append(f"     {level}: {len(docs)} 篇")
        if self.domain_groups:
            lines.append(f"   领域分布:")
            for domain, docs in sorted(self.domain_groups.items()):
                lines.append(f"     {domain}: {len(docs)} 篇")
        return "\n".join(lines)


def _guess_level_from_path_or_name(filepath: str, title: str = "") -> str:
    text = filepath + " " + title
    for pattern, level in _POLICY_LEVEL_PATTERNS:
        if re.search(pattern, text):
            return level
    return _POLICY_LEVEL_DEFAULT


def _extract_doc_number(filename: str, content_hint: str = "") -> list[str]:
    """从文件名或内容提取文号。"""
    numbers = []

    # 先从内容提取
    for m in _DOC_NUM_PATTERN.finditer(content_hint or filename):
        org = m.group(1) or ""
        year = m.group(2) or ""
        num = m.group(3) or ""
        numbers.append(f"{org}〔{year}〕{num}号")

    # 再从文件名提取
    for m in _DOC_NUM_FILE_PATTERN.finditer(filename):
        numbers.append(f"〔{m.group(1)}〕{m.group(2)}号")

    # 去重
    seen = set()
    return [n for n in numbers if not (n in seen or seen.add(n))]


def _extract_domain_from_path(filepath: str) -> str:
    """从目录路径推断业务领域。"""
    path_lower = filepath.lower()
    domain_map = [
        ("中小试", "中试平台"),
        ("中试", "中试平台"),
        ("概念验证", "概念验证"),
        ("成果转化", "科技成果转化"),
        ("绿色能源", "绿色能源"),
        ("绿色低碳", "绿色能源"),
        ("节能", "节能环保"),
        ("金融", "金融支持"),
        ("拨投结合", "金融支持"),
        ("人才", "人才培养"),
        ("高校", "高校对接"),
        ("展厅", "展厅资料"),
        ("组织架构", "组织架构"),
    ]
    for keyword, domain in domain_map:
        if keyword in path_lower:
            return domain
    return "通用政策"


def analyze_policy_directory(root_path: str) -> PolicyGraph:
    """扫描政策文档目录，提取元数据并构建关系图谱。"""
    root = Path(root_path).resolve()
    graph = PolicyGraph()

    if not root.is_dir():
        return graph

    # 支持的公文格式
    policy_extensions = {".pdf", ".docx", ".doc", ".txt", ".md"}

    for fp in sorted(root.rglob("*")):
        if not fp.is_file() or fp.suffix.lower() not in policy_extensions:
            continue
        if fp.name == ".DS_Store":
            continue

        rel_path = str(fp.relative_to(root.parent) if fp.relative_to(root.parent) else fp.name)
        filename = fp.stem

        # 基础信息
        doc = PolicyDocument(
            path=fp,
            filename=filename,
            byte_size=fp.stat().st_size,
        )

        # 从文件名提取信息
        doc.title = _clean_title(filename)
        doc.level = _guess_level_from_path_or_name(rel_path, filename)

        # 提取文号
        doc_nums = _extract_doc_number(filename)
        if doc_nums:
            doc.doc_number = doc_nums[0]

        # 提取发文机关（从文件名）
        org_match = re.search(
            r"([一-龥]{2,}(?:部|委|局|办|中心|院|行|公司|大学|集团))",
            filename
        )
        if org_match:
            doc.issuing_org = org_match.group(1)

        # 提取日期（从文件名）
        date_match = _DATE_PATTERN.search(filename)
        if date_match:
            doc.pub_date = f"{date_match.group(1)}-{date_match.group(2).zfill(2)}-{date_match.group(3).zfill(2)}"

        # 从目录推断领域
        doc.domain = _extract_domain_from_path(rel_path)

        # Extract text content from binary formats (docx/doc via LibreOffice, txt/md direct)
        content_text = None
        suffix_lower = fp.suffix.lower()

        if suffix_lower in {".txt", ".md"}:
            try:
                content_text = fp.read_text(encoding="utf-8", errors="ignore")[:800]
            except Exception:
                pass
        elif suffix_lower == ".docx":
            try:
                import zipfile
                with zipfile.ZipFile(fp) as z:
                    xml_content = z.read("word/document.xml")
                    content_text = re.sub(r'<[^>]+>', '', xml_content.decode('utf-8', errors='ignore'))
                    content_text = re.sub(r'\s+', ' ', content_text).strip()[:800]
            except Exception:
                pass
        elif suffix_lower == ".pdf":
            try:
                import subprocess
                result = subprocess.run(
                    ["pdftotext", "-l", "3", str(fp), "-"],
                    capture_output=True, text=True, timeout=15
                )
                if result.stdout:
                    content_text = result.stdout[:800]
            except Exception:
                pass
        elif suffix_lower == ".xlsx":
            try:
                import zipfile
                with zipfile.ZipFile(fp) as z:
                    for sheet_file in [n for n in z.namelist() if n.startswith('xl/worksheets/sheet') and n.endswith('.xml')][:1]:
                        xml = z.read(sheet_file)
                        text = re.sub(r'<[^>]+>', '', xml.decode('utf-8', errors='ignore'))
                        text = re.sub(r'\s+', ' ', text).strip()
                        if text:
                            content_text = text[:800]
            except Exception:
                pass
        elif suffix_lower == ".pptx":
            try:
                import zipfile
                with zipfile.ZipFile(fp) as z:
                    slides = sorted([n for n in z.namelist() if n.startswith('ppt/slides/slide') and n.endswith('.xml')])
                    texts = []
                    for s in slides[:3]:
                        xml = z.read(s)
                        t = re.sub(r'<[^>]+>', '', xml.decode('utf-8', errors='ignore'))
                        t = re.sub(r'\s+', ' ', t).strip()
                        if t:
                            texts.append(t)
                    if texts:
                        content_text = ' | '.join(texts)[:800]
            except Exception:
                pass

        if content_text:
            doc.content_preview = content_text[:500]

            # extract doc numbers
            more_nums = _extract_doc_number(fp.name, content_text)
            if more_nums:
                doc.doc_number = doc.doc_number or more_nums[0]
                doc.related_policies.extend(more_nums[1:])

            # extract issuing org from content
            if not doc.issuing_org:
                org_match = re.search(
                    r"(?:发文|主办|发布|印发)\s*[:：]\s*([一-鿿]{2,}(?:部|委|局|办|中心|院|委员会|领导小组))",
                    content_text
                )
                if org_match:
                    doc.issuing_org = org_match.group(1)

            # extract date from content
            if not doc.pub_date:
                date_match = re.search(
                    r"(\d{4})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日",
                    content_text
                )
                if date_match:
                    doc.pub_date = f"{date_match.group(1)}-{date_match.group(2).zfill(2)}-{date_match.group(3).zfill(2)}"

        # 提取结构化预览（从.txt或.md文件）
        if fp.suffix.lower() in {".txt", ".md"}:
            try:
                text = fp.read_text(encoding="utf-8", errors="ignore")[:800]
                doc.content_preview = text[:500]

                # 从内容提取更多文号和关联政策
                more_nums = _extract_doc_number(fp.name, text)
                if more_nums:
                    doc.doc_number = doc.doc_number or more_nums[0]
                    doc.related_policies.extend(more_nums[1:])

                if not doc.issuing_org:
                    org_match = re.search(
                        r"(?:发文|主办|发布|印发)\s*[:：]\s*([一-鿿]{2,}(?:部|委|局|办|中心|院|委员会|领导小组))",
                        text
                    )
                    if org_match:
                        doc.issuing_org = org_match.group(1)

                if not doc.pub_date:
                    date_match = re.search(
                        r"(\d{4})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日",
                        text
                    )
                    if date_match:
                        doc.pub_date = f"{date_match.group(1)}-{date_match.group(2).zfill(2)}-{date_match.group(3).zfill(2)}"
            except Exception:
                pass

        graph.documents.append(doc)
        graph.total_count += 1

    # 按层级分组
    level_groups = {}
    for doc in graph.documents:
        level_groups.setdefault(doc.level, []).append(doc)
    graph.level_groups = level_groups

    # 按领域分组
    domain_groups = {}
    for doc in graph.documents:
        domain_groups.setdefault(doc.domain, []).append(doc)
    graph.domain_groups = domain_groups

    # 构建政策间关系
    for doc in graph.documents:
        for ref in doc.related_policies:
            graph.relationships.append({
                "source": doc.full_id,
                "target": ref,
                "type": "REFERENCES",
            })

    return graph


def _clean_title(filename: str) -> str:
    """清理文件名，提取可读标题。"""
    # 去掉文号前缀
    title = re.sub(r"〔\d{4}〕\d+号?", "", filename).strip()
    # 去掉常见后缀
    title = re.sub(r"[\s_\-\.]+$", "", title)
    # 去掉常见前缀
    title = re.sub(r"^(附件|附表|附件?：)", "", title).strip()
    return title


def format_policy_graph_report(graph: PolicyGraph) -> str:
    """将政策图谱格式化为 Markdown 报告。"""
    lines = [
        "# 政策文档分析报告",
        "",
        "## 概览",
        f"- 总文档数: {graph.total_count}",
        "",
        "## 层级分布",
    ]

    for level in ["国家级", "部委级", "北京市级", "房山区级", "其他"]:
        docs = graph.level_groups.get(level, [])
        if docs:
            lines.append(f"\n### {level}（{len(docs)} 篇）")
            for doc in sorted(docs, key=lambda d: d.pub_date or "0000"):
                doc_num = f" | {doc.doc_number}" if doc.doc_number else ""
                org = f" | {doc.issuing_org}" if doc.issuing_org else ""
                date = f" | {doc.pub_date}" if doc.pub_date else ""
                lines.append(f"- **{doc.title}**{doc_num}{org}{date}")
                if doc.content_preview:
                    lines.append(f"  > {doc.content_preview[:120]}...")

    if graph.domain_groups:
        lines.append("\n## 领域分布")
        for domain, docs in sorted(graph.domain_groups.items()):
            lines.append(f"- {domain}: {len(docs)} 篇")

    if graph.relationships:
        lines.append("\n## 政策间关系")
        for rel in graph.relationships[:20]:
            lines.append(f"- {rel['source']} → {rel['target']} [{rel['type']}]")

    lines.append("")
    lines.append("---")
    lines.append("*该报告由 codeanalyze documents 命令自动生成。*")

    return "\n".join(lines)
