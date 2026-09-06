#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""P-67 — **개발·스테이징의 선언을 그 자리에 심는다** (2026-09-06 · 차선 E).

    세종 판정 P-67: 「개발·스테이징 선언(세종 · 이 문서로 집행): 감사 로그 보존
    **365일** · 스냅샷·구간 참조 30일 · 백업 매일 03:00 · 목적지 별도 볼륨 `/backup` ·
    백업 보존 14일 · 복구 시험 주 1회 자동.」

왜 스크립트가 따로 필요한가 — **설정에 적는 것으로는 뜻이 안 생긴다**
--------------------------------------------------------------------
선언 여섯 중 다섯은 `backend/config/retention_seed.py` 가 `settings` 로 세운다.
**감사 로그 보존 365일 하나만** 그럴 수 없다. 실제로 지우는 것은 dj-core
`core/logger/tasks.py::purge_old_audit_logs` 이고, 그 함수는

    get_config_value_by_path("System", "security.audit_log_retention_days", 90)

**이 자리 하나만** 읽는다. 우리는 그 함수를 못 고친다(§0.4 · dj-core 읽기만).
그러니 `settings.AUDIT_LOG_RETENTION_DAYS = 365` 라고 적어 두면 이렇게 된다:

    우리 층 판정 : 「365일로 선언됐다 — 돌려도 된다」
    실제 삭제    : **90일 기준 하드 삭제** (아무도 정하지 않은 수)

「선언한 수」와 「지우는 수」가 갈리는 그 상태가 D-369 다. 그래서 값을 **그 자리에
심는다.** 심기 전에는 `common/ops_tasks.py::audit_retention_declared_days()` 가
`None` 을 내고 파기는 **한 번도 안 불린다** — 그것이 옳은 정지다.

★ 무엇을 쓰고 어떻게 되돌리는가 — **하기 전에 적는다** (⚠ 지시 규약)
--------------------------------------------------------------------
  쓰는 것 : `AdminConfig(name="System")` 행의 `settings["security"]
            ["audit_log_retention_days"]` **한 칸.** 다른 칸은 읽지도 쓰지도 않는다.
  안 쓰는 것: 그 행의 나머지 전부 · 다른 `AdminConfig` 행 · 다른 어떤 표도.
  덮어쓰지 않는다: 그 칸에 **이미 값이 있으면 거부**한다(exit 1). 고객이 U5 에서
            정한 값을 우리가 덮는 것은 선언을 기본값으로 되돌리는 일이다.
  되돌리는 법: `--unseed` 로 그 칸만 지운다(다른 칸은 그대로).

★ 개발·스테이징에서만 심는다
----------------------------
`settings.GUARDIANX_ENVIRONMENT` 가 `config/retention_seed.DECLARED_ENVIRONMENTS`
안에 있을 때만 돈다. 운영에서는 **거부**한다 — 운영 값은 고객이 정한다.

    docker exec -e DJANGO_SETTINGS_MODULE=config.settings gx-shell \
        python /repo/scripts/seed_retention_declaration.py            # 재기만 한다
    docker exec -e DJANGO_SETTINGS_MODULE=config.settings gx-shell \
        python /repo/scripts/seed_retention_declaration.py --apply    # 심는다
    python scripts/seed_retention_declaration.py --self-test          # Django 없이

종료 코드: 0 뜻대로 됐다 · 1 거부했다(이미 값이 있다 · 운영이다) · 2 **못 쟀다**
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, "/app")
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

EXIT_OK, EXIT_FAIL, EXIT_UNDECIDABLE = 0, 1, 2

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, OSError):
    pass

#: dj-core 가 읽는 자리. **두 벌로 적지 않는다** — `ops_tasks` 와 같은 상수를 쓴다.
CONFIG_NAME = "System"
CONFIG_PATH = ("security", "audit_log_retention_days")

TAG = "[P-67]"


