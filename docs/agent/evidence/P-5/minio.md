# 저장소를 세웠다 — 그리고 세우고 나서 더 조용한 결함이 드러났다 (P-5 · D-406·D-407)

**실행 2026-09-18** · `docker compose up -d minio` · 판정 `scripts/verify_minio.py` ·
`docs/agent/verify_gates.sh --gate route-alive` · `scripts/ops_monitor.py`

---

## 1. 게이트 — 전후 [실측]

| | 잼고 통과 | 잼고 실패 | 못 잼 | 대기 |
|---|---|---|---|---|
| 2026-09-17 | 6 | **1** | 0 | 2 |
| **2026-09-18** | **7** | **0** | 0 | 2 |

빨강→초록 사유(P-10): **MinIO 200.** `route-alive` 의 유일한 빨강이던
`/api/media-data/` · `/api/media-data` 두 자리가 **500 → 200**.

---

## 2. 착수 전 실측 — 이미 있던 것과 없던 것 (D-379 · D-333)

| | 상태 |
|---|---|
| compose 의 minio 서비스 | **없음** |
| minio 이미지 | **이미 로컬에 있음** — 밖에 사러 가지 않았다 (D-333 ①) |
| 백엔드 배선 | **이미 있음** (`django_minio_backend` · settings 506~526) |
| 기존 자격증명 | ★ **더미** — 5자였다. MinIO 루트 요건은 8자 이상 |

마지막 줄이 이번 실측의 첫 수확이다. 자격증명이 요건 미달이라는 것은
**이 저장소가 한 번도 진짜로 서 본 적이 없다**는 뜻이다. 「설정은 다 되어 있는데
환경만 없다」가 아니었다.

## 3. 세운 방법

```yaml
minio:
  # minio/minio:RELEASE.2025-09-07T16-13-09Z
  image: minio/minio@sha256:14cea493d9a34af32f524e538b8346cf79f3321eff8e708c1e2960462bd8936e
  environment:
    MINIO_ROOT_USER: ${MINIO_ROOT_USER:?뿌리 .env 에 … 가 없다}
    MINIO_ROOT_PASSWORD: ${MINIO_ROOT_PASSWORD:?…}
```

- **판을 digest 로 못박았다**(D-387). `:latest` 는 lock 이 아니다 — 내일 받으면 다른
  물건이 오고, 그때 빨개지면 우리는 그 빨강을 「환경 탓」으로 읽는다. 태그는 사람이
  읽으라고 옆 줄에 적었다. **둘을 따로 고치면 lock 이 아니다.**
- **자격증명은 저장소에 없다.** 뿌리 `.env`(gitignored)를 compose 가 자동으로 읽고,
  저장소에는 이름만 남는다(`.env.example`). `${VAR:?}` 는 값이 없으면 **조용히 기본
  자격증명으로 서는 대신 그 자리에서 멈추라**는 뜻이다.
- ⚠ 이 기계의 개발 환경은 손으로 만든 `gx-main-network` 위에 있다. compose 가 세운
  컨테이너를 그 망에 한 번 더 이어 준다:
  `docker network connect --alias minio gx-main-network guardianx-source-minio-1`.
  새 환경을 compose 만으로 세우면 이 줄은 필요 없다.

## 4. 강제 도구 [실측]

```
[MINIO] [입력] 1건 — 저장소 health (minio:9000) → 200
[MINIO] [입력] 1건 — 버킷 `guardianx-dev` 의 객체
[MINIO]   200 success=True  /api/media-data/?page_size=25&current_page=1   받는다
[MINIO]   200 success=True  /api/media-data?page_size=25&current_page=1    받는다
[MINIO] 통과 — 저장소 산다 · 객체 1건 · 화면이 부르는 두 자리가 받는다
```

★ 응답의 `success` 를 상태 코드와 **함께** 본다. 2026-09-14 에 이 자리가
`success: true` · `status: 500` 을 냈다(D-397) — dj-core `BaseResponse` 의 기본값이
True 라 뷰가 안 넘기면 조용히 참이 된다. **상태 코드만 보는 판정은 그날 초록이었을
것이고, 오늘도 그럴 것이다.**

대조 [실측]: 저장소를 내리면 `verify_minio.py` **exit 1**, 되돌리면 **exit 0**.

---

## 5. ★ 세우고 나서 드러난 것 — 이제 더 조용하다

