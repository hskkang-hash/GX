# N4 승격 제안 — 턴 AP (P-356·392·419·428 · WO-19 · 세종 P-424)
(턴 AP · WO-GX-20261001-19 · 차선 N4)

**조율자가 대장(`docs/agent/evidence/D-346/ga_readiness.yaml`)에 적용한다 — 이
문서는 제안·보고만 한다.** 이 차선은 `ga_readiness.yaml` 을 손대지 않았다.

게이트: `python scripts/verify_spec_ap_n4.py`(기본 `--no-run` · `--self-test` 있음)
+ 자기시험 짝 `backend/tests/test_ap_n4_gate_can_fail.py`.

## 0. 일 둘 요약

① **온보딩 U4#8 조합 검색(세종 P-424)** — `GET /api/dsm/events/combined-search`
(사건번호 PK 정확 일치 + 주소·유형 서버 대조) + `EventList.tsx` 조합 검색 칸 셋
(사건번호·주소·유형). `scripts/measure_onboarding_t.py` 는 고치지 않았다 —
그 행은 정본이 「◐ 상한」을 직접 선언한 행(`cap_half=True`)이라 온보딩 점수
자체는 이 턴이 무엇을 해도 0.5 를 넘지 않는다(정본 표기 — 버그가 아니다).
이 턴이 올린 것은 그 행이 가리키는 **실제 기능**이다. 시험
`backend/tests/test_ap_n4_u4_8_combined_search.py` 5/5 통과.

② **새 절 승격(annex, 미포함표 F3·F5·F6·U4 잔여)** — 아래 8건을 닫았다(P-356
넷 다 있음). 3건(FWS-F3-16 · FWS-F5-10 · DSM-U4-05)은 반쪽으로 정직하게
남겼다(무엇이 없는가 §2 참고 — FWS-F3-16 은 이 차선이 먼저 닫았다고 적었다가,
같은 절을 병행 손대던 차선이 더 정확한 판정으로 정정해 다시 열었다 · §2 참고).

## 1. 닫은 여덟 (승격 제안)

| id | 제목 | 구현 | 증거 | 게이트 행 |
|---|---|---|---|---|
| FWS-F5-01 | 정찰 임무 수신(발화 추정 좌표·반경) → 열화상 정찰 | 기존 요청·상태 전이(턴 AM `drone.py`, 손대지 않음) + 이 턴 신설 `GET /api/fws/ap/drone/missions/{id}/recon-coords`(`ap_f5.py::recon_coords`, K1 이벤트 lat/lng + 반경 합침) · 열화상 센서 행은 `excluded_by: P-428` | `docs/agent/evidence/SPEC/FWS-F5-01.json` | `verify_spec_ap_n4.py` |
| FWS-F5-02 | 열점·화선 표시(열화상 프레임 → 지도 폴리라인) | 기존 구현(턴 AM `drone.py`, 손대지 않음) 그대로 · 이 턴은 두 열린 행(열화상 프레임 판독·지도 렌더)을 `excluded_by: P-428` 로 재판정(하드웨어 실연동·§0.4 인접 지도 렌더 — WO-19 명시) | `docs/agent/evidence/SPEC/FWS-F5-02.json` | `verify_spec_ap_n4.py` |
| FWS-F5-03 | 확인 회신(산불 맞음/오인 · 사진·열화상) | 기존 판정 문(F1-06 재사용, 손대지 않음) + 이 턴 신설 `POST/GET /api/fws/ap/drone/verifications/{id}/thermal-attachment`(`ap_f5.py::attach_thermal`/`thermal_attachments` — 사진 참조와 다른 칸) | `docs/agent/evidence/SPEC/FWS-F5-03.json` | `verify_spec_ap_n4.py` |
| FWS-F5-08 | 비행 기록·배터리·기체 상태 | 기존 구현(턴 AM `drone.py`, 손대지 않음) 그대로 · 이 턴은 열린 행(실제 기체 자동 수신)을 `excluded_by: P-428` 로 재판정(드론 커넥터 — WO-19 명시) | `docs/agent/evidence/SPEC/FWS-F5-08.json` | `verify_spec_ap_n4.py` |
| FWS-F6-04 | 확산예측 결과 수신(API [미확인] 또는 업로드) | 이 턴 신설 `POST/GET /api/fws/ap/incidents/{id}/spread-results`(`ap_f6.py`, 업로드 경로) · API 경로 행은 `excluded_by: P-428`(외부 기관 실연동, 명세가 「API 또는 업로드」로 택일 허락) | `docs/agent/evidence/SPEC/FWS-F6-04.json` | `verify_spec_ap_n4.py` |
| DSM-U4-02 | 중간 보고 사이클 — 08시·17시 기준 자동 초안 · NDMS 내보내기 | 이 턴 신설 `POST /api/dsm/situation-reports/interim-batch`(`u4_interim_report_service.py::issue_interim_batch` — 슬롯·날짜 중복 방지) + `GET /api/dsm/situation-reports/ndms-export.csv`(항목 1:1) · 기존 `situation_report_ledger_service.issue_report(kind="중간")`(턴 AM, 손대지 않음) 재사용 | `docs/agent/evidence/SPEC/DSM-U4-02.json` | `verify_spec_ap_n4.py` |
| DSM-U4-08 | 재난관리평가·감사 자료 묶음 — ZIP(PDF+CSV) | 이 턴 신설 `GET /api/dsm/evaluation-bundle.zip`(`u4_evaluation_bundle_service.py` — 기존 일곱 원천의 `list_x`/`read_csv`/`drill_report` 공개 면을 그대로 CSV 로 묶는다, 새 집계 없음) · PDF 행은 `excluded_by: P-392`(이미 있는 결정 재사용 — HWPX/PDF 렌더 미채움) | `docs/agent/evidence/SPEC/DSM-U4-08.json` | `verify_spec_ap_n4.py` |
| DSM-U4-09 | 통계 축 추가 — 지역안전지수 6분야 | 이 턴 신설 `GET /api/dsm/stats/safety-index`(`u4_safety_index_stats.py` — 기존 `stats.stats_axes()` 의 event_type 축을 재접음, 새 질의 없음) + 매핑 표(`u4_regulations.EVENT_TYPE_SAFETY_INDEX`) | `docs/agent/evidence/SPEC/DSM-U4-09.json` | `verify_spec_ap_n4.py` |

