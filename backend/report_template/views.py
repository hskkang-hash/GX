"""Report Template API.

W0-18 / P-W0-18-1 — `response=<단일 스키마>` 선언을 이 컨트롤러의 쓰기·상세 라우트에서 뗐다.

핸들러는 전 경로에서 `BaseResponse`(JsonResponse 서브클래스)를 돌려주고, ninja 는
HttpResponse 를 검증 없이 통과시킨다. 즉 그 선언은 **성공 경로에 한 번도 적용된 적이 없다.**
실제로 그 스키마를 통과한 것은 `@path_permission` 이 만든 **권한거부 dict** 뿐이었고,
그것이 검증에서 `{}` 로 소멸했다 — 클라이언트도 감사 로그도 "거부됐다"를 알 수 없었다
(evidence/W0-18/backward_compat_impact.md §1 · response_decl_before_after.md).

소멸하는 까닭은 이 출력 스키마가 `core.common.schema_utils.DynamicSchema` 를 상속해
**선언된 필드가 하나도 없기** 때문이다(`model_fields == {}`). 필드가 없으니 어떤 dict 를
넣어도 `{}` 가 나온다.

선언을 떼면 성공 응답은 한 글자도 바뀌지 않고(어차피 통과였다), 거부는 A 부류가 되어
`common/api_contract.py` 의 미들웨어가 403 으로 승격한다.
**OpenAPI 문서는 이 제거로 바뀌지 않는다** — 필드 없는 스키마라 ninja 가 애초에
응답 본문을 문서에 싣지 않았다(제거 전후 대조 실측). 즉 잃는 문서가 없다.
목록 라우트의 `response=List[...]` 는 그대로 둔다 — 그쪽은 예외로 요란하게 실패하고
미들웨어가 `process_exception` 에서 복원한다(B 부류).
"""

from ninja_extra import api_controller, route
from common.tenant_filters import assert_scoped
from report_template.models import ReportTemplate
from report_template.schemas import (
    ReportTemplateInputSchema,
    ReportTemplateOutputSchema,
)
from typing import List
from core.base import BaseResponse
from core.common.search.dynamic_search import apply_dynamic_filters
from common.constant import MESSAGE_ENUM
from common.pagination import OptimizedPaginator
from core.role.permission import path_permission
from core.api.v1.auth import CustomJWTAuth


