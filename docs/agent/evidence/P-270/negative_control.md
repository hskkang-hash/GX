# P-273 음성 대조 실측 (턴 AF · 차선 S · 2026-09-23)

## ① 순수 판정기(judge_rows) 자기시험 — --self-test 출력 그대로

```
[P-273] [입력] 자기시험 facts 3개(흉내 · 실제 라우트 0개) — 도커·DB 없이 판정 규칙(judge_rows)만 잰다
[P-273] AS=**없는 토큰**(Bearer gx.nonexistent.probe.token.do-not-issue-this) · SOURCE=자기시험 흉내 facts(레지스트리 아님) · MEASURED=judge_rows() 순수 함수 하나
[P-273] 자기시험 통과 — 정상 갈래 2(401 · 공개선언) · 음성 대조 1(★ auth= 없는 자리를 빨강으로 잡았다: ['/api/fake/no-auth-oops'])
```

## ② 실제 364행(진짜 레지스트리) + 흉내 낸 「auth= 없는 자리」 1행을 섞은 대조

실행: gx-shell 안에서 `gate_fake_bearer_regression.collect_rows()` 로 얻은 **진짜**
364행에, `auth=` 가 빠졌다고 흉내 낸 가짜 행 하나(`/api/fake/no-auth-planted-by-
negative-control`, `data=True`)를 코드로 섞어 넣고 같은 `judge_rows()` 를 두 번 불렀다.

```
진짜 실측 행 수: 364

=== BEFORE(진짜 364행만) ===
leaked: 0 -> 게이트 판정: 초록

=== AFTER(가짜 누출 행 1개를 섞음) ===
leaked: 1 -> 게이트 판정: **빨강**
  · GET /api/fake/no-auth-planted-by-negative-control 200 ★ 음성 대조 — auth= 를 뺐다고 흉내 낸 자리(실제 라우트 아님, 섞어 넣은 행)

[결론] 진짜 실측(364행)은 초록이었고, auth= 없는 자리를 하나 섞자 게이트가
정확히 그 한 행만 빨강으로 잡았다 — 회귀 게이트가 실제로 작동한다.
```

## ③ 시도했으나 포기한 방법 — 실제 라이브 라우트의 `auth_callbacks` 런타임 제거

`/api/article` GET 오퍼레이션의 `op.auth_callbacks` 를 프로세스 메모리에서
`[]` 로 지워 "auth= 를 방금 뺐다"를 흉내 내려 했다. 결과: BEFORE/AFTER 모두
**500**(가짜 토큰이 JWT 모양이 아니라 `CustomJWTAuth` 가 디코드 예외를 던지고,
그 예외가 `auth_callbacks` 유무와 무관하게 **같은 자리에서** 잡혔다 — ninja_extra
의 디스패치가 `Operation.auth_callbacks` 를 실행 중에 다시 읽지 않는 것으로
보인다). 즉 이 레버는 신뢰할 수 없었다 — 그래서 ①②(순수 함수 + 실제 facts에
섞기)로 방향을 바꿨다. 이 시도 자체도 "내가 틀렸던 것"에 적는다.
