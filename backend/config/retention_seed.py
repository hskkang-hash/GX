# -*- coding: utf-8 -*-
"""P-67 — **보존 일수·백업의 기본값은 없다. 선언만 있다** (2026-09-06 · 차선 E).

    세종(CPO) 판정 P-67 원문:
      "보존 일수·백업 목적지·일정에 **코드 기본값 없음.** 미선언 테넌트 =
       「미선언」 상태로 화면에 빨강 배지 · 파기·백업 **돌지 않음**."
      "**개발·스테이징 선언(세종 · 이 문서로 집행)**: 감사 로그 보존 365일 ·
       스냅샷·구간 참조 30일 · 백업 매일 03:00 · 목적지 별도 볼륨 `/backup` ·
       백업 보존 14일 · 복구 시험 주 1회 자동."

★ 왜 이 파일이 「기본값」이 아닌가 — **셋이 다르다**
---------------------------------------------------
    기본값 : 아무도 정하지 않았는데 **집행하는 코드가 수를 지어낸다.**
             누가 정했는지 되짚을 수 없고, 고객 환경에서도 그 수가 돈다.
    선언   : **정한 사람과 그 환경이 있다.** 여기 적힌 수의 임자는 세종이고,
             적용 범위는 `DECLARED_ENVIRONMENTS` 둘뿐이다.
    운영 값: **고객이 U5 설정 화면에서 선언한다.** 코드가 정하지 않는다 —
             그래서 `production` 은 이 표를 **한 칸도 읽지 않는다.**

    ⚠ 이 파일을 「기본값 파일」로 쓰면 P-67 이 원상복구된다. 새 이름을 넣기 전에
      물어라: **이 수를 정한 사람이 누구이고 어느 환경에만 도는가.**
      답이 없으면 그것은 선언이 아니라 기본값이다 — 넣지 마라.

★ 함정 (세종이 미리 적었다 · 지시서 §4 함정 ①)
----------------------------------------------
    「기본값을 지우면 **개발 테넌트도 미선언이 된다**」 — 그래서 순서가 곧 내용이다:
        ① 이 시드를 먼저 넣는다   ② **그 다음에** 코드 기본값을 지운다.
    거꾸로 하면 그 사이 개발 환경의 파기·백업이 조용히 멈추고, 멈춘 것을
    아무도 모른 채 초록으로 읽는다.

★ 환경변수가 **언제나 이긴다**
------------------------------
    이 표는 「아무도 안 정했을 때 개발·스테이징이 정한 것」이다. `.env` 나
    컨테이너 환경이 같은 이름을 주면 그 값이 이긴다 — 시드가 운영자의 선언을
    덮어쓰면 그 순간 이것은 기본값이 된다.
"""
from __future__ import annotations

#: 이 선언이 도는 환경. **여기 없는 환경(운영)은 한 칸도 안 읽는다.**
#: `settings.GUARDIANX_ENVIRONMENT` 와 같은 낱말을 쓴다.
DECLARED_ENVIRONMENTS: tuple[str, ...] = ("development", "staging")

#: 세종이 이 판정문으로 집행한 수. **우리가 고르는 수가 아니다.**
#: 값 옆의 낱말은 판정문의 낱말 그대로다 — 옮겨 적으면서 뜻이 바뀌지 않게.
SEED: dict[str, object] = {
    # 감사 로그 보존 **365일** (감사 대응 최소 · LAW-03 초안).
    # ⚠ dj-core `purge_old_audit_logs` 의 코드 기본값 90 은 **아무도 정한 적이 없다**
    #   [실측 2026-09-05 · OPS-07b]. 그 90 을 우리 층에서 받아 주지 않는 것이
    #   `common/ops_tasks.py::audit_retention_declared_days()` 이고, 이 줄이
    #   개발·스테이징에서 그 자리를 **선언으로** 채운다.
    "AUDIT_LOG_RETENTION_DAYS": 365,

    # 스냅샷·구간 참조 **30일** (용량산정서 기본). 전역 선언이므로 개발 DB 의
    # 테넌트 10개가 모두 이 수로 선언된 것이 된다
    # (`retention.declared_retention_days()` 가 전역 선언을 되짚는다).
    "VIDEO_RETENTION_DAYS": 30,

    # 백업 **매일 03:00** — 시각 자체는 beat 표(`config/celery.py`)에 있고,
    # 여기 있는 것은 **켜짐/꺼짐**이다. 끈 채로 등록만 해 두는 것이 착시 ⑨ 다.
    "OPS_BACKUP_SCHEDULE_ENABLED": True,

    # 목적지 **별도 볼륨 `/backup`** (OPS-12a). 「같은 디스크는 백업이 아니다」 —
    # 이 경로는 백업 컨테이너 **안**의 자리이고, 그 뒤를 받치는 것은
    # 도커 볼륨 `OPS_BACKUP_VOLUME` 이다. 저장소 작업복사본이 아니다.
    # ★ 감사 로그 파기의 **되돌림 저널**도 이 칸 아래에 산다 (OPS-07b · 턴 H):
    #   `/backup/audit_purge_journal/`. 이름을 하나 더 만들지 않았다 — 저널의 자리가
    #   백업과 갈라질 이유가 없고, 아무도 안 채우는 이름은 안 켠 스위치다(D-377).
    "OPS_BACKUP_DIR": "/backup",
    "OPS_BACKUP_VOLUME": "gx_backup_vault_e",

    # 백업 보존 **14일**.
    "OPS_BACKUP_RETENTION_DAYS": 14,


    # 복구 시험 **주 1회 자동** (`ops_restore` dry-run → RTO 실측 기록).
    "OPS_RESTORE_DRILL_ENABLED": True,
}


def declarations(environment: str, already_declared) -> dict:
    """이 환경이 **선언한** 값들. 선언이 아닌 환경에서는 빈 표다.

    Args:
        environment: `settings.GUARDIANX_ENVIRONMENT`.
        already_declared: 환경변수 등으로 **이미 정해진 이름들**. 그쪽이 이긴다 —
            시드가 운영자의 선언을 덮으면 그 순간 이것은 기본값이 된다.

    Returns:
        `{설정 이름: 값}`. **운영(production)에서는 언제나 `{}`** 이다.
    """
    if environment not in DECLARED_ENVIRONMENTS:
        return {}
    taken = set(already_declared or ())
    return {name: value for name, value in SEED.items() if name not in taken}
