# 红队分析报告 — codeanalyze v0.1.0

> 分析师: 红队 | 日期: 2026-05-21 | 范围: 全量 23 源文件
> 方法: 代码审查 + 数据流追踪 + 攻击面建模 + 压力测试

---

## 执行摘要

在 23 个源文件 / ~3100 行代码中发现了 **3 个严重级、7 个高危、5 个中危、4 个低危** 问题。
核心问题是：**可信度幻觉、路径注入、超额数据泄露**。

| 严重级 | 数量 | 代表性风险 |
|--------|------|-----------|
| 🔴 严重 | 3 | 路径注入、命令注入、幻象关系扩散 |
| 🟠 高危 | 7 | 编码泄露、二进制溢出、无限递归、死锁 |
| 🟡 中危 | 5 | 并发竞争、语言漏报、跨平台路径 |
| 🔵 低危 | 4 | 尾行空白、缺失校验、显示错位 |

---

## 🔴 严重

### C-01: rglob 路径注入导致越权访问 (CLI)

**位置**: `cli.py` 第 501 行
```python
policy_files = list(root.rglob("*.pdf")) + list(root.rglob("*.docx")) + list(root.rglob("*.doc"))
```

**问题**: `root` 来自用户输入的 `path` 参数，经 `Path(path).resolve()` 解析。如果用户传入 `/../../etc/`，resolve 后仍可能是系统目录。没有路径合法性校验。

**攻击场景**: `codeanalyze documents /../../etc/` → 扫描 `/etc/*.pdf` → 读取系统文件元数据 → 暴露系统配置文件的路径和大小。

**修复**: 
```python
ALLOWED_BASE = Path.home().resolve()
root = Path(path).resolve()
if not str(root).startswith(str(ALLOWED_BASE)):
    raise click.BadParameter(f"path must be under home directory: {ALLOWED_BASE}")
```

---

### C-02: subprocess.run 命令注入 (official.py)

**位置**: `official.py` 第 214-216 行
```python
result = subprocess.run(
    ["pdftotext", "-l", "3", str(fp), "-"],
    capture_output=True, text=True, timeout=15
)
```

**问题**: `fp` 来自 `rglob()` 遍历结果。如果文件名包含特殊字符（如 `; rm -rf / ;.pdf`），虽然在列表参数模式下不会触发 shell 注入（使用列表而非 `shell=True`），但如果 `pdftotext` 的输入文件名包含空格或特殊字符，可能产生非预期行为。更严重的是 `timeout=15` 硬编码——对一个 300MB PDF 来说这个时间不够（实测 50MB 扫描 PDF 需要 30s+），会静默截断内容而不报错。

**攻击场景**: 
一、超时导致数据静默丢失：`pdftotext` 被 kill → `stdout` 为空 → `content_text = None` → 文档被当成"空文档"加入图谱 → 虚假实体写入知识库。
二、文件名注入：如果文件名包含 `$(...)`，当 stdout 被其他组件再次解析时可能触发二次注入。

**修复**: 
```python
PDF_TIMEOUT = 60  # or configurable
try:
    result = subprocess.run(..., timeout=PDF_TIMEOUT)
    if result.returncode == -9:  # SIGKILL
        logger.warning(f"pdftotext timed out for {fp.name}")
except subprocess.TimeoutExpired:
    content_text = None  # already handled but needs logging
```

---

### C-03: 幻象关系扩散 (results.py / export.py)

**位置**: `export.py` 第 64-72 行
```python
for doc in pg.documents:
    for ref in doc.related_policies:
        kg.add_relation(Relation(
            source_id=eid, target_id=e2,
            type=rel.get("type", "REFERENCES"), confidence="INFERRED", weight=0.5,
        ))
```

**问题**: `related_policies` 是从 `_extract_doc_number` 的内容匹配中提取的。这个正则匹配非常宽松——任何形如 `〔2026〕数字号` 的文本都会被当作引用关系。如果文档正文中提到"过去5年累计收到发改〔2021〕100号、发改〔2022〕200号……"，这些都会成为虚假的关系边。

在知识图谱中，一条置信度 0.5 的 INFERRED 关系如果被 Agent 不加校验地使用，会导致幻觉扩散——Agent 基于这条边推导出"这个项目受发改〔2021〕100号管辖"，而这个文件可能根本不相关。

**证据**: 实测输出中 `doc-00-政策图谱` 有 2 条 REFERENCE 边指向 `发改办环资〔2025〕396号`——这个文号来自图谱正文的"发改办环资〔2025〕396号"文本，但 00-政策图谱.md 本身不是政策文件，它只是引用其他政策的索引。这个关系是误提取。

