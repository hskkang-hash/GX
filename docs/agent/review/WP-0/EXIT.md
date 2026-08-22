<!-- 승인 시 사람이 이 파일 첫 줄에 다음 한 줄을 넣는다. 에이전트는 절대 쓰지 않는다.
APPROVED: 2026-__-__ 강희석
-->
# WP-0 완료검토서 — 미결 정리 (verify-pending 해소 + 정본 동기화)

## ▲ 갱신 재제출 — 2026-08-22 (로컬 기동 성공분 반영 · RESUME_NEXT §5-④)

**이 블록이 최신 판정이다. 아래 §1~§9 는 2026-08-15 원문으로 보존한다.**
근거: `docs/agent/review/LOCAL_BRINGUP_결과.md` · `evidence/LOCAL_BRINGUP/`

### 갱신 판정 — goal 은 **여전히 부분적으로 참**이다. 그러나 이유가 바뀌었다.

**goal**: 떠 있는 verify-pending 을 전부 종결하고(사내망 1회 작업 포함) 정본을 v3.1 로 맞춘다

| | 문장 | 08-15 | **08-22** | 무엇이 바뀌었나 |
|---|---|---|---|---|
| **A** | verify-pending 4건 종결 | 거짓 0/4 | **부분적으로 참 — 2/4** | W0-2 · W0-4 **done**. W0-3 · W2-1 은 남았다 |
| **B** | 정본 v3.1 일치 | 부분적으로 참 | **참** | manifest 복원(D-227)·sha256 폐기(D-228)·v3.7-local 로 정합. `gen_manifest.py` exit 0 |

**"사내망 1회 작업 포함" 이라는 goal 의 전제 자체가 소멸했다.** 사내망은 없어졌고,
그 방문이 풀어 줄 것이라 적었던 5건은 **이 PC 안의 이미지에서 전부 풀렸다.**
즉 A 가 2/4 에 멈춘 것은 **더 이상 환경 때문이 아니다.** 남은 둘은 사람의 판단을 기다린다.

### 티켓별 갱신

| 티켓 | 08-15 | **08-22** | 증명 |
|---|---|---|---|
| W0-2 | verify-pending | **done** | `test_bypass_list_does_not_grow` **ok** · grep 0건 |
| W0-4 | verify-pending | **done** | 빌드 exit 0 · 데모 청크 ON=196/OFF=190 대조 |
| W0-3 | verify-pending | **decision-pending** | 처음 실행됨 — 1 ok / 2 FAIL / 2 ERROR. P-LOCAL-2 · P-LOCAL-3 |
| W2-1 | verify-pending | verify-pending (유지) | dry-run 리포트 확보. 마이그레이션 생성은 승인 대기 |
| W0-10 | done | done (유지) | — |

### §8 "사내망 방문 1회로 전부 풀린다" 는 **사문이다**

그 방문은 오지 않는다. 실제로 무엇으로 풀렸는지로 대체한다:

| §8 항목 | 실제 해소 경로 | 상태 |
|---|---|---|
| dj-core 수령 | `guardianx-backend.tar` 에서 추출 (1.1.6) | **완료** |
| 격리 테스트 실행 | 이미지 site-packages + 스키마 템플릿 test DB | **완료** (결과는 §갱신 티켓별) |
| W2-1 makemigrations | 같은 환경 | **완료 — dry-run 까지** |
| npm install / 프론트 빌드 | `guardianx-frontend.tar` 의 node_modules | **완료** |
| package-lock.json | 같은 이미지에서 회수 (106의존성 일치) | **완료 — 커밋 승인 대기** |

### 자가검증 갱신 — 측정 불가였던 축이 숫자를 얻었다

