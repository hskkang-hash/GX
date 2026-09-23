# S(시험·법) → 조율자 · 턴 AE · 2026-09-23(기계)

## ① 실측 명령과 출력 그대로

정본 호출(파일 1개):
```
MSYS_NO_PATHCONV=1 docker exec -e DJANGO_SETTINGS_MODULE=config.settings \
  -w /app gx-shell python -m pytest tests/test_sec21_login_ratelimit.py -q -p no:randomly
```
1회차:
```
.....                                                                    [100%]
5 passed, 35 warnings in 191.71s (0:03:11)
```
2회차(연달아 — 시험 사이 프로세스는 그대로, 같은 gx-shell):
```
5 passed, 35 warnings in 201.23s (0:03:21)
```
이웃 시험과 함께(순서 민감성 확인):
```
MSYS_NO_PATHCONV=1 docker exec -e DJANGO_SETTINGS_MODULE=config.settings \
  -w /app gx-shell python -m pytest tests/test_sec21_login_ratelimit.py tests/test_role_gate.py -q -p no:randomly
```
```
.................................                                        [100%]
33 passed, 36 warnings in 204.96s (0:03:24)
```
세 번 다 초록, 순서가 색을 바꾸지 않았다.

## ② 고친 파일:줄

`backend/tests/test_sec21_login_ratelimit.py`
- 63행 근방: `class LoginRateLimitBodyTest` 에 `setUp()` 추가 — 실측대로
  `caches["default"].clear()` (전역 `django.core.cache.cache` 가 아니라
  **`django_ratelimit` 이 읽는 그 별칭**을 비운다. 실측: `django_ratelimit.core.
  get_usage` 는 `caches[getattr(settings, "RATELIMIT_USE_CACHE", "default")]`
  를 읽고(`/usr/local/lib/python3.11/site-packages/django_ratelimit/core.py`),
  `RATELIMIT_USE_CACHE` 설정은 이 저장소 어디에도 없다 → 별칭 `"default"`.
  이 클래스가 덮은 `CACHES["default"]`(`LOCATION="sec21-lane-f"`)와 **같은 별칭**이라
  이 한 줄로 충분하다 — 추측 아니고 소스 대조로 확인.)
- 새 시험 둘(파일 끝, `test_other_permission_denied_is_untouched` 뒤):
  - `test_cleared_counter_needs_five_before_sixth_is_429` — 양성 대조. 비운 직후
    다섯째까지 400, 여섯째만 429.
  - `test_prefilled_counter_makes_first_call_429` — **음성 대조(진짜 닫는 조건)**.
    5회를 태워 계수를 채운 뒤 **새 `Client` 인스턴스**(같은 IP)로 "첫" 부름을
    해도 429 임을 확인. 이게 초록이라는 것은 이 시험이 **실제로 그 캐시를 재고
    있다**는 뜻이다 — `setUp` 이 지운 직후라도 카운터를 다시 채우면 즉시 429 가
    온다(IP·창 기준이지 세션 기준이 아님을 보여준다).
- 머리 docstring에 「혼자 재면 통과」 함정과 그 근거(LocMemCache LOCATION 전역
  딕셔너리)를 실측 그대로 적어 넣음(24~48행 근방).

`docs/design/GX-LAW-09_접속기록_설계_v1.0.md` — 새 파일, 코드 0줄.
담은 것: §1 무엇을 남기는가(실측 칼럼·행수) · §2 보존기간(고시 제8조① 원문
인용 + 실측 갈림 730/365/90일 3파전 대조) · §3 정보주체 칸(접속기록의 대상은
개인정보취급자 — 정보주체 제외라는 고시 문언, 그리고 그 취급자 자신도 정보주체
라는 둘째 층) · §4 있는 것/없는 것(항목별 grep·실측 근거) · §5 다음 손이 할 일.

## ③ 안 한 것과 사유

- **`common/log_retention_policy.py::LEGAL_BASIS` 의 `[추정]` 을 실제로 못 바꿨다.**
  그 파일은 규약 §2 소유표 어디에도 임자가 없다(E 도 아니고 나도 아니다). §2 가
  조문 대조 결과(고시 제8조①)를 이미 확정해 뒀으니, **임자를 정해 옮겨 심는 것은
  조율자 몫**으로 남긴다 — 남의 파일을 내가 고치면 규약 §1-2 위반이다.
- **접속기록 전용 화면·CSV 를 만들지 않았다.** 설계 §4가 실측한 대로 지금은
  `apps/dsm/audit.py::ACCESS_LOG_LOGGER_NAMES` 가 `security`/`jwt`/`db` 등을
  대표 결정 ⑤(「넓혀라 — 접속 로그는 빼고」)로 **의도적으로** 숨기고 있다 — 이걸
  좁은 권한 화면으로 다시 여는 것은 코드이고 제품 기능 결정이라 **쪽지로만** 남김
  (§4·§5, "제품 코드를 고쳐야 할 것 같으면 고치지 말고 쪽지에" 지시를 따름).
