# OPS-16 — 이번 달 사용량 (계량 표 · Commercial Readiness 의 뿌리)

- 차선 E (Backend/DB) · 2026-09-05 (기계) · 턴 E
- 판정: **닫힘 후보 — 조율자 확인 필요** (아래 §5 「못 잰 것」과 §6 「조율자 배선」을 함께 읽어라)

## 0. 이 절이 있는 이유 — [실측]

턴 D 까지 **계량 자리가 0건**이었다. 가격표를 쓸 수는 있어도 **청구할 수는 없었다** —
「이번 달에 얼마나 썼나」에 답할 자리가 제품 안에 없었기 때문이다.

## 1. 무엇을 만들었나

| 자리 | 파일 | 하는 일 |
|---|---|---|
| 세는 손 | `backend/apps/dsm/metering.py` (새 파일) | 다섯 수를 **읽기 전용**으로 센다 |
| HTTP | `backend/apps/dsm/law_api.py` `GET /api/dsm/metering` · `/metering/series` · `/metering/csv` | 라우트 셋 (컨트롤러 기존 것 · `urls.py` **한 줄도 안 고쳤다**) |
| 화면 | `frontend/src/features/dsm/pages/Metering.tsx` | 자리표(「준비 중입니다」)를 채웠다 |
| 상수 | `frontend/src/features/dsm/api.ts` | **끝에 `dsmMeteringEndpoint` 만 추가** · 기존 줄 무수정 |
| 시험 | `backend/tests/test_be_metering.py` (새 파일) | 21건 |

다섯 칸 — **낱말은 `docs/design/GX-COPY_v1.md` §5 그대로다**:
카메라 대수 · 쓰는 사람 수 · 이벤트 수 · 보낸 알림 수 · 저장 용량 (+「표 내려받기」).

## 2. 다섯 수를 **어디서** 세나 — 정의가 응답에 함께 나간다

| 칸 | 표 | 정의 (응답 `definitions` 에 그대로 실린다) |
|---|---|---|
| 카메라 대수 | `stream_monitors.StreamMonitor` | 그 달 **끝 시점**에 등록되어 있던 카메라 (지운 것 제외) |
| 쓰는 사람 수 | `user.CoreUser` × `userprofilelink.group` | 살아 있는 로그인 계정 (비활성·지운 계정 제외) |
| 이벤트 수 | `stream_monitors.DetectionEvent` | 그 달에 **발생한**(`occurred_at`) 탐지 이벤트 |
| 보낸 알림 수 | `stream_monitors.DeliveryRecord` | 그 달에 **실제로 보낸**(`succeeded=True`·`sent_at`) 알림 |
| 저장 용량 | `file_management.UserMediaFile` | 그 달 끝 시점 보유 바이트 (`file_size` 합계) |

★ **저장 용량을 객체저장소에서 세지 않는 이유** — 두 가지다.
㉠ 객체 이름 앞머리가 `group.code` 라 테넌트 몫만 재려면 **버킷 전체를 나열**해야 하고,
그러면 화면 한 장이 저장소 전체를 훑는다. ㉡ 이 환경의 저장소는 `minio.invalid` 라
아예 못 닿는다 — 청구서의 수가 저장소의 생사에 매달리면 **저장소가 죽은 달은 청구를 못 한다.**
MinIO 업로드 경로가 `UserMediaFile(file_size, group)` 행을 함께 쓴다
[실측 `stream_monitors/utils/minio_client.py:253`]. 그 장부를 센다.

## 3. 이 절에서 찾은 것 — **소프트 삭제가 청구서에 올라온다**

[실측 2026-09-05 · gx-shell · test DB · `EventClip` 1행]

```
clip.delete()  →  _base_manager 1 · all_objects 1 · deleted_objects 1 · objects 1
```

dj-core `BaseModel` 이 `SafeDeleteModel(SOFT_DELETE_CASCADE)` 인 것은 턴 D 가 찾았다
[실측 `core/base.py:2059`]. 이번에 더 나온 것은 그 다음 줄이다: `objects` 가
`CustomManagerGroup(models.Manager)` 로 덮여 있어 **safedelete 의 매니저가 아니다**
[실측 `core/base.py:2082 · 2393`]. 그래서 **소프트 삭제된 행이 평범한 조회에서도 보인다.**

    → `StreamMonitor.objects.filter(group=...)` 를 그냥 세면 **지운 카메라가 청구서에 오른다.**
      고객은 지웠다고 알고 있고, 우리는 돈을 받는다.

