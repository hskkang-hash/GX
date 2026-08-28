# 실측 — **DA-01 OPEN-03 의 전제가 틀렸다** (K4 착수 전 확인)

**날짜** 2026-08-30 · **절차** D-210(실측 우선) · D-214(작성자 오류 기록)
**결론** **기저 클래스 변경도, 마이그레이션도, 백필도 필요 없다.** K4 는 막혀 있지 않았다.

---

## 0. 왜 이 문서가 있나

직전 회신에서 저는 *"⑥ 에서 멈춘다 — K4 가 막힌다. `ReportTemplate` 이 `BaseModel`
상속이라 group 격리가 없고(OPEN-03), 고치려면 기존 행 백필이 따라온다"* 고 적었습니다.

**그 판단은 문서를 읽고 내린 것이었고, 실측하지 않았습니다.** 실측하니 전제가 둘 다
틀렸습니다. 그대로 남깁니다 — 되돌린 판단을 지우면 다음 사람이 같은 길로 다시 들어갑니다.

---

## 1. 전제 ① — "`BaseModel` 상속이라 group 격리가 없다" → **틀렸다**

실행 중인 dj-core (`site-packages/core/base.py`) 실측:

```python
# base.py:2059
class BaseModel(TimestampMixin, BaseSoftDeleteCascadeModel, MultiLanguageContentMixin, …):
    created_by  = FK('user.CoreUser', …)
    modified_by = FK('user.CoreUser', …)
    # 🆕 MIGRATION SAFE: Thêm field group với null=True …
    group = models.ForeignKey('user.UserGroup', blank=True, null=True, …)   # ← 2073
    objects = CustomManagerGroup()                                          # ← 2082

# base.py:2382
class BaseModelWithGroup(BaseModel):
    """🔄 DEPRECATED: Sử dụng BaseModel trực tiếp thay thế
    BaseModel đã có field 'group', class này giữ lại để backward compatibility
    Sẽ được remove trong phiên bản tương lai"""
    # ⚠️ MIGRATION NOTE: Không định nghĩa lại field 'group'
    objects = CustomManagerGroup()
```

**`BaseModelWithGroup` 은 그 파일에서 스스로를 DEPRECATED 라 적었고, 필드를 하나도 더
정의하지 않습니다.** `group` FK 도 `CustomManagerGroup` 도 이미 `BaseModel` 에 있습니다.

→ `ReportTemplate(BaseModel)` 의 격리 수준은 `BaseModelWithGroup` 모델과 **같습니다.**

DB 도 그렇게 말합니다:

```
report_template 열: id deleted deleted_by_cascade created_on modified_on
                    name template is_default is_enabled usage_count
                    created_by_id modified_by_id  group_id      ← 이미 있다
```

---

## 2. 전제 ② — "고치려면 기존 행 백필이 따라온다" → **백필할 것이 없다**

```
전체 19행 · soft-deleted 6 · 살아 있는 13
group_id NULL       4행   ← 전부 soft-deleted (id 1·2·3·6)
created_by_id NULL  4행   ← 같은 4행
살아 있는 13행       group_id·created_by_id **전부 채워져 있음** (6개 테넌트에 분산)
```

| id | 이름 | group | created_by | 삭제됨 |
|---|---|---|---|---|
| 1 · 2 · 6 | Default Delivery Report Template | – | – | **예** |
| 3 | Test Template | – | – | **예** |
| 4 · 5 · 11 · 14 · 15 · 16 | (각 고객사 템플릿) | 6 | 43·44·29·53·43·53 | 아니오 |
| 7 · 10 · 13 | … | 4 · 7 · 7 | 16 · 34 · 33 | 아니오 |
| 8 · 9 · 17 · 18 | … | 8 · 8 · 12 · 14 | 69 · 75 · 88 · 97 | 아니오 |

→ **주인 없는 살아 있는 행은 0건입니다.** W0-13 이 다룬 백필 대상이 여기엔 없습니다.
  NULL 인 4행은 전부 지워진 씨앗·시험 잔여물이고, **지워진 행을 백필하는 것은
  소유자를 추측하는 일**이라 D-261 이 이미 금지한 종류입니다.

또한 `report_template.ReportTemplate` 은 **이미 격리 시험 레지스트리에 등재**돼 있고
(인구조사 `covered` · `direct_pk` · 라우트 `/api/report-template/{id}`),
격리 시험 28건이 통과합니다.

---

## 3. 그래서 K4 는 무엇을 했나

기저 클래스도 스키마도 건드리지 않았습니다. **커널만 세웠습니다** —
`backend/kernels/k4_report/`. 마이그레이션 0건.

전제가 다시 바뀌면(사내 패키지가 갱신되어 정말로 갈리면) **시험이 멈춥니다**:

```
tests/test_k4_report_kernel.py::OpenIssuePremiseTest
  test_report_template_has_the_same_isolation_as_grouped_models
  test_base_model_and_base_model_with_group_declare_the_same_tenant_field
```

문서만 고쳐 두면 아무도 모릅니다 — D-286 이 이름 붙인 그대로입니다.

---

## 4. 남은 것 — 이건 진짜다

`BaseModelWithGroup` 이 **DEPRECATED** 라는 사실은 이 저장소 전체에 걸립니다.
지금 8개 앱이 그 클래스를 상속하고 있고(`core.base` 판 · `common.base_model` 판 둘 다),
사내 패키지가 예고대로 그것을 **remove** 하면 그 앱들이 한 번에 깨집니다.

`backend/tests/test_tenant_isolation.py` 머리말이 적은 "BaseModelWithGroup 이 두 개"
문제와 같은 뿌리이고, 이 문서는 그 사실을 **처음으로 실측해 적은 것**입니다.
→ **P-ENV-3 으로 적재**했습니다. 판단 사안입니다(사내 패키지 로드맵 확인 필요).