| 축 | 08-15 | **08-22** |
|---|---|---|
| **안정성** | 측정 불가 (테스트 미실행) | **테스트 12건 실행** — route 9건(8 ok/1 skip) + isolation 3건(1 ok/2 FAIL) + setUpClass 2 ERROR |
| **완결성** | DoD 충족률 4/9 조건 | **WP-0 티켓 5건 중 done 3 · 판단대기 1 · 승인대기 1** |
| **편리성** | 해당 없음 (내부 정비 WP) | 해당 없음 |
| **참신성** | 해당 없음 | 해당 없음 |
| **보안** | 시크릿 스캔 0건 | 0건 유지. **다만 WP 밖에서 운영 실키 53개 발견 → W0-1b 사고 대응** |
| **코드** | 컨벤션 위반 0건 | 0건 유지. **신규 소스 변경 0줄** (이번 실행은 조사·측정뿐) |

### 이번 갱신으로 새로 생긴 사람 판단 사항

`docs/agent/review/LOCAL_BRINGUP_결과.md §6` 의 7건. 그중 이 WP 를 막는 것은 **2건**:
1. **P-LOCAL-2** — 격리 테스트 픽스처(email UNIQUE). 이것 없이는 W0-3 의 5시나리오가 영구 미실행.
2. **W2-1 마이그레이션 생성 승인** — dry-run 은 나왔다. 되돌릴 수 없는 작업이라 승인이 필요하다.

---

**작성** 에이전트 · 2026-08-15 · **착수검토 승인일** *(ENTRY.md 에 `APPROVED:` 줄 없음 — §7-1 참조)*
**정본** tickets v3.1 / 66티켓 / WP 1/9 · **baseline** `4afca2b`
**티켓** W0-2 · W0-3 · W2-1 · W0-4 · W0-10

> **이 WP 는 새 기능이 없다. 이미 쓴 코드를 실제로 실행해 보는 작업이었다.**
> 그래서 판정도 "무엇을 만들었나"가 아니라 **"실행했나"**로 갈린다. 실행하지 못했다.

---

## 1. 판정 — goal 한 문장이 참인가

**goal**: 떠 있는 verify-pending 을 전부 종결하고(사내망 1회 작업 포함) 정본을 v3.1 로 맞춘다

**판정**: ☐ 참 · **☑ 부분적으로 참** · ☐ 거짓

goal 은 ENTRY §1 에서 두 문장으로 쪼개졌다. **한쪽만 참이다.**

| | 문장 | 판정 | 근거 |
|---|---|---|---|
| **A** | verify-pending 4건이 **종결**된다 | **거짓 — 0/4** | 4건 전부 사내망(`192.168.0.22`)에 묶여 있고, 방문이 없었다 |
| **B** | 정본이 v3.1 과 **일치**한다 | **부분적으로 참** | 티켓 5건의 `status`·`evidence`·`blocker` 재부착 완료. 그러나 §7-2·§7-3 의 정본 결손 3건이 남아 있다 |

**ENTRY §1 의 9개 조건 — 사내망 불필요 4건은 전부 충족, 사내망 5건은 전부 미충족.**

### 증명 (사내망 불필요 4건 — 실제 명령과 출력)

