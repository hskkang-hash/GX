# DSM-U3-04 — 사람이 확인한 제목 부분 표

P-431 · **손으로만 고친다** — 시험·쓰개가 이 파일을 쓰면 반쪽 게이트가 빨강이다.
기계 실측(요청/응답)은 옆 파일 `DSM-U3-04.json` 이다. 아래 json 블록 하나가 정본이다.

```json
{
  "id": "DSM-U3-04",
  "title_parts": [
    {
      "part": "상황실 번호 저장/조회",
      "where": "backend/apps/dsm/hotline_service.py::set_hotline / latest_hotline (POST|GET /api/dsm/hotline)",
      "status": "measured: evidence body.situation_room_phone='031-120-2222' 저장·응답 확인"
    },
    {
      "part": "PS-LTE 그룹통화 번호 저장/조회",
      "where": "backend/apps/dsm/hotline_service.py::set_hotline / latest_hotline",
      "status": "measured: evidence body.pslte_group_call='*911' 저장·응답 확인"
    },
    {
      "part": "M2 화면 버튼(번호가 있을 때만 렌더)",
      "where": "frontend/src/features/mobile/pages/MobileEventDetail.tsx 758~777행 (hotline.data.configured 로 게이트, tel: 버튼 렌더)",
      "status": "present — 프런트 코드가 실재한다. situation_room_tel/pslte_group_call_tel 값이 있을 때만 버튼을 그리는 것을 코드로 확인(2026-09-28 턴 AM 추가분)"
    },
    {
      "part": "완결 조건 「1탭」(tel: 링크 1회 클릭으로 다이얼)",
      "where": "frontend/src/features/mobile/pages/MobileEventDetail.tsx 763~776행 <a href={`tel:${...}`}>",
      "status": "present — tel: 앵커 1개가 곧 1탭 다이얼이다. hotline_service.py::to_tel() 이 공백·하이픈을 떼 유효한 tel URI를 만든다"
    }
  ]
}
```
