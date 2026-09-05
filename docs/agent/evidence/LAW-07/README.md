# LAW-07 — 개인정보 열람·삭제 청구 대응 (접수 → 마스킹본 조회 → 회신 기록)

- 차선 L (법·영역 ⑧) · 2026-09-05 (기계) · 턴 D
- 판정: **닫힘 후보 — 조율자 확인 필요.** 세 걸음이 한 줄로 이어지고 원본은 안 나간다.
  남은 것은 아래 「법률 검토 대기」 둘이다.

## 1. 무엇을 만들었나

| 자리 | 파일 | 하는 일 |
|---|---|---|
| 대장 | `backend/apps/dsm/privacy_request.py` | 접수 · 목록 · 상세 · 마스킹본 조회 · 회신 기록 |
| 마스킹 | 같은 파일 `mask_jpeg()` | **전면 마스킹**(픽셀화 → 흐림 → 축소) + 소인 |
| HTTP | `backend/apps/dsm/law_api.py` | 5개 라우트 (아래 실측) |
| 화면 | `frontend/src/features/dsm/pages/PrivacyRequests.tsx` | 자리표를 채웠다(「준비 중입니다」 사라짐) |

## 2. ★ 모델을 어디에 둘지 — 실측하고 정했다 (지시 요구 사항)

**새 표를 만들지 않았다. 따라서 새 마이그레이션도 없다.** 그 판단의 근거:

1. `apps/dsm` 은 **Django 앱이 아니다** — `INSTALLED_APPS` 에 없고, 그 앱 스스로가
   「모델이 없기 때문에 앱이 아니다」라고 머리말에 적어 두었다
   [실측 `backend/apps/dsm/__init__.py`]. 모델을 두려면 설정을 고쳐야 한다.
2. `stream_monitors` 에 표를 만들면 **공용 자리 둘을 함께** 고쳐야 한다:
   `tests/test_tenant_isolation.py::MODELS`(머지 게이트)와 `tests/tenant_census.py`
   (정본 모수). 이번 턴에 차선 넷이 도는데 그 둘은 여러 차선이 함께 쓰는 파일이다.
3. **이 기록의 성질이 감사다.** 접수·조회·회신은 덧붙기만 하는 이력이고 뒤에서
   조용히 고쳐지면 안 된다. `logger.AuditLogs` 에 쓰면 LAW-08 해시 체인 위에 그대로
   얹힌다. 「새 감사 표를 만들지 않는다」는 `apps/dsm/audit.py` 의 판단과 같다.

   ⚠ 조율자가 경고한 함정(「`--nomigrations` 때문에 모델을 만들어도 시험은 초록이
   난다」)은 **이 절에 해당하지 않는다** — 모델을 만들지 않았기 때문이다.
   `backend/apps/dsm/migrations/` 는 만들지 않았고, `makemigrations` 로 생길 파일도 없다.

   ⚠ **대가**: 감사 보존기간 집행(`ops-audit-purge-daily` · 기본 90일)이 이 청구
   기록도 지운다 → 아래 「법률 검토 대기」.

## 3. ★ 원본은 안 나간다 — 부작위 시험

응답 전체를 재귀로 훑어 **원본을 가리키는 칸 이름과 값이 0건**인지 잰다:

- 금지 칸 이름: `snapshot_path` · `object_key` · `object_path` · `clip_path` · `bucket` · `url`
- 금지 값: `minio://` · `/dsm/` · `s3://` · `.mp4`

★ **양성 대조를 함께 둔다** — 시험 픽스처의 이벤트는 `snapshot_path` 가 실제로
채워져 있다(`minio://dsm/N.jpg`). 그것을 먼저 단언한다: **셀 것이 있는 상태**에서
0건이어야 뜻이 있다. 비어 있었다면 이 시험은 「안 샜다」가 아니라 「샐 것이 없었다」다.

## 4. 실행한 명령과 출력 원문

```
$ docker exec gx-shell sh -c 'cd /app && DJANGO_SETTINGS_MODULE=config.settings \
    DB_TEST_NAME=test_gx_l python -m pytest tests/test_l_privacy_request.py -q \
    --nomigrations -p no:randomly --tb=short 2>/dev/null'
20 passed, 34 warnings in 11.05s
```

라우트 실측(대장 파일을 건드리지 않고 임시 파일로 떴다):

