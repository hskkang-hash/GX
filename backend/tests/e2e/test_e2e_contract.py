# -*- coding: utf-8 -*-
"""공통 규약을 **시험이 시험을 검사한다** (D-291).

E2E 하나하나가 규약 ①~⑥ 을 지켰는지 사람이 확인하면, 그 확인은 다음 시나리오에서
빠진다. D-286: *"사람의 기억에 맡긴 절차는 도구가 우회한다."*

그래서 여기서 판정한다:
  · 해금된 시나리오에 **모듈이 실재하는가** (없으면 실패 — 조용히 빠지지 못한다)
  · 그 모듈이 규약 ①~④ 의 **시험 메서드를 실제로 갖는가**
  · 실시간 대기(`sleep`)를 쓰지 않는가 (규약 ⑤)
  · 실물 표본 출처를 선언했는가 (D-289)
  · ★ **이 판정기 자신이 위반을 잡는가** (양성 대조 · D-277)
"""
from __future__ import annotations

import importlib
import inspect
from pathlib import Path
from unittest import TestCase

from tests.e2e.e2e_contract import (
    FORBIDDEN_WAITS,
    KERNEL_PACKAGES,
    LOCKED_CAPABILITIES,
    REQUIRED_ATTRS,
    REQUIRED_METHODS,
    SCENARIOS,
    Scenario,
    Step,
    StepLedger,
)

#: 등재부가 잠그는 이름 집합. **개수가 아니라 이름이다** (D-285 ②).
#: 시나리오를 늘리려면 여기와 `e2e_contract.SCENARIOS` 를 같은 커밋에서 함께 고친다.
EXPECTED_CODES = {"E2E-1", "E2E-2", "E2E-3"}


def _module_of(scenario: Scenario):
    try:
        return importlib.import_module(scenario.module)
    except ModuleNotFoundError:
        return None


def _test_methods(module) -> set[str]:
    names: set[str] = set()
    for _, obj in inspect.getmembers(module, inspect.isclass):
        if not issubclass(obj, TestCase):
            continue
        names |= {n for n in dir(obj) if n.startswith("test_")}
    return names


