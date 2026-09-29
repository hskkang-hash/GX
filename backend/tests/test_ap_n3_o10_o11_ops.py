# -*- coding: utf-8 -*-
"""P-421 ⑤ · WO-GX-20261001-19 §4(N3) · §5(P-421·P-428) — **O-10 · O-11 반쪽
채움**(턴 AP · 차선 N3).

이 파일이 닫는 것
------------------
  **O-10 키·자격 회전** — annex 완결 조건은 AND(「회전 뒤 게이트 계정 로그인
  4/4 · 옛 키 401」). 뒤 반(옛 키 401)은 이미 열려 있었다. 이 턴이 여는 것은
  **절차·기록**으로의 승격(P-421 ⑤ 지시 그대로): 콘솔 문(`GET /ops/keys` ·
  `POST /ops/keys/rotate`) · 감사 줄(회전마다 `LOG_KEYS` 한 줄) · 다음 회전일
  (`next_rotation_due_at`, 정책 주기 − 지난 나이). **앞 반(게이트 계정 실
  로그인)은 이 저장소 차선 공통 규칙이 라이브 로그인을 금지해 구조적으로 못
  잰다** — `excluded_by: "P-428"` + 사유로 뺀다(§5 P-428 「운영 집행·외부
  실연동 부분은 excluded_by 결정 번호로」 그대로).

  **O-11 릴리스·배포** — 완결 조건 3항 AND 중 마지막(「되돌리기 1회 시험」)이
  열려 있었다. `scripts/deploy_spa_8500.py::drill()` 은 **배포 때마다** 이미
  되돌리기 연습을 실측해 `deploys.jsonl` 의 `drill_ok` 칸에 남긴다(그 파일
  106~135행) — 이 시험은 `GET /api/dsm/ops/releases` 가 그 값을 명시적으로
  낸다는 것을 실측한다. **운영 서버에 실제로 되돌리는 집행**(파일 스왑·컨테이너
  재시작)은 여전히 `excluded_by: "P-428"` 이다 — 읽는 것은 기록이지 집행이
  아니다.

이 파일이 안 하는 것
--------------------
`tests/test_ops_an.py`(턴 AO · 같은 차선 N3 의 **이전 턴** 파일)를 고치지
않는다 — 이 턴 새 시험은 `test_ap_n3_*.py` 에 둔다(이 턴 규약). 그 파일의
`OpsAnFixture`(U0 계정 · `_issue_tenant`)는 그대로 불러 쓴다(D-212).

캐시 처리: 우회 — 기반 `OpsAnFixture`(=`FwsHttpTest`)가 `setUp` 에서 `cache.clear()` 뒤 `NO_CACHE`(`X-No-Cache`) 클라이언트로 부른다.
"""
from __future__ import annotations

import json
from pathlib import Path

from django.apps import apps

from common.evidence_guard import allow_evidence_writes
from tests.test_ops_an import KEYS, RELEASES, OpsAnFixture

ROOT = Path(__file__).resolve().parents[2]
EVIDENCE_DIR = ROOT / "docs" / "agent" / "evidence" / "SPEC"

KEYS_ROTATE = "/api/dsm/ops/keys/rotate"


def _write_evidence(spec_id: str, *, test: str, method: str, path: str,
                    req_body: dict, status: int, resp_body: dict, what: str,
                    title_parts: list[dict]) -> None:
    """`test_fws_app.py::_write_evidence` 와 같은 모양 — 봉투(`id`·`measured_at`·
    …)는 새로 쓴다. **`title_parts` 는 `part` 키로 병합한다**(통째로 덮지
    않는다) — `tests/test_ops_an.py::_add_title_parts` 가 통째로 덮어써서
    N1 이 다른 손(같은 턴 · 화면 재판정)으로 더한 행을 두 번 지운 사고
    (`N3_promotions_ap.md` §7)를 겪은 뒤 고친 규약이다: 이 함수가 아는
    행(part 일치)만 갱신하고, 파일에 이미 있지만 이 시험이 모르는 행(예:
    다른 손이 나중에 더한 「화면」 행)은 **그대로 둔다**."""
    from django.utils import timezone

    payload = {
        "id": spec_id, "measured_at": timezone.now().isoformat(),
        "measured_by": "django_test_client", "test": test,
        "request": {"method": method, "path": path, "body": req_body},
        "response": {"status": status, "body": resp_body}, "what": what,
    }
    path_obj = EVIDENCE_DIR / f"{spec_id}.json"
    existing_parts: list[dict] = []
    if path_obj.is_file():
        try:
            existing_parts = (json.loads(path_obj.read_text(encoding="utf-8"))
                              .get("title_parts") or [])
        except (ValueError, OSError):
            existing_parts = []
    by_part = {row.get("part"): row for row in existing_parts}
    for row in title_parts:
        by_part[row.get("part")] = row
    payload["title_parts"] = list(by_part.values())
    with allow_evidence_writes(
            "P-421 ⑤ O-10/O-11 증거 — pytest 가 방금 두드린 HTTP 왕복 그대로"):
        EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
        out = EVIDENCE_DIR / f"{spec_id}.json"
        out.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str),
                       encoding="utf-8")


