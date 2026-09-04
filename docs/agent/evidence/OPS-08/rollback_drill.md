# OPS-08 — 되돌려 본 기록 (2026-09-04 06:34:14)

**이 파일은 `scripts/ops_rollback_drill.py` 가 실행하며 적었다.**
손으로 옮겨 적은 문장이 아니다 — 아래 rc 는 전부 그 실행의 것이다.

## 0. 무엇을 지우고 어떻게 되살리는가 — **하기 전에 적는다**

지우는 것: 훈련용 DB `e_rollback_check` **하나뿐**이다. 이 실행이 방금 만든 것이고,
다른 차선이 쓰는 `database_guardianx`·`postgres`·`gx-shell` 은 건드리지 않는다.
되살리는 절차: 없다 — **되살릴 것이 없다.** 훈련이 끝나면 사라지는 것이 정상이고,
다시 필요하면 이 스크립트를 한 번 더 돌리면 같은 것이 처음부터 선다.

## 1. 빈 DB 를 만든다

```
psql -c DROP DATABASE IF EXISTS "e_rollback_check"     rc=0
psql -c CREATE DATABASE "e_rollback_check"             rc=0
```

## 2. 매뉴얼 §2-3 대로 세운다 — **세 줄이다**

```
manage.py migrate user                 rc=0
manage.py migrate multilanguage        rc=0
manage.py migrate                      rc=0
manage.py migrate --check              rc=0
```

세운 직후: 표 220개 · stream_monitors 머리 `0027_ops15_camera_pulse`

## 3. 매뉴얼 §5 의 문장을 **친다**

```
manage.py migrate stream_monitors 0019 rc=0
INFO ✅ [BATCH_DELETE] Successfully cleared 1/1 cache entries
INFO 🎯 [MODEL_SPECIFIC] Found 1 keys matching *guardianx:universal:*migration*
INFO 🌍 [SYSTEM_WIDE] Will clear 1 cache entries for model migration (groups: all) - SYSTEM-WIDE invalidation
INFO 📋 [INVALIDATION_PREVIEW] Sample keys to delete (first 3):
INFO    - :1:guardianx:universal:version:migration
INFO ✅ [BATCH_DELETE] Successfully cleared 1/1 cache entries
```

되돌린 뒤: 표 214개 · stream_monitors 머리 `0019_zone`

## 4. 되살린다 — **되돌린 뒤에 다시 설 수 있는가**

```
manage.py migrate stream_monitors      rc=0
INFO ✅ [BATCH_DELETE] Successfully cleared 1/1 cache entries
INFO 🎯 [MODEL_SPECIFIC] Found 1 keys matching *guardianx:universal:*migration*
INFO 🌍 [SYSTEM_WIDE] Will clear 1 cache entries for model migration (groups: all) - SYSTEM-WIDE invalidation
INFO 📋 [INVALIDATION_PREVIEW] Sample keys to delete (first 3):
INFO    - :1:guardianx:universal:version:migration
INFO ✅ [BATCH_DELETE] Successfully cleared 1/1 cache entries
```

다시 민 뒤: 표 220개 · stream_monitors 머리 `0027_ops15_camera_pulse`

훈련 DB `e_rollback_check` 를 지웠다 (rc=0).

## 5. 판정

  OK   ① 세운 직후      0020 의 칸 2/2 개가 있다
  OK   ② 되돌린 뒤      0020 의 칸이 **사라졌다**
  OK   ③ 다시 민 뒤     칸 2/2 개가 **되돌아왔다**
  OK   ④ 0019 눈금    0019 의 표 1/1 개가 남아 있다 — 목표 지점을 지나치지 않았다

걸린 시간 381초 · 판정 **통과**