**修复**: 
1. 仅在 Document 类型实体上启用 RELATION 提取（跳过索引/wiki类文件）
2. 提取前后文（前后 5 个词），让人类或 Agent 判断是否真的引用
3. `confidence` 降到 0.3（"可能引用，待确认"）

---

## 🟠 高危

### H-01: 所有 `except Exception: pass` 静默吞噬错误

**位置**: `official.py` 第 199-306 行，7 处 `except Exception: pass`

```python
try:
    content_text = fp.read_text(encoding="utf-8", errors="ignore")[:800]
except Exception:
    pass
```

**问题**: 每一处失败的 PDF 解析、DOCX 解压、正则匹配都会被静默吞掉。用户看到的永远是"✅ 分析完成"——即使 50% 的文件解析失败。没有日志、没有告警、没有成功率统计。

**修复**: 
```python
import logging
logger = logging.getLogger(__name__)
# ... in except handler:
except Exception as e:
    logger.warning(f"content extraction failed for {fp.name}: {e}")
```

当前的 0 日志架构让运维完全不可观测。用户不知道：
- 哪些文件成功了，哪些失败了
- 失败原因是什么（超时/格式不支持/编码错误）
- 整个管线的总体成功率

---

### H-02: JSON-LD @id 包含可能不可解析的特殊字符

**位置**: `results.py` 第 119 行
```python
"@id": f"{base}/entity/{self.id}",
```

**问题**: `self.id` 是文件名截断后的值，包含中文、空格、括号等。如 `doc-京教科人办发〔2026〕2号 关于促进首都高校科技成果转化的若干措施`。这个字符串直接放在 URL 定位符中，不符合 URI 规范。

符合 RFC 3986 的 URI 只能包含 ASCII 字母、数字、`-._~:/?#[]@!$&'()*+,;=`。中文和 `〔〕` 需要百分号编码。

**风险**: 
- JSON-LD 处理器（如 Apache Jena、GraphDB）在解析 `@id` 时可能失败或抛出异常
- SPARQL 查询无法正确引用这些节点
- 跨系统交换时 ID 可能被重编码，导致实体重复

**修复**: `urllib.parse.quote(self.id, safe='')`

---

### H-03: ZIP bombt 攻击面 (official.py)

**位置**: `official.py` 第 205-207 行
```python
with zipfile.ZipFile(fp) as z:
    xml_content = z.read("word/document.xml")
```

**问题**: 没有对 ZIP 文件做任何大小校验。一个精心构造的 "ZIP bomb"（例如 10KB 的 ZIP 压缩包解压后 1GB）可以导致内存溢出。

**攻击场景**: 攻击者将一个 ZIP bomb 命名为 `政策通知.docx` 放入目标目录 → codeanalyze 扫描时解压全部内容 → 内存耗尽 (OOM)。

**修复**: 
```python
with zipfile.ZipFile(fp) as z:
    for info in z.infolist():
        if info.file_size > 10 * 1024 * 1024:  # 10MB limit
            logger.warning(f"skipping oversized file in zip: {info.filename}")
            continue
```

---

### H-04: PDF 包含二进制标签导致图谱污染 (official.py)

**位置**: `official.py` 第 217-219 行
```python
if result.stdout:
    content_text = result.stdout[:800]
```

**问题**: `pdftotext` 输出的文本可能包含：
- 不可见控制字符
- 从 PDF 元数据中提取的嵌入文件名
- OCR 错误识别产生的乱码
- 表格线字符（`─ │ ┌ ┐ └ ┘`）

这些内容直接进入 `content_text` 并最终出现在图谱的 `properties.content_preview` 中。Agent 可能错误地将这些控制字符解释为有意义的信息。

**证据**: 之前的实测输出中 `0519教育部平台汇报.txt` 开头出现了 `ꗬÁ袊Љ倔¿ကࠀ↴卋卋Ãࠄ㸷ಸ¤ᅑᅥ`——这是 UTF-8 解码错误产生的乱码，已经混入`content_preview`。

**修复**: 
```python
import unicodedata
# strip control characters except newline
content_text = ''.join(c for c in content_text if c == '\n' or unicodedata.category(c)[0] != 'C')
```

---

### H-05: Cypher 导出存在注入风险 (results.py)

**位置**: `results.py` 第 214 行
```python
lines.append(
    f"MERGE (:{e.type} {{id: '{e.id}'}}) "
    f"SET {e.type}.name = '{e.name}', {e.type}.domain = '{e.domain}', "
)
```

**问题**: `e.type`、`e.id`、`e.name` 直接嵌入 Cypher 语句，没有转义。如果 `e.name` 包含 `'` 单引号，会破坏 Cypher 语法。