```
$ cd /c/GuardianX/guardianx-source

### 조건 8 — W0-10: settings.py·.env.example 기본값에 사설 IP·내부 도메인 0건
$ grep -REn '192\.168\.[0-9]+\.[0-9]+' backend/.env.example frontend/.env.example ; echo "exit=$?"
exit=1                       ← 매치 없음. 정본 verify 는 `&& exit 1 || exit 0` 이므로 통과
$ grep -REc '192\.168\.|10\.10\.|\.gaion\.local' backend/config/settings.py
0
$ grep -cE "env\(|env\.list\(|env\.int\(|env\.bool\(" backend/config/settings.py
41                           ← 16곳 치환 후 전 토폴로지 값이 env 경유

### 조건 5(정적 부분) — W0-2: 우회 목록에 업무 모델 0건
$ grep -Ec "'(order|orderitem|payment|terminal)'" backend/common/base_model.py
0
$ sed -n '77,81p' backend/common/base_model.py
        performance_bypass_models = [
            # 프레임워크 모델 (rj-core/dj-core 의존 — 뷰 레벨 필터로 대응)
            'coreuser', 'usergroup', 'role', 'userprofilelink',
            'multilanguagecontent', 'userprofile', 'group',
        ]                    ← 잔여 7종 전부 프레임워크. 업무 7종과 교집합 ∅

### 조건 6 — W0-3: 수집 모델 수·EXEMPT 사유 기록
$ test -f docs/agent/evidence/W0-3/coverage.md ; echo "exit=$?"
exit=0                       ← 122줄. 격리가능 17종 전수 · 등록 6/17 · EXEMPT 3군 · 예상실패 등록부

### 조건 7 — W0-3: 미수정 결함의 명시 등록
   ※ 코드의 @expectedFailure 가 아니라 coverage.md §3 등록부로 대체했다. 사유는 §6-3.

### 조건 9 — 정본 재부착
$ git log --format='%h %s' -1 -- docs/agent/tickets.yaml
dfced8d docs(agent): WP-0 오프라인 산출물 — 격리 커버리지 대장 · D-218 재대조 · 정본 재부착

### 게이트 스크립트 2종 — 이 저장소에서 실제로 실행되는 유일한 자동 검사
$ python scripts/check_key_divergence.py ; echo "exit=$?"
exit=0
$ python scripts/check_demo_isolation.py ; echo "exit=$?"
PASS: 데모·목업 임포트가 가드되지 않은 경로에서 발견되지 않았다 (W0-4)
exit=0
```

### 증명 (사내망 5건이 왜 못 열렸는가 — 2026-08-15 실측)

```
$ Test-NetConnection 192.168.0.22 -Port 22
TcpTestSucceeded : False                     ← rj-core / @gaion/gcs-fe 를 받을 수 없다

$ docker info --format '{{.ServerVersion}}'
failed to connect to the docker API at npipe:////./pipe/dockerDesktopLinuxEngine   ← DB 없음

$ test -f frontend/package-lock.json ; echo $?
1                                            ← npm install 이 한 번도 성공한 적 없다
$ ls frontend/node_modules
(없음)
```

**즉 미충족 5건은 판단 실패가 아니라 단일 원인 하나에 묶여 있다 — 사내망 1회 방문.**
ENTRY §10 실행계획서는 그대로 유효하며, 방문 당일 소요는 §8 에 재산정해 두었다.

---

## 2. 티켓별 결과

| 티켓 | 상태 | 커밋 | 한 줄 요약 |
|---|---|---|---|
| **W0-10** | **done** | `c89215a` → `97c0924` → `7af88b6` | `.env.example` 13건 + `settings.py` **16건**(ENTRY 기재 13건은 오산) 전량 env 치환. DoD 는 grep 기준이라 오프라인에서 종결 |
| **W0-2** | verify-pending | `c1b9825` | ① 업무 7종 제거 **정적 확인 완료**. ② `test_bypass_list_does_not_grow` 실행 대기. ③ 은 P-W0-2-1 A안으로 **WP-1 이월** |
| **W0-3** | verify-pending | `c1b9825` · `c89215a` · `dfced8d` | 스위트 350줄 / 테스트 10건 존재. `coverage.md` 신규(격리가능 **17종**, 등록 **6/17**, 미등록 11종 열거). 실행 0건 |
| **W2-1** | verify-pending | `c89215a` | 모델·계약 19/19 일치, 격리 레지스트리 등록 확인. **마이그레이션 파일 없음** — 이번 WP 의 유일한 되돌릴 수 없는 작업 |
| **W0-4** | verify-pending | `9998b93` · `dfced8d` | D-218 새 DoD 4항목 중 **2항목 코드로 확정**(라우터 테이블 부재·홈 폴백). 나머지 2항목은 `npm install` 하나에 묶임 |

