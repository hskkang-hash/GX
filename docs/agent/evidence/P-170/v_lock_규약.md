# P-170 ① — V 단독 세션 잠금 규약 (2026-09-18 · 턴 U · 조율자)

「**재는 동안 아무도 로그인하지 않는다**」를 사람의 기억이 아니라 **파일 하나**로 세운다.
턴 T 에 조율자가 V 측정 중 `verify_ga_readiness` 를 돌려 V 의 세션을 빼앗았다(D-487) — 그 자리를 막는다.

## 무엇이 생겼나

| 자리 | 잠겼을 때 하는 일 |
|---|---|
| `scripts/v_lock.py` | `--lock` / `--unlock` / `--status` / `--self-test`. LOCK 은 `docs/agent/evidence/V_LOCK`(커밋 안 함) |
| `verify_route_alive.login` | 토큰을 안 받고 `None` — 판정기는 「못 받았다」(회색) |
| `verify_ga_readiness.run_gate` | **직렬 묶음**(로그인하는 판정기 전부: sidebar · route_alive · contract_route_reach · screens · write_auth · seed_roles · authn_paths · feature_reach)을 **부르지 않고** exit 2(회색 · 「V 단독 중 · 재지 않음」). 실행 머리에도 한 줄 경고 |
| `probe_read_surface.Client.login` | SystemExit — 회색으로 끝난다 |
| `gate_env.probe_session` | 묻지 않는다(`end_previous_session:false` 라 세션은 안 끊지만 **율제한 5회/분은 먹는다**) → `session` MISSING |
| `probe_tenant_isolation` | SystemExit 회색 |

## 규칙 넷

1. **잠근 사람만 지나간다.** V 는 `--lock` 이 출력한 세션 id 를 `GX_V_SESSION_ID` 로 자기 도구에 준다 —
   그러면 V 의 캡처·걷기·click_completes·feature_reach·온보딩 측정은 막히지 않는다.
2. **깨진 LOCK 은 잠긴 것으로 본다** — 모르면 안 재는 쪽. 읽을 수 없는 파일이 통과 사유가 되면 안 된다.
3. **안 지운 LOCK 은 회색으로 드러난다.** 다음 게이트가 「V 단독 중」이라고 말한다 — 조용히 초록이 되는 것보다 낫다.
4. **회색은 초록이 아니다.** 잠긴 동안 그 게이트는 **잰 것이 아니다** — 보고에 「V 단독 중 회색 N」으로 적는다.

## V 가 이번 턴 돌릴 순서 (조율자가 병합을 끝낸 뒤)

    # 0. 잠근다 — 출력된 세션 id 를 아래 모든 명령 앞에 GX_V_SESSION_ID 로 준다
    PYTHONIOENCODING=utf-8 python scripts/v_lock.py --lock
    #    → [V_LOCK] 잠금 — 시작 … · 세션 <ID>
    export GX_V_SESSION_ID=<ID>

    # 1. 로그인 4/4 → 걷기(S4·S5 + S1 회귀) → FC 48 → 온보딩 35행 → 캡처 append → feature_reach
    #    (각 도구의 명령은 차선 Q·U1 이 낸 「V 가 돌릴 명령」 절을 따른다 — 씨앗은 P-170 ② 파이프)

    # 2. 끝나면 **조율자가** 푼다
    PYTHONIOENCODING=utf-8 python scripts/v_lock.py --unlock
    PYTHONIOENCODING=utf-8 python scripts/v_lock.py --status      # 안 잠김 이어야 한다

## 조율자의 약속 (이 40분 동안)

브라우저를 열지 않는다 · 게이트를 돌리지 않는다 · 어떤 계정으로도 로그인하지 않는다.
할 일이 있으면 **읽기**(코드·대장·로그)와 **문서 쓰기**뿐이다.
