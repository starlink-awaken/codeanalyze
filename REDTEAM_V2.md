# 红队对抗分析 — 第二轮

> 对抗模式: 假设第一轮 13 项修复已部署，红队需要绕过这些修复
> 日期: 2026-05-21 | 范围: 修复有效性验证 + 新增攻击面

---

## 执行摘要

第一轮修复存在 **3 项绕过、2 项回归、4 项未覆盖到的攻击面**。
核心问题是：路径注入的白名单校验没出现在代码里（插入错位），Cypher 注入的转义不完整，XLSX 解析的 ElementTree 有 XXE 风险。

---

## 🔴 严重

### C-R1: 路径注入白名单未生效（修复绕过）

**位置**: `cli.py` 所有含 `path` 参数的 CLI 命令

**发现**: 我试图在 `documents` 命令的 `root = Path(path).resolve()` 后插入越权检查，但 Python 脚本匹配错了位置——检查被插入到了 `docscan` 函数的下面。实际代码中没有生效的路径白名单。

**影响**: `codeanalyze analyze /etc/` → `analyze_policy_directory()` 遍历 `/etc/*.pdf` → 报告输出到 `/etc/codeanalyze-report.md`（需要写权限但 read 仍可泄露路径信息）。

**更严重的问题**：6 个有 `path` 参数的命令（`analyze`, `deps`, `docs`, `report`, `docscan`, `export`）全部没有路径白名单。修复只在 `documents` 上做，其他命令完全暴露。

**修复验证**: 
```bash
# 确认白名单是否存在
grep -n "startswith.*home\|startswith.*Path.home" src/codeanalyze/cli.py
# 输出的应该是干净的——白名单不存在
```

**真正修复**：在 `cli.py` 添加一个装饰器或集中 check 函数：

```python
def _validate_path(path: str) -> Path:
    root = Path(path).resolve()
    home = Path.home().resolve()
    if not str(root).startswith(str(home)):
        raise click.BadParameter(f"path must be under home directory: {home}")
    return root
```

然后在所有命令中替换 `root = Path(path).resolve()` 为 `root = _validate_path(path)`。

---

### C-R2: Cypher 注入转义不完整（修复绕过）

**位置**: `results.py` 第 285-288 行

**当前修复**:
```python
safe_id = e.id.replace("'", "\\'")
safe_name = e.name.replace("'", "\\'")
```

**绕过**: 反斜杠本身可以被注入。如果一个实体的 name 包含 `\'`，转义后变成 `\\'`——第一个反斜杠转义了第二个，单引号逃逸。

**攻击构造**: `Entity(name="文件\\'; MATCH (n) DETACH DELETE n --")`

渲染后的 Cypher:
```cypher
SET Entity.name = '文件\\'; MATCH (n) DETACH DELETE n --'
```
第一个 `\\` 是转义后的反斜杠，`'` 闭合字符串，`;` 开始新语句。删除所有节点。

**真正修复**: 
```python
# 使用参数化查询或更彻底的转义
safe_name = e.name.replace("\\", "\\\\").replace("'", "\\'")
```

或更好的方案——用 Cypher 的 `$param` 参数化语法（需要 driver 支持），但这超出了 codeanalyze 的纯文本生成范围。当前修复至少要做到双反斜杠转义。

---

### C-R3: XLSX 解析引入 XXE 漏洞（新增攻击面）

**位置**: `official.py` 第 203-204 行

**当前代码**:
```python
tree = ET.fromstring(z.read(sheets[0]))
```

**问题**: Python 的 `xml.etree.ElementTree` 默认解析外部实体（XXE）。如果 XLSX 文件中嵌入了 `<!ENTITY xxe SYSTEM "file:///etc/passwd">`，解析时会读取文件内容。

**攻击构造**: 创建一个包含恶意 XML 实体的 `xl/worksheets/sheet1.xml`：
```xml
<?xml version="1.0"?>
<!DOCTYPE foo [
  <!ENTITY xxe SYSTEM "file:///etc/passwd">]>
<worksheet>
  <sheetData>
    <row r="1"><c r="A1"><v>&xxe;</v></c></row>
  </sheetData>
</worksheet>
```

打包成 `.xlsx` → 放入目标目录 → `codeanalyze documents --docs /target` → ET 解析读取 `/etc/passwd` → 内容进入知识图谱 → 导出时泄露。

**验证**: Python 3.10+ 的 ET 默认允许外部实体。

