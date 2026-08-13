from core.common.constant import Language
from core.middleware.refresh_token import get_current_request


def get_message(message_dict):
    """
    Get the message in the correct language based on user preferences.
    Falls back to English if the preferred language is not available.

    Args:
        message_dict: The message dictionary containing translations

    Returns:
        str: The translated message
    """
    try:
        request = get_current_request()
        if request.user.language:
            language = request.user.language.code
            if language in message_dict:
                return message_dict[language]
    except Exception:
        # If any error occurs, fall back to English
        pass

    # Default to English if no language preference found or error occurred
    return message_dict[Language.EN]


class MESSAGE_ENUM:
    ACTION_ACTIVATE_SUCCESS = {
        Language.EN: "Activated successfully",
        Language.KR: "활성화되었습니다",
        Language.TH: "Activated successfully",
    }
    ACTION_ACTIVATE_FAILED = {
        Language.EN: "Activation failed",
        Language.KR: "활성화에 실패했습니다",
        Language.TH: "Activation failed",
    }
    ACTION_DEACTIVATE_SUCCESS = {
        Language.EN: "Deactivated successfully",
        Language.KR: "비활성화되었습니다",
        Language.TH: "Deactivated successfully",
    }
    ACTION_DEACTIVATE_FAILED = {
        Language.EN: "Deactivation failed",
        Language.KR: "비활성화에 실패했습니다",
        Language.TH: "Deactivation failed",
    }
    ACTION_DELETE_SUCCESS = {
        Language.EN: "Deleted successfully",
        Language.KR: "삭제되었습니다",
        Language.TH: "Deleted successfully",
    }
    ACTION_DELETE_FAILED = {
        Language.EN: "Deletion failed",
        Language.KR: "삭제에 실패했습니다",
        Language.TH: "Deletion failed",
    }
    ACTION_EXPORT_SUCCESS = {
        Language.EN: "Downloaded successfully",
        Language.KR: "다운로드가 완료되었습니다",
        Language.TH: "Downloaded successfully",
    }
    ACTION_EXPORT_FAILED = {
        Language.EN: "Download failed",
        Language.KR: "다운로드에 실패했습니다",
        Language.TH: "Download failed",
    }
    UPDATE_EXTERNAL_STREAM_MONITOR_SUCCESS = {
        Language.EN: "External stream monitor updated successfully",
        Language.KR: "외부 스트림 모니터 업데이트 성공",
        Language.TH: "อัปเดตสตรีมสำเร็จ",
    }
    UPDATE_EXTERNAL_STREAM_MONITOR_FAILED = {
        Language.EN: "External stream monitor update failed",
        Language.KR: "외부 스트림 모니터 업데이트 실패",
        Language.TH: "อัปเดตสตรีมล้มเหลว",
    }
    DELETE_FLIGHT_LOG_SUCCESS = {
        Language.EN: "Flight log deleted successfully",
        Language.KR: "항공 로그 삭제 성공",
        Language.TH: "ลบบันทึกการบินสำเร็จ",
    }
    DELETE_FLIGHT_LOG_FAILED = {
        Language.EN: "Flight log deletion failed",
        Language.KR: "항공 로그 삭제 실패",
        Language.TH: "ลบบันทึกการบินล้มเหลว",
    }
    DELETE_EXTERNAL_STREAM_MONITOR_SUCCESS = {
        Language.EN: "External stream monitor deleted successfully",
        Language.KR: "외부 스트림 모니터 삭제 성공",
        Language.TH: "ลบสตรีมสำเร็จ",
    }
    DELETE_EXTERNAL_STREAM_MONITOR_FAILED = {
        Language.EN: "External stream monitor deletion failed",
        Language.KR: "외부 스트림 모니터 삭제 실패",
        Language.TH: "ลบสตรีมล้มเหลว",
    }
    DELETE_FUNC_TYPE_SUCCESS = {
        Language.EN: "Function type deleted successfully",
        Language.KR: "함수 유형 삭제 성공",
        Language.TH: "ลบประเภทฟังก์ชันสำเร็จ",
    }
    DELETE_FUNC_TYPE_FAILED = {
        Language.EN: "Function type deletion failed",
        Language.KR: "함수 유형 삭제 실패",
        Language.TH: "ลบประเภทฟังก์ชันล้มเหลว",
    }
    DOWNLOAD_ANALYSIS_SUCCESS = {
        Language.EN: "Analysis downloaded successfully",
        Language.KR: "분석 다운로드 성공",
        Language.TH: "ดาวน์โหลดการวิเคราะห์สำเร็จ",
    }
    DOWNLOAD_ANALYSIS_FAILED = {
        Language.EN: "Analysis download failed",
        Language.KR: "분석 다운로드 실패",
        Language.TH: "ดาวน์โหลดการวิเคราะห์ล้มเหลว",
    }
    MEDIA_DETECT_OBJECT_FOUND = {
        Language.EN: "Detected {object_name}.",
        Language.KR: "{object_name} 감지됨.",
        Language.TH: "ตรวจพบ {object_name}.",
    }
    GET_WEATHER_SETTING_SUCCESS = {
        Language.EN: "Weather setting fetched successfully",
        Language.KR: "날씨 설정 가져오기 성공",
        Language.TH: "ดึงข้อมูลการตั้งค่าภายนอกสำเร็จ",
    }
    LIBRARY_REGISTRATION_NUMBER_ALREADY_EXISTS = {
        Language.EN: "Library registration number already exists",
        Language.KR: "입력하신 신고번호는 이미 등록된 신고번호입니다",
        Language.TH: "รหัสลิบรารี่ที่ระบุมีอยู่แล้ว",
    }
    DEVICE_REGISTRATION_NUMBER_ALREADY_EXISTS = {
        Language.EN: "Device registration number already exists",
        Language.KR: "드론 번호가 이미 등록되었습니다",
        Language.TH: "หมายเลขดอร์นมีอยู่แล้ว",
    }
    STOP_REPEAT_SURVEILLANCE_PROFILE_SUCCESS = {
        Language.EN: "Surveillance profile repeat stopped successfully",
        Language.KR: "정찰 프로파일 반복 중지 성공",
        Language.TH: "การดำเนินการสำเร็จ",
    }
    STOP_REPEAT_SURVEILLANCE_PROFILE_FAILED = {
        Language.EN: "Surveillance profile repeat stop failed",
        Language.KR: "정찰 프로파일 반복 중지 실패",
        Language.TH: "การดำเนินการล้มเหลว",
    }
    CANCEL_SURVEILLANCE_PROFILE_SUCCESS = {
        Language.EN: "Surveillance profile canceled successfully",
        Language.KR: "정찰 프로파일 취소 성공",
        Language.TH: "การดำเนินการสำเร็จ",
    }
    CANCEL_SURVEILLANCE_PROFILE_FAILED = {
        Language.EN: "Surveillance profile cancellation failed",
        Language.KR: "정찰 프로파일 취소 실패",
        Language.TH: "การดำเนินการล้มเหลว",
    }
    SURVEILLANCE_PROFILE_DRONE_ISSUE_CANCEL_REASON = {
        Language.EN: "The drone encountered an issue during the mission.",
        Language.KR: "드론이 임무 수행 중 문제를 발생했습니다.",
        Language.TH: "โดรนพบปัญหาระหว่างการปฏิบัติภารกิจ",
    }
    COMPLETED_SURVEILLANCE_PROFILE_SUCCESS = {
        Language.EN: "Surveillance profile completed successfully",
        Language.KR: "정찰 프로파일 완료 성공",
        Language.TH: "การดำเนินการสำเร็จ",
    }
    COMPLETED_SURVEILLANCE_PROFILE_FAILED = {
        Language.EN: "Surveillance profile completion failed",
        Language.KR: "정찰 프로파일 완료 실패",
        Language.TH: "การดำเนินการล้มเหลว",
    }
    NO_SUITABLE_DEVICE_FOUND = {
        Language.EN: "No suitable device found",
        Language.KR: "적합한 장치를 찾을 수 없습니다",
        Language.TH: "ไม่พบอุปกรณ์ที่เหมาะสม",
    }
    DRONE_UNAVAILABLE_CANCEL_REASON = {
        Language.EN: "Profile cancelled because assigned drones are performing other missions",
        Language.KR: "할당 드론이 다른 임무 수행 중으로 프로파일 취소됨",
        Language.TH: "ยกเลิกโปรไฟล์เนื่องจากโดรนที่กำหนดกำลังปฏิบัติภารกิจอื่น",
    }
    SURVEILLANCE_PROFILE_PREEMPTED_CANCEL_REASON = {
        Language.EN: "Profile cancelled because its drones were preempted by another profile with an earlier start time",
        Language.KR: "더 이른 시작 시간의 다른 프로파일이 드론을 선점하여 프로파일이 취소되었습니다",
        Language.TH: "ยกเลิกโปรไฟล์เนื่องจากโดรนถูกโปรไฟล์อื่นที่เริ่มก่อนหน้าชิงไป",
    }
    DEACTIVATE_DELIVERY_HUB_WITH_DOCKING_IN_OTHER_ROUTE = {
        Language.EN: "Cannot deactivate hub {hub_name} (ID: {hub_id}) because there are dockings in other routes. Route IDs: {route_ids}",
        Language.KR: "다른 경로에 연결된 배달점이 있으므로 배달거점 {hub_name} (ID: {hub_id})를 비활성화할 수 없습니다. 관련 경로 ID: {route_ids}",
        Language.TH: "ไม่สามารถปิดใช้งานฮับ {hub_name} (ID: {hub_id}) ได้เนื่องจากมี docking ในเส้นทางอื่น Route IDs: {route_ids}",
    }
    DOWNLOAD_ANALYSIS_SUCCESS = {
        Language.EN: "Analysis downloaded successfully",
        Language.KR: "분석 다운로드 성공",
        Language.TH: "ดาวน์โหลดการวิเคราะห์สำเร็จ",
    }
    DOWNLOAD_ANALYSIS_FAILED = {
        Language.EN: "Analysis download failed",
        Language.KR: "분석 다운로드 실패",
        Language.TH: "ดาวน์โหลดการวิเคราะห์ล้มเหลว",
    }

    # Terminal messages
    GET_LIST_TERMINAL_SUCCESS = {
        Language.EN: "Terminals fetched successfully",
        Language.KR: "터미널 목록 가져오기 성공",
        Language.TH: "รายการคอมพิวเตอร์ที่เชื่อมต่อได้สำเร็จ",
    }
    GET_TERMINAL_DETAIL_SUCCESS = {
        Language.EN: "Terminal fetched successfully",
        Language.KR: "터미널 정보 가져오기 성공",
        Language.TH: "ดึงข้อมูลเทอร์มินัลสำเร็จ",
    }
    CREATE_TERMINAL_SUCCESS = {
        Language.EN: "Terminal created successfully",
        Language.KR: "터미널 생성 성공",
        Language.TH: "สร้างเทอร์มินัลสำเร็จ",
    }
    UPDATE_TERMINAL_SUCCESS = {
        Language.EN: "Terminal updated successfully",
        Language.KR: "터미널 업데이트 성공",
        Language.TH: "อัปเดตเทอร์มินัลสำเร็จ",
    }
    UPDATE_TERMINAL_FAILED = {
        Language.EN: "Terminal updated failed",
        Language.KR: "터미널 업데이트 실패",
        Language.TH: "อัปเดตเทอร์มินัลล้มเหลว",
    }
    DELETE_TERMINAL_SUCCESS = {
        Language.EN: "Terminal deleted successfully",
        Language.KR: "터미널 삭제 성공",
        Language.TH: "ลบเทอร์มินัลสำเร็จ",
    }
    CHANGE_STATUS_SUCCESS = {
        Language.EN: "Status changed successfully",
        Language.KR: "배달거점 상태 변경",
        Language.TH: "เปลี่ยนสถานะสำเร็จ",
    }
    CHANGE_STATUS_FAILED = {
        Language.EN: "Status change failed, terminals are in use",
        Language.KR: "터미널 상태 변경 실패, 터미널이 사용 중입니다",
        Language.TH: "เปลี่ยนสถานะล้มเหลว เทอร์มินัลกำลังใช้งานอยู่",
    }
    # Terminal Operating Time messages
    GET_LIST_OPERATING_TIME_SUCCESS = {
        Language.EN: "Operating times fetched successfully",
        Language.KR: "운영 시간 목록 가져오기 성공",
        Language.TH: "ดึงรายการเวลาทำงานสำเร็จ",
    }
    GET_OPERATING_TIME_DETAIL_SUCCESS = {
        Language.EN: "Operating time fetched successfully",
        Language.KR: "운영 시간 정보 가져오기 성공",
        Language.TH: "ดึงข้อมูลเวลาทำงานสำเร็จ",
    }
    CREATE_OPERATING_TIME_SUCCESS = {
        Language.EN: "Operating time created successfully",
        Language.KR: "운영 시간 생성 성공",
        Language.TH: "สร้างเวลาทำงานสำเร็จ",
    }
    UPDATE_OPERATING_TIME_SUCCESS = {
        Language.EN: "Operating time updated successfully",
        Language.KR: "운영 시간 업데이트 성공",
        Language.TH: "อัปเดตเวลาทำงานสำเร็จ",
    }
    DELETE_OPERATING_TIME_SUCCESS = {
        Language.EN: "Operating time deleted successfully",
        Language.KR: "운영 시간 삭제 성공",
        Language.TH: "ลบเวลาทำงานสำเร็จ",
    }
    # Terminal Exception messages
    GET_LIST_EXCEPTION_SUCCESS = {
        Language.EN: "Exceptions fetched successfully",
        Language.KR: "예외 목록 가져오기 성공",
        Language.TH: "ดึงรายการข้อยกเว้นสำเร็จ",
    }
    GET_EXCEPTION_DETAIL_SUCCESS = {
        Language.EN: "Exception fetched successfully",
        Language.KR: "예외 정보 가져오기 성공",
        Language.TH: "ดึงข้อมูลข้อยกเว้นสำเร็จ",
    }
    CREATE_EXCEPTION_SUCCESS = {
        Language.EN: "Exception created successfully",
        Language.KR: "예외 생성 성공",
        Language.TH: "สร้างข้อยกเว้นสำเร็จ",
    }
    UPDATE_EXCEPTION_SUCCESS = {
        Language.EN: "Exception updated successfully",
        Language.KR: "예외 업데이트 성공",
        Language.TH: "อัปเดตข้อยกเว้นสำเร็จ",
    }
    DELETE_EXCEPTION_SUCCESS = {
        Language.EN: "Exception deleted successfully",
        Language.KR: "예외 삭제 성공",
        Language.TH: "ลบข้อยกเว้นสำเร็จ",
    }
    # Terminal Type messages
    GET_LIST_TERMINAL_TYPE_SUCCESS = {
        Language.EN: "Terminal types fetched successfully",
        Language.KR: "터미널 유형 목록 가져오기 성공",
        Language.TH: "ดึงรายการประเภทเทอร์มินัลสำเร็จ",
    }
    GET_TERMINAL_TYPE_DETAIL_SUCCESS = {
        Language.EN: "Terminal type fetched successfully",
        Language.KR: "터미널 유형 정보 가져오기 성공",
        Language.TH: "ดึงข้อมูลประเภทเทอร์มินัลสำเร็จ",
    }
    CREATE_TERMINAL_TYPE_SUCCESS = {
        Language.EN: "Terminal type created successfully",
        Language.KR: "터미널 유형 생성 성공",
        Language.TH: "สร้างประเภทเทอร์มินัลสำเร็จ",
    }
    UPDATE_TERMINAL_TYPE_SUCCESS = {
        Language.EN: "Terminal type updated successfully",
        Language.KR: "터미널 유형 업데이트 성공",
        Language.TH: "อัปเดตประเภทเทอร์มินัลสำเร็จ",
    }
    DELETE_TERMINAL_TYPE_SUCCESS = {
        Language.EN: "Terminal type deleted successfully",
        Language.KR: "터미널 유형 삭제 성공",
        Language.TH: "ลบประเภทเทอร์มินัลสำเร็จ",
    }

    # Route messages
    GET_LIST_ROUTE_SUCCESS = {
        Language.EN: "Routes fetched successfully",
        Language.KR: "경로 목록 가져오기 성공",
        Language.TH: "ดึงรายการเส้นทางสำเร็จ",
    }
    GET_ROUTE_DETAIL_SUCCESS = {
        Language.EN: "Route fetched successfully",
        Language.KR: "경로 정보 가져오기 성공",
        Language.TH: "ดึงข้อมูลเส้นทางสำเร็จ",
    }
    CREATE_ROUTE_SUCCESS = {
        Language.EN: "Route created successfully",
        Language.KR: "경로 생성 성공",
        Language.TH: "สร้างเส้นทางสำเร็จ",
    }
    UPDATE_ROUTE_SUCCESS = {
        Language.EN: "Route updated successfully",
        Language.KR: "경로가 성공적으로 업로드되었습니다",
        Language.TH: "เส้นทางได้รับการอัปเดตเรียบร้อยแล้ว",
    }
    DELETE_ROUTE_SUCCESS = {
        Language.EN: "Route deleted successfully",
        Language.KR: "경로 삭제 성공",
        Language.TH: "ลบเส้นทางสำเร็จ",
    }

    GET_LIST_DEVICE_SUCCESS = {
        Language.EN: "Devices fetched successfully",
        Language.KR: "장치 목록 가져오기 성공",
        Language.TH: "ดึงรายการอุปกรณ์สำเร็จ",
    }
    GET_DEVICE_DETAIL_SUCCESS = {
        Language.EN: "Device fetched successfully",
        Language.KR: "장치 정보 가져오기 성공",
        Language.TH: "ดึงข้อมูลอุปกรณ์สำเร็จ",
    }
    CREATE_DEVICE_SUCCESS = {
        Language.EN: "Device created successfully",
        Language.KR: "장치 생성 성공",
        Language.TH: "สร้างอุปกรณ์สำเร็จ",
    }
    UPDATE_DEVICE_SUCCESS = {
        Language.EN: "Device updated successfully",
        Language.KR: "경로가 성공적으로 업로드되었습니다",
        Language.TH: "อัปเดตอุปกรณ์สำเร็จ",
    }
    UPDATE_STATUS_DRONE_ROBOT_SUCCESS = {
        Language.EN: "Drone and robot information updated successfully",
        Language.KR: "장치 정보 업데이트가 완료되었습니다",
        Language.TH: "อัปเดตอุปกรณ์สำเร็จสำเร็จ",
    }
    EDIT_DEVICE_SUCCESS = {
        Language.EN: "Drone and robot information updated successfully",
        Language.KR: "장치 정보 업데이트가 완료되었습니다",
        Language.TH: "อัปเดตอุปกรณ์สำเร็จ",
    }
    UPDATE_DEVICE_FAILED = {
        Language.EN: "Device update failed",
        Language.KR: "장치 업데이트 실패",
        Language.TH: "อัปเดตอุปกรณ์ล้มเหลว",
    }
    DELETE_DEVICE_SUCCESS = {
        Language.EN: "Device deleted successfully",
        Language.KR: "장치 삭제 성공",
        Language.TH: "ลบอุปกรณ์สำเร็จ",
    }
    DELETE_DEVICE_FAILED = {
        Language.EN: "Device delete failed",
        Language.KR: "장치 삭제 실패",
        Language.TH: "ลบอุปกรณ์ล้มเหลว",
    }
    DEVICE_IN_USE_CANNOT_DELETE = {
        Language.EN: "Cannot delete device(s) because they are currently in use in delivery operations",
        Language.KR: "장치가 현재 배송 작업에 사용 중이므로 삭제할 수 없습니다",
        Language.TH: "ไม่สามารถลบอุปกรณ์ได้เนื่องจากกำลังใช้งานในการดำเนินการจัดส่ง",
    }

    # Protocol messages
    GET_LIST_PROTOCOL_SUCCESS = {
        Language.EN: "Protocols fetched successfully",
        Language.KR: "프로토콜 목록 가져오기 성공",
        Language.TH: "ดึงรายการโปรโตคอลสำเร็จ",
    }
    GET_PROTOCOL_DETAIL_SUCCESS = {
        Language.EN: "Protocol fetched successfully",
        Language.KR: "프로토콜 정보 가져오기 성공",
        Language.TH: "ดึงข้อมูลโปรโตคอลสำเร็จ",
    }
    CREATE_PROTOCOL_SUCCESS = {
        Language.EN: "Protocol created successfully",
        Language.KR: "프로토콜 생성 성공",
        Language.TH: "สร้างโปรโตคอลสำเร็จ",
    }
    UPDATE_PROTOCOL_SUCCESS = {
        Language.EN: "Protocol updated successfully",
        Language.KR: "프로토콜 업데이트 성공",
        Language.TH: "อัปเดตโปรโตคอลสำเร็จ",
    }
    DELETE_PROTOCOL_SUCCESS = {
        Language.EN: "Protocol deleted successfully",
        Language.KR: "프로토콜 삭제 성공",
        Language.TH: "ลบโปรโตคอลสำเร็จ",
    }

    # Motor Type messages
    GET_LIST_MOTOR_TYPE_SUCCESS = {
        Language.EN: "Motor types fetched successfully",
        Language.KR: "모터 유형 목록 가져오기 성공",
        Language.TH: "ดึงรายการประเภทมอเตอร์สำเร็จ",
    }
    GET_MOTOR_TYPE_DETAIL_SUCCESS = {
        Language.EN: "Motor type fetched successfully",
        Language.KR: "모터 유형 정보 가져오기 성공",
        Language.TH: "ดึงข้อมูลประเภทมอเตอร์สำเร็จ",
    }
    CREATE_MOTOR_TYPE_SUCCESS = {
        Language.EN: "Motor type created successfully",
        Language.KR: "모터 유형 생성 성공",
        Language.TH: "สร้างประเภทมอเตอร์สำเร็จ",
    }
    UPDATE_MOTOR_TYPE_SUCCESS = {
        Language.EN: "Motor type updated successfully",
        Language.KR: "모터 유형 업데이트 성공",
        Language.TH: "อัปเดตประเภทมอเตอร์สำเร็จ",
    }
    DELETE_MOTOR_TYPE_SUCCESS = {
        Language.EN: "Motor type deleted successfully",
        Language.KR: "모터 유형 삭제 성공",
        Language.TH: "ลบประเภทมอเตอร์สำเร็จ",
    }

    # Battery Type messages
    GET_LIST_BATTERY_TYPE_SUCCESS = {
        Language.EN: "Battery types fetched successfully",
        Language.KR: "배터리 유형 목록 가져오기 성공",
        Language.TH: "ดึงรายการประเภทแบตเตอรี่สำเร็จ",
    }
    GET_BATTERY_TYPE_DETAIL_SUCCESS = {
        Language.EN: "Battery type fetched successfully",
        Language.KR: "배터리 유형 정보 가져오기 성공",
        Language.TH: "ดึงข้อมูลประเภทแบตเตอรี่สำเร็จ",
    }
    CREATE_BATTERY_TYPE_SUCCESS = {
        Language.EN: "Battery type created successfully",
        Language.KR: "배터리 유형 생성 성공",
        Language.TH: "สร้างประเภทแบตเตอรี่สำเร็จ",
    }
    UPDATE_BATTERY_TYPE_SUCCESS = {
        Language.EN: "Battery type updated successfully",
        Language.KR: "배터리 유형 업데이트 성공",
        Language.TH: "อัปเดตประเภทแบตเตอรี่สำเร็จ",
    }
    DELETE_BATTERY_TYPE_SUCCESS = {
        Language.EN: "Battery type deleted successfully",
        Language.KR: "배터리 유형 삭제 성공",
        Language.TH: "ลบประเภทแบตเตอรี่สำเร็จ",
    }

    # IMU messages
    GET_LIST_IMU_SUCCESS = {
        Language.EN: "IMUs fetched successfully",
        Language.KR: "IMU 목록 가져오기 성공",
        Language.TH: "ดึงรายการ IMU สำเร็จ",
    }
    GET_IMU_DETAIL_SUCCESS = {
        Language.EN: "IMU fetched successfully",
        Language.KR: "IMU 정보 가져오기 성공",
        Language.TH: "ดึงข้อมูล IMU สำเร็จ",
    }
    CREATE_IMU_SUCCESS = {
        Language.EN: "IMU created successfully",
        Language.KR: "IMU 생성 성공",
        Language.TH: "สร้าง IMU สำเร็จ",
    }
    UPDATE_IMU_SUCCESS = {
        Language.EN: "IMU updated successfully",
        Language.KR: "IMU 업데이트 성공",
        Language.TH: "อัปเดต IMU สำเร็จ",
    }
    DELETE_IMU_SUCCESS = {
        Language.EN: "IMU deleted successfully",
        Language.KR: "IMU 삭제 성공",
        Language.TH: "ลบ IMU สำเร็จ",
    }

    # Image Stabilization messages
    GET_LIST_IMAGE_STABILIZATION_SUCCESS = {
        Language.EN: "Image stabilizations fetched successfully",
        Language.KR: "이미지 안정화 목록 가져오기 성공",
        Language.TH: "ดึงรายการการปรับภาพให้คงที่สำเร็จ",
    }
    GET_IMAGE_STABILIZATION_DETAIL_SUCCESS = {
        Language.EN: "Image stabilization fetched successfully",
        Language.KR: "이미지 안정화 정보 가져오기 성공",
        Language.TH: "ดึงข้อมูลการปรับภาพให้คงที่สำเร็จ",
    }
    CREATE_IMAGE_STABILIZATION_SUCCESS = {
        Language.EN: "Image stabilization created successfully",
        Language.KR: "이미지 안정화 생성 성공",
        Language.TH: "สร้างการปรับภาพให้คงที่สำเร็จ",
    }
    UPDATE_IMAGE_STABILIZATION_SUCCESS = {
        Language.EN: "Image stabilization updated successfully",
        Language.KR: "이미지 안정화 업데이트 성공",
        Language.TH: "อัปเดตการปรับภาพให้คงที่สำเร็จ",
    }
    DELETE_IMAGE_STABILIZATION_SUCCESS = {
        Language.EN: "Image stabilization deleted successfully",
        Language.KR: "이미지 안정화 삭제 성공",
        Language.TH: "ลบการปรับภาพให้คงที่สำเร็จ",
    }

    # GNSS System messages
    GET_LIST_GNSS_SYSTEM_SUCCESS = {
        Language.EN: "GNSS systems fetched successfully",
        Language.KR: "GNSS 시스템 목록 가져오기 성공",
        Language.TH: "ดึงรายการระบบ GNSS สำเร็จ",
    }
    GET_GNSS_SYSTEM_DETAIL_SUCCESS = {
        Language.EN: "GNSS system fetched successfully",
        Language.KR: "GNSS 시스템 정보 가져오기 성공",
        Language.TH: "ดึงข้อมูลระบบ GNSS สำเร็จ",
    }
    CREATE_GNSS_SYSTEM_SUCCESS = {
        Language.EN: "GNSS system created successfully",
        Language.KR: "GNSS 시스템 생성 성공",
        Language.TH: "สร้างระบบ GNSS สำเร็จ",
    }
    UPDATE_GNSS_SYSTEM_SUCCESS = {
        Language.EN: "GNSS system updated successfully",
        Language.KR: "GNSS 시스템 업데이트 성공",
        Language.TH: "อัปเดตระบบ GNSS สำเร็จ",
    }
    DELETE_GNSS_SYSTEM_SUCCESS = {
        Language.EN: "GNSS system deleted successfully",
        Language.KR: "GNSS 시스템 삭제 성공",
        Language.TH: "ลบระบบ GNSS สำเร็จ",
    }

    # Package Type messages
    GET_LIST_PACKAGE_TYPE_SUCCESS = {
        Language.EN: "Package types fetched successfully",
        Language.KR: "패키지 유형 목록 가져오기 성공",
        Language.TH: "ดึงรายการประเภทแพ็คเกจสำเร็จ",
    }
    GET_PACKAGE_TYPE_DETAIL_SUCCESS = {
        Language.EN: "Package type fetched successfully",
        Language.KR: "패키지 유형 정보 가져오기 성공",
        Language.TH: "ดึงข้อมูลประเภทแพ็คเกจสำเร็จ",
    }
    CREATE_PACKAGE_TYPE_SUCCESS = {
        Language.EN: "Package type created successfully",
        Language.KR: "패키지 유형 생성 성공",
        Language.TH: "สร้างประเภทแพ็คเกจสำเร็จ",
    }
    UPDATE_PACKAGE_TYPE_SUCCESS = {
        Language.EN: "Package type updated successfully",
        Language.KR: "패키지 유형 업데이트 성공",
        Language.TH: "อัปเดตประเภทแพ็คเกจสำเร็จ",
    }
    DELETE_PACKAGE_TYPE_SUCCESS = {
        Language.EN: "Package type deleted successfully",
        Language.KR: "패키지 유형 삭제 성공",
        Language.TH: "ลบประเภทแพ็คเกจสำเร็จ",
    }
    GET_LIST_PACKAGING_SPECIFICATION_SUCCESS = {
        Language.EN: "Packaging specifications fetched successfully",
        Language.KR: "패키징 사양 목록 가져오기 성공",
        Language.TH: "ดึงรายการข้อกำหนดการบรรจุหีบห่อสำเร็จ",
    }
    GET_PACKAGING_SPECIFICATION_DETAIL_SUCCESS = {
        Language.EN: "Packaging specification detail fetched successfully",
        Language.KR: "패키징 사양 상세 가져오기 성공",
        Language.TH: "ดึงรายละเอียดข้อกำหนดการบรรจุหีบห่อสำเร็จ",
    }
    CREATE_PACKAGING_SPECIFICATION_SUCCESS = {
        Language.EN: "Packaging specification created successfully",
        Language.KR: "적재함이 성공적으로 생성되었습니다",
        Language.TH: "สร้างข้อกำหนดการบรรจุหีบห่อสำเร็จ",
    }
    CREATE_PACKAGING_SPECIFICATION_FAILED = {
        Language.EN: "Packaging specification created failed",
        Language.KR: "패키징 사양 생성 실패",
        Language.TH: "สร้างข้อกำหนดการบรรจุหีบห่อล้มเหลว",
    }
    UPDATE_PACKAGING_SPECIFICATION_SUCCESS = {
        Language.EN: "Packaging specification updated successfully",
        Language.KR: "적재함이 성공적으로 업데이트되었습니다",
        Language.TH: "อัปเดตข้อกำหนดการบรรจุหีบห่อสำเร็จ",
    }
    UPDATE_PACKAGING_SPECIFICATION_FAILED = {
        Language.EN: "Packaging specification updated failed",
        Language.KR: "패키징 사양 업데이트 실패",
        Language.TH: "อัปเดตข้อกำหนดการบรรจุหีบห่อล้มเหลว",
    }
    DELETE_PACKAGING_SPECIFICATION_SUCCESS = {
        Language.EN: "Packaging specification deleted successfully",
        Language.KR: "패키징 사양 삭제 성공",
        Language.TH: "ลบข้อกำหนดการบรรจุหีบห่อสำเร็จ",
    }
    PACKAGING_DIMENSIONS_REQUIRED = {
        Language.EN: "Dimensions are required for packaging specification",
        Language.KR: "패키징 사양에는 치수가 필요합니다",
        Language.TH: "ต้องระบุขนาดสำหรับข้อกำหนดการบรรจุหีบห่อ",
    }
    PACKAGING_MAX_WEIGHT_REQUIRED = {
        Language.EN: "Max weight is required for packaging specification",
        Language.KR: "패키징 사양에는 최대 무게가 필요합니다",
        Language.TH: "ต้องระบุน้ำหนักสูงสุดสำหรับข้อกำหนดการบรรจุหีบห่อ",
    }
    INVALID_PACKAGING_DIMENSIONS_FORMAT = {
        Language.EN: "Invalid packaging dimensions format",
        Language.KR: "잘못된 패키징 치수 형식",
        Language.TH: "รูปแบบขนาดการบรรจุหีบห่อไม่ถูกต้อง",
    }
    INVALID_PACKAGING_MAX_WEIGHT_FORMAT = {
        Language.EN: "Invalid packaging max weight format",
        Language.KR: "잘못된 패키징 최대 무게 형식",
        Language.TH: "รูปแบบน้ำหนักสูงสุดการบรรจุหีบห่อไม่ถูกต้อง",
    }
    CREATE_INFRASTRUCTURE_SUCCESS = {
        Language.EN: "Infrastructure created successfully",
        Language.KR: "인프라 생성 성공",
        Language.TH: "สร้างโครงสร้างพื้นฐานสำเร็จ",
    }
    UPDATE_INFRASTRUCTURE_SUCCESS = {
        Language.EN: "Infrastructure updated successfully",
        Language.KR: "인프라 업데이트 성공",
        Language.TH: "อัปเดตโครงสร้างพื้นฐานสำเร็จ",
    }
    UPDATE_INFRASTRUCTURE_FAILED = {
        Language.EN: "Infrastructure updated failed",
        Language.KR: "인프라 업데이트 실패",
        Language.TH: "อัปเดตโครงสร้างพื้นฐานล้มเหลว",
    }
    UPDATE_DOCKING_STATION_SUCCESS = {
        Language.EN: "Docking station updated successfully",
        Language.KR: "도킹스테이션 업데이트 성공",
        Language.TH: "อัปเดตสถานีเชื่อมต่อสำเร็จ",
    }
    UPDATE_DOCKING_STATION_FAILED = {
        Language.EN: "Docking station updated failed",
        Language.KR: "도킹스테이션 업데이트 실패",
        Language.TH: "อัปเดตสถานีเชื่อมต่อล้มเหลว",
    }
    CREATE_DOCKING_STATION_SUCCESS = {
        Language.EN: "Docking station created successfully",
        Language.KR: "도킹스테이션 생성 성공 ",
        Language.TH: "สร้างสถานีเชื่อมต่อสำเร็จ",
    }
    # General error messages
    NOT_FOUND = {
        Language.EN: "{0} not found",
        Language.KR: "{0} 찾을 수 없음",
        Language.TH: "ไม่พบ {0}",
    }
    GET_DEVICE_CAMERAS_SUCCESS = {
        Language.EN: "Device cameras fetched successfully",
        Language.KR: "장치 카메라 가져오기 성공",
        Language.TH: "ดึงกล้องอุปกรณ์สำเร็จ",
    }
    GET_DEVICE_CAMERAS_FAILED = {
        Language.EN: "Device cameras fetched failed",
        Language.KR: "장치 카메라 가져오기 실패",
        Language.TH: "ดึงกล้องอุปกรณ์ล้มเหลว",
    }
    CREATE_CAMERA_SUCCESS = {
        Language.EN: "Camera created successfully",
        Language.KR: "카메라 생성 성공",
        Language.TH: "สร้างกล้องสำเร็จ",
    }
    CREATE_CAMERA_FAILED = {
        Language.EN: "Camera created failed",
        Language.KR: "카메라 생성 실패",
        Language.TH: "สร้างกล้องล้มเหลว",
    }
    UPDATE_CAMERA_SUCCESS = {
        Language.EN: "Camera updated successfully",
        Language.KR: "카메라 업데이트 성공",
        Language.TH: "อัปเดตกล้องสำเร็จ",
    }
    UPDATE_CAMERA_FAILED = {
        Language.EN: "Camera updated failed",
        Language.KR: "카메라 업데이트 실패",
        Language.TH: "อัปเดตกล้องล้มเหลว",
    }
    DELETE_CAMERA_SUCCESS = {
        Language.EN: "Camera deleted successfully",
        Language.KR: "카메라 삭제 성공",
        Language.TH: "ลบกล้องสำเร็จ",
    }
    DELETE_CAMERA_FAILED = {
        Language.EN: "Camera deleted failed",
        Language.KR: "카메라 삭제 실패",
        Language.TH: "ลบกล้องล้มเหลว",
    }
    GET_CAMERA_DETAIL_SUCCESS = {
        Language.EN: "Camera detail fetched successfully",
        Language.KR: "카메라 상세 가져오기 성공",
        Language.TH: "ดึงรายละเอียดกล้องสำเร็จ",
    }
    GET_CAMERA_DETAIL_FAILED = {
        Language.EN: "Camera detail fetched failed",
        Language.KR: "카메라 상세 가져오기 실패",
        Language.TH: "ดึงรายละเอียดกล้องล้มเหลว",
    }
    GET_LIST_CAMERA_SUCCESS = {
        Language.EN: "Cameras fetched successfully",
        Language.KR: "카메라 목록 가져오기 성공",
        Language.TH: "ดึงรายการกล้องสำเร็จ",
    }
    GET_LIST_CAMERA_FAILED = {
        Language.EN: "Cameras fetched failed",
        Language.KR: "카메라 목록 가져오기 실패",
        Language.TH: "ดึงรายการกล้องล้มเหลว",
    }
    # Geolocation messages
    GEOCODE_ADDRESS_SUCCESS = {
        Language.EN: "Address geocoded successfully",
        Language.KR: "주소 지오코딩 성공",
        Language.TH: "แปลงที่อยู่เป็นพิกัดสำเร็จ",
    }
    REVERSE_GEOCODE_SUCCESS = {
        Language.EN: "Coordinates reverse geocoded successfully",
        Language.KR: "좌표 역지오코딩 성공",
        Language.TH: "แปลงพิกัดเป็นที่ตั้งสำเร็จ",
    }
    SEARCH_LOCATIONS_SUCCESS = {
        Language.EN: "Locations searched successfully",
        Language.KR: "위치 검색 성공",
        Language.TH: "ค้นหาสถานที่สำเร็จ",
    }
    IMPORT_DATA_SUCCESS = {
        Language.EN: "Geolocation data imported successfully",
        Language.KR: "지오로케이션 데이터 가져오기 성공",
        Language.TH: "นำเข้าข้อมูลตำแหน่งที่ตั้งสำเร็จ",
    }
    PERMISSION_DENIED = {
        Language.EN: "Permission denied",
        Language.KR: "권한이 거부되었습니다",
        Language.TH: "ไม่มีสิทธิ์เข้าถึง",
    }
    INTERNAL_SERVER_ERROR = {
        Language.EN: "Internal server error",
        Language.KR: "내부 서버 오류",
        Language.TH: "ข้อผิดพลาดของเซิร์ฟเวอร์ภายใน",
    }
    GET_LIST_SUCCESS = {
        Language.EN: "List fetched successfully",
        Language.KR: "목록 가져오기 성공",
        Language.TH: "ดึงรายการสำเร็จ",
    }
    CREATE_ORDER_SUCCESS = {
        Language.EN: "Order created successfully",
        Language.KR: "주문이 성공적으로 생성되었습니다",
        Language.TH: "สร้างคำสั่งซื้อสำเร็จแล้ว",
    }
    GET_ORDER_SUCCESS = {
        Language.EN: "Order fetched successfully",
        Language.KR: "주문 가져오기 성공",
        Language.TH: "ดึงข้อมูลคำสั่งซื้อสำเร็จ",
    }
    GET_LIST_ORDER_SUCCESS = {
        Language.EN: "Orders fetched successfully",
        Language.KR: "주문 목록 가져오기 성공",
        Language.TH: "ดึงรายการคำสั่งซื้อสำเร็จ",
    }
    GET_DELIVERY_OPTIONS_SUCCESS = {
        Language.EN: "Delivery options fetched successfully",
        Language.KR: "배송 옵션 가져오기 성공",
        Language.TH: "ดึงตัวเลือกการจัดส่งสำเร็จ",
    }
    GET_PACKAGE_LIST_SUCCESS = {
        Language.EN: "Package list fetched successfully",
        Language.KR: "패키지 목록 가져오기 성공",
        Language.TH: "ดึงรายการแพ็คเกจสำเร็จ",
    }
    CANCEL_ORDER_SUCCESS = {
        Language.EN: "Order cancelled successfully",
        Language.KR: "주문이 성공적으로 취소되었습니다",
        Language.TH: "คำสั่งถูกยกเลิกเรียบร้อยแล้ว",
    }
    CANCEL_ORDER_FAILED = {
        Language.EN: "Order cancelled failed",
        Language.KR: "주문 취소 실패",
        Language.TH: "ยกเลิกคำสั่งซื้อล้มเหลว",
    }
    RETURN_ORDER_SUCCESS = {
        Language.EN: "Order returned successfully",
        Language.KR: "주문 반환 성공",
        Language.TH: "คืนคำสั่งซื้อสำเร็จ",
    }
    DELETE_PRINT_FORMAT_SUCCESS = {
        Language.EN: "Print format deleted successfully",
        Language.KR: "프린트 포맷 삭제 성공",
        Language.TH: "ลบรูปแบบการพิมพ์สำเร็จ",
    }
    DELETE_PRINT_FORMAT_FAILED = {
        Language.EN: "Print format deleted failed",
        Language.KR: "프린트 포맷 삭제 실패",
        Language.TH: "ลบรูปแบบการพิมพ์ล้มเหลว",
    }
    GET_LIST_TEMPLATE_SUCCESS = {
        Language.EN: "List template fetched successfully",
        Language.KR: "템플릿 목록 가져오기 성공",
        Language.TH: "ดึงรายการแม่แบบสำเร็จ",
    }
    CREATE_PRINT_FORMAT_SUCCESS = {
        Language.EN: "Print format created successfully",
        Language.KR: "프린트 포맷 생성 성공",
        Language.TH: "สร้างรูปแบบการพิมพ์สำเร็จ",
    }
    PREVIEW_PRINT_FORMAT_SUCCESS = {
        Language.EN: "Print format previewed successfully",
        Language.KR: "프린트 포맷 미리보기 성공",
        Language.TH: "ดูตัวอย่างรูปแบบการพิมพ์สำเร็จ",
    }
    PAYMENT_ORDER_SUCCESS = {
        Language.EN: "Order paid successfully",
        Language.KR: "주문 결제 성공",
        Language.TH: "ชำระเงินคำสั่งซื้อสำเร็จ",
    }
    PAYMENT_ORDER_FAILED = {
        Language.EN: "Order paid failed",
        Language.KR: "주문 결제 실패",
        Language.TH: "ชำระเงินคำสั่งซื้อล้มเหลว",
    }
    GET_PRINT_FORMAT_SUCCESS = {
        Language.EN: "Print format fetched successfully",
        Language.KR: "프린트 포맷 가져오기 성공",
        Language.TH: "ดึงรูปแบบการพิมพ์สำเร็จ",
    }
    REFUND_ORDER_SUCCESS = {
        Language.EN: "Order refunded successfully",
        Language.KR: "주문 환불 성공",
        Language.TH: "คืนเงินคำสั่งซื้อสำเร็จ",
    }
    GET_BANKS_SUCCESS = {
        Language.EN: "Banks retrieved successfully",
        Language.KR: "은행 목록 가져오기 성공",
        Language.TH: "ดึงข้อมูลธนาคารสำเร็จ",
    }

    ADD_RECORD_TO_GROUP_SUCCESS = {
        Language.EN: "Record added to group successfully",
        Language.KR: "레코드 그룹에 추가 성공",
        Language.TH: "เพิ่มบันทึกเข้ากลุ่มสำเร็จ",
    }
    ADD_RECORD_TO_GROUP_FAILED = {
        Language.EN: "Record added to group failed",
        Language.KR: "레코드 그룹에 추가 실패",
        Language.TH: "เพิ่มบันทึกเข้ากลุ่มล้มเหลว",
    }
    REMOVE_RECORD_FROM_GROUP_SUCCESS = {
        Language.EN: "Record removed from group successfully",
        Language.KR: "레코드 그룹에서 제거 성공",
        Language.TH: "ลบบันทึกออกจากกลุ่มสำเร็จ",
    }

    # Library messages
    GET_LIST_LIBRARY_SUCCESS = {
        Language.EN: "Libraries fetched successfully",
        Language.KR: "라이브러리 목록 가져오기 성공",
        Language.TH: "ดึงรายการไลบรารีสำเร็จ",
    }
    GET_LIBRARY_DETAIL_SUCCESS = {
        Language.EN: "Library fetched successfully",
        Language.KR: "라이브러리 정보 가져오기 성공",
        Language.TH: "ดึงข้อมูลไลบรารีสำเร็จ",
    }
    CREATE_LIBRARY_SUCCESS = {
        Language.EN: "Library created successfully",
        Language.KR: "템플릿이 생성되었습니다",
        Language.TH: "สร้างไลบรารีสำเร็จ",
    }
    UPDATE_LIBRARY_SUCCESS = {
        Language.EN: "Library updated successfully",
        Language.KR: "템플릿이 업데이트되었습니다",
        Language.TH: "อัปเดตไลบรารีสำเร็จ",
    }
    DELETE_LIBRARY_SUCCESS = {
        Language.EN: "Library deleted successfully",
        Language.KR: "템플릿이 삭제되었습니다",
        Language.TH: "ลบไลบรารีสำเร็จ",
    }

    GET_LIST_GROUP_SUCCESS = {
        Language.EN: "Groups fetched successfully",
        Language.KR: "그룹 목록 가져오기 성공",
        Language.TH: "ดึงรายการกลุ่มสำเร็จ",
    }
    GET_GROUP_DETAIL_SUCCESS = {
        Language.EN: "Group detail fetched successfully",
        Language.KR: "그룹 상세 가져오기 성공",
        Language.TH: "ดึงรายละเอียดกลุ่มสำเร็จ",
    }
    CREATE_GROUP_SUCCESS = {
        Language.EN: "Group created successfully",
        Language.KR: "그룹 생성 성공",
        Language.TH: "สร้างกลุ่มสำเร็จ",
    }
    UPDATE_GROUP_SUCCESS = {
        Language.EN: "Group updated successfully",
        Language.KR: "그룹 업데이트 성공",
        Language.TH: "อัปเดตกลุ่มสำเร็จ",
    }
    UPDATE_PRINT_FORMAT_SUCCESS = {
        Language.EN: "Print format updated successfully",
        Language.KR: "프린트 포맷 업데이트 성공",
        Language.TH: "อัปเดตรูปแบบการพิมพ์สำเร็จ",
    }
    CREATE_ORDER_BY_WORKFLOW_SUCCESS = {
        Language.EN: "Order created successfully by workflow",
        Language.KR: "워크플로우로 주문 생성 성공",
        Language.TH: "สร้างคำสั่งซื้อด้วยเวิร์กโฟลว์สำเร็จ",
    }
    ORDER_WORKFLOW_NOT_FOUND = {
        Language.EN: "Order workflow not found",
        Language.KR: "주문 워크플로우를 찾을 수 없습니다",
        Language.TH: "ไม่พบเวิร์กโฟลว์คำสั่งซื้อ",
    }
    CREATE_ORDER_FAILED = {
        Language.EN: "Order created failed",
        Language.KR: "주문 생성 실패",
        Language.TH: "สร้างคำสั่งซื้อล้มเหลว",
    }
    CONFIRM_ORDER_SUCCESS = {
        Language.EN: "Order confirmed successfully",
        Language.KR: "주문 확인 성공",
        Language.TH: "ยืนยันคำสั่งซื้อสำเร็จ",
    }
    CONFIRM_ORDER_FAILED = {
        Language.EN: "Order confirmation failed",
        Language.KR: "주문 확인 실패",
        Language.TH: "ยืนยันคำสั่งซื้อล้มเหลว",
    }
    SELECT_DRONE_SUCCESS = {
        Language.EN: "Drone selected successfully",
        Language.KR: "드론 선택 성공",
        Language.TH: "เลือกโดรนสำเร็จ",
    }
    SELECT_DRONE_FAILED = {
        Language.EN: "Drone selection failed",
        Language.KR: "드론 선택 실패",
        Language.TH: "เลือกโดรนล้มเหลว",
    }

    # Processing errors (assign/approve)
    INSUFFICIENT_WEIGHT_CAPACITY = {
        Language.EN: "Drone does not have enough remaining weight capacity",
        Language.KR: "드론의 잔여 하중 용량이 부족합니다",
        Language.TH: "โดรนไม่มีกำลังการรับน้ำหนักที่เหลือเพอ",
    }
    INSUFFICIENT_PACKAGE_SLOTS = {
        Language.EN: "Drone does not have enough available package slots",
        Language.KR: "드론의 가용 패키지 슬롯이 부족합니다",
        Language.TH: "โดรนไม่มีช่องแพ็คเกจที่มีอยู่เพียงพอ",
    }
    DIMENSION_NOT_FIT = {
        Language.EN: "Package dimensions do not fit in the drone cargo",
        Language.KR: "패키지 크기가 드론 적재함에 맞지 않습니다",
        Language.TH: "ขนาดแพ็คเกจไม่เข้ากับกระเป๋าบรรทุกของโดรน",
    }
    PENDING_APPROVALS = {
        Language.EN: "Approval pending for related drones",
        Language.KR: "연관된 드론 승인이 보류 중입니다",
        Language.TH: "การอนุมัติโดรนที่เกี่ยวข้องกำลังรอดำเนินการ",
    }
    ASSIGN_PACKAGES_TO_DRONES_SUCCESS = {
        Language.EN: "Packages assigned to drones successfully",
        Language.KR: "패키지가 드론에 성공적으로 할당되었습니다",
        Language.TH: "มอบหมายแพ็คเกจให้โดรนสำเร็จ",
    }
    # Execution Engine messages
    GET_LIST_FUNC_TYPE_SUCCESS = {
        Language.EN: "Function types fetched successfully",
        Language.KR: "기능 유형 목록 가져오기 성공",
        Language.TH: "ดึงรายการประเภทฟังก์ชันสำเร็จ",
    }
    GET_FUNC_TYPE_DETAIL_SUCCESS = {
        Language.EN: "Function type fetched successfully",
        Language.KR: "기능 유형 정보 가져오기 성공",
        Language.TH: "ดึงข้อมูลประเภทฟังก์ชันสำเร็จ",
    }
    CREATE_FUNC_TYPE_SUCCESS = {
        Language.EN: "Function type created successfully",
        Language.KR: "기능 유형 생성 성공",
        Language.TH: "สร้างประเภทฟังก์ชันสำเร็จ",
    }
    UPDATE_FUNC_TYPE_SUCCESS = {
        Language.EN: "Function type updated successfully",
        Language.KR: "기능 유형 업데이트 성공",
        Language.TH: "อัปเดตประเภทฟังก์ชันสำเร็จ",
    }
    DELETE_FUNC_TYPE_SUCCESS = {
        Language.EN: "Function type deleted successfully",
        Language.KR: "기능 유형 삭제 성공",
        Language.TH: "ลบประเภทฟังก์ชันสำเร็จ",
    }
    SYNC_FUNC_TYPE_SUCCESS = {
        Language.EN: "Function types synchronized successfully",
        Language.KR: "기능 유형 동기화 성공",
        Language.TH: "ซิงค์ประเภทฟังก์ชันสำเร็จ",
    }

    GET_LIST_FUNCTION_EXECUTION_SUCCESS = {
        Language.EN: "Function executions fetched successfully",
        Language.KR: "기능 실행 목록 가져오기 성공",
        Language.TH: "ดึงรายการการดำเนินการฟังก์ชันสำเร็จ",
    }
    GET_FUNCTION_EXECUTION_DETAIL_SUCCESS = {
        Language.EN: "Function execution fetched successfully",
        Language.KR: "기능 실행 정보 가져오기 성공",
        Language.TH: "ดึงข้อมูลการดำเนินการฟังก์ชันสำเร็จ",
    }
    CREATE_FUNCTION_EXECUTION_SUCCESS = {
        Language.EN: "Function execution created successfully",
        Language.KR: "기능 실행 생성 성공",
        Language.TH: "สร้างการดำเนินการฟังก์ชันสำเร็จ",
    }
    UPDATE_FUNCTION_EXECUTION_SUCCESS = {
        Language.EN: "Function execution updated successfully",
        Language.KR: "기능 실행 업데이트 성공",
        Language.TH: "อัปเดตการดำเนินการฟังก์ชันสำเร็จ",
    }
    DELETE_FUNCTION_EXECUTION_SUCCESS = {
        Language.EN: "Function execution deleted successfully",
        Language.KR: "기능 실행 삭제 성공",
        Language.TH: "ลบการดำเนินการฟังก์ชันสำเร็จ",
    }
    EXECUTE_STEP_SUCCESS = {
        Language.EN: "Step executed successfully",
        Language.KR: "단계 실행 성공",
        Language.TH: "ดำเนินการขั้นตอนสำเร็จ",
    }
    FEATURE_TYPE_INACTIVE = {
        Language.EN: "Feature type is inactive",
        Language.KR: "기능 유형이 비활성화됨",
        Language.TH: "ประเภทฟังก์ชันไม่ได้ใช้งาน",
    }
    INVALID_FEATURE_TYPE = {
        Language.EN: "Invalid feature type",
        Language.KR: "잘못된 기능 유형",
        Language.TH: "ประเภทฟังก์ชันไม่ถูกต้อง",
    }
    EXECUTION_ERROR = {
        Language.EN: "Execution error occurred",
        Language.KR: "실행 오류 발생",
        Language.TH: "เกิดข้อผิดพลาดในการดำเนินการ",
    }

    NO_OPERATION_FOUND = {
        Language.EN: "Operation not found",
        Language.KR: "작업을 찾을 수 없습니다",
        Language.TH: "ไม่พบการดำเนินการ",
    }

    # Operation Settings Messages
    OPERATION_SETTINGS_LIST_SUCCESS = {
        Language.EN: "Operation settings retrieved successfully.",
        Language.KR: "작업 설정을 성공적으로 검색했습니다.",
        Language.TH: "ดึงการตั้งค่าเครื่องมือสำเร็จ",
    }

    OPERATION_SETTINGS_LIST_ERROR = {
        Language.EN: "Error retrieving operation settings.",
        Language.KR: "작업 설정 검색 중 오류가 발생했습니다.",
        Language.TH: "เกิดข้อผิดพลาดในการดึงการตั้งค่าเครื่องมือ",
    }

    OPERATION_SETTINGS_GET_SUCCESS = {
        Language.EN: "Operation setting retrieved successfully.",
        Language.KR: "작업 설정을 성공적으로 검색했습니다.",
        Language.TH: "ดึงการตั้งค่าเครื่องมือสำเร็จ",
    }

    OPERATION_SETTINGS_GET_ERROR = {
        Language.EN: "Error retrieving operation setting.",
        Language.KR: "작업 설정 검색 중 오류가 발생했습니다.",
        Language.TH: "เกิดข้อผิดพลาดในการดึงการตั้งค่าเครื่องมือ",
    }

    OPERATION_SETTINGS_NOT_FOUND = {
        Language.EN: "Operation setting not found.",
        Language.KR: "작업 설정을 찾을 수 없습니다.",
        Language.TH: "ไม่พบการตั้งค่าเครื่องมือ",
    }

    OPERATION_SETTINGS_CREATE_SUCCESS = {
        Language.EN: "Operation setting created successfully.",
        Language.KR: "작업 설정이 성공적으로 생성되었습니다.",
        Language.TH: "สร้างการตั้งค่าเครื่องมือสำเร็จ",
    }

    OPERATION_SETTINGS_CREATE_ERROR = {
        Language.EN: "Error creating operation setting.",
        Language.KR: "작업 설정 생성 중 오류가 발생했습니다.",
        Language.TH: "เกิดข้อผิดพลาดในการสร้างการตั้งค่าเครื่องมือ",
    }

    OPERATION_SETTINGS_UPDATE_SUCCESS = {
        Language.EN: "Operation setting updated successfully.",
        Language.KR: "작업 설정이 성공적으로 업데이트되었습니다.",
        Language.TH: "อัปเดตการตั้งค่าเครื่องมือสำเร็จ",
    }

    OPERATION_SETTINGS_UPDATE_ERROR = {
        Language.EN: "Error updating operation setting.",
        Language.KR: "작업 설정 업데이트 중 오류가 발생했습니다.",
        Language.TH: "เกิดข้อผิดพลาดในการอัปเดตการตั้งค่าเครื่องมือ",
    }

    OPERATION_SETTINGS_DELETE_SUCCESS = {
        Language.EN: "Operation setting deleted successfully.",
        Language.KR: "작업 설정이 성공적으로 삭제되었습니다.",
        Language.TH: "ลบการตั้งค่าเครื่องมือสำเร็จ",
    }

    OPERATION_SETTINGS_DELETE_ERROR = {
        Language.EN: "Error deleting operation setting.",
        Language.KR: "작업 설정 삭제 중 오류가 발생했습니다.",
        Language.TH: "เกิดข้อผิดพลาดในการลบการตั้งค่าเครื่องมือ",
    }

    REFRESH_DASHBOARD_DATA_SUCCESS = {
        Language.EN: "Dashboard data refreshed successfully.",
        Language.KR: "대시보드 데이터가 성공적으로 새로고침되었습니다.",
        Language.TH: "ดึงข้อมูลการตั้งค่าเครื่องมือสำเร็จ",
    }

    GET_DASHBOARD_DATA_SUCCESS = {
        Language.EN: "Dashboard data fetched successfully.",
        Language.KR: "대시보드 데이터가 성공적으로 가져왔습니다.",
        Language.TH: "ดึงข้อมูลการตั้งค่าเครื่องมือสำเร็จ",
    }
    GET_DRONE_HEALTH_SUCCESS = {
        Language.EN: "Drone health data fetched successfully.",
        Language.KR: "드론 건강 데이터가 성공적으로 가져왔습니다.",
        Language.TH: "ดึงข้อมูลสุขภาพโดรนสำเร็จ",
    }

    GET_LIST_LOCATION_TYPE_SUCCESS = {
        Language.EN: "Location types fetched successfully.",
        Language.KR: "위치 유형 목록 가져오기 성공.",
        Language.TH: "ดึงรายการประเภทตำแหน่งสำเร็จ",
    }

    CREATE_DELIVERY_HUB_SUCCESS = {
        Language.EN: "Delivery hub created successfully.",
        Language.KR: "배달거점 생성이 완료되었습니다.",
        Language.TH: "สร้างสถานที่จัดส่งสำเร็จ",
    }

    GET_DELIVERY_HUB_DETAIL_SUCCESS = {
        Language.EN: "Delivery hub detail fetched successfully.",
        Language.KR: "배송 허브 상세 정보가 성공적으로 가져왔습니다.",
        Language.TH: "ดึงข้อมูลสถานที่จัดส่งสำเร็จ",
    }

    UPDATE_DELIVERY_HUB_SUCCESS = {
        Language.EN: "Delivery hub updated successfully.",
        Language.KR: "배달거점 수정이 완료되었습니다.",
        Language.TH: "อัปเดตสถานที่จัดส่งสำเร็จ",
    }
    ACTIVATE_DELIVERY_LOCATION_SUCCESS = {
        Language.EN: "Delivery location status changed successfully.",
        Language.KR: "배달거점 상태 변경 성공.",
        Language.TH: "การเปลี่ยนแปลงสถานะสถานที่จัดส่งสำเร็จ",
    }
    ACTIVATE_DELIVERY_LOCATION_FAILED = {
        Language.EN: "Delivery location status changed failed.",
        Language.KR: "배달거점 상태 변경 실패.",
        Language.TH: "การเปลี่ยนแปลงสถานะสถานที่จัดส่งล้มเหลว",
    }
    DEACTIVATE_DELIVERY_LOCATION_FAILED = {
        Language.EN: "Delivery location status changed failed.",
        Language.KR: "배달거점 상태 변경 실패.",
        Language.TH: "การเปลี่ยนแปลงสถานะสถานที่จัดส่งล้มเหลว",
    }
    DELIVERY_HUB_ON_MISSION = {
        Language.EN: "Delivery hub is currently on a mission.",
        Language.KR: "배달거점은 현재 임무 중입니다.",
        Language.TH: "สถานที่จัดส่งอยู่ในการดำเนินงานปัจจุบัน",
    }
    DEACTIVATE_DELIVERY_LOCATION_SUCCESS = {
        Language.EN: "Delivery location status changed successfully.",
        Language.KR: "배달거점 상태 변경 성공.",
        Language.TH: "การเปลี่ยนแปลงสถานะสถานที่จัดส่งสำเร็จ",
    }
    ACTIVATE_DOCKING_STATION_SUCCESS = {
        Language.EN: "Docking station status changed successfully.",
        Language.KR: "도킹스테이션 상태가 변경되었습니다.",
        Language.TH: "การเปลี่ยนแปลงสถานะสถานีเชื่อมต่อสำเร็จ",
    }
    ACTIVATE_DOCKING_STATION_FAILED = {
        Language.EN: "Docking station status changed failed.",
        Language.KR: "도킹스테이션 상태 변경에 실패했습니다.",
        Language.TH: "การเปลี่ยนแปลงสถานะสถานีเชื่อมต่อล้มเหลว",
    }
    
    # Detection message templates with placeholders: {detect_name}
    DETECTION_MESSAGE_TEMPLATE_FIRE_SMOKE = {
        Language.EN: "Detected {detect_name}.",
        Language.KR: "{detect_name}을(를) 감지했습니다.",
        Language.TH: "ตรวจพบ {detect_name}.",
    }
    DETECTION_MESSAGE_TEMPLATE_ANIMALS = {
        Language.EN: "Detected {detect_name}.",
        Language.KR: "{detect_name}을(를) 감지했습니다.",
        Language.TH: "ตรวจพบ {detect_name}.",
    }
    DETECTION_MESSAGE_TEMPLATE_HUMAN = {
        Language.EN: "Detected {detect_name}.",
        Language.KR: "{detect_name}을(를) 감지했습니다.",
        Language.TH: "ตรวจพบ {detect_name}.",
    }
    DETECTION_MESSAGE_TEMPLATE_VEHICLE = {
        Language.EN: "Detected {detect_name}.",
        Language.KR: "{detect_name}을(를) 감지했습니다.",
        Language.TH: "ตรวจพบ {detect_name}.",
    }
    DETECTION_MESSAGE_TEMPLATE_ANOMALY = {
        Language.EN: "Detected {detect_name}.",
        Language.KR: "{detect_name}을(를) 감지했습니다.",
        Language.TH: "ตรวจพบ {detect_name}.",
    }
    
    # Detection names in different languages
    DETECTION_NAME_FIRE_SMOKE = {
        Language.EN: "fire/smoke",
        Language.KR: "화재/연기",
        Language.TH: "ไฟ/ควัน",
    }
    DETECTION_NAME_ANIMALS = {
        Language.EN: "animals",
        Language.KR: "동물",
        Language.TH: "สัตว์",
    }
    DETECTION_NAME_HUMAN = {
        Language.EN: "human",
        Language.KR: "사람",
        Language.TH: "คน",
    }
    DETECTION_NAME_VEHICLE = {
        Language.EN: "vehicle",
        Language.KR: "차량",
        Language.TH: "ยานพาหนะ",
    }
    DETECTION_NAME_ANOMALY = {
        Language.EN: "suspicious movement",
        Language.KR: "의심스러운 움직임",
        Language.TH: "การเคลื่อนไหวที่น่าสงสัย",
    }

    # Media detect label translations (COCO + fire/smoke)
    MEDIA_DETECT_LABEL_DEFAULT = {
        Language.EN: "object",
        Language.KR: "객체",
        Language.TH: "วัตถุ",
    }
    MEDIA_DETECT_LABEL_TRANSLATIONS = {
        "person": {Language.EN: "person", Language.KR: "사람", Language.TH: "คน"},
        "bicycle": {Language.EN: "bicycle", Language.KR: "자전거", Language.TH: "รถจักรยาน"},
        "car": {Language.EN: "car", Language.KR: "자동차", Language.TH: "รถยนต์"},
        "motorcycle": {Language.EN: "motorcycle", Language.KR: "오토바이", Language.TH: "รถจักรยานยนต์"},
        "airplane": {Language.EN: "airplane", Language.KR: "비행기", Language.TH: "เครื่องบิน"},
        "bus": {Language.EN: "bus", Language.KR: "버스", Language.TH: "รถบัส"},
        "train": {Language.EN: "train", Language.KR: "기차", Language.TH: "รถไฟ"},
        "truck": {Language.EN: "truck", Language.KR: "트럭", Language.TH: "รถบรรทุก"},
        "boat": {Language.EN: "boat", Language.KR: "보트", Language.TH: "เรือ"},
        "traffic light": {Language.EN: "traffic light", Language.KR: "신호등", Language.TH: "ไฟจราจร"},
        "fire hydrant": {Language.EN: "fire hydrant", Language.KR: "소화전", Language.TH: "หัวดับเพลิง"},
        "stop sign": {Language.EN: "stop sign", Language.KR: "정지 표지판", Language.TH: "ป้ายหยุด"},
        "parking meter": {Language.EN: "parking meter", Language.KR: "주차 요금기", Language.TH: "มิเตอร์จอดรถ"},
        "bench": {Language.EN: "bench", Language.KR: "벤치", Language.TH: "ม้านั่ง"},
        "bird": {Language.EN: "bird", Language.KR: "새", Language.TH: "นก"},
        "cat": {Language.EN: "cat", Language.KR: "고양이", Language.TH: "แมว"},
        "dog": {Language.EN: "dog", Language.KR: "개", Language.TH: "สุนัข"},
        "horse": {Language.EN: "horse", Language.KR: "말", Language.TH: "ม้า"},
        "sheep": {Language.EN: "sheep", Language.KR: "양", Language.TH: "แกะ"},
        "cow": {Language.EN: "cow", Language.KR: "소", Language.TH: "วัว"},
        "elephant": {Language.EN: "elephant", Language.KR: "코끼리", Language.TH: "ช้าง"},
        "bear": {Language.EN: "bear", Language.KR: "곰", Language.TH: "หมี"},
        "zebra": {Language.EN: "zebra", Language.KR: "얼룩말", Language.TH: "ม้าลาย"},
        "giraffe": {Language.EN: "giraffe", Language.KR: "기린", Language.TH: "ยีราฟ"},
        "backpack": {Language.EN: "backpack", Language.KR: "배낭", Language.TH: "กระเป๋าเป้"},
        "umbrella": {Language.EN: "umbrella", Language.KR: "우산", Language.TH: "ร่ม"},
        "handbag": {Language.EN: "handbag", Language.KR: "핸드백", Language.TH: "กระเป๋าถือ"},
        "tie": {Language.EN: "tie", Language.KR: "넥타이", Language.TH: "เนคไท"},
        "suitcase": {Language.EN: "suitcase", Language.KR: "여행가방", Language.TH: "กระเป๋าเดินทาง"},
        "frisbee": {Language.EN: "frisbee", Language.KR: "프리스비", Language.TH: "จานร่อน"},
        "skis": {Language.EN: "skis", Language.KR: "스키", Language.TH: "สกี"},
        "snowboard": {Language.EN: "snowboard", Language.KR: "스노보드", Language.TH: "สโนว์บอร์ด"},
        "sports ball": {Language.EN: "sports ball", Language.KR: "스포츠 공", Language.TH: "ลูกบอลกีฬา"},
        "kite": {Language.EN: "kite", Language.KR: "연", Language.TH: "ว่าว"},
        "baseball bat": {Language.EN: "baseball bat", Language.KR: "야구 방망이", Language.TH: "ไม้เบสบอล"},
        "baseball glove": {Language.EN: "baseball glove", Language.KR: "야구 글러브", Language.TH: "ถุงมือเบสบอล"},
        "skateboard": {Language.EN: "skateboard", Language.KR: "스케이트보드", Language.TH: "สเก็ตบอร์ด"},
        "surfboard": {Language.EN: "surfboard", Language.KR: "서프보드", Language.TH: "กระดานโต้คลื่น"},
        "tennis racket": {Language.EN: "tennis racket", Language.KR: "테니스 라켓", Language.TH: "ไม้เทนนิส"},
        "bottle": {Language.EN: "bottle", Language.KR: "병", Language.TH: "ขวด"},
        "wine glass": {Language.EN: "wine glass", Language.KR: "와인잔", Language.TH: "แก้วไวน์"},
        "cup": {Language.EN: "cup", Language.KR: "컵", Language.TH: "ถ้วย"},
        "fork": {Language.EN: "fork", Language.KR: "포크", Language.TH: "ส้อม"},
        "knife": {Language.EN: "knife", Language.KR: "칼", Language.TH: "มีด"},
        "spoon": {Language.EN: "spoon", Language.KR: "숟가락", Language.TH: "ช้อน"},
        "bowl": {Language.EN: "bowl", Language.KR: "그릇", Language.TH: "ชาม"},
        "banana": {Language.EN: "banana", Language.KR: "바나나", Language.TH: "กล้วย"},
        "apple": {Language.EN: "apple", Language.KR: "사과", Language.TH: "แอปเปิล"},
        "sandwich": {Language.EN: "sandwich", Language.KR: "샌드위치", Language.TH: "แซนด์วิช"},
        "orange": {Language.EN: "orange", Language.KR: "오렌지", Language.TH: "ส้ม"},
        "broccoli": {Language.EN: "broccoli", Language.KR: "브로콜리", Language.TH: "บรอกโคลี"},
        "carrot": {Language.EN: "carrot", Language.KR: "당근", Language.TH: "แครอท"},
        "hot dog": {Language.EN: "hot dog", Language.KR: "핫도그", Language.TH: "ฮอตด็อก"},
        "pizza": {Language.EN: "pizza", Language.KR: "피자", Language.TH: "พิซซ่า"},
        "donut": {Language.EN: "donut", Language.KR: "도넛", Language.TH: "โดนัท"},
        "cake": {Language.EN: "cake", Language.KR: "케이크", Language.TH: "เค้ก"},
        "chair": {Language.EN: "chair", Language.KR: "의자", Language.TH: "เก้าอี้"},
        "couch": {Language.EN: "couch", Language.KR: "소파", Language.TH: "โซฟา"},
        "potted plant": {Language.EN: "potted plant", Language.KR: "화분", Language.TH: "กระถางต้นไม้"},
        "bed": {Language.EN: "bed", Language.KR: "침대", Language.TH: "เตียง"},
        "dining table": {Language.EN: "dining table", Language.KR: "식탁", Language.TH: "โต๊ะรับประทานอาหาร"},
        "toilet": {Language.EN: "toilet", Language.KR: "변기", Language.TH: "ชักโครก"},
        "tv": {Language.EN: "tv", Language.KR: "텔레비전", Language.TH: "โทรทัศน์"},
        "laptop": {Language.EN: "laptop", Language.KR: "노트북", Language.TH: "แล็ปท็อป"},
        "mouse": {Language.EN: "mouse", Language.KR: "마우스", Language.TH: "เมาส์"},
        "remote": {Language.EN: "remote", Language.KR: "리모컨", Language.TH: "รีโมท"},
        "keyboard": {Language.EN: "keyboard", Language.KR: "키보드", Language.TH: "แป้นพิมพ์"},
        "cell phone": {Language.EN: "cell phone", Language.KR: "휴대폰", Language.TH: "โทรศัพท์มือถือ"},
        "microwave": {Language.EN: "microwave", Language.KR: "전자레인지", Language.TH: "ไมโครเวฟ"},
        "oven": {Language.EN: "oven", Language.KR: "오븐", Language.TH: "เตาอบ"},
        "toaster": {Language.EN: "toaster", Language.KR: "토스터", Language.TH: "เครื่องปิ้งขนมปัง"},
        "sink": {Language.EN: "sink", Language.KR: "싱크대", Language.TH: "อ่างล้างจาน"},
        "refrigerator": {Language.EN: "refrigerator", Language.KR: "냉장고", Language.TH: "ตู้เย็น"},
        "book": {Language.EN: "book", Language.KR: "책", Language.TH: "หนังสือ"},
        "clock": {Language.EN: "clock", Language.KR: "시계", Language.TH: "นาฬิกา"},
        "vase": {Language.EN: "vase", Language.KR: "꽃병", Language.TH: "แจกัน"},
        "scissors": {Language.EN: "scissors", Language.KR: "가위", Language.TH: "กรรไกร"},
        "teddy bear": {Language.EN: "teddy bear", Language.KR: "곰인형", Language.TH: "ตุ๊กตาหมี"},
        "hair drier": {Language.EN: "hair drier", Language.KR: "헤어드라이어", Language.TH: "ไดร์เป่าผม"},
        "toothbrush": {Language.EN: "toothbrush", Language.KR: "칫솔", Language.TH: "แปรงสีฟัน"},
        "fire": {Language.EN: "fire", Language.KR: "화재", Language.TH: "ไฟ"},
        "smoke": {Language.EN: "smoke", Language.KR: "연기", Language.TH: "ควัน"},
    }
    
    # Relative time translations
    RELATIVE_TIME_JUST_NOW = {
        Language.EN: "just now",
        Language.KR: "방금 전",
        Language.TH: "เมื่อสักครู่",
    }
    RELATIVE_TIME_SECOND = {
        Language.EN: "second",
        Language.KR: "초",
        Language.TH: "วินาที",
    }
    RELATIVE_TIME_SECONDS = {
        Language.EN: "seconds",
        Language.KR: "초",
        Language.TH: "วินาที",
    }
    RELATIVE_TIME_MINUTE = {
        Language.EN: "minute",
        Language.KR: "분",
        Language.TH: "นาที",
    }
    RELATIVE_TIME_MINUTES = {
        Language.EN: "minutes",
        Language.KR: "분",
        Language.TH: "นาที",
    }
    RELATIVE_TIME_HOUR = {
        Language.EN: "hour",
        Language.KR: "시간",
        Language.TH: "ชั่วโมง",
    }
    RELATIVE_TIME_HOURS = {
        Language.EN: "hours",
        Language.KR: "시간",
        Language.TH: "ชั่วโมง",
    }
    RELATIVE_TIME_DAY = {
        Language.EN: "day",
        Language.KR: "일",
        Language.TH: "วัน",
    }
    RELATIVE_TIME_DAYS = {
        Language.EN: "days",
        Language.KR: "일",
        Language.TH: "วัน",
    }
    RELATIVE_TIME_WEEK = {
        Language.EN: "week",
        Language.KR: "주",
        Language.TH: "สัปดาห์",
    }
    RELATIVE_TIME_WEEKS = {
        Language.EN: "weeks",
        Language.KR: "주",
        Language.TH: "สัปดาห์",
    }
    RELATIVE_TIME_MONTH = {
        Language.EN: "month",
        Language.KR: "개월",
        Language.TH: "เดือน",
    }
    RELATIVE_TIME_MONTHS = {
        Language.EN: "months",
        Language.KR: "개월",
        Language.TH: "เดือน",
    }
    RELATIVE_TIME_AGO = {
        Language.EN: "ago",
        Language.KR: "전",
        Language.TH: "ที่แล้ว",
    }
    
    # Month names translations
    MONTH_JANUARY = {
        Language.EN: "January",
        Language.KR: "1월",
        Language.TH: "มกราคม",
    }
    MONTH_FEBRUARY = {
        Language.EN: "February",
        Language.KR: "2월",
        Language.TH: "กุมภาพันธ์",
    }
    MONTH_MARCH = {
        Language.EN: "March",
        Language.KR: "3월",
        Language.TH: "มีนาคม",
    }
    MONTH_APRIL = {
        Language.EN: "April",
        Language.KR: "4월",
        Language.TH: "เมษายน",
    }
    MONTH_MAY = {
        Language.EN: "May",
        Language.KR: "5월",
        Language.TH: "พฤษภาคม",
    }
    MONTH_JUNE = {
        Language.EN: "June",
        Language.KR: "6월",
        Language.TH: "มิถุนายน",
    }
    MONTH_JULY = {
        Language.EN: "July",
        Language.KR: "7월",
        Language.TH: "กรกฎาคม",
    }
    MONTH_AUGUST = {
        Language.EN: "August",
        Language.KR: "8월",
        Language.TH: "สิงหาคม",
    }
    MONTH_SEPTEMBER = {
        Language.EN: "September",
        Language.KR: "9월",
        Language.TH: "กันยายน",
    }
    MONTH_OCTOBER = {
        Language.EN: "October",
        Language.KR: "10월",
        Language.TH: "ตุลาคม",
    }
    MONTH_NOVEMBER = {
        Language.EN: "November",
        Language.KR: "11월",
        Language.TH: "พฤศจิกายน",
    }
    MONTH_DECEMBER = {
        Language.EN: "December",
        Language.KR: "12월",
        Language.TH: "ธันวาคม",
    }
    
    # Month abbreviations translations
    MONTH_ABBR_JANUARY = {
        Language.EN: "Jan",
        Language.KR: "1월",
        Language.TH: "ม.ค.",
    }
    MONTH_ABBR_FEBRUARY = {
        Language.EN: "Feb",
        Language.KR: "2월",
        Language.TH: "ก.พ.",
    }
    MONTH_ABBR_MARCH = {
        Language.EN: "Mar",
        Language.KR: "3월",
        Language.TH: "มี.ค.",
    }
    MONTH_ABBR_APRIL = {
        Language.EN: "Apr",
        Language.KR: "4월",
        Language.TH: "เม.ย.",
    }
    MONTH_ABBR_MAY = {
        Language.EN: "May",
        Language.KR: "5월",
        Language.TH: "พ.ค.",
    }
    MONTH_ABBR_JUNE = {
        Language.EN: "Jun",
        Language.KR: "6월",
        Language.TH: "มิ.ย.",
    }
    MONTH_ABBR_JULY = {
        Language.EN: "Jul",
        Language.KR: "7월",
        Language.TH: "ก.ค.",
    }
    MONTH_ABBR_AUGUST = {
        Language.EN: "Aug",
        Language.KR: "8월",
        Language.TH: "ส.ค.",
    }
    MONTH_ABBR_SEPTEMBER = {
        Language.EN: "Sep",
        Language.KR: "9월",
        Language.TH: "ก.ย.",
    }
    MONTH_ABBR_OCTOBER = {
        Language.EN: "Oct",
        Language.KR: "10월",
        Language.TH: "ต.ค.",
    }
    MONTH_ABBR_NOVEMBER = {
        Language.EN: "Nov",
        Language.KR: "11월",
        Language.TH: "พ.ย.",
    }
    MONTH_ABBR_DECEMBER = {
        Language.EN: "Dec",
        Language.KR: "12월",
        Language.TH: "ธ.ค.",
    }
    
    GET_DRONE_STATUS_OVERVIEW_SUCCESS = {
        Language.EN: "Drone status overview fetched successfully.",
        Language.KR: "드론 상태 개요가 성공적으로 가져왔습니다.",
        Language.TH: "ดึงข้อมูลภาพรวมสถานะโดรนสำเร็จ",
    }
    GET_DAILY_PROFILE_OVERVIEW_SUCCESS = {
        Language.EN: "Daily profile overview fetched successfully.",
        Language.KR: "일일 프로파일 개요가 성공적으로 가져왔습니다.",
        Language.TH: "ดึงข้อมูลภาพรวมโปรไฟล์รายวันสำเร็จ",
    }
    GET_ABNORMAL_SIGNS_OVERVIEW_SUCCESS = {
        Language.EN: "Abnormal signs overview fetched successfully.",
        Language.KR: "이상 징후 개요가 성공적으로 가져왔습니다.",
        Language.TH: "ดึงข้อมูลภาพรวมสัญญาณผิดปกติสำเร็จ",
    }
    GET_ABNORMAL_SIGNS_MESSAGES_SUCCESS = {
        Language.EN: "Abnormal signs messages fetched successfully.",
        Language.KR: "이상 징후 메시지가 성공적으로 가져왔습니다.",
        Language.TH: "ดึงข้อความสัญญาณผิดปกติสำเร็จ",
    }
    GET_TODAY_PROFILES_POLYGON_SUCCESS = {
        Language.EN: "Today profiles polygon fetched successfully.",
        Language.KR: "오늘 프로파일 폴리곤이 성공적으로 가져왔습니다.",
        Language.TH: "ดึงข้อมูลโพลีกอนโปรไฟล์วันนี้สำเร็จ",
    }
    GET_TODAY_REGION_DRONES_SUCCESS = {
        Language.EN: "Today region drones fetched successfully.",
        Language.KR: "오늘 지역 드론 목록을 성공적으로 가져왔습니다.",
        Language.TH: "ดึงข้อมูลโดรนตามภูมิภาคสำหรับวันนี้สำเร็จ",
    }
    
    ACTIVATE_INFRASTRUCTURE_SUCCESS = { 
        Language.EN: "Infrastructure status changed successfully.", 
        Language.KR: "인프라 상태가 변경되었습니다.",
        Language.TH: "การเปลี่ยนแปลงสถานะโครงสร้างพื้นฐานสำเร็จ",
    }
    ACTIVATE_INFRASTRUCTURE_FAILED = {
        Language.EN: "Infrastructure status changed failed.",
        Language.KR: "인프라 상태 변경에 실패했습니다.",
        Language.TH: "การเปลี่ยนแปลงสถานะโครงสร้างพื้นฐานล้มเหลว",
    }
    ACTIVATE_DELIVERY_HUB_SUCCESS = {
        Language.EN: "Delivery hub status changed successfully.",
        Language.KR: "배달거점 상태가 변경되었습니다.",
        Language.TH: "การเปลี่ยนแปลงสถานะสถานที่จัดส่งสำเร็จ",
    }
    ACTIVATE_DELIVERY_HUB_FAILED = {
        Language.EN: "Delivery hub status changed failed.",
        Language.KR: "배달거점 상태 변경에 실패했습니다.",
        Language.TH: "การเปลี่ยนแปลงสถานะสถานที่จัดส่งล้มเหลว",
    }
    DEACTIVATE_DELIVERY_HUB_WITH_DOCKING_IN_OTHER_ROUTE = {
        Language.EN: "Cannot deactivate hub {hub_name} (ID: {hub_id}) because there are dockings in other routes. Route IDs: {route_ids}",
        Language.KR: "다른 경로에 도킹이 있어 {hub_name} 허브(ID: {hub_id})를 비활성화할 수 없습니다. 경로 ID: {route_ids}",
        Language.TH: "ไม่สามารถปิดใช้งานฮับ {hub_name} (ID: {hub_id}) ได้เนื่องจากมี docking ในเส้นทางอื่น Route IDs: {route_ids}",
    }
    UPDATE_DELIVERY_HUB_FAILED = {
        Language.EN: "Delivery hub updated failed.",
        Language.KR: "배달거점 수정이 실패했습니다.",
        Language.TH: "อัปเดตสถานที่จัดส่งล้มเหลว",
    }

    DEVICE_IN_MISSION = {
        Language.EN: "The drone you want to disable is currently delivering goods. Please try again after the delivery is completed.",
        Language.KR: "비활성화하려는 드론은 현재 배송 중입니다. 배송이 완료된 후 다시 시도해 주세요.",
        Language.TH: "อุปกรณ์ที่ต้องการปิดไม่ได้ใช้งานในปัจจุบัน กรุณาลองใหม่หลังจากการจัดส่งเสร็จสิ้น",
    }

    DEVICE_NOT_FOUND = {
        Language.EN: "Device not found.",
        Language.KR: "장비를 찾을 수 없습니다.",
        Language.TH: "ไม่พบอุปกรณ์",
    }

    GET_LIST_REPORT_TEMPLATE_SUCCESS = {
        Language.EN: "Report template list fetched successfully",
        Language.KR: "보고서 템플릿 목록 가져오기 성공",
        Language.TH: "ดึงรายการแม่แบบการพิมพ์สำเร็จ",
    }

    GET_REPORT_TEMPLATE_DETAIL_SUCCESS = {
        Language.EN: "Report template detail fetched successfully",
        Language.KR: "보고서 템플릿 상세 정보 가져오기 성공",
        Language.TH: "ดึงข้อมูลแม่แบบการพิมพ์สำเร็จ",
    }

    CREATE_REPORT_TEMPLATE_SUCCESS = {
        Language.EN: "Report template created successfully",
        Language.KR: "보고서 템플릿 생성 성공",
        Language.TH: "สร้างแม่แบบการพิมพ์สำเร็จ",
    }

    UPDATE_REPORT_TEMPLATE_SUCCESS = {
        Language.EN: "Report template updated successfully",
        Language.KR: "보고서 템플릿 수정 성공",
        Language.TH: "อัปเดตแม่แบบการพิมพ์สำเร็จ",
    }

    DELETE_REPORT_TEMPLATE_SUCCESS = {
        Language.EN: "Report template deleted successfully",
        Language.KR: "보고서 템플릿 삭제 성공",
        Language.TH: "ลบแม่แบบการพิมพ์สำเร็จ",
    }

    REPORT_TEMPLATE_NOT_FOUND = {
        Language.EN: "Report template not found",
        Language.KR: "보고서 템플릿을 찾을 수 없습니다",
        Language.TH: "ไม่พบแม่แบบการพิมพ์",
    }

    GET_STREAM_MONITORS_SUCCESS = {
        Language.EN: "Stream monitors fetched successfully.",
        Language.KR: "스트림 모니터 목록 가져오기 성공.",
        Language.TH: "ดึงรายการสตรีมตัวตรวจสอบสำเร็จ",
    }

    GET_STREAM_MONITOR_CAPTURE_SUCCESS = {
        Language.EN: "The captured image has been saved.",
        Language.KR: "캡처된 이미지가 저장되었습니다.",
        Language.TH: "ภาพที่ถ่ายได้ถูกบันทึกไว้แล้ว",
    }

    STREAM_MONITOR_START_SUCCESS = {
        Language.EN: "Stream monitor started successfully.",
        Language.KR: "스트림 모니터 시작 성공.",
        Language.TH: "สตรีมตัวตรวจสอบถูกเริ่มต้นสำเร็จ",
    }

    STREAM_MONITOR_STOP_SUCCESS = {
        Language.EN: "Stream monitor stopped successfully.",
        Language.KR: "스트림 모니터 중지 성공.",
        Language.TH: "สตรีมตัวตรวจสอบถูกหยุดสำเร็จ",
    }

    # External Order Status Messages
    CREATE_EXTERNAL_ORDER_STATUS_SUCCESS = {
        Language.EN: "External order status created successfully",
        Language.KR: "외부 주문 상태가 성공적으로 생성되었습니다",
        Language.TH: "สร้างสถานะคำสั่งซื้อภายนอกสำเร็จ",
    }
    UPDATE_EXTERNAL_ORDER_STATUS_SUCCESS = {
        Language.EN: "Order status updated successfully",
        Language.KR: "주문 상태가 성공적으로 업데이트되었습니다",
        Language.TH: "สถานะคำสั่งซื้ออัปเดตสำเร็จแล้ว",
    }
    DELETE_EXTERNAL_ORDER_STATUS_SUCCESS = {
        Language.EN: "External order status deleted successfully",
        Language.KR: "외부 주문 상태가 성공적으로 삭제되었습니다",
        Language.TH: "ลบสถานะคำสั่งซื้อภายนอกสำเร็จ",
    }
    GET_LIST_EXTERNAL_ORDER_STATUS_SUCCESS = {
        Language.EN: "External order statuses fetched successfully",
        Language.KR: "외부 주문 상태 목록을 성공적으로 가져왔습니다",
        Language.TH: "ดึงรายการสถานะคำสั่งซื้อภายนอกสำเร็จ",
    }
    GET_EXTERNAL_ORDER_STATUS_DETAIL_SUCCESS = {
        Language.EN: "External order status fetched successfully",
        Language.KR: "외부 주문 상태 정보를 성공적으로 가져왔습니다",
        Language.TH: "ดึงข้อมูลสถานะคำสั่งซื้อภายนอกสำเร็จ",
    }

    # Order Status Mapping Messages
    CREATE_ORDER_STATUS_MAPPING_SUCCESS = {
        Language.EN: "Order status mapping created successfully",
        Language.KR: "주문 상태 매핑이 성공적으로 생성되었습니다",
        Language.TH: "สร้างการจัดการสถานะคำสั่งซื้อสำเร็จ",
    }
    UPDATE_ORDER_STATUS_MAPPING_SUCCESS = {
        Language.EN: "Order status mapping updated successfully",
        Language.KR: "주문 상태 매핑이 성공적으로 업데이트되었습니다",
        Language.TH: "อัปเดตการจัดการสถานะคำสั่งซื้อสำเร็จ",
    }
    DELETE_ORDER_STATUS_MAPPING_SUCCESS = {
        Language.EN: "Order status mapping deleted successfully",
        Language.KR: "주문 상태 매핑이 성공적으로 삭제되었습니다",
        Language.TH: "ลบการจัดการสถานะคำสั่งซื้อสำเร็จ",
    }
    GET_LIST_ORDER_STATUS_MAPPING_SUCCESS = {
        Language.EN: "Order status mappings fetched successfully",
        Language.KR: "주문 상태 매핑 목록을 성공적으로 가져왔습니다",
        Language.TH: "ดึงรายการการจัดการสถานะคำสั่งซื้อสำเร็จ",
    }
    GET_ORDER_STATUS_MAPPING_DETAIL_SUCCESS = {
        Language.EN: "Order status mapping fetched successfully",
        Language.KR: "주문 상태 매핑 정보를 성공적으로 가져왔습니다",
        Language.TH: "ดึงข้อมูลการจัดการสถานะคำสั่งซื้อสำเร็จ",
    }
    GET_AVAILABLE_STATUSES_SUCCESS = {
        Language.EN: "Available statuses fetched successfully",
        Language.KR: "사용 가능한 상태를 성공적으로 가져왔습니다",
        Language.TH: "ดึงรายการสถานะที่ใช้ได้สำเร็จ",
    }
    RESOLVE_STATUS_MAPPING_SUCCESS = {
        Language.EN: "Status mapping resolved successfully",
        Language.KR: "상태 매핑이 성공적으로 해결되었습니다",
        Language.TH: "การจัดการสถานะถูกแก้ไขสำเร็จ",
    }
    STATUS_MAPPING_NOT_FOUND = {
        Language.EN: "No mapping found for this external status code",
        Language.KR: "이 외부 상태 코드에 대한 매핑을 찾을 수 없습니다",
        Language.TH: "ไม่พบการจัดการสถานะสำเร็จ",
    }
    EXTERNAL_ORDER_STATUS_NOT_FOUND = {
        Language.EN: "External order status not found",
        Language.KR: "외부 주문 상태를 찾을 수 없습니다",
        Language.TH: "ไม่พบสถานะคำสั่งซื้อภายนอก",
    }
    ORDER_STATUS_MAPPING_NOT_FOUND = {
        Language.EN: "Order status mapping not found",
        Language.KR: "주문 상태 매핑을 찾을 수 없습니다",
        Language.TH: "ไม่พบการจัดการสถานะคำสั่งซื้อ",
    }

    # Drawing session messages
    GET_DRAWING_SESSIONS_SUCCESS = {
        Language.EN: "Drawing sessions retrieved successfully.",
        Language.KR: "드로잉 세션 목록 가져오기 성공.",
        Language.TH: "ดึงรายการการวาดสำเร็จ",
    }

    CREATE_DRAWING_SESSION_SUCCESS = {
        Language.EN: "Drawing session created successfully.",
        Language.KR: "드로잉 세션 생성 성공.",
        Language.TH: "สร้างการวาดสำเร็จ",
    }

    GET_DRAWING_SESSION_DETAIL_SUCCESS = {
        Language.EN: "Drawing session detail retrieved successfully.",
        Language.KR: "드로잉 세션 세부정보 가져오기 성공.",
        Language.TH: "ดึงข้อมูลการวาดสำเร็จ",
    }

    UPDATE_DRAWING_SESSION_SUCCESS = {
        Language.EN: "Drawing session updated successfully.",
        Language.KR: "드로잉 세션 업데이트 성공.",
        Language.TH: "อัปเดตการวาดสำเร็จ",
    }

    DELETE_DRAWING_SESSION_SUCCESS = {
        Language.EN: "Drawing session deleted successfully.",
        Language.KR: "드로잉 세션 삭제 성공.",
        Language.TH: "ลบการวาดสำเร็จ",
    }

    JOIN_DRAWING_SESSION_SUCCESS = {
        Language.EN: "Joined drawing session successfully.",
        Language.KR: "드로잉 세션 참여 성공.",
        Language.TH: "เข้าร่วมการวาดสำเร็จ",
    }

    LEAVE_DRAWING_SESSION_SUCCESS = {
        Language.EN: "Left drawing session successfully.",
        Language.KR: "드로잉 세션 나가기 성공.",
        Language.TH: "ออกจากการวาดสำเร็จ",
    }

    CLEAR_DRAWING_ELEMENTS_SUCCESS = {
        Language.EN: "Drawing elements cleared successfully.",
        Language.KR: "드로잉 요소 지우기 성공.",
        Language.TH: "ลบการวาดสำเร็จ",
    }

    # Drawing element messages
    CREATE_DRAWING_ELEMENT_SUCCESS = {
        Language.EN: "Drawing element created successfully.",
        Language.KR: "드로잉 요소 생성 성공.",
        Language.TH: "สร้างการวาดสำเร็จ",
    }

    UPDATE_DRAWING_ELEMENT_SUCCESS = {
        Language.EN: "Drawing element updated successfully.",
        Language.KR: "드로잉 요소 업데이트 성공.",
        Language.TH: "อัปเดตการวาดสำเร็จ",
    }

    DELETE_DRAWING_ELEMENT_SUCCESS = {
        Language.EN: "Drawing element deleted successfully.",
        Language.KR: "드로잉 요소 삭제 성공.",
        Language.TH: "ลบการวาดสำเร็จ",
    }

    UPDATE_STREAM_MONITOR_SUCCESS = {
        Language.EN: "Stream monitor updated successfully.",
        Language.KR: "스트림 모니터 업데이트 성공.",
        Language.TH: "อัปเดตการวาดสำเร็จ",
    }

    GET_AI_MODELS_SUCCESS = {
        Language.EN: "AI models retrieved successfully.",
        Language.KR: "AI 모델 목록 가져오기 성공.",
        Language.TH: "ดึงรายการการวาดสำเร็จ",
    }

    START_RECORD_SUCCESS = {
        Language.EN: "Stream monitor record started successfully.",
        Language.KR: "스트림 모니터 녹화 시작 성공.",
        Language.TH: "การวาดสำเร็จ",
    }

    STOP_RECORD_SUCCESS = STOP_RECORD_SUCCESS = {
        Language.EN: "Recording has been stopped successfully. Please wait 30-60 seconds while the video and analysis are uploaded to storage.",
        Language.KR: "녹화가 성공적으로 중지되었습니다. 녹화된 비디오와 분석 결과가 스토리지에 업로드되는 동안 30~60초 정도 기다려 주세요.",
        Language.TH: "หยุดการบันทึกสำเร็จแล้ว กรุณารอประมาณ 30-60 วินาที ระหว่างอัปโหลดวิดีโอและผลการวิเคราะห์ไปยังพื้นที่จัดเก็บ",
    }

    GET_STREAM_MONITOR_CAPTURE_FAILED = {
        Language.EN: "Failed to save the captured image.",
        Language.KR: "캡처된 이미지를 저장하지 못했습니다.",
        Language.TH: "ภาพที่ถ่ายได้ถูกบันทึกไว้แล้ว",
    }

    GET_LIST_CHECKLIST_SETTING_SUCCESS = {
        Language.EN: "Checklist setting list fetched successfully.",
        Language.KR: "체크리스트 설정 목록 가져오기 성공.",
        Language.TH: "ดึงรายการการวาดสำเร็จ",
    }

    CREATE_CHECKLIST_SETTING_SUCCESS = {
        Language.EN: "Checklist setting created successfully.",
        Language.KR: "체크리스트 설정 생성 성공.",
        Language.TH: "สร้างการวาดสำเร็จ",
    }

    UPDATE_CHECKLIST_SETTING_SUCCESS = {
        Language.EN: "Checklist setting updated successfully.",
        Language.KR: "체크리스트 설정 업데이트 성공.",
        Language.TH: "อัปเดตการวาดสำเร็จ",
    }

    DELETE_CHECKLIST_SETTING_SUCCESS = {
        Language.EN: "Checklist setting deleted successfully.",
        Language.KR: "체크리스트 설정 삭제 성공.",
        Language.TH: "ลบการวาดสำเร็จ",
    }

    DELETE_CHECKLIST_SETTING_FAILED = {
        Language.EN: "The checklist has been used and cannot be deleted.",
        Language.KR: "체크리스트에 사용된 체크리스트 설정은 삭제할 수 없습니다.",
        Language.TH: "การวาดสำเร็จ",
    }

    CHECKLIST_SETTING_NOT_FOUND = {
        Language.EN: "Checklist setting not found.",
        Language.KR: "체크리스트 설정을 찾을 수 없습니다.",
        Language.TH: "การวาดสำเร็จ",
    }

    GET_LIST_CHECKLIST_SETTING_CATEGORY_SUCCESS = {
        Language.EN: "Checklist setting category list fetched successfully.",
        Language.KR: "체크리스트 설정 카테고리 목록 가져오기 성공.",
        Language.TH: "การวาดสำเร็จ",
    }

    CREATE_CHECKLIST_SETTING_CATEGORY_SUCCESS = {
        Language.EN: "Checklist setting category created successfully.",
        Language.KR: "체크리스트 설정 카테고리 생성 성공.",
        Language.TH: "การวาดสำเร็จ",
    }

    DELETE_CHECKLIST_SETTING_CATEGORY_SUCCESS = {
        Language.EN: "Checklist setting category deleted successfully.",
        Language.KR: "체크리스트 설정 카테고리 삭제 성공.",
        Language.TH: "การวาดสำเร็จ",
    }

    UNEXPECTED_ERROR = {
        Language.EN: "Unexpected error occurred.",
        Language.KR: "예상치 못한 오류가 발생했습니다.",
        Language.TH: "การวาดสำเร็จ",
    }

    PAUSE_RECORD_SUCCESS = {
        Language.EN: "Stream monitor record paused successfully.",
        Language.KR: "스트림 모니터 녹화 일시정지 성공.",
        Language.TH: "การวาดสำเร็จ",
    }

    RESUME_RECORD_SUCCESS = {
        Language.EN: "Stream monitor record resumed successfully.",
        Language.KR: "스트림 모니터 녹화 재생 성공.",
        Language.TH: "การวาดสำเร็จ",
    }

    CHANGE_STATUS_ORDER_SUCCESS = {
        Language.EN: "Order status changed successfully.",
        Language.KR: "주문 상태가 성공적으로 변경되었습니다.",
        Language.TH: "การวาดสำเร็จ",
    }

    GET_LIST_OPERATIONAL_DATA_SUCCESS = {
        Language.EN: "Operational data fetched successfully.",
        Language.KR: "운영 데이터가 성공적으로 가져왔습니다.",
        Language.TH: "การวาดสำเร็จ",
    }

    GET_LIST_OPERATIONAL_DATA_FAILED = {
        Language.EN: "Operational data fetched failed.",
        Language.KR: "운영 데이터가 가져오기 실패했습니다.",
        Language.TH: "การวาดสำเร็จ",
    }

    CREATE_WEATHER_SETTING_SUCCESS = {
        Language.EN: "Weather setting created successfully.",
        Language.KR: "날씨 설정이 성공적으로 생성되었습니다.",
        Language.TH: "การวาดสำเร็จ",
    }

    DOWNLOAD_OPERATIONAL_LOG_DRONE_SUCCESS = {
        Language.EN: "Operational log drone downloaded successfully.",
        Language.KR: "운영 로그 드론이 성공적으로 다운로드되었습니다.",
        Language.TH: "การวาดสำเร็จ",
    }
    
    DOWNLOAD_OPERATIONAL_LOG_DRONE_FAILED = {
        Language.EN: "Operational log drone downloaded failed.",
        Language.KR: "운영 로그 드론이 다운로드 실패했습니다.",
        Language.TH: "การวาดสำเร็จ",
    }

    UPLOAD_OPERATIONAL_LOG_ROBOT_SUCCESS = {
        Language.EN: "Operational log robot uploaded successfully.",
        Language.KR: "운영 로그 로봇이 성공적으로 업로드되었습니다.",
        Language.TH: "การวาดสำเร็จ",
    }
    
    UPLOAD_OPERATIONAL_LOG_ROBOT_FAILED = {
        Language.EN: "Operational log robot uploaded failed.",
        Language.KR: "운영 로그 로봇이 업로드 실패했습니다.",
        Language.TH: "การวาดสำเร็จ",
    }

    UPLOAD_OPERATIONAL_VIDEO_DRONE_SUCCESS = {
        Language.EN: "Operational video drone upload queued successfully. You will be notified when complete.",
        Language.KR: "운영 비디오 드론 업로드가 성공적으로 대기열에 추가되었습니다. 완료되면 알림을 받게 됩니다.",
        Language.TH: "การวาดสำเร็จ",
    }
    
    UPLOAD_OPERATIONAL_VIDEO_DRONE_FAILED = {
        Language.EN: "Operational video drone uploaded failed.",
        Language.KR: "운영 비디오 드론이 업로드 실패했습니다.",
        Language.TH: "การวาดสำเร็จ",
    }

    UPLOAD_OPERATIONAL_VIDEO_ROBOT_SUCCESS = {
        Language.EN: "Operational video robot upload queued successfully. You will be notified when complete.",
        Language.KR: "운영 비디오 로봇 업로드가 성공적으로 대기열에 추가되었습니다. 완료되면 알림을 받게 됩니다.",
        Language.TH: "การวาดสำเร็จ",
    }
    
    UPLOAD_OPERATIONAL_VIDEO_ROBOT_FAILED = {
        Language.EN: "Operational video robot uploaded failed.",
        Language.KR: "운영 비디오 로봇이 업로드 실패했습니다.",
        Language.TH: "การวาดสำเร็จ",
    }
    # QGroundController Plan Import/Export messages
    IMPORT_PLAN_SUCCESS = {
        Language.EN: "Plan file imported successfully.",
        Language.KR: "계획 파일 가져오기 성공.",
        Language.TH: "การวาดสำเร็จ",
    }

    IMPORT_PLAN_FAILED = {
        Language.EN: "Failed to import plan file.",
        Language.KR: "계획 파일 가져오기 실패.",
        Language.TH: "การวาดสำเร็จ",
    }

    EXPORT_PLANS_SUCCESS = {
        Language.EN: "Downloaded successfully",
        Language.KR: "다운로드가 완료되었습니다",
        Language.TH: "Downloaded successfully",
    }

    EXPORT_PLANS_FAILED = {
        Language.EN: "Download failed",
        Language.KR: "다운로드에 실패했습니다",
        Language.TH: "Download failed",
    }

    INVALID_PLAN_FORMAT = {
        Language.EN: "Invalid plan file format.",
        Language.KR: "잘못된 계획 파일 형식.",
        Language.TH: "การวาดสำเร็จ",
    }

    PLAN_FILE_TOO_LARGE = {
        Language.EN: "Plan file size too large. Maximum size is 10MB.",
        Language.KR: "계획 파일 크기가 너무 큽니다. 최대 크기는 10MB입니다.",
        Language.TH: "การวาดสำเร็จ",
    }

    NO_VALID_ROUTES_FOUND = {
        Language.EN: "No valid routes found for export.",
        Language.KR: "내보낼 유효한 경로를 찾을 수 없습니다.",
        Language.TH: "การวาดสำเร็จ",
    }

    UPLOAD_OPERATIONAL_LOG_DRONE_SUCCESS = {
        Language.EN: "Operational log drone uploaded successfully.",
        Language.KR: "운영 로그 드론이 성공적으로 업로드되었습니다.",
        Language.TH: "การวาดสำเร็จ",
    }
    
    UPLOAD_OPERATIONAL_LOG_DRONE_FAILED = {
        Language.EN: "Operational log drone uploaded failed.",
        Language.KR: "운영 로그 드론이 업로드 실패했습니다.",
        Language.TH: "การวาดสำเร็จ",
    }

    DOWNLOAD_OPERATIONAL_LOG_ROBOT_SUCCESS = {
        Language.EN: "Operational log robot downloaded successfully.",
        Language.KR: "운영 로그 로봇이 성공적으로 다운로드되었습니다.",
        Language.TH: "การวาดสำเร็จ",
    }
    
    DOWNLOAD_OPERATIONAL_LOG_ROBOT_FAILED = {
        Language.EN: "Operational log robot downloaded failed.",
        Language.KR: "운영 로그 로봇이 다운로드 실패했습니다.",
        Language.TH: "การวาดสำเร็จ",
    }

    OPERATIONAL_LOG_ROBOT_EMPTY = {
        Language.EN: "Operational log robot is empty.",
        Language.KR: "운영 로그 로봇이 비어있습니다.",
        Language.TH: "การวาดสำเร็จ",
    }
    
    OPERATIONAL_LOG_DRONE_EMPTY = {
        Language.EN: "Operational log drone is empty.",
        Language.KR: "운영 로그 드론이 비어있습니다.",
        Language.TH: "การวาดสำเร็จ",
    }

    DOWNLOAD_OPERATIONAL_DATA_SUCCESS = {
        Language.EN: "Operational data downloaded successfully.",
        Language.KR: "운영 데이터가 성공적으로 다운로드되었습니다.",
        Language.TH: "การวาดสำเร็จ",
    }
    
    DOWNLOAD_OPERATIONAL_DATA_FAILED = {
        Language.EN: "Operational data downloaded failed.",
        Language.KR: "운영 데이터가 다운로드 실패했습니다.",
        Language.TH: "การวาดสำเร็จ",
    }

    OPERATIONAL_DATA_EMPTY = {
        Language.EN: "Operational data is empty.",
        Language.KR: "운영 데이터가 비어있습니다.",
        Language.TH: "การวาดสำเร็จ",
    }

    # Partner messages
    GET_LIST_PARTNER_SUCCESS = {
        Language.EN: "Partners fetched successfully.",
        Language.KR: "파트너 목록 가져오기 성공.",
        Language.TH: "การวาดสำเร็จ",
    }
    GET_PARTNER_SUCCESS = {
        Language.EN: "Partner fetched successfully.",
        Language.KR: "파트너 정보 가져오기 성공.",
        Language.TH: "การวาดสำเร็จ",
    }
    CREATE_PARTNER_SUCCESS = {
        Language.EN: "Partner created successfully.",
        Language.KR: "파트너 생성 성공.",
        Language.TH: "การวาดสำเร็จ",
    }
    CREATE_PARTNER_FAILED = {
        Language.EN: "Partner creation failed.",
        Language.KR: "파트너 생성 실패.",
        Language.TH: "การวาดสำเร็จ",
    }
    UPDATE_PARTNER_SUCCESS = {
        Language.EN: "Partner updated successfully.",
        Language.KR: "파트너 업데이트 성공.",
        Language.TH: "การวาดสำเร็จ",
    }
    UPDATE_PARTNER_FAILED = {
        Language.EN: "Partner update failed.",
        Language.KR: "파트너 업데이트 실패.",
        Language.TH: "การวาดสำเร็จ",
    }
    DELETE_PARTNER_SUCCESS = {
        Language.EN: "Partner deleted successfully.",
        Language.KR: "파트너 삭제 성공.",
        Language.TH: "การวาดสำเร็จ",
    }
    DELETE_PARTNER_FAILED = {
        Language.EN: "Partner deletion failed.",
        Language.KR: "파트너 삭제 실패.",
        Language.TH: "การวาดสำเร็จ",
    }
    PARTNER_NOT_FOUND = {
        Language.EN: "Partner not found.",
        Language.KR: "파트너를 찾을 수 없습니다.",
    }
    UPDATE_PARTNER_API_CALLBACK_SUCCESS = {
        Language.EN: "Partner API callback URLs updated successfully.",
        Language.KR: "파트너 API 콜백 URL 업데이트 성공.",
        Language.TH: "การวาดสำเร็จ",
    }
    UPDATE_PARTNER_API_CALLBACK_FAILED = {
        Language.EN: "Partner API callback URLs update failed.",
        Language.KR: "파트너 API 콜백 URL 업데이트 실패.",
        Language.TH: "การวาดสำเร็จ",
    }
    GENERATE_PARTNER_API_KEY_SUCCESS = {
        Language.EN: "Partner API key generated successfully.",
        Language.KR: "파트너 API 키 생성 성공.",
        Language.TH: "การวาดสำเร็จ",
    }
    GENERATE_PARTNER_API_KEY_FAILED = {
        Language.EN: "Partner API key generation failed.",
        Language.KR: "파트너 API 키 생성 실패.",
        Language.TH: "การวาดสำเร็จ",
    }
    GENERATE_PARTNER_REFRESH_TOKEN_SUCCESS = {
        Language.EN: "Partner refresh token generated successfully.",
        Language.KR: "파트너 리프레시 토큰 생성 성공.",
        Language.TH: "การวาดสำเร็จ",
    }
    GENERATE_PARTNER_REFRESH_TOKEN_FAILED = {
        Language.EN: "Partner refresh token generation failed.",
        Language.KR: "파트너 리프레시 토큰 생성 실패.",
        Language.TH: "การวาดสำเร็จ",
    }
    REFRESH_PARTNER_TOKEN_SUCCESS = {
        Language.EN: "Partner token refreshed successfully.",
        Language.KR: "파트너 토큰 갱신 성공.",
        Language.TH: "การวาดสำเร็จ",
    }
    REFRESH_PARTNER_TOKEN_FAILED = {
        Language.EN: "Partner token refresh failed.",
        Language.KR: "파트너 토큰 갱신 실패.",
        Language.TH: "การวาดสำเร็จ",
    }
    REVOKE_PARTNER_REFRESH_TOKEN_SUCCESS = {
        Language.EN: "Partner refresh token revoked successfully.",
        Language.KR: "파트너 리프레시 토큰 폐기 성공.",
        Language.TH: "การวาดสำเร็จ",
    }
    REVOKE_PARTNER_REFRESH_TOKEN_FAILED = {
        Language.EN: "Partner refresh token revocation failed.",
        Language.KR: "파트너 리프레시 토큰 폐기 실패.",
        Language.TH: "การวาดสำเร็จ",
    }
    
    # Partner Management messages
    CREATE_PARTNER_WITH_PROXY_SUCCESS = {
        Language.EN: "Partner created successfully with auto-generated credentials.",
        Language.KR: "파트너가 자동 생성된 자격 증명과 함께 성공적으로 생성되었습니다.",
        Language.TH: "การวาดสำเร็จ",
    }
    CREATE_PARTNER_WITH_PROXY_FAILED = {
        Language.EN: "Failed to create partner with proxy user.",
        Language.KR: "프록시 사용자로 파트너 생성에 실패했습니다.",
        Language.TH: "การวาดสำเร็จ",
    }
    TOGGLE_PARTNER_STATUS_SUCCESS = {
        Language.EN: "Partner status updated successfully.",
        Language.KR: "파트너 상태가 성공적으로 업데이트되었습니다.",
        Language.TH: "การวาดสำเร็จ",
    }
    TOGGLE_PARTNER_STATUS_FAILED = {
        Language.EN: "Failed to update partner status.",
        Language.KR: "파트너 상태 업데이트에 실패했습니다.",
        Language.TH: "การวาดสำเร็จ",
    }
    REGENERATE_PARTNER_API_KEY_SUCCESS = {
        Language.EN: "Partner API key regenerated successfully.",
        Language.KR: "파트너 API 키가 성공적으로 재생성되었습니다.",
        Language.TH: "การวาดสำเร็จ",
    }
    REGENERATE_PARTNER_API_KEY_FAILED = {
        Language.EN: "Failed to regenerate partner API key.",
        Language.KR: "파트너 API 키 재생성에 실패했습니다.",
        Language.TH: "การวาดสำเร็จ",
    }
    UPDATE_PARTNER_API_KEY_SUCCESS = {
        Language.EN: "Partner API key updated successfully.",
        Language.KR: "파트너 API 키가 성공적으로 업데이트되었습니다.",
        Language.TH: "การวาดสำเร็จ",
    }
    UPDATE_PARTNER_API_KEY_FAILED = {
        Language.EN: "Failed to update partner API key.",
        Language.KR: "파트너 API 키 업데이트에 실패했습니다.",
        Language.TH: "การวาดสำเร็จ",
    }
    GET_PARTNER_MANAGEMENT_LIST_SUCCESS = {
        Language.EN: "Partner management list fetched successfully.",
        Language.KR: "파트너 관리 목록을 성공적으로 가져왔습니다.",
        Language.TH: "การวาดสำเร็จ",
    }
    GET_PARTNER_MANAGEMENT_DETAIL_SUCCESS = {
        Language.EN: "Partner management detail fetched successfully.",
        Language.KR: "파트너 관리 세부 정보를 성공적으로 가져왔습니다.",
        Language.TH: "การวาดสำเร็จ",
    }
    TERMINAL_CODE_ALREADY_EXISTS = {
        Language.EN: "Terminal id already exists.",
        Language.KR: "터미널 ID가 이미 존재했습니다.",
        Language.TH: "ไอดีเทอร์มินัลมีอยู่แล้ว",
    }

    DOCKING_STATION_CODE_ALREADY_EXISTS = {
        Language.EN: "Docking station id already exists.",
        Language.KR: "도킹스테이션 ID가 이미 존재했습니다.",
        Language.TH: "ไอดีสถานีเชื่อมต่อมีอยู่แล้ว",
    }

    INFRASTRUCTURE_CODE_ALREADY_EXISTS = {
        Language.EN: "Infrastructure id already exists.",
        Language.KR: "인프라 ID가 이미 존재했습니다.",
        Language.TH: "ไอดีโครงสร้างพื้นฐานมีอยู่แล้ว",
    }


    DELIVERY_HUB_CODE_ALREADY_EXISTS = {
        Language.EN: "Delivery hub id already exists.",
        Language.KR: "배달거점 ID가 이미 존재했습니다.",
        Language.TH: "ไอดีศูนย์จัดส่งมีอยู่แล้ว",
    }

    GET_LIST_FLIGHT_LOG_SUCCESS = {
        Language.EN: "Flight log list fetched successfully.",
        Language.KR: "항공 로그 목록을 성공적으로 가져왔습니다.",
        Language.TH: "การวาดสำเร็จ",
    }

    GET_LIST_FLIGHT_LOG_FAILED = {
        Language.EN: "Failed to fetch flight log list.",
        Language.KR: "항공 로그 목록을 가져오는데 실패했습니다.",
        Language.TH: "การวาดสำเร็จ",
    }

    GET_FLIGHT_LOG_DETAIL_SUCCESS = {
        Language.EN: "Flight log detail fetched successfully.",
        Language.KR: "항공 로그 세부 정보를 성공적으로 가져왔습니다.",
        Language.TH: "การวาดสำเร็จ",
    }

    GET_FLIGHT_LOG_DETAIL_FAILED = {
        Language.EN: "Failed to fetch flight log detail.",
        Language.KR: "항공 로그 세부 정보를 가져오는데 실패했습니다.",
        Language.TH: "การวาดสำเร็จ",
    }

    # Generic CRUD messages
    GET_SUCCESS = {
        Language.EN: "Get operational notice successfully",
        Language.KR: "연산 공지 가져오기 성공",
        Language.TH: "การวาดสำเร็จ",
    }
    GET_FAILED = {
        Language.EN: "Failed to retrieve operational notice",
        Language.KR: "연산 공지 가져오기 실패",
        Language.TH: "การวาดสำเร็จ",
    }
    GET_LIST_FAILED = {
        Language.EN: "Failed to retrieve operational notice list",
        Language.KR: "연산 공지 목록 가져오기 실패",
        Language.TH: "การวาดสำเร็จ",
    }
    CREATE_SUCCESS = {
        Language.EN: "Created operational notice successfully",
        Language.KR: "공지가 생성되었습니다",
        Language.TH: "การวาดสำเร็จ",
    }
    CREATE_FAILED = {
        Language.EN: "Creation operational notice failed",
        Language.KR: "공지 생성에 실패했습니다",
        Language.TH: "การวาดสำเร็จ",
    }
    UPDATE_SUCCESS = {
        Language.EN: "Updated operational notice successfully", 
        Language.KR: "공지가 업데이트되었습니다",
        Language.TH: "การวาดสำเร็จ",
    }
    UPDATE_FAILED = {
        Language.EN: "Update operational notice failed",
        Language.KR: "공지 업데이트에 실패했습니다",
        Language.TH: "การวาดสำเร็จ",
    }
    DELETE_SUCCESS = {
        Language.EN: "Deleted operational notice successfully",
        Language.KR: "공지가 삭제되었습니다",
        Language.TH: "การวาดสำเร็จ",
    }
    DELETE_FAILED = {
        Language.EN: "Deletion operational notice failed",
        Language.KR: "공지 삭제에 실패했습니다",
        Language.TH: "การวาดสำเร็จ",
    }
    VALIDATION_ERROR = {
        Language.EN: "Validation operational notice error",
        Language.KR: "연산 공지 유효성 검사 오류",
        Language.TH: "การวาดสำเร็จ",
    }

    # AI Stream URL webhook messages
    GET_AI_STREAM_URL_SUCCESS = {
        Language.EN: "AI stream data processed successfully",
        Language.KR: "AI 스트림 데이터 처리 성공",
        Language.TH: "ประมวลผลข้อมูล AI สตรีมสำเร็จ",
    }
    GET_AI_STREAM_URL_FAILED = {
        Language.EN: "Failed to process AI stream data",
        Language.KR: "AI 스트림 데이터 처리 실패",
        Language.TH: "ประมวลผลข้อมูล AI สตรีมไม่สำเร็จ",
    }

    CANCEL_FLIGHT_SUCCESS = {
        Language.EN: "Flight cancelled successfully",
        Language.KR: "비행이 성공적으로 취소되었습니다",
        Language.TH: "เที่ยวบินถูกยกเลิกสำเร็จ",
    }

    CHANGE_DRONE_SUCCESS = {
        Language.EN: "Drone changed successfully",
        Language.KR: "드론이 변경되었습니다",
        Language.TH: "โดรนถูกเปลี่ยนเรียบร้อยแล้ว",
    }

    APPROVE_FLIGHT_SUCCESS = {
        Language.EN: "Flight approved successfully",
        Language.KR: "비행이 승인되었습니다",
        Language.TH: "การบินได้รับการอนุมัติเรียบร้อยแล้ว",
    }
    APPROVE_FLIGHT_FLIGHTBIRD_ERROR = {
        Language.EN: "Delivery start failed.",
        Language.KR: "배송 시작에 실패했습니다.",
        Language.TH: "เกิดข้อผิดพลาดในการอนุมัติการบิน.",
    }

    # Surveillance Profile messages
    GET_SURVEILLANCE_PROFILE_SUCCESS = {
        Language.EN: "Surveillance profile retrieved successfully",
        Language.KR: "프로파일이 조회되었습니다",
        Language.TH: "การดำเนินการสำเร็จ",
    }
    CREATE_SURVEILLANCE_PROFILE_SUCCESS = {
        Language.EN: "Surveillance profile created successfully",
        Language.KR: "프로파일이 생성되었습니다",
        Language.TH: "การดำเนินการสำเร็จ",
    }
    CREATE_SURVEILLANCE_PROFILE_FAILED = {
        Language.EN: "Surveillance profile creation failed",
        Language.KR: "프로파일 생성에 실패했습니다",
        Language.TH: "การดำเนินการล้มเหลว",
    }
    UPDATE_SURVEILLANCE_PROFILE_SUCCESS = {
        Language.EN: "Surveillance profile updated successfully",
        Language.KR: "프로파일이 업데이트되었습니다",
        Language.TH: "การดำเนินการสำเร็จ",
    }
    APPROVE_SURVEILLANCE_PROFILE_SUCCESS = {
        Language.EN: "Surveillance profile approved successfully",
        Language.KR: "프로파일이 승인되었습니다",
        Language.TH: "การดำเนินการสำเร็จ",
    }
    COMPLETE_SURVEILLANCE_PROFILE_CHECK_SUCCESS = {
        Language.EN: "Surveillance profile checklist completed successfully",
        Language.KR: "프로파일이 성공적으로 시작되었습니다",
        Language.TH: "การดำเนินการสำเร็จ",
    }
    REJECT_SURVEILLANCE_PROFILE_SUCCESS = {
        Language.EN: "Surveillance profile rejected successfully",
        Language.KR: "프로파일이 반려되었습니다",
        Language.TH: "การดำเนินการสำเร็จ",
    }
    DELETE_SURVEILLANCE_PROFILE_SUCCESS = {
        Language.EN: "Surveillance profile deleted successfully",
        Language.KR: "프로파일이 삭제되었습니다",
        Language.TH: "การดำเนินการสำเร็จ",
    }
    MARK_SURVEILLANCE_PROFILE_DRONE_FLIGHT_TIME_SUCCESS = {
        Language.EN: "Drone flight time recorded successfully",
        Language.KR: "드론 비행 시간이 기록되었습니다",
        Language.TH: "บันทึกเวลาการบินของโดรนเรียบร้อยแล้ว",
    }
    DRONE_CONFLICT_WITH_PROFILE = {
        Language.EN: "The following drones cannot be assigned due to time overlap with other profiles: {drone_names}. Details: {conflict_details}. Please change the time or select different drones.",
        Language.KR: "다음 드론은 다른 프로파일과 시간이 겹쳐 할당할 수 없습니다: {drone_names}. 세부사항: {conflict_details}. 시간을 변경하거나 다른 드론을 선택해주세요.",
        Language.TH: "โดรนต่อไปนี้ไม่สามารถกำหนดได้เนื่องจากเวลาซ้อนทับกับโปรไฟล์อื่น: {drone_names}. รายละเอียด: {conflict_details}. กรุณาเปลี่ยนเวลาหรือเลือกโดรนอื่น",
    }

    # Surveillance - available devices (GCS + route assignment diagnostics)
    SURVEILLANCE_AVAILABLE_DEVICES_GCS_URL_NOT_CONFIGURED = {
        Language.EN: "GCS base URL is not configured (missing FLIGHTBRID_URL).",
        Language.KR: "GCS 기본 URL이 설정되지 않았습니다(FLIGHTBRID_URL 누락).",
        Language.TH: "ไม่ได้ตั้งค่า URL ของ GCS (ขาด FLIGHTBRID_URL)",
    }
    SURVEILLANCE_AVAILABLE_DEVICES_GCS_FETCH_FAILED = {
        Language.EN: "Failed to fetch available drones from GCS: {error}",
        Language.KR: "GCS에서 사용 가능한 드론을 가져오지 못했습니다: {error}",
        Language.TH: "ไม่สามารถดึงข้อมูลโดรนที่พร้อมใช้งานจาก GCS ได้: {error}",
    }
    SURVEILLANCE_AVAILABLE_DEVICES_GCS_EMPTY = {
        Language.EN: "GCS returned no available drones (full-battery list is empty).",
        Language.KR: "GCS에서 사용 가능한 드론이 없습니다(완충 목록이 비어있음).",
        Language.TH: "GCS ไม่พบโดรนที่พร้อมใช้งาน (รายการแบตเตอรี่เต็มว่างเปล่า)",
    }
    SURVEILLANCE_AVAILABLE_DEVICES_NO_MATCHING_DB_DRONES = {
        Language.EN: "No active drone devices in the system match the available drones from GCS (unit_ids={unit_ids_count}).",
        Language.KR: "GCS의 사용 가능한 드론과 일치하는 활성 드론 장치를 시스템에서 찾을 수 없습니다(unit_ids={unit_ids_count}).",
        Language.TH: "ไม่พบอุปกรณ์โดรนที่เปิดใช้งานในระบบซึ่งตรงกับโดรนที่ GCS รายงาน (unit_ids={unit_ids_count})",
    }
    SURVEILLANCE_AVAILABLE_DEVICES_IMPORTED_ROUTE_NO_SEGMENTS = {
        Language.EN: "Mission is imported from route but has no drone segments to build the path.",
        Language.KR: "임무가 경로에서 가져왔지만 경로를 만들 드론 세그먼트가 없습니다.",
        Language.TH: "ภารกิจนำเข้าจากเส้นทาง แต่ไม่มี drone segments สำหรับสร้างเส้นทาง",
    }
    SURVEILLANCE_AVAILABLE_DEVICES_NO_CANDIDATES = {
        Language.EN: "No suitable drone candidates for mission assignment (devices={devices_count}, missing_instances={missing_instances_count}).",
        Language.KR: "임무 할당을 위한 적합한 드론 후보가 없습니다(장치={devices_count}, 인스턴스 누락={missing_instances_count}).",
        Language.TH: "ไม่มีโดรนที่เหมาะสมสำหรับการกำหนดภารกิจ (อุปกรณ์={devices_count}, ขาดข้อมูลอุปกรณ์={missing_instances_count})",
    }
    SURVEILLANCE_AVAILABLE_DEVICES_ASSIGNMENT_FAILED = {
        Language.EN: "Unable to generate default routes/assignments for this mission. {detail}",
        Language.KR: "이 임무에 대한 기본 경로/할당을 생성할 수 없습니다. {detail}",
        Language.TH: "ไม่สามารถสร้างเส้นทาง/การกำหนดค่าเริ่มต้นสำหรับภารกิจนี้ได้ {detail}",
    }
    SURVEILLANCE_AVAILABLE_DEVICES_SEGMENT_UNASSIGNABLE = {
        Language.EN: "Segment {segment_index} cannot be assigned (distance={distance_km} km). Example: {example}",
        Language.KR: "구간 {segment_index}을(를) 할당할 수 없습니다(거리={distance_km} km). 예: {example}",
        Language.TH: "ไม่สามารถกำหนดช่วง {segment_index} ได้ (ระยะทาง={distance_km} กม.). ตัวอย่าง: {example}",
    }
    SURVEILLANCE_AVAILABLE_DEVICES_DRONE_CANNOT_COMPLETE = {
        Language.EN: "Drone {drone_name} cannot complete: {reasons}",
        Language.KR: "드론 {drone_name}이(가) 완료할 수 없습니다: {reasons}",
        Language.TH: "โดรน {drone_name} ไม่สามารถทำภารกิจให้สำเร็จได้: {reasons}",
    }

    # Surveillance - estimation failure reasons (used when can_complete=False)
    SURVEILLANCE_ESTIMATION_FAIL_MISSING_CRUISE_SPEED = {
        Language.EN: "Missing cruise speed; cannot estimate duration.",
        Language.KR: "순항 속도 정보가 없어 비행 시간을 추정할 수 없습니다.",
        Language.TH: "ไม่มีความเร็วล่องเรือ จึงประเมินเวลาได้",
    }
    SURVEILLANCE_ESTIMATION_FAIL_MISSING_FLIGHT_TIME = {
        Language.EN: "Missing flight time measurement; cannot verify battery/time constraint.",
        Language.KR: "비행 시간 측정값이 없어 배터리/시간 제약을 확인할 수 없습니다.",
        Language.TH: "ไม่มีค่าระยะเวลาการบิน จึงตรวจสอบข้อจำกัดแบตเตอรี่/เวลาไม่ได้",
    }
    SURVEILLANCE_ESTIMATION_FAIL_BATTERY_TIME = {
        Language.EN: "Estimated duration {estimated_min} min exceeds flight time {flight_time_min} min.",
        Language.KR: "예상 비행 시간 {estimated_min}분이 비행 가능 시간 {flight_time_min}분을 초과합니다.",
        Language.TH: "เวลาที่คาดการณ์ {estimated_min} นาที เกินเวลาบิน {flight_time_min} นาที",
    }
    SURVEILLANCE_ESTIMATION_FAIL_RANGE = {
        Language.EN: "Distance {distance_km} km exceeds maximum range {max_range_km} km.",
        Language.KR: "거리 {distance_km}km가 최대 항속 거리 {max_range_km}km를 초과합니다.",
        Language.TH: "ระยะทาง {distance_km} กม. เกินระยะสูงสุด {max_range_km} กม.",
    }
    SURVEILLANCE_ESTIMATION_FAIL_WIND = {
        Language.EN: "Wind speed {wind_ms} m/s exceeds wind resistance {resistance_ms} m/s.",
        Language.KR: "풍속 {wind_ms}m/s가 풍속 저항 {resistance_ms}m/s를 초과합니다.",
        Language.TH: "ความเร็วลม {wind_ms} ม./วินาที เกินความต้านทานลม {resistance_ms} ม./วินาที",
    }
    SURVEILLANCE_ESTIMATION_FAIL_UNKNOWN = {
        Language.EN: "Flight constraints are not satisfied.",
        Language.KR: "비행 제약 조건을 만족하지 않습니다.",
        Language.TH: "ไม่เป็นไปตามข้อจำกัดการบิน",
    }

    # Patrol GCS messages
    GET_GCS_SESSION_SUCCESS = {
        Language.EN: "GCS session retrieved successfully",
        Language.KR: "GCS 세션 조회 성공",
        Language.TH: "การดำเนินการสำเร็จ",
    }
    CREATE_GCS_SESSION_SUCCESS = {
        Language.EN: "GCS session created successfully",
        Language.KR: "GCS 세션 생성 성공",
        Language.TH: "การดำเนินการสำเร็จ",
    }
    UPDATE_GCS_SESSION_SUCCESS = {
        Language.EN: "GCS session updated successfully",
        Language.KR: "GCS 세션 업데이트 성공",
        Language.TH: "การดำเนินการสำเร็จ",
    }
    START_GCS_SESSION_SUCCESS = {
        Language.EN: "GCS session started successfully",
        Language.KR: "GCS 세션 시작 성공",
        Language.TH: "การดำเนินการสำเร็จ",
    }
    STOP_GCS_SESSION_SUCCESS = {
        Language.EN: "GCS session stopped successfully",
        Language.KR: "GCS 세션 종료 성공",
        Language.TH: "การดำเนินการสำเร็จ",
    }
    GET_TELEMETRY_SUCCESS = {
        Language.EN: "Telemetry data retrieved successfully",
        Language.KR: "텔레메트리 데이터 조회 성공",
        Language.TH: "การดำเนินการสำเร็จ",
    }
    GET_STREAM_URL_SUCCESS = {
        Language.EN: "Stream URL retrieved successfully",
        Language.KR: "스트림 URL 조회 성공",
        Language.TH: "การดำเนินการสำเร็จ",
    }

    # Flight Inspection messages
    GET_FLIGHT_INSPECTION_SUCCESS = {
        Language.EN: "Flight inspection retrieved successfully",
        Language.KR: "비행 점검 조회 성공",
        Language.TH: "การดำเนินการสำเร็จ",
    }
    CREATE_FLIGHT_INSPECTION_SUCCESS = {
        Language.EN: "Flight inspection created successfully",
        Language.KR: "비행 점검 생성 성공",
        Language.TH: "การดำเนินการสำเร็จ",
    }
    UPDATE_FLIGHT_INSPECTION_SUCCESS = {
        Language.EN: "Flight inspection updated successfully",
        Language.KR: "비행 점검 업데이트 성공",
        Language.TH: "การดำเนินการสำเร็จ",
    }
    START_FLIGHT_INSPECTION_SUCCESS = {
        Language.EN: "Flight inspection started successfully",
        Language.KR: "비행 점검 시작 성공",
        Language.TH: "การดำเนินการสำเร็จ",
    }
    SUBMIT_FLIGHT_INSPECTION_SUCCESS = {
        Language.EN: "Flight inspection submitted successfully",
        Language.KR: "비행 점검 제출 성공",
        Language.TH: "การดำเนินการสำเร็จ",
    }
    GET_SENSOR_STATUS_SUCCESS = {
        Language.EN: "Sensor status retrieved successfully",
        Language.KR: "센서 상태 조회 성공",
        Language.TH: "การดำเนินการสำเร็จ",
    }
    SENSOR_STATUS_NOT_AVAILABLE = {
        Language.EN: "Sensor status not available",
        Language.KR: "센서 상태를 사용할 수 없습니다",
        Language.TH: "การดำเนินการสำเร็จ",
    }

    # Survey Mission messages
    MESSAGE_SURVEY_MISSION_CREATED = {
        Language.EN: "Mission created successfully",
        Language.KR: "임무가 성공적으로 생성되었습니다",
        Language.TH: "สร้างภารกิจเรียบร้อยแล้ว",
    }
    MESSAGE_SURVEY_MISSION_UPDATED = {
        Language.EN: "Mission updated successfully",
        Language.KR: "임무가 성공적으로 업데이트되었습니다",
        Language.TH: "อัปเดตภารกิจเรียบร้อยแล้ว",
    }
    MESSAGE_SURVEY_MISSION_DELETED = {
        Language.EN: "Mission deleted successfully",
        Language.KR: "임무가 성공적으로 삭제되었습니다",
        Language.TH: "ลบภารกิจเรียบร้อยแล้ว",
    }
    MESSAGE_SURVEY_MISSION_NOT_FOUND = {
        Language.EN: "Mission not found",
        Language.KR: "임무를 찾을 수 없습니다",
        Language.TH: "ไม่พบภารกิจ",
    }
    MESSAGE_SURVEY_MISSION_APPROVED = {
        Language.EN: "Mission approved successfully",
        Language.KR: "임무가 성공적으로 승인되었습니다",
        Language.TH: "ภารกิจได้รับการอนุมัติเรียบร้อยแล้ว",
    }
    MESSAGE_SURVEY_MISSION_APPROVAL_FAILED = {
        Language.EN: "Mission approval failed",
        Language.KR: "임무 승인에 실패했습니다",
        Language.TH: "การอนุมัติภารกิจล้มเหลว",
    }
    MESSAGE_SURVEY_MISSION_REJECTED = {
        Language.EN: "Mission rejected",
        Language.KR: "임무가 반려되었습니다",
        Language.TH: "ภารกิจถูกปฏิเสธแล้ว",
    }
    MESSAGE_SURVEY_MISSION_REJECTION_FAILED = {
        Language.EN: "Mission rejection failed",
        Language.KR: "임무 반려에 실패했습니다",
        Language.TH: "การปฏิเสธภารกิจล้มเหลว",
    }
    MESSAGE_SURVEY_MISSIONS_ACTIVATED = {
        Language.EN: "Missions activated successfully",
        Language.KR: "임무가 성공적으로 활성화되었습니다",
        Language.TH: "เปิดใช้งานภารกิจเรียบร้อยแล้ว",
    }
    MESSAGE_SURVEY_MISSIONS_ACTIVATION_FAILED = {
        Language.EN: "Survey missions activation failed",
        Language.KR: "정찰 임무 활성화에 실패했습니다",
        Language.TH: "การเปิดใช้งานภารกิจสำรวจล้มเหลว",
    }
    MESSAGE_SURVEY_MISSIONS_DEACTIVATED = {
        Language.EN: "Missions deactivated successfully",
        Language.KR: "임무가 성공적으로 비활성화되었습니다",
        Language.TH: "ปิดใช้งานภารกิจเรียบร้อยแล้ว",
    }
    MESSAGE_SURVEY_MISSIONS_DEACTIVATION_FAILED = {
        Language.EN: "Survey missions deactivation failed",
        Language.KR: "정찰 임무 비활성화에 실패했습니다",
        Language.TH: "การปิดใช้งานภารกิจสำรวจล้มเหลว",
    }
    MESSAGE_OPERATION_FAILED = {
        Language.EN: "Operation failed",
        Language.KR: "작업 실패",
    }
    MESSAGE_SURVEY_MISSION_LIST_SUCCESS = {
        Language.EN: "Survey mission list fetched successfully",
        Language.KR: "조사 미션 목록 조회 성공",
        Language.TH: "ดึงรายการการสำเร็จ",
    }
    MESSAGE_SURVEY_MISSION_IMPORT_STARTED = {
        Language.EN: "Mission import started",
        Language.KR: "임무 가져오기가 시작되었습니다",
        Language.TH: "เริ่มต้นการนำเข้าภารกิจ",
    }
    MESSAGE_SURVEY_MISSION_IMPORT_PROCESSING = {
        Language.EN: "Processing mission import",
        Language.KR: "임무 가져오기 처리 중",
        Language.TH: "กำลังประมวลผลการนำเข้าภารกิจ",
    }
    MESSAGE_SURVEY_MISSION_IMPORT_SUCCESS = {
        Language.EN: "Mission imported successfully",
        Language.KR: "임무가 성공적으로 가져와졌습니다",
        Language.TH: "นำเข้าภารกิจเรียบร้อยแล้ว",
    }
    MESSAGE_SURVEY_MISSION_IMPORT_FAILED = {
        Language.EN: "Mission import failed",
        Language.KR: "임무 가져오기에 실패했습니다",
        Language.TH: "การนำเข้าภารกิจล้มเหลว",
    }

    START_AI_DUAL_STREAM_SUCCESS = {
        Language.EN: "AI dual stream started successfully",
        Language.KR: "AI 듀얼 스트림이 성공적으로 시작되었습니다",
        Language.TH: "การเริ่มต้น AI สตรีมสองสายสำเร็จ",
    }

    STOP_AI_DUAL_STREAM_SUCCESS = {
        Language.EN: "AI dual stream stopped successfully",
        Language.KR: "AI 듀얼 스트림이 성공적으로 중지되었습니다",
        Language.TH: "การหยุด AI สตรีมสองสายสำเร็จ",
    }
    
    GET_AI_DUAL_STREAM_STATUS_SUCCESS = {
        Language.EN: "AI dual stream status retrieved successfully",
        Language.KR: "AI 듀얼 스트림 상태를 성공적으로 가져왔습니다",
        Language.TH: "การดึงสถานะ AI สตรีมสองสายสำเร็จ",
    }

    MESSAGE_PERMISSION_DENIED = {
        Language.EN: "Permission denied",
        Language.KR: "권한이 없습니다",
        Language.TH: "คุณไม่มีสิทธิ์เข้าถึง",
    }

    MESSAGE_GET_DETAIL_PROFILE_SUCCESS = {
        Language.EN: "Profile fetched successfully",
        Language.KR: "프로필 조회 성공",
        Language.TH: "ดึงข้อมูลสำเร็จ",
    }

    DOWNLOAD_LOG_SUCCESS = {
        Language.EN: "Log downloaded successfully",
        Language.KR: "로그가 성공적으로 다운로드되었습니다",
        Language.TH: "ดาวน์โหลดบันทึกสำเร็จ",
    }
    DOWNLOAD_LOG_FAILED = {
        Language.EN: "Log downloaded failed",
        Language.KR: "로그가 다운로드 실패했습니다",
    }
    UPDATE_ALLOW_ORDER_IN_BAD_WEATHER_SUCCESS = {
        Language.EN: "Updated allow order in bad weather successfully",
        Language.KR: "날씨 문제 발생 시 주문을 접수할 수 있도록 설정됨",
        Language.TH: "ตั้งค่าให้รับคำสั่งซื้อได้เมื่อเกิดปัญหาสภาพอากาศ",
    }

    ALLOW_ORDER_IN_BAD_WEATHER_UPDATED = {
        Language.EN: "Set to accept orders in case of weather issues",
        Language.KR: "날씨 문제 발생 시 주문을 접수할 수 있도록 설정됨",
        Language.TH: "ตั้งค่าให้รับคำสั่งซื้อได้เมื่อเกิดปัญหาสภาพอากาศ",
    }

    NOT_ALLOW_ORDER_IN_BAD_WEATHER_UPDATED = {
        Language.EN: "Set to not accept orders in case of weather issues",
        Language.KR: "날씨 문제 발생 시 주문을 접수할 수 없도록 설정됨",
        Language.TH: "ตั้งค่าให้ไม่สามารถรับคำสั่งซื้อได้เมื่อเกิดปัญหาสภาพอากาศ",
    }

    ADD_EXTERNAL_STREAM_MONITOR_SUCCESS = {
        Language.EN: "External stream monitor added successfully",
        Language.KR: "외부 스트림 모니터가 성공적으로 추가되었습니다",
        Language.TH: "สร้างสตรีมสำเร็จ",
    }
    ADD_EXTERNAL_STREAM_MONITOR_FAILED = {
        Language.EN: "External stream monitor added failed",
        Language.KR: "외부 스트림 모니터 추가에 실패했습니다",
        Language.TH: "การสร้างสตรีมล้มเหลว",
    }
    GET_VIDEO_ANALYSIS_SUCCESS = {
        Language.EN: "Video analysis retrieved successfully",
        Language.KR: "비디오 분석 조회 성공",
        Language.TH: "การดำเนินการสำเร็จ",
    }
    GET_VIDEO_ANALYSIS_FAILED = {
        Language.EN: "Video analysis retrieval failed",
        Language.KR: "비디오 분석 조회 실패",
        Language.TH: "การดำเนินการล้มเหลว",
    }

    # Handover Download messages
    START_DOWNLOAD_FILE = {
        Language.EN: "Download request received and queued for processing. You will be notified when complete.",
        Language.KR: "다운로드 요청이 수신되어 처리 대기열에 추가되었습니다. 완료되면 알림을 받게 됩니다.",
        Language.TH: "รับคำขอดาวน์โหลดและเพิ่มเข้าคิวการประมวลผลแล้ว คุณจะได้รับการแจ้งเตือนเมื่อเสร็จสิ้น",
    }
    DOWNLOAD_HANDOVER_MANAGEMENT_SUCCESS = {
        Language.EN: "Handover management file downloaded successfully.",
        Language.KR: "인수인계 관리 파일이 성공적으로 다운로드되었습니다.",
        Language.TH: "ดาวน์โหลดไฟล์การจัดการการส่งมอบสำเร็จ",
    }
    DOWNLOAD_HANDOVER_MANAGEMENT_FAILED = {
        Language.EN: "Handover management file download failed.",
        Language.KR: "인수인계 관리 파일 다운로드 실패했습니다.",
        Language.TH: "ดาวน์โหลดไฟล์การจัดการการส่งมอบล้มเหลว",
    }
    DOWNLOAD_HANDOVER_MANAGEMENT_PROCESSING = {
        Language.EN: "Processing handover management download request...",
        Language.KR: "인수인계 관리 다운로드 요청 처리 중...",
        Language.TH: "กำลังประมวลผลคำขอดาวน์โหลดการจัดการการส่งมอบ...",
    }
    DOWNLOAD_HANDOVER_NOTICE_SUCCESS = {
        Language.EN: "Handover notice file downloaded successfully.",
        Language.KR: "인수인계 공지 파일이 성공적으로 다운로드되었습니다.",
        Language.TH: "ดาวน์โหลดไฟล์ประกาศการส่งมอบสำเร็จ",
    }
    DOWNLOAD_HANDOVER_NOTICE_FAILED = {
        Language.EN: "Handover notice file download failed.",
        Language.KR: "인수인계 공지 파일 다운로드 실패했습니다.",
        Language.TH: "ดาวน์โหลดไฟล์ประกาศการส่งมอบล้มเหลว",
    }
    DOWNLOAD_HANDOVER_NOTICE_PROCESSING = {
        Language.EN: "Processing handover notice download request...",
        Language.KR: "인수인계 공지 다운로드 요청 처리 중...",
        Language.TH: "กำลังประมวลผลคำขอดาวน์โหลดประกาศการส่งมอบ...",
    }
    DOWNLOAD_HANDOVER_EMPTY_DATA = {
        Language.EN: "No data found for the selected date range.",
        Language.KR: "선택한 날짜 범위에 대한 데이터를 찾을 수 없습니다.",
        Language.TH: "ไม่พบข้อมูลในช่วงวันที่ที่เลือก",
    }

    # Task Status messages
    GET_TASK_STATUS_SUCCESS = {
        Language.EN: "Task status retrieved successfully.",
        Language.KR: "작업 상태를 성공적으로 조회했습니다.",
        Language.TH: "ตรวจสอบสถานะงานสำเร็จ",
    }
    GET_TASK_STATUS_FAILED = {
        Language.EN: "Failed to retrieve task status.",
        Language.KR: "작업 상태를 조회하지 못했습니다.",
        Language.TH: "ตรวจสอบสถานะงานไม่สำเร็จ",
    }

    # Handover Shift messages
    GET_LIST_HANDOVER_SHIFT_SUCCESS = {
        Language.EN: "Handover shifts fetched successfully",
        Language.KR: "인수인계 교대 근무 목록 조회 성공",
        Language.TH: "ดึงรายการกะการส่งมอบสำเร็จ",
    }
    CREATE_HANDOVER_SHIFT_SUCCESS = {
        Language.EN: "Handover shift created successfully",
        Language.KR: "인수인계 교대 근무 생성 성공",
        Language.TH: "สร้างกะการส่งมอบสำเร็จ",
    }
    CREATE_HANDOVER_SHIFT_FAILED = {
        Language.EN: "Handover shift creation failed",
        Language.KR: "인수인계 교대 근무 생성 실패",
        Language.TH: "สร้างกะการส่งมอบล้มเหลว",
    }
    UPDATE_HANDOVER_SHIFT_SUCCESS = {
        Language.EN: "Handover shift updated successfully",
        Language.KR: "인수인계 교대 근무 업데이트 성공",
        Language.TH: "อัปเดตกะการส่งมอบสำเร็จ",
    }
    UPDATE_HANDOVER_SHIFT_FAILED = {
        Language.EN: "Handover shift update failed",
        Language.KR: "인수인계 교대 근무 업데이트 실패",
        Language.TH: "อัปเดตกะการส่งมอบล้มเหลว",
    }
    DELETE_HANDOVER_SHIFT_SUCCESS = {
        Language.EN: "Handover shift deleted successfully",
        Language.KR: "인수인계 교대 근무 삭제 성공",
        Language.TH: "ลบกะการส่งมอบสำเร็จ",
    }
    CONFIG_HANDOVER_SHIFT_SUCCESS = {
        Language.EN: "Handover shifts configured successfully",
        Language.KR: "인수인계 교대 근무 설정 성공",
        Language.TH: "ตั้งค่ากะการส่งมอบสำเร็จ",
    }
    CONFIG_HANDOVER_SHIFT_FAILED = {
        Language.EN: "Handover shifts configuration failed",
        Language.KR: "인수인계 교대 근무 설정 실패",
        Language.TH: "ตั้งค่ากะการส่งมอบล้มเหลว",
    }

    # Handover Management/Document messages
    GET_LIST_HANDOVER_MANAGEMENT_SUCCESS = {
        Language.EN: "Handover management documents fetched successfully",
        Language.KR: "인수인계 관리 문서 목록 조회 성공",
        Language.TH: "ดึงรายการเอกสารการจัดการการส่งมอบสำเร็จ",
    }
    CREATE_HANDOVER_MANAGEMENT_SUCCESS = {
        Language.EN: "Handover management document created successfully",
        Language.KR: "인수인계 관리 문서 생성 성공",
        Language.TH: "สร้างเอกสารการจัดการการส่งมอบสำเร็จ",
    }
    CREATE_HANDOVER_MANAGEMENT_FAILED = {
        Language.EN: "Handover management document creation failed",
        Language.KR: "인수인계 관리 문서 생성 실패",
        Language.TH: "สร้างเอกสารการจัดการการส่งมอบล้มเหลว",
    }
    DELETE_HANDOVER_MANAGEMENT_SUCCESS = {
        Language.EN: "Shift log deletion is almost complete.",
        Language.KR: "교대 근무 로그 삭제가 거의 완료되었습니다.",
        Language.TH: "กำลังลบกะการส่งมอบสำเร็จ",
    }
    REMOVED_BLANK_JOURNALS = {
        Language.EN: "Removed blank journals.",
        Language.KR: "빈 일지를 삭제가 완료되었습니다.",
        Language.TH: "ลบวารสารว่างเปล่าสำเร็จ",
    }
    HANDOVER_DOCUMENT_WARNING = {
        Language.EN: "Shift log deletion is almost complete.",
        Language.KR: "교대 근무 로그 삭제가 거의 완료되었습니다.",
        Language.TH: "กำลังลบกะการส่งมอบสำเร็จ",
    }
    HANDOVER_DOCS_EXIST = {
        Language.EN: "Shift log already exists.",
        Language.KR: "교대근무 로그가 는 이미 존재합니",
        Language.TH: "บันทึกกะการส่งมอบมีอยู่แล้ว",
    }

    # Handover Content messages
    CREATE_HANDOVER_CONTENT_SUCCESS = {
        Language.EN: "Handover content created successfully",
        Language.KR: "인수인계 내용 생성 성공",
        Language.TH: "สร้างเนื้อหาการส่งมอบสำเร็จ",
    }
    CREATE_HANDOVER_CONTENT_FAILED = {
        Language.EN: "Handover content creation failed",
        Language.KR: "인수인계 내용 생성 실패",
        Language.TH: "สร้างเนื้อหาการส่งมอบล้มเหลว",
    }
    UPDATE_HANDOVER_CONTENT_SUCCESS = {
        Language.EN: "Handover content updated successfully",
        Language.KR: "인수인계 내용 업데이트 성공",
        Language.TH: "อัปเดตเนื้อหาการส่งมอบสำเร็จ",
    }
    UPDATE_HANDOVER_CONTENT_FAILED = {
        Language.EN: "Handover content update failed",
        Language.KR: "인수인계 내용 업데이트 실패",
        Language.TH: "อัปเดตเนื้อหาการส่งมอบล้มเหลว",
    }
    DELETE_HANDOVER_CONTENT_SUCCESS = {
        Language.EN: "Handover content deleted successfully",
        Language.KR: "인수인계 내용 삭제 성공",
        Language.TH: "ลบเนื้อหาการส่งมอบสำเร็จ",
    }
    GET_HANDOVER_CONTENT_SUCCESS = {
        Language.EN: "Handover content fetched successfully",
        Language.KR: "인수인계 내용 조회 성공",
        Language.TH: "ดึงเนื้อหาการส่งมอบสำเร็จ",
    }
    GET_HANDOVER_DUTY_DETAIL_SUCCESS = {
        Language.EN: "Handover duty details fetched successfully",
        Language.KR: "인수인계 근무 상세 조회 성공",
        Language.TH: "ดึงรายละเอียดหน้าที่การส่งมอบสำเร็จ",
    }
    BATCH_UPDATE_HANDOVER_CONTENT_SUCCESS = {
        Language.EN: "Handover contents updated successfully",
        Language.KR: "인수인계 내용 일괄 업데이트 성공",
        Language.TH: "อัปเดตเนื้อหาการส่งมอบหลายรายการสำเร็จ",
    }

    # Handover Notice messages
    GET_LIST_HANDOVER_NOTICE_SUCCESS = {
        Language.EN: "Handover notices fetched successfully",
        Language.KR: "인수인계 공지 목록 조회 성공",
        Language.TH: "ดึงรายการประกาศการส่งมอบสำเร็จ",
    }
    CREATE_HANDOVER_NOTICE_SUCCESS = {
        Language.EN: "Handover notice created successfully",
        Language.KR: "인수인계 공지 생성 성공",
        Language.TH: "สร้างประกาศการส่งมอบสำเร็จ",
    }
    CREATE_HANDOVER_NOTICE_FAILED = {
        Language.EN: "Handover notice creation failed",
        Language.KR: "인수인계 공지 생성 실패",
        Language.TH: "สร้างประกาศการส่งมอบล้มเหลว",
    }
    UPDATE_HANDOVER_NOTICE_SUCCESS = {
        Language.EN: "Handover notice updated successfully",
        Language.KR: "인수인계 공지 업데이트 성공",
        Language.TH: "อัปเดตประกาศการส่งมอบสำเร็จ",
    }
    UPDATE_HANDOVER_NOTICE_FAILED = {
        Language.EN: "Handover notice update failed",
        Language.KR: "인수인계 공지 업데이트 실패",
        Language.TH: "อัปเดตประกาศการส่งมอบล้มเหลว",
    }
    DELETE_HANDOVER_NOTICE_SUCCESS = {
        Language.EN: "Handover notice deleted successfully",
        Language.KR: "인수인계 공지 삭제 성공",
        Language.TH: "ลบประกาศการส่งมอบสำเร็จ",
    }
    GET_HANDOVER_NOTICE_DETAIL_SUCCESS = {
        Language.EN: "Handover notice detail fetched successfully",
        Language.KR: "인수인계 공지 상세 조회 성공",
        Language.TH: "ดึงรายละเอียดประกาศการส่งมอบสำเร็จ",
    }
    PROCESS_HANDOVER_NOTICE_SUCCESS = {
        Language.EN: "Handover notice processed successfully",
        Language.KR: "인수인계 공지 처리 성공",
        Language.TH: "ประมวลผลประกาศการส่งมอบสำเร็จ",
    }
    PROCESS_HANDOVER_NOTICE_FAILED = {
        Language.EN: "Handover notice processing failed",
        Language.KR: "인수인계 공지 처리 실패",
        Language.TH: "ประมวลผลประกาศการส่งมอบล้มเหลว",
    }
    RESTORE_HANDOVER_NOTICE_SUCCESS = {
        Language.EN: "Handover notice restored successfully",
        Language.KR: "인수인계 공지 복원 성공",
        Language.TH: "กู้คืนประกาศการส่งมอบสำเร็จ",
    }
    RESTORE_HANDOVER_NOTICE_FAILED = {
        Language.EN: "Handover notice restoration failed",
        Language.KR: "인수인계 공지 복원 실패",
        Language.TH: "กู้คืนประกาศการส่งมอบล้มเหลว",
    }
    HANDOVER_NOTICE_NOT_FOUND = {
        Language.EN: "Handover notice not found",
        Language.KR: "인수인계 공지를 찾을 수 없습니다",
        Language.TH: "ไม่พบประกาศการส่งมอบ",
    }

    # Handover Notice Comment messages
    GET_LIST_HANDOVER_NOTICE_COMMENT_SUCCESS = {
        Language.EN: "Handover notice comments fetched successfully",
        Language.KR: "인수인계 공지 댓글 목록 조회 성공",
        Language.TH: "ดึงรายการความคิดเห็นประกาศการส่งมอบสำเร็จ",
    }
    CREATE_HANDOVER_NOTICE_COMMENT_SUCCESS = {
        Language.EN: "Handover notice comment created successfully",
        Language.KR: "인수인계 공지 댓글 생성 성공",
        Language.TH: "สร้างความคิดเห็นประกาศการส่งมอบสำเร็จ",
    }
    CREATE_HANDOVER_NOTICE_COMMENT_FAILED = {
        Language.EN: "Handover notice comment creation failed",
        Language.KR: "인수인계 공지 댓글 생성 실패",
        Language.TH: "สร้างความคิดเห็นประกาศการส่งมอบล้มเหลว",
    }
    UPDATE_HANDOVER_NOTICE_COMMENT_SUCCESS = {
        Language.EN: "Handover notice comment updated successfully",
        Language.KR: "인수인계 공지 댓글 업데이트 성공",
        Language.TH: "อัปเดตความคิดเห็นประกาศการส่งมอบสำเร็จ",
    }
    UPDATE_HANDOVER_NOTICE_COMMENT_FAILED = {
        Language.EN: "Handover notice comment update failed",
        Language.KR: "인수인계 공지 댓글 업데이트 실패",
        Language.TH: "อัปเดตความคิดเห็นประกาศการส่งมอบล้มเหลว",
    }
    DELETE_HANDOVER_NOTICE_COMMENT_SUCCESS = {
        Language.EN: "Handover notice comment deleted successfully",
        Language.KR: "인수인계 공지 댓글 삭제 성공",
        Language.TH: "ลบความคิดเห็นประกาศการส่งมอบสำเร็จ",
    }

    # Handover Error messages
    HANDOVER_UNEXPECTED_ERROR = {
        Language.EN: "An unexpected error occurred while processing handover request",
        Language.KR: "인수인계 요청 처리 중 예상치 못한 오류가 발생했습니다",
        Language.TH: "เกิดข้อผิดพลาดที่ไม่คาดคิดขณะประมวลผลคำขอการส่งมอบ",
    }
    HANDOVER_NOT_FOUND = {
        Language.EN: "Handover not found",
        Language.KR: "인수인계를 찾을 수 없습니다",
        Language.TH: "ไม่พบการส่งมอบ",
    }
    DETECT_MEDIA_SUCCESS = {
        Language.EN: "Media detection completed successfully",
        Language.KR: "미디어 감지 완료",
        Language.TH: "การตรวจจับสื่อสำเร็จ",
    }
    DETECT_MEDIA_FAILED = {
        Language.EN: "Media detection failed",
        Language.KR: "미디어 감지 실패",
        Language.TH: "การตรวจจับสื่อล้มเหลว",
    }

    @classmethod
    def get(cls, message_enum, *args):
        """
        Get a translated message and format it with the provided arguments.

        Args:
            message_enum: The message enum constant
            *args: Arguments to format the message with

        Returns:
            str: The translated and formatted message
        """
        message = get_message(message_enum)
        if args:
            return message.format(*args)
        return message


# Survey Mission shortcuts
MESSAGE_SURVEY_MISSION_CREATED = MESSAGE_ENUM.MESSAGE_SURVEY_MISSION_CREATED
MESSAGE_SURVEY_MISSION_UPDATED = MESSAGE_ENUM.MESSAGE_SURVEY_MISSION_UPDATED
MESSAGE_SURVEY_MISSION_DELETED = MESSAGE_ENUM.MESSAGE_SURVEY_MISSION_DELETED
MESSAGE_SURVEY_MISSION_NOT_FOUND = MESSAGE_ENUM.MESSAGE_SURVEY_MISSION_NOT_FOUND
MESSAGE_OPERATION_FAILED = MESSAGE_ENUM.MESSAGE_OPERATION_FAILED
MARK_SURVEILLANCE_PROFILE_DRONE_FLIGHT_TIME_SUCCESS = MESSAGE_ENUM.MARK_SURVEILLANCE_PROFILE_DRONE_FLIGHT_TIME_SUCCESS
