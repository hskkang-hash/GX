# -*- coding: utf-8 -*-
"""OPS-07 — **로그 보존 정책의 선언** (P-230 · 2026-09-21 · 턴 AB · 차선 F).

    세종 판정 P-230 원문 (WO-GX-20260921-04 §5):
      「감사 로그 보존 — 정책 선언: **감사 2년 · 사건 기록 영구 · 수집기 로그 90일**
       (개인정보 안전성 확보조치 접속기록 보관 기준 이상 [추정 · S 가 조문 대조]).
       이 턴은 만료 표식·건수 산출·`gate:` 부착까지. **삭제 실행은 대표 한 마디 뒤**
       (결정문에 없는 삭제는 삭제가 아니다).」

★ 이 파일은 **선언이지 집행이 아니다** — 여기에 지우는 손은 없다
------------------------------------------------------------------
이 모듈은 수(數)와 그 수의 **임자·근거·부류**만 갖는다. `delete()` 도
`purge` 도 없고, 앞으로도 여기 두지 않는다. 집행하는 손은 따로 있고
(`common/ops_tasks.py::ops_audit_purge_beat` · dj-core `purge_old_audit_logs`),
그 손이 도는 조건은 **선언이 그 손이 읽는 자리에 심겨 있을 때**뿐이다.

    선언(이 파일)  :  「무엇을 얼마나 보관한다고 우리가 말했는가」
    집행 값        :  `AdminConfig::System > security.audit_log_retention_days`
                      — dj-core 가 **그 자리 하나만** 읽는다(§0.4 · 우린 못 고친다)
    코드 기본값    :  dj-core `purge_old_audit_logs` 의 **90** — 아무도 정한 적이 없다

★★ **셋이 지금 다르다. 한쪽으로 조용히 맞추지 않았다** [조율자 지시 2026-09-21 20:5x]
---------------------------------------------------------------------------------
    P-230 선언           **730일**(감사 2년)          ← 세종 · 2026-09-21
    이 기계에 심긴 값     **365일**                    ← P-67 세종 선언(개발·스테이징)
                                                        `config/retention_seed.py`
    dj-core 코드 기본값   **90일**                     ← 아무도 정한 적이 없다

**셋을 나란히 적는 것이 이 파일의 일 절반이다.** 맞추는 것은 쓰기이고,
그 쓰기는 `AdminConfig` 공용 마스터에 닿는다 — 이 턴의 차선 몫이 아니다.
`scripts/ops_retention_policy.py` 가 매 실행마다 **셋을 나란히 찍고**,
갈리면 빨강을 낸다. 조용히 갈려 있는 것이 이 자리가 세 턴을 숨어 있던 방법이었다.

★ 근거 조문은 **[추정]이다 — 단정하지 않는다**
----------------------------------------------
「개인정보 안전성 확보조치 기준」의 접속기록 보관 조항이 근거로 **지목**돼 있으나,
그 조문이 이 표(`logger_auditlogs`)에 그대로 걸리는지는 **차선 S 가 대조한다.**
여기서 조문 번호를 적지 않는 것은 게을러서가 아니다 — 틀린 조문을 적으면
그 다음 사람이 **그 조문 위에서 파기를 켠다.**

★ 「영구」는 `None` 이고 0 이 아니다
-----------------------------------
`days=None` 은 **파기하지 않는다**는 뜻이다. `0` 으로 적으면 「오늘 것도 만료」가
되고, 그 수 하나로 사건 기록 전건이 만료 표식을 받는다. 표 ① 임계값이
`default=None` 으로 같은 함정을 막았다(D-284 · D-290) — 같은 규약을 쓴다.
"""
from __future__ import annotations

from dataclasses import dataclass

#: 이 선언의 임자. **선언에는 임자와 근거가 있고, 기본값에는 없다**(P-67).
DECLARED_BY = "세종(CPO) · P-230 · WO-GX-20260921-04 §5"
DECLARED_AT = "2026-09-21"

