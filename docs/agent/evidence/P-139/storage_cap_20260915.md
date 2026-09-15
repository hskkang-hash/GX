# P-139 ② 저장 용량 상한 — `GX_STORAGE_CAPACITY_GB` = 50 (2026-09-15 · 턴 Q · 차선 E)

판정(RESUME_NEXT §2 P-139): 값 = 실측 볼륨 **`df` 가용 × 0.8, 정수 GB** → `.env` · `.env.example` →
`ops_monitor::storage_used_pct` 가 UNKNOWN 에서 %로.

## 1. 코드가 무엇을 재나 [코드 읽기]

| 자리 | 하는 일 |
|---|---|
| `scripts/ops_monitor.py:87-89` | 이름 `GX_STORAGE_CAPACITY_GB` — 「용량 상한은 환경이 선언한다」 |
| `scripts/ops_monitor.py:305` | `float(os.environ.get(...) or 0)` — **`collect()` 를 부를 때** 프로세스 환경에서 읽는다 |
| `scripts/ops_monitor.py:310-323` | 분자 = MinIO 버킷(`MINIO_STORAGE_MEDIA_BUCKET_NAME`) **객체 합계** ÷ 1024³ — 파일시스템 경로가 아니다 |
| `scripts/ops_monitor.py:329-337` | 상한 ≤ 0 이면 UNKNOWN · 있으면 `used/capacity×100` |
| `backend/common/ops_tasks.py:186-197` · `backend/config/celery.py:80` | 도는 감시 = `gx-celery-e` 워커 안의 `common.ops_monitor_beat`(beat 표) — 워커 프로세스의 환경을 본다 |
| `scripts/ops_patrol.py:57` | 순찰 = `docker exec gx-shell python /repo/scripts/ops_monitor.py --check` — **새 프로세스** |

그러므로 「코드가 재는 볼륨」 = 버킷이 사는 곳 = `guardianx-source-minio-1:/data`
(= 도커 볼륨 `guardianx-source_minio-data`).

## 2. df [실측 2026-09-15 · 바이트]

| 자리 | 명령 | 크기 | 가용 | 가용 GiB |
|---|---|---|---|---|
| minio `/data` | `docker exec guardianx-source-minio-1 df -B1 /data` | 1,081,101,176,832 | 1,004,928,692,224 | 935.9 |
| 호스트 C: | `df -B1 /c` (Git Bash) | 511,462,862,848 | 67,116,318,720 | 62.5 |

`/data` 의 1007G 는 **Docker Desktop 가상 디스크의 명목 크기**다. 그 디스크의 실물은
`C:\Users\hskka\AppData\Local\Docker\wsl\disk\docker_data.vhdx`(지금 23,900,192,768 바이트 · 자라는 파일)이고,
그 파일은 **C: 가 비어 있는 만큼만** 자랄 수 있다. 즉 실제로 찰 수 있는 한도는 두 수 중 **작은 쪽**이다.

    min(935.9, 62.5) × 0.8 = 50.006  →  정수 50 (GiB · ops_monitor 의 단위 1024³)

⚠ **[가정 · 기본값 「닫힌 쪽」]** 판정의 산식은 「볼륨 `df` 가용 × 0.8」이다. 볼륨 df(748)를 그대로 쓰면
C: 가 다 차는 날에도 이 신호는 한 자리 %를 말한다 — 모르는 것을 초록으로 적는 모양(D-301)이라 작은 쪽을 택했다.
세종이 볼륨 df 를 원하면 값만 748 로 바꾸면 된다(코드 변경 없음).

## 3. 컨테이너 안에서 한 번 계산 [실측 · 값 출력 없이 수만]

`gx-celery-e`(도는 감시가 사는 곳)에서 `ops_monitor.collect()` 를 새 프로세스로 두 번 — `docker exec -e` 는
컨테이너 설정을 바꾸지 않는다.

| 환경 | `storage_used_gb` | `storage_used_pct` |
|---|---|---|
| 상한 없음(지금) | 0.0006 · OK | **None · UNKNOWN** |
| `-e GX_STORAGE_CAPACITY_GB=50` | 0.0006 · OK | **0.0 · OK** |

같은 시각 감시 증거 `docs/agent/evidence/D-373/monitor_last.json`(10:39:43Z)도 `storage_used_pct None UNKNOWN`.
⚠ 0.0 은 반올림(`round(…, 2)`)이다 — 0.0006/50 = 0.0012%.

⚠ **분자의 한계(고치지 않고 적는다)**: 분자는 버킷 하나의 객체 합계이고 분모는 디스크다. 같은 가상 디스크에
`gx_pgdata`·이미지·로그도 산다. 그래서 이 %는 「디스크가 얼마나 찼나」가 아니라 「버킷이 상한의 몇 %인가」이고,
80% 경보는 버킷이 40GiB 가 될 때 운다 — 다른 것이 C: 를 채우는 경우는 이 신호가 못 본다. 새 코드 경로는 만들지 않았다.

## 4. 적은 곳 · 반영되는 길

| 자리 | 적었나 | 도는 감시에 닿나 |
|---|---|---|
| 뿌리 `.env` | **적었다** (`grep -c` 0 → 1 · 한 줄 추가만) | **아니다** — compose 만 읽는다. gx-* 는 손으로 만든 컨테이너 |
| `.env.example` | **적었다** (P-139 절) | — (이름·형식 문서) |
| `backend/.env` | 안 적었다 (**내 소유 밖** — 조율자 요청) | **재생성 없이 닿는 유일한 길** ↓ |
| 재생성 창 env-file | runbook ⑤ | 창에서 |

**재생성 없이 닿는 길이 기존 코드에 있다** [코드 읽기]: `backend/config/settings.py:25`
`environ.Env.read_env(BASE_DIR/".env")` 는 `setdefault` 라 **프로세스 환경에 이름이 없을 때만** 채운다(`.env.example:38-41` 이
MinIO 에서 같은 사실을 적었다). 이 이름은 지금 **어느 컨테이너의 프로세스 환경에도 없다** —
`gx-celery-e`·`gx-shell`·`gx-beat-e`·`gx-gunicorn-e` 넷 다 0 [실측 · 이름만 셈].
그러므로 `backend/.env`(= 컨테이너의 `/app/.env`)에 한 줄을 넣으면:

* 순찰(`ops_patrol` → `docker exec gx-shell … ops_monitor.py`)은 **새 프로세스라 바로** 닿는다.
* beat 감시(`gx-celery-e` 워커)는 워커가 뜰 때 한 번 읽었으므로 **프로세스 재시작**(`docker restart gx-celery-e` — 재생성 아님) 뒤에 닿는다.
  재시작은 이 차선의 권한 밖이라 하지 않았다.