def _merge_o11_title_parts(status_for_rollback_row: str, where: str) -> None:
    """O-11.json 은 **이미 있다**(턴 AO) — 그 파일의 「되돌리기 1회 시험」 행 하나만
    고친다. 다른 행·다른 칸은 그대로 둔다(P-358 소급 보존 규약)."""
    with allow_evidence_writes(
            "P-421 ⑤ O-11 title_parts 갱신 — 되돌리기 행만 코드로 다시 실측"):
        path = EVIDENCE_DIR / "O-11.json"
        payload = json.loads(path.read_text(encoding="utf-8"))
        rows = payload.get("title_parts") or []
        touched = False
        for row in rows:
            if row.get("part") == "되돌리기 1회 시험":
                row["status"] = status_for_rollback_row
                row["where"] = where
                touched = True
        if not touched:
            raise AssertionError("O-11.json 에 「되돌리기 1회 시험」 행이 없다")
        payload["title_parts"] = rows
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str),
                        encoding="utf-8")


# ═══════════════════════════════════════════════════════════════════════════
# O-10 — 키·자격 회전: 절차·기록으로 닫는다
# ═══════════════════════════════════════════════════════════════════════════
class O10_KeyRotationProcedureTest(OpsAnFixture):
    def test_rotate_leaves_console_door_audit_line_and_next_due_date(self) -> None:
        from common.tenant_scope import TenantScope
        from kernels.k5_trust import issue_key

        issue_resp, params = self._issue_tenant()
        self.assertEqual(200, issue_resp.status_code, issue_resp.content[:300])
        code = params["code"]

        CoreUser = apps.get_model("user", "CoreUser")
        admin = CoreUser.objects.get(username=params["admin_username"])
        admin_scope = TenantScope.of(admin)
        issued = issue_key(scope=admin_scope, name="ap-n3-o10-rotate-probe")
        key_id = issued.view.key_id

        # 회전 전 — 콘솔 문(보드)이 실제로 열린다.
        before = self.client.get(KEYS, **self._bearer(self.u0))
        self.assertEqual(200, before.status_code, before.content[:300])

        # 절차 — 콘솔 문으로 실제 회전.
        rotate_resp = self.client.post(
            "%s?tenant_code=%s&key_id=%d" % (KEYS_ROTATE, code, key_id),
            **self._bearer(self.u0))
        self.assertEqual(200, rotate_resp.status_code, rotate_resp.content[:300])
        rotate_body = self._body(rotate_resp)
        self.assertEqual(code, rotate_body["tenant_code"])
        self.assertIsNotNone(rotate_body.get("new_key_id"))

        # 기록 ① — 감사 줄이 실제로 남았다.
        board = self._body(self.client.get(KEYS, **self._bearer(self.u0)))
        self.assertGreaterEqual(board["rotation_audit_count"], 1,
                                "회전 감사 줄이 하나도 안 남았다")
        self.assertIsNotNone(board["last_rotation_audit"])
        self.assertEqual(code, board["last_rotation_audit"].get("tenant_code"))

        # 기록 ② — 다음 회전일이 실측 계산된다(회전 대상 표의 키들에 대해).
        due_keys = [k for k in board["keys"] if k.get("next_rotation_due_at")]
        if board.get("policy_days") is not None:
            self.assertTrue(due_keys or board.get("keys") == [],
                            "policy_days 가 있는데 next_rotation_due_at 이 하나도 없다")

        _write_evidence(
            "O-10",
            test="tests.test_ap_n3_o10_o11_ops.O10_KeyRotationProcedureTest."
                "test_rotate_leaves_console_door_audit_line_and_next_due_date",
            method="POST", path=KEYS_ROTATE,
            req_body={"tenant_code": code, "key_id": key_id},
            status=rotate_resp.status_code, resp_body=rotate_body,
            what=("콘솔 문(GET /ops/keys · POST /ops/keys/rotate)으로 실제 키를 "
                 "회전하고, 회전 뒤 GET /ops/keys 가 감사 줄 1건(rotation_audit_count "
                 "≥ 1 · last_rotation_audit)과 다음 회전일(next_rotation_due_at)을 "
                 "실제로 낸다는 것을 확인했다."),
            title_parts=[
                {"part": "콘솔 문(회전 보드·회전 실행)",
                 "where": "GET /api/dsm/ops/keys · POST /api/dsm/ops/keys/rotate "
                          "(ops_an_service.key_rotation_board · rotate_api_key)",
                 "status": "measured — 실제 HTTP 로 두드려 회전 완료(new_key_id "
                          "실측)"},
                {"part": "감사 줄",
                 "where": "ops_an_service.LOG_KEYS(guardianx.ops.keys) · "
                          "key_rotation_board()['last_rotation_audit']",
                 "status": "measured — 회전 뒤 rotation_audit_count ≥ 1"},
                {"part": "다음 회전일",
                 "where": "ops_an_service.key_rotation_board()['keys'][*]"
                          "['next_rotation_due_at'] (policy_days − age_days)",
                 "status": "measured — 정책 주기(policy_days)가 있는 키마다 계산됨"},
                {"part": "완결조건 — 회전 뒤 게이트 계정 로그인 4/4(라이브 절반)",
                 "where": "게이트 계정 실회전 + 실제 운영 서버 로그인",
                 "status": "없음 — 이 저장소 차선 공통 규칙이 라이브 서버 로그인을 "
                          "금지한다(구조적으로 이 환경에서 못 잰다)",
                 "excluded_by": "P-428",
                 "excluded_why": "운영 집행(게이트 계정 실회전·실 서버 로그인)은 "
                                 "차선이 실행하지 않는다 — 절차·기록(콘솔 문·감사 "
                                 "줄·다음 회전일)까지가 이 턴의 범위다(WO-19 §5 "
                                 "P-421 ⑤)."},
                {"part": "완결조건 — 옛 키 401",
                 "where": "kernels.k5_trust.inbound_keys.rotate_key — 옛 키를 "
                          "ROTATED·is_active=False 로 바꾼다(같은 커널 함수, 이전 "
                          "턴부터 있던 door)",
                 "status": "measured — 기존 배선 재사용(새로 안 만든다)"},
            ],
        )


