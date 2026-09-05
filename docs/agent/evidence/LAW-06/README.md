# LAW-06 — AI기본법 34조 5의무 내장 (자리표 + 고지 문구)

- 차선 L (법·영역 ⑧) · 2026-09-05 (기계) · 턴 D
- 판정: **부분 닫힘 — 자리표와 고지는 섰고, 문서화 의무의 한 칸은 「없다」로 적혀 있다**

## 1. 무엇을 만들었나

| 자리 | 파일 | 하는 일 |
|---|---|---|
| 자리표 | `backend/apps/dsm/ai_act.py` | 다섯 의무 × 「어디에 사는가」 · **import 로 실재를 잰다** |
| 고지 정본 | `backend/common/ai_act_notice.py` | 문장 **한 곳**. 커널도 App 도 여기서 읽는다 |
| 알림 본문 | `backend/kernels/k2_notify/services.py::_subject_and_body` | 본문 꼬리에 고지 한 줄 |
| 첫 화면 | `frontend/src/features/dsm/components/AutoAnalysisNotice.tsx` | 「자동 분석 안내」 상자 |
| 첫 화면 부착 | `frontend/src/features/dsm/pages/ControlDashboard.tsx` | 관제 대시보드 맨 위 |
| HTTP | `GET /api/dsm/law/ai-act/duties` | 자리표를 화면·검수가 읽는 자리 |

문장은 제품 언어 사전(`GX-COPY_v1.md` §5 턴 D)에 조율자가 넣어 둔 그대로다:
「자동 분석 안내」 / 「이 알림은 자동 분석 결과이며, 관제요원이 최종 확인합니다.」

## 2. 다섯 칸 — 실측 결과

컨테이너에서 `duty_table()` 을 직접 부른 출력:

```
duties 5   duties_without_any_anchor []   duties_with_gaps ['문서화']
```

| 의무 | 어디에 사는가 | 실재 |
|---|---|---|
| 위험관리 | 알림 예산 · 월간 오탐률 · 임계값 | 3/3 |
| 설명가능성 | 등급 판정 규칙 · 규칙 표 | 2/2 |
| 이용자보호 | 원본 무반출 잠금 · 스냅샷 소인 · 열람·삭제 청구 접수 | 3/3 |
| 사람감독 | 진위 판정 · 대응 단계 · 고지 문구 | 3/3 |
| 문서화 | 설정 전건 감사 · 증거 해시 체인 · **AI 모델 기술문서** | **2/3 — 셋째가 없다** |

★ **빈칸과 「없음」은 다르다.** 없는 칸을 지우지 않고 `present=false` + 사유로 남긴다.
[실측 2026-09-05] `grep -rl "모델 카드" docs/ backend/` = 1건이고 그 1건은 VLM 후보
조사 메모(`docs/agent/evidence/PERF-07/...`)이지 **우리 모델의 문서가 아니다.**

## 3. 실행한 명령과 출력 원문

```
$ docker exec gx-shell sh -c 'cd /app && DJANGO_SETTINGS_MODULE=config.settings \
    DB_TEST_NAME=test_gx_l python -m pytest tests/test_l_ai_act.py -q \
    --nomigrations -p no:randomly --tb=short 2>/dev/null'
10 passed, 1 skipped, 4 warnings in 8.76s
```

건너뛴 1건은 **화면 대조**다 — 이 컨테이너에 frontend 가 마운트돼 있지 않다:

```
$ docker inspect gx-shell --format '{{range .Mounts}}{{.Source}} -> {{.Destination}}{{println}}{{end}}'
C:/GuardianX/guardianx-source/backend -> /app
C:/GuardianX/guardianx-source/docs    -> /docs
C:/GuardianX/guardianx-source/backend -> /repo/backend (ro)
C:/GuardianX/guardianx-source/scripts -> /repo/scripts (ro)
```

**회색을 초록으로 적지 않았다.** 대신 같은 대조를 호스트에서 실제로 돌렸고, 출력은 이렇다:

```
component has title : True
component has body  : True
server    has body  : True
dashboard mounts    : True
privacy   mounts    : True
```

알림 본문 쪽은 컨테이너에서 잰다(위 10 passed 에 포함): 이벤트 하나를 만들어
알림 본문 생성 함수를 부르고, 그 결과 문자열에 정본 문장이 들어 있는지 본다.

두 벌 금지도 잰다 — 백엔드 전체에서 그 문장을 가진 파일은 **`ai_act_notice.py` 하나뿐**이다.

## 4. 못 쟀고, 왜

- **로그인 뒤 첫 화면이 사람마다 다르다.** [실측 `frontend/src/App.tsx::RootRedirect`]
  착지 화면은 `home_screen_setting` 으로 사용자마다 정해진다. 그래서 「모든 사람의
  첫 화면」에 붙었다고 말할 수 없다. 붙인 곳은 **DSM 관제 대시보드**와 청구 화면이다.
  전 사용자 공통 자리(예: `PrivateLayout`)는 공용 파일이라 이 차선이 만지지 않았다.
- **고지가 법이 요구하는 수준인가** — 재지 않았다. 조문 대조는 법률대리인의 판정이고,
  이 표는 그 사실을 `legal_review_pending: true` 로 스스로 말한다.
- **다섯 의무의 이름이 조문의 이름과 같은가** — 대장(ga_readiness.yaml LAW-06 제목)이
  적은 이름을 그대로 썼다. 조문에서 직접 옮기지 않았다(법률 조문을 지어내지 않는다).

## 5. 법률 검토 대기

- 다섯 의무 각각의 **충족 수준**. 이 표는 「닿는 자리가 있다」까지만 말한다.
- 고지 문안이 사전 고지 의무를 만족하는지 · 고지가 닿아야 하는 자리가 더 있는지.

## 6. 다음 사람이 확인할 것 3줄

1. 문서화 칸이 아직 「없다」이다 — AI 모델 기술문서(학습 자료·성능·한계)를 만들면
   `apps/dsm/ai_act.py` 의 `apps.dsm.model_card:MODEL_CARD` 자리를 실물로 바꾸고
   `test_l_ai_act.py::test_the_missing_model_card_is_reported_as_missing` 를 함께 고쳐라.
2. gx-shell 에 `frontend` 읽기전용 마운트를 더하면 건너뛴 1건이 **저절로** 재기 시작한다
   (시험은 이미 그 경로를 본다 — 고칠 것이 없다).
3. 고지 문장을 고치려면 `common/ai_act_notice.py` **한 곳**만 고쳐라. 화면 조각과
   사전을 함께 고치지 않으면 시험이 빨개진다 — 그것이 의도다.

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