**done 1 / verify-pending 4.** 티켓을 몇 개 닫았는지는 판정 기준이 아니므로(§6-3) §1 이 판정이다.

---

## 3. 자가검증 — KPI 4축

| 축 | 지표 | 착수 시점 | 완료 시점 | 판정 |
|---|---|---|---|---|
| **편리성** | 사용자 조작 수·소요 시간 | — | — | **측정 불가.** 이 WP 는 사용자 경로를 한 곳도 바꾸지 않았다(신규 화면 0 · 신규 엔드포인트 0). 잴 대상이 없다 |
| **완결성** | 티켓 DoD 세부항목 충족률 | 3/12 (25.0%) | **6/12 (50.0%)** | **부분 달성.** W0-10 1/1 · W0-2 1/2 · W0-3 2/3 · W2-1 0/2 · W0-4 2/4 (W0-2 ③ 은 이월분이라 분모 제외) |
| " | 남은 TODO/FIXME (관여 5파일) | 0건 | **0건** | 유지 |
| **안정성** | 자동 게이트 실행/통과 | 0/0 | **2/2 통과** | `check_key_divergence.py` · `check_demo_isolation.py` |
| " | 격리 테스트 실행률 | 0/10 | **0/10** | **미달.** 스위트는 존재하나 dj-core·DB 부재로 한 번도 돌지 않았다 |
| " | 회귀 테스트 수 | 10건 존재 | 10건 존재 | 증감 없음 |
| **참신성** | 경쟁 대비 차별점 | — | **해당 없음** | 신규 기능 0건인 정리 WP. 차별점을 만든 WP 가 아니다 — §3-1 참조 |

**참신성 근거** — 경쟁 제품이 못 하는 것:
- **없음. 이 WP 에서는 만들지 않았다.** 억지로 적지 않는다.
  다만 `coverage.md` §4 가 다음 방문에서 **"저장소 밖(dj-core)에 격리 대상이 몇 종 더 있었는가"** 를 숫자로
  확정하게 되어 있고, 그 수는 이 프로젝트가 한 번도 가진 적 없는 값이다. 차별점이 아니라 **부채의 크기**이며,
  구별해서 적는다.

> **완결성 25%→50% 의 의미.** 오른 12.5%p × 2 는 전부 **오프라인에서 확정 가능한 항목을 확정한 것**이다.
> 남은 50% 는 난이도가 아니라 **접속**에 걸려 있다. 이 WP 에서 더 짜낼 수 있는 것은 없다.

---

## 4. 자가검증 — 보안

| 항목 | 결과 | 명령/근거 |
|---|---|---|
| 시크릿 스캔 | **0건 (대체 검사)** | `gitleaks`·`trufflehog`·`pre-commit` **셋 다 이 머신에 미설치** → 규정 도구 실행 불가. 대체로 ① `check_key_divergence.py` exit 0 ② `.env.example` 2파일 전 항목 플레이스홀더 확인(`your-…-here` / `CHANGE_ME_…`) 실값 0건 |
| 권한 우회 목록 증가 | **☑ 없음** | `base_model.py` 잔여 7종, 업무모델 매칭 `grep -Ec` = **0**. 베이스라인 대비 항목 추가 0 |
| 테넌트 격리 테스트 | **0/10 실행** | 환경 부재. 통과율이 아니라 **실행률이 0**이라는 점을 그대로 적는다 |
| 신규 외부 통신 목적지 | **0건** | 이 WP 의 코드 변경은 `settings.py` 기본값 제거뿐 — 목적지를 **더한 것이 아니라 뺐다** |
| 새로 열린 엔드포인트의 인증·권한 | **해당 없음 (0건)** | 신규 라우트·뷰 0 |

