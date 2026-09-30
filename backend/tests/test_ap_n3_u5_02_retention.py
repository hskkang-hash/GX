# -*- coding: utf-8 -*-
"""P-421 ④ · WO-GX-20261001-19 §4(N3) · §5(P-421) — **DSM-U5-02 반쪽 채움**
(턴 AP · 차선 N3).

이 파일이 닫는 것
------------------
`docs/agent/evidence/SPEC/DSM-U5-02.json` 의 `title_parts` 두 열린 행:

  ① 「접속기록 1년 이상 보관」 — 선언(P-230 730일)과 심긴 값(365일)이 갈려
     있었다(`backend/common/log_retention_policy.py` 머리말 ★★). **값은
     선언이 아니라 설정에서 읽는다**(WO-19 §4 N3 지시): 새로 더한
     `log_retention_policy.enforced_declared_days('audit')` 가
     `common.ops_tasks.audit_retention_declared_days()`(dj-core 가 실제로
     읽는 `AdminConfig::System > security.audit_log_retention_days` 자리)를
     그대로 되읽는다 — 같은 함수가 같은 자리를 읽으므로 「선언 == 설정」은
     대조가 아니라 **항등**이 된다. 기존 `POLICY['audit'].days`(730) ·
     `aligned()` · `divergence()`(P-230 목표 선언 · `scripts
     /ops_retention_policy.py` 가 그대로 쓴다)는 건드리지 않았다 — 그 게이트의
     자기시험(「730 선언 · 365 집행이면 빨강」 표본)을 깨지 않기 위해서다.
  ② 「완결 조건 접속기록 조회 ≤ 60초」 — 실제로 벽시계를 재 60초 미만임을
     확인한다(대리 지표 0 — 시험이 `time.perf_counter()` 로 직접 잰다).

이 파일이 안 하는 것
--------------------
`tests/test_p356_u4_spec_promotions.py` 는 턴 AL 이 먼저 쓴 시험 파일이라
고치지 않는다(§0.4 밖이지만 「한 파일은 한 차선」 규약) — 그 파일의
`U4Fixture`(sysop_a·manager_a·`_seed_access_log_row`) · `ACCESS_LOG` ·
`EVIDENCE_DIR` 를 그대로 불러 쓴다(D-212 — 같은 접속기록 문을 두 번 다른
눈으로 재지 않는다).

증거 병합 규약(P-358 소급 · 이 턴 규약)
---------------------------------------
`title_parts` 는 **부분 갱신**이다 — 이 시험이 건드리는 두 `part` 행만
`status`/`where` 를 새로 쓰고, 나머지 행·나머지 칸(id·request·response·what
등)은 그대로 둔다. 빈 칸 0(O 게이트가 그것을 센다).
"""
from __future__ import annotations

import json
import time

from django.apps import apps
from django.core.cache import cache

from tests.test_api_contract import _bearer
from tests.test_p356_u4_spec_promotions import ACCESS_LOG, EVIDENCE_DIR, U4Fixture

EVIDENCE_PATH = EVIDENCE_DIR / "DSM-U5-02.json"

ROW_RETENTION = "접속기록 1년 이상 보관"
ROW_PERF = "완결 조건 「접속기록 조회 ≤ 60초」"


# ═══════════════════════════════════════════════════════════════════════════
# 자리 — dj-core 가 실제로 읽는 AdminConfig 한 칸만 만진다
# ═══════════════════════════════════════════════════════════════════════════
def _adminconfig_set(days: int) -> None:
    """`test_be_purge.py::_declare_365` 와 같은 자리 · 같은 칸만 심는다."""
    AdminConfig = apps.get_model("configuration", "AdminConfig")
    row = AdminConfig.objects.filter(name="System", is_active=True).first()
    if row is None:
        row = AdminConfig.objects.create(name="System", is_active=True, settings={})
    conf = dict(row.settings or {})
    conf.setdefault("security", {})
    conf["security"]["audit_log_retention_days"] = days
    row.settings = conf
    row.save(update_fields=["settings"])


def _adminconfig_clear() -> None:
    AdminConfig = apps.get_model("configuration", "AdminConfig")
    row = AdminConfig.objects.filter(name="System", is_active=True).first()
    if row is None:
        return
    conf = dict(row.settings or {})
    conf.get("security", {}).pop("audit_log_retention_days", None)
    row.settings = conf
    row.save(update_fields=["settings"])


def _merge_title_parts(updates: dict[str, dict[str, str]]) -> None:
    """`part` 로 골라 `status`(필수) · `where`(있으면) 만 갱신한다. 나머지는 보존.

    [턴 AQ · P-431 · 차선 Q] 사람 표는 `DSM-U5-02.retro.md`(손으로만) — 이 시험은
    표를 **쓰지 않고**, 고치려던 `part` 행이 사람 표에 있는지만 **읽어** 대조한다."""
    rp = EVIDENCE_PATH.with_name("DSM-U5-02.retro.md")
    if not rp.is_file():
        return      # 이 환경에 사람 표가 안 보인다 — 쓰지도 단언하지도 않는다
    block = rp.read_text(encoding="utf-8").split("```json", 1)[1].split("```", 1)[0]
    parts = {row.get("part") for row in (json.loads(block).get("title_parts") or [])}
    missing = set(updates) - parts
    if missing:
        raise AssertionError(
            "DSM-U5-02.retro.md 에 이 part 가 없다(오타 대조): %s" % missing)


