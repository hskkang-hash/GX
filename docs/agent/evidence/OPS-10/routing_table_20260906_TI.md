# OPS-10 — 경보 발송처 표 (2026-09-06 20:44:17)

**이 파일은 `scripts/ops_alert_routing.py` 가 실행하며 적었다.**
표의 사람·수는 K2 커널(`resolve_recipients`)이 답한 그대로다 —
판정식을 복제하지 않았다(D-369).

## 1. 발송처 표 — **누구에게**

| 소속 | 등급 | 역할 | 채널 | 사람에게 도달 | 받는 사람 수 | 그중 **주소가 살아 있는** 사람 | 받는 사람 |
|---|---|---|---|---|---|---|---|
| 4(ETRI-Group) | critical | fire_admin | log | **✗ 로그로만 간다** | 1 | 0 | gxseed_u2_manager |
| 4(ETRI-Group) | critical | fire_user | log | **✗ 로그로만 간다** | 1 | 0 | gxseed_u1_operator |
| 4(ETRI-Group) | critical | operator | log | **✗ 로그로만 간다** | 12 | 12 | oper_chi, oper_chungnam, oper_geumsan, operation_chungnam_001, operation_cn_001, operator_chi, operator_user, operator_user_1, operator_user_2, operator_user_3, operator_user_4, operator_user_5 |
| 4(ETRI-Group) | critical | view_only_-_anyang | log | **✗ 로그로만 간다** | 1 | 0 | gxseed_u4_official |
| 4(ETRI-Group) | info | fire_user | log | **✗ 로그로만 간다** | 1 | 0 | gxseed_u1_operator |
| 4(ETRI-Group) | info | operator | log | **✗ 로그로만 간다** | 12 | 12 | oper_chi, oper_chungnam, oper_geumsan, operation_chungnam_001, operation_cn_001, operator_chi, operator_user, operator_user_1, operator_user_2, operator_user_3, operator_user_4, operator_user_5 |
| 4(ETRI-Group) | warning | fire_admin | log | **✗ 로그로만 간다** | 1 | 0 | gxseed_u2_manager |
| 4(ETRI-Group) | warning | fire_user | log | **✗ 로그로만 간다** | 1 | 0 | gxseed_u1_operator |
| 4(ETRI-Group) | warning | operator | log | **✗ 로그로만 간다** | 12 | 12 | oper_chi, oper_chungnam, oper_geumsan, operation_chungnam_001, operation_cn_001, operator_chi, operator_user, operator_user_1, operator_user_2, operator_user_3, operator_user_4, operator_user_5 |

★ 「받는 사람 수」와 「주소가 살아 있는 사람」이 다른 이유: 시드 사람의 주소는
  `@seed.invalid` 다(RFC 2606 — 절대 존재하지 않는 TLD). **주소가 있다**와
  **사람이 받는다**는 다른 사실이고, 뒤엣것이 0이면 채널을 `email` 로 바꿔도
  이력은 전부 실패 행이 된다 — 그것은 배선의 사실이 아니라 환경의 사실이다.

## 2. 덮이지 않은 자리 — **아무 규칙도 없는 등급**

  없다 — 모든 등급에 규칙이 하나 이상 있다.

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

### 이메일 채널 — **보낼 수 있는 모양인가** [실측]

  · SMTP 설정: **미설정(회색)**
  · 사유: SMTP 미설정 — EMAIL_HOST, EMAIL_HOST_USER, EMAIL_HOST_PASSWORD, DEFAULT_FROM_EMAIL 이(가) 자리 표시자 그대로다. 값은 로컬 `.env` 로만 준다(저장소에 넣지 않는다 · D-204). 백엔드=django.core.mail.backends.smtp.EmailBackend

  · **채널을 켜면 메일이 날아갈 도메인** [실측] (규칙이 고른 사람 기준 · 중복 포함):
      yopmail.com      24
      org.kr           12
      seed.invalid     6  ← 도달 불가(RFC 2606). 시드 사람이다

  ⚠ **이 표를 읽고 채널을 켜라.** 「수신 주소가 없다」가 아니다 — 규칙이 고르는
    사람 중 상당수는 **이미 도달 가능한 주소를 갖고 있다**(개발 계정). 채널을
    `email` 로 바꾸는 순간 그들에게 **진짜로** 메일이 나간다. 대표에게만 보내려면
    주소를 넣는 것이 아니라 **규칙이 고르는 역할을 먼저 좁혀야 한다.**
    주소가 0개일 것이라고 짐작하고 켜는 것이 이 절의 가장 큰 사고 가능성이다.

  SMTP 자격증명과 수신 주소는 **저장소에 오지 않는다**(D-204). 로컬 `.env` 로만 온다:
  `EMAIL_HOST` · `EMAIL_HOST_USER` · `EMAIL_HOST_PASSWORD` · `DEFAULT_FROM_EMAIL` ·
  `K2_ALERT_EMAIL_TO` · `K2_ALERT_CHANNEL`. 이름은 `backend/.env.example` 에 있다.

  ★ **지금 상태는 「발송까지 · 수신 대기」다.** 어댑터는 서 있고(⑤), 세 등급 전부에
    규칙이 있고(⑥), 남은 것은 **저장소 밖에서 오는 값 둘**이다:
      ㉠ SMTP 자격증명 (`.env` — 지금 자리 표시자 그대로다)
      ㉡ 대표가 줄 **수신 주소**, 그리고 그 주소만 받게 할 것인지의 결정
    ㉡이 결정이라는 것이 위 도메인 표의 뜻이다 — 주소는 이미 있고, 문제는
    **누가 받을 것인가**다. 둘이 오면 고칠 자리는 한 줄이다:

    ```
    K2_ALERT_CHANNEL=email  python manage.py seed_alert_routing --user gxprobe_e2e
    ```

  ⚠ **발송 기록은 증거가 아니다.** `DeliveryRecord` 행이 생겼다는 것은 「보냈다」이지
    「받았다」가 아니다. 이 절을 닫는 증거는 **사람이 실제로 받은 수신함 캡처**
    하나뿐이다 — 그 캡처가 오기 전까지 이 절의 상태는 「구현」이 아니라
    **「발송까지 · 수신 대기」**로 적는다.

## 4. 판정

  OK   ① 표를 세웠는가        규칙 9줄을 폈다
  OK   ② 닿는 사람 0명       모든 규칙에 받을 사람이 있다
  OK   ③ 미구현 채널         규칙이 가리키는 채널이 전부 등록돼 있다
  FAIL ④ 사람에게 도달        **모든 규칙이 `log` 다 — 사람에게 도달하는 경보가 0건이다.** 배선은 살아 있고 **주소가 오면 채널 한 칸으로 켜진다**: `manage.py seed_alert_routing --channel email`
  OK   ⑤ 이메일 어댑터        `email` 어댑터가 등록돼 있고 사람에게 도달하는 채널이다 — 규칙의 채널 한 칸을 바꾸는 것으로 켜진다
  OK   ⑥ 등급 전수          등급 3종 전부에 규칙이 있다

판정 **실패**.
④가 빨간 것은 **배선의 결함이 아니라 수신 주소 대기**다. ⑤가 초록이면 어댑터는
서 있고, ⑥이 초록이면 규칙이 빠진 등급도 없다 — 남은 것은 주소 하나이고,
그 하나는 저장소가 아니라 사람이 준다. **그래서 이 절은 「발송까지 · 수신 대기」다.**
문자·카톡·앱은 여전히 대표 결정 대기이고(DA-04 D4-1), 이번 턴에 만들지 않았다.