```
$ docker exec gx-shell sh -c 'cd /app && DJANGO_SETTINGS_MODULE=config.settings \
    python /repo/scripts/probe_route_inventory.py /tmp/routes_l.json'
routes 699        (대장은 690건 — 이 턴에 는 만큼 다시 떠야 한다 · 아래 「조율자 배선」)
  GET  /api/dsm/law/privacy-requests                      tenant_scope=required
  POST /api/dsm/law/privacy-requests                      tenant_scope=required
  GET  /api/dsm/law/privacy-requests/{receipt_no}         tenant_scope=required
  GET  /api/dsm/law/privacy-requests/{receipt_no}/masked  tenant_scope=required
  POST /api/dsm/law/privacy-requests/{receipt_no}/reply   tenant_scope=required
  (여덟 건 모두 authn=JwtOrInboundKey · inbound_key=refuses · classification=session_only)
```

화면 문구 대조(호스트):

```
copy: 열람·삭제 청구 True
copy: 청구 접수 True
copy: 접수 번호 True
copy: 마스킹본 보기 True
copy: 원본 영상은 제공되지 않습니다 True
copy: 회신 기록 True
placeholder gone    : True      ← 「준비 중입니다」가 사라졌다
```

```
$ python scripts/verify_ui_copy.py
[COPY] [입력] 37개 화면 파일 (주석 걷어낸 뒤) · 패턴 7종
[COPY] 통과 — 새로 생긴 대장 언어 0건
```

## 5. 무엇을 쟀나

- **한 줄로 이어진다**: 접수(접수 번호 발급) → 상세(회신 0건) → 마스킹본 조회 →
  회신 기록 → 상태가 「회신 완료」로 바뀐다.
- **원본 경로 0건** (위 §3).
- **남의 테넌트**: 목록에 안 보이고, 상세는 「권한 없음」이 아니라 **「없다」**로 답한다
  (권한 없음으로 답하면 그 접수 번호가 존재한다는 사실이 새어 나간다).
  ★ 양성도 함께: 주인은 읽을 수 있다.
- **마스킹이 정보를 실제로 버린다**: 가로줄 무늬 이미지를 넣어 명암 대비가
  150 초과 → 120 미만으로 떨어지는 것을 **바이트로** 잰다. 폭은 320 이하로 줄어든다.
- **연락처는 가려서 나간다**: 응답 어디에도 원문이 없다.
- **회신은 덧붙기만 한다**: 1차·2차가 순서대로 남는다. 빈 회신은 거절된다.
- **사람 없는 호출은 접수할 수 없다**: 파이프라인 스코프는 예외로 막힌다.
- **셋 다 감사에 남는다**: `law07:accept` · `law07:masked_view` · `law07:reply`.

## 6. 못 쟀고, 왜

- **마스킹본 이미지가 실제로 만들어지는 것** — 못 쟀다. 시험 환경에는 원본 객체가
  객체저장소에 없어서 조회 결과가 「마스킹본을 만들지 못했습니다」 + 사유로 온다.
  마스킹 함수 자체는 위 §5 처럼 **바이트로** 쟀다. 실물 객체를 넣고 끝까지 도는 것은
  E2E 자리다.
- **선택적(얼굴만) 마스킹** — **없다.** 제품 사양이 얼굴 인식 특징값을 만들지 않기로
  못박았으므로 얼굴 위치를 찾을 수 없다. 그래서 **이미지 전체**를 가린다.
  `SELECTIVE_MASKING_READY = False` 로 그 부재를 상수로 잠갔고 사유가 응답에 실린다.
  ⚠ 이 화면의 「마스킹본」은 **전면 마스킹**이다 — 청구인이 자기 모습을 확인하는
  용도로는 부족할 수 있다. 그 판단은 법률 검토가 필요하다.
- **삭제 청구의 실제 집행** — 없다. 접수와 회신 기록까지다. 특정인의 영상만 골라
  지우는 것은 얼굴을 찾을 수 있어야 가능하고(위와 같은 부재), 범위를 넓혀 지우면
  **남의 영상까지 지운다.**
- **법정 회신 기한(10일 등)** — 시험이 강제하지 않았다. 기한은 대조 전이고
  (GX-LAW-03 초안이 「[확인 — 법정 기한 대조]」로 남겼다), 없는 기한을 시험이 강제하면
  그 수가 곧 계약처럼 읽힌다.

