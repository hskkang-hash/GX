# P-68 · mailpit 로컬 SMTP 수신함 — 「발송 → 도착」 기계 실측

- 날짜: **2026-09-06** (턴 G · 차선 E)
- 판정 근거: 세종(CPO) P-68
- 대상: `docker-compose.yml` 의 `mailpit` 서비스(신규) · `backend/kernels/k2_notify/channels.py::EmailChannel`(기존, 수정 없음)

---

## ⛔ 먼저 — **이 문서는 OPS-10 을 닫지 못한다**

여기서 잰 것은 정확히 이만큼이다:

> Django 의 `EMAIL_*` 설정 → SMTP 소켓 → 우리가 세운 수신함이 메시지로 파싱 → HTTP API 로 되읽기

이 구간이 **살아 있다**는 것은 실물로 확인됐다. 그러나 **닫히지 않는 것**이 더 많다:

1. **받은 것은 우리가 세운 통이다.** mailpit 은 인증도 검사도 없이 무엇이든 받아 삼킨다.
   사람의 수신함이 아니다. 「도착했다」의 주어가 **사람이 아니라 계측기**다.
2. **발송 업체가 미정이다**(D4-1). 실제 SMTP 릴레이·인증(SMTP AUTH)·TLS 협상은
   이 실측에 **한 줄도 들어오지 않았다** — mailpit 실측은 `EMAIL_USE_TLS=False` 로 돌았다.
   즉 **TLS 경로는 못 쟀다.**
3. **SPF/DKIM/DMARC·스팸함·수신 거부**는 통과한 적이 없다. 실제 도메인으로 보냈을 때
   받는 쪽 메일 서버가 버릴지 여부는 **여기서 알 수 없다**.
4. **사람이 읽었는가**는 어떤 기계도 여기서 답하지 못한다.
5. 이 실측은 **환경변수로 덮어쓴 형상**에서 돌았다. 지금 `backend/.env` 의 상시 형상은
   `EMAIL_HOST=smtp.gmail.com` 이고 `DEFAULT_FROM_EMAIL` 은 **비어 있다**(아래 §6 참조).
   그러므로 「메일이 나간다」가 **평시 형상의 사실은 아니다**.

→ 그러므로 이 초록을 「경보가 사람에게 도달한다」로 옮겨 적으면 그것이
D-284 가 이름 붙인 **「조용한 성공」**이다. OPS-10 은 여전히 **회색**이다.

⚠ 아래 표식(UUID)은 **앞 12자만** 적는다. `.gitleaks.toml` 의 `gx-agent-docs-hex` 룰이
`docs/agent/**` 의 32자 이상 16진수를 실값 인용으로 보기 때문이다.

---

## 1. 세운 것

`docker-compose.yml` 에 서비스 하나를 **추가만** 했다(기존 서비스·앵커 `x-gx-logging`·
볼륨·네트워크 선언은 건드리지 않았다). 판은 digest 로 못박았다(D-387 · MinIO 와 같은 규약):

```
image: axllent/mailpit@sha256:98b916bd3c8d61f7633a52d3ea2f58d00620cb01ca57ab59edde68c347a95365
```

- 위 digest 는 `docker pull axllent/mailpit:latest` [실측 2026-09-06] 가 준 값 그대로다.
- ⚠ 이 이미지는 `org.opencontainers.image.version` 라벨이 **비어 있다** — 판 번호를 못 읽었다.
  읽은 것은 이미지 생성 시각뿐이다: `2026-09-05T11:15:32Z`. **판 번호를 안다고 적지 않는다.**
- `profiles: ["mail"]` 로 감쌌다 — 계측기가 맨 `docker compose up` 에 딸려 오지 않게 한다.
- 호스트 포트를 `127.0.0.1` 로 묶었다 — mailpit 은 무인증이라 0.0.0.0 에 열면 같은 망의
  누구나 이 통에 넣고 읽는다.

### 쓴 명령 그대로

