from __future__ import annotations

import csv
import re
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable
from xml.sax.saxutils import escape


EXPORT_COLUMNS = [
    ("platform", "平台"),
    ("user_name", "用户名称"),
    ("user_id", "平台用户标识"),
    ("content", "评论内容"),
    ("comment_time", "评论时间"),
    ("video_title", "视频标题"),
    ("video_url", "视频链接"),
    ("intent_label", "意向类型"),
    ("intent_level", "意向等级"),
    ("intent_score", "意向分数"),
    ("reason", "AI判断理由"),
    ("suggested_reply", "建议回复"),
    ("status", "处理状态"),
    ("final_reply", "最终回复"),
]

ALIASES = {
    "平台": "platform", "platform": "platform",
    "用户名称": "user_name", "用户名": "user_name", "昵称": "user_name", "user_name": "user_name",
    "抖音账号": "user_id", "平台用户标识": "user_id", "用户id": "user_id", "user_id": "user_id",
    "评论内容": "content", "评论": "content", "content": "content", "text": "content",
    "评论时间": "comment_time", "时间": "comment_time", "comment_time": "comment_time",
    "视频id": "video_id", "video_id": "video_id",
    "视频标题": "video_title", "video_title": "video_title",
    "视频链接": "video_url", "链接": "video_url", "video_url": "video_url",
    "评论id": "platform_comment_id", "comment_id": "platform_comment_id",
}


def _safe_spreadsheet_text(value: Any) -> str:
    text = "" if value is None else str(value)
    if text.startswith(("=", "+", "-", "@")):
        return "'" + text
    return text


def import_csv(path: str | Path, platform_override: str = "") -> list[dict[str, str]]:
    file_path = Path(path)
    raw = file_path.read_bytes()
    for encoding in ("utf-8-sig", "gb18030", "utf-8"):
        try:
            text = raw.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    else:
        raise ValueError("无法识别CSV编码，请保存为UTF-8或GB18030")

    reader = csv.DictReader(text.splitlines())
    if not reader.fieldnames:
        raise ValueError("CSV缺少表头")
    header_map: dict[str, str] = {}
    for header in reader.fieldnames:
        normalized = re.sub(r"\s+", "", (header or "").lower())
        if normalized in ALIASES:
            header_map[header] = ALIASES[normalized]

    if "content" not in header_map.values():
        raise ValueError("CSV必须包含“评论内容”列")

    items: list[dict[str, str]] = []
    for row in reader:
        item = {target: (row.get(source) or "").strip() for source, target in header_map.items()}
        if item.get("content"):
            if platform_override:
                item["platform"] = platform_override
            else:
                item.setdefault("platform", "手工导入")
            items.append(item)
    return items


def export_csv(path: str | Path, rows: Iterable[dict[str, Any]]) -> None:
    with Path(path).open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow([title for _, title in EXPORT_COLUMNS])
        for row in rows:
            writer.writerow([_safe_spreadsheet_text(row.get(key, "")) for key, _ in EXPORT_COLUMNS])


def _excel_column(index: int) -> str:
    name = ""
    while index:
        index, remainder = divmod(index - 1, 26)
        name = chr(65 + remainder) + name
    return name


def _inline_cell(reference: str, value: Any, style: int = 0) -> str:
    text = escape(_safe_spreadsheet_text(value))
    style_attr = f' s="{style}"' if style else ""
    return f'<c r="{reference}" t="inlineStr"{style_attr}><is><t xml:space="preserve">{text}</t></is></c>'


def export_xlsx(path: str | Path, rows: Iterable[dict[str, Any]]) -> None:
    """Write a dependency-free XLSX workbook with one formatted sheet."""
    row_list = list(rows)
    sheet_rows: list[str] = []
    header_cells = [
        _inline_cell(f"{_excel_column(index)}1", title, 1)
        for index, (_, title) in enumerate(EXPORT_COLUMNS, start=1)
    ]
    sheet_rows.append(f'<row r="1" ht="28" customHeight="1">{"".join(header_cells)}</row>')
    for row_index, row in enumerate(row_list, start=2):
        cells = [
            _inline_cell(f"{_excel_column(column_index)}{row_index}", row.get(key, ""), 2 if row_index % 2 == 0 else 0)
            for column_index, (key, _) in enumerate(EXPORT_COLUMNS, start=1)
        ]
        sheet_rows.append(f'<row r="{row_index}">{"".join(cells)}</row>')

    widths = [12, 18, 24, 55, 22, 35, 40, 14, 12, 12, 42, 55, 12, 55]
    cols = "".join(
        f'<col min="{i}" max="{i}" width="{width}" customWidth="1"/>'
        for i, width in enumerate(widths, start=1)
    )
    max_row = max(1, len(row_list) + 1)
    max_col = _excel_column(len(EXPORT_COLUMNS))
    sheet_xml = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <dimension ref="A1:{max_col}{max_row}"/>
  <sheetViews><sheetView workbookViewId="0"><pane ySplit="1" topLeftCell="A2" activePane="bottomLeft" state="frozen"/></sheetView></sheetViews>
  <cols>{cols}</cols>
  <sheetData>{''.join(sheet_rows)}</sheetData>
  <autoFilter ref="A1:{max_col}{max_row}"/>
</worksheet>'''

    content_types = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
  <Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
  <Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>
  <Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>
</Types>'''
    root_rels = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>
</Relationships>'''
    workbook = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <sheets><sheet name="媒介线索清单" sheetId="1" r:id="rId1"/></sheets>
</workbook>'''
    workbook_rels = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>
</Relationships>'''
    styles = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <fonts count="2"><font><sz val="10"/><name val="Microsoft YaHei"/></font><font><b/><color rgb="FFFFFFFF"/><sz val="10"/><name val="Microsoft YaHei"/></font></fonts>
  <fills count="4"><fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill><fill><patternFill patternType="solid"><fgColor rgb="FF0A5B78"/><bgColor indexed="64"/></patternFill></fill><fill><patternFill patternType="solid"><fgColor rgb="FFEAF5F8"/><bgColor indexed="64"/></patternFill></fill></fills>
  <borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders>
  <cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>
  <cellXfs count="3"><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0" applyAlignment="1"><alignment vertical="top" wrapText="1"/></xf><xf numFmtId="0" fontId="1" fillId="2" borderId="0" xfId="0" applyFill="1" applyFont="1" applyAlignment="1"><alignment vertical="center" wrapText="1"/></xf><xf numFmtId="0" fontId="0" fillId="3" borderId="0" xfId="0" applyFill="1" applyAlignment="1"><alignment vertical="top" wrapText="1"/></xf></cellXfs>
</styleSheet>'''
    created = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    core = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"><dc:title>全域媒介线索清单</dc:title><dc:creator>OmniMedia Intelligence Radar</dc:creator><dcterms:created xsi:type="dcterms:W3CDTF">{created}</dcterms:created></cp:coreProperties>'''

    with zipfile.ZipFile(Path(path), "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", content_types)
        archive.writestr("_rels/.rels", root_rels)
        archive.writestr("xl/workbook.xml", workbook)
        archive.writestr("xl/_rels/workbook.xml.rels", workbook_rels)
        archive.writestr("xl/worksheets/sheet1.xml", sheet_xml)
        archive.writestr("xl/styles.xml", styles)
        archive.writestr("docProps/core.xml", core)
