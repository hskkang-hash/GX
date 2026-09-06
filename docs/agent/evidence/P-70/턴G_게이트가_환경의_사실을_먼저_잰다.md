# P-70 턴 G — 게이트가 **환경의 사실**과 **제품의 사실**을 스스로 가른다

- 집행: 차선 S · **2026-09-06 턴 G** · 차선 이름: `test_gx_s` · 8900 · 탐침 `gxprobe_s`
- 새로 난 것: `scripts/gate_env.py` (몸통 한 곳) · `docs/agent/verify_gates.sh` (부르는 줄만)

---

## 1. 무엇을 없앴나 — **게이트 여섯이 유령 파일 953개를 훑고 있었다**

[턴 F 실측 · `docs/agent/evidence/P-55/window_20260905_2247.md`]
`gx-shell:/repo/frontend` 가 마운트가 아니라 **사본**이었다. 사본 1,956개 vs 호스트 1,003개
— **953개가 유령**이었고 컨테이너 안에서 도는 게이트 여섯이 그것을 훑으며 색을 냈다.

그 색은 제품의 색이 아니었다. **환경이 어긋난 것이 제품 결함처럼 보였다.**
이제 모든 게이트가 판정 전에 자기가 딛는 환경을 먼저 잰다.

```
env_require mount session minio   ← 이 환경이 없으면 잴 수 없다
env_none "…"                      ← 딛는 환경이 없다고 **명시**한다
```

환경이 빠지면 **회색(exit 2) + 사유 = 환경 이름**. 빨강과 절대 섞지 않는다.

## 2. `env:` 블록이 붙은 게이트 — **13**

| 게이트 | 딛는 환경 |
|---|---|
| `secrets` | 없음 (호스트 저장소의 `.env.example`·스캐너·git 이력) |
| `forbidden-zone` | 없음 (베이스라인 대비 git diff) |
| `ui-secrets` · `ui-copy` · `ui-library` · `post-arg-style` | `mount` (frontend/src — 유령 953의 자리) |
| `bypass` · `isolation` · `model-inheritance` · `deprecated-base` · `dormant` | `mount` (backend) |
| `contract-route-reach` | `mount` `session` |
| `route-alive` | `mount` `session` `minio` |

★ 몸통은 `scripts/gate_env.py` **한 곳**이다. 열두 곳에 복붙하지 않았다 — 달라진 판정식
  복사본 하나가 D-212 였다.

## 3. 환경 넷 — 실측 [2026-09-06 14:0x · 차선 S]

```
[ENV]    minio    guardianx-source-minio-1 떠 있고 http://localhost:9000/minio/health/live → 200
[ENV]    smtp     수신함 http://localhost:8025/api/v1/messages?limit=1 → 200   ← 차선 E 가 세웠다
[ENV]    mount    호스트 = 컨테이너 — frontend 1007 · backend 1026 · scripts 122 · docs 424
[ENV]    session  점유자 `gxprobe_s` = **이 차선 전용 계정**(차선 s) — 앞선 창은 우리 것이다
```

### 마운트 일치 — **호스트 = 컨테이너, 네 짝 모두**

| 짝 | 호스트 | `gx-shell` | |
|---|---|---|---|
| `frontend` → `/repo/frontend` | 1007 | 1007 | 일치 (유령 953이 났던 자리) |
| `backend` → `/app` | 1026 | 1026 | 일치 |
| `scripts` → `/repo/scripts` | 122 | 122 | 일치 |
| `docs` → `/docs` | 424 | 424 | 일치 |

(턴 초 첫 측정은 1006 / 1025 / 118 / 390 이었다 — 이번 턴에 우리가 파일을 더한 만큼
**양쪽이 같이 늘었다.** 늘어도 같이 느는 것이 마운트의 증거다. 기록:
`docs/agent/evidence/P-70/env_20260906_S.json`)

두 쪽이 **같은 규칙**으로 센다(`node_modules`·`dist`·`__pycache__`·`.git`·`_fe_dist*` 제외).
규칙이 다르면 비교가 성립하지 않는다 — 자기시험이 그것을 판정한다.

