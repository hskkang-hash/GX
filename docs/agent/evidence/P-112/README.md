# P-112 — **한 낱말이 74계정을 연다** · 반경 먼저, 회전 나중 [차선 S · 2026-09-10 턴 O]

- AS = gx-shell Django ORM · `check_password` 전수. **로그인은 0회 소모했다.**
- SOURCE = 오늘 내가 직접 센 수. 값은 이 문서 어디에도 없다 — `sha256[:12]` 과 길이뿐이다
  (D-335 규약 ④).

## ① 반경 [실측 2026-09-10]

| | 수 |
|---|---|
| 전체 계정 | **114** |
| 그 한 낱말(`sha256[:12]=e86f78a8a3ca` · 길이 9)을 쓰는 계정 | **74** |
| 그중 활성 | **73** |
| 그중 `is_superuser` | **1** — 이 저장소의 **유일한 superuser `phatlh`** |
| 그중 역할 `superuser` 보유 | 8 (`admin` · `man` · `rin` · `kimchi` · `kimchi1` · `gaion09` · `rin_superuser` · `tuan_superuser`) |
| **그중 게이트가 인증에 쓰는 계정** | **0** |

전수 명세(값 없음): `shared_password_radius.json`

### 게이트 반경 — **하나도 겹치지 않았다**

`.env.gates` 의 비밀번호 넷을 같은 방식(`sha256[:12]`)으로 대조했다:

| 이름 | sha256[:12] | 길이 | 공유 낱말과 같은가 |
|---|---|---|---|
| 공유 낱말 | `e86f78a8a3ca` | 9 | — |
| `GX_ROUTE_PASSWORD` (`gxseed_u4_official`) | `cede203691cd` | 18 | **아니오** |
| `GX_SEED_ROLE_PASSWORD` (`gxseed_u1/u2/u5`) | `cede203691cd` | 18 | **아니오** |
| `GX_PROBE_PASSWORD` (`gxprobe_{s,q,e,c,v}`) | `b6ae237c2c7b` | 18 | **아니오** |
| `GX_ROUTE_PASSWORD_ROLE0` (`gxprobe_e2e`) | `b16434bb44d5` | 26 | **아니오** |

★ `GX_ROUTE_PASSWORD` 와 `GX_SEED_ROLE_PASSWORD` 는 **서로 같은 값**이다
(sha 가 같다) — 그 자체가 다음 사람이 볼 작은 흠이지만, 공유 낱말과는 다르고
이번 회전의 반경 밖이다. 이름을 적어 남긴다.

또한 저장소 전수 검색 결과, 74개 이름 중 **어떤 자동화도(게이트·`capture_screens.py`·
E2E·시드) 인증에 쓰지 않는다.** `anyang` 이 걸린 자리는 역할 코드
`view_only_-_anyang` 문자열이지 계정이 아니다.

## ② 회전 [실측 2026-09-10 · `scripts/rotate_shared_passwords.py --apply`]

```
[P-112] 전체 114 계정 중 **74** 이 이 낱말을 쓴다 (활성 73 · superuser 1)
[P-112] 회전 **74계정** · 새 값 검증 통과 74/74 · 옛 낱말이 남은 계정 **0**
```

- 새 값은 계정마다 **다른 24자 임의 문자열**(대·소·숫자·기호 각 1 이상, `secrets` 로만 생성).
- `last_password_reset = None` 을 함께 세웠다. dj-core 는 이 값을 보고 로그인 응답에
  `must_change_password: True` 를 싣는다 — 다만 그 판정은 **superuser·역할 superuser
  에만** 걸린다(`core/api/v1/auth.py:737`). ⑤ 참조.
- 산출물(값 없음): `rotation_20260910.json` — 계정마다 새 값의 `sha256[:12]` 과 길이만.
- **새 값 원장(유일한 사본, 저장소 밖)**: `C:\GuardianX\_patches\P-112_rotated_20260910.tsv`
  (74줄 · `username<TAB>password`). 잃으면 관리자가 다시 발급해야 한다.

## ③ 게이트 전 → 후 — **안 잠갔다**

`verify_route_alive` (TARGET=`http://localhost:8000` · gx-shell · AS `gxseed_u4_official`):

