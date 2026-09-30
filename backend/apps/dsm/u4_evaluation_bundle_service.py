# -*- coding: utf-8 -*-
"""DSM-U4-08 — 재난관리평가·감사 자료 묶음 (턴 AP · WO-19 · 차선 N4).

명세 §4.4: 「재난관리평가·감사 자료 묶음 — 기간 선택 → 상황보고 발송 이력 ·
CBS 승인 기록 · 통제 4시각 · 상황판단회의 · 열람 대장 · 훈련 실적 · 접속기록
요약을 ZIP(PDF+CSV)」 완결 조건 「ZIP 1 · 10분 내 생성」.

★ **새 집계를 짜지 않는다** — 일곱 원천 전부 이미 있는 공개 면을 그대로
  CSV 로 편다(DA-04, 두 번째 집계를 만들지 않는다):

    상황보고 발송 이력   situation_report_ledger_service.list_reports
    CBS 승인 기록        cbs_draft_service.list_drafts
    통제 4시각           control_board_service.list_board
    상황판단회의         situation_meeting_service.list_meetings
    열람 대장            video_access_ledger_service.list_requests
    훈련 실적            apps.dsm.services.drill_report
    접속기록 요약        access_log_service.read_csv(U5 전용 문 — 권한 없으면
                         그 파일 자리에 「권한 없음」 한 줄만 남긴다. 전체 묶음
                         생성을 막지 않는다 — 나머지 여섯은 그 사람 권한 그대로
                         본다)

★ **PDF 도 함께 낸다** (턴 AQ · 차선 N4 · P-436). 예전 머리말은 「PDF 는 만들지
  않는다 — P-392 결정 재사용」이라 적었지만 **번호 오용**이었다(P-392 는 HWPX ·
  F6-07 결정이지 이 절의 PDF 결정이 아니다). PDF 렌더는 새 의존성이 아니다 — 턴 U 의
  DOCX 정본 곁에 이미 있는 PDF 경로(`kernels.k4_report.render_html` · 공개 면 ·
  D-278 · `monthly_report.render_run` 과 같은 호출)를 그대로 부른다. PDF 는
  **사람이 읽는 표지·요약**이다: 기간 · 생성 시각 · 일곱 원천 각각의 담긴 줄 수와
  상태(담음/못 담음). 원자료 전량은 같은 ZIP 의 CSV 가 갖는다 — 두 번째 집계를
  짜지 않는다. PDF 렌더가 실패해도 CSV 묶음은 막지 않는다(부분 실패 규약 그대로 —
  그 자리에 사유 한 줄 · manifest 에 `error:`).
"""
import csv
import io
import json
import zipfile

from django.utils import timezone
from django.utils.html import escape

from apps.dsm import (access_log_service, cbs_draft_service, control_board_service,
                     services, situation_meeting_service,
                     situation_report_ledger_service, video_access_ledger_service)


def _rows_to_csv(rows: list[dict]) -> str:
    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator="\n")
    if not rows:
        writer.writerow(("(0 rows)",))
        return buf.getvalue()
    keys = list(rows[0].keys())
    writer.writerow(keys)
    for row in rows:
        writer.writerow([row.get(k, "") for k in keys])
    return buf.getvalue()


PDF_NAME = "evaluation_bundle.pdf"

#: CSV 파일 이름 → PDF 요약표에 쓰는 사람 말(명세 §4.4 의 일곱 이름 그대로).
SOURCE_LABELS: dict[str, str] = {
    "situation_reports.csv": "상황보고 발송 이력",
    "cbs_drafts.csv": "CBS 승인 기록",
    "control_points.csv": "통제 4시각",
    "situation_meetings.csv": "상황판단회의",
    "video_access_requests.csv": "열람 대장",
    "drill_report.csv": "훈련 실적",
    "access_log.csv": "접속기록 요약",
}


def _count_rows(text: str) -> int:
    """CSV 본문의 자료 줄 수(머리줄 제외 · `(0 rows)` 는 0)."""
    rows = list(csv.reader(io.StringIO(text or "")))
    if not rows or rows == [["(0 rows)"]]:
        return 0
    return max(len(rows) - 1, 0)