★ `gx-fe-build:/app` 은 **일부러 뺐다.** 그 컨테이너의 `/app` 은 마운트가 아니라 사본이고
  (`docker inspect` 의 `Mounts` 가 비어 있다 [실측]), `scripts/deploy.sh` 가 빌드할 때마다
  `docker cp` 로 소스를 새로 넣는다 — **사본인 것이 설계다.** 넣으면 영원한 회색이 되고,
  영원한 회색은 아무도 안 읽는다. 드릴로만 얹는다: `GX_MOUNT_EXTRA=…`.

### 세션 점유자 — **차선 이름이 가른다**

`end_previous_session: **false**` 로 묻는다. `true` 로 물으면 묻는 행위가 남의 화면을 죽인다 —
**재는 것이 대상을 바꾸면 그것은 측정이 아니다.**
차선 전용 계정(`gxprobe_<차선>`)이 쥔 앞선 창은 **우리 것**이므로 초록,
공용 계정이 쥐고 있으면 **회색**이다. 동시 접속 1(UX-24 · §0.4 자료구조)을 차선 이름으로 가른다.

## 4. 회색이 실제로 나는가 — **드릴 셋** [실측]

```
① 마운트 어긋남   GX_MOUNT_EXTRA="febuild:frontend:gx-fe-build:/app" verify_gates.sh --gate ui-secrets
   [환경] 미비 — 딛는 환경: mount
   [ENV] ? *mount  **컨테이너가 저장소를 보고 있지 않다** — febuild: 호스트 1007 vs 컨테이너 1005 (**유령 -2**)
   SKIP  환경 미비 — mount        → exit 2

② MinIO 없음     GX_MINIO_CONTAINER=no-such-minio verify_gates.sh --gate route-alive
   [ENV] ? *minio  컨테이너 `no-such-minio` 가 떠 있지 않다 — 객체 저장소를 쓰는 판정은 잴 자리가 없다
   SKIP  환경 미비 — minio        → exit 2

③ 세션 점유      GX_LANE="" GX_PROBE_USER=gxprobe_s gate_env.py --require session
   [ENV] ? *session **세션 점유자가 있다: `gxprobe_s`** — 그런데 이 계정은 차선 전용이 아니다 …
                                   → exit 2
```

**회색은 초록이 아니고, 빨강도 아니다.** 사유가 언제나 **환경 이름**이라 무엇을 세워야
하는지가 그 자리에서 보인다.

## 5. 판정기의 자기시험 (D-277 · D-350)

```
[ENV] 자기시험 통과 — **출생 표본 1**(유령 953 · P-55) · 양성 1 · 음성 9 ·
      해당없음 1 · 요구범위 1 · 세는규칙 2
```

출생 표본은 합성이 아니다 — 호스트 1,003 vs 컨테이너 1,956 을 그대로 먹이고 회색이
나오는지, 사유에 **유령 수(953)** 가 적히는지를 본다.

「요구범위」 갈래: **요구하지 않은 환경**이 빠졌다고 회색이 되면 안 된다. 게이트마다 딛는
환경이 다르고, 남의 환경으로 회색이 되는 게이트는 곧 꺼진다(D-353).

「해당없음」 갈래: 컨테이너가 아예 안 떠 있으면 **위임 경로가 없으므로** 유령이 생길
자리가 아니다 — 회색이 아니라 `na` 다. 잴 자리가 없는 것과 못 잰 것은 다른 사실이다(P-12 ③④).

## 6. 러너에 붙인 한 줄

환경이 빠져 회색이 된 게이트는 **건수를 말할 수 없다**(D-301 의 `[입력]` 요구).
그것을 빨강으로 바꾸면 환경 결함이 다시 제품 결함의 색을 입는다 — 그래서 `run_gate` 가
`[환경] 미비` 를 본 게이트에는 건수 요구를 적용하지 않는다.

## 7. 못 한 것

- `smtp` 를 **요구하는** 게이트는 아직 없다(측정만 한다). 발송→도착을 게이트로 만드는 것은
  차선 E 의 P-68 이 세운 뒤의 일이다.
- 포트 8900(차선 S 전용 서버)은 이번 턴에 띄우지 않았다 — 게이트는 이미 떠 있는
  `gx-shell` 위임과 `localhost:8500` 을 썼다. **떠 있는 것을 내리지 않았다.**
