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

    @route.get("/{id}", response=ReportTemplateOutputSchema, auth=CustomJWTAuth())
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

    @route.post("", response=ReportTemplateOutputSchema, auth=CustomJWTAuth())
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

    @route.put("/{id}", response=ReportTemplateOutputSchema, auth=CustomJWTAuth())
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

    @route.delete(
        "/delete/{ids}", response=ReportTemplateOutputSchema, auth=CustomJWTAuth()
    )
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