그래서 `metering._alive()` 가 **모든 셈의 유일한 문**이고, `deleted` 칸이 있는 표는
반드시 그 칸이 빈 행만 센다. 시험
`test_a_soft_deleted_camera_is_not_billed` 가 그것을 잰다 — 지우기 전 N, 지운 뒤 N-1.

## 4. 실행한 명령과 출력 원문

```
$ docker exec gx-shell sh -c 'cd /app && DJANGO_SETTINGS_MODULE=config.settings \
    DB_TEST_NAME=test_gx_be python -m pytest tests/test_be_metering.py -q \
    --nomigrations -p no:randomly --tb=short 2>/dev/null'
21 passed, 34 warnings in 13.69s
```

개발 DB 실측 — **테넌트 다섯의 이번 달 사용량**(읽기 전용 확인 포함):

```
[2026-09] ETRI-Group    :: 카메라 대수 5  · 쓰는 사람 수 23 · 이벤트 수 24 · 보낸 알림 수 120 · 저장 용량 1,493,917,814
[2026-09] Group Default :: 카메라 대수 0  · 쓰는 사람 수 4  · 이벤트 수 0  · 보낸 알림 수 0   · 저장 용량 793,418
[2026-09] Anyang        :: 카메라 대수 9  · 쓰는 사람 수 25 · 이벤트 수 0  · 보낸 알림 수 0   · 저장 용량 379,668,206
[2026-09] Gaion         :: 카메라 대수 15 · 쓰는 사람 수 15 · 이벤트 수 0  · 보낸 알림 수 0   · 저장 용량 2,122,401,540
[2026-09] Thailand      :: 카메라 대수 0  · 쓰는 사람 수 8  · 이벤트 수 0  · 보낸 알림 수 0   · 저장 용량 169,389,509

--- 표 내려받기 (한 테넌트 · 3개월) ---
달,카메라 대수,쓰는 사람 수,이벤트 수,보낸 알림 수,저장 용량
2026-09,0,8,0,0,169389509
2026-08,0,8,0,0,169389509
2026-07,0,8,0,0,169389509

읽기 전용 확인 — 행 수 before/after:
  {'DetectionEvent': 24, 'DeliveryRecord': 120, 'AuditLogs': 3063}
  {'DetectionEvent': 24, 'DeliveryRecord': 120, 'AuditLogs': 3063}   같은가: True
```

라우트 대장 (699 → **705** · +6, 그중 계량 셋):

```
/api/dsm/metering             GET   scope=required  authn=JwtOrInboundKey
/api/dsm/metering/series      GET   scope=required  authn=JwtOrInboundKey
/api/dsm/metering/csv         GET   scope=required  authn=JwtOrInboundKey
```

게이트:

```
$ python scripts/verify_ui_copy.py        → 통과 (41개 화면 파일 · 잔여 0건)
$ python scripts/verify_ui_secrets.py     → 통과 (795개 프런트 파일 · 렌더 문자열 0건)
$ ... verify_post_arg_style.py            → 통과 (POST 16건 · NOARG 2 · QUERY 14)
$ ... verify_layers.py                    → 통과 (58개 파일 · 계층 위반 0건)
```

### ★ 프런트 검사에서 찾은 것 — **`tsc -p tsconfig.json` 은 아무것도 안 본다**

처음 돌린 것은 이것이었고 **exit 0** 이었다:

```
$ docker exec gx-fe-build ./node_modules/.bin/tsc --noEmit -p tsconfig.json
TSC_EXIT=0
```

그런데 `frontend/tsconfig.json` 은 이렇다 [실측]:

```json
{ "files": [], "references": [{ "path": "./tsconfig.app.json" }, …] }
```

`files` 가 비어 있고 참조만 있는 프로젝트를 `--build` 없이 `-p` 로 돌리면 **검사 대상이
0개**다. 그 exit 0 은 「형이 맞다」가 아니라 **「아무것도 안 봤다」**이다 —
D-341 착시 ⑦·P-59 와 같은 모양의 거짓 초록이다.

실제로 그 순간 `Metering.tsx` 에는 **JSX 파싱 오류**가 있었다(`map(…) => (` 안쪽 첫 줄에
`{/* 주석 */}` 을 두어 형제 노드가 둘이 됐다). `tsc -p tsconfig.json` 은 초록이었고,
**eslint 가 `Parsing error: ')' expected` 로 잡았다.** 고쳤다.

