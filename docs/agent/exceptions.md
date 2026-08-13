# 예외 대장 (D-206)

§0.4 리팩터링 금지 구역이나 절대금지 항목에 저촉되는 변경을 승인받아 수행한 경우
여기에 기록한다. **기한과 해소 조건이 없는 예외는 예외가 아니라 방치다.**

관리 규칙
- 예외는 사람이 승인한다. 에이전트가 스스로 부여하지 않는다.
- 각 항목은 기한(review_by)을 가진다. 기한이 지나면 Phase Exit 체크리스트에서 걸린다.
- 해소되면 status 를 `resolved` 로 바꾸고 해소 커밋을 적는다. 삭제하지 않는다.

---

## EX-001 — delivery 앱 2개 파일의 하드코딩 시크릿 제거

| | |
|---|---|
| **status** | active |
| **저촉** | §0.4 리팩터링 금지 구역 — `delivery` 앱 (269 파일, 배송 라인) |
| **승인** | 2026-08-13, 사람 승인 ("예외 승인 — 시크릿만 제거") |
| **티켓** | W0-0 |
| **커밋** | `4afca2b` |

### 무엇을 했나

```
backend/delivery/services/opensearch_data.py:21
  OPENSEARCH_USERNAME / OPENSEARCH_PASSWORD 의 하드코딩 기본값 제거 → 빈 문자열
backend/delivery/services/static_map_template.py:56
  HTML 템플릿에 박힌 Kakao JS appkey → os.environ["KAKAO_JS_API_KEY"] 참조
```

### 왜 예외를 허용했나

§0.4 의 취지는 **리팩터링 금지**이지 보안 수정 금지가 아니다.
두 파일은 실제 운영 자격증명을 소스에 담고 있었고, 그대로 두면 W0-0 의 목적
("실키는 단 한 번도 히스토리에 들어가지 않아야 한다")을 달성할 수 없었다.

변경 범위는 **값 → 환경변수 참조**뿐이다. 로직·시그니처·호출 관계를 바꾸지 않았다.

### 위험

- `delivery` 앱은 R1 에서 라이선스 플래그로 숨기기만 하고 손대지 않기로 한 영역이다.
  두 파일에 회귀가 생기면 배송 라인의 OpenSearch 조회와 정적 지도 렌더가 깨진다.
- 특히 `static_map_template.py` 는 `KAKAO_JS_API_KEY` 가 비면 지도가 렌더되지 않는다.
  기존에는 하드코딩 값 덕분에 환경변수 없이도 동작했다 — **동작 조건이 바뀌었다.**

### 해소 조건

- [ ] `KAKAO_JS_API_KEY` 가 배포 환경(dev/stg/prod)의 `.env` 에 설정됨
- [ ] `OPENSEARCH_USERNAME` / `OPENSEARCH_PASSWORD` 가 배포 환경에 설정됨
- [ ] 배송 라인 정적 지도 렌더 1회 육안 확인
- [ ] OpenSearch 조회 1회 육안 확인

**review_by**: R1 Exit (2026-12) — 그때까지 해소되지 않으면 배송 라인 회귀 시험 필수

---

## EX-002 — 프레임워크 모델 7종의 권한 우회 잔존

| | |
|---|---|
| **status** | active |
| **저촉** | 절대금지 #6 의 취지 (권한 우회) — 다만 신규 추가가 아니라 **기존 잔존** |
| **승인** | W0-2 spec 이 명시적으로 지시 ("즉시 제거 대신 뷰 레벨 필터 강제") |
| **티켓** | W0-2 |
| **커밋** | `c1b9825` |

### 무엇이 남아 있나

`backend/common/base_model.py` `performance_bypass_models`

```
coreuser, usergroup, role, userprofilelink, multilanguagecontent, userprofile, group
```

업무 데이터 모델 7종(order·orderitem·orderhistory·payment·ordercomment·
orderassignment·terminal)은 제거했다. 위 7종은 rj-core/dj-core 의존이라
즉시 제거하면 전 화면이 흔들린다(§0.4).

### 대체 통제

`backend/common/tenant_filters.py` — 뷰·서비스 레벨에서 group 필터를 강제한다.
`filter_users_by_group` / `filter_by_group_field` / `get_scoped_or_404`.

### 아직 통제되지 않는 것

헬퍼는 만들었으나 **호출 지점에 적용되지 않았다.** 적용 대상:

- 사용자/역할 목록 API — dj-core(`core.urls`) 안에 있어 이 저장소에서 수정 불가
- `CoreUser.objects.get(id=user_id)` 형태의 단건 조회 30개소 → `get_scoped_or_404` 로 치환 필요

### 해소 조건

- [ ] dj-core 쪽에 동일한 우회 목록이 있는지 확인 (W0-2 blocker A안)
- [ ] 단건 조회 30개소를 `get_scoped_or_404` 로 치환
- [ ] `tests/test_tenant_isolation.py` 의 프레임워크 모델 시나리오 green

**review_by**: R1 Exit (2026-12) — CSAP/SaaS 판매 전 필수

---

## EX-003 — `verify-pending` 상태값이 정본 status_enum 에 없음

| | |
|---|---|
| **status** | active |
| **저촉** | 정본 스키마 위반 (meta.status_enum) |
| **사유** | RESUME_NEXT §1-1 이 지시한 tickets.yaml v2.2 정본이 전달되지 않음 |
| **티켓** | W0-3, W0-2 |

`D-202` 가 도입한 `verify-pending` 을 사용 중이나, 현재 설치된 정본은 v2.0 이고
`meta.status_enum` 은 `[backlog, ready, in_progress, review, done, blocked, dropped]` 다.
`meta` 는 에이전트 수정 권한 밖이라 enum 을 고치지 않았다.

### 해소 조건

- [ ] tickets.yaml v2.2 (manifest.total = 62) 수령 및 교체
- [ ] 교체 후 W0-0/W0-1a/W0-2/W0-3 의 status·evidence 이관

**review_by**: 즉시 — 정본 전달만 되면 해소
