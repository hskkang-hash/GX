# W0-18 · P-W0-18-1 A 안 적용 — `response=<단일 스키마>` 8건 제거 전후 실측

**티켓** W0-18 (W0-14 연계) · **판정** P-W0-18-1 `chosen_default: "A"` · **일자** 2026-08-25
**환경** `gx-shell` 컨테이너 (LOCAL_BRINGUP 경로 A) · dj-core 1.1.6 · 운영 DB 무접촉

> **한 줄**: 권한거부가 `{}` 로 소멸하던 라우트가 **8 → 0** 이 됐고, 그 8건이 이제 실제로 **403** 을 낸다.
> **한 줄 더**: 다만 P-W0-18-1 이 A 안의 이득으로 적은 것 중 **"OpenAPI 가 참을 말하게 된다"는 틀렸다** — §4.

---

## 1. 무엇을 고쳤나 — 8줄

`@path_permission` 이 붙은 라우트 중 `response=<단일 스키마>` 를 선언한 8건에서 그 선언만 뗐다.
핸들러 본문·권한 판정·미들웨어는 **한 줄도 건드리지 않았다.**

| # | 라우트 | 파일 |
|---|---|---|
| 1 | `GET /api/report-template/{id}` | `backend/report_template/views.py` |
| 2 | `POST /api/report-template` | 〃 |
| 3 | `PUT /api/report-template/{id}` | 〃 |
| 4 | `DELETE /api/report-template/delete/{ids}` | 〃 |
| 5 | `POST /api/checklist-setting` | `backend/checklist_setting/views.py` |
| 6 | `PUT /api/checklist-setting/{id}` | 〃 |
| 7 | `DELETE /api/checklist-setting/delete/{ids}` | 〃 |
| 8 | `PUT /api/checklist-setting/{id}/activate` | 〃 |

목록 라우트의 `response=List[…]`(B 부류 2건)는 **그대로 뒀다** — 그쪽은 예외로 요란하게
실패하고 미들웨어가 `process_exception` 에서 복원한다. 고칠 이유가 없다.

`checklist_setting` 의 카테고리 컨트롤러(`/categories`)에도 단일 스키마 선언이 둘 있으나
**`@path_permission` 이 없어** 이 분류의 대상이 아니다. 손대지 않았다. (별건 — §5)

---

## 2. 분류 실측 — 8 → 0

```bash
docker exec gx-shell sh -c 'cd /app && python -c "
import sys, os, django; sys.path.insert(0, \"/app\")
os.environ.setdefault(\"DJANGO_SETTINGS_MODULE\", \"config.settings\"); django.setup()
from common.api_contract import classify_permission_routes
print({k: len(v) for k, v in classify_permission_routes().items()})"'
```

| | A `response=` 없음 | B `List[…]` | C 단일 스키마 |
|---|---|---|---|
| 제거 전 (`git stash` 로 되돌려 실측) | 281 | 7 | **8** |
| 제거 후 | **289** | 7 | **0** |

합 296 은 변하지 않는다 — 라우트가 부류를 옮겼을 뿐 늘거나 줄지 않았다.

---

## 3. HTTP 실측 — 세는 것으로는 부족하다

분류가 맞아도 응답이 틀릴 수 있다. 그래서 시험이 실제로 HTTP 를 때린다.

`tests/test_api_contract.py` 신규 2건 (`ROUTE_FORMERLY_SWALLOWED = /api/report-template/1`):

| 시험 | 플래그 | 기대 | 결과 |
|---|---|---|---|
| `test_flag_on_promotes_formerly_swallowed_route` | ON | `403` + `success:false` | **ok** |
| `test_flag_off_formerly_swallowed_route_keeps_200` | OFF | `200` + 거부 본문 | **ok** |

제거 전 같은 요청의 응답은 **`200` + `{}`** 였다(2026-08-24 실측 · `backward_compat_impact.md` §1).

**되돌림 약속은 유지된다** — 플래그 OFF 면 상태는 `200` 그대로다.
다만 OFF 에서도 **본문은 더 이상 `{}` 가 아니다.** 거부 dict 가 실려 나간다.
이것이 선언 제거로 얻은 것이고, **플래그로 되돌아가지 않는 유일한 변화**다.
"거부를 감추는 상태"로는 어떤 설정으로도 돌아가지 않는다 — 되돌리려면 커밋을 되돌려야 한다.