def _summary_html(*, since, until, generated_at: str, manifest: dict,
                  counts: dict) -> str:
    lines = []
    for name, label in SOURCE_LABELS.items():
        status = manifest.get(name, "")
        count = counts.get(name)
        lines.append(
            "<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>" % (
                escape(label), escape(name),
                escape(str(count)) if count is not None else "-",
                "담음" if status == "ok" else escape("담지 못함 — " + status)))
    period = "%s ~ %s" % (escape(since or "처음"), escape(until or "지금"))
    return (
        "<html><head><meta charset='utf-8'><style>"
        "body{font-family:sans-serif;font-size:11pt}"
        "table{border-collapse:collapse;width:100%}"
        "td,th{border:1px solid #888;padding:4px;text-align:left}"
        "</style></head><body>"
        "<h1>재난관리평가·감사 자료 묶음</h1>"
        f"<p>기간: {period}</p>"
        f"<p>생성 시각: {escape(generated_at)}</p>"
        "<table><thead><tr><th>자료</th><th>파일</th><th>줄 수</th><th>상태</th>"
        "</tr></thead><tbody>" + "".join(lines) + "</tbody></table>"
        "<p>원자료 전량은 같은 묶음(ZIP)의 CSV 파일에 있습니다.</p>"
        "</body></html>")


def _render_summary_pdf(*, scope, since, until, generated_at: str, manifest: dict,
                        counts: dict) -> bytes:
    """PDF 한 장 — K4 공개 면(`kernels.k4_report.render_html`)만 부른다(D-278)."""
    from kernels.k4_report import render_html

    return render_html(scope=scope, html=_summary_html(
        since=since, until=until, generated_at=generated_at, manifest=manifest,
        counts=counts))


def build_bundle_zip(*, scope, since=None, until=None) -> bytes:
    """`GET /evaluation-bundle.zip` — 일곱 원천을 CSV 로 묶은 ZIP 바이트.

    각 원천은 **독립적으로** 담긴다 — 한 원천이 예외(예: 접속기록 권한 없음)를
    내도 나머지 여섯은 그대로 담는다(부분 실패가 전체를 막지 않는다).

    Raises:
        common.tenant_scope.SystemScopeCannotRead: 요청자가 없다(시스템 스코프
            — 이것은 개별 원천이 아니라 호출 자체가 성립하지 않는 경우다).
    """
    scope.require_actor()  # 시스템 스코프면 여기서 바로 던진다

    manifest: dict[str, str] = {}
    counts: dict[str, int | None] = {}
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        def _add(name: str, fn):
            try:
                text = fn()
                zf.writestr(name, text)
                manifest[name] = "ok"
                counts[name] = _count_rows(text)
            except Exception as exc:  # noqa: BLE001 — 부분 실패를 담아 계속한다
                zf.writestr(name, f"이 자료를 담지 못했습니다: {exc}")
                manifest[name] = f"error: {exc}"
                counts[name] = None

        _add("situation_reports.csv", lambda: _rows_to_csv(
            situation_report_ledger_service.list_reports(
                scope=scope, limit=situation_report_ledger_service.SCAN_CAP)))
        _add("cbs_drafts.csv", lambda: _rows_to_csv(
            cbs_draft_service.list_drafts(scope=scope, limit=cbs_draft_service.SCAN_CAP)))
        _add("control_points.csv", lambda: _rows_to_csv(
            control_board_service.list_board(
                scope=scope, limit=control_board_service.SCAN_CAP)))
        _add("situation_meetings.csv", lambda: _rows_to_csv(
            situation_meeting_service.list_meetings(scope=scope, limit=500)))
        _add("video_access_requests.csv", lambda: _rows_to_csv(
            video_access_ledger_service.list_requests(scope=scope, limit=500)))
        _add("drill_report.csv", lambda: _rows_to_csv([services.drill_report(scope=scope)]))
        _add("access_log.csv", lambda: access_log_service.read_csv(
            scope=scope, since=since, until=until))

        generated_at = timezone.now().isoformat()
        try:
            zf.writestr(PDF_NAME, _render_summary_pdf(
                scope=scope, since=since, until=until, generated_at=generated_at,
                manifest=manifest, counts=counts))
            pdf_status = "ok"
        except Exception as exc:  # noqa: BLE001 — PDF 실패가 CSV 묶음을 막지 않는다
            zf.writestr(PDF_NAME + ".error.txt", f"PDF 를 만들지 못했습니다: {exc}")
            pdf_status = f"error: {exc}"

        zf.writestr("manifest.json", json.dumps({
            "generated_at": generated_at,
            "since": since, "until": until,
            "sources": manifest,
            #: [턴 AQ · N4 · P-436] PDF 요약 한 장 — K4 공개 면(render_html)으로 찍는다.
            "pdf": {"name": PDF_NAME, "status": pdf_status},
        }, ensure_ascii=False, indent=2))

    return buf.getvalue()