**修复**:
```python
from xml.etree.ElementTree import parse, fromstring
from xml.parsers.expat import ExpatError

# 安全解析
parser = ET.XMLParser(target=ET.TreeBuilder())
# Python 3.8+:
# parser.parser.UseForeignDTD(False)
# 更通用的方法：
import defusedxml.ElementTree as safe_et
tree = safe_et.fromstring(z.read(sheets[0]))
```

如果不能引入 `defusedxml`，至少用 `ET.XMLParser(resolve_entities=False)`。

---

## 🟠 高危

### H-R1: 所有命令未做路径白名单（修复范围不足）

除了 C-R1 中提到的外部攻击面，`codeanalyze analyze` 和 `codeanalyze export` 同样脆弱。`export` 尤其严重，因为它同时写 JSON/JSON-LD/Cypher 三个输出文件。

**命令路径注入攻击面矩阵**:

| 命令 | 有白名单 | 输入路径读文件 | 输出路径写文件 |
|------|---------|--------------|--------------|
| `analyze` | ❌ | ✅ | ✅ 报告 |
| `deps` | ❌ | ✅ | ❌ |
| `docs` | ❌ | ✅ 文档 | ✅ 报告 |
| `docscan` | ❌ | ✅ 目录扫描 | ✅ 报告 |
| `report` | ❌ | ❌ | ✅ 报告 |
| `export` | ❌ | ✅ 文件 | ✅ JSON/Cypher/JSON-LD |
| `documents` | ❌ | ✅ | ✅ 报告 |
| `graph` | ❌ | ❌ | ❌ |
| `wiki` | ❌ | ❌ | ✅ Wiki |

`export` 是最大的风险——它读路径下的所有文件，写 SQL 兼容脚本。如果路径指向 `/var/lib/neo4j/import/`，可能覆盖图数据库的导入文件。

---

### H-R2: `analyze_policy_directory` 在非目录路径上的行为

**位置**: `official.py` 第 230 行

```python
def analyze_policy_directory(root_path: str) -> PolicyGraph:
    root = Path(root_path).resolve()
    graph = PolicyGraph()
    if not root.is_dir():
        return graph  # 静默返回空图
```

**问题**: 如果用户传入文件路径而非目录路径，函数静默返回空 PolicyGraph（`total_count=0，documents=[]`）。调用方看到"✅ 0 个政策文档"——但不报错。用户不知道路径输错了。

**对比**: `documents` 命令在第 495-497 行有 `not root.is_dir()` 检查并报错。但 CLI 命令直接调 `analyze_policy_directory` 时不报错（如 `export` 命令第 573 行）。

---

### H-R3: `_extract_file_content` 文件描述符泄露

**位置**: `official.py` 第 166-176 行 (DOCX) 和第 189-212 行 (XLSX)

```python
if ext == ".docx":
    with zipfile.ZipFile(fp) as z:
        for info in z.infolist():
            if info.file_size > MAX_EMBEDDED_FILE_SIZE:
                logger.warning(...)
                return None  # ⚠️ ZIP 文件未关闭就 return！
```

**问题**: 当检测到大文件时 `return None` 直接跳出，`with` 语句正常执行 `__exit__` 所以 `z` 会关闭。但 XLSX 分支中第 189 行同样是 `with zipfile.ZipFile(fp) as z:`——如果第 200 行 `if not sheets: return None`，同样是安全的。但第 193 行的 `z.read()` 如果抛出异常（损坏的 sharedStrings.xml），异常会被第 259 行的 `except Exception` 捕获——此时 `with` 仍然能正确关闭文件句柄。

实际无泄露风险，但逻辑上 5 个 `return` 分布在 try 块内，可读性差。

---

## 🟡 中危

### M-R1: Rich console 输出可能导致终端注入

**位置**: `cli.py` 全量 `console.print()` 调用

**风险**: `rich` 的 `Panel` 和 `Table` 支持 ANSI 转义序列。如果文件名或路径中包含 ANSI 转义码（如 `\x1b[2J\x1b[H` 清屏指令），输出时可能被终端解释执行。

**攻击构造**: 创建一个名为 `\x1b[2J\x1b[H清屏.pdf` 的文件放入目录 → `codeanalyze docscan` 列出文件 → `console.print()` 输出文件名 → 终端执行清屏。

**缓解**: 文件名来自文件系统，攻击者需要写入权限才能创建恶意文件名。非远程攻击向量。

**修复**: `rich` 使用 `rich.markup.escape()` 包裹用户输入文件名。

---

### M-R2: JSON 导出默认 `ensure_ascii=True` 丢失中文

**位置**: `cli.py` 第 597 行

```python
"json": lambda: kg.to_json(),
```

