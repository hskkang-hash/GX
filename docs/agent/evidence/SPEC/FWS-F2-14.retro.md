# FWS-F2-14 — 사람이 확인한 제목 부분 표

P-431 · **손으로만 고친다** — 시험·쓰개가 이 파일을 쓰면 반쪽 게이트가 빨강이다.
기계 실측(요청/응답)은 옆 파일 `FWS-F2-14.json` 이다. 아래 json 블록 하나가 정본이다.

```json
{
  "id": "FWS-F2-14",
  "title_parts": [
    {
      "part": "등짐펌프(backpack_pump) 점검 체크",
      "where": "backend/apps/fws/equipment.py:check · POST /api/fws/equipment/checks?equipment_type=backpack_pump",
      "status": "measured: tests.test_fws_f2.F2_14_EquipmentCheckTest.test_check_is_recorded_and_read_back — equipment_type=\"backpack_pump\",equipment_code=\"BP-7\",result=\"pass\" POST 뒤 GET mine 에서 그대로 재조회(SPEC/FWS-F2-14.json)"
    },
    {
      "part": "진화차(fire_truck) 점검 체크",
      "where": "backend/apps/fws/equipment.py:check — equipment_type 은 자유 문자열(41-44행), 닫힌 목록이 아님",
      "status": "measured: 코드가 equipment_type 을 자유 문자열로 받는다고 명시적으로 설계함(머리말 38-40행 「등짐펌프·진화차는 명세서의 예시이지 전체 목록이 아니다」) — 같은 검증 경로(빈 문자열만 거절)를 backpack_pump 로 실측했고 fire_truck 값 자체의 전용 HTTP 요청은 없음"
    },
    {
      "part": "점검 1(완결조건 — 명세서 §5.2 169행)",
      "where": "backend/apps/fws/equipment.py:mine (count) · GET /api/fws/equipment/checks/mine",
      "status": "measured: 같은 시험 — mine_body[\"count\"]==1, 방금 남긴 equipment_code=\"BP-7\" 재조회로 확인"
    }
  ]
}
```