#: 근거 조문. [턴 AE] 차선 S 가 `docs/design/GX-LAW-09_접속기록_설계_v1.0.md`
#: §2 에서 국가법령정보센터 원문과 대조를 끝냈다 — 그 문서가 이 문자열의
#: 소스다(두 벌로 안 적는다·D-212, 값만 여기 옮겨 심는다).
#:
#: ★ 대조 결과: 「개인정보의 안전성 확보조치 기준」(개인정보보호위원회고시)
#:   **제8조(접속기록의 보관 및 점검) ①** — "개인정보처리자는 개인정보처리
#:   시스템에 접속한 자(정보주체는 제외한다)의 접속기록을 **1년 이상**
#:   보관·관리하여야 한다. 다만 5만 명 이상의 정보주체에 관하여 개인정보를
#:   처리하거나, 고유식별정보 또는 민감정보를 처리하는 개인정보처리시스템의
#:   경우에는 **2년 이상** 보관·관리하여야 한다."
#:
#:   위 `POLICY["audit"].days = 730`(2년)은 「5만 명 이상/민감정보」 조건
#:   쪽으로 **안전하게** 잡은 값이다 — GuardianX 가 그 조건을 실제로 넘는지는
#:   **[확인 안 됨]**(테넌트별 정보주체 수 집계는 GX-LAW-09 §2 조사 범위
#:   밖이었다). 조건이 안 맞아도 원칙(1년) 이상이므로 730일은 **과소가 아니다.**
#:   조 번호의 시행일별 이동 이력이 있어 **차수(호수) 표기는 여전히 [확인]**
#:   대상이다 — 법률대리인 최종 대조 전까지 "제8조①" 이라는 조 번호 자체는
#:   믿되, 항·호 세부 표기가 바뀌었을 가능성은 열어 둔다.
LEGAL_BASIS = (
    "「개인정보의 안전성 확보조치 기준」(개인정보보호위원회고시) 제8조(접속기록의 "
    "보관 및 점검) ① — 접속기록 보관 1년 이상(5만 명 이상의 정보주체 처리 또는 "
    "고유식별정보·민감정보 처리 시스템은 2년 이상). 대조 완료 "
    "[GX-LAW-09 §2 · 2026-09-23 · 차선 S · 국가법령정보센터 원문 대조] — "
    "이 저장소는 원칙 조건(1년)을 웃도는 730일(2년)을 선언해 두었다. "
    "「5만 명 이상/민감정보」 조건 해당 여부는 [확인 안 됨](테넌트별 정보주체 수 "
    "미집계) · 조 번호의 항·호 세부 표기는 [확인](법률대리인 최종 대조 전)"
)

#: dj-core 가 **실제로 읽는 자리**. 두 벌로 적지 않는다 —
#: `common/ops_tasks.AUDIT_RETENTION_CONFIG` 와 같은 자리를 가리킨다.
ENFORCEMENT_SITE = "AdminConfig::System > security.audit_log_retention_days"

#: dj-core `core/logger/tasks.py::purge_old_audit_logs` 에 박힌 수.
#: **아무도 정한 적이 없다**(OPS-07b 실측 2026-09-05). 비교하려고 적어 둔다.
DJCORE_CODE_DEFAULT_DAYS = 90


@dataclass(frozen=True)
class RetentionClass:
    """보존 부류 하나. **수가 아니라 「무엇을 얼마나」라는 진술**이다."""

    key: str
    title: str
    #: `None` = **영구**(파기하지 않는다). `0` 이 아니다.
    days: int | None
    #: 어느 표·어느 수집기가 이 부류인가. 사람 말이 아니라 **잴 수 있는 이름**.
    applies_to: str
    #: 지금 이 수가 실제로 걸려 있는가. 걸릴 자리가 없으면 그 사실을 적는다.
    enforced_where: str
    why: str