| | 전 | 후 |
|---|---|---|
| 종료 코드 | **0** | **0** |
| 살아 있는 라우트 | 43 / 43 | **43 / 43** |
| 토큰-익명 응답 차 | 42 / 43 | **42 / 43** |
| 토큰을 들고도 401/403 | 10건 | **10건** |

**한 자리도 안 바뀌었다.** 그리고 회전 뒤 `check_password` 로 다시 대조:
`gxseed_u4_official` · `gxseed_u2_manager` · `gxseed_u5_sysop` · `gxseed_u1_operator` ·
`gxprobe_v` · `gxprobe_e2e` — **여섯 다 여전히 인증된다** (로그인 0회 소모).

`.env.gates` 는 **값을 한 자도 안 고쳤다.** 위 대조와 원장 위치를 적은 주석 블록만 붙였다.

## ④ 아직 남은 자리 — **옛 낱말이 저장소에 글자 그대로 있다**

```
backend/run_be.sh:80   # python manage.py create_default_superuser --username=phatlh … --password=<옛 낱말>
```

주석 처리된 줄이지만 **이력에는 남는다.** 회전으로 그 값은 무력해졌으나 지워야 한다.
`backend/run_be.sh` 는 차선 S 소유가 아니라 **손대지 않았다** — 소유 차선이 지워야 한다.

## ⑤ CPO 정책 — **적기만 한다. 실행하지 않았다**

| # | 정책 | 이 제품의 현재 상태 [실측] | 왜 이번 턴에 실행 안 했나 |
|---|---|---|---|
| 1 | **첫 로그인 강제 변경** | **장치가 없다.** `CoreUser` 에 `must_change_password` 필드가 **없고**(전 필드 목록 확인), 로그인이 그 이름을 응답에 싣는 조건은 `last_password_reset is None` **그리고** superuser·역할 superuser 다. 나머지 계정에는 강제 장치가 없다 | 모델은 dj-core 소유(§0.4). 필드를 못 만든다. 우리 층에서 강제하려면 **새 관문 한 겹**이 필요하고 그건 이 턴의 셋째 우선순위 밖이다 |
| 2 | **흔한 비밀번호 차단 목록 ≥100 + 길이 ≥ 12** | 없다. 회전한 74계정의 새 값은 **24자**라 하한을 이미 넘는다 | 검증기는 회원가입·비밀번호 변경 경로(둘 다 dj-core)에 걸려야 한다. 우리 층 관문으로 본문을 검사하는 설계가 필요하다 |
| 3 | **superuser 를 일상 계정에서 분리** | `is_superuser` 는 **1계정(`phatlh`)** 뿐이지만 역할 `superuser` 보유가 **13계정**이다. 그중 8이 공유 낱말을 쓰고 있었다 | 계정 생성·역할 재배치는 운영 결정이다. 계정을 만들지도 지우지도 않는다 |
| 4 | **휴면 계정 잠금(삭제 아님)** | CPO 문안의 「40」과 **오늘 수가 다르다**: `is_active=False` 는 **1**, 로그인 이력 없음 **20**, 마지막 로그인 90일 초과 **84** → 휴면(둘의 합) **104 / 114** | 「40」이 어느 술어의 수인지 모른다(D-280 추정 금지). 술어를 정하는 것이 먼저다. 계정을 지우지 않는다는 원칙만 지켰다 |
| 5 | **5회 실패 후 잠금/지연** | 필드는 **있다**: `failed_login_attempts` · `account_locked_until` · `login_fail_count` · `is_account_lock` · `time_account_lock`. 그것을 **읽어서 막는 코드**는 확인하지 못했다 | 「필드가 있다」는 「막힌다」가 아니다. 실측으로 가르려면 로그인을 5회 태워야 하고(동시 세션 1개 제약), 이 턴에는 그 예산이 없었다. **회색으로 남긴다 — 회색은 초록이 아니다** |

## ⑥ 되돌리기

**없다.** 옛 낱말로 돌아가는 것은 사고로 돌아가는 것이다. 새 값은 ② 의 원장에 있고,
잃으면 관리자가 다시 발급한다.