class E2EContractTest(TestCase):
    """등재부와 실제 시험 파일이 갈리지 않게 한다."""

    def test_registry_locks_the_scenario_names(self) -> None:
        """이름 집합이 정본이다. 시나리오가 조용히 사라지면 여기서 멈춘다."""
        self.assertEqual(
            EXPECTED_CODES, set(SCENARIOS),
            "E2E 시나리오 이름 집합이 바뀌었습니다. 늘리거나 줄이려면 "
            "e2e_contract.SCENARIOS 와 EXPECTED_CODES 를 **같은 커밋에서** 고치십시오 "
            "(D-285 ② — 개수가 아니라 이름으로 잠근다).")

    def test_unlocked_scenario_has_a_module(self) -> None:
        """해금됐는데 파일이 없으면 실패. **여기가 증분 규칙의 강제 지점이다.**

        K2 가 붙는 순간 E2E-1 의 4·5 단계가 해금되고, 그러면 시험 파일이 **있어야 한다.**
        "다음 턴에 쓰겠다"는 여기서 통과하지 못한다 (D-291 증분 규칙).
        """
        missing = []
        for scenario in SCENARIOS.values():
            if not scenario.unlocked:
                continue
            if _module_of(scenario) is None:
                missing.append(
                    f"{scenario.code}: 해금 단계 {len(scenario.active_steps)}건 "
                    f"(커널 실재) 인데 {scenario.module} 이 없다"
                )
        self.assertEqual([], missing,
                         "해금된 E2E 에 시험 모듈이 없습니다 — " + "; ".join(missing))

    def test_pending_reason_is_gone_once_unlocked(self) -> None:
        """해금 전에만 사유가 허용된다. 해금 후에도 남아 있으면 사유가 아니라 **핑계**다."""
        stale = [s.code for s in SCENARIOS.values() if s.unlocked and s.pending_reason]
        self.assertEqual([], stale,
                         f"해금됐는데 pending_reason 이 남아 있습니다: {stale}. "
                         "사유를 지우고 시험을 쓰거나, 왜 아직 못 쓰는지를 다시 적으십시오.")

    def test_locked_scenario_states_why(self) -> None:
        """아직 못 여는 시나리오는 **이유를 적는다.** 빈 자리는 잊힌 자리다."""
        silent = [s.code for s in SCENARIOS.values()
                  if not s.unlocked and not s.pending_reason.strip()]
        self.assertEqual([], silent,
                         f"해금 전 시나리오에 사유가 없습니다: {silent} (D-264 — 모르면 멈춘다).")

    def test_every_unlock_name_is_known_and_has_a_reason(self) -> None:
        """★ 단계가 가리키는 해금 이름은 **커널이거나, 사유 있는 잠긴 능력**이다.

        셋째는 없다. 이름을 오타 내면 그 단계는 **영원히 해금되지 않으면서 아무도
        모르는** 상태가 된다 — 빠진 줄은 보이지 않는다 (D-264).
        """
        unknown = []
        for scenario in SCENARIOS.values():
            for step in scenario.steps:
                if step.unlocked_by is None:
                    continue
                if step.unlocked_by in KERNEL_PACKAGES:
                    continue
                reason = LOCKED_CAPABILITIES.get(step.unlocked_by, "")
                if not reason.strip():
                    unknown.append(
                        f"{scenario.code} {step.no}단계 → {step.unlocked_by!r}")
        self.assertEqual(
            [], unknown,
            f"해금 이름이 커널도 아니고 사유 있는 잠긴 능력도 아닙니다: {unknown}. "
            "KERNEL_PACKAGES 에 넣거나 LOCKED_CAPABILITIES 에 **사유와 함께** 등재하십시오.")

    def test_locked_capability_is_not_secretly_a_kernel(self) -> None:
        """잠긴 능력과 커널 이름이 겹치면 어느 쪽이 정본인지 알 수 없다."""
        overlap = sorted(set(LOCKED_CAPABILITIES) & set(KERNEL_PACKAGES))
        self.assertEqual(
            [], overlap,
            f"같은 이름이 커널과 잠긴 능력 양쪽에 있습니다: {overlap}. "
            "여는 커밋에서 LOCKED_CAPABILITIES 의 줄을 **지우고** KERNEL_PACKAGES 로 옮기십시오.")

    def test_every_e2e_meets_the_common_contract(self) -> None:
        """★ 규약 ①~④ 를 **메서드 이름으로** 확인한다.

        규약을 지켰다는 주석과, 그 이름의 시험이 실제로 도는 것은 다르다.
        """
        problems: list[str] = []
        for scenario in SCENARIOS.values():
            module = _module_of(scenario)
            if module is None:
                continue  # 위 시험이 이미 판정한다 — 여기서 두 번 실패시키지 않는다
            names = _test_methods(module)
            for rule, (method, what) in REQUIRED_METHODS.items():
                if method not in names:
                    problems.append(
                        f"{scenario.code} 규약 {rule} 누락 — `{method}` 가 없다 ({what})")
            for attr in REQUIRED_ATTRS:
                if not getattr(module, attr, None):
                    problems.append(f"{scenario.code}: 모듈 변수 `{attr}` 가 비었다")
        self.assertEqual([], problems, "E2E 공통 규약 위반 — " + "; ".join(problems))

    def test_no_realtime_wait_in_e2e_modules(self) -> None:
        """규약 ⑤ — 논리 시계. CI 에서 30초를 **실제로 기다리지 않는다.**

        기다리는 시험은 느려서 꺼지고, 꺼진 시험은 없는 시험이다.
        """
        offenders: list[str] = []
        for scenario in SCENARIOS.values():
            module = _module_of(scenario)
            if module is None:
                continue
            src = Path(inspect.getfile(module)).read_text(encoding="utf-8")
            for token in FORBIDDEN_WAITS:
                if token in src:
                    offenders.append(f"{scenario.code}: {token}")
        self.assertEqual([], offenders,
                         "E2E 에 실시간 대기가 있습니다 — 시간 단언은 논리 시계로 하십시오 "
                         f"(D-291 규약 ⑤): {offenders}")

    def test_the_checker_itself_catches_violations(self) -> None:
        """★ **양성 대조** — 이 판정기가 눈이 멀지 않았는가 (D-277).

        규약을 하나도 안 지킨 가짜 모듈을 만들어 넣어 본다. 통과하면 위의 초록은
        아무것도 증명하지 않는다.

        ※ D-289(표본은 실물에서): 아래 `real` 는 **저장소의 진짜 E2E 모듈**에서 뽑는다.
          합성만으로 검증한 탐지기는 "내가 만든 것만 잡는" 상태가 된다.
        """
        class _Fake:
            """규약 메서드가 하나도 없는 가짜 시나리오 모듈."""

        fake_names = _test_methods(_Fake)
        missing = [m for m, _ in REQUIRED_METHODS.values() if m not in fake_names]
        self.assertEqual(
            len(REQUIRED_METHODS), len(missing),
            "합성 대조: 규약 메서드가 없는 모듈을 통과시켰습니다 — 판정기가 눈이 멀었습니다.")

        # ── 실물 표본 (D-289) ────────────────────────────────────────────
        real = next((s for s in SCENARIOS.values() if _module_of(s) is not None), None)
        if real is None:
            self.assert_no_real_sample_is_legitimate()  # 아래 참조 — skip 하지 않는다
            return
        module = _module_of(real)
        names = _test_methods(module)
        for rule, (method, _) in REQUIRED_METHODS.items():
            self.assertIn(
                method, names,
                f"실물 표본 {real.code} 이 규약 {rule} 을 만족하지 않습니다 — "
                "판정기가 정상을 위반으로 보거나, 실물이 실제로 규약을 어겼습니다.")

    def assert_no_real_sample_is_legitimate(self) -> None:
        """★ 여기서 `skipTest` 를 부르지 않는다 (절대금지 #4).

        실물 표본이 없다는 사실을 **조용히 넘기지 않는다.** 다만 두 상태를 가른다:

          (가) 아직 아무 시나리오도 해금되지 않았다 → 실물이 **있을 수 없다.**
               D-289 의 "표본은 실물에서 뽑는다"는 실물이 존재할 때의 요구다.
               이때만 합성 대조로 이 판정기를 검증한 상태를 허용하고, 그 사실을 **출력한다.**
          (나) 해금됐는데 모듈이 없다 → **실패.** `test_unlocked_scenario_has_a_module`
               가 이미 잡지만, 여기서도 한 번 더 막는다 — 우연에 기대지 않는다(D-274).

        (가)는 이 파일이 K2 착수 직전 한 턴 동안만 지나는 자리다. K2 가 붙으면
        E2E-1 이 의무가 되고, 그 순간부터 실물 표본이 강제된다.
        """
        unlocked = [s.code for s in SCENARIOS.values() if s.unlocked]
        self.assertEqual(
            [], unlocked,
            f"해금된 시나리오 {unlocked} 가 있는데 실물 E2E 모듈이 하나도 없습니다 — "
            "합성 대조만으로 이 판정기를 검증할 수 없습니다 "
            "(D-289 — 표본 최소 1건은 저장소 실물에서 뽑는다).")
        print(
            "\n[E2E] 해금된 시나리오가 아직 없어 실물 표본을 뽑을 수 없다 — "
            "합성 대조 4건으로만 판정기를 검증했다 (D-289 미충족 상태를 명시한다)."
        )


