# FWS-F1-02 — 사람이 확인한 제목 부분 표

P-431 · **손으로만 고친다** — 시험·쓰개가 이 파일을 쓰면 반쪽 게이트가 빨강이다.
기계 실측(요청/응답)은 옆 파일 `FWS-F1-02.json` 이다. 아래 json 블록 하나가 정본이다.

```json
{
  "id": "FWS-F1-02",
  "title_parts": [
    {
      "part": "GPS 트랙 포인트가 누적 카운트된다(track_count)",
      "where": "backend/apps/fws/patrol.py::track — POST /api/fws/patrol/track?lat=...&lng=...",
      "status": "measured: F1_02_TrackTest.test_gps_point_and_checkpoint_pass_are_counted_separately — track_count=1 실측"
    },
    {
      "part": "전자순찰함(체크포인트) 통과가 GPS 트랙과 별도 칸으로 카운트된다(checkpoint_count)",
      "where": "backend/apps/fws/patrol.py::track — POST /api/fws/patrol/track?checkpoint_code=CHK-3",
      "status": "measured: 같은 시험 — checkpoint_count=1, track_count는 그대로 1(섞이지 않음)"
    },
    {
      "part": "순찰함 코드가 실재 등록된 순찰함 목록과 대조되는가(위조 NFC 코드 방지)",
      "where": "backend/apps/fws/patrol.py::track — checkpoint_code는 트림만 하고 그대로 저장",
      "status": "없음: checkpoint_code는 임의 문자열을 그대로 받아들인다 — 순찰함 레지스트리·유효성 검증이 없다(어떤 문자열을 보내도 '통과'로 집계됨)"
    },
    {
      "part": "화면(F1 감시원 화면)에서 실제로 GPS 트랙/NFC 통과를 전송하는 자리",
      "where": "frontend/src/features/fws/pages/PatrolW2aCards.tsx::data-gx=\"fws-f1-02-gps\"(이 기기 위치 한 점) · data-gx=\"fws-f1-02-checkpoint-code\" + data-gx=\"fws-f1-02-checkpoint\"(순찰함 번호 입력 · NFC 실기기 읽기는 없음) · data-gx=\"fws-f1-02-post\" — PatrolHome.tsx 에 마운트 · POST /api/fws/patrol/track 뒤 GET /api/fws/patrol/mine 재조회(fws-f1-11-table)",
      "status": "measured: tests.test_aq_w2a_field_screens.F1_02_TrackScreenTest.test_gps_and_checkpoint_press_then_refetch_mine — GPS 1점·순찰함 1건 POST 뒤 새 GET 재조회 today.tracks=1·checkpoints=1 · 남의 테넌트 0 · 화면 정적 대조 test_screen_sends_track_and_refetches"
    }
  ],
  "retro": "턴 AQ 차선 W2A · 화면 배선 · 사람 확인 — 화면 전송 칸은 닫았다. 순찰함 등록 목록 대조(위조 코드 방지) 행은 등록 목록이 코드에 없어 열린 채 둔다"
}
```
