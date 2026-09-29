# O-01 대행 호출 재확인 — P-427 ⑤ (턴 AP · 차선 N3)

**질문(턴 AO 청구 ⑤ · `docs/workorders/WO-GX-20260930-18_report.md` 끝 문단)**:
`backend/apps/dsm/ops_an_service.py::issue_tenant()` 가 U0 요청의
`Authorization` 헤더를 안쪽 `POST /api/v1/user/create-user` 호출에 그대로
물려준다(대행 호출). 턴 AO 는 "이미 인증된 U0 의 대행 · 새 구멍 아님"이라
판단했지만, **그 판단이 자격의 나이를 묻지 않았다** — 가로챈 지 오래된
Authorization 헤더도 안쪽 호출을 그대로 지날 수 있었다.

## 재확인 표 (셋)

| # | 물음 | 판정 | 근거(코드·시험) |
|---|---|---|---|
| ① | **U0 만 이 문을 여는가** | 그대로 참(안 바뀜) | `ops_an_service._require_operator()` — `issue_tenant()` 첫 줄. `PlatformOperatorGateTest`(`tests/test_ops_an.py`)가 U0 아니면 403 임을 이미 실측 |
| ② | **감사 줄이 1개 남는가**(성공·거절 각각) | 참 — 이 턴이 「거절」쪽 줄을 더함 | 성공: `_audit(..., "issue", ...)`(기존). 거절: `_audit(..., LOG_TENANTS_PROXY_DENIED_ACTION="issue_denied_stale_proxy", ...)`(신설). 시험: `test_ap_n3_o01_proxy.py::O01ProxyFreshnessTest.test_fresh_token_still_issues_tenant` · `::test_stale_token_is_rejected_with_403_and_audited` |
| ③ | **시간 제한(15분)이 실제로 걸리는가** | 참 — 이 턴이 신설 | `ops_an_service.PROXY_FRESHNESS_LIMIT_SECONDS = 900` · `_forwarded_auth_age_seconds()` 가 JWT `iat` 를 읽어 나이를 재고, `issue_tenant()` 가 900초 초과면 `OpsAnPermissionDenied`(403, 테넌트 미생성)로 거절한다. 시험: `test_ap_n3_o01_proxy.py::O01ProxyFreshnessTest.test_stale_token_is_rejected_with_403_and_audited`(20분 된 자격 → 403 · 테넌트 미생성 · 감사 줄 확인) · `::test_freshness_helper_reads_real_iat`(도우미 함수 자체가 5분 된 토큰의 나이를 옳게 잰다) |

## 결론

턴 AO 의 "새 구멍 아님" 판단은 **자격이 살아 있는 동안(최대 200분,
`NINJA_JWT.ACCESS_TOKEN_LIFETIME`) 전체를 대행 창으로 열어 둔다**는 뜻이었다
— 그 창이 이 턴 전까지는 안 좁혀져 있었다. 이 턴은 그 창을 **15분**으로
좁혔다(코드는 `PROXY_FRESHNESS_LIMIT_SECONDS`). U0 이 이 절을 부르기 15분
이내에 로그인(또는 토큰 재발급)했을 때만 대행이 선다 — 그보다 오래된
Authorization 헤더는 전체 요청 인증(`JwtOrInboundKey()`)은 통과해도(서명·
`exp` 는 여전히 유효할 수 있으므로), **대행 자체는 거절**된다.

거절된 시도는 테넌트를 만들지 않고(반쯤 만든 테넌트를 남기지 않는다 —
`UserGroup` 생성 전에 신선도부터 확인), 감사에 「거절됐다」는 사실 한 줄을
남긴다.

## 남는 것 — 정직하게 적는다

- 이 제한은 **U0 자신의 세션**을 건드리지 않는다(로그아웃시키지 않는다) —
  대행에 쓰는 것만 막는다. U0 이 다시 같은 요청을 보내려면 재로그인해
  새 액세스 토큰을 받아야 한다(리프레시 토큰 재사용도 `iat` 를 다시 찍으므로
  통과한다).
- 15분이라는 수는 이 턴의 세종 판정(WO-19 §5 P-427 ⑤ 「시간 제한(15분)」)을
  그대로 옮긴 것이다 — 이 코드가 스스로 고른 수가 아니다.
- 더 넓은 질문("이 대행 패턴 자체를 없애고 별도 서비스 계정으로 바꿀지")은
  이 턴 범위 밖이다 — 여전히 대행이지만, 그 대행의 창을 좁혔을 뿐이다.