```bash
# 1) 판 받기 (digest 확인)
docker pull axllent/mailpit:latest                      # exit 0
docker image inspect axllent/mailpit:latest \
  --format '{{index .Config.Labels "org.opencontainers.image.version"}} | {{.Created}} | {{index .RepoDigests 0}}'
#   → " | 2026-09-05T11:15:32.076262606Z | axllent/mailpit@sha256:98b916bd..."   (판 번호 라벨 비어 있음)

# 2) 세우기
#    ⚠ 함정: 그냥 부르면 `POSTGRES_PASSWORD 가 없다` 로 멈춘다. compose 의 변수 치환은
#      프로필로 걸러진 서비스까지 **파일 전체**에 걸린다. 뿌리 .env 는 고치지 않는다.
POSTGRES_PASSWORD=interpolation-only-not-used docker compose --profile mail up -d mailpit
#   → Container guardianx-source-mailpit-1 Started        (exit 0)

# 3) 손으로 만든 망에 한 번 더 잇는다 (MinIO·postgres 와 같은 절차)
docker network connect --alias mailpit gx-main-network guardianx-source-mailpit-1   # exit 0

# 4) 떴는가 / 받는가
docker ps --filter name=mailpit --format '{{.Names}}  {{.Status}}  {{.Ports}}'
#   → guardianx-source-mailpit-1  Up 4 seconds (healthy)  127.0.0.1:1025->1025/tcp, 127.0.0.1:8025->8025/tcp
```

| 항목 | 값 [실측 2026-09-06] |
|---|---|
| 컨테이너 이름 | `guardianx-source-mailpit-1` |
| 상태 | `Up (healthy)` — healthcheck `/mailpit readyz` |
| SMTP | 컨테이너 `mailpit:1025` · 호스트 `127.0.0.1:1025` |
| 웹 UI / HTTP API | 컨테이너 `mailpit:8025` · 호스트 `127.0.0.1:8025` |
| 붙은 망 | `guardianx-source_guardianx-network` + `gx-main-network`(alias `mailpit`) |

`gx-shell` 에서 닿는지 먼저 확인했다(빈 수신함 = 오염 없는 출발선):

```bash
MSYS_NO_PATHCONV=1 docker exec gx-shell python -c "
import urllib.request, json
r = urllib.request.urlopen('http://mailpit:8025/api/v1/messages?limit=5', timeout=10)
d = json.load(r); print('http', r.status, 'total=', d.get('total'))"
#   → http 200 total= 0        (exit 0)
```

---

## 2. `settings.py` 는 고치지 않았다 — 환경변수로 덮인다 [확인함]

`backend/config/settings.py:802-808` 은 이미 `env(...)` 로 읽는다. `environ.Env.read_env` 는
`os.environ.setdefault` 를 쓰므로 **`docker exec -e` 로 준 값이 이긴다**. 실측으로 확인했다:

```bash
MSYS_NO_PATHCONV=1 docker exec -e DJANGO_SETTINGS_MODULE=config.settings \
  -e EMAIL_HOST=mailpit -e EMAIL_PORT=1025 -e EMAIL_USE_TLS=False \
  -w /app gx-shell python -c "
import django; django.setup()
from django.conf import settings
print('HOST', settings.EMAIL_HOST, 'PORT', settings.EMAIL_PORT, 'TLS', settings.EMAIL_USE_TLS)"
#   → HOST mailpit PORT 1025 TLS False        (exit 0)
```

---

## 3. 실측 ① — `django.core.mail.send_mail` (Django 기본 경로)

제목에 UUID 표식을 넣어 보내고, mailpit HTTP API(`GET /api/v1/messages`)를 **0.2초마다
최대 30초** 되읽어 그 표식을 찾았다. 계측 스크립트는 저장소에 남기지 않았다(임시 파일).

```bash
MSYS_NO_PATHCONV=1 docker exec -i \
  -e DJANGO_SETTINGS_MODULE=config.settings \
  -e EMAIL_HOST=mailpit -e EMAIL_PORT=1025 -e EMAIL_USE_TLS=False \
  -e DEFAULT_FROM_EMAIL=gx-gate@gate.local \
  -w /app gx-shell python - < p68_direct.py
```

| 항목 | 값 |
|---|---|
| 표식(UUID 앞 12자) | `77b45b8c04c7…` |
| 제목 | `[P-68] mailpit inbox probe 77b45b8c04c7…` |
| 보낸 이 → 받는 이 | `gx-gate@gate.local` → `p68-probe@gate.local` |
| `send_mail()` 반환 | **1** (보낸 개수) |
| 보낸 시각 (UTC) | `2026-09-06T06:51:07.378672Z` |
| SMTP 핸드오프 | **0.026 s** |
| 수신함에서 찾은 시각 (UTC) | `2026-09-06T06:51:07.407647Z` |
| mailpit 이 적은 도착 시각 | `2026-09-06T06:51:07.402Z` |
| **보냄 → 도착까지** | **0.029 s** |
| mailpit 메시지 id | `4SAhafmvznARSPExVCxINO` |
| 수신함 총량 | 보내기 전 **0** → 보낸 뒤 **1** |

**도착했다.** exit 0.

---

## 4. 실측 ② — 제품의 실제 발송 경로 `k2_notify` `EmailChannel`