```
Ran 21 tests in 1.639s      (착수 전 19건 → 신규 2건)
OK
```

---

## 4. ★ 정정 — P-W0-18-1 의 A 안 설명 한 줄이 틀렸다

P-W0-18-1 은 A 안의 이득을 이렇게 적었다:

> "OpenAPI 는 거짓 스키마를 잃고 참을 말하게 된다"

**실측하니 틀렸다. OpenAPI 문서는 제거 전후가 완전히 같다.**

```bash
# 제거 후
docker exec gx-shell python /tmp/probe.py /tmp/after.json
git stash push backend/report_template/views.py backend/checklist_setting/views.py
docker exec gx-shell python /tmp/probe.py /tmp/before.json   # 제거 전
git stash pop
diff -u before.json after.json      # → 출력 없음
```

원자료: `openapi_decl_before.json` · `openapi_decl_after.json` (둘이 같다) ·
도구 `scripts/probe_openapi_response_decl.py`

제거 전 `GET /api/report-template/{id}` 의 OpenAPI 응답 선언:

```json
{"200": {"description": "OK"}}
```

**본문 스키마가 애초에 없다.** 까닭은 그 출력 스키마가
`core.common.schema_utils.DynamicSchema` 를 상속해 **선언된 필드가 하나도 없기** 때문이다:

```
ReportTemplateOutputSchema.__mro__ = (…, DynamicSchema, ninja.schema.Schema, pydantic.BaseModel, object)
ReportTemplateOutputSchema.model_fields = {}      # ← 비어 있다
```

같은 사실이 두 증상의 뿌리다:
- **런타임** — 필드가 없으니 어떤 dict 를 검증해도 `{}` 가 나온다. 거부가 소멸한 이유.
- **문서** — 실을 속성이 없으니 ninja 가 응답 본문을 문서에 싣지 않았다. `List[…]` 쪽은
  배열이라 `$ref` 가 남아 문서에 실린다 — 그래서 B 와 C 의 문서 모양이 달랐다.

**즉 잃은 문서가 없다.** A 안의 이득은 "OpenAPI 정직화"가 아니라 **"거부가 다시 보이게 된 것"** 하나다.
이 정정은 판정을 뒤집지 않는다(A 안의 다른 근거는 그대로 성립한다). 다만 **근거 하나가 사실이
아니었다는 것을 남긴다** — 적재는 P-W0-18-4.

---

## 5. 범위 밖에서 눈에 띈 것 (손대지 않음)

`GET /api/checklist-setting/categories/` 는 `auth=` 도 `@path_permission` 도 없다 — 인증 없이
호출되는 라우트다. 이 티켓의 분류(권한거부 응답)에는 잡히지 않지만
**P-W0-18-2(=`@path_permission` 은 있고 `auth=` 는 없는 24건)와 같은 계열**이다.
그 조사에서 함께 다룬다. 여기서는 **적기만 한다.**

---

## 6. 회귀 — 착수 전과 같은가

| 대상 | 착수 전 | 지금 |
|---|---|---|
| `tests.test_api_contract` | 19 OK | **21 OK** |
| `tests.test_external_dependency_degraded` | 11 OK | 11 OK |
| `tests.test_tenant_roles` | 9 OK | 9 OK |
| `tests.test_tenant_filters_scope` | 7 OK | 7 OK |
| `tests.test_route_tenant_scope` | 9 OK | 9 OK |
| `tests.test_tenant_isolation` | 4 failures / 1 error | **4 failures / 1 error** (동일) |
| `manage.py check` | 무이슈 | 무이슈 |

`test_tenant_isolation` 의 4/1 은 P-W0-18-3 이 적재한 §0.4 3건 + 레지스트리 2건이다.
이 작업으로 **늘지도 줄지도 않았다** — 예상대로다. 그 셋은 권한거부가 아니라서
응답 계층도 선언 제거도 닿지 않는다.

---

## 7. 되돌리기

| 무엇 | 어떻게 | 난이도 |
|---|---|---|
| 선언 제거 8줄 | 커밋 되돌리기 1회. 스키마·데이터·마이그레이션 변경이 없다 | **설정** |
| 승격 자체 | `API_CONTRACT_PROMOTE_ERROR_STATUS=false` (기본값) | **설정** |

되돌릴 수 없는 변경: **없다.** 데이터·스키마 무접촉, §0.4 무변경, 시크릿 0건.