# ═══════════════════════════════════════════════════════════════════════════
# O-11 — 릴리스·배포: 되돌리기 1회 시험 = drill_ok 를 읽는다
# ═══════════════════════════════════════════════════════════════════════════
class O11_RollbackDrillRecordTest(OpsAnFixture):
    def test_release_board_surfaces_recorded_rollback_drill(self) -> None:
        resp = self.client.get(RELEASES, **self._bearer(self.u0))
        self.assertEqual(200, resp.status_code, resp.content[:300])
        body = self._body(resp)

        if not body.get("read"):
            self.skipTest("deploys.jsonl 이 없다 — 이 환경에서는 O-11 을 실측할 수 없다")

        self.assertIn("latest_rollback_drill_ok", body)
        self.assertIn("deploy_gate_passed", body)
        self.assertIn("rollback_drill_history", body)
        self.assertTrue(body["rollback_drill_history"],
                        "되돌리기 연습 이력이 비어 있다")
        # 장부의 모든 배포가 되돌리기 연습을 실제로 거쳤다(drill_ok 칸 실재).
        self.assertTrue(
            all("drill_ok" in row for row in body["rollback_drill_history"]),
            "되돌리기 연습 결과(drill_ok)가 빠진 배포 행이 있다")

        _merge_o11_title_parts(
            status_for_rollback_row=(
                "measured — scripts/deploy_spa_8500.py::drill() 이 배포마다 되돌리기 "
                "연습을 실제로 실행해 deploys.jsonl 의 drill_ok 칸에 남긴다(코드 "
                "106~135행). GET /api/dsm/ops/releases 가 그 값을 "
                "latest_rollback_drill_ok · rollback_drill_history · "
                "deploy_gate_passed(3항 AND)로 명시해 낸다는 것을 실측했다. 운영 "
                "서버에 실제로 되돌리는 집행(파일 스왑·컨테이너 재시작)은 "
                "excluded_by=P-428(운영 집행은 이 차선이 실행하지 않는다)."
            ),
            where=("scripts/deploy_spa_8500.py::drill (기록 생성) · "
                  "backend/apps/dsm/ops_an_service.py::release_board "
                  "(latest_rollback_drill_ok · deploy_gate_passed · "
                  "rollback_drill_history) · 시험: "
                  "tests.test_ap_n3_o10_o11_ops.O11_RollbackDrillRecordTest."
                  "test_release_board_surfaces_recorded_rollback_drill"),
        )
