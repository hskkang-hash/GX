# 턴 L · 조율자 20분 [영실 실측 · 2026-09-07]

## ① 계정 세트 — **4/4 있음 · 심을 것 0** (지시서 §P-98 정정)

지시서는 「U1 `fire_user`(1명 있음 — 대장 935행)」이라 적었다. **`fire_user` 는 계정이 아니라 역할 코드다.**
계정 이름으로 `fire_user` 를 찾으면 0건이 나오고, 그것을 「없다」로 읽으면 없는 계정을 심게 된다.

명령:
```
docker exec gx-shell sh -c 'cd /app && DJANGO_SETTINGS_MODULE=config.settings python -c "…U.objects.filter(username__startswith=\"gxseed\")…"'
```
결과 [실측]:

| U | 계정 | id | 역할 코드 | 로그인 |
|---|---|---|---|---|
| U1 | `gxseed_u1_operator` | 110 | `fire_user` | **200** |
| U2 | `gxseed_u2_manager` | 108 | `fire_admin` | **200** |
| U4 | `gxseed_u4_official` | 109 | `view_only_-_anyang` | **200** |
| U5 | `gxseed_u5_sysop` | 115 | `admin` | **200** |
| — | `gxprobe_e2e` | 105 | **`[]` (역할 0)** | — |
| — | `admin` / `anyang` | 2 / 32 | `superuser` / `user` | — |

- `fire_user` 계정 조회 → **0건**. `gxseed_u1_operator` 조회 → 1건. 「없다」의 정체는 **이름 자리에 역할 코드를 적은 것**이었다. (P-97 사례 1 · 회수)
- U5 는 `anyang/Admin@123` 이 아니라 `gxseed_u5_sysop` 다 — 지시서 추정과 일치(회전 대상 아님).
- 로그인 실증: `POST /api/v1/auth/login` (`end_previous_session:true`) · 컨테이너 `gx-shell` 안에서 `urllib` (컨테이너에 `curl` 없음) · 4/4 **200**.
- **결론: P-98 재촬영의 전제는 이 턴 시작 시점에 이미 충족돼 있었다.** 심는 일 없음.

## ② P-104 ③ 재측 → 차선 P 위임
## ③ P-90′ 운영 탐침 「보내라」 → **없음 · 대기**. 운영계로 이 턴에도 한 패킷도 나가지 않았다.
## ④ `nginx/` 소유 → 차선 E 이관 표기 완료.

## 기준선 [실측 · 차선 착수 전]

| 게이트 | 값 | 색 |
|---|---|---|
| `verify_write_auth` | 관문 15 · writes 0 · 선언 11 · read_only 4 = **분모 30** | 초록(분모 의심) |
| 라이브 라우터 쓰기 메서드 | **377** (POST 234 · PUT 77 · DELETE 64 · PATCH 2) / 전체 705 | — |
| `verify_tenant_scope` | 라우트 705 대조 · 트립와이어 518 (unguarded 346) | 초록(출처 의심) |
| `verify_readiness_scores` | CR 실측 · **FC·PR 회색(셈법 미정)** | 회색 |
| `verify_prod_settings` | **5/5** | 초록 |
| `verify_live_freshness` | 8000 기동 17:55:13 · 커밋 6cf2c19 = HEAD | 초록 |
| `verify_envelope` | 705건 · 계약면 53 · 갈림 0 · 미대조 1(`POST /api/proxy/notam`) | 초록 |
| `verify_screens` | 33/33 (실측 1 · 시드 28 · 모의 4) | 초록(**역할 0 계정**) |

**분모 30 vs 377** — `write_auth` 가 재고 있던 것은 쓰기 면 **전체가 아니라 8.0%** 였다. `receive-from-etri` 가 그 밖에 있었던 이유.

## 자진 신고 — 이 문서를 쓰는 동안 만든 거짓 초록 1
기준선을 뜰 때 `python scripts/X.py 2>&1 | tail -18; echo "[exit=$?]"` 로 적었다. `$?` 는 파이프의 **마지막 명령(`tail`)** 의 값이라 **전부 0** 이 나왔다. `verify_readiness_scores` 는 스스로 「회색(exit 2)」라고 적고 있었는데 내 줄은 `exit=0` 이었다. 여덟 줄 중 여덟이 무의미했다.
→ 이후 전부 `${PIPESTATUS[0]}`. 차선 여섯에 같은 경고를 브리핑에 넣었다. **영실 오판 1(자진).**

---

# 병합 (STEP 5) [영실 실측 · 2026-09-07 19:1x~19:4x]

## 병합에서만 드러난 것 넷 — 어느 차선도 혼자서는 못 본 것

