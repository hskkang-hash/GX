# OPS-10 — 경보 발송처 표 (2026-09-04 13:48:15)

**이 파일은 `scripts/ops_alert_routing.py` 가 실행하며 적었다.**
표의 사람·수는 K2 커널(`resolve_recipients`)이 답한 그대로다 —
판정식을 복제하지 않았다(D-369).

## 1. 발송처 표 — **누구에게**

| 소속 | 등급 | 역할 | 채널 | 사람에게 도달 | 받는 사람 수 | 받는 사람 |
|---|---|---|---|---|---|---|
| 4(ETRI-Group) | critical | fire_admin | log | **✗ 로그로만 간다** | 1 | gxseed_u2_manager |
| 4(ETRI-Group) | critical | fire_user | log | **✗ 로그로만 간다** | 0 | **아무도 없다** |
| 4(ETRI-Group) | critical | operator | log | **✗ 로그로만 간다** | 12 | oper_chi, oper_chungnam, oper_geumsan, operation_chungnam_001, operation_cn_001, operator_chi, operator_user, operator_user_1, operator_user_2, operator_user_3, operator_user_4, operator_user_5 |
| 4(ETRI-Group) | critical | view_only_-_anyang | log | **✗ 로그로만 간다** | 1 | gxseed_u4_official |

## 2. 덮이지 않은 자리 — **아무 규칙도 없는 등급**

  · 4(ETRI-Group) / `info` — 이 등급의 이벤트는 **아무에게도 가지 않는다**
  · 4(ETRI-Group) / `warning` — 이 등급의 이벤트는 **아무에게도 가지 않는다**

  ★ 이것이 결함인지 결정인지는 이 판정기가 정하지 않는다. `info`·`warning` 을
    알리지 않기로 한 것이라면 그 결정이 어디에도 안 적혀 있다는 뜻이고,
    적혀 있지 않은 결정은 **잊힌 자리**와 구별되지 않는다(D-264).

## 3. **어떤 경로로** — 채널의 지금 상태

| 채널 | 상태 | 사람에게 도달 | 사유 |
|---|---|---|---|
| `email` | 등록됨 | ○ | 어댑터가 있다 |
| `log` | 등록됨 | ✗ (로그로만) | 어댑터가 있다 |
| `push` | **미구현** | — (보낼 수 없다) | 발송 업체 미선정 (DA-04 D4-1). 앱 푸시는 모바일 클라이언트 배포와 함께 온다. |
| `sms` | **미구현** | — (보낼 수 없다) | 발송 업체 미선정 (DA-04 D4-1 · 계약·비용 사안). WP-DA2b ENTRY 까지 판단 대기. |
| `webhook` | **미구현** | — (보낼 수 없다) | 수신 URL 의 테넌트 소유 판정과 서명키 보관이 선행 — K1.subscribe 와 같은 선행이다. |

★ `log` 는 **사람이 아니라 로그에 도달한다**(`k2_notify.channels.NON_HUMAN`).
  검수 환경에 도달할 수신자가 없고 업체도 미정(DA-04 D4-1)이라 메일로 보내면
  이력이 **전부 실패 행**이 된다 — 그것은 배선의 사실이 아니라 환경의 사실이다.

## 4. 판정

  OK   ① 표를 세웠는가        규칙 4줄을 폈다
  FAIL ② 닿는 사람 0명       규칙은 있는데 **받을 사람이 0명**: 4(ETRI-Group)/critical/fire_user
  OK   ③ 미구현 채널         규칙이 가리키는 채널이 전부 등록돼 있다
  FAIL ④ 사람에게 도달        **모든 규칙이 `log` 다 — 사람에게 도달하는 경보가 0건이다.** 배선은 살아 있고 수신 채널만 미정이다(DA-04 D4-1)

판정 **실패**.
④가 빨간 것은 **배선의 결함이 아니라 대표 결정 대기**다(DA-04 D4-1). 그 결정이
오면 고칠 자리는 규칙의 `channels` 한 칸이고, ①②③이 초록이면 그 한 칸을 바꾸는
것만으로 사람에게 간다 — 그것을 미리 확인해 두는 것이 이 표의 값이다.