저장소를 **실제로 내려 보았다.** 같은 라우트, 같은 토큰:

| | 응답 |
|---|---|
| 저장소 살아 있을 때 | `200 · success:true · 1건` |
| 저장소 **내렸을 때** | `200 · success:true · 1건` |
| 되돌린 뒤 | `200 · success:true · 1건` |

**아무 일도 일어나지 않는다.**

코드 근거 — `backend/stream_monitors/utils/minio_client.py`:

```python
self.available = False        # 21행
…
self._ensure_bucket_exists()
self.available = True         # 41행 — __init__ 안. 이후 다시 보지 않는다
```

**가용성이 기동 시점의 사진 한 장**이다.

저장소가 없던 동안에는 최소한 **500 으로 소리쳤다.** 이제는 조용하다.
새벽 두 시에 저장소가 죽으면 화면은 계속 「자료가 있습니다」라고 말하고,
당직자는 파일을 눌러 본 뒤에야 안다.

**이번 턴에 고치지 않는다.** 매 요청 확인은 F-05 의 p95 를 먹고, 처분은 셋 중
하나인데 그 선택은 설계 판정이다 — 짐작해서 고르지 않는다(D-280):

```
㉮ 짧은 TTL(예: 5초)로 다시 본다
㉯ 실패했을 때만 재확인하고 500 으로 승격한다
㉰ 그대로 두고 감시에만 맡긴다 (화면은 조용한 채로)
```

대장에 올렸다: `MINIO_AVAILABILITY_IS_BOOT_TIME_ONLY`.

---

## 6. ★★ 감시도 눈이 멀어 있었다 — 그리고 그건 고쳤다

같은 조건에서 `ops_monitor.py` 를 돌렸다:

| | `object_store_alive` |
|---|---|
| 저장소 살아 있을 때 | **OK** |
| 저장소 **내렸을 때** | **OK** ← 눈이 감겨 있었다 |

원인: 신호가 `default_storage.exists("존재하지_않는_이름")` 을 부르고
**예외가 안 나면 닿은 것**으로 읽었다. 그런데 저장소가 죽어도 그 호출은 예외 없이
**False** 를 돌려준다. 「없다」와 「못 물어봤다」를 **한 값으로 읽은 것**이다 —
D-301 이 이름 붙인 그 모양이고, 하필 **「살아 있는가」를 보라고 세운 신호**에서 났다.

고침: 저장소에게 **저장소만 답할 수 있는 것**을 묻는다 — 버킷의 존재.
닿지 못하면 그 호출은 예외를 던지고, 그 예외가 우리가 원하는 갈림이다.

```
저장소 살아 있을 때   OK      저장소가 답했다 · 버킷 guardianx-dev 있음
저장소 내렸을 때      ALARM   저장소에 닿지 못했다: MaxRetryError …
되돌린 뒤             OK      저장소가 답했다 · 버킷 guardianx-dev 있음
```

★ 이 결함은 **저장소를 세우기 전에는 드러날 수 없었다.** 없는 것을 감시하면 무엇을
물어도 답이 같다. 세워 놓고 **일부러 내려 봐야** 처음으로 시험된다.

> **가짜 환경에서 초록인 감시는 감시가 아니다.**

---

## 7. 정정 보고 (D-379)

지시서 §3 은 「P-5 가 media 화면·영상 백업·**EventClip** 을 한 번에 연다」고 적었다.

**EventClip 은 P-5 로 안 열린다** [실측]. `CLIP_EXTRACTION_READY=False` 는 저장소
부재가 아니라 **계약 11조(원본 영상 반출 금지) 설계 잠금**이다 —
코덱·전송 방식·보존 기간이 정해져야 풀린다. 저장소는 그 셋 중 어느 것도 아니다.
(`backend/stream_monitors/services/clips.py:61` · `CLIP_EXTRACTION` 잠금 등재)

## 8. 목록의 내용은 MinIO 가 아니라 DB 가 낸다

`MediaDataService.list_media` 는 MinIO 로 **가용성만** 보고, 항목은 `_build_queryset`
으로 만든다. 그래서 버킷에 객체를 직접 넣어도 목록에 안 뜬다 — **그것이 옳다.**

판정기가 「버킷의 객체 수」와 「라우트의 응답」을 **따로** 세는 이유가 이것이다.
둘은 다른 것을 증명한다: 앞은 **저장소에 닿았다**, 뒤는 **제품이 받는다**.
