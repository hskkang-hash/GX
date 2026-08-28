# -*- coding: utf-8 -*-
"""E2E 3시나리오 (D-291).

여기 있는 시험은 **`--nomigrations` 없이** 돈다. 실 마이그레이션 DB 에서 도는 것이
공통 규약 ① 이고, 그것이 착시 ⑤(D-282 — 재는 자리가 실물인가)의 대응이다.

    docker exec gx-shell sh -c 'cd /app && DJANGO_SETTINGS_MODULE=config.settings \
      PYTHONPATH=/app python -m pytest tests/e2e -q -p no:randomly'

`tests/` 전체를 `--nomigrations` 로 돌리는 빠른 경로는 그대로 두되, **이 폴더만은
느리게 돈다.** 속도용 보조 수단이 정본 판정 환경이 되지 않게 하는 것이 D-282 다.
"""
