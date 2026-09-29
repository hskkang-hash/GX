# P-394 — U6 카드 진행률 문 권한 (턴 AN · 2026-09-29 · 조율자 E)

| 항목 | 값 |
|---|---|
| 원인 | 예비 계정 `gxseed_u5_newop` 역할 = `fire_user`(→ U1 버킷). `PERSONA_VIEWERS["U6"] == ("U5",)` → `persona=U6` 403(not_yours) |
| 고침 | 역할 행 `admin`(Role id 4 · 본계정 `gxseed_u5_sysop` 과 같은 행) **더함**. `fire_user` 는 그대로 |
| 전 → 뒤 | `['fire_user']` → `['fire_user', 'admin']` · `bucket_of` U1 → **U5** · `resolve_bucket(U5, U6)` = `('U6', '')` |
| 되돌리기 한 칸 | `CoreUser.objects.get(username='gxseed_u5_newop').roles.remove(4)` |
| 확인 | `python scripts/verify_onboarding_walk.py --api http://localhost:8500` → U1 3/3 · U2 1/3 · U3 3/3 · U4 1/1 · U5 3/6 · **U6 3/4** · 「6개 버킷 다 쟀다」 = **카드 6/6** |
| 시험 | `backend/tests/test_p394_u6_reserve_bucket.py`(3) |
| 코드 변경 | 0 — 재세움 도구(`seed_*`)는 이 계정의 역할을 건드리지 않는다(grep) |