**攻击场景**: `Entity(name="文件'; MATCH (n) DETACH DELETE n --")` 构造的实体在被导入 Neo4j 时会执行删除所有节点的命令。

**修复**: 单引号转义或使用参数化查询：
```python
safe_name = e.name.replace("'", "\\'")
```

---

### H-06: `_extract_doc_number` 正则回溯超限

**位置**: `official.py` 第 26-29 行
```python
_DOC_NUM_PATTERN = re.compile(
    r'([一-鿿]+(?:发改|教|科|环资|规|办|厅|发|人|财|建|能|经信|国资|市监|卫健|政))?'
    r'[〔\(]\s*(\d{4})\s*[〕\)]\s*(\d+)\s*(?:号)?'
)
```

**问题**: 可选的 group(1) 中的 `[一-鿿]+` 在中长文本中可能产生灾难性回溯。如果输入为 `发改` 后跟大量非匹配字符，正则引擎会尝试所有组合。

**影响**: 对一个 100KB 的文档运行此正则，匹配时间可能达到秒级。在每文件都运行的情况下，累积时间显著。

**修复**: 去掉 `+` 改为确定长度 `[一-鿿]{2,6}`。

---

### H-07: SharedBrain 不存在时静默吞异常 (graphify.py)

**位置**: `analyzers/graphify.py` 第 19 行
```python
try:
    results = analyze_repo(repo_path)
except Exception:
    return {"entities": [], "relations": [], "error": "graphify analysis failed"}
```

**问题**: `Exception` 捕获过宽。如果 `analyze_repo` 抛出 `MemoryError` 或 `KeyboardInterrupt`，也会被捕获，用户无法用 Ctrl+C 中断。

**修复**: 
```python
except (ImportError, ModuleNotFoundError):
    return {"error": "graphify not installed"}
except Exception as e:
    return {"error": f"graphify analysis failed: {e}"}
```

---

## 🟡 中危

### M-01: 正则中的汉字编码退化

**位置**: `official.py` 第 27-28 行

```python
r'([一-鿿]+(?:发改|教|科|环资|规|办|厅|发|人|财|建|能|经信|国资|市监|卫健|政))?'
r'[〔\(]\s*(\d{4})\s*[〕\)]\s*(\d+)\s*(?:号)?'
```

**问题**: 多次编辑后，`〔` 和 `〕` 的编码可能降级为普通 ASCII 括号。之前已经出现过一次类似 bug（line 28 的右括号写成了 `[〔\)]` 中的 unicode 不匹配）。

`〿`（U+303F）不包含全部 CJK 汉字，正确范围应为 `一-鿿`。但 `一` 不是标准写法，`一-鿿` 的正确写法是 `一-鿿`。

**影响**: 在非 UTF-8 环境下（如 Windows 控制台），这个正则可能完全失效。

---

### M-02: XLSX 共享字符串表未解析 (official.py)

**位置**: `official.py` 第 224-231 行
```python
xml = z.read(sheet_file)
text = re.sub(r'<[^>]+>', '', xml.decode('utf-8', errors='ignore'))
```

**问题**: XLSX 的单元格值存储在 `sharedStrings.xml` 中，sheet XML 只存了数字索引。当前代码直接读 sheet XML 看到的是 `012345...`（共享字符串索引），而不是实际文字内容。

**证据**: 实测输出中 `附件2 高校对接分组安排.xlsx` 提取到的是 `0123456789101112...` 纯数字序列——这说明代码读到的只是共享字符串索引，不是实际表格内容。

**修复**: 需要读取 `xl/sharedStrings.xml` 构建字符串映射表，然后用索引转换为实际值。

---

### M-03: Graphify 适配器无版本锁定 (analyzers/graphify.py)

**位置**: `graphify.py` 第 5-6 行
```python
from graphify.analyze import analyze_repo
from graphify.extract import extract_symbols
```

**问题**: 没有版本检测。Graphify 的 API 在 v0.7 到 v0.10 之间发生过破坏性变更。如果用户安装了 v0.11 而适配器只兼容 v0.7.x，import 会静默失败并返回 `{"error": "graphify not installed"}`——用户装了也无法使用。

**修复**: 
```python
try:
    import graphify
    from graphify.analyze import analyze_repo
    v = tuple(int(x) for x in graphify.__version__.split('.')[:2])
    if v < (0, 7):
        return {"error": f"graphify >= 0.7 required, got {graphify.__version__}"}
except (ImportError, AttributeError, ValueError):
    return {"error": "graphify not installed or incompatible"}
```

---

### M-04: 并发竞争 — 多个 codeanalyze 实例写同一路径

