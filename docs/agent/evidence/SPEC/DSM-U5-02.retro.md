# DSM-U5-02 — 사람이 확인한 제목 부분 표

P-431 · **손으로만 고친다** — 시험·쓰개가 이 파일을 쓰면 반쪽 게이트가 빨강이다.
기계 실측(요청/응답)은 옆 파일 `DSM-U5-02.json` 이다. 아래 json 블록 하나가 정본이다.

```json
{
  "id": "DSM-U5-02",
  "title_parts": [
    {
      "part": "사람별 카메라·기능 권한 매트릭스",
      "where": "backend/apps/dsm/access_permission_service.py::person_permissions (GET /api/dsm/access-log/permissions), tests: test_p376_half_clauses.py::test_sysop_sees_person_camera_and_feature_permissions, test_other_tenants_people_and_cameras_do_not_leak",
      "status": "measured — 별도 evidence JSON 은 없지만 실제 엔드포인트·시험이 존재. 단 카메라 칸은 '사람별'이 아니라 '그룹(테넌트) 단위'로 같은 그룹 전원이 동일 목록을 본다(access_permission_service.py 28~34행 자기 고백 — 사람별 ACL 은 이 제품에 없다)"
    },
    {
      "part": "접속기록 조회(목록)",
      "where": "backend/apps/dsm/access_log_service.py::read (GET /api/dsm/access-log)",
      "status": "measured: evidence GET /api/dsm/access-log 응답에서 security 채널 행 1건 확인"
    },
    {
      "part": "접속기록 CSV 내보내기",
      "where": "backend/apps/dsm/access_log_service.py::read_csv (GET /api/dsm/access-log/export.csv), test: test_p356_u4_spec_promotions.py::test_csv_export_is_a_real_csv_with_bom",
      "status": "measured — CSV 내보내기 실재 시험으로 확인(BOM 포함 실 CSV)"
    },
    {
      "part": "접속기록 1년 이상 보관",
      "where": "backend/common/log_retention_policy.py::enforced_declared_days · backend/common/ops_tasks.py::audit_retention_declared_days · scripts/verify_spec_dsm.py::judge_retention_alignment(④)",
      "status": "measured — 선언이 설정을 그대로 읽는다(항등, 값은 선언이 아니라 설정에서 읽는다 · P-421 ④): log_retention_policy.enforced_declared_days('audit') == ops_tasks.audit_retention_declared_days() (테스트 재대조 365일). 미선언이면 0/None 이 아니라 법정 목표(730일)로 안전하게 대체된다 — '1년 이상' 하한은 두 경우 모두 만족한다. 게이트 scripts/verify_spec_dsm.py 의 ④ 행이 gx-shell 안에서 이 항등을 매 실행 실측 대조한다. 시험: tests.test_ap_n3_u5_02_retention.RetentionDeclarationReadsSettingTest.test_gate_row_and_evidence"
    },
    {
      "part": "완결 조건 「접속기록 조회 ≤ 60초」",
      "where": "backend/tests/test_p356_u4_spec_promotions.py (access-log 관련 테스트 전수 확인 — 응답시간 assert 0건)",
      "status": "measured — GET /api/dsm/access-log 응답시간 0.053초 실측(< 60초, time.perf_counter() 직접 계측 · 대리 지표 0). 시험: tests.test_ap_n3_u5_02_retention.AccessLogQueryPerformanceTest.test_access_log_query_is_under_60_seconds"
    }
  ]
}
```
