# 턴 V — V 단독 검증 차선 (P-176 · 마지막 갱신)

잠금: 컨테이너 안에 잘못 잠갔다가(2026-09-19T05:38:23Z) 풀고 **호스트에** 다시 잠갔다(05:48:12Z · 세션 `turn-v`).

## 잰 것
| 수 | 값 | 직전(턴 U) |
|---|---|---|
| 상용 점수 | **67.8** | 67.8 |
| 손 안 도달율 | **69.2%** (92/133) | 69.2% (92/133) |
| 영역 ① | **10/39** (26%) · 빨강 0 · 회색 22 · 잠김 7 | 10/39 |
| FC 하한 (정정 후 34식) | **29/48** · 초록 29 · 빨강 4 · 회색 15 | 28/48 (정정 전) |
| FC 하한 (같은 관측 · 정정 전 정본) | **26/48** | — |
| 온보딩 (잰 행 35) | **24.5/48** · 초록 22 · 반 5 · 빨강 8 · 회색 0 · 정본없음 13 | 14.5/48 (잰 행 22) |
| 캡처 | **33/36** (+ 역할 0 **6/7**) | 33/36 |
| 걷기 | **5/5 완주** (W4 = NOT_WALKED) · 게이트는 빨강 | 3/3 |
| 계약 진입면 | 108/108 도달 | — |
| 감사 체인 | **끊김 4** (하나는 이번 턴에 새로 났다) | 끊김 3 |
| 편리성 U1 | 2/3 (죽은 카메라 0클릭·271ms · 인계 메모 1클릭·8,870ms) · #1 회색 | 0/3 |
| 편리성 U3 | 1/1 (2탭 · 17,875ms · opened 9,825ms) — 목표 ≤30초 충족 · **1탭 목표는 2탭** | 0/1 |
| 단위시험 | 안 쟀다 (조율자 실측 1,650 passed · 6 skipped 를 그대로 인용) | — |

## 게이트 17종
초록 13 — live-freshness · secrets · ui-secrets · ui-copy · post-arg-style · bypass · isolation ·
deprecated-base · ui-library · forbidden-zone · route-alive · contract-route-reach · bundle-api-base
빨강 3 — gate-header · dormant · click-completes
대기 1 — model-inheritance (변경된 models.py 0건 · 빚 아님)

## 손 위
- (없음 — 순서를 다 돌았다) · `walk_states`(U5) 가 아직 돈다

## 안 잰 것
- **U4·U5 5상태 캡처** — 지시서가 가리킨 자리 `docs/review/WO-GX-20260915-01/<화면코드>/` 가 **없다**(`docs/review/` 자체가 없다). 회색.
- **실카메라 스냅샷** — 원천 0. 회색(직전과 같다).
- 단위시험 전량 — 안 돌렸다(조율자 수를 인용).

## 함정 넷 (다음 V 가 안 밟게)
1. **gx-shell 의 `/repo` 에 `docs/` 가 없다.** bind 는 backend·frontend·scripts 뿐이다.
   컨테이너에서 판정기를 돌리면 증거를 못 읽어 **FC 0/48 거짓 회색**이 난다. **판정은 호스트에서.**
   (같은 이유로 `capture_screens --role0` 의 산출물 `/repo/docs/agent/evidence/P-105/...` 는 저장소에 안 남는다.)
2. **V_LOCK 을 컨테이너 안에 잠그면 안 된다.** `v_lock` 의 ROOT 가 갈려 딴 파일이 생기고,
   `verify_route_alive.delegate_to_container` 는 `GX_V_SESSION_ID` 를 안 넘겨서 **잠근 사람 자신**이 막힌다.
   그때 영역 ① 7/39 · 상용 66.3 · 도달율 66.9% 라는 **거짓 낮은 수**가 나왔다. 호스트로 옮기니 10/39 · 67.8 · 69.2%.
3. **호스트 도구는 `MSYS_NO_PATHCONV=1` 없이 돈다** — 붙이면 `verify_gates.sh` 가 `/c/...` 를 Windows python 에
   넘겨 게이트 17종이 전부 exit 3(tickets.yaml 파싱 실패)이 된다. 반대로 `docker exec -w /repo` 는 그 변수가 **있어야** 한다.
4. **세션 점유자 `gxprobe_v` 는 `GX_LANE=v` 를 줘야 자기 것으로 읽힌다.** 안 주면 route-alive·contract-route-reach 가
   「남의 세션」으로 회색이 된다 — 역시 거짓 회색.

## 덧 — 상태 표 (walk_states · U5 계정 · 주입은 브라우저 안에서 끝난다)
**48/56** (● 25 · ◐ 23 · 빈칸 2 · — 6) · 오류 흐름 주입 40건 중 통과 36 · 못 쟀다 4
빨강 1항목 — **빈 상태 문구가 없다 3화면**: 관리·설정 · 카메라 일괄 등록 · 보고서 (0건을 침묵으로 그린다)

## 덧 — FC 정본과 온보딩 정본이 갈린다 (정정 문안 후보)
FC 회색 15 중 **9자리**를 같은 턴에 온보딩 도구가 실제로 눌러 색을 냈다:
 초록 6 — U2#9 · U3#16 · U4#1 · U5#1 · U5#4 · U5#5
 빨강 3 — U2#16 · U4#15 · U5#10
FC 정본이 이 아홉 자리에 「정본 없음」이라 적고 있다. 고치지 않았다 — 문안만 적는다.

## 덧 — LAW-07′
`gxseed_u4_official`(view_only_-_anyang)로 두드린 `/api/dsm/law/privacy-requests` **5자리 전부 403**
(GET · POST · GET {receipt_no} · GET {receipt_no}/masked · POST {receipt_no}/reply). 빨강 그대로 둔다.