def judge(before, declared_env: bool, seed_value) -> list:
    """심어도 되는가. `(이름, 통과, 사유)` 셋. **순수 함수다** (D-277)."""
    out = []
    out.append(("개발·스테이징인가", bool(declared_env),
                "선언 환경이다" if declared_env else
                "**운영이다** — 운영 값은 고객이 U5 에서 선언한다. 심지 않는다"))
    out.append(("심을 값이 있는가", seed_value is not None,
                f"{seed_value}일" if seed_value is not None else
                "`config/retention_seed.py` 에 심을 값이 없다"))
    out.append(("그 자리가 비었는가", before is None,
                "비었다 — 심을 수 있다" if before is None else
                f"이미 {before!r} 이 있다 — **덮지 않는다.** 남의 선언이다"))
    return out


def self_test() -> int:
    bad = []
    if [ok for _, ok, _ in judge(None, True, 365)] != [True, True, True]:
        bad.append("정상 갈래가 초록이 아니다")
    if [ok for _, ok, _ in judge(None, False, 365)] != [False, True, True]:
        bad.append("운영 갈래를 거부하지 못한다")
    if [ok for _, ok, _ in judge(90, True, 365)] != [True, True, False]:
        bad.append("이미 값이 있는 자리를 덮으려 한다")
    if [ok for _, ok, _ in judge(None, True, None)] != [True, False, True]:
        bad.append("심을 값이 없는데 심으려 한다")
    if bad:
        print(f"{TAG} 자기시험 실패 — 판정기를 먼저 의심한다 (D-350):")
        for b in bad:
            print("    " + b)
        return EXIT_FAIL
    print(f"{TAG} 자기시험 통과 — 정상 1 · 음성 3")
    return EXIT_OK


