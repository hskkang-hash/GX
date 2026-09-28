# -*- coding: utf-8 -*-
"""P-356 — OPS annex O-10(키·자격 회전) · O-04(모델 레지스트리) 실측. 차선 O · 턴 AM.

캐시 처리: 해당 없음 — 이 파일은 HTTP 를 안 두드린다. 있는 것(기존 모듈)과 없는
것(annex 가 이름 대는 자리)을 grep·import 로 실측할 뿐이라 캐시가 낄 자리가 없다.

이 파일이 왜 P-356 넷을 안 갖춘 채로 존재하나
-----------------------------------------------
O-10·O-04 는 annex(`docs/agent/roadmap/기능명세_미포함표_20260925.md`) 원문에
「없음 · 신설 필요」로 적혀 있었고, 이번 턴(P-376 반쪽 금지 규율 아래) 조사 결과도
**같은 결론**이다 — 「실제 구현」한 줄을 못 채운다(아래 각 클래스 머리말 참조).
P-376 은 「반쪽을 닫힌 것으로 올리지 말라」이지 「조사한 사실을 시험 없이 두라」가
아니다 — 그래서 이 파일은 **승격 시험이 아니라 「무엇이 없는가」를 코드로 고정하는
시험**이다. `docs/agent/evidence/SPEC/O_promotions.md` 의 표가 이 파일의 결론을
그대로 옮긴 것이고, 여기 있는 시험들이 그 표가 늙지 않게 한다 — 나중에 누가
`ModelVersion` 을 만들면 `ModelRegistryAbsenceTest` 가 먼저 실패해서 표를 고치라고
말한다.

`scripts/verify_spec_ops.py` 가 이 파일을 「길목」으로 돈다(`--run` 일 때만 — 기본은
`--no-run`, 레포 규약대로 닫힌 절이 없으므로 매 판정에서 다시 돌릴 것이 없다).
"""
from __future__ import annotations

import ast
import inspect
from pathlib import Path

from django.test import SimpleTestCase

ROOT = Path(__file__).resolve().parents[2]


# ═══════════════════════════════════════════════════════════════════════════
# O-04 「모델 레지스트리」 — **저장처·판정 어느 쪽도 없다**
# ═══════════════════════════════════════════════════════════════════════════
class ModelRegistryAbsenceTest(SimpleTestCase):
    """완결 조건(플랫폼 구조설계서 §7 O-04)은 「배포 → 테넌트 오탐률 추세 표시」다.
    그러려면 **모델 버전 · 테넌트 배포 · 롤백 · 카메라별 바인딩**을 담을 저장처가
    있어야 한다 — 없다(전수 grep, 아래가 그 grep 을 시험으로 고정한다)."""

    _NAMES = ("ModelVersion", "ModelRegistry", "ModelDeployment", "ModelBinding")

    def test_no_model_registry_storage_exists(self) -> None:
        hits: list[str] = []
        for py in ROOT.glob("backend/**/models.py"):
            if any(part in {"migrations", "__pycache__", "node_modules"}
                  for part in py.parts):
                continue
            try:
                src = py.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            for name in self._NAMES:
                if f"class {name}" in src:
                    hits.append(f"{py.relative_to(ROOT)}::{name}")
        self.assertEqual(
            [], hits,
            "모델 레지스트리 저장처가 생겼습니다 — O_promotions.md 의 「없다」 결론을 "
            "고쳐야 합니다(이 시험이 그 드리프트를 잡는 것이 존재 이유입니다).")

    def test_the_only_model_facing_number_is_false_positive_rate_not_a_registry(
            self) -> None:
        """있는 것은 **오탐률 하나**(`kernels.k6_feedback.false_positive_rate`)뿐이고,
        그것은 판정자별·카메라별 판정 결과의 비율이지 **AI 모델 버전**과 엮이지
        않는다 — 「배포 → 추세」를 이을 축이 없다는 것을 실측으로 고정한다."""
        from kernels.k6_feedback.services import false_positive_rate

        sig = inspect.signature(false_positive_rate)
        params = set(sig.parameters)
        self.assertNotIn(
            "model_version", params,
            "false_positive_rate 가 model_version 인자를 받게 됐다면 O-04 재조사가 "
            "필요합니다 — 오탐률과 모델 버전이 이어질 자리가 생겼다는 뜻입니다.")