class StepLedgerTest(TestCase):
    """규약 ⑥ — 실패 표가 **미측정과 실패를 가르는가**."""

    STEPS = (Step(1, "첫 단계"), Step(2, "둘째 단계"), Step(3, "셋째 단계"))

    def test_unreached_steps_are_not_reported_as_passed(self) -> None:
        ledger = StepLedger(scenario="E2E-0")
        ledger.record(self.STEPS[0], ok=True)
        ledger.record(self.STEPS[1], ok=False, note="여기서 끊겼다")
        table = ledger.render(self.STEPS)

        self.assertIn("FAIL", table, "실패한 단계가 표에 없습니다.")
        self.assertIn("미측정", table,
                      "도달하지 못한 단계가 '미측정' 으로 구별되지 않습니다 — "
                      "미측정을 통과로 읽는 것이 이 저장소가 반복해 만난 실패입니다 (D-274).")
        self.assertNotIn("OK    3.", table, "도달하지 못한 3단계가 통과로 표시됐습니다.")

    def test_table_lists_every_planned_step(self) -> None:
        ledger = StepLedger(scenario="E2E-0")
        table = ledger.render(self.STEPS)
        for step in self.STEPS:
            self.assertIn(step.title, table,
                          f"{step.no}단계가 표에서 빠졌습니다 — 빠진 줄은 보이지 않습니다.")