다시 잰 수 — **본 프로젝트로**:

```
$ docker exec gx-fe-build ./node_modules/.bin/tsc --noEmit -p tsconfig.app.json
(전체 3,229줄의 오류 — App.tsx · rj-core · antd 등 **이 차선 이전부터 있던 것**)
$ … | grep 'features/dsm/(pages/Metering|api)'   → **0건**
```

즉 이 저장소는 **형 검사도 lint 도 게이트가 아니다**(이웃 `CameraAddress.tsx` 도
prettier 18건으로 빨갛다 · `api.ts` 의 기존 줄도 4건). 빌드는 vite(esbuild)라 형을 안 본다.
→ **보고 사항**: 「프런트 빌드 exit 0」은 형이 맞다는 뜻이 아니다. 새 화면은
`tsc -p tsconfig.app.json | grep <내 파일>` 로 **자기 파일만** 재는 것이 지금 가능한 최선이다.

## 5. 못 쟀고, 왜

- **브라우저에서 이 화면이 뜨는 것을 본 적은 없다.** 이번 턴 라이브 접속 자리는
  QA/E2E 차선의 것이고(동시 접속 1개), 이 차선은 브라우저를 열지 않았다.
  대신 **문을 두드려** 200 과 다섯 칸을 쟀다(`MeteringDoorIsGuardedTest`) — 그것이
  D-378(라우트가 질의 인자를 만드는 순간의 500)을 잡는 자리다.
  **화면 캡처는 아직 없다 — 캡처 없이 「화면이 선다」로 적지 않는다.**
- **`gx-fe-build` 컨테이너의 사본이 낡아 있었다** [실측 — `/app/.../Metering.tsx` 가
  자리표 그대로였다]. 턴 D 의 「영실 거짓 초록 1」과 **같은 자리**다. 형변환 검사를
  돌리려고 바뀐 두 파일만 `docker cp` 로 넣고 `tsc --noEmit` 을 돌렸다(exit 0).
  ⚠ **그 컨테이너의 나머지 사본은 여전히 낡았다** — 실제 빌드 전에 재생성이 필요하다
  (P-59 · RUNBOOK).
- **테넌트별 가격 적용** — 없다. 이 절은 **세는 것**까지다. 단가·청구서 발행은 다음 절이다.
- **「쓰는 사람 수」를 「그 달에 로그인한 사람」으로 세지 않았다.** `last_login` 은
  마지막 한 번만 남는 칸이라 지난 달을 다시 세면 수가 달라진다 — **다시 재면
  달라지는 수로 청구서를 쓸 수 없다.** 정의를 응답에 실어 그 선택을 드러냈다.

## 6. 조율자 배선 필요

- **없다.** 경로 `/dsm/metering` 은 이미 등록돼 있고(`routes.ts` · 조율자), 컨트롤러는
  기존 `DsmLawAPI` 에 붙였으므로 **`urls.py` 는 한 줄도 안 고쳤다.**
- 다만 **소유 목록 밖 파일 하나**: `backend/tests/test_f05_event_api.py` 의
  `EVENT_ENTRY_SURFACE` 에 계량 셋(+파기 셋)을 사유와 함께 등재했다. F-05 진입면 잠금이
  47 != 53 으로 멈춰 세웠고, **그것이 그 시험의 값이다** — 안 적으면 새 문이 대장의
  눈 밖이 된다. 자세한 것은 `evidence/LAW-02a/P-57_파기.md` §4.
- 확인만: 병합 뒤 `gx-fe-build` 재생성(P-59) 없이 낸 빌드 초록은 초록이 아니다.

## 7. 다음 사람이 확인할 것 3줄

1. **이 화면은 아무것도 만들지 않는다.** 계량이 이벤트를 하나라도 만들면 그 수로
   청구하게 된다 — `test_reading_usage_creates_no_rows` 가 그것을 지킨다. 지우지 말 것.
2. 새 칸을 더할 때는 **정의를 `definitions` 에 함께** 넣어라. 정의 없는 수는 고객이
   다시 셀 수 없고, 다시 못 세는 수는 다툼이 된다.
3. 못 잰 칸은 `value=None` · `state="unknown"` 이다. **0으로 바꾸지 마라** —
   그 순간 「못 쟀다」가 「안 썼다」가 되고, 그 달의 청구가 조용히 0원이 된다.
