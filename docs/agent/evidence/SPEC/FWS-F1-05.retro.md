# FWS-F1-05 — 사람이 확인한 제목 부분 표

P-431 · **손으로만 고친다** — 시험·쓰개가 이 파일을 쓰면 반쪽 게이트가 빨강이다.
기계 실측(요청/응답)은 옆 파일 `FWS-F1-05.json` 이다. 아래 json 블록 하나가 정본이다.

```json
{
  "id": "FWS-F1-05",
  "title_parts": [
    {
      "part": "확인 요청 상세 조회(K1 이벤트를 '확인 요청'으로 GET)",
      "where": "backend/apps/fws/verification.py::get_verification — GET /api/fws/verifications/{id}",
      "status": "measured: F1_05_06_VerificationTest.test_verification_detail_and_fire_confirmed_reply — verification_id 실측"
    },
    {
      "part": "카메라 스냅샷 경로(사진)",
      "where": "backend/apps/fws/verification.py:51-62 snapshot_path",
      "status": "measured: snapshot_path='minio://dsm/1.jpg' 응답에 실림"
    },
    {
      "part": "위치(lat/lng/address)",
      "where": "backend/apps/fws/verification.py:56-58 · backend/tests/test_fws_f3a.py:271 (다른 시험에서 lat=36.351,lng=127.381 로 실제 채워 전달)",
      "status": "measured: 필드 자체는 K1 record_detection의 lat/lng/address 를 그대로 전달하고 다른 시험(test_fws_f3a.py)에서 실제 좌표로 채워지는 것을 확인 — 다만 FWS-F1-05 자신의 evidence(docs/agent/evidence/SPEC/FWS-F1-05.json)에 찍힌 실제 응답은 lat:null,lng:null,address:null(픽스처가 좌표를 안 줌)이라 이 절 자체의 실측 인스턴스는 빈 값이다"
    },
    {
      "part": "거리(관측자↔사건 거리)",
      "where": "backend/apps/fws/verification.py::get_verification 응답 스키마(전체) — 비교: backend/apps/fws/office.py:49-58 하버사인 거리 계산(F3-04 전용)",
      "status": "없음: office.py에 하버사인 거리 계산이 있지만 그것은 F3(산림과 담당)가 '가장 가까운 감시원'을 고르는 용도이고, F1-05 GET /verifications/{id} 응답에는 거리 필드가 전혀 없다 — 감시원 화면이 볼 수 있는 '거리'가 없다"
    },
    {
      "part": "지도(위치를 지도에 표시)",
      "where": "backend/apps/fws/verification.py:47-49 머리말 — §0.4 금지구역(MapForRoute/FormRoute) 밖이라 좌표 값만 낸다고 명시",
      "status": "부분: 좌표 값은 서버가 내주지만(위 항목 참고), 그 값을 실제로 그릴 F1 화면이 없다 — frontend 전체에서 fwsEndpoint.verification(GET) 을 부르는 페이지가 0건(OfficeHome.tsx는 F3용 reply만 재사용, F1 조회 화면 없음)"
    },
    {
      "part": "확인 요청 '수신'(발송→도달) 자체 — 관제가 K2로 보낸 요청이 감시원에게 실제로 도달하는가",
      "where": "backend/tests/test_fws_app.py:280-296 (F1_05_06_VerificationTest) — 이미 존재하는 event_id를 알고 바로 GET",
      "status": "없음: F1-05 시험은 이벤트 id를 픽스처로 미리 알고 바로 GET한다 — K2 send()로 실제 발송돼 도달하는지는 이 시험이 재지 않는다(F1-10 시험만 도달·확인을 잰다). '확인 요청 수신'의 '수신(도달)' 절반이 미실측"
    }
  ]
}
```