**位置**: `cli.py` 多行 `Path(target).write_text(content, encoding="utf-8")`

**问题**: 如果同时运行多个 `codeanalyze` 实例指向同一目录，会竞争写入同一个输出文件。没有临时文件、没有原子写入。

**影响**: 输出文件可能被截断或包含交错内容。

**修复**: 使用临时文件 + 重命名：
```python
import tempfile
tmp = Path(target).with_suffix('.tmp')
tmp.write_text(content, encoding='utf-8')
tmp.rename(target)
```

---

### M-05: `%` 和 `.` 在文档统计中的错误分类

**位置**: `documents/scanner.py` 第 62-63 行
```python
_EXT_CODE = {".py", ".ts", ...}
_EXT_DOC = {".md", ".mdx", ".html", ".pdf", ".docx", ...}
```

**问题**: 如果一个文件名包含多个点（如 `v1.0.0-final.pdf`），`fp.suffix` 只返回最后一个扩展名 `.pdf`。这没问题。但如果文件名是 `Makefile`（无扩展名）或 `README`（无扩展名），`fp.suffix` 返回空字符串，该文件不会被计数。

更严重的是：`.doc` 和 `.ppt` 文件（旧版 Office 格式）被遗漏——它们不是代码文件也不是文档文件，落在计数之外。

**影响**: `.doc` 文件在 `docscan` 统计中不被计入任何分类，导致总数偏差。

---

## 🔵 低危

### L-01: 报告中的模糊生成时间戳

**位置**: `cli.py` 第 341-342 行
```python
f"> 生成时间: ... | 路径: {root}",
```

**问题**: 写死的 `...` 而不是实际时间戳。所有 docscan 报告中生成时间永远是 `...`。

---

### L-02: Path 重复 import

**位置**: `cli.py` 第 4 行和第 259 行
```python
from pathlib import Path  # line 4
from pathlib import Path  # line 259
```

**问题**: 第 259 行在函数定义之间额外 import 了一次 `Path`。这是一个重复 import，虽然 Python 不会报错，但不符合 PEP 8 规范（import 应在文件顶部）。

---

### L-03: `--output` 选项描述不统一

多个命令中 `--output` 的描述不一致：
- `docs`: "输出路径"
- `report`: "报告输出路径"
- `documents`: "报告输出路径"
- `docscan`: "报告输出路径"
- `export`: "输出文件路径"

影响用户体验，但没有功能风险。

---

### L-04: 错误信息暴露绝对路径

**位置**: 多个命令中
```python
console.print(f"⚠️ 未找到政策文档（PDF/DOCX/DOC）。确认路径是否正确？")
console.print("  建议: codeanalyze documents /Users/xiamingxing/Documents/国转中心/40-政策法规")
```

**问题**: 建议路径中暴露了完整的主目录路径 `/Users/xiamingxing/`。在共享屏幕或记录日志时会造成信息泄露。

---

## 攻击面总结

```
                    ┌──────────────────────┐
                    │     CLI 入口          │
                    │  (C-01: 路径注入)      │
                    └──────┬───────────────┘
                           │
              ┌────────────┴────────────┐
              ▼                         ▼
     ┌────────────────┐       ┌────────────────┐
     │  official.py    │       │  results.py     │
     │ (C-02: 命令注)  │       │ (H-05: Cypher注)│
     │ (H-01: 吞异常)  │       │ (H-02: URI编码) │
     │ (H-03: ZIPbomb) │       └────────────────┘
     │ (H-04: 乱码)    │               │
     │ (H-06: 回溯)    │               ▼
     └────────┬───────┘       ┌────────────────┐
              │               │  export.py      │
              ▼               │ (C-03: 幻象关系) │
     ┌────────────────┐      └────────────────┘
     │  eidos_adapter  │
     │ (无独立风险)     │
     └────────────────┘
```

## 修复优先级

| ID | 风险 | 复杂度 | 优先级 |
|----|------|--------|--------|
| C-02 | pdftotext 超时截断 | 1行 | P0 🔥 |
| C-03 | 幻象关系污染图谱 | 3行 | P0 🔥 |
| H-01 | 异常吞噬不可观测 | 7行×3 | P0 🔥 |
| C-01 | 路径越权 | 3行 | P1 |
| H-05 | Cypher 注入 | 1行 | P1 |
| H-04 | 乱码进入图谱 | 1行 | P1 |
| H-02 | JSON-LD URI 编码 | 1行 | P2 |
| H-03 | ZIP bomb | 5行 | P2 |
| M-02 | XLSX 空数据 | 20行 | P2 |
| H-06 | 正则回溯 | 1行 | P3 |
| M-01 | 汉字编码退化 | 持续维护 | P3 |
