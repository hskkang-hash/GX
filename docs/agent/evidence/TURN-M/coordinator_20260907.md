# 턴 M · 조율자 20분 [영실 실측 · 2026-09-07 20:0x]

## ① 보험 패치 — 그리고 **첫 패치는 보험이 아니었다**

지시서 첫 일. 80파일이 세상에 한 벌이므로 저장소 밖으로 뜬다.

**1차 (실패)** — `git diff HEAD > …patch`
- 되읽기 검사가 빨강. 두 가지가 섞여 있었다:
  - ⓐ **검사 방향이 틀렸다** — `git apply --check` 는 *현재 나무에 적용*을 시험한다. 이미 적용된 것을 또 적용하려 하니 당연히 실패다. 옳은 검사는 `--reverse`.
  - ⓑ **그리고 패치가 진짜로 불완전했다** — `Binary files … differ` **33줄** · `GIT binary patch` **0줄**. `git diff` 는 기본으로 **바이너리 내용을 담지 않는다.** PNG 33장(역할 0 계정 인수 화면)이 **복원 불가**였다.
- ⓑ 를 ⓐ 가 가릴 뻔했다. 방향만 고쳤으면 「검사 통과」를 받고 **빈 보험**을 들고 갔을 것이다.

**2차 (성립)** — `git diff HEAD --binary`
```
Binary files 줄 0 · GIT binary patch 줄 33 · 6.7M · 115,500줄
git apply --check --reverse → 조용함 (HEAD→현재 를 그대로 담았다)
```

**복원 시험** (회수증과 같은 규율 — 「뜬 것」이 아니라 「되돌아온 것」을 잰다):
깨끗한 `6cf2c19` 사본에 실제로 적용 + 미추적 115건 풀기 →

| 되돌아온 것 | 수 | 원본 |
|---|---|---|
| 역할 계정 PNG | **32** | 32 |
| `P-98/denied/` PNG | **33** | 33 |
| `scripts/verify_error_body.py` | 있음 | 있음 |
| `write_surface.json` routes | **377** (mode `live-router-schema-passing-body`) | 377 |

보험 자리: `C:\GuardianX\_patches\turnL_worktree_20260907_turnL.patch` (+ `.tgz` 미추적 115건 · `_status_` · `_untracked_` 목록). 격리 사본은 지웠다(저장소 밖).

> **원칙 등재: 패치는 뜬 것이 아니라 되돌아온 것으로 잰다.** `--binary` 없는 `git diff` 는
> 바이너리를 「다르다」고만 적는다 — 그 패치는 보험이 아니다. 그리고 **`--check` 는
> `--reverse` 로 건다** (같은 나무에서 정방향 검사는 언제나 실패한다).

## ② P-108 MinIO 자격 출처 — **B갈래(프로세스 env) 확정**

D-379 순서대로 「이미 있음/부분/없음」을 먼저 쟀다.

| 잰 것 | 결과 |
|---|---|
| `settings.py:789~791` | `MINIO_ENDPOINT` 는 기본값 있음 · `ACCESS_KEY`·`SECRET_KEY` 는 **기본값 없음**(W0-0 「미설정 시 즉시 실패」) |
| `settings.py:25` | `environ.Env.read_env(BASE_DIR/".env")` 를 **부른다** |
| `/app/.env` | **존재** · 호스트 `backend/` 마운트 (`C:/GuardianX/guardianx-source/backend:/app`) |
| 그 파일의 MINIO 키 | **전부 MISSING** — 한 줄도 없다 |
| 컨테이너 `Config.Env` | `MINIO_ENDPOINT`·`ACCESS_KEY`·`SECRET_KEY`·`BUCKET_NAME`·`USE_HTTPS` **전부 있음** |
| 실효값 | `ENDPOINT=minio.invalid` · `ACCESS` 5자 · `SECRET` 5자 · **둘의 sha256 이 같다** |

`read_env` 는 `setdefault` 다 → **프로세스 env 가 이긴다.** 파일에 넣어도 안 이긴다.
→ **B갈래: 본 서버를 고치려면 컨테이너 재생성(대표 ③).**

