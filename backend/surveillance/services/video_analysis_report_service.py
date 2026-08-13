import html as html_lib
import re
from datetime import datetime
from typing import Any, Dict, List, Optional

from config import settings


class VideoAnalysisReportService:
    @staticmethod
    def _scheme() -> str:
        return "https" if getattr(settings, "MINIO_USE_HTTPS", False) else "http"

    @staticmethod
    def normalize_media_url(raw: Optional[str]) -> Optional[str]:
        """
        Normalize different media URL shapes to an absolute URL.

        Examples:
        - "/bucket/path.jpg" -> "http(s)://MINIO_ENDPOINT/bucket/path.jpg"
        - "endpoint/bucket/path.jpg" -> "http(s)://endpoint/bucket/path.jpg"
        - "http(s)://..." -> unchanged
        """
        if not raw:
            return None
        url = str(raw).strip()
        if not url or url == "-":
            return None

        # Allow local cached files (used for WeasyPrint optimization)
        if url.startswith("file://"):
            return url

        if url.startswith("http://") or url.startswith("https://"):
            return url

        scheme = VideoAnalysisReportService._scheme()

        if url.startswith("/"):
            return f"{scheme}://{settings.MINIO_ENDPOINT}{url}"

        # If starts with bucket name, still assume it's at MINIO_ENDPOINT
        bucket = getattr(settings, "MINIO_STORAGE_MEDIA_BUCKET_NAME", "")
        if bucket and url.startswith(f"{bucket}/"):
            return f"{scheme}://{settings.MINIO_ENDPOINT}/{url}"

        # If looks like host/bucket/path (no scheme) -> prefix scheme
        if re.match(r"^[^/]+/[^/]+/.+", url):
            return f"{scheme}://{url}"

        # Fallback: treat as object path under bucket
        if bucket:
            return f"{scheme}://{settings.MINIO_ENDPOINT}/{bucket}/{url.lstrip('/')}"
        return f"{scheme}://{settings.MINIO_ENDPOINT}/{url.lstrip('/')}"

    @staticmethod
    def _safe(value: Any) -> str:
        if value is None:
            return "-"
        s = str(value)
        if not s.strip():
            return "-"
        return html_lib.escape(s)

    @staticmethod
    def build_report_number(video_analysis_id: int) -> str:
        now = datetime.now()
        year = now.year
        month_day = now.strftime("%m%d")
        return f"{year}-{month_day}-{str(video_analysis_id).zfill(4)}"

    @staticmethod
    def _normalize_lang_code(raw: Optional[str]) -> str:
        """
        Normalize different language code shapes to a small supported set.

        Supported: en, ko, th (fallback: en)
        """
        if not raw:
            return "en"
        s = str(raw).strip().lower()
        if not s:
            return "en"
        # common variants
        if s in {"kr", "ko-kr", "ko_kr"}:
            return "ko"
        if s in {"en-us", "en_us", "en-gb", "en_gb"}:
            return "en"
        if s in {"th-th", "th_th"}:
            return "th"
        # direct
        if s in {"en", "ko", "th"}:
            return s
        # tolerate i18n-like codes "ko-KR", "th-TH"
        if "-" in s:
            base = s.split("-", 1)[0]
            if base in {"en", "ko", "th"}:
                return base
        return "en"

    @staticmethod
    def build_video_analysis_report_html(detail: Dict[str, Any], lang: Optional[str] = None) -> str:
        """
        Build an HTML report similar in spirit to FE template `DownloadTemplateVideoAnalysis.tsx`.
        This HTML is intended for WeasyPrint (A4 portrait).
        """
        lang_code = VideoAnalysisReportService._normalize_lang_code(lang or detail.get("_lang"))
        # Mirror FE i18n keys in `frontend/src/i18n/locales/*`.
        # Keep this mapping local to the report generator (fast, no request-context dependency).
        I18N: Dict[str, Dict[str, str]] = {
            "en": {
                "DataAnalysis.ReportTitle": "Drone Flight Mission Execution Report",
                "DataAnalysis.Section01Title": "01. Basic Information",
                "DataAnalysis.Section02Title": "02. Detailed Information",
                "DataAnalysis.Section03Title": "03. AI Video Data Analysis",
                "DataAnalysis.MissionPurpose": "Mission Purpose",
                "DataAnalysis.PersonInCharge": "Person in Charge",
                "DataAnalysis.MissionDateTime": "Mission Date/Time",
                "DataAnalysis.MissionLocation": "Mission Location",
                "DataAnalysis.Aircraft": "Aircraft",
                "DataAnalysis.Operator": "Operator",
                "DataAnalysis.RegistrationNumber": "Registration Number",
                "DataAnalysis.Manufacturer": "Manufacturer",
                "DataAnalysis.FlightDistance": "Flight Distance",
                "DataAnalysis.FlightTime": "Flight Time",
                "DataAnalysis.FlightAltitude": "Flight Altitude",
                "DataAnalysis.FlightType": "Flight Type",
                "DataAnalysis.TakeoffLocation": "Takeoff Location",
                "DataAnalysis.LandingLocation": "Landing Location",
                "DataAnalysis.TakeoffTime": "Takeoff Time",
                "DataAnalysis.LandingTime": "Landing Time",
                "DataAnalysis.Remarks": "Remarks",
                "DataAnalysis.AttachImage": "<Attach Image>",
                "DataAnalysis.Object": "Object",
                "DataAnalysis.NumberOfObjects": "Number of Objects",
                "DataAnalysis.ObjectLocation": "Object Location",
            },
            "ko": {
                "DataAnalysis.ReportTitle": "드론 비행 임무 수행 결과 보고서",
                "DataAnalysis.Section01Title": "01. 기본 정보",
                "DataAnalysis.Section02Title": "02. 세부 정보",
                "DataAnalysis.Section03Title": "03. AI 영상 데이터 분석",
                "DataAnalysis.MissionPurpose": "임무 목적",
                "DataAnalysis.PersonInCharge": "담당자",
                "DataAnalysis.MissionDateTime": "임무 일시",
                "DataAnalysis.MissionLocation": "임무 장소",
                "DataAnalysis.Aircraft": "기체",
                "DataAnalysis.Operator": "운영자",
                "DataAnalysis.RegistrationNumber": "신고번호",
                "DataAnalysis.Manufacturer": "제조사",
                "DataAnalysis.FlightDistance": "비행 거리",
                "DataAnalysis.FlightTime": "비행 시간",
                "DataAnalysis.FlightAltitude": "비행 고도",
                "DataAnalysis.FlightType": "비행 유형",
                "DataAnalysis.TakeoffLocation": "이륙 위치",
                "DataAnalysis.LandingLocation": "착륙 위치",
                "DataAnalysis.TakeoffTime": "이륙 시각",
                "DataAnalysis.LandingTime": "착륙 시각",
                "DataAnalysis.Remarks": "특이사항",
                "DataAnalysis.AttachImage": "<이미지 첨부>",
                "DataAnalysis.Object": "객체",
                "DataAnalysis.NumberOfObjects": "객체 수",
                "DataAnalysis.ObjectLocation": "객체 위치",
            },
            "th": {
                "DataAnalysis.ReportTitle": "รายงานผลการปฏิบัติภารกิจบินโดรน",
                "DataAnalysis.Section01Title": "01. ข้อมูลพื้นฐาน",
                "DataAnalysis.Section02Title": "02. ข้อมูลรายละเอียด",
                "DataAnalysis.Section03Title": "03. การวิเคราะห์ข้อมูลวิดีโอ AI",
                "DataAnalysis.MissionPurpose": "วัตถุประสงค์ภารกิจ",
                "DataAnalysis.PersonInCharge": "ผู้รับผิดชอบ",
                "DataAnalysis.MissionDateTime": "วันที่/เวลาภารกิจ",
                "DataAnalysis.MissionLocation": "สถานที่ภารกิจ",
                "DataAnalysis.Aircraft": "อากาศยาน",
                "DataAnalysis.Operator": "ผู้ดำเนินการ",
                "DataAnalysis.RegistrationNumber": "หมายเลขทะเบียน",
                "DataAnalysis.Manufacturer": "ผู้ผลิต",
                "DataAnalysis.FlightDistance": "ระยะทางบิน",
                "DataAnalysis.FlightTime": "เวลาบิน",
                "DataAnalysis.FlightAltitude": "ระดับความสูงบิน",
                "DataAnalysis.FlightType": "ประเภทการบิน",
                "DataAnalysis.TakeoffLocation": "ตำแหน่งขึ้นบิน",
                "DataAnalysis.LandingLocation": "ตำแหน่งลงจอด",
                "DataAnalysis.TakeoffTime": "เวลาขึ้นบิน",
                "DataAnalysis.LandingTime": "เวลาลงจอด",
                "DataAnalysis.Remarks": "หมายเหตุ",
                "DataAnalysis.AttachImage": "<แนบรูปภาพ>",
                "DataAnalysis.Object": "วัตถุ",
                "DataAnalysis.NumberOfObjects": "จำนวนวัตถุ",
                "DataAnalysis.ObjectLocation": "ตำแหน่งวัตถุ",
            },
        }

        def _t(key: str) -> str:
            # Fallback: en → key
            return I18N.get(lang_code, {}).get(key) or I18N["en"].get(key) or key

        report_number = VideoAnalysisReportService.build_report_number(int(detail.get("id") or 0))

        # ---------------------------
        # Data mapping (must match the provided template)
        # ---------------------------
        # Basic section
        basic_purpose = VideoAnalysisReportService._safe(
            detail.get("purpose") or detail.get("purpose__name") or detail.get("purpose_name")
        )
        basic_person_in_charge = VideoAnalysisReportService._safe(detail.get("operator_name"))
        basic_date = VideoAnalysisReportService._safe(detail.get("start_time") or detail.get("created_at"))
        basic_location = VideoAnalysisReportService._safe(detail.get("mission_location"))
        # Detailed section
        detail_aircraft = VideoAnalysisReportService._safe(detail.get("drone_name"))
        detail_operator = VideoAnalysisReportService._safe(detail.get("operator_name"))
        detail_registration_number = VideoAnalysisReportService._safe(detail.get("register_number"))
        detail_manufacturer = VideoAnalysisReportService._safe(detail.get("manufacturer"))
        detail_flight_distance = VideoAnalysisReportService._safe(detail.get("flight_distance"))
        detail_flight_time = VideoAnalysisReportService._safe(detail.get("flight_time"))
        detail_flight_altitude = VideoAnalysisReportService._safe(detail.get("capture_altitude"))
        detail_flight_type = basic_purpose
        detail_takeoff_location = f"{VideoAnalysisReportService._safe(detail.get('start_point_x'))}, {VideoAnalysisReportService._safe(detail.get('start_point_y'))}"
        detail_landing_location = f"{VideoAnalysisReportService._safe(detail.get('end_point_x'))}, {VideoAnalysisReportService._safe(detail.get('end_point_y'))}"
        detail_takeoff_time = basic_date
        detail_landing_time = VideoAnalysisReportService._safe(detail.get("landing_time"))
        detail_remarks = VideoAnalysisReportService._safe(detail.get("remarks") or detail.get("remark"))

        # AI analysis list + detected images
        analysis_items: List[Dict[str, Any]] = []
        if isinstance(detail.get("analysis"), list):
            analysis_items = detail["analysis"]

        detected_images: List[str] = []
        for item in analysis_items:
            path = item.get("detected_image_path")
            if path and str(path).strip():
                normalized = VideoAnalysisReportService.normalize_media_url(path)
                if normalized:
                    detected_images.append(normalized)
            if len(detected_images) >= 2:
                break

        ai_rows_html: List[str] = []
        for item in analysis_items:
            detections = item.get("detections") or []
            obj_label = "-"
            if isinstance(detections, list) and len(detections) > 0 and isinstance(detections[0], dict):
                obj_label = detections[0].get("label") or "-"

            obj_count = item.get("detection_count") or "-"
            detected_img = VideoAnalysisReportService.normalize_media_url(item.get("detected_image_path"))
            object_location = "-"  # not available in current analysis payload (kept for template compatibility)

            if detected_img:
                location_cell = f"""
                      <div style="display:flex; justify-content:center;">
                        <div class="thumb-table">
                          <div class="img-16-9">
                            <img src="{html_lib.escape(detected_img)}" alt="{html_lib.escape(str(obj_label))}" />
                          </div>
                        </div>
                      </div>
                """
            else:
                location_cell = html_lib.escape(str(object_location))

            ai_rows_html.append(
                f"""
                <tr>
                  <th class="w15">{html_lib.escape(_t('DataAnalysis.Object'))}</th>
                  <td class="w35">{html_lib.escape(str(obj_label))}</td>
                  <th class="w15">{html_lib.escape(_t('DataAnalysis.NumberOfObjects'))}</th>
                  <td class="w35">{VideoAnalysisReportService._safe(obj_count)}</td>
                </tr>
                <tr>
                  <th>{html_lib.escape(_t('DataAnalysis.ObjectLocation'))}</th>
                  <td colspan="3">
                    {location_cell}
                  </td>
                </tr>
                """
            )

        img_1 = detected_images[0] if len(detected_images) > 0 else None
        img_2 = detected_images[1] if len(detected_images) > 1 else None

        detected_img_box_1 = (
            f"""
              <div class="img-wrap">
                <div class="img-16-9">
                  <img src="{html_lib.escape(img_1)}" alt="Detected Image 1" />
                </div>
              </div>
            """
            if img_1
            else f'<div class="placeholder">{html_lib.escape(_t("DataAnalysis.AttachImage"))}</div>'
        )

        detected_img_box_2 = (
            f"""
              <div class="img-wrap">
                <div class="img-16-9">
                  <img src="{html_lib.escape(img_2)}" alt="Detected Image 2" />
                </div>
              </div>
            """
            if img_2
            else f'<div class="placeholder">{html_lib.escape(_t("DataAnalysis.AttachImage"))}</div>'
        )

        report_title = html_lib.escape(_t("DataAnalysis.ReportTitle"))
        section01_title = html_lib.escape(_t("DataAnalysis.Section01Title"))
        section02_title = html_lib.escape(_t("DataAnalysis.Section02Title"))
        section03_title = html_lib.escape(_t("DataAnalysis.Section03Title"))

        return f"""
<!doctype html>

<html>

  <head>

    <meta charset="utf-8" />

    <title>DataAnalysis Report</title>

    <style>

      @page {{ size: A4; margin: 0; }}

      * {{

        -webkit-print-color-adjust: exact !important;

        print-color-adjust: exact !important;

        color-adjust: exact !important;

        box-sizing: border-box;

      }}

      body {{ margin: 0; background: #fff; color: #000; font-family: Arial, 'Noto Sans KR', 'Malgun Gothic', sans-serif; }}

      .page {{

        width: 210mm;

        min-height: 297mm;

        padding: 20mm;

        font-size: 16px;

        line-height: 1.6;

      }}

      h1 {{

        text-align: center;

        font-size: 26px;

        font-weight: 700;

        margin: 0 0 20px 0;

        padding: 5px;

        border: 2px solid #000;

        background: #dae9f8;

      }}

      .report-no {{

        text-align: right;

        margin-bottom: 5px;

        font-size: 14px;

      }}

      /* Allow free page breaking (may cut through sections/rows/images) */
      .section {{ margin-bottom: 15px; page-break-inside: auto; break-inside: auto; }}

      .section-title {{

        font-size: 16px;

        font-weight: 700;

        text-align: center;

        border-top: 2px solid #000;

        border-left: 2px solid #000;

        border-right: 2px solid #000;

        padding: 5px;

        width: 200px;

        background: #a6c8eb;

        margin: 0;

        /* Allow free breaking */
        break-after: auto;
        page-break-after: auto;

      }}

      table {{

        width: 100%;

        border-collapse: collapse;

        border: 2px solid #000;

        page-break-inside: auto;

        break-inside: auto;

      }}

      tr {{ page-break-inside: auto; break-inside: auto; }}

      th, td {{ border: 1px solid #000; padding: 8px; text-align: center; vertical-align: middle; }}

      th.w15 {{ width: 15%; }}

      td.w35 {{ width: 35%; }}

      .images-row {{

        display: flex;

        gap: 0;

        margin-top: 10px;

        margin-bottom: 10px;

        page-break-inside: avoid;

        break-inside: avoid;

      }}

      .image-box {{

        flex: 1;

        border: 2px solid #000;

        min-height: 250px;

        padding: 10px;

        display: flex;

        align-items: center;

        justify-content: center;

        background: #fafafa;

      }}

      .placeholder {{

        font-weight: 700;

        margin-bottom: 10px;

        color: #666;

      }}

      .img-wrap {{

        width: 100%;

        max-width: 500px;

        display: flex;

        align-items: center;

        justify-content: center;

      }}

      .img-16-9 {{

        width: 100%;

        max-width: 500px;

        aspect-ratio: 16/9;

        position: relative;

        overflow: hidden;

      }}

      .img-16-9 img {{

        width: 100%;

        height: 100%;

        object-fit: contain;

        display: block;

      }}

      .thumb-table {{

        max-width: 200px;

        width: 100%;

      }}

      .thumb-table .img-16-9 {{ max-width: 200px; }}

      .thumb-table .img-16-9 img {{ object-fit: contain; }}

      /* For long AI tables, allow splitting across pages to avoid huge whitespace */
      table.ai-table {{
        page-break-inside: auto;
        break-inside: auto;
      }}

    </style>

  </head>

  <body>

    <div class="page">

      <div class="report-no">No. {html_lib.escape(report_number)}</div>

      <h1>{report_title}</h1>

      <!-- Section 01: Basic Information -->

      <div class="section">

        <h2 class="section-title">{section01_title}</h2>

        <table>

          <tbody>

            <tr>

              <th class="w15">{html_lib.escape(_t('DataAnalysis.MissionPurpose'))}</th>

              <td class="w35">{basic_purpose}</td>

              <th class="w15">{html_lib.escape(_t('DataAnalysis.PersonInCharge'))}</th>

              <td class="w35">{basic_person_in_charge}</td>

            </tr>

            <tr>

              <th>{html_lib.escape(_t('DataAnalysis.MissionDateTime'))}</th>

              <td>{basic_date}</td>

              <th>{html_lib.escape(_t('DataAnalysis.MissionLocation'))}</th>

              <td>{basic_location}</td>

            </tr>

          </tbody>

        </table>

      </div>

      <!-- Section 02: Detailed Information -->

      <div class="section">

        <h2 class="section-title">{section02_title}</h2>

        <table>

          <tbody>

            <tr>

              <th class="w15">{html_lib.escape(_t('DataAnalysis.Aircraft'))}</th>

              <td class="w35">{detail_aircraft}</td>

              <th class="w15">{html_lib.escape(_t('DataAnalysis.Operator'))}</th>

              <td class="w35">{detail_operator}</td>

            </tr>

            <tr>

              <th>{html_lib.escape(_t('DataAnalysis.RegistrationNumber'))}</th>

              <td>{detail_registration_number}</td>

              <th>{html_lib.escape(_t('DataAnalysis.Manufacturer'))}</th>

              <td>{detail_manufacturer}</td>

            </tr>

            <tr>

              <th>{html_lib.escape(_t('DataAnalysis.FlightDistance'))}</th>

              <td>{detail_flight_distance}</td>

              <th>{html_lib.escape(_t('DataAnalysis.FlightTime'))}</th>

              <td>{detail_flight_time}</td>

            </tr>

            <tr>

              <th>{html_lib.escape(_t('DataAnalysis.FlightAltitude'))}</th>

              <td>{detail_flight_altitude}</td>

              <th>{html_lib.escape(_t('DataAnalysis.FlightType'))}</th>

              <td>{detail_flight_type}</td>

            </tr>

            <tr>

              <th>{html_lib.escape(_t('DataAnalysis.TakeoffLocation'))}</th>

              <td>{detail_takeoff_location}</td>

              <th>{html_lib.escape(_t('DataAnalysis.LandingLocation'))}</th>

              <td>{detail_landing_location}</td>

            </tr>

            <tr>

              <th>{html_lib.escape(_t('DataAnalysis.TakeoffTime'))}</th>

              <td>{detail_takeoff_time}</td>

              <th>{html_lib.escape(_t('DataAnalysis.LandingTime'))}</th>

              <td>{detail_landing_time}</td>

            </tr>

            <tr>

              <th>{html_lib.escape(_t('DataAnalysis.Remarks'))}</th>

              <td colspan="3">{detail_remarks}</td>

            </tr>

          </tbody>

        </table>

        <!-- 2 detected images -->

        <div class="images-row">

          <div class="image-box">
            {detected_img_box_1}
          </div>

          <div class="image-box">
            {detected_img_box_2}
          </div>

        </div>

      </div>

      <!-- Section 03: AI Video Data Analysis -->

      <div class="section">

        <h2 class="section-title">{section03_title}</h2>

        {(
            f"<table class='ai-table'><tbody>{''.join(ai_rows_html)}</tbody></table>"
            if ai_rows_html
            else f'''
          <table class="ai-table">
            <tbody>
              <tr>
                <th>{html_lib.escape(_t("DataAnalysis.Object"))}</th><td></td>
                <th>{html_lib.escape(_t("DataAnalysis.NumberOfObjects"))}</th><td></td>
              </tr>
              <tr>
                <th>{html_lib.escape(_t("DataAnalysis.ObjectLocation"))}</th><td colspan="3"></td>
              </tr>
            </tbody>
          </table>
            '''
        )}

      </div>

    </div>

  </body>

</html>
        """