> **범위 밖 발견 1건을 지우지 않고 남긴다.** `settings.py` L629 `CORS_ALLOW_ALL_ORIGINS = True` 때문에
> `CORS_ALLOWED_ORIGINS` 허용목록이 현재 **무효**다. W0-10 의 DoD(사설 IP·내부 도메인) 범위 밖이라
> 코드는 건드리지 않고 P-W0-10-2 로 적재했다(WP-2 이관 제안). **"우리 빌드는 전 origin 을 허용한다"** 가
> 지금의 사실이며, WP-2 goal("외부에 내보낼 수 있는 빌드")과 정확히 같은 문제다.

---

## 5. 자가검증 — 코드

| 항목 | 결과 | 근거 |
|---|---|---|
| Coding Convention 위반 | **0건** | 신규 Django 모델 0 · 신규 FE 화면 0 · 신규 앱 0 → 컨벤션 적용 대상 자체가 없다. `settings.py` 치환은 D-212(유도값 1곳) 준수 — 41개 값 전부 `env(...)` 단일 경유 |
| Design Convention 위반 | **0건** | UI 변경 0 |
| 신규 파일 컨벤션 적용률 | **해당 없음** | 이 구간 신규 파일은 문서 3종(`coverage.md` · `ENTRY.md` · 템플릿 2)뿐. 신규 소스 0 |
| 테스트 커버리지 (해당 모듈) | **측정 불가** | `coverage.py` 실행에 Django 기동 필요 → dj-core 부재. 정적 대체값: 격리가능 모델 **17종 중 6종(35.3%)** 이 레지스트리에 등록 |
| 남은 TODO / FIXME | **0건** | `settings.py` · `base_model.py` · `tenant_filters.py` · `test_tenant_isolation.py` · `App.tsx` 전부 0 |

---

## 6. AUTHOR-ERROR — 지시서가 틀렸던 것

