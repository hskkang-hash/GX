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

★ **PDF 는 만들지 않는다** — 이미 있는 결정을 그대로 따른다(P-392, HWPX/PDF
  같은 문서 렌더링을 이번 결로 새로 들이지 않는다는 결정 — `situation_report_
  ledger_service.py` 머리말과 같은 번호). CSV 일곱 + `manifest.json` 하나로
  ZIP 을 채운다 — evidence 의 PDF 행은 `excluded_by: P-392` 로 적는다.
"""
import csv
import io
import json
import zipfile

from django.utils import timezone

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
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        def _add(name: str, fn):
            try:
                zf.writestr(name, fn())
                manifest[name] = "ok"
            except Exception as exc:  # noqa: BLE001 — 부분 실패를 담아 계속한다
                zf.writestr(name, f"이 자료를 담지 못했습니다: {exc}")
                manifest[name] = f"error: {exc}"

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

        zf.writestr("manifest.json", json.dumps({
            "generated_at": timezone.now().isoformat(),
            "since": since, "until": until,
            "sources": manifest,
            #: PDF 는 이번 턴 만들지 않는다 — evidence 에 excluded_by: P-392.
            "pdf": "not_generated — P-392 결정 재사용(HWPX/PDF 렌더 미채움)",
        }, ensure_ascii=False, indent=2))

    return buf.getvalue()