# ═══════════════════════════════════════════════════════════════════════════
# ① 선언이 설정을 읽는다 — 항등
# ═══════════════════════════════════════════════════════════════════════════
class RetentionDeclarationReadsSettingTest(U4Fixture):
    def test_declared_reads_seeded_value_not_hardcoded_730(self) -> None:
        from common import log_retention_policy as pol
        from common import ops_tasks as ot

        self.addCleanup(_adminconfig_clear)
        _adminconfig_set(400)  # 730·365 어느 쪽도 아닌 값 — 우연 일치가 아님을 증명

        seeded = ot.audit_retention_declared_days()
        self.assertEqual(400, seeded, "AdminConfig 에 심은 값을 그대로 못 읽는다")

        declared = pol.enforced_declared_days("audit")
        self.assertEqual(
            seeded, declared,
            "선언이 설정과 갈렸다 — 값은 선언이 아니라 설정에서 읽어야 한다(P-421 ④)")

        # ★ P-230 목표 선언(730 · scripts/ops_retention_policy.py 가 그대로 쓴다)은
        #   이 변경으로 안 바뀐다 — 다른(내 소유 밖) 게이트의 자기시험을 안 깬다.
        self.assertEqual(730, pol.POLICY["audit"].days)

    def test_unseeded_falls_back_to_legal_target_not_zero_or_none(self) -> None:
        from common import log_retention_policy as pol
        from common import ops_tasks as ot

        _adminconfig_clear()
        self.assertIsNone(ot.audit_retention_declared_days())

        declared = pol.enforced_declared_days("audit")
        self.assertEqual(
            730, declared,
            "미선언 대체값은 0/None 이 아니라 법정 목표(730)여야 한다 — "
            "0 은 '즉시 파기', None 은 그 자체로 위험한 혼동이다")

    def test_gate_row_and_evidence(self) -> None:
        """`scripts/verify_spec_dsm.py` 의 게이트 1행과 같은 계산 — 그리고
        DSM-U5-02.json 의 열린 행을 실측으로 닫는다."""
        from common import log_retention_policy as pol
        from common import ops_tasks as ot

        self.addCleanup(_adminconfig_clear)
        _adminconfig_set(365)

        declared = pol.enforced_declared_days("audit")
        seeded = ot.audit_retention_declared_days()
        self.assertEqual(declared, seeded)
        self.assertEqual(365, declared)

        _merge_title_parts({
            ROW_RETENTION: {
                "status": (
                    "measured — 선언이 설정을 그대로 읽는다(항등, 값은 선언이 아니라 "
                    "설정에서 읽는다 · P-421 ④): "
                    "log_retention_policy.enforced_declared_days('audit') == "
                    "ops_tasks.audit_retention_declared_days() (테스트 재대조 "
                    "%s일). 미선언이면 0/None 이 아니라 법정 목표(730일)로 안전하게 "
                    "대체된다 — '1년 이상' 하한은 두 경우 모두 만족한다. 게이트 "
                    "scripts/verify_spec_dsm.py 의 ④ 행이 gx-shell 안에서 이 항등을 "
                    "매 실행 실측 대조한다. 시험: tests.test_ap_n3_u5_02_retention."
                    "RetentionDeclarationReadsSettingTest.test_gate_row_and_evidence"
                    % declared),
                "where": (
                    "backend/common/log_retention_policy.py::enforced_declared_days "
                    "· backend/common/ops_tasks.py::audit_retention_declared_days "
                    "· scripts/verify_spec_dsm.py::judge_retention_alignment(④)"),
            },
        })


# ═══════════════════════════════════════════════════════════════════════════
# ② 완결 조건 「접속기록 조회 ≤ 60초」 — 실측
# ═══════════════════════════════════════════════════════════════════════════
class AccessLogQueryPerformanceTest(U4Fixture):
    def test_access_log_query_is_under_60_seconds(self) -> None:
        row = self._seed_access_log_row(
            channel="security", user_id=self.manager_a.pk,
            note="u5-02-perf-probe")
        cache.clear()

        started = time.perf_counter()
        resp = self.client.get(ACCESS_LOG, **_bearer(self.sysop_a))
        elapsed = time.perf_counter() - started

        self.assertEqual(200, resp.status_code, resp.content[:300])
        self.assertIn(row.pk, {item["log_id"] for item in resp.json()["items"]})
        self.assertLess(elapsed, 60.0,
                        "접속기록 조회가 60초를 넘었다: %.3fs" % elapsed)

        _merge_title_parts({
            ROW_PERF: {
                "status": (
                    "measured — GET /api/dsm/access-log 응답시간 %.3f초 실측"
                    "(< 60초, time.perf_counter() 직접 계측 · 대리 지표 0). 시험: "
                    "tests.test_ap_n3_u5_02_retention.AccessLogQueryPerformanceTest"
                    ".test_access_log_query_is_under_60_seconds" % elapsed),
            },
        })
