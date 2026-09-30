# FWS-F1-13 — 사람이 확인한 제목 부분 표

P-431 · **손으로만 고친다** — 시험·쓰개가 이 파일을 쓰면 반쪽 게이트가 빨강이다.
기계 실측(요청/응답)은 옆 파일 `FWS-F1-13.json` 이다. 아래 json 블록 하나가 정본이다.

```json
{
  "id": "FWS-F1-13",
  "title_parts": [
    {
      "part": "서버 쪽 재전송 중복 제거(Idempotency-Key) — 같은 키로 두 번 보내도 근무 기록이 1건",
      "where": "backend/common/idempotency.py::idempotent · backend/apps/fws/api.py:50 @idempotent('fws.patrol.checkin') · POST /api/fws/patrol/checkin",
      "status": "measured: F1_13_OfflineReplayTest.test_replayed_checkin_with_same_key_is_not_double_counted — 같은 Idempotency-Key 두 번 전송 뒤 patrol/mine.today.checkins=1 실측"
    },
    {
      "part": "프런트 오프라인 큐 — 통신 불가 시 localStorage에 쌓고 'online' 복귀 시 같은 키로 재전송",
      "where": "frontend/src/features/fws/offlineQueue.ts:25-89 (readQueue/writeQueue/checkinOrQueue/flushQueue/installAutoFlush)",
      "status": "present: 코드가 실제로 존재하고 로직이 일관됨(같은 idempotency 키 재사용, 성공한 것만 큐에서 제거) — 다만 이 파일을 직접 재는 프런트 자동 시험은 0건(find/grep 결과 *.test.*·*.spec.* 어디에도 offlineQueue 없음), 코드 확인으로만 닫음"
    },
    {
      "part": "순찰 트랙(track)도 오프라인 큐에 실제로 쌓이는가(큐는 checkin·track 둘 다 지원한다고 선언)",
      "where": "frontend/src/features/fws/offlineQueue.ts:20 QueuedPatrolAction.kind: 'checkin' | 'track' — 그러나 kind:'track' 을 실제로 넣는 호출부는 0건(PatrolHome.tsx는 checkinOrQueue만 부름)",
      "status": "없음: 큐 자료구조는 'track'을 지원하도록 선언돼 있지만, 어떤 화면도 순찰 트랙 요청을 큐에 넣지 않는다 — track에 대한 오프라인 큐잉은 죽은 코드"
    },
    {
      "part": "'서비스워커'로 구현되는가(원 명세서 §5.1 표의 구현 칸 원문)",
      "where": "원 명세서:148행 'FWS-F1-13 … | FM1 | 서비스워커 | 복귀 시 전송 N' vs frontend/src/features/fws/offlineQueue.ts:83-89 installAutoFlush() — window.addEventListener('online', …) 사용, service worker 파일(grep 'serviceWorker' 결과 frontend/src/features/mobile/push.ts·MobileShell.tsx 둘 뿐, fws 쪽 0건)",
      "status": "대리: 원 명세서는 '서비스워커'를 구현 수단으로 적었지만 실제로는 브라우저 탭이 열려 있을 때만 동작하는 window 'online' 이벤트 리스너 + localStorage다 — 탭이 닫힌 채 복귀하면 재전송되지 않는다(진짜 Service Worker의 Background Sync와 다른 약한 대안)"
    }
  ]
}
```