> D-214: 실측대로 구현하고 차이를 여기 적는다. `spec`·`dod`·`verify` 는 수정 권한 밖(금지 #11)이라 **한 자도 고치지 않았다.**

| # | 티켓/문서 | 무엇이 틀렸나 | 실측 | 내가 어떻게 했나 |
|---|---|---|---|---|
| 1 | W0-2 `verify` | `tests.test_tenant_isolation.BypassListTest` — **그런 클래스가 없다** | 실제 경로는 `TenantIsolationRegistryTest.test_bypass_list_does_not_grow` (`test_tenant_isolation.py:206`) | 정본 미수정. 방문 시 실측 경로로 실행하고 §8 에 명령을 박아 둠. **작성자 정정 요청** |
| 2 | W0-4 `dod` | *"해당 URL 직접 접근 시 404"* — **D-218 이 이미 기각한 문구** | D-218 확정본은 *"플래그 OFF 청크에 데모 식별자 0건 + 라우터 테이블 부재(홈 폴백 허용)"* | P-W0-4-1 A안. D-218 을 실효 DoD 로 검증. **정본 텍스트대로 읽으면 다음 사람이 nginx 404 를 구현한다** |
| 3 | ENTRY §11-2 | 예상 실패 **3건**에 `@expectedFailure` 를 **코드에** 걸라고 지시 | ① 파일 머리말이 xfail 금지 ② 금지 #5 격리테스트 수정 금지 ③ **D-209: 실패가 산출물** — xfail 은 그 산출물을 스위트에서 지운다. 게다가 실측상 확정 실패는 **1건뿐**(나머지 통과예상 1·판정불가 1) | 코드 무수정. `coverage.md` §3 문서 등록부로 대체 → P-W0-3-1 A안. **3건 전부 걸었다면 뒤 둘이 unexpected success 로 스위트를 깨뜨렸다** |
| 4 | ENTRY §2 | `settings.py` 사설 IP·내부 도메인 **13곳** | 실제 **16곳** (주석 1 · `AI_RTSP_PATH` 1 · ENTRY 산술오류 1) | 16곳 전량 치환. ENTRY 수치는 고치지 않고 여기 기록 |
| 5 | **AGENT_LOOP v4.0 STEP 0-2·0-3** | 첫 출력 줄에 `total=<manifest.total>` 을 요구하고 `manifest.total`·`manifest.ids` 대조를 지시 | **`tickets.yaml` v3.1 의 `meta` 에 `manifest` 키가 없다** (키 13개: version·source_root·active_phase·updated_at·status_enum·gate_enum·baseline_sha·decisions_file·pending_file·autorun·review·work_packages·kind_enum) | 배열 길이 실측(**66**)과 `meta.version`(3.1)으로 대체 보고. **무결성 검사 0-3 은 현 정본에서 수행 불가** |
| 6 | **`tickets.sha256`** | 정본 무결성 체크섬 — **전 커밋에서 한 번도 맞은 적이 없다** | 아래 §6-1 | 이 파일은 에이전트 권한 밖(정본은 `status`·`blocker`·`evidence`·`updated_at` 만)이라 **갱신하지 않았다.** 작성자 판단 요청 |

### 6-1. `tickets.sha256` — 게이트가 처음부터 죽어 있었다

```
$ sha256sum -c docs/agent/tickets.sha256
docs/agent/tickets.yaml: FAILED

$ for c in $(git log --format='%h' -- docs/agent/tickets.yaml); do ... done
dfced8d  actual=285ffa9c2586dc0a  recorded=e3cccf4583848057  MISMATCH
9998b93  actual=3315f308a68e6e61  recorded=b583551002dc84ea  MISMATCH
c89215a  actual=40b2d75afac4f29d  recorded=b583551002dc84ea  MISMATCH
c1b9825  actual=e4e1dc91507cd63b  recorded=b583551002dc84ea  MISMATCH
19c61e8  actual=84d816205293c85c  recorded=b583551002dc84ea  MISMATCH
4afca2b  actual=4df5f0f15ced455c  recorded=b583551002dc84ea  MISMATCH   ← 베이스라인조차 불일치
```

**베이스라인 커밋에서부터 어긋나 있다.** 즉 `registry-mismatch` 는 hard_stop 5개 중 하나인데,
그 판정에 쓰라고 놓은 파일이 **단 한 번도 참을 낸 적이 없다.** 셋 중 하나다.

- **(a) 설계 문제** — 체크섬이 파일 **전체**를 덮는데 에이전트는 `status`·`evidence`·`blocker` 를 정당하게 고친다.
  그러면 정상 작업마다 깨진다. 체크섬은 **`spec`·`dod`·`verify`·`manifest`·`work_packages` 부분집합**에 걸려야 한다.
- **(b) 생성 시점 문제** — `e3cccf4…` 는 어떤 커밋 상태와도 대응하지 않는다. 계산 후 파일을 더 고친 것으로 보인다.
- **(c) 미사용** — 애초에 STEP 0 이 이 파일을 읽지 않는다(0-3 은 `manifest` 만 말한다).

**의견: (a)+(c) 로 보고, 부분집합 해시로 바꾸거나 파일을 폐기하는 것이 맞다.**
지금 상태는 **"무결성 게이트가 있다"는 착시**를 만들며, 그것이 게이트가 없는 것보다 나쁘다.

---

## 7. ★ 사람이 답해야 하는 것

| ID | 질문 | 선택지 | 내 의견 | 왜 내가 못 정하나 |
|---|---|---|---|---|
| **7-1** | **ENTRY.md 에 `APPROVED:` 줄이 없는데 §11 오프라인 작업 5건이 이미 실행·커밋되었다.** 승인은 있었던 것으로 보는가 | A: 소급 승인 — ENTRY 첫 줄에 `APPROVED:` 기입 / B: 승인 없이 진행된 것으로 보고 §11 산출물 재검토 | **A**. `tickets.yaml` 블로커에 *"대표 승인 2026-08-15"* 가 두 곳 기록돼 있어 실질 승인은 있었던 것으로 읽힌다 | **금지 #16 — 승인 줄은 사람만 쓴다.** 에이전트가 이 판단을 내리면 관문 자체가 무의미해진다 |
| **7-2** | **`decisions_pending.yaml` 5건이 전부 `status: open` 인데, 그중 2건(P-W0-2-1·P-W0-10-1)은 티켓 블로커에 "대표 승인 2026-08-15" 로 적혀 있다.** 어느 쪽이 사실인가 | A: 승인됨 — D-221·D-222 발행하고 `status: answered` / B: 미승인 — 블로커 문구 정정 | **A**. 두 결정을 전제로 이미 코드가 나갔다(`settings.py` 16곳 치환) | **`decisions.yaml` 은 읽기 전용(금지 #12), pending 은 추가만 가능.** `status` 변경은 작성자 몫이라고 파일 머리말에 명시돼 있다 |
| **7-3** | **`tickets.sha256` 을 어떻게 할 것인가** (§6-1) | A: 부분집합(`spec`/`dod`/`verify`/`work_packages`) 해시로 재설계 / B: 파일 폐기 + STEP 0-3 을 `manifest` 신설로 대체 / C: 매 커밋 전체 해시 갱신 | **A**. C 는 에이전트가 정본 해시를 갱신하게 되어 게이트가 자기증명이 된다 | 정본 파일 권한 밖 + 루프 명세 변경 사항 |
| **7-4** | **`manifest` 블록 부재** (§6 #5). STEP 0-2·0-3 을 살릴 것인가 | A: `tickets.yaml meta` 에 `manifest: {total: 66, ids: [...]}` 신설 / B: STEP 0-2·0-3 문구를 실제 구조에 맞게 개정 | **A**. 66개 id 목록이 정본에 박히면 티켓 유실을 실제로 잡는다 | `meta` 는 에이전트 수정 권한 밖(금지 #11) |
| **7-5** | **W0-2 `verify` 의 `BypassListTest` 오기** (§6 #1) | A: 정본을 실측 경로로 정정 / B: 그 이름의 별칭 클래스를 코드에 신설 | **A**. B 는 테스트 파일을 지시서에 맞추려고 고치는 것이라 금지 #5 와 결이 같다 | `verify` 필드 수정 권한 밖 |
| **7-6** | **사내망 방문일 확정** — WP-0 종결의 **유일한** 잔여 조건 | 날짜 지정 | ENTRY §10 기준 실작업 **약 2시간**. §8 참조 | 일정은 사람의 것 |

**되돌릴 수 없어 보류한 것: 1건.**
`W2-1` 마이그레이션 생성·적용은 이 WP 의 유일한 스키마 변경이며,
**dry-run 리포트 선행 없이는 실행하지 않는다**(금지 #9 · hard_stop `data-destructive`). 절차는 §8 에 그대로 있다.

---

## 8. 남은 미완결 — 사내망 방문 1회로 전부 풀린다

| 티켓 | 상태 | 푸는 조건 | 실행할 명령 |
|---|---|---|---|
| (전제) | — | `192.168.0.22:22` 도달 | `npm ci` 또는 `npm install` → `npm ls rj-core @gaion/gcs-fe` · **`package-lock.json` 커밋(W0-8 부수 종결)** |
| **W0-4** | verify-pending | 위 전제 | `VITE_ENABLE_DEMO=false npm run build` → `grep -rlE 'mockupDemoUi\|setup-demo-(file\|url)' dist/assets` **→ 0건** · 대조군 `VITE_ENABLE_DEMO=true` 로 재빌드해 **청크가 나오는 것**까지 확인(게이트가 실제로 작동한다는 증거) |
| **W2-1** | verify-pending | Docker 기동 + 위 전제 | ① `python manage.py makemigrations stream_monitors --dry-run -v 2` **→ 리포트 먼저 커밋** ② `sqlmigrate` 보존 ③ `migrate` ④ `makemigrations --check --dry-run` exit 0 |
| **W0-3** | verify-pending | 위 전제 | `python manage.py test tests.test_tenant_isolation -v 2` → 출력 전문을 `evidence/W0-3/` 에 저장 → **`coverage.md` §4 여섯 칸 기입** (마지막 칸 = dj-core 안에 있던 격리 대상 수) |
| **W0-2** | verify-pending | 위와 동일 실행 | ⚠ 정본 verify 의 `BypassListTest` 는 없다. **실측 명령**: `python manage.py test tests.test_tenant_isolation.TenantIsolationRegistryTest.test_bypass_list_does_not_grow -v 2` |

**예상 결과를 미리 못박아 둔다** (`coverage.md` §3 — 사후 합리화 방지).

| 테스트 | 예상 | 실패 시 귀속 |
|---|---|---|
| `test_registry_covers_all_isolatable_models` | **실패 확정** (미등록 11종) | W0-14 (WP-1) |
| `test_unisolated_set_has_not_grown` | 통과 예상 | 실패 = 새 비격리 모델 유입 |
| `test_bypass_list_does_not_grow` | 통과 예상 | 실패 = W0-2 회귀 |
| `test_null_created_by_is_not_globally_visible` | 판정 불가 (dj-core 매니저) | W0-13 (WP-1) |
| `TenantIsolationAPITest` 5건 | 판정 불가 (`api_base` 실측 미확인) | 404 면 **테스트가 아니라 `api_base` 를 고친다** |

> **이 스위트가 처음 돌 때 초록이 아닌 것이 정상이다.** WP-0 의 goal 은 "격리 완결"이 아니라
> "verify-pending 종결"이고, 실패를 **분류해서 WP-1 입력으로 넘기면** WP-0 의 임무는 끝난다.

**권고: 같은 방문에 W0-1b(실키 재발급 · WP-2)를 함께 처리한다.** 방문 1회를 아낀다.

---

## 9. 다음 WP 착수 전 필요한 사람 작업

1. **§7-1 · §7-2 정리** — ENTRY 승인 줄 기입, `decisions_pending` 2건을 D-221·D-222 로 발행하고 `answered` 처리.
   **이것이 goal (B)"정본 일치"의 남은 절반이다.**
2. **§7-3 · §7-4 · §7-5 정본 손질** — `tickets.sha256` 처리 방침 · `manifest` 신설 여부 · W0-2 `verify` 경로 정정.
3. **§7-6 사내망 방문일 확정** (실작업 ~2시간). 이것 없이는 WP-0 이 영구히 부분 참으로 남는다.
4. **WP-1 착수 판단** — WP-0 을 verify-pending 상태로 두고 WP-1(테넌트 격리 완결)을 여는 것이 가능한가.
   - **의견: 열 수 없다.** WP-1 의 goal 은 *"group A 토큰으로 group B 데이터에 도달 불가함을 **HTTP 레벨로** 증명"*
     이고, 그 증명 도구가 바로 이번에 못 돌린 `TenantIsolationAPITest` 다. **같은 환경에 같이 묶여 있다.**
   - 다만 `coverage.md` §1 이 미등록 11종을 이미 열거했으므로, **W0-14 의 등록 작업(코드)은 오프라인에서 선행 가능**하다.
     방문일이 멀면 그쪽을 먼저 여는 것을 제안한다 — **단 WP 순서 변경은 대표 승인 사항(금지 #18)이라 내가 정하지 않는다.**

---

**승인 요청 사항**: **1항(판정 — 부분적으로 참)** 과 **7항(사람이 답할 것 6건)** 을 특히 봐 주십시오.
그중 **7-1(승인 줄 부재)** 과 **7-3(무결성 게이트가 처음부터 죽어 있었다)** 은 이 WP 의 결과물이 아니라
**루프 자체의 결손**이며, 다음 8개 WP 에 그대로 상속됩니다.