@api_controller("/", tags=["Report Template"])
class ReportTemplateController:
    @route.get("", response=List[ReportTemplateOutputSchema], auth=CustomJWTAuth())
    @path_permission("read", path_override="/report-template")
    def list(self, request, page_size: int = 25, current_page: int = 1):
        """
        Get paginated list of report templates with optional filtering and sorting

        Parameters:
        - page_size: Number of items per page
        - current_page: Current page number
        - sort_obj: JSON string for sorting (e.g. {"field": "created_on", "order": "desc"})
        """
        data = ReportTemplate.objects.all().order_by("-id")

        data = apply_dynamic_filters(
            data, request, [], request.GET.get("sort_obj", None)
        )
        # 🚀 OPTIMIZED: Use OptimizedPaginator to automatically optimize COUNT query
        paginator = OptimizedPaginator(data, page_size)
        pages = paginator.page(current_page)
        all_template = ReportTemplateOutputSchema.from_queryset(
            pages.object_list, many=True
        )
        return BaseResponse(
            status_code=200,
            message=MESSAGE_ENUM.get(MESSAGE_ENUM.GET_LIST_REPORT_TEMPLATE_SUCCESS),
            data=all_template,
            total_pages=paginator.num_pages,
            total_items=paginator.count,
            current_page=current_page,
        )

    # W0-18 / P-W0-18-1 — `response=` 를 뗐다 (사유: 이 파일 머리말).
    @route.get("/{id}", auth=CustomJWTAuth())
    @path_permission("read", path_override="/report-template")
    def get(self, request, id: int):
        """
        Get report template detail

        Parameters:
        - id: ID of the report template
        """
        try:
            template_data = ReportTemplate.objects.get(id=id)
            return BaseResponse(
                status_code=200,
                message=MESSAGE_ENUM.get(
                    MESSAGE_ENUM.GET_REPORT_TEMPLATE_DETAIL_SUCCESS
                ),
                data=ReportTemplateOutputSchema.from_queryset(template_data),
            )
        except Exception as e:
            return BaseResponse(
                status_code=404,
                message=MESSAGE_ENUM.get(MESSAGE_ENUM.REPORT_TEMPLATE_NOT_FOUND),
                data=None,
            )

    # W0-18 / P-W0-18-1 — `response=` 를 뗐다 (사유: 이 파일 머리말).
    @route.post("", auth=CustomJWTAuth())
    @path_permission("create", path_override="/report-template")
    def create(self, request, data: ReportTemplateInputSchema):
        """
        Create report template
        Request body:
        - name: Name of the report template
        - template: Template of the report template
        - is_default: Whether the report template is default
        - is_enabled: Whether the report template is enabled
        """
        # If setting this template as default, remove default from all other templates
        if data.is_default:
            ReportTemplate.objects.filter(is_default=True,
                                            created_by__userprofilelink__group=request.user.userprofilelink.group).update(is_default=False)

        created_data = ReportTemplate(
            name=data.name,
            template=data.template,
            is_default=data.is_default,
            is_enabled=data.is_enabled,
        )
        created_data.save()
        return BaseResponse(
            status_code=200,
            message=MESSAGE_ENUM.get(MESSAGE_ENUM.CREATE_REPORT_TEMPLATE_SUCCESS),
            data=ReportTemplateOutputSchema.from_queryset(created_data),
        )

    # W0-18 / P-W0-18-1 — `response=` 를 뗐다 (사유: 이 파일 머리말).
    @route.put("/{id}", auth=CustomJWTAuth())
    @path_permission("update", path_override="/report-template")
    def update(self, request, id: int, data: ReportTemplateInputSchema):
        """
        Update report template

        Parameters:
        - id: ID of the report template

        Request body:
        - name: Name of the report template
        - template: Template of the report template
        - is_default: Whether the report template is default
        - is_enabled: Whether the report template is enabled
        """
        # W0-14c — 남의 테넌트 레코드면 여기서 404. **try 밖에 둔다** — 이 핸들러의
        # except 는 모든 예외를 잡아 본문에 404 를 적고 HTTP 200 으로 내보낸다 (W0-18 대상).
        # 문지기를 try 안에 두면 차단이 200 으로 바뀌어 아무것도 막지 못한다.
        assert_scoped(ReportTemplate, id, request.user)
        try:
            template_instance = ReportTemplate.objects.get(id=id)

            # If setting this template as default, remove default from all other templates
            if data.is_default:
                ReportTemplate.objects.filter(is_default=True,
                                                created_by__userprofilelink__group=request.user.userprofilelink.group).exclude(id=id).update(
                    is_default=False
                )

            for key, value in data.dict().items():
                setattr(template_instance, key, value)
            template_instance.save()
            return BaseResponse(
                status_code=200,
                message=MESSAGE_ENUM.get(MESSAGE_ENUM.UPDATE_REPORT_TEMPLATE_SUCCESS),
                data=ReportTemplateOutputSchema.from_queryset(template_instance),
            )
        except Exception as e:
            return BaseResponse(
                status_code=404,
                message=MESSAGE_ENUM.get(MESSAGE_ENUM.REPORT_TEMPLATE_NOT_FOUND),
                data=None,
            )

    # W0-18 / P-W0-18-1 — `response=` 를 뗐다 (사유: 이 파일 머리말).
    @route.delete("/delete/{ids}", auth=CustomJWTAuth())
    @path_permission("delete", path_override="/report-template")
    def delete(self, request, ids: str):
        """
        Delete report template

        Parameters:
        - ids: Comma-separated IDs of the report templates to delete
        """
        # W0-14c — 문지기는 try 밖이다 (위 update 주석 참조).
        assert_scoped(ReportTemplate, ids, request.user)
        try:
            ids = ids.split(",")
            data_to_delete = []
            for item in ids:
                template_instance = ReportTemplate.objects.get(id=item)
                serialized_data = ReportTemplateOutputSchema.from_queryset(
                    template_instance
                )
                data_to_delete.append(serialized_data)
                template_instance.delete()

            return BaseResponse(
                status_code=200,
                message=MESSAGE_ENUM.get(MESSAGE_ENUM.ACTION_DELETE_SUCCESS),
                data=data_to_delete,
            )
        except Exception as e:
            return BaseResponse(
                status_code=404,
                message=MESSAGE_ENUM.get(MESSAGE_ENUM.ACTION_DELETE_FAILED),
                data=None,
            )