**对比**: JSON-LD 导出用 `ensure_ascii=False` 保留中文。但 `to_json()` 默认 `ensure_ascii=True`——所有中文字符会转为 `\uXXXX` 转义。

**影响**: Agent 看到的 JSON 是 `中文` 而不是 `中文`。可读性下降，token 消耗增加（每个中文从 1 token 变成 6 token）。

---

### M-R3: `_strip_control_chars` 移除 \t 但不一致

**位置**: `official.py` 第 22-26 行

```python
def _strip_control_chars(text: str) -> str:
    return ''.join(
        c for c in text
        if c == '\n' or c == '\t' or unicodedata.category(c)[0] != 'C'
    )
```

**问题**: `\t` 被保留（tab），但 `\r`（回车）被移除。在 Windows 格式的文本文件中，`\r\n` 被拆成保留 `\n` 移除 `\r`——这是正确的。但 `\f`（换页符）被移除，可能存在于多栏 PDF 的输出中。

**影响**: 极小。`\f` 在 PDF 文本流中可能出现，移除后多栏文本可能合并。

---

### M-R4: `zipfile` 的 `BadZipFile` 捕获但不完全

**位置**: `official.py` 第 253 行

```python
except zipfile.BadZipFile:
    logger.warning("bad zip file: %s", fp.name)
```

**问题**: `zipfile.BadZipFile` 是 `zipfile` 可能抛出的异常之一。但 `zipfile.LargeZipFile`（需要 ZIP64 但未启用）、`zipfile.error`（基类）同样可能抛出。只捕获 `BadZipFile` 而遗漏 `LargeZipFile`。

**影响**: 超过 4GB 的 ZIP 文件（如大视频被误当 docx 处理）将不被捕获，进入 `except Exception` 被标注为通用的"content extraction failed"。

---

## 🔵 低危

### L-R1: `_extract_doc_number` 从文件名正则提取时重复计数

**位置**: `official.py` 第 101-113 行

```python
for m in _DOC_NUM_PATTERN.finditer(content_hint or filename):
    ...numbers.append(...)
for m in _DOC_NUM_FILE_PATTERN.finditer(filename):
    numbers.append(...)
seen = set()
return [n for n in numbers if not (n in seen or seen.add(n))]
```

**问题**: 内容提取和文件名提取是串行的，但文件名中的文号可能同时被两个正则匹配（`_DOC_NUM_PATTERN` 和 `_DOC_NUM_FILE_PATTERN` 在文件名上重叠）。`_DOC_NUM_FILE_PATTERN` 只匹配文件名，但 `_DOC_NUM_PATTERN` 也匹配文件名（当 `content_hint` 为空时 fallback 到 `filename`）。结果：文件名中的文号可能重复出现一次。

**影响**: 在 40-政策法规/ 测试中无感知，因为 `content_hint` 为空时 `content_hint or filename` 使用了 `filename`，两个正则会匹配到同一个 `京教科人办发〔2026〕2号`——但因为去重逻辑的存在，最终不重复。逻辑正确但效率低。

---

## 红队 vs 蓝队 对抗评分

```
第一轮红队发现 13 个问题
↓
蓝队修复 13 个问题
↓
第二轮红队对抗结果:
  ├─ 3 个绕过 (C-R1, C-R2, C-R3)
  ├─ 1 个修复范围不足 (H-R1)
  ├─ 2 个新攻击面 (H-R2, H-R3)
  ├─ 4 个低/中风险 (M-R1~M-R4)
  └─ 1 个逻辑正确 (L-R1)

对抗结论: 修复有效率 = (13 - 3) / 13 = 77%
          新攻击面发现 = 4 个
          真正需要修的新缺陷 = 4 个 (C-R1, C-R2, C-R3, H-R1)
```

**真正需要修的 4 个 P0/P1**:

| ID | 问题 | 修复复杂度 | 优先级 | 状态 |
|----|------|----------|--------|------|
| C-R1 | 路径白名单没生效 | 新建 `_validate_path` 函数 + 替换 8 处 | P0 🔥 | ✅ `_validate_path()` 替换全部 `Path.resolve()` |
| C-R2 | Cypher 反斜杠绕过 | `replace("\\\\", "\\\\\\\\")` 加在单引号前 | P0 🔥 | ✅ 先转义反斜杠再转义单引号 |
| C-R3 | XLSX XXE 漏洞 | 改用 `defusedxml` 或安全 parser | P0 🔥 | ✅ `_safe_parse()` 优先 defusedxml，降级禁用外部实体 |
| H-R1 | 所有命令路径白名单 | 同 C-R1，一次到位 | P1 | ✅ 8 个命令全部使用 `_validate_path()` |