# ═══════════════════════════════════════════════════════════════════════════
# O-10 「키·자격 회전」 — **조각은 여럿, 한 콘솔은 없다. AND 조건 절반이 이 환경에서
# 구조적으로 못 잰다**
# ═══════════════════════════════════════════════════════════════════════════
class KeyRotationCoverageTest(SimpleTestCase):
    """완결 조건(플랫폼 구조설계서 §7 O-10)은 **AND** 다 —
    「회전 뒤 게이트 계정 로그인 4/4 **·** 옛 키 401」. 뒤 반(옛 키 401)은
    `kernels.k5_trust.inbound_keys.rotate_key` 로 Django test client 실측이
    가능하다(F-05 들어오는 키(inbound_api_key) 회전 문, 이미 있다 —
    `EVENT_ENTRY_SURFACE` 참조). **앞 반(게이트 계정 로그인)은 못 잰다** — 이유는
    사유가 아니라 **구조**다: 아래가 그 구조를 코드로 고정한다."""

    def test_gate_accounts_are_structurally_excluded_from_the_shared_rotation(
            self) -> None:
        """`rotate_shared_passwords.py`(O-10 이 가리키는 「DB 자격」 회전 도구)는
        게이트 계정을 **일부러 회전하지 않는다**(`NEVER_TOUCH`). 그러므로 이 스크립트를
        돌려도 「게이트 계정이 새 값으로 로그인된다」는 애초에 관측 대상이 아니다 —
        관측하려면 **게이트 계정 자신의 자격을 실제로 바꾸고 실제 서버에 로그인**해야
        하는데, 그것은 이 저장소 규약(§ 차선 공통 규칙 「Don't log in to live
        servers」)이 이 차선에 금지한 행위다. annex 의 AND 조건 절반이 이 환경에서
        원천적으로 재현 불가능하다는 사실을 여기서 고정한다."""
        import importlib.util
        import sys

        #: ★ 컨테이너와 호스트의 경로가 다르다(메모리 「재생성 창 함정 넷」·
        #:   `test_verify_spec_fws_gate_can_fail.py::_gate` 와 같은 계산) — gx-shell
        #:   안에서는 `scripts/` 가 컨테이너 루트가 아니라 `/repo/scripts` 에 있다
        #:   (`docs/` 만 루트에 바로 물려 있다, `test_p356_u2_spec_promotions.py::
        #:   _repo_root` 머리말 실측 그대로). 둘 다 시도한다.
        path = None
        for cand in (Path("/repo/scripts/rotate_shared_passwords.py"),
                    ROOT / "scripts" / "rotate_shared_passwords.py"):
            if cand.is_file():
                path = cand
                break
        self.assertIsNotNone(path, "rotate_shared_passwords.py 를 어디서도 못 찾았다 "
                                   "(/repo/scripts · %s 둘 다 확인)" % (ROOT / "scripts"))
        spec = importlib.util.spec_from_file_location("rotate_shared_passwords", path)
        module = importlib.util.module_from_spec(spec)
        sys.modules.setdefault("rotate_shared_passwords", module)
        spec.loader.exec_module(module)

        gate_accounts = {
            "gxseed_u1_operator", "gxseed_u2_manager", "gxseed_u3_field",
            "gxseed_u4_official", "gxseed_u5_sysop",
        }
        self.assertTrue(
            gate_accounts.issubset(module.NEVER_TOUCH),
            "게이트 계정 이름이 NEVER_TOUCH 에서 빠졌습니다 — O-10 조사 결론을 "
            "다시 봐야 합니다.")

    def test_the_401_half_is_reachable_through_an_existing_kernel_function(
            self) -> None:
        """반대로 **옛 키 401** 은 이미 있는 door 로 실측 가능하다는 사실도 함께
        고정한다 — 「전혀 없다」가 아니라 「반쪽은 있고 반쪽은 이 환경에서 원천
        차단」이라는 것이 O-10 의 정확한 상태다(P-376 이 요구하는 정직한 갈래)."""
        from kernels.k5_trust import inbound_keys

        self.assertTrue(hasattr(inbound_keys, "rotate_key"))
        sig = inspect.signature(inbound_keys.rotate_key)
        self.assertIn("key_id", sig.parameters)

    def test_credentials_table_does_not_cover_db_minio_or_vapid(self) -> None:
        """표 ②(`kernels.k5_trust.credentials.CREDENTIALS`)는 annex 가 이름 대는
        여섯 중 **나가는 API 키 셋**만 다룬다 — 서명키·DB/MinIO 자격·VAPID 는 각자
        다른 곳에 흩어져 있다(`webhook_signing_keys.py`·`rotate_shared_passwords.py`·
        `apps/dsm/notify_prefs.py`). **하나의 O-10 콘솔로 통합된 곳이 없다**는
        것이 이 절의 핵심 결손이다 — 그 흩어짐을 여기 실측으로 고정한다."""
        from kernels.k5_trust.credentials import CREDENTIALS

        names_lower = " ".join(CREDENTIALS).lower()
        for absent_hint in ("db", "minio", "vapid"):
            self.assertNotIn(
                absent_hint, names_lower,
                f"표 ②에 {absent_hint} 관련 키가 생겼습니다 — O-10 재조사가 필요합니다.")
