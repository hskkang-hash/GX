# P-72 턴 G — 번들 해시 게이트의 대조 상대가 **HEAD → 배치 커밋**으로 바뀌었다

- 집행: 차선 S · **2026-09-06 턴 G**
- 고친 파일: `scripts/verify_bundle_hash.py` · `scripts/deploy.sh`
- 새 자리: `docs/agent/evidence/deploy/` (배치 증거 JSON)

---

## 1. 무엇을 없앴나 — **문서 커밋 하나가 배치를 빨갛게 만들었다**

옛 규칙은 「서버 번들 == HEAD」였다. 배치를 마친 뒤 **보고서 한 장을 커밋하는 것만으로**
게이트가 빨개졌다 — 코드는 한 줄도 안 움직였는데. 그 빨강이 가리키는 사실은
「서버가 낡은 코드를 낸다」가 아니라 「문서가 하나 늘었다」였다.
**사실과 색이 어긋나는 게이트는 곧 무시당한다**(D-353).

## 2. 새 규칙 — **한 문장을 둘로 나눈다**

```
① 서버가 내는 번들 = docs/agent/evidence/deploy/ 의 `deploy_commit`
② HEAD − 배치 커밋 차이가 `docs/**` 뿐
```

둘 다 초록이라야 「지금 서는 것이 지금 코드다」라고 말할 수 있다.
배치 증거가 없는 자리에서는 **옛 규칙 그대로** 돈다 — 증거를 아직 안 쓰는 사람의 게이트를
태어나면서부터 빨갛게 만들지 않는다.

`docs/agent/evidence/deploy/<시각>.json` 은 `scripts/deploy.sh` 가 **게이트가 돌기 전에**
자동으로 쓴다. 게이트가 물어야 할 것이 그 증거이기 때문이다.

⚠ **컨테이너에는 `.git` 이 없다** [실측 2026-09-06 · `/repo/.git` 없음. git 실행파일은 있다].
  그래서 ②는 저장소가 있는 호스트에서 재서 `GX_DRIFT_JSON` 으로 넘긴다
  (`verify_bundle_hash.py --emit-drift`). `deploy.sh` 가 그 일을 한다 —
  **사람이 기억할 절차를 만들지 않는다**(D-286).

★ 배치 **전** 게이트(`--dist "$NEW"`)는 `--no-deploy-evidence` 로 옛 규칙을 쓴다.
  그 순간 HEAD 가 곧 배치 커밋이고, 아직 안 쓴 이번 증거 대신 **지난 배치의 증거**를 물면
  늘 빨개진다.

## 3. 실측 — 지금 서는 것 [2026-09-06]

```
docker exec -e GX_COMMIT=c86b678… -e GX_DRIFT_JSON='{"paths":[],"ancestor":true,…}' gx-shell \
  python /repo/scripts/verify_bundle_hash.py --web http://localhost:3002 \
  --deploy-evidence /docs/agent/evidence/deploy

[BUNDLE] [배치 커밋] c86b678dfda96ebcdc764da212e54fc9a7a42a59 ← 배치 증거 20260905_235520.json (commit_sha)
[BUNDLE]   번들이 자기 커밋을 말한다        `GX_COMMIT:c86b678…` ← /assets/index-KtOB6Mu5.js, /assets/router-CWOBuQ2U.js
[BUNDLE]   번들 해시 = **배치 커밋**       c86b678 = c86b678 — 서버가 내는 번들이 **배치 커밋**이다
[BUNDLE]   HEAD − 배치 커밋 차이가 `docs/**` 뿐   HEAD = 배치 커밋 c86b678 — 배치 뒤 커밋이 없다
[BUNDLE] 통과 — 서버가 내는 번들이 **배치 커밋**이고, 그 뒤 바뀐 것은 `docs/**` 뿐이다 (P-72)
                                                                              → exit 0
```

## 4. 드릴 둘 — **초록이 아무 때나 나오지 않는다** [실측]

```
드릴 A — 배치 뒤에 **문서만** 늘었다 (P-72 가 없애려던 그 빨강)
  GX_DRIFT_JSON='{"paths":["docs/agent/RESUME_NEXT.md","docs/agent/evidence/deploy/…json"],…}'
  → HEAD − 배치 커밋 차이가 `docs/**` 뿐
      배치 뒤 2건이 바뀌었고 **전부 `docs/` 아래다** — 문서 커밋은 배치 대상이 아니다
  → **exit 0**   ← 옛 규칙에서는 여기가 빨강이었다

드릴 B — 배치 뒤에 **코드**가 움직였다 (실제 `git diff a3f63d1..c86b678`)
  paths = [".gitleaksignore", "docs/agent/evidence/…" ×5]
  → X HEAD − 배치 커밋 차이가 `docs/**` 뿐
      배치 뒤에 **문서가 아닌 것**이 1건 바뀌었다: .gitleaksignore
      — 서버는 그 변경을 내주지 않는다. 다시 배치해야 한다
  → **exit 1**   ← 규칙을 넓힌 것이 게이트를 끈 것이 아니다
```

## 5. 판정기의 자기시험

```
[BUNDLE] 자기시험 통과 — **출생 표본 4**(턴 D · 낡은 사본 · 말없는 번들 · **P-72 문서 커밋**) ·
  양성 2 · 음성 2 · 회색 2 · 곁파일 2 · 갈래 2 · 토큰 2 · 파싱 1 ·
  **배치 6**(문서만 · 코드 표류 · 가지 밖 · git 없음 · 대조 상대 · 옛 규칙)
```

배치 여섯 갈래가 각각 지키는 것:

| 갈래 | 지키는 것 |
|---|---|
| 문서만 | P-72 출생 표본 — 문서 커밋 하나로 배치가 빨개지던 자리 |
| 코드 표류 | `frontend/src` 가 배치 뒤 바뀌면 **빨강**. 이 갈래가 없으면 P-72 는 게이트를 끈 것이 된다 |
| 가지 밖 | 배치 커밋이 지금 가지에 없으면 빨강 — 그 번들이 어느 코드인지 저장소가 말할 수 없다 |
| git 없음 | 거리를 **못 쟀으면 회색**. 컨테이너에는 `.git` 이 없다 |
| 대조 상대 | 증거가 있으면 **HEAD 가 아니라 배치 커밋**과 맞춘다 |
| 옛 규칙 | 증거가 없는 자리에서 옛 규칙이 그대로 돈다 |

## 6. 넓힌 자리는 **`docs/` 하나뿐이다**

`DOC_ONLY_PREFIXES = ("docs/",)`. 여기를 넓히는 것은 규칙을 바꾸는 일이다 —
넓히려면 **왜 그것이 서버가 내주는 것과 무관한지**를 먼저 적어야 한다.
(이번 드릴 B 가 보였듯 `.gitleaksignore` 같은 뿌리 파일은 `docs/` 가 아니므로 빨강이다.)
