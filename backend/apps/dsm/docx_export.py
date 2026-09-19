# -*- coding: utf-8 -*-
"""DOCX 정본 — **HWP 가 여는 서식** (결정 ⑤ · 턴 U · P-173 U24).

왜 DOCX 가 정본인가
-------------------
받는 쪽(재난안전과 · 상급기관)이 쓰는 편집기는 한글(HWP)이다. PDF 는 결재에 붙일 수는
있어도 **고쳐서 보낼 수 없다** — 담당자가 마지막에 한 줄 고치는 일이 실제 업무의 대부분
이다. HWPX 를 직접 쓰지 않는 이유: 그 규격을 우리가 만들 수 없고(우리가 만들 수 없는
포맷은 우리가 못 고친다), 한글은 **DOCX 를 연다**. 그래서 정본은 DOCX 이고 PDF 는 병행이다.

왜 HTML 에서 만드나 — 서식이 하나여야 하기 때문이다
---------------------------------------------------
종이의 모양은 `apps/dsm/incident_report.py` 한 곳이다. 여기서 문단과 표를 **다시 짜면**
서식이 두 벌이 되고, 두 벌은 반드시 어긋난다(어느 날 PDF 에만 칸이 하나 는다). 그래서
같은 HTML 을 받아 `htmldocx` 로 옮긴다 — **글자는 한 곳에서 나온다.**
   ⚠ 그래서 「택배 필드 0」도 자동으로 따라온다: HTML 에 없는 칸은 DOCX 에도 없다.
     그래도 시험은 **완성된 DOCX 의 글자**를 다시 센다(`tests/test_u24_reports.py`) —
     「같은 데서 나왔으니 같을 것이다」는 검사가 아니다.

HWP 가 열게 하려고 지키는 것 넷
-------------------------------
  ① 표는 **단순 격자**만 쓴다(중첩·병합 없음) — HTML 서식이 이미 그 모양이다.
  ② CSS 는 **버린다.** `<style>` 은 한글이 해석하지 않고, htmldocx 가 그 글자를 본문에
     떨어뜨리면 종이 첫 장이 CSS 로 시작한다(실측 방어).
  ③ 글꼴은 동아시아 글꼴을 함께 지정한다 — `w:eastAsia` 가 없으면 한글이 기본 서구 글꼴로
     떨어져 글자가 네모로 보인다.
  ④ 머리글(`section.header`)에 기관명과 문서 이름을 둔다 — 쪽이 넘어가도 남는다.

이 파일이 하지 않는 것
----------------------
· 파일을 저장하지 않는다(경로 0 · 객체 저장소 0). 바이트를 돌려줄 뿐이고, 저장 여부는
  부르는 쪽의 결정이다. 「특이사항」을 고치면 다음 내려받기가 다시 만든다.
· 원본 영상·스냅샷을 담지 않는다(계약 11조 · 원본 무반출). 이 문서에 그림은 0장이다.
"""
import io
import re

#: 문서 머리글에 쓰는 글꼴. 한글이 기본으로 갖고 있는 이름 — 없는 글꼴을 지정하면
#: 열리기는 하고 모양만 조용히 달라진다.
FONT_NAME = "맑은 고딕"

#: 제목 없이 열리는 문서를 만들지 않는다 — 파일 속성의 제목이 비면 결재 시스템이
#: 파일 이름을 제목으로 쓴다.
DEFAULT_TITLE = "GuardianX 보고서"

_STYLE_RE = re.compile(r"<style[^>]*>.*?</style>", re.IGNORECASE | re.DOTALL)
_SCRIPT_RE = re.compile(r"<script[^>]*>.*?</script>", re.IGNORECASE | re.DOTALL)
_BODY_RE = re.compile(r"<body[^>]*>(.*?)</body>", re.IGNORECASE | re.DOTALL)
_TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.IGNORECASE | re.DOTALL)


class DocxRenderFailed(Exception):
    """DOCX 를 만들지 못했다. **빈 파일을 성공으로 내보내지 않는다**(D-284 · K4 와 같은 규약)."""


def body_of(html: str) -> str:
    """`<body>` 안쪽만. CSS·스크립트는 **버린다**(머리말 ②).

    ★ `<body>` 가 없으면 원문 그대로 쓴다 — 조각 HTML 도 그릴 수 있어야 시험이 서식
      함수 하나만으로 이 변환을 잴 수 있다.
    """
    text = _SCRIPT_RE.sub("", _STYLE_RE.sub("", html or ""))
    found = _BODY_RE.search(text)
    return (found.group(1) if found else text).strip()