## 2. 못 닫은 셋 — 무엇이 없는가

- **FWS-F3-16**(통계 — 골든타임 준수율 포함) — 이 차선은 처음에 골든타임 행을
  `excluded_by: P-428`(외부 운영 집행)로 닫았다고 적었다. 같은 절을 이 턴
  병행 손대던 다른 차선(`office2.py` 소유)이 대응 시계 실측(`arrived_at`,
  신고 접수 → 현장 도착)으로 그 행을 코드로 더 깊이 채웠고, 그 과정에서
  **이 차선의 판정을 정정**했다 — 헬기 물 투하 시각이 없는 것은 외부 실연동이
  아니라 「그 값을 담는 칸 자체가 저장소에 없는」 코드 결손이라 `excluded_by`
  로 못 막는다(TITLE_PARTS §3). 이 차선은 그 정정을 그대로 받아들인다(D-212,
  남의 더 나은 판정을 덮어쓰지 않는다) — 골든타임(신고 기준)은 이제 실측으로
  닫혔지만 헬기 투하 기준 하나가 남아 절 전체는 여전히 반쪽이다.
- **FWS-F5-10**(계량(비행 분)) — 이 턴이 닫은 것: 합계·건수(기존, 손대지 않음)
  + **월별 필터 실제 검증**(새 시험, 코드 변경 없음) + **월 표**(신설
  `GET /api/fws/ap/drone/flights/minutes/monthly-table`). 여전히 못 닫은 것:
  공용 계량 커널(S-20/`apps.dsm.metering` 류)과의 연계 — 이 절의 집계는
  F5-08 감사 로그를 세는 드론 전용 로컬 카운터일 뿐 공용 커널에 반영되지
  않는다. 공용 모듈을 고치는 일은 여러 차선이 공유하는 자리라 `excluded_by`
  로 막을 수 없다(외부 실연동이 아니다) — 이 턴 범위 밖으로 정직하게 남긴다.
- **DSM-U4-05**(일일상황보고 자동) — 이 턴이 닫은 것: 재난상황(오늘 발생·
  등급별·미종결)·통제 현황(`control_board_service.daily_reflection` 재사용)·
  대피(통제 지점 대피 인원 합산) 셋(신설 `GET /api/dsm/daily-report`). 여전히
  못 닫은 것: 기상특보(외부 기관 API — `excluded_by: P-428` 로 닫힘)를 빼도
  **피해 누계·동원·향후 계획** 셋이 열려 있다 — 이 저장소에 그 값을 쥔
  구조화 표가 없다(별지 제1호서식은 사람이 그때그때 채우는 자유 입력칸, 재조회
  가능한 표가 아니다 · `incident_report.py` 실측). 지어내지 않는다(D-280).

## 3. 조율자에게 넘길 줄

- 새 `/api/dsm/` 라우트 다섯 — `EVENT_ENTRY_SURFACE`(`backend/tests/test_f05_event_api.py`, 조율자 소유)에 올려야 한다:
  `GET /api/dsm/events/combined-search` · `POST /api/dsm/situation-reports/interim-batch` ·
  `GET /api/dsm/situation-reports/ndms-export.csv` · `GET /api/dsm/daily-report` ·
  `GET /api/dsm/evaluation-bundle.zip` · `GET /api/dsm/stats/safety-index`
  (여섯 — 위 표기 「다섯」을 「여섯」으로 정정, 손으로 세다 하나 빠뜨렸다).
- `scripts/_gate_header.py::SELF_TEST_LINKS` 에 `scripts/verify_spec_ap_n4.py` →
  `backend/tests/test_ap_n4_gate_can_fail.py` 등록 줄 필요.
- 대장 이동: 위 §1 아홉 건을 `status: 구현 · kind: closed` 로, §2 둘은 그대로
  `미착수`(반쪽이므로 승격하지 않는다).