def main() -> int:
    ap = argparse.ArgumentParser(
        description="P-67 개발·스테이징 감사 로그 보존 선언을 그 자리에 심는다")
    ap.add_argument("--apply", action="store_true",
                    help="실제로 심는다. 없으면 **재기만 한다**")
    ap.add_argument("--unseed", action="store_true",
                    help="심은 칸 하나만 지운다 (되돌리기)")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    if args.self_test:
        return self_test()
    if self_test() != EXIT_OK:
        return EXIT_FAIL

    try:
        import django

        import os
        os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
        django.setup()
        from django.conf import settings

        from config.retention_seed import DECLARED_ENVIRONMENTS
        from core.configuration.models import AdminConfig
    except Exception as exc:                                   # noqa: BLE001
        print(f"{TAG} **판정 불가(exit 2)** — Django 환경을 세우지 못했다: "
              f"{type(exc).__name__}: {exc}")
        print(f"{TAG} 컨테이너 안에서 DJANGO_SETTINGS_MODULE 를 주고 돌린다")
        return EXIT_UNDECIDABLE

    env = getattr(settings, "GUARDIANX_ENVIRONMENT", "")
    declared_env = env in DECLARED_ENVIRONMENTS
    seed_value = getattr(settings, "AUDIT_LOG_RETENTION_DAYS", None)

    # ── 분류 등록부 대조 (D-270 ③) — **쓰기 전에 그 표가 무엇인지 먼저 묻는다** ──
    #   이 스크립트가 쓰는 행은 `configuration.AdminConfig` 하나이고, 그것은
    #   **공용 마스터**다 — `group IS NULL` 이 정상이고 전 테넌트가 같은 값을 읽는다.
    #   그 사실을 여기서 **확인한다**. 확인하지 않으면 이 쓰기는 「테넌트 것을 썼는가
    #   공용 것을 썼는가」를 말할 수 없고, 말할 수 없는 쓰기는 나중에 아무도 못 되짚는다.
    #   ⚠ 등록부에 없으면 **쓰지 않는다.** 「일단 쓰고 나중에 등재」는 그 순서가 거꾸로다.
    import importlib.util as _ilu

    _spec = _ilu.spec_from_file_location(
        "tenant_classification",
        str(Path(__file__).resolve().parents[1] / "backend" / "tests"
            / "tenant_classification.py"))
    _reg = _ilu.module_from_spec(_spec)
    _spec.loader.exec_module(_reg)
    TARGET_MODEL = "configuration.AdminConfig"
    if TARGET_MODEL not in _reg.SHARED_MASTERS:
        print(f"{TAG} **멈춘다** — {TARGET_MODEL} 이 분류 등록부의 공용 마스터가 아니다. "
              f"테넌트 소유일 수 있는 표에 전역 선언을 심으면 그 값이 남의 것이 된다")
        return EXIT_FAIL
    if TARGET_MODEL in getattr(_reg, "TENANT_UNASSIGNED", {}):
        print(f"{TAG} **멈춘다** — {TARGET_MODEL} 이 미배정으로도 등재돼 있다(모순)")
        return EXIT_FAIL
    print(f"{TAG} 분류 대조 — {TARGET_MODEL} = 공용 마스터: "
          f"{_reg.SHARED_MASTERS[TARGET_MODEL]}")

    row = AdminConfig.objects.filter(name=CONFIG_NAME, is_active=True).first()
    if row is None:
        print(f"{TAG} **판정 불가(exit 2)** — `AdminConfig(name={CONFIG_NAME!r})` "
              f"행이 없다. 없는 행을 만들지 않는다 — 그 행은 우리 것이 아니다")
        return EXIT_UNDECIDABLE

    conf = row.settings or {}
    section, key = CONFIG_PATH
    before = (conf.get(section) or {}).get(key)

    print(f"{TAG} [입력] 환경 {env!r} · 심을 값 {seed_value!r} · "
          f"그 자리의 지금 값 {before!r}")

    if args.unseed:
        if before is None:
            print(f"{TAG} 그 자리는 이미 비었다 — 할 일이 없다")
            return EXIT_OK
        block = dict(conf.get(section) or {})
        block.pop(key, None)
        conf = dict(conf)
        if block:
            conf[section] = block
        else:
            conf.pop(section, None)
        row.settings = conf
        row.save(update_fields=["settings"])
        print(f"{TAG} 되돌렸다 — `{section}.{key}` 한 칸을 지웠다 (이전 값 {before!r})")
        return EXIT_OK

    rc = EXIT_OK
    for name, ok, why in judge(before, declared_env, seed_value):
        print(f"{TAG} {'  ' if ok else 'X '}{name:20} {why}")
        if not ok:
            rc = EXIT_FAIL
    if rc != EXIT_OK:
        print(f"{TAG} 심지 않았다 — 위의 X 가 사유다")
        return rc

    if not args.apply:
        print(f"{TAG} **재기만 했다.** 실제로 심으려면 `--apply` 를 준다 — "
              f"`{section}.{key} = {seed_value}` 한 칸만 쓴다")
        return EXIT_OK

    conf = dict(conf)
    conf[section] = dict(conf.get(section) or {})
    conf[section][key] = int(seed_value)
    row.settings = conf
    row.save(update_fields=["settings"])

    # 「썼다」와 「그 자리에서 읽힌다」는 다른 사실이다 — dj-core 의 눈으로 되읽는다.
    from core.configuration.utils import get_config_value_by_path

    readback = get_config_value_by_path(CONFIG_NAME, f"{section}.{key}", None)
    print(f"{TAG} 심었다 — `{section}.{key} = {seed_value}` · "
          f"dj-core 가 읽는 값 {readback!r}")
    if readback is None or int(readback) != int(seed_value):
        print(f"{TAG} **실패** — 썼는데 그 자리에서 읽히지 않는다. "
              f"「썼다」는 성공이 아니다")
        return EXIT_FAIL
    print(f"{TAG} 통과 — 이제 감사 로그 파기가 **선언된 {seed_value}일**로 돈다. "
          f"되돌리려면 `--unseed`")
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