def title_of(html: str, fallback: str = DEFAULT_TITLE) -> str:
    found = _TITLE_RE.search(html or "")
    title = (found.group(1).strip() if found else "")
    return title or fallback


def _set_korean_font(document) -> None:
    """기본 글꼴에 동아시아 글꼴을 함께 건다(머리말 ③)."""
    from docx.oxml.ns import qn

    style = document.styles["Normal"]
    style.font.name = FONT_NAME
    style.font.size = None
    rpr = style.element.get_or_add_rPr()
    fonts = rpr.get_or_add_rFonts()
    fonts.set(qn("w:eastAsia"), FONT_NAME)
    fonts.set(qn("w:ascii"), FONT_NAME)
    fonts.set(qn("w:hAnsi"), FONT_NAME)


def html_to_docx_bytes(html: str, *, title: str | None = None,
                       header: str = "") -> bytes:
    """HTML 한 장 → DOCX 바이트. **0바이트는 성공이 아니다.**

    Args:
        html: 서식 함수가 낸 HTML(`incident_report.build_*_html`).
        title: 문서 속성 제목. 없으면 `<title>` 에서 가져온다.
        header: 머리글 한 줄(기관명 등). 비면 머리글을 만들지 않는다 — 빈 머리글은
            쪽마다 빈 줄을 남긴다.
    """
    body = body_of(html)
    if not body:
        raise DocxRenderFailed("옮길 내용이 비었다 — 빈 문서를 성공으로 내보내지 않는다")
    try:
        from docx import Document
        from htmldocx import HtmlToDocx
    except ImportError as exc:                     # pragma: no cover - 꾸러미 부재
        raise DocxRenderFailed(
            f"DOCX 꾸러미를 찾지 못했다({exc}) — python-docx · htmldocx 가 필요하다") from exc

    document = Document()
    _set_korean_font(document)
    document.core_properties.title = title or title_of(html)
    if header:
        para = document.sections[0].header.paragraphs[0]
        para.text = header

    parser = HtmlToDocx()
    #: 표에 테두리를 준다 — 결재에 올라가는 표는 선이 있어야 칸이 읽힌다.
    parser.table_style = "Table Grid"
    try:
        parser.add_html_to_document(body, document)
    except Exception as exc:
        raise DocxRenderFailed(f"{type(exc).__name__}: {exc}"[:240]) from exc

    buf = io.BytesIO()
    document.save(buf)
    data = buf.getvalue()
    if not data:
        raise DocxRenderFailed("0바이트를 냈다 — 빈 파일은 성공이 아니다")
    if not data.startswith(b"PK"):
        #: DOCX 는 zip 이다. 앞 두 글자가 `PK` 가 아니면 그것은 DOCX 가 아니다 —
        #: 확장자만 `.docx` 인 파일을 정본이라고 내보내지 않는다.
        raise DocxRenderFailed("DOCX(zip) 모양이 아니다")
    return data


def render(report_run, *, html: str | None = None, scope=None) -> bytes:
    """**정본 면** — `render(report_run) -> bytes` (WO-01 §5 HWPX 인터페이스 자리).

    `html` 을 주면 그것을 옮긴다(라우트가 이미 만든 글자를 두 번 만들지 않는다).
    안 주면 `scope` 로 실행 기록에서 다시 그린다.
    """
    if html is None:
        if scope is None:
            raise DocxRenderFailed(
                "html 도 scope 도 없다 — 무엇으로 그릴지 정해지지 않았다")
        from apps.dsm import monthly_report

        html = monthly_report.html_for_run(scope=scope, run=report_run)

    from apps.dsm import monthly_report

    kind = getattr(report_run, "kind", "")
    header = monthly_report.KIND_LABEL.get(kind, "GuardianX 보고서")
    return html_to_docx_bytes(html, header=header)


#: * [2026-09-19 · 턴 V 병합 · D-377] **`text_of` 는 여기 없다 — 시험 파일로 옮겼다.**
#:   완성된 DOCX 에서 사람이 보는 글자를 긁어내는 함수였는데, 제품은 한 번도 부르지
#:   않고 `backend/tests/test_u24_reports.py` 만 불렀다. 잠자는 기능 게이트(D-377)가
#:   「새로 만드는 것은 켜진 상태로 태어나야 한다」로 잡았고, 그 빨강이 옳다 —
#:   제품 모듈에 시험 도우미가 앉아 있으면 다음 사람은 그것을 제품 기능으로 읽는다.
#:   기준선(`evidence/D-377/dormant_baseline.txt`)은 **줄어들기만 하므로** 등재로
#:   덮지 않고 **자리를 옮겼다.** 쓰는 곳에 두는 것이 켜 두는 것이다.