`backend/kernels/k2_notify/channels.py::EmailChannel.send()` 를 **그대로** 태웠다
(`REGISTRY["email"]` 에서 꺼내 부른다 — 코드를 고치거나 흉내 내지 않았다).
P-41 허용 도메인 관문이 `send_mail` **앞**에 서 있으므로 `K2_SEND_ALLOWED_DOMAINS` 에
`gate.local` 을 환경변수로 줬다(저장소·`.env` 는 안 고쳤다).

```bash
MSYS_NO_PATHCONV=1 docker exec -i \
  -e DJANGO_SETTINGS_MODULE=config.settings \
  -e EMAIL_HOST=mailpit -e EMAIL_PORT=1025 -e EMAIL_USE_TLS=False \
  -e DEFAULT_FROM_EMAIL=gx-gate@gate.local \
  -e EMAIL_HOST_USER=gx-gate@gate.local -e EMAIL_HOST_PASSWORD=gate-local-no-auth \
  -e K2_SEND_ALLOWED_DOMAINS=gate.local \
  -w /app gx-shell python - < p68_k2.py
```

| 항목 | 값 |
|---|---|
| 어댑터 | `kernels.k2_notify.channels.EmailChannel` (실물) |
| `EmailChannel.configured()` | `ok=True` |
| `EmailChannel.deliverable()` | `ok=True` (`gate.local` 은 `.invalid` 가 아니다) |
| `EmailChannel.send_allowed()` | `ok=True` (허용 목록 `["gate.local"]`) |
| 표식(UUID 앞 12자) | `89da46fb6d18…` |
| `SendOutcome` | **`ok=True`** |
| 보낸 시각 (UTC) | `2026-09-06T06:51:55.303379Z` |
| SMTP 핸드오프 | **0.009 s** |
| 수신함에서 찾은 시각 (UTC) | `2026-09-06T06:51:55.315390Z` |
| mailpit 이 적은 도착 시각 | `2026-09-06T06:51:55.311Z` |
| **보냄 → 도착까지** | **0.012 s** |
| mailpit 메시지 id | `4Y0mzRQVgqgwxHRSd8PlYm` |
| 수신함 총량 | **2** |

**도착했다.** exit 0.

⚠ **여기까지가 태운 구간이다.** `k2_notify/services.py::send()`(이벤트 → 수신자 해석 →
발송 이력 행 기록)는 **태우지 않았다.** 그 경로는 공용 개발 DB 에 이력 행을 남기고,
지금 그 DB 위에서 다른 차선들이 일하고 있다. 즉 **「규칙이 이 채널을 고르는가」와
「이력에 무엇이 남는가」는 이 문서가 잰 것이 아니다.**

---

## 5. 실측 ③ — 음성 대조군 (이 측정이 무엇이든 초록으로 만들지 않는다는 증거)

수신함을 보는 측정은 **무엇을 넣어도 초록**이면 아무 값이 없다. 그래서 허용 목록에서
`gate.local` 을 빼고 같은 코드를 한 번 더 태웠다 — **도착하면 안 되는 메일**이다.

```bash
MSYS_NO_PATHCONV=1 docker exec -i ... -e K2_SEND_ALLOWED_DOMAINS=example.com \
  -w /app gx-shell python - < p68_neg.py
```

| 항목 | 값 |
|---|---|
| 표식(UUID 앞 12자) | `7d67db5d44e0…` |
| `SendOutcome` | **`ok=False`** — 「실발송 차단 — 로그 어댑터로 떨어뜨렸다. `gate.local` 는 실발송 허용 도메인 목록 밖이다(P-41). 허용된 것: example.com」 |
| 3초 뒤 수신함 | 총량 **2 → 2** · 표식 **없음** |

즉 이 측정은 **막힌 것을 막혔다고 말한다.** exit 0.

---

## 6. 덤으로 잰 것 — **평시 형상은 아직 못 보낸다**

`backend/.env` 의 현재 값으로 읽으면:

```
DEFAULT_FROM_EMAIL = ''            ← 비어 있다
K2_SEND_ALLOWED_DOMAINS = ['gmail.com']
```

`EMAIL_PLACEHOLDER_VALUES` 에 `""` 가 들어 있으므로(`backend/config/settings.py:826`)
**`EmailChannel.configured()` 는 평시 형상에서 `ok=False`(회색)** 가 된다. 위 실측 ②가
`ok=True` 였던 것은 `DEFAULT_FROM_EMAIL` 을 **환경변수로 채웠기 때문**이다.
→ 「mailpit 으로 보냈다」가 「지금 형상으로 보낸다」가 아니다. 이 줄을 지우지 말 것.

