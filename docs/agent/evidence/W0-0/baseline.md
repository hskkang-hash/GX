# W0-0 증거 — 베이스라인 커밋

생성: 2026-08-13 · baseline_sha: 4afca2bb17f0dd64afce238579ad58380f9c4b57 (1,796 files)

> 이 문서에는 실제 시크릿 값을 적지 않는다 (RESUME_NEXT §7-2).
> 구 실값은 SHA-256 앞 12자 지문으로만 식별한다. 원본은 ~/.guardianx-secrets 백업에 있다 (D-002).
> 최초 작성본에 실값을 나열했다가 W0-1a 스캔에 걸려 재작성했다 — 스캔이 실제로 작동한 사례다.

## DoD 1 — 커밋 1개 + 그 커밋의 .env.example 실값 0개

```
15ba89a docs(agent): W0-0 baseline_sha·증거 기록, status=review [W0-0]
4afca2b chore(repo): 베이스라인 커밋 — 실키 제거 후 초기화 [W0-0]
```

## 구 실값 13종 전수 검사 (HEAD 트리 전체)

```
  DB_PASSWORD                            sha256:279f8ad60113  LEAK HEAD:docs/agent/tickets.yaml
  MINIO_ACCESS_KEY                       sha256:ad9858116e63  LEAK HEAD:docs/agent/tickets.yaml
  MINIO_SECRET_KEY                       sha256:248b1b2079ee  LEAK HEAD:docs/agent/tickets.yaml
  SMTP_PASSWORD                          sha256:c448720742fa  CLEAN
  GCS_APIKEY / VITE_CGS_APIKEY (동일값)     sha256:829108e96c95  CLEAN
  OPENSEARCH_PASSWORD                    sha256:a9e92623ede9  CLEAN
  KAKAO_API_KEY(REST)                    sha256:94547c8d6fc3  CLEAN
  ANYANG_SERVICE_KEY                     sha256:1a6b908b8dc3  CLEAN
  VITE_KAKAO_API_KEY(JS)                 sha256:baa7719d6473  CLEAN
  VITE_GOOGLE_MAPS_API_KEY               sha256:5627c5c6037c  CLEAN
  VITE_TURN_PASSWORD                     sha256:209765a34b39  CLEAN
  VITE_TURN_USERNAME                     sha256:a0fd7e384174  CLEAN
  SMTP_USERNAME                          sha256:79ccd9814130  CLEAN
```

CLEAN 10/13

## DoD 2 — meta.baseline_sha

tickets.yaml `meta.baseline_sha` 에 기록됨. 이 커밋 이후 파일이 '신규' 판정 대상이다 (D-005).

## DoD 3 — D-205 로 재정의된 기준

- 루트 `yarn.lock` 부재 — OK
- `frontend/.npmrc` 에 `legacy-peer-deps=true` 커밋 — OK (4afca2b)
- `package-lock.json` 생성은 W0-8(사내망 필요)로 분리

`.npmrc` 는 `package.json` 이 있는 `frontend/` 에 두어야 npm 이 읽는다. 루트에 두면 무시된다.