### B갈래가 정한 대로 — 격리 전/후

`gx-shell` 안에 8041 을 띄우고 **끝점·access·secret·bucket 넷을 진짜 값으로** (본 서버 무관):

| 라우트 | 정본 8000 (자리표) | 격리 8041 (진짜 자격) |
|---|---|---|
| `GET /api/media-data/` | **503** `Failed to retrieve media list` | **200** · `data:[{...}]` |
| `GET /api/dsm/events/4798/snapshot` | **503** · JSON 137B | **200** · `image/jpeg` · **37,506B** · 매직 `ffd8ffe0` |

**코드는 맞았다. 자격만 자리표였다.** 8041 은 내렸다.

⚠ **빨강을 회색으로 바꾸지 않는다** — 본 서버(`TARGET=localhost:8000`)를 잰 줄은 **빨강 그대로** 남는다. 위 초록은 `TARGET=격리 8041` 의 사실이고, 그 이름을 함께 적는다.

⚠ 첫 시도에서 **끝점 하나만** 바꿔 봤고 여전히 503 이었다 — 「끝점 값 하나다」 가설은 그때 **기각**됐다. 자격 넷을 함께 넣고서야 200 이 났다. 가설을 재기 전에 적었으면 거짓이 될 뻔했다.

## ③ P-90′ 운영 탐침 「보내라」 — **없음 · 대기(두 턴째)**. 운영계로 이번 턴에도 한 패킷도 나가지 않았다.
## ④ 보고 칸 복구 — 8영역 한 줄 · 502 A/B 수 · 커밋 사유 를 이번 보고에 되살린다(차선 P·E 산출).

## 커밋 판정 [조율자]
- 자격은 재생성 없이는 못 고친다 → 걷기·`route_alive`·`contract_route_reach` 의 **본 서버 빨강은 이 턴에도 남는다**.
- 예외 칸을 열지 않는다 · `--no-verify` 없다 → **커밋 보류 유지**, 보험 패치로 받친다.
- 이 보류의 값은 대표 결정 ③ 하나로 풀린다. 지시서 §4 가 「MinIO 자격 · `/backup` 마운트 · 백업 스위치 · 이미지 재빌드가 한 덩어리」라 적은 것과 같다.

---

# 병합 (STEP 5·6) [영실 실측]

## ① 읽기 면 — **95 → 0** (역할 0 계정)

차선 S 가 잰 95는 **고치기 전** 서버의 수였다. B 가 `RoleGateMiddleware` 를 세우고 재기동한 뒤 같은 탐침을 다시 돌렸다:

| | 전 (S · 20:5x) | 후 (병합 · 21:16 기동 서버) |
|---|---:|---:|
| 역할 0 **빨강** | **95** | **0** |
| 역할 0 초록 | 130 | **327** |
| 역할 0 회색 | 102 | **1** |
| 익명 빨강 | 5 | **5** (안 움직였다) |

회색 102 → 1 이 같이 내려간 것이 중요하다 — 「200 인데 자료인지 모르겠다」가 사라지고 **깨끗한 403** 이 됐다.

허용목록에 **하나** 올렸다: `GET /api/v1/access/role-pending` — CPO 판정이 말한 「그 화면 하나」가 자기를 채우는 유일한 문. `/api/v1/user/me`·`/api/v1/auth/profile` 은 **여전히 빨강**(그 화면은 이 문 하나로 채워진다). 탐침 자기시험의 못을 「비어 있다」에서 **「이 하나뿐이다」**로 옮겼다 — 빈 목록은 늘어나는 것을 못 잡는다.

**익명 빨강 5는 빨강으로 둔다**(기본값 「닫힌 쪽」 · 세종 판정 대기):
`config-management/list-optimized` **16,436 B** · `auth/timezones` **109,309 B** · `auth/groups` 1,685 B · `auth/languages` 466 B · `register-settings` 182 B.

## ② ★ 우리 수정이 게이트 하나를 **눈먼 초록**으로 만들었다 — 그리고 자격 출처에서 고쳤다