---

## 7. 다음 사람이 밟을 함정

1. **`docker compose --profile mail up -d mailpit` 이 그냥은 안 선다.** compose 의 변수
   치환은 프로필로 걸러진 `postgres` 서비스까지 파일 전체에 걸리고, 뿌리 `.env` 에는
   `POSTGRES_PASSWORD` 가 없다. `POSTGRES_PASSWORD=<더미>` 를 앞에 한 번 얹는다.
   **`.env` 를 고쳐서 풀지 말 것** — 그 파일은 다른 차선의 것이다.
2. **`docker network connect` 를 잊으면 `gx-shell` 에서 `mailpit` 이 안 풀린다.**
   compose 망(`guardianx-source_guardianx-network`)과 손으로 만든 `gx-main-network` 는
   다른 망이다. MinIO·postgres 주석에 같은 절차가 있다.
3. **`EMAIL_USE_TLS` 를 안 끄면 못 붙는다.** mailpit 기본 SMTP 는 평문이다.
4. **수신함이 비어 있는 것을 먼저 확인하고 재라.** 남아 있던 어제 메일을 오늘 도착으로
   읽으면 그것이 거짓 초록이다. 이 실측은 매번 `before_total` 을 먼저 찍고 시작했다.
5. **제목의 표식을 지우지 말 것.** 「메일이 있다」와 「내가 방금 보낸 그 메일이 있다」는
   다른 사실이다. 표식 없이 개수만 세면 다른 차선이 보낸 메일을 내 초록으로 읽는다.
6. `docs/agent/**` 에 digest·해시를 적을 때는 **같은 줄에 `sha256` 또는 `digest`** 를
   넣어야 `.gitleaks.toml` 의 `gx-agent-docs-hex` 룰을 통과한다. UUID 표식은 32자
   16진수라 그대로 적으면 걸린다 — 이 문서는 앞 12자만 적었다.

---

## 8. 턴 H 재측 (2026-09-06 · 차선 E) — **여전히 도착한다. 여전히 OPS-10 은 안 닫힌다**

[실측 2026-09-06 · 같은 형상 · `django.core.mail.send_mail`]

| 항목 | 값 |
|---|---|
| mailpit 컨테이너 | `guardianx-source-mailpit-1` · `Up 3 hours (healthy)` |
| 출발선 (수신함 총량) | **2** — 턴 G 가 넣은 둘이 그대로 있다 |
| 표식(UUID 앞 12자) | `b375191c9fb3…` |
| `send_mail()` 반환 | **1** |
| SMTP 핸드오프 | **0.0221 s** |
| **보냄 → 도착까지** | **0.0234 s** |
| mailpit 이 적은 도착 시각 | `2026-09-06T10:17:37.4Z` |
| 도착 뒤 수신함 총량 | **3** |

**도착했다.** 턴 G 의 0.029 s 와 같은 자릿수다.

### ⛔ 그리고 **한계는 한 줄도 안 줄었다** — 다시 적는다

1. **받은 통이 우리 것이다.** mailpit 은 무인증으로 무엇이든 받아 삼킨다.
   「도착했다」의 주어가 **사람이 아니라 계측기**다.
2. **TLS 구간은 이번에도 한 줄도 안 쟀다** — 이 측정 역시 `EMAIL_USE_TLS=False` 로 돌았다.
3. **SMTP AUTH·발송업체(릴레이) 구간 0건.** 발송 업체는 여전히 미정이다(D4-1).
4. **SPF/DKIM/DMARC·스팸함·수신 거부** 통과 이력 0건.
5. **평시 형상의 사실이 아니다** — 이 수는 `EMAIL_HOST` 등을 `docker exec -e` 로 덮어쓴
   형상에서 났다. `backend/.env` 의 상시 형상은 `EMAIL_HOST=smtp.gmail.com` ·
   `DEFAULT_FROM_EMAIL=''` 이고, 그 형상에서 `EmailChannel.configured()` 는 **회색**이다.
6. **사람이 읽었는가**는 어떤 기계도 여기서 답하지 못한다.

→ **OPS-10 은 회색이다.** 이 초록을 「경보가 사람에게 도달한다」로 옮겨 적는 것이
D-284 의 「조용한 성공」이다. 닫으려면 SLA v0.2 §4 가 적은 둘이 필요하다:
**사람 수신함에 도착한 캡처 1장** + **TLS·SMTP 인증 경로를 실제 릴레이로 1회.**
둘 다 **대표 결정(주소·발송 업체)** 뒤에 온다.