### ① 경로 어긋남이 헤드라인 수를 깎고 있었다 (FC)
차선 Q 의 FC 술어는 `evidence/P-98/`(판정 **번호**)를 뒤졌고 → 0장.
차선 C 는 같은 시각 화면 색인의 **정본 자리**에 32장을 내고 있었다.
→ `P-98` 은 저장 경로가 아니다. 근거 경로를 정본으로 고치자 PR 항목 8 이 0 → 0.5, **PR 50.0 → 53.3**.
**원칙 등재: 판정 번호는 저장 경로가 아니다.** P-93 의 병렬 판(版).

### ② `verify_prod_settings` 6번째 항목 — 설정은 섰는데 판정기가 다섯 줄 하드코딩이었다
차선 B 가 `SAFE_ERROR_BODY` + 미들웨어를 세웠으나 게이트의 `PROBE`·`judge()` 가 다섯 줄
고정이라 6이 되지 않았다. 조율자가 여섯째를 달았다 — **스위치와 그물을 함께** 본다
(하나만 재면 「켰다」가 「막힌다」로 읽힌다). 변이 둘 다 잡힘 · 자기시험 변이 **6/6** · **6/6 통과**.

### ③ `envelope` 초록 → 빨강 — 회귀가 아니라 **분모가 늘어서 드러난 것**
화면이 부르는 고유 호출 **37 → 43**(역할 계정이 6개 더 부른다) · 봉투 갈림 **1건 `GET /api/roles/`**.
차선 S 가 찾은 끝-슬래시 결함(`/api/roles` 로 POST → `APPEND_SLASH` → 500, 관문 있는 **29자리**
오측)과 **같은 자리**다. 두 차선이 다른 문으로 같은 방에 들어왔다.

### ④ ★ MinIO — 「저장소는 200」과 「앱은 503」이 같은 순간에 참이었다
`/api/media-data` · `/api/dsm/events/{id}/snapshot` 이 **503**. 넘겨짚지 않고 셋을 갈랐다:

| 잰 것 | 결과 |
|---|---|
| MinIO 살아 있나 | `minio:9000/minio/health/live` → **200** · 버킷 `guardianx-dev` 객체 **21개** |
| 끝점만 고치면 되나 | 격리 서버 8040 을 `MINIO_ENDPOINT=minio:9000` 로 띄움 → **여전히 503** (가설 기각) |
| 그럼 무엇인가 | **앱이 든 자격이 자리표다** — `ACCESS_KEY` 5자 · `SECRET_KEY` 5자 · **둘의 sha256 이 같다**(= 같은 문자열). 게이트가 든 root 자격은 7자/28자 · 다르다 |

**`verify_minio.py` 의 「[입력] 저장소 health 200 · 객체 21」은 참이지만 앱에 관한 말이 아니다** —
그 줄은 호스트 `.env` 의 **root 자격**으로 잰 것이고, 앱은 그 자격을 가진 적이 없다.
판정기가 읽는 출처 ≠ 앱이 쓰는 출처, 이 턴 **네 번째** 사례(tenant_scope · write_auth · screens · minio).
※ 게이트 자체는 앱 라우트를 따로 때려 ✗ 를 냈다 — 눈이 먼 것은 판정이 아니라 **[입력] 줄**이다.

## STEP 6 실사용 여정 — **역할 계정으로 걸으니 빨강이 됐다**
`walk_scenarios.py` 의 기본 사용자는 `GX_ROUTE_USER` = `gxprobe_e2e` = **역할 0 계정**이다.
화면 33장과 **같은 결함이 걷기에도 있었다.**

U1 `gxseed_u1_operator`(관제요원)로 재주행 → 증거 `walk_U1_20260907_193712.json`:
- **완주 3/3** (S1 목록 · S2 대시보드 · S3 단일 초점) · 세션 정상 종료(logout 200)
- **판정 실패(exit 1)** — 분류되지 않은 콘솔 오류 **3건**, 전부 `snapshot` **503**(위 ④)
- 역할 0 계정의 걷기는 **콘솔 오류 0** 이었다 — 스냅샷을 부르는 자리까지 못 갔기 때문이다

**즉 「걷기 3/3 · 콘솔 0」은 완주의 증거가 아니라 도달 못 함의 증거였다.**

## 게이트 15 [실측 · 병합 뒤]
초록 5 (`live_freshness` · `prod_settings` **6/6** · `error_body` **신설·초록** · `tenant_scope` · `screens` · `secret_scan`)
회색 2 (`write_auth` — 회색 8자리 · `bundle_hash` — 3002 가 컨테이너 안이라 호스트에서 못 읽음)
빨강 6 (`envelope` 1건 · `route_alive` 503×2 · `contract_route_reach` 503×1 · `front_line_502` 2건 · `dormant` 1건 · `readiness_scores` PRD 자기모순)
→ **「게이트 14 · 빨강 0」은 이번에도 거짓이었다.**