P-105 가 서자 `.env.gates` 의 `GX_ROUTE_USER=gxprobe_e2e`(역할 0)를 쓰는 게이트 **여덟**이 동시에 눈이 멀었다. 그 순간을 그대로 남긴다:

```
verify_route_alive --user gxprobe_e2e        → rc=0 「43건 전부 살아 있다」
                                               같은 줄: 「토큰을 들고도 401/403 인 자리 43건」
verify_route_alive --user gxseed_u4_official → rc=1 · 죽은 라우트 2건 (media-data 503)
```

**43자리를 하나도 못 들어가고 「전부 살아 있다」를 냈다.** 「관문이 섰다」와 「내가 못 들어갔다」를 한 칸에 넣으면 그 칸은 **언제나 초록**이다.
→ 정본 탐침을 **역할 있는 최소권한 계정**(`gxseed_u4_official` · view_only)으로 옮겼다. admin 으로 옮기지 않은 이유: admin 으로 재면 권한 결함이 안 보인다(P-107). 역할 0 이 필요한 게이트는 제 이름(`GX_READ_SUBJECT_PW`)을 따로 받는다. 사본 `_patches/env.gates.bak_20260907_turnM`.

## ③ 자격 자리표는 **제품이 아니라 잰 대상의 문제였다** — 턴 L 보고 TOP 1 정정

| TARGET | `/api/media-data/` | `snapshot` |
|---|---|---|
| `localhost:8000` — **gx-shell runserver**(정본이라 부르던 것) | 503 | 503 |
| `localhost:8500` — **gx-nginx-e → gx-gunicorn-e**(운영 모양) | **200** | **200 · image/jpeg · 37,511 B · `ffd8ffe0`** |

자리표를 든 것은 `gx-shell` 하나뿐. `gx-gunicorn-e`·`gx-celery-e`·`gx-beat-e` 는 root 자격과 일치한다(차선 E 실측).
**「MinIO 자격이 상용을 막는다」는 제품 사실이 아니었다.** 막고 있던 것은 **모든 게이트가 가진 서버 중 가장 운영과 안 닮은 개발 runserver 를 겨누고 있었다는 것**이다. P-107 이 게이트 하나가 아니라 **게이트 전체의 겨냥**에 적용되어야 한다는 뜻 — 다음 턴 첫 일.

## ④ STEP 6 실사용 여정 — 역할 계정 U1

`walk_U1_20260907_220807.json` · **완주 3/3** · 판정 **실패(exit 1)** · 분류되지 않은 콘솔 오류 **3건 — 전부 `snapshot` 503**(위 ③ 의 그 자리). 턴 L 과 같은 수다: 걷기는 완주하고 사진에서 걸린다.

## ⑤ 게이트 17 [실측 · 병합 뒤]
초록 6 (`live_freshness` · `error_body` · **`gate_header` 신설** · `tenant_scope` · `screens` · `secret_scan`)
회색 1 (`write_auth` — 회색 8자리)
빨강 10 (`prod_settings` ⑦자격형식 · `read_auth` 익명 5 · `feature_reach` 회색 25 · `envelope` · `route_alive` · `readiness_scores` PRD 자기모순 · `ga_readiness` · `contract_route_reach` · `front_line_502` · `dormant`)

## ⑥ 수 [실측 · 2026-09-07 22:0x]
**상용 67.8** (82.2 → −14.4) · **손 안 70.2** (92.7 → −22.5) · 온보딩 60 · **FC 41.7~52.8** · **PR 50.0** · CR 34.4~45.6
8영역 ①**10.3** ②80 ③100 ④77 ⑤71 ⑥92 ⑦89 ⑧60 · 절 141(구현 87 · **미측정 35**)

**내려간 수가 이번 턴의 산출이다.** ① 이 82%(자기신고)에서 10.3%(게이트 실측)로 간 것은 제품이 나빠진 것이 아니라 **25개 절이 그동안 안 재진 채 「구현」으로 세어지고 있었다**는 뜻이다.
