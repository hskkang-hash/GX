# DSM-U2-05 — 사람이 확인한 제목 부분 표

P-431 · **손으로만 고친다** — 시험·쓰개가 이 파일을 쓰면 반쪽 게이트가 빨강이다.
기계 실측(요청/응답)은 옆 파일 `DSM-U2-05.json` 이다. 아래 json 블록 하나가 정본이다.

```json
{
  "id": "DSM-U2-05",
  "title_parts": [
    {
      "part": "인계 메모(선행 조건) 자동 초안·저장",
      "where": "backend/apps/dsm/handover_service.py::build_draft / save (UX-34, 이전 턴 구현)",
      "status": "measured — 이 턴 이전부터 존재, DsmHandover 행으로 저장됨(evidence latest_after_ack.body 에서 자동 초안 문구 확인)"
    },
    {
      "part": "특정 시간대(08~09시) 인계 창",
      "where": "backend/apps/dsm/handover_service.py (파일 전문 — build_draft 는 hours 롤링 창만 받고, 시각(00~24) 제약 코드 없음)",
      "status": "없음 — '08~09시'를 강제하는 코드가 없다. 아무 때나 ack 가능(관행 서술일 뿐 검증 로직 아님, 코드 전문 확인)"
    },
    {
      "part": "팀장이 「확인」 체크(ack)",
      "where": "backend/apps/dsm/handover_service.py::acknowledge (POST /api/dsm/handover/{id}/ack)",
      "status": "measured: evidence — ack 후 latest().acknowledged 가 true 로 바뀌는 것을 같은 시험에서 재확인(test_p356_u2_spec_promotions.py)"
    },
    {
      "part": "홈 카드 「인계 확인 ✓」 UI",
      "where": "backend/apps/dsm/handover_service.py::latest 함수 docstring 234행 '★ 화면에 그리는 것은 F 차선의 몫이다 — 여기서는 라우트와 응답만 연다'; frontend/src 전수 grep — DSM 교대인계(DsmHandover) 카드를 그리는 화면 없음(매칭된 'handover ack' 프런트 2건은 무관한 인사/근무 Handover 기능(features/Handover/...)이다)",
      "status": "없음 — 백엔드는 acknowledged 플래그를 내려줄 뿐, 그 값을 읽어 체크 표시를 그리는 DSM 홈 카드 코드가 없다"
    },
    {
      "part": "완결 조건 「감사」",
      "where": "backend/apps/dsm/handover_service.py::acknowledge → audit_writer.write(logger_name=_ACK_LOGGER_NAME)",
      "status": "measured: ack 마다 audit_writer 감사 줄 1건(evidence ack_id=397)"
    }
  ]
}
```