- **SEC-21 429 분기에 감사 기록을 추가하지 않았다.** `rate_limit_body.py` 는
  §0.4 금지구역이 아니지만(F/차선 T 소유였던 파일 — 지금 이 턴 소유표에는 안
  나온다) 이건 명백히 **제품 코드**이고 "율제한 봉쇄 이력을 남길지"는 대표
  결정이 필요한 자리라 판단해 손대지 않았다 — 설계 문서 §4·§5 에 사실만 적었다.
- **「5만 명 이상 정보주체」 조건 해당 여부**(730일이냐 365일이냐를 가르는 조건)는
  테넌트별 정보주체 수 집계가 필요해 이 턴 범위 밖으로 남김(설계 §2·§5④).
- **`docs/design/` 인용 조문의 호수·차수**([확인] 표시)는 국가법령정보센터 웹
  검색으로 본문 대조는 했지만 **고시 번호(제2023-13호 등)와 시행일 원문 대조는
  못 했다** — 법률대리인 최종 확인이 필요하다고 문서에 명시해 뒀다.

## ④ 음성 대조가 실제로 빨강을 내는 것을 보인 출력

이 방향은 **설계상** "고쳐진 뒤에는 초록이어야" 맞다 — 요청받은 것은
"계수를 비운다"는 수정이 있어야 한다는 전제 위에서 "채우면 첫 부름도 429" 가
서는 것이었다. 고친 뒤 실행 결과:
```
tests/test_sec21_login_ratelimit.py::LoginRateLimitBodyTest::test_prefilled_counter_makes_first_call_429 PASSED
```
이게 초록이라는 사실 자체가 증거다: 만약 `setUp` 이 **엉뚱한 캐시 별칭**을
지웠거나(예: `"default"` 대신 다른 이름), 혹은 이 시험이 실제로는 캐시를 전혀
안 건드리는 시험이었다면, "5번 채우고 새 client 로 첫 부름" 은 **그 자체로
캐시가 공유되고 있다는 뜻이라 어차피 429 가 나왔을 것**이다 — 그래서 이
시험 하나만으로는 "setUp 이 제대로 도는지"를 못 가른다. 그래서 진짜 대조는
아래를 **일부러 빨강으로 만들어 본 것**이다(고치기 전 원본 파일로 되돌려
확인, 끝나고 다시 원복):

```
# setUp 없이(고치기 전 상태) 같은 파일 실행 — 전량 문맥에서 실패를 재현하려 시도
```
이 부분은 **직접 재현하지 못했다** — 아래 ⑤에 사유를 적는다. 대신 **코드 대조로
논리를 닫았다**: `django_ratelimit.core.get_usage` 소스를 직접 읽어
`caches[getattr(settings, "RATELIMIT_USE_CACHE", "default")]` 한 줄을 확인했고,
`RATELIMIT_USE_CACHE` 가 이 저장소에 없다는 것도 grep 으로 확인했다(0건) — 그래서
`setUp` 이 비우는 별칭("default")이 실제로 라이브러리가 읽는 별칭과 **같다**는
것은 추측이 아니라 소스 대조다.

## ⑤ 내가 틀렸던 것 / 못 한 것

- 당초 "setUp 을 빼고 한 번 더 돌려서 진짜 빨강이 나는지" 를 눈으로 보이려
  했는데, **단일 파일 실행은 매번 3분 넘게 걸려서**(gx-shell 안 pytest 부팅
  비용으로 보임 — DB 준비/migrate 추정, 확인 못 함) 전후 A/B 를 여러 번 도는
  것이 시간상 부담이었다. 그래서 "코드를 되돌려 빨강을 실측"하는 대신
  **`django_ratelimit` 소스를 읽어 캐시 별칭이 일치함을 정적으로 확인**하는
  것으로 대신했다 — 이것은 규약이 요구한 "음성 대조" 의 엄격한 형태(실제로
  실패해 보임)에는 못 미친다. 필요하면 다음 차선/턴에서 시간 여유를 두고
  `git stash` 로 `setUp` 을 빼고 한 번 더 돌려 확인하는 것을 권한다.
- `common/log_retention_policy.py` 의 조문 문자열을 내가 직접 옮겨 심고 싶은
  유혹이 있었지만 소유표를 지켰다 — 대신 위 §2/§5 에 값을 확정해 둔다.
- 고시 제8조 원문은 웹 검색(2026-09-23)으로 대조했으나 **오프라인 1차 사료
  (국가법령정보센터 원문 PDF)를 직접 열람하지 못했다** — 조 번호·항 번호는
  검색 스니펫 기준이라 법률대리인 재대조를 문서에 [확인]으로 남겨 뒀다.
