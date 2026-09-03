# MinIO 맥박 — 강제 도구 실측 (D-412 · 판정 1)

**2026-09-19** · 환경: `gx-shell` runserver 8000 · `guardianx-source-minio-1` · `MINIO_ENDPOINT=minio:9000`

> 09-18 의 물음: *「세우고 나서 더 조용해졌다」* — 저장소를 내려도 200 이었다.
> 이번에 재어 보니 **뿌리가 둘**이었다. 하나만 고쳤으면 여전히 조용했을 것이다.

---

## ① HTTP 경로 — `GET /api/media-data/` (자격증명 있이)

| 시각 | 사건 | 응답 | 걸린 시간 |
|---|---|---|---|
| 01:40:17 | 저장소 살아 있음 | `200 · success:true` | 0.027s |
| 01:40:18 | | `200 · success:true` | 0.025s |
| 01:40:19 | **`docker stop minio`** | | |
| 01:40:20 | | `200 · success:true` | 0.025s |
| 01:40:22 | | `200 · success:true` | 0.028s |
| **01:40:24** | | **`500 · success:false`** | **3.316s** ← 맥박이 잡았다 |
| 01:40:29 | | `500 · success:false` | 0.047s ← 캐시된 False |
| 01:40:31 | | `500 · success:false` | 0.024s |
| 01:40:33 | | `500 · success:false` | 3.397s ← TTL 만료 · 다시 잼 |
| 01:40:37 | **`docker start minio`** | | |
| 01:40:39 | | `500 · success:false` | 0.022s |
| 01:40:41 | | `500 · success:false` | 0.025s |
| **01:40:43** | | **`200 · success:true`** | 0.026s ← 회복 |
| 01:40:49 | | `200 · success:true` | 0.030s |

**하강 감지 약 5초 · 회복 약 6초 · 살아 있을 때 25~30ms**
(매 요청 저장소 왕복 없음 — TTL 이 F-05 p95 예산을 지킨다)

---

## ② 프로세스 안 대조 — `minio_client.available`

```
ttl=5.0 endpoint='minio:9000' alive=True client=True
t+ 0.0s available=True  (0.00s)
t+ 2.0s available=True  (0.00s)
t+ 4.0s available=True  (0.00s)      ← 여기서 minio 내림
t+ 9.3s available=False (3.31s)      ← TTL 지나자 실제로 물었다
t+11.3s available=False (0.00s)      ← 캐시된 False (요청은 안 문다)
t+13.3s available=False (0.00s)
t+18.6s available=False (3.33s)      ← 여기서 minio 올림
t+20.6s available=False (0.00s)
t+22.6s available=False (0.00s)
t+24.6s available=True  (0.00s)      ← 회복
```

앞판은 이 자리가 **t+0 부터 끝까지 True** 였다 — 기동 시점의 사진.

---

## ③ ★ 캐시가 사진을 액자에 넣고 있었다 — 뿌리 ②

MinIO 를 **내린 채**, 같은 순간에 두 번 물었다:

```
GET /api/media-data/            → 200 · success:true   (0.01s)   ← 캐시된 본문
GET /api/media-data/?bust=…     → 500 · success:false  (6.68s)   ← 실제로 돈 것
```

`UniversalCacheMiddleware` 는 적중한 본문을 **언제나 `JsonResponse(200)`** 으로 다시
만든다. 살아 있을 때 담긴 200 이 죽은 뒤에도 「목록을 가져왔다」고 말했다.

★ **`available` 만 고쳤으면 이 실측은 여전히 200 이었을 것이다.** 실제로 처음 한 시간
동안 그랬고, 그것을 「고쳤는데 왜 안 되지」로 넘기지 않고 **같은 순간 두 URL 을 견준
것**이 뿌리 ②를 드러냈다. 한 갈래만 재면 어느 쪽이든 그럴듯하다(09-18 의 그 문장).

고침: `BYPASS_PATTERNS` 에 `media-data`. 그 파일이 이미 `surveillance-dashboard` 를
같은 사유로 빼 두고 있었다 — **바깥에서 바뀌는 것은 무효화 신호가 없다.**

---

## ④ 곁가지 — 죽은 저장소 탐침이 6.6초였다

데이터용 풀(`connect 3s · retries 1`)로 맥박을 재고 있었다. 맥박 전용 접속을
따로 뒀다(`connect 1s · read 1s · retries 없음`) → **6.6s → 3.3s**.
맥박은 건강검진이지 데이터 왕복이 아니다.

남는 비용: 저장소가 죽은 동안 **5초에 한 번 3.3초**. 나머지 요청은 캐시된 False 로 0ms.
(3.3초가 1.0초로 안 내려간 것은 DNS 이름 해석 실패가 urllib3 시간 상한 밖이기 때문 —
컨테이너가 멈추면 `minio` 별칭 자체가 사라진다. **재지 않은 것을 고쳤다고 적지 않는다.**)

---

## 재현

```bash
docker exec -e GX_API=… -e GX_ROUTE_USER=… -e GX_ROUTE_PASSWORD=… gx-shell python /tmp/pulse.py 6 2
docker stop  guardianx-source-minio-1     # → 5초 안에 500
docker start guardianx-source-minio-1 && docker network connect --alias minio gx-main-network guardianx-source-minio-1
                                          # → 6초 안에 200
```