#: ★ P-230 — 부류 **셋**. 여기 없는 로그는 이 선언이 답하지 않는다.
POLICY: dict[str, RetentionClass] = {
    "audit": RetentionClass(
        key="audit",
        title="감사 로그 — **2년**",
        days=730,
        applies_to="logger_auditlogs (DB · dj-core AuditLogs)",
        enforced_where=ENFORCEMENT_SITE,
        why="접속기록은 「누가 무엇을 언제 봤는가」이고, 사고 조사는 대개 몇 달 뒤에 "
            "시작된다. 90일은 그 조사가 시작되기 전에 증거가 사라지는 길이다. "
            "⚠ 이 기계에 **심긴 값은 여전히 365** 다(재확인 2026-09-23 · 턴 AF) — "
            "이 선언(730)과 갈려 있다. 맞추려면 `config/retention_seed.py` 의 "
            "시드값(365)을 730 으로 고치고 `scripts/seed_retention_declaration.py "
            "--unseed` 뒤 `--apply` 로 `AdminConfig` 에 다시 심어야 하는데, 그 두 "
            "파일은 **이 턴 이 차선의 소유표 밖**이다(§2 미배정) — 써 두기만 하고 "
            "쓰지 않았다. ★ 안전성은 확인했다: [실측 2026-09-23] "
            "`ops-audit-purge-daily`·`purge-audit-logs-daily` 둘 다 "
            "`PeriodicTask.enabled=False` — 지금은 365 든 730 이든 **아무 것도 "
            "안 지운다.** 365→730 은 늘리는 쪽이라 스위치가 켜져도 이미 지워진 "
            "행은 없다(파기 자체가 한 번도 안 돌았다). 갈렸다는 사실과 그 안전성을 "
            "판정기가 함께 찍는다",
    ),
    "incident": RetentionClass(
        key="incident",
        title="사건 기록 — **영구**",
        days=None,
        applies_to="사건/이벤트 기록 (K1 이벤트 · 사건 보고)",
        enforced_where="**없다** — 파기하는 손 자체를 두지 않는다. 그것이 집행이다",
        why="영구는 「아주 긴 수」가 아니라 **파기 경로가 없다**는 뜻이다. 수를 적으면 "
            "언젠가 그 수가 돌고, 사건 기록은 한 번 사라지면 되돌릴 수 없다. "
            "`days=None` 은 0 일이 아니다 — 만료 표식을 **한 행도** 붙이지 않는다",
    ),
    "collector": RetentionClass(
        key="collector",
        title="수집기 로그 — **90일**",
        days=90,
        applies_to="컨테이너 stdout (`json-file`) · `settings.LOGGING` 파일 핸들러",
        enforced_where="`json-file` 회전(`max-size 10m × max-file 5`) — **크기 기반이다**",
        why="⚠ **선언은 기간이고 집행은 크기다.** `json-file` 은 날짜를 모른다 — "
            "조용한 달에는 90일보다 오래 남고, 시끄러운 날에는 몇 시간 만에 밀린다. "
            "그러므로 「90일 보존」은 이 수집기에 대해 **약속이 아니라 목표**이고, "
            "판정기는 그 둘을 갈라서 적는다. 합치면 「걸었다」가 「지켜진다」가 된다",
    ),
}

#: 부류 이름 순서 — 보고에 적는 차례를 코드가 정한다(사람이 매번 안 고르게).
ORDER: tuple[str, ...] = ("audit", "incident", "collector")


def declared_days(key: str) -> int | None:
    """그 부류의 선언 일수. **영구는 `None`** 이고 0 이 아니다."""
    return POLICY[key].days


def divergence(seeded_days: int | None) -> list[tuple[str, object]]:
    """감사 보존의 **세 수를 나란히** 낸다. 맞추지 않는다 — 나란히 적을 뿐이다.

    Args:
        seeded_days: `ENFORCEMENT_SITE` 에서 실제로 읽힌 값. 못 읽었으면 `None`.

    Returns:
        `(이름, 값)` 목록. 값이 `None` 이면 **미선언/못 읽음**이지 0 이 아니다.
    """
    return [
        ("P-230 선언", POLICY["audit"].days),
        ("심긴 값(%s)" % ENFORCEMENT_SITE, seeded_days),
        ("dj-core 코드 기본값", DJCORE_CODE_DEFAULT_DAYS),
    ]


def aligned(seeded_days: int | None) -> bool:
    """선언과 **집행 자리의 값**이 같은가. 다르면 화면이 말하는 수와 지우는 수가 갈린다."""
    return seeded_days is not None and seeded_days == POLICY["audit"].days