## 7. 법률 검토 대기

1. **청구 기록의 보존기간.** 지금 이 대장은 감사 표 위에 서 있고, 감사 보존기간
   집행(기본 90일)이 그것도 지운다. 청구 대응 기록을 몇 년 보관해야 하는지는
   법이 정하는 값이지 우리가 정할 값이 아니다. 정해지면 두 갈래다 —
   ㉠ 청구 기록을 정리 대상에서 빼거나 ㉡ 감사 보존기간을 그 값에 맞춘다.
2. **전면 마스킹이 열람 청구의 답으로 충분한가.** (§6)
3. ★ **처리방침 초안에 없는 수집 항목이 하나 생겼다** — 청구인의 **이름과 연락처**.
   `GX-LAW-03` §1 수집 항목 표에 그 줄이 없다 [실측 2026-09-05]. CPO 가 표에 한 줄을
   더해야 방침이 제품과 어긋나지 않는다.

## 8. 다음 사람이 확인할 것 3줄

1. 이 면은 **관리자만** 볼 수 있다(라우트가 403 으로 막는다) — 청구인 이름과 연락처가
   실려 있기 때문이다. 화면을 열어 보려면 관리자 계정으로 로그인하라.
2. `logger.AuditLogs` 의 `logger_name = "guardianx.law07.privacy_request"` 한 줄로
   청구 대장 전건을 뽑을 수 있다. 그 표를 지우는 주기가 무엇을 지우는지 §7-1 을 읽어라.
3. 마스킹본은 **값으로** 실려 나간다(데이터 URI). 바이트 라우트를 새로 내지 마라 —
   이미지 주소가 생기면 그 주소가 화면 밖으로 복사되고, 복사된 주소는 문지기 밖에서 열린다.

## 부록 — 이 턴에 함께 움직인 것 (전 차선 회귀)

```
$ docker exec gx-shell sh -c 'cd /app && DJANGO_SETTINGS_MODULE=config.settings     DB_TEST_NAME=test_gx_l python -m pytest tests --ignore=tests/e2e -q     --nomigrations -p no:randomly --tb=line 2>/dev/null'
992 passed, 3 skipped, 34 warnings in 276.72s (0:04:36)
```

★ 첫 전수 실행은 **2 failed** 였다 — `test_f05_event_api.py::EntrySurfaceIsLockedTest`.
F-05 진입면 잠금이 새 라우트 여덟을 보고 멈춰 세운 것이고, **그것이 그 시험의 값이다.**
여덟 줄을 손으로 등재하는 일이 곧 「진입면을 넓힌다」는 선언이므로, 사유와 함께
`EVENT_ENTRY_SURFACE` 에 더했다. 지시보다 게이트가 위다.

이 차선이 만진 **공용 파일**(내 소유 목록 밖 · 사유와 함께):

| 파일 | 무엇을 | 왜 |
|---|---|---|
| `backend/kernels/k2_notify/services.py` | 알림 본문 꼬리 한 줄 + import | 고지가 닿아야 하는 자리이고, 커널은 App 을 import 할 수 없다 |
| `backend/common/ops_tasks.py` | 주기 태스크 하나 덧붙임 | 감사 정리 옆에 같은 모양으로 선다(지시대로) |
| `backend/config/celery.py` | beat 항목 하나 | 이 줄이 없으면 화면의 「자동으로 지워집니다」가 거짓이 된다 |
| `backend/apps/dsm/legal_notice.py` | `retention_days` 위임 + 낡은 사유 갱신 | 안내판과 삭제가 **같은 수**를 봐야 한다 |
| `backend/tests/test_f05_event_api.py` | 진입면 여덟 줄 등재 | 그 잠금이 요구하는 선언 |
| `scripts/verify_post_arg_style.py` | `API_MODULES` 에 새 컨트롤러 한 줄 | 안 적으면 새 파일이 게이트의 **눈 밖**이다 |
| `frontend/src/features/dsm/api.ts` | 끝에 엔드포인트 상수만 추가 | 기존 줄은 고치지 않았다 |
| `frontend/src/features/dsm/pages/ControlDashboard.tsx` | 고지 조각 부착 2줄 | 고지가 「읽는 자리」에 있어야 한다 |
