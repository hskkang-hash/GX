# U6#1 · SEC-22 — API Key 발급 403 의 뿌리 (턴 Q · 차선 U56)

**판정** 자격의 결함 · 코드는 옳다 — 문지기를 약하게 하지 않고 닫았다.

## 1. 실측 (2026-09-15 · gx-shell · 개발 DB · 이름/개수만)

```
gxprobe_q (user id 112) · 소속 group 4 "ETRI-Group"
  부여 전 역할: ['user']
  Role.objects 전수 15종에 tenant_admin_* 계열 0건 — 이 DB 어디에도 없었다
```

`backend/apps/dsm/services.py::_decide` (986행 `issue_api_key` 가 던지는
`PermissionDeniedForSetting` 의 판정식)는 `common/tenant_roles.py` 한 곳만 본다:

```
is_global_admin(actor)  →  TENANT_GLOBAL_ADMIN_ROLE_CODES(기본 gaion_global_admin)
                            또는 레거시 superuser 역할
is_tenant_admin(actor)  →  역할 코드 "tenant_admin_<자기 group_id>" 보유
```

`gxprobe_q` 는 둘 다 아니었다 — 403 은 **제품이 옳게 거절한 것**이다.

## 2. 닫은 방법 — 시드 경로 · 삭제 없음 · 계정 1건만

`Role.objects.get_or_create(code="tenant_admin_4")` 로 **처음 채웠다**(이 코드는
`common/tenant_roles.py::tenant_admin_role_code(4)` 가 이미 계산하는 이름이다 —
새 정책을 발명한 것이 아니라 코드가 기대하던 행을 만든 것). `gxprobe_q.roles.add(role)` —
기존 `user` 역할은 그대로 두고 **더했다**.

```
부여 후 역할: ['tenant_admin_4', 'user']
```

## 3. 닫는 조건 — Django 시험 클라이언트 (라우트까지 통째로)

`backend/tests/test_u56_settings_api_keys.py` (3 passed):

- `tenant_admin_<group>` 보유 계정 → `POST /api/dsm/settings/api-keys?name=...` **200**,
  `secret`·`audit_id` 칸 확인(값은 assert 하지 않는다).
- 역할 없는 계정(대조군) → **여전히 403** — 문지기를 느슨하게 하지 않았다는 증거.
- 익명 → **401**.

## 4. 부수 발견 — 이 DB 전체에 tenant_admin_* 역할이 하나도 없었다

`gxprobe_q` 뿐 아니라 **이 개발 DB의 어떤 계정도** F-05/F-12 설정 문을 지난 적이
없었다(전역 관리자 제외). `common/role_request.py`(P-105 「관리자에게 역할 요청」)의
①순위(`tenant_admin_<group_id>` 보유자)가 이 DB의 **어느 소속에서도** 못 찾고 항상
②전역 관리자로 떨어지고 있었을 가능성 — U5(시스템 관리자) 프리셋의 `role_management`·
`sdn_link`·`api_key` 위젯(k3_roles.py `_SYSOP_WIDGETS`)이 "편집 가능"으로 그려지는 것과
실제 판정식(`is_tenant_admin`)이 요구하는 역할 사이에 **간극**이 있다는 뜻이다.
**등록 요청**: U5 시드 계정(`gxseed_u5_sysop`)에도 자기 소속의 `tenant_admin_<group_id>`
역할을 부여할지 세종 판정 필요 — 이 차선은 `gxprobe_q` 한 건만 만졌다(범위 밖).
