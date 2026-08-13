import json
import logging
import os
import uuid
import requests
import time
from typing import Dict, Any, List, Tuple, Optional
from django.db import transaction
from django.core.files.uploadedfile import UploadedFile
from ninja.errors import ValidationError

from terminals.models import Terminal, Routes, RouteTerminal, TerminalType
from devices.utils import convert_unit
from devices.models import Measurement
from common.utils import get_waypoint_speed
from django.contrib.contenttypes.models import ContentType
from common.utils import get_gcs_api_headers

logger = logging.getLogger(__name__)


class QGroundControlService:
    """
    Service để xử lý import/export file .plan của QGroundControl
    Tuân thủ chính xác QGroundControl Plan File Format và MAVLink specification
    Hỗ trợ đầy đủ các field mission properties và command_line
    Hỗ trợ xử lý tham số hold từ MAV_CMD_NAV_WAYPOINT và chuyển đổi thành time_stops
    
    Logic xử lý tham số hold:
    - IMPORT: hold (giây) → time_stops (mins) - lưu vào database
    - EXPORT: time_stops (mins) → hold (giây) - xuất ra file plan
    """
    
    def __init__(self):
        """Khởi tạo cache cho command names và frame names"""
        self._command_names_cache = {}  # {command_id: command_name}
        self._frame_names_cache = {}    # {frame_id: frame_name}
        self._command_names_loaded = False
        self._frame_names_loaded = False
    
    # MAVLink Command Constants theo specification
    COMMAND_TAKEOFF = 22                    # MAV_CMD_NAV_TAKEOFF
    COMMAND_WAYPOINT = 16                   # MAV_CMD_NAV_WAYPOINT
    COMMAND_RTL = 20                        # MAV_CMD_NAV_RETURN_TO_LAUNCH
    COMMAND_LAND = 21                       # MAV_CMD_NAV_LAND
    COMMAND_JUMP = 177                      # MAV_CMD_DO_JUMP
    COMMAND_DO_CHANGE_SPEED = 178           # MAV_CMD_DO_CHANGE_SPEED
    COMMAND_DO_SET_SERVO = 183              # MAV_CMD_DO_SET_SERVO
    COMMAND_SET_CAMERA_MODE = 530           # MAV_CMD_SET_CAMERA_MODE
    
    # Additional MAVLink Commands từ docs
    COMMAND_DO_SET_PARAMETER = 180          # MAV_CMD_DO_SET_PARAMETER
    COMMAND_DO_SET_RELAY = 181              # MAV_CMD_DO_SET_RELAY
    COMMAND_DO_REPEAT_RELAY = 182           # MAV_CMD_DO_REPEAT_RELAY
    COMMAND_DO_REPEAT_SERVO = 184           # MAV_CMD_DO_REPEAT_SERVO
    COMMAND_DO_FLIGHTTERMINATION = 185      # MAV_CMD_DO_FLIGHTTERMINATION
    COMMAND_DO_CHANGE_ALTITUDE = 186        # MAV_CMD_DO_CHANGE_ALTITUDE
    COMMAND_DO_SET_ACTUATOR = 187           # MAV_CMD_DO_SET_ACTUATOR
    COMMAND_DO_LAND_START = 189             # MAV_CMD_DO_LAND_START
    COMMAND_DO_RALLY_LAND = 190             # MAV_CMD_DO_RALLY_LAND
    COMMAND_DO_GO_AROUND = 191              # MAV_CMD_DO_GO_AROUND
    COMMAND_DO_REPOSITION = 192             # MAV_CMD_DO_REPOSITION
    COMMAND_DO_PAUSE_CONTINUE = 193         # MAV_CMD_DO_PAUSE_CONTINUE
    COMMAND_DO_SET_REVERSE = 194            # MAV_CMD_DO_SET_REVERSE
    COMMAND_DO_SET_ROI_LOCATION = 195       # MAV_CMD_DO_SET_ROI_LOCATION
    COMMAND_DO_SET_ROI_WPNEXT_OFFSET = 196  # MAV_CMD_DO_SET_ROI_WPNEXT_OFFSET
    COMMAND_DO_SET_ROI_NONE = 197           # MAV_CMD_DO_SET_ROI_NONE
    COMMAND_DO_SET_ROI_SYSID = 198          # MAV_CMD_DO_SET_ROI_SYSID
    COMMAND_DO_CONTROL_VIDEO = 200          # MAV_CMD_DO_CONTROL_VIDEO
    COMMAND_DO_SET_ROI = 201                # MAV_CMD_DO_SET_ROI
    COMMAND_DO_DIGICAM_CONFIGURE = 202      # MAV_CMD_DO_DIGICAM_CONFIGURE
    COMMAND_DO_DIGICAM_CONTROL = 203        # MAV_CMD_DO_DIGICAM_CONTROL
    COMMAND_DO_MOUNT_CONFIGURE = 204        # MAV_CMD_DO_MOUNT_CONFIGURE
    COMMAND_DO_MOUNT_CONTROL = 205          # MAV_CMD_DO_MOUNT_CONTROL
    COMMAND_DO_SET_CAM_TRIGG_DIST = 206     # MAV_CMD_DO_SET_CAM_TRIGG_DIST
    COMMAND_DO_FENCE_ENABLE = 207           # MAV_CMD_DO_FENCE_ENABLE
    COMMAND_DO_PARACHUTE = 208              # MAV_CMD_DO_PARACHUTE
    COMMAND_DO_MOTOR_TEST = 209             # MAV_CMD_DO_MOTOR_TEST
    COMMAND_DO_INVERTED_FLIGHT = 210        # MAV_CMD_DO_INVERTED_FLIGHT
    COMMAND_DO_GRIPPER = 211                # MAV_CMD_DO_GRIPPER
    COMMAND_DO_AUTOTUNE_ENABLE = 212        # MAV_CMD_DO_AUTOTUNE_ENABLE
    COMMAND_NAV_SET_YAW_SPEED = 213         # MAV_CMD_NAV_SET_YAW_SPEED
    COMMAND_DO_SET_CAM_TRIGG_INTERVAL = 214 # MAV_CMD_DO_SET_CAM_TRIGG_INTERVAL
    COMMAND_DO_SET_MODE = 176               # MAV_CMD_DO_SET_MODE
    COMMAND_DO_SET_HOME = 179               # MAV_CMD_DO_SET_HOME
    COMMAND_NAV_LOITER_UNLIM = 17           # MAV_CMD_NAV_LOITER_UNLIM
    COMMAND_NAV_LOITER_TURNS = 18           # MAV_CMD_NAV_LOITER_TURNS
    COMMAND_NAV_LOITER_TIME = 19            # MAV_CMD_NAV_LOITER_TIME
    
    # MAVLink Frame Types theo specification
    FRAME_GLOBAL = 0  # MAV_FRAME_GLOBAL
    FRAME_GLOBAL_RELATIVE_ALT = 3  # MAV_FRAME_GLOBAL_RELATIVE_ALT
    
    # Altitude Modes theo QGroundControl
    ALTITUDE_MODE_RELATIVE = 0
    ALTITUDE_MODE_ABSOLUTE = 1
    
    # Đơn vị mặc định theo model
    TIME_STOPS_DEFAULT_UNIT = 'mins'  # Theo model Terminal.time_stops
    
    # Param Index theo MAVLink MISSION_ITEM specification
    # params[0-3]: param1, param2, param3, param4 (command-specific parameters)
    # params[4-6]: x, y, z (thường là latitude, longitude, altitude)
    PARAM_INDEX = {
        'PARAM1': 0,  # param1 - command-specific (với WAYPOINT: hold time in seconds)
        'PARAM2': 1,  # param2 - command-specific
        'PARAM3': 2,  # param3 - command-specific  
        'PARAM4': 3,  # param4 - command-specific
        'X': 4,       # x - latitude
        'Y': 5,       # y - longitude
        'Z': 6,       # z - altitude
    }
    
    # Command descriptions theo MAVLink specification
    COMMAND_DESCRIPTIONS = {
        COMMAND_TAKEOFF: "Takeoff",
        COMMAND_WAYPOINT: "Waypoint", 
        COMMAND_RTL: "Return to Launch",
        COMMAND_LAND: "Land",
        COMMAND_JUMP: "Do Jump",
        COMMAND_DO_CHANGE_SPEED: "Change Speed",
        COMMAND_DO_SET_SERVO: "Set Servo",
        COMMAND_SET_CAMERA_MODE: "Set Camera Mode",
        COMMAND_DO_SET_PARAMETER: "Set Parameter",
        COMMAND_DO_SET_RELAY: "Set Relay",
        COMMAND_DO_REPEAT_RELAY: "Repeat Relay",
        COMMAND_DO_REPEAT_SERVO: "Repeat Servo",
        COMMAND_DO_FLIGHTTERMINATION: "Flight Termination",
        COMMAND_DO_CHANGE_ALTITUDE: "Change Altitude",
        COMMAND_DO_SET_ACTUATOR: "Set Actuator",
        COMMAND_DO_LAND_START: "Land Start",
        COMMAND_DO_RALLY_LAND: "Rally Land",
        COMMAND_DO_GO_AROUND: "Go Around",
        COMMAND_DO_REPOSITION: "Reposition",
        COMMAND_DO_PAUSE_CONTINUE: "Pause Continue",
        COMMAND_DO_SET_REVERSE: "Set Reverse",
        COMMAND_DO_SET_ROI_LOCATION: "Set ROI Location",
        COMMAND_DO_SET_ROI_WPNEXT_OFFSET: "Set ROI WP Next Offset",
        COMMAND_DO_SET_ROI_NONE: "Set ROI None",
        COMMAND_DO_SET_ROI_SYSID: "Set ROI System ID",
        COMMAND_DO_CONTROL_VIDEO: "Control Video",
        COMMAND_DO_SET_ROI: "Set ROI",
        COMMAND_DO_DIGICAM_CONFIGURE: "DigiCam Configure",
        COMMAND_DO_DIGICAM_CONTROL: "DigiCam Control",
        COMMAND_DO_MOUNT_CONFIGURE: "Mount Configure",
        COMMAND_DO_MOUNT_CONTROL: "Mount Control",
        COMMAND_DO_SET_CAM_TRIGG_DIST: "Set Camera Trigger Distance",
        COMMAND_DO_FENCE_ENABLE: "Fence Enable",
        COMMAND_DO_PARACHUTE: "Parachute",
        COMMAND_DO_MOTOR_TEST: "Motor Test",
        COMMAND_DO_INVERTED_FLIGHT: "Inverted Flight",
        COMMAND_DO_GRIPPER: "Gripper",
        COMMAND_DO_AUTOTUNE_ENABLE: "Autotune Enable",
        COMMAND_NAV_SET_YAW_SPEED: "Set Yaw Speed",
        COMMAND_DO_SET_CAM_TRIGG_INTERVAL: "Set Camera Trigger Interval",
        COMMAND_DO_SET_MODE: "Set Mode",
        COMMAND_DO_SET_HOME: "Set Home",
        COMMAND_NAV_LOITER_UNLIM: "Loiter Unlimited",
        COMMAND_NAV_LOITER_TURNS: "Loiter Turns",
        COMMAND_NAV_LOITER_TIME: "Loiter Time",
    }
    
    def __init__(self):
        self.temp_terminal_type = None
        self._mavlink_frames_cache = None
        self._mavlink_frames_cache_timestamp = None
        self._cache_duration = 300  # Cache 5 phút
        # Cache cho command names và frame names (tối ưu import)
        self._command_names_cache = {}  # {command_id: command_name}
        self._frame_names_cache = {}    # {frame_id: frame_name}
        self._command_names_loaded = False
        self._frame_names_loaded = False
    
    def _get_mavlink_frames_from_api(self) -> Optional[Dict]:
        """
        Lấy danh sách MAVLink frames từ API
        
        Returns:
            Dict chứa frames data hoặc None nếu lỗi
        """
        try:
            # Kiểm tra cache
            if self._mavlink_frames_cache and self._mavlink_frames_cache_timestamp:
                from time import time
                if time() - self._mavlink_frames_cache_timestamp < self._cache_duration:
                    logger.debug("Sử dụng cached MAVLink frames")
                    return self._mavlink_frames_cache
            
            # Gọi API mavlink-frames
            base_url = os.getenv('FLIGHTBRID_URL')
            api_url = f"{base_url}/api/drone/mavlink-frames?isFull=true"
            
            headers = get_gcs_api_headers()
            response = requests.get(api_url, headers=headers, timeout=10)
            if response.status_code == 200:
                data = response.json()
                print(f"DEBUG: data: {data}")
                # Xử lý response theo cấu trúc thực tế
                if data.get('frames') :
                    # Cache data
                    self._mavlink_frames_cache = data.get('frames')
                    from time import time
                    self._mavlink_frames_cache_timestamp = time()
                    return data.get('frames')
                else:
                    logger.warning("API response không có data hợp lệ")
                    return None
            else:
                logger.warning(f"API mavlink-frames trả về status {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Lỗi khi gọi API mavlink-frames: {e}")
            return None
    
    def _load_frame_names_cache(self) -> None:
        """Load tất cả frame names từ API một lần và cache lại (sử dụng cache có sẵn)"""
        if self._frame_names_loaded:
            return
        
        try:
            # Sử dụng hàm _get_mavlink_frames_from_api() đã có cache sẵn
            frames_data = self._get_mavlink_frames_from_api()
            
            if frames_data:
                for frame in frames_data:
                    frame_id = frame.get('FrameId')
                    frame_name = frame.get('FrameName')
                    if frame_id is not None and frame_name:
                        self._frame_names_cache[int(frame_id)] = frame_name
                self._frame_names_loaded = True
                logger.info(f"Đã load {len(self._frame_names_cache)} frame names vào cache")
        except Exception as e:
            logger.warning(f"Không thể load frame names từ API: {e}, sẽ dùng fallback khi cần")
    
    def _get_frame_name_by_id(self, frame_id: int) -> str:
        """
        Lấy tên frame từ cache (đã được load trước), fallback về FRAME_{frame_id} nếu không có
        
        Args:
            frame_id: Frame ID cần tìm
            
        Returns:
            Tên frame hoặc f"FRAME_{frame_id}" nếu không tìm thấy
        """
        # Sử dụng cache thay vì gọi API mỗi lần
        if frame_id in self._frame_names_cache:
            return self._frame_names_cache[frame_id]
        
        # Fallback nếu không tìm thấy trong cache
        logger.debug(f"Frame {frame_id} không có trong cache, sử dụng fallback")
        return f"FRAME_{frame_id}"
    
    def _get_frame_id_by_name(self, frame_name: str) -> Optional[int]:
        """
        Lấy frame ID từ tên frame sử dụng API
        
        Args:
            frame_name: Tên frame cần tìm
            
        Returns:
            Frame ID hoặc None nếu không tìm thấy
        """
        try:
            frames_data = self._get_mavlink_frames_from_api()
            if frames_data:
                for frame in frames_data:
                    # Xử lý cả hai format có thể có
                    frame_name_from_api = frame.get('FrameName') or frame.get('frame_name')
                    if frame_name_from_api == frame_name:
                        frame_id = frame.get('FrameId') or frame.get('id_frame')
                        if frame_id is not None:
                            logger.debug(f"Tìm thấy frame {frame_name}: {frame_id}")
                            return int(frame_id)
            
            logger.debug(f"Không tìm thấy frame {frame_name} trong API")
            return None
            
        except Exception as e:
            logger.error(f"Lỗi khi lấy frame ID cho name {frame_name}: {e}")
            return None
    
    def _get_frame_from_mission_item(self, mission_item: Dict[str, Any]) -> Dict[str, str]:
        """
        Lấy frame từ mission item khi import
        
        Args:
            mission_item: Mission item từ file plan
            
        Returns:
            Dict với format {"id": "name"} hoặc {"0": "global"} nếu không có
        """
        try:
            frame = mission_item.get('frame')
            if frame is not None:
                frame_id = int(frame)
                if frame_id >= 0:
                    # Sử dụng API để lấy tên frame
                    frame_name = self._get_frame_name_by_id(frame_id)
                    return {str(frame_id): frame_name}
                else:
                    logger.warning(f"Frame ID không hợp lệ: {frame_id}, sử dụng default")
                    return {"0": "global"}
            else:
                #print("Mission item không có frame, sử dụng default MAV_FRAME_GLOBAL (0)")
                return {"0": "global"}
        except (ValueError, TypeError) as e:
            logger.warning(f"Error parsing frame từ mission item: {e}, sử dụng default")
            return {"0": "global"}
    
    @transaction.atomic
    def import_plan_file(self, plan_file: UploadedFile, plan_file_name: str, service_id: int | None = None) -> Tuple[bool, Any]:
        """
        Import file .plan và tạo terminals TEMP + route
        Toàn bộ quá trình được bọc trong một transaction để đảm bảo atomicity:
        - Nếu có bất kỳ lỗi nào xảy ra, tất cả thay đổi sẽ được rollback
        - Chỉ commit khi tất cả các bước thành công
        - Nếu exception được raise, Django sẽ tự động rollback transaction
        
        Args:
            plan_file: File .plan được upload
            
        Returns:
            Tuple (success, result) với result là route được tạo hoặc error message
            
        Raises:
            ValidationError: Nếu có lỗi validation hoặc lỗi trong quá trình import
            Exception: Bất kỳ exception nào khác sẽ được propagate để rollback transaction
        """
        start_time = time.perf_counter()
        print(f"\n{'='*60}")
        print(f"🚀 BẮT ĐẦU IMPORT FILE .PLAN")
        print(f"{'='*60}")
        print(f"📁 File: {plan_file.name if hasattr(plan_file, 'name') else 'Unknown'}")
        print(f"📏 Size: {plan_file.size / 1024:.2f} KB" if hasattr(plan_file, 'size') else "")
        
        # Parse file .plan
        parse_start = time.perf_counter()
        plan_data = self._parse_plan_file(plan_file)
        parse_time = time.perf_counter() - parse_start
        print(f"⏱️  Parse file: {parse_time:.3f}s")
        
        # Validate dữ liệu
        validate_start = time.perf_counter()
        self._validate_plan_data(plan_data)
        validate_time = time.perf_counter() - validate_start
        print(f"⏱️  Validate data: {validate_time:.3f}s")
        
        mission_items = plan_data.get('mission', {}).get('items', [])
        print(f"📊 Số lượng mission items: {len(mission_items)}")
        
        # Tối ưu: Load tất cả command names và frame names một lần và cache
        cache_start = time.perf_counter()
        self._load_command_names_cache()
        self._load_frame_names_cache()
        cache_time = time.perf_counter() - cache_start
        print(f"⏱️  Load cache (commands & frames): {cache_time:.3f}s")
        
        # Tạo terminals từ mission items
        # Nếu có lỗi, exception sẽ được raise và transaction sẽ rollback
        terminals_start = time.perf_counter()
        terminal_mission_pairs = self._create_terminals_from_mission(mission_items)
        terminals_time = time.perf_counter() - terminals_start
        print(f"⏱️  Tạo terminals ({len(terminal_mission_pairs)} terminals): {terminals_time:.3f}s")
        
        # Tạo route từ terminals
        # Nếu có lỗi, exception sẽ được raise và transaction sẽ rollback
        route_start = time.perf_counter()
        route = self._create_route_from_terminals(terminal_mission_pairs, plan_data, plan_file_name, service_id)
        route_time = time.perf_counter() - route_start
        print(f"⏱️  Tạo route và route terminals: {route_time:.3f}s")
        
        total_time = time.perf_counter() - start_time
        print(f"\n{'='*60}")
        print(f"✅ HOÀN THÀNH IMPORT FILE")
        print(f"{'='*60}")
        print(f"⏱️  Tổng thời gian: {total_time:.3f}s ({total_time/60:.2f} phút)")
        print(f"📈 Tốc độ: {len(terminal_mission_pairs)/total_time:.2f} terminals/giây")
        print(f"{'='*60}\n")
        
        # Nếu đến đây mà không có exception, transaction sẽ được commit tự động
        return True, route
    
    def _parse_plan_file(self, plan_file: UploadedFile) -> Dict[str, Any]:
        """Parse file .plan JSON"""
        try:
            content = plan_file.read().decode('utf-8')
            return json.loads(content)
        except json.JSONDecodeError:
            raise ValidationError("File .plan không phải là JSON hợp lệ")
        except UnicodeDecodeError:
            raise ValidationError("File .plan không thể decode UTF-8")
    
    def _validate_plan_data(self, plan_data: Dict[str, Any]) -> None:
        """Validate cấu trúc dữ liệu .plan"""
        if not isinstance(plan_data, dict):
            raise ValidationError("Dữ liệu .plan phải là object")
        
        if plan_data.get('fileType') != 'Plan':
            raise ValidationError("FileType phải là 'Plan'")
        
        mission = plan_data.get('mission')
        if not mission:
            raise ValidationError("Thiếu thông tin mission")
        
        items = mission.get('items')
        if not items or not isinstance(items, list):
            raise ValidationError("Mission phải có items array")
    
    @transaction.atomic
    def _create_terminals_from_mission(self, mission_items: List[Dict]) -> List[Tuple[Terminal, Dict]]:
        """
        Tạo terminals từ mission items, giữ nguyên thứ tự gốc (tối ưu với bulk_create)
        
        Mỗi command sẽ tạo 1 terminal TEMP để hiển thị đủ data:
        - Commands có coordinates: tạo terminal với lat/long từ params
        - Commands không có coordinates: tạo terminal với lat/long từ command trước đó
        """
        # Sắp xếp mission items theo doJumpId để giữ thứ tự gốc
        sorted_items = sorted(mission_items, key=lambda x: x.get('doJumpId', 0))
        
        # Lấy TEMP terminal type một lần
        try:
            temp_type = TerminalType.objects.get(code='TEMP')
        except TerminalType.DoesNotExist:
            error_msg = "TerminalType TEMP không tồn tại trong hệ thống"
            logger.error(error_msg)
            raise ValidationError(error_msg)  # Raise để rollback transaction
        
        # Chuẩn bị dữ liệu cho bulk create
        terminals_to_create = []
        terminal_mission_pairs_data = []  # Lưu (terminal_data, mission_item) để xử lý sau
        last_coordinates = None
        first_coordinates = None
        
        for idx, item in enumerate(sorted_items):
            command = item.get('command')
            
            try:
                terminal_data = None
                
                # Tạo terminal cho TẤT CẢ commands (có coordinates hoặc không)
                # Lưu ý: chỉ override logic LAT/LONG khi import terminals.
                # KHÔNG thay đổi params của mission item.
                if self._is_coordinate_command(command, item.get('params', [])) and command != self.COMMAND_RTL:
                    # Command có coordinates - chuẩn bị terminal data
                    terminal_data = self._prepare_terminal_data_from_mission_item(item)
                    if terminal_data:
                        # Cập nhật last_coordinates cho commands tiếp theo
                        last_coordinates = {
                            'latitude': terminal_data['latitude'],
                            'longitude': terminal_data['longitude']
                        }
                        # Lưu lại tọa độ điểm đầu tiên trong route (waypoint/coordinate đầu tiên)
                        if first_coordinates is None:
                            first_coordinates = dict(last_coordinates)
                else:
                    # Command KHÔNG có coordinates - chuẩn bị terminal data với coordinates từ command trước
                    coords_for_non_coordinate = last_coordinates
                    
                    # Nếu route cuối của file là RTL thì lat/long của điểm đó = điểm đầu tiên trong route
                    # Các command action khác vẫn giữ lat/long theo waypoint trước đó như cũ
                    is_last_item = idx == (len(sorted_items) - 1)
                    if is_last_item and command == self.COMMAND_RTL and first_coordinates:
                        coords_for_non_coordinate = first_coordinates
                    
                    terminal_data = self._prepare_terminal_data_for_non_coordinate_command(item, coords_for_non_coordinate)
                
                if terminal_data:
                    terminals_to_create.append(terminal_data)
                    terminal_mission_pairs_data.append((terminal_data, item))
                        
            except Exception as e:
                logger.warning(f"Error preparing terminal from mission item {command}: {e}")
                continue
        
        if not terminals_to_create:
            raise ValidationError("Không có terminal nào được tạo từ mission items")  # Raise để rollback transaction
        
        # Chia nhỏ thành các batch để tránh connection pool overflow
        BATCH_SIZE = 50
        created_terminals = []
        terminal_mission_pairs = []
        total_batches = (len(terminals_to_create) + BATCH_SIZE - 1) // BATCH_SIZE
        
        print(f"  📦 Chia thành {total_batches} batch(es), mỗi batch {BATCH_SIZE} terminals")
        
        batch_start_time = time.perf_counter()
        
        # Bulk create terminals theo batch
        for batch_num, i in enumerate(range(0, len(terminals_to_create), BATCH_SIZE), 1):
            batch_start = time.perf_counter()
            batch_data = terminals_to_create[i:i + BATCH_SIZE]
            batch_mission_data = terminal_mission_pairs_data[i:i + BATCH_SIZE]
            
            # Bulk create batch terminals
            create_start = time.perf_counter()
            batch_terminals = Terminal.objects.bulk_create(
                [Terminal(**data) for data in batch_data],
                batch_size=BATCH_SIZE
            )
            create_time = time.perf_counter() - create_start
            created_terminals.extend(batch_terminals)
            
            # Bulk create ManyToMany relationships cho batch này
            m2m_start = time.perf_counter()
            TerminalTerminalTypes = Terminal.terminal_types.through
            m2m_relationships = [
                TerminalTerminalTypes(terminal=terminal, terminaltype=temp_type)
                for terminal in batch_terminals
            ]
            TerminalTerminalTypes.objects.bulk_create(m2m_relationships, batch_size=BATCH_SIZE)
            m2m_time = time.perf_counter() - m2m_start
            
            # Xử lý measurements và các thao tác khác cho batch này
            measurements_start = time.perf_counter()
            for terminal, (terminal_data, mission_item) in zip(batch_terminals, batch_mission_data):
                try:
                    # Xử lý hold parameter nếu cần
                    self._process_hold_parameter_for_terminal(terminal, mission_item)
                    
                    # Xử lý command parameters measurements cho non-coordinate commands
                    command = mission_item.get('command')
                    if not self._is_coordinate_command(command, mission_item.get('params', [])):
                        self._create_command_parameters_measurements(terminal, mission_item)
                    
                    terminal_mission_pairs.append((terminal, mission_item))
                except Exception as e:
                    logger.warning(f"Error processing terminal {terminal.id} from mission item: {e}")
                    continue
            measurements_time = time.perf_counter() - measurements_start
            
            batch_time = time.perf_counter() - batch_start
            print(f"    Batch {batch_num}/{total_batches}: {len(batch_terminals)} terminals - "
                  f"Create: {create_time:.3f}s, M2M: {m2m_time:.3f}s, Measurements: {measurements_time:.3f}s, "
                  f"Total: {batch_time:.3f}s")
        
        total_batch_time = time.perf_counter() - batch_start_time
        print(f"  ⏱️  Tổng thời gian tạo terminals: {total_batch_time:.3f}s")
        
        return terminal_mission_pairs

    def _is_coordinate_command(self, command: int, params: List[Any] = None) -> bool:
        """
        Kiểm tra command có chứa coordinates không theo MAVLink spec
        
        Commands có coordinates (params[4-6] = lat, lon, alt):
        - Navigation commands (MAV_CMD_NAV_*)
        - Location-specific commands (DO_SET_ROI_LOCATION, DO_REPOSITION)
        
        Commands không có coordinates:
        - Action commands (MAV_CMD_DO_*) trừ một số exceptions
        - Control commands 
        """
        # Navigation commands luôn có coordinates
        nav_commands = [
            self.COMMAND_TAKEOFF,           # 22
            self.COMMAND_WAYPOINT,          # 16
            self.COMMAND_LAND,              # 21
            self.COMMAND_RTL,               # 20
            self.COMMAND_NAV_LOITER_UNLIM,  # 17
            self.COMMAND_NAV_LOITER_TURNS,  # 18
            self.COMMAND_NAV_LOITER_TIME,   # 19
            self.COMMAND_NAV_SET_YAW_SPEED, # 213
        ]
        
        # DO commands có coordinates (exceptions)
        do_commands_with_coordinates = [
            self.COMMAND_DO_SET_ROI_LOCATION,    # 195
            self.COMMAND_DO_REPOSITION,          # 192
            self.COMMAND_DO_SET_HOME,            # 179
        ]
        
        # DO commands không có coordinates
        do_commands_without_coordinates = [
            self.COMMAND_DO_SET_SERVO,           # 183
            self.COMMAND_DO_CHANGE_SPEED,        # 178
            self.COMMAND_SET_CAMERA_MODE,        # 530
            self.COMMAND_DO_SET_PARAMETER,       # 180
            self.COMMAND_DO_SET_RELAY,           # 181
            self.COMMAND_DO_REPEAT_RELAY,        # 182
            self.COMMAND_DO_REPEAT_SERVO,        # 184
            self.COMMAND_DO_FLIGHTTERMINATION,   # 185
            self.COMMAND_DO_CHANGE_ALTITUDE,     # 186
            self.COMMAND_DO_SET_ACTUATOR,        # 187
            self.COMMAND_DO_LAND_START,          # 189
            self.COMMAND_DO_RALLY_LAND,          # 190
            self.COMMAND_DO_GO_AROUND,           # 191
            self.COMMAND_DO_PAUSE_CONTINUE,      # 193
            self.COMMAND_DO_SET_REVERSE,         # 194
            self.COMMAND_DO_SET_ROI_WPNEXT_OFFSET, # 196
            self.COMMAND_DO_SET_ROI_NONE,        # 197
            self.COMMAND_DO_SET_ROI_SYSID,       # 198
            self.COMMAND_DO_CONTROL_VIDEO,       # 200
            self.COMMAND_DO_SET_ROI,             # 201
            self.COMMAND_DO_DIGICAM_CONFIGURE,   # 202
            self.COMMAND_DO_DIGICAM_CONTROL,     # 203
            self.COMMAND_DO_MOUNT_CONFIGURE,     # 204
            self.COMMAND_DO_MOUNT_CONTROL,       # 205
            self.COMMAND_DO_SET_CAM_TRIGG_DIST,  # 206
            self.COMMAND_DO_FENCE_ENABLE,        # 207
            self.COMMAND_DO_PARACHUTE,           # 208
            self.COMMAND_DO_MOTOR_TEST,          # 209
            self.COMMAND_DO_INVERTED_FLIGHT,     # 210
            self.COMMAND_DO_GRIPPER,             # 211
            self.COMMAND_DO_AUTOTUNE_ENABLE,     # 212
            self.COMMAND_DO_SET_CAM_TRIGG_INTERVAL, # 214
            self.COMMAND_DO_SET_MODE,            # 176
            self.COMMAND_JUMP,                   # 177
        ]
        
        # Check theo thứ tự ưu tiên
        if command in nav_commands:
            return True
        elif command in do_commands_with_coordinates:
            return True
        elif command in do_commands_without_coordinates:
            return False
        else:
            # Default: unknown commands assumed to have coordinates
            logger.warning(f"Unknown command {command}, assuming has coordinates")
            return True
    
    def _get_mission_item_name(self, mission_item: Dict[str, Any]) -> str:
        """Lấy tên cho mission item dựa trên command"""
        command = mission_item.get('command')
        
        # Kiểm tra nếu là mission start (thường là item đầu tiên hoặc có command đặc biệt)
        if command == 0:  # START command
            return 'Waypoint'
        elif command == 22:  # MAV_CMD_NAV_TAKEOFF
            return 'Takeoff'
        elif command == 20:  # MAV_CMD_NAV_RETURN_TO_LAUNCH
            return 'Return To Launch'
        elif command == 21:  # MAV_CMD_NAV_LAND
            return 'Land'
        elif command == 181:  # MAV_CMD_DO_SET_RELAY
            return 'Set relay'
        elif command == 182:  # MAV_CMD_DO_REPEAT_RELAY
            return 'Cycle relay'
        elif command == 183:  # MAV_CMD_DO_SET_SERVO
            return 'Set Servo'
        elif command == 203:  # MAV_CMD_DO_DIGICAM_CONTROL
            return 'Camera Trigger'
        elif command == 2000:  # MAV_CMD_IMAGE_START_CAPTURE
            return 'Start Image Capture'
        elif command == 208:  # MAV_CMD_DO_PARACHUTE
            return 'Trigger parachute'
        elif command == 211:  # MAV_CMD_DO_GRIPPER
            return 'Gripper Mechanism'
        else:
            return 'Waypoint'

    def _prepare_terminal_data_from_mission_item(self, mission_item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Chuẩn bị dữ liệu terminal từ mission item (có coordinates) để dùng cho bulk_create
        Returns dict với các field cần thiết để tạo Terminal
        """
        try:
            # Lấy coordinates từ params
            coordinates = self._extract_coordinates_from_params(mission_item.get('params', []))
            
            if not coordinates:
                return None
            
            # Validate coordinates
            if not self._validate_coordinates(coordinates):
                return None
            
            # Lấy tên dựa trên command
            item_name = self._get_mission_item_name(mission_item)
            
            return {
                'name': item_name,
                'latitude': coordinates['latitude'],
                'longitude': coordinates['longitude'],
            }
            
        except Exception as e:
            logger.warning(f"Error preparing terminal data from mission item: {e}")
            return None

    def _prepare_terminal_data_for_non_coordinate_command(self, mission_item: Dict[str, Any], last_coordinates: Optional[Dict[str, float]]) -> Optional[Dict[str, Any]]:
        """
        Chuẩn bị dữ liệu terminal cho commands không có coordinates để dùng cho bulk_create
        
        Args:
            mission_item: Mission item của command không có coordinates
            last_coordinates: Coordinates từ command trước đó {'latitude': float, 'longitude': float}
            
        Returns:
            dict với các field cần thiết để tạo Terminal hoặc None nếu lỗi
        """
        try:
            command = mission_item.get('command')
            command_name = self.COMMAND_DESCRIPTIONS.get(command, f"Command_{command}")
            
            # Sử dụng coordinates từ command trước đó
            if last_coordinates:
                latitude = last_coordinates['latitude']
                longitude = last_coordinates['longitude']
            else:
                # Fallback: sử dụng coordinates mặc định nếu không có command trước đó
                logger.warning(f"Không có coordinates từ command trước đó cho {command_name}, sử dụng default")
                latitude = 0.0
                longitude = 0.0
            
            # Tạo tên terminal mô tả command
            terminal_name = f"{command_name}"
            
            return {
                'name': terminal_name,
                'latitude': latitude,
                'longitude': longitude,
            }
            
        except Exception as e:
            logger.error(f"Error preparing terminal data for non-coordinate command {mission_item.get('command')}: {e}")
            return None

    def _create_terminal_from_mission_item(self, mission_item: Dict[str, Any]) -> Terminal:
        """Tạo Terminal từ mission item với đầy đủ properties"""
        try:
            # Lấy coordinates từ params
            coordinates = self._extract_coordinates_from_params(mission_item.get('params', []))
            
            if not coordinates:
                return None
            
            # Validate coordinates
            if not self._validate_coordinates(coordinates):
                return None
            
            # Lấy tên dựa trên command
            item_name = self._get_mission_item_name(mission_item)
            
            # Tạo terminal với các field hợp lệ
            terminal = Terminal.objects.create(
                name=item_name,
                latitude=coordinates['latitude'],
                longitude=coordinates['longitude'],
                # Bỏ field altitude vì Terminal model không có
                # Bỏ field terminal_type vì sẽ set qua ManyToMany sau
            )
            
            # Set terminal type TEMP qua ManyToMany
            temp_type = TerminalType.objects.get(code='TEMP')
            terminal.terminal_types.add(temp_type)
            
            # Xử lý tham số hold từ MAV_CMD_NAV_WAYPOINT và chuyển đổi thành time_stops
            self._process_hold_parameter_for_terminal(terminal, mission_item)
            
            return terminal
            
        except Exception as e:
            #print(f"Error creating terminal from mission item: {e}")
            return None
    
    def _create_terminal_for_non_coordinate_command(self, mission_item: Dict[str, Any], last_coordinates: Optional[Dict[str, float]]) -> Optional[Terminal]:
        """
        Tạo Terminal cho commands không có coordinates, sử dụng coordinates từ command trước đó
        
        Args:
            mission_item: Mission item của command không có coordinates
            last_coordinates: Coordinates từ command trước đó {'latitude': float, 'longitude': float}
            
        Returns:
            Terminal object hoặc None nếu lỗi
        """
        try:
            command = mission_item.get('command')
            command_name = self.COMMAND_DESCRIPTIONS.get(command, f"Command_{command}")
            
            # Sử dụng coordinates từ command trước đó
            if last_coordinates:
                latitude = last_coordinates['latitude']
                longitude = last_coordinates['longitude']
            else:
                # Fallback: sử dụng coordinates mặc định nếu không có command trước đó
                logger.warning(f"Không có coordinates từ command trước đó cho {command_name}, sử dụng default")
                latitude = 0.0
                longitude = 0.0
            
            # Tạo tên terminal mô tả command
            terminal_name = f"{command_name}"
            
            # Tạo terminal với coordinates kế thừa
            terminal = Terminal.objects.create(
                name=terminal_name,
                latitude=latitude,
                longitude=longitude,
            )
            
            # Set terminal type TEMP qua ManyToMany
            temp_type = TerminalType.objects.get(code='TEMP')
            terminal.terminal_types.add(temp_type)
            
            # Lưu thông tin command vào terminal description hoặc custom field
            terminal.description = f"MAVLink Command: {command_name} (ID: {command})"
            terminal.save()
            
            # Tạo measurements cho parameters của command để hiển thị đủ data
            self._create_command_parameters_measurements(terminal, mission_item)
            
            logger.info(f"Tạo thành công terminal cho {command_name} với coordinates kế thừa: ({latitude}, {longitude})")
            
            return terminal
            
        except Exception as e:
            logger.error(f"Error creating terminal for non-coordinate command {mission_item.get('command')}: {e}")
            return None
    
    def _create_command_parameters_measurements(self, terminal: Terminal, mission_item: Dict[str, Any]) -> None:
        """
        Tạo measurements cho parameters của command để hiển thị đủ data trên terminal
        
        Args:
            terminal: Terminal object đã được tạo
            mission_item: Mission item chứa command và parameters
        """
        try:
            command = mission_item.get('command')
            params = mission_item.get('params', [])
            
            # Xử lý parameters theo từng command cụ thể
            if command == self.COMMAND_DO_SET_SERVO:
                self._create_servo_measurements(terminal, params)
            elif command == self.COMMAND_DO_CHANGE_SPEED:
                self._create_speed_measurements(terminal, params)
            elif command == self.COMMAND_SET_CAMERA_MODE:
                self._create_camera_measurements(terminal, params)
            elif command == self.COMMAND_DO_SET_RELAY:
                self._create_relay_measurements(terminal, params)
            elif command == self.COMMAND_DO_SET_PARAMETER:
                self._create_parameter_measurements(terminal, params)
            elif command == self.COMMAND_DO_MOUNT_CONTROL:
                self._create_mount_control_measurements(terminal, params)
            elif command == self.COMMAND_DO_DIGICAM_CONTROL:
                self._create_digicam_measurements(terminal, params)
            elif command == self.COMMAND_DO_SET_CAM_TRIGG_DIST:
                self._create_camera_trigger_measurements(terminal, params)
            else:
                # Tạo generic measurements cho các commands khác
                self._create_generic_command_measurements(terminal, params, command)
                
        except Exception as e:
            logger.error(f"Error creating command parameters measurements for command {command}: {e}")
    
    def _create_servo_measurements(self, terminal: Terminal, params: List) -> None:
        """Tạo measurements cho MAV_CMD_DO_SET_SERVO command"""
        try:
            if len(params) >= 2:
                # param1: Servo number (1-8 for ArduPilot, 1-16 for PX4)
                servo_number = self._safe_get_param(params, 0)
                if servo_number is not None:
                    terminal.set_measurement('servo_number', f"{int(servo_number)}")
                
                # param2: PWM value (1000-2000 microseconds)
                pwm_value = self._safe_get_param(params, 1)
                if pwm_value is not None:
                    terminal.set_measurement('servo_pwm', f"{int(pwm_value)} microseconds")
                    
                logger.info(f"Tạo servo measurements: servo_{int(servo_number or 0)}, PWM={int(pwm_value or 0)}")
        except Exception as e:
            logger.warning(f"Error creating servo measurements: {e}")
    
    def _create_speed_measurements(self, terminal: Terminal, params: List) -> None:
        """Tạo measurements cho MAV_CMD_DO_CHANGE_SPEED command"""
        try:
            if len(params) >= 2:
                # param1: Speed type (0=Airspeed, 1=Ground Speed, 2=Climb Speed, 3=Descent Speed)
                speed_type = self._safe_get_param(params, 0)
                if speed_type is not None:
                    speed_type_names = {0: "Airspeed", 1: "Ground Speed", 2: "Climb Speed", 3: "Descent Speed"}
                    terminal.set_measurement('speed_type', speed_type_names.get(int(speed_type), f"Type_{int(speed_type)}"))
                
                # param2: Speed value (m/s)
                speed_value = self._safe_get_param(params, 1)
                if speed_value is not None:
                    terminal.set_measurement('speed_value', f"{speed_value} m/s")
                    
                logger.info(f"Tạo speed measurements: type={int(speed_type or 0)}, value={speed_value}")
        except Exception as e:
            logger.warning(f"Error creating speed measurements: {e}")
    
    def _create_camera_measurements(self, terminal: Terminal, params: List) -> None:
        """Tạo measurements cho MAV_CMD_SET_CAMERA_MODE command"""
        try:
            if len(params) >= 1:
                # param1: Camera mode (0=Image, 1=Video, 2=Image Survey)
                camera_mode = self._safe_get_param(params, 0)
                if camera_mode is not None:
                    mode_names = {0: "Image", 1: "Video", 2: "Image Survey"}
                    terminal.set_measurement('camera_mode', mode_names.get(int(camera_mode), f"Mode_{int(camera_mode)}"))
                    
                logger.info(f"Tạo camera measurements: mode={int(camera_mode or 0)}")
        except Exception as e:
            logger.warning(f"Error creating camera measurements: {e}")
    
    def _create_relay_measurements(self, terminal: Terminal, params: List) -> None:
        """Tạo measurements cho MAV_CMD_DO_SET_RELAY command"""
        try:
            if len(params) >= 2:
                # param1: Relay number
                relay_number = self._safe_get_param(params, 0)
                if relay_number is not None:
                    terminal.set_measurement('relay_number', f"{int(relay_number)}")
                
                # param2: Setting (0=Off, 1=On)
                relay_setting = self._safe_get_param(params, 1)
                if relay_setting is not None:
                    setting_name = "On" if int(relay_setting) == 1 else "Off"
                    terminal.set_measurement('relay_setting', setting_name)
                    
                logger.info(f"Tạo relay measurements: relay_{int(relay_number or 0)}, setting={setting_name}")
        except Exception as e:
            logger.warning(f"Error creating relay measurements: {e}")
    
    def _create_parameter_measurements(self, terminal: Terminal, params: List) -> None:
        """Tạo measurements cho MAV_CMD_DO_SET_PARAMETER command"""
        try:
            if len(params) >= 2:
                # param1: Parameter number
                param_number = self._safe_get_param(params, 0)
                if param_number is not None:
                    terminal.set_measurement('parameter_number', f"{int(param_number)}")
                
                # param2: Parameter value
                param_value = self._safe_get_param(params, 1)
                if param_value is not None:
                    terminal.set_measurement('parameter_value', f"{param_value}")
                    
                logger.info(f"Tạo parameter measurements: param_{int(param_number or 0)}={param_value}")
        except Exception as e:
            logger.warning(f"Error creating parameter measurements: {e}")
    
    def _create_mount_control_measurements(self, terminal: Terminal, params: List) -> None:
        """Tạo measurements cho MAV_CMD_DO_MOUNT_CONTROL command"""
        try:
            if len(params) >= 3:
                # param1: Pitch angle (degrees)
                pitch = self._safe_get_param(params, 0)
                if pitch is not None:
                    terminal.set_measurement('mount_pitch', f"{pitch} degrees")
                
                # param2: Roll angle (degrees)
                roll = self._safe_get_param(params, 1)
                if roll is not None:
                    terminal.set_measurement('mount_roll', f"{roll} degrees")
                
                # param3: Yaw angle (degrees)
                yaw = self._safe_get_param(params, 2)
                if yaw is not None:
                    terminal.set_measurement('mount_yaw', f"{yaw} degrees")
                    
                logger.info(f"Tạo mount control measurements: pitch={pitch}, roll={roll}, yaw={yaw}")
        except Exception as e:
            logger.warning(f"Error creating mount control measurements: {e}")
    
    def _create_digicam_measurements(self, terminal: Terminal, params: List) -> None:
        """Tạo measurements cho MAV_CMD_DO_DIGICAM_CONTROL command"""
        try:
            if len(params) >= 1:
                # param1: Session control (0=stop, 1=start)
                session_control = self._safe_get_param(params, 0)
                if session_control is not None:
                    control_name = "Start" if int(session_control) == 1 else "Stop"
                    terminal.set_measurement('digicam_session', control_name)
                    
                logger.info(f"Tạo digicam measurements: session={control_name}")
        except Exception as e:
            logger.warning(f"Error creating digicam measurements: {e}")
    
    def _create_camera_trigger_measurements(self, terminal: Terminal, params: List) -> None:
        """Tạo measurements cho MAV_CMD_DO_SET_CAM_TRIGG_DIST command"""
        try:
            if len(params) >= 1:
                # param1: Distance between triggers (meters, 0 to disable)
                trigger_distance = self._safe_get_param(params, 0)
                if trigger_distance is not None:
                    if trigger_distance == 0:
                        terminal.set_measurement('camera_trigger', "Disabled")
                    else:
                        terminal.set_measurement('camera_trigger_distance', f"{trigger_distance} m")
                        
                logger.info(f"Tạo camera trigger measurements: distance={trigger_distance}m")
        except Exception as e:
            logger.warning(f"Error creating camera trigger measurements: {e}")
    
    def _create_generic_command_measurements(self, terminal: Terminal, params: List, command: int) -> None:
        """Tạo generic measurements cho các commands khác"""
        try:
            command_name = self.COMMAND_DESCRIPTIONS.get(command, f"Command_{command}")
            
            # Lưu tất cả parameters có giá trị vào measurements
            for i, param in enumerate(params[:7]):  # Chỉ lấy 7 params đầu tiên
                if param is not None and param != 0.0:
                    param_name = f"{command_name.lower().replace(' ', '_')}_param{i+1}"
                    terminal.set_measurement(param_name, f"{param}")
                    
            logger.info(f"Tạo generic measurements cho {command_name} với {len(params)} parameters")
        except Exception as e:
            logger.warning(f"Error creating generic command measurements: {e}")
    
    def _process_hold_parameter_for_terminal(self, terminal: Terminal, mission_item: Dict[str, Any]) -> None:
        """
        Xử lý tham số hold từ MAV_CMD_NAV_WAYPOINT và chuyển đổi thành time_stops measurement
        
        IMPORT: hold (giây) → time_stops (mins)
        
        Args:
            terminal: Terminal object đã được tạo
            mission_item: Mission item từ file plan
        """
        try:
            command = mission_item.get('command')
            params = mission_item.get('params', [])
            
            # Chỉ xử lý cho MAV_CMD_NAV_WAYPOINT (command = 16)
            if command == self.COMMAND_WAYPOINT and params and len(params) >= 1:
                # Tận dụng _safe_get_param và PARAM_INDEX đã có sẵn
                hold_time_s = self._safe_get_param(params, self.PARAM_INDEX['PARAM1'])
                
                if hold_time_s and hold_time_s > 0:
                    #print(f"IMPORT: Phát hiện tham số hold: {hold_time_s}s cho terminal {terminal.id}")
                    
                    # IMPORT: Chuyển đổi từ giây sang mins (theo model)
                    hold_time_mins = self._convert_seconds_to_default_unit(hold_time_s)
                    #print(f"IMPORT: Chuyển đổi thành công: {hold_time_s}s -> {hold_time_mins} {self.TIME_STOPS_DEFAULT_UNIT}")
                    # hold_time_mins = hold_time_s
                    # Tạo measurement time_stops với đơn vị mins (theo model)
                    terminal.set_measurement('time_stops', f"{hold_time_mins} {self.TIME_STOPS_DEFAULT_UNIT}")
                    terminal.stop = True
                    terminal.save()
                    #print(f"IMPORT: Đã tạo time_stops measurement: {hold_time_mins} {self.TIME_STOPS_DEFAULT_UNIT} cho terminal {terminal.id}")
                else:
                    logger.debug(f"IMPORT: Không có tham số hold hoặc hold = 0 cho terminal {terminal.id}")
            else:
                logger.debug(f"IMPORT: Command {command} không phải WAYPOINT hoặc không có params cho terminal {terminal.id}")
                
        except Exception as e:
            logger.error(f"IMPORT: Lỗi khi xử lý tham số hold cho terminal {terminal.id}: {e}")
    
    def _should_be_stop(self, mission_item: Dict[str, Any]) -> bool:
        """
        Xác định terminal nào nên có stop=True dựa trên command type và params
        
        Logic xác định stop:
        - WAYPOINT: dựa vào param1 (hold time)
          + Nếu có hold time > 0 → stop=True (dừng lại)
          + Mặc định: stop=False (bay qua)
        - TAKEOFF: không dừng lại (stop=False)
        - LAND: dừng lại (stop=True)
        - RTL: dừng lại (stop=True)
        - Các command khác: mặc định dừng lại (stop=True)
        
        Args:
            mission_item: Mission item từ file plan
            
        Returns:
            True nếu terminal nên dừng lại, False nếu chỉ bay qua
        """
        command = mission_item.get('command')
        params = mission_item.get('params', [])
        
        # MAV_CMD_NAV_WAYPOINT (16) - dựa vào hold time
        if command == self.COMMAND_WAYPOINT and params and len(params) >= 1:
            # param1: hold time (giây) - nếu > 0 thì dừng lại
            hold_time = self._safe_get_param(params, 0)  # param1
            if hold_time and hold_time > 0:
                #print(f"WAYPOINT có hold time {hold_time}s → stop=True")
                return True
            else:
                #print(f"WAYPOINT không có hold time → stop=False")
                return False
        
        # MAV_CMD_NAV_TAKEOFF (22) - không dừng lại
        elif command == self.COMMAND_TAKEOFF:
            #print(f"TAKEOFF → stop=False")
            return False
        
        # MAV_CMD_NAV_LAND (21) - dừng lại
        elif command == self.COMMAND_LAND:
            #print(f"LAND → stop=True")
            return True
        
        # MAV_CMD_NAV_RETURN_TO_LAUNCH (20) - dừng lại
        elif command == self.COMMAND_RTL:
            #print(f"RTL → stop=True")
            return True
        
        # Các command khác - mặc định là dừng lại
        else:
            #print(f"Command {command} → stop=True (mặc định)")
            return True
    
    def _get_hold_time_from_terminal(self, terminal: Terminal) -> Optional[float]:
        """
        Lấy giá trị hold time từ time_stops measurement của terminal và chuyển đổi về giây
        
        EXPORT: time_stops (mins) → hold (giây)
        
        Args:
            terminal: Terminal object
            
        Returns:
            Hold time in seconds hoặc None nếu không có
        """
        try:
            # Lấy time_stops measurement
            time_stops_measurement = terminal.measurements.filter(measurement_type='time_stops').first()
            
            if time_stops_measurement:
                # Lấy giá trị số từ measurement
                time_stops_value = time_stops_measurement.get_numeric_value(user_units=None)
                
                if time_stops_value is not None and time_stops_value > 0:
                    # hold_time_s = time_stops_value
                    # return hold_time_s
                    # Lấy đơn vị từ measurement
                    measurement_data = time_stops_measurement.data
                    if isinstance(measurement_data, dict) and 'unit' in measurement_data:
                        unit = measurement_data['unit']
                        hold_time_s = time_stops_value
                        # EXPORT: Chuyển đổi từ mins về giây
                        hold_time_s = self._convert_time_to_seconds(time_stops_value, unit)
                        #print(f"EXPORT: Chuyển đổi time_stops: {time_stops_value} {unit} -> {hold_time_s}s")
                        return hold_time_s
                    else:
                        # Nếu không có unit, giả sử đơn vị là mins (theo model default)
                        #print(f"EXPORT: Không có đơn vị, giả sử là {self.TIME_STOPS_DEFAULT_UNIT} (theo model): {time_stops_value} -> {time_stops_value * 60.0}s")
                        hold_time_s = time_stops_value * 60.0
                        return hold_time_s
            
            return None
            
        except Exception as e:
            logger.error(f"EXPORT: Lỗi khi lấy hold time từ terminal {terminal.id}: {e}")
            return None
    
    def _create_default_waypoint_params(self, terminal: Terminal, route_terminal: RouteTerminal) -> List[float]:
        """
        Tạo default params array cho WAYPOINT command
        
        Args:
            terminal: Terminal object
            route_terminal: RouteTerminal object
            
        Returns:
            List params với 7 giá trị
        """
        # Tạo default params array cho WAYPOINT
        # params[0]: hold time (từ time_stops measurement)
        # params[1-3]: command-specific parameters (0.0)
        # params[4-5]: latitude, longitude từ terminal
        # params[6]: altitude từ operating_altitude hoặc default
        default_params = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
        
        # Cập nhật params[0] với hold time từ time_stops measurement
        hold_time_s = self._get_hold_time_from_terminal(terminal)
        if hold_time_s is not None:
            default_params[self.PARAM_INDEX['PARAM1']] = hold_time_s
            #print(f"Đã cập nhật default param1 (hold): {hold_time_s}s cho terminal {terminal.id}")
        
        # Cập nhật params[4] và params[5] với coordinates của terminal
        if hasattr(terminal, 'latitude') and terminal.latitude is not None:
            default_params[self.PARAM_INDEX['X']] = float(terminal.latitude)
        if hasattr(terminal, 'longitude') and terminal.longitude is not None:
            default_params[self.PARAM_INDEX['Y']] = float(terminal.longitude)
        
        # Cập nhật params[6] với altitude từ operating_altitude hoặc default
        altitude_m = self._get_operating_altitude_from_route_terminal(route_terminal)
        if altitude_m is not None:
            default_params[self.PARAM_INDEX['Z']] = float(altitude_m)
        else:
            default_params[self.PARAM_INDEX['Z']] = 50.0  # Default altitude 50m
        
        return default_params
    
    def _create_default_non_coordinate_params(self) -> List[float]:
        """
        Tạo default params array cho các command không cần coordinates
        
        Returns:
            List params với 7 giá trị 0.0
        """
        return [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
    
    def _convert_time_to_seconds(self, value: float, unit: str) -> float:
        """
        Chuyển đổi thời gian về giây (dùng cho EXPORT)
        
        Args:
            value: Giá trị thời gian
            unit: Đơn vị thời gian
            
        Returns:
            Thời gian tính bằng giây
        """
        try:
            print(f"Chuyển đổi đơn vị: {value} {unit} -> {convert_unit(value, unit, 's')}")
            if unit == self.TIME_STOPS_DEFAULT_UNIT:
                return convert_unit(value, self.TIME_STOPS_DEFAULT_UNIT, 's')
            elif unit == 'min':
                return convert_unit(value, 'min', 's')
            elif unit == 's':
                return value
            elif unit == 'sec':
                return convert_unit(value, 'sec', 's')
            else:
                # Fallback: giả sử đơn vị là mins (theo model default)
                return convert_unit(value, self.TIME_STOPS_DEFAULT_UNIT, 's')
        except Exception as conversion_error:
            logger.warning(f"Không thể chuyển đổi đơn vị {unit}, sử dụng fallback: {conversion_error}")
            # Fallback: giả sử đơn vị là mins (theo model default)
            return value * 60.0
    
    def _convert_seconds_to_default_unit(self, seconds: float) -> float:
        """
        Chuyển đổi từ giây sang đơn vị mặc định (dùng cho IMPORT)
        
        Args:
            seconds: Thời gian tính bằng giây
            
        Returns:
            Thời gian tính bằng đơn vị mặc định (mins)
        """
        try:
            return convert_unit(seconds, 's', self.TIME_STOPS_DEFAULT_UNIT)
        except Exception as conversion_error:
            logger.warning(f"Không thể chuyển đổi từ giây sang {self.TIME_STOPS_DEFAULT_UNIT}, sử dụng phép chia thủ công: {conversion_error}")
            # Fallback: chuyển đổi thủ công từ giây sang phút
            return seconds / 60.0
    
    def _update_waypoint_hold_param(self, params: List[float], terminal: Terminal) -> None:
        """
        Cập nhật tham số hold (param1) cho WAYPOINT command từ time_stops measurement
        
        Args:
            params: List params cần cập nhật
            terminal: Terminal object để lấy time_stops
        """
        if params and len(params) > self.PARAM_INDEX['PARAM1']:
            hold_time_s = self._get_hold_time_from_terminal(terminal)
            if hold_time_s is not None:
                params[self.PARAM_INDEX['PARAM1']] = hold_time_s
                #print(f"Đã cập nhật param1 (hold) cho WAYPOINT: {hold_time_s}s")
    
    def _create_coordinate_params(self, terminal: Terminal, altitude_ft: float) -> List[float]:
        """
        Tạo params array với coordinates từ terminal
        
        Args:
            terminal: Terminal object
            altitude_ft: Altitude in feet
            
        Returns:
            List params với coordinates
        """
        params = self._create_default_non_coordinate_params()
        params[self.PARAM_INDEX['X']] = float(terminal.latitude)
        params[self.PARAM_INDEX['Y']] = float(terminal.longitude)
        params[self.PARAM_INDEX['Z']] = float(altitude_ft)
        return params
    
    def _update_coordinate_params(self, params: List[float], terminal: Terminal, altitude_ft: float) -> None:
        """
        Cập nhật coordinates vào params array
        
        Args:
            params: List params cần cập nhật
            terminal: Terminal object
            altitude_ft: Altitude in feet
        """
        if params and len(params) > self.PARAM_INDEX['Z']:
            params[self.PARAM_INDEX['X']] = float(terminal.latitude)
            params[self.PARAM_INDEX['Y']] = float(terminal.longitude)
            params[self.PARAM_INDEX['Z']] = float(altitude_ft)
    
    def _ensure_params_length(self, params_array: List, min_length: int = 7) -> List[float]:
        """
        Đảm bảo params array có đủ độ dài với các giá trị mặc định
        
        Args:
            params_array: List params gốc
            min_length: Độ dài tối thiểu cần thiết
            
        Returns:
            List params với đủ độ dài
        """
        params = []
        for i in range(min_length):
            if i < len(params_array) and params_array[i] is not None:
                try:
                    params.append(float(params_array[i]))
                except (ValueError, TypeError):
                    params.append(0.0)
            else:
                params.append(0.0)
        return params
    
    def _extract_coordinates_from_params(self, params: List[Any]) -> Optional[Dict[str, Optional[float]]]:
        """Extract coordinates từ params theo MAVLink MISSION_ITEM spec"""
        if not params or len(params) < 7:
            return None
        
        try:
            # Theo MAVLink spec: params[4-6] là x, y, z (lat, lon, alt)
            latitude = self._safe_get_param(params, self.PARAM_INDEX['X'])
            longitude = self._safe_get_param(params, self.PARAM_INDEX['Y'])
            altitude = self._safe_get_param(params, self.PARAM_INDEX['Z'])
            
            return {
                'latitude': latitude,
                'longitude': longitude,
                'altitude': altitude
            }
        except Exception:
            return None
    
    def _safe_get_param(self, params: List[Any], index: int) -> Optional[float]:
        """Lấy param an toàn theo index với type conversion"""
        try:
            if index < len(params):
                value = params[index]
                if value is not None and value != '':
                    return float(value)
        except (ValueError, TypeError):
            pass
        return None
    
    def _validate_coordinates(self, coordinates: Dict[str, Optional[float]]) -> bool:
        """Validate coordinates theo geographical ranges"""
        lat = coordinates.get('latitude')
        lon = coordinates.get('longitude')
        
        if lat is None or lon is None:
            return False
        
        # Validate latitude: -90 to 90
        if not (-90 <= lat <= 90):
            return False
        
        # Validate longitude: -180 to 180
        if not (-180 <= lon <= 180):
            return False
        
        return True
    
    def _get_command_description(self, command: int) -> str:
        """Lấy mô tả command theo MAVLink specification"""
        # Sử dụng mapping mới từ API FLIGHTBRID
        command_name = self._get_command_name_from_api(command)
        # Chuyển đổi từ MAV_CMD_NAME sang description ngắn gọn
        if command_name.startswith("MAV_CMD_"):
            return command_name.replace("MAV_CMD_", "").replace("_", " ").title()
        return command_name
    
    @transaction.atomic
    def _create_route_from_terminals(self, terminal_mission_pairs: List[Tuple[Terminal, Dict]], plan_data: Dict, plan_file_name: str, service_id: int | None = None) -> Routes:
        """Tạo route từ danh sách terminals và lưu đầy đủ mission data (tối ưu với bulk_create)"""
        try:
            mission = plan_data.get('mission', {})
            mission_items = mission.get('items', [])
            
            # Lấy tên file từ plan_data để đặt tên route
            ground_station = plan_data.get('groundStation', 'Unknown')
            file_name = plan_file_name  # Nếu có tên file
            print(file_name)
            if not file_name:
                # Fallback: dùng timestamp
                from datetime import datetime
                now = datetime.now()
                timestamp = f"{now:%Y%m%d_%H%M%S}_{now.microsecond:06d}"
                file_name = f"plan_{timestamp}_{uuid.uuid4().hex}"
            
            # Xác định two_way từ file .plan
            # Kiểm tra xem có RTL command hoặc return pattern không
            two_way = self._determine_two_way_from_plan(mission_items)
            
            # Tạo route với tên theo file
            route_start = time.perf_counter()
            # Chỉ đếm những terminals có stop=True cho total_stops
            total_stops = sum(1 for _, mission_item in terminal_mission_pairs if self._should_be_stop(mission_item))
            route = Routes.objects.create(
                name=f"{file_name}",
                description=f"Route được tạo từ file .plan với {len(terminal_mission_pairs)} terminals, {total_stops} stops",
                status='active',
                total_stops=total_stops,
                code=f"ROUTE_PLAN_{str(uuid.uuid4()).replace('-', '')}",
                two_way=two_way, 
                route_service_id=service_id,
            )
            
            # Tạo measurement cho total_distance nếu có thể tính được
            terminals = [pair[0] for pair in terminal_mission_pairs]
            if len(terminals) > 1:
                try:
                    total_distance = self._calculate_total_distance(terminals)
                    route.create_measurement('total_distance', {
                        'type': 'simple',
                        'value': total_distance,
                        'unit': 'km'
                    })

                    # Tạo measurement cho estimated_time (phút) nếu có cruiseSpeed hợp lệ
                    # QGC mission.cruiseSpeed thường là m/s
                    cruise_speed = mission.get('cruiseSpeed')
                    try:
                        cruise_speed_mps = float(cruise_speed) if cruise_speed is not None else None
                    except (ValueError, TypeError):
                        cruise_speed_mps = None

                    # time(min) = distance(km)*1000 / speed(m/s) / 60
                    if cruise_speed_mps and cruise_speed_mps > 0:
                        estimated_time_mins = (float(total_distance) * 1000.0) / cruise_speed_mps / 60.0
                        route.create_measurement('estimated_time', {
                            'type': 'simple',
                            'value': round(estimated_time_mins, 2),
                            'unit': 'min'
                        })
                except Exception:
                    pass
            route_create_time = time.perf_counter() - route_start
            print(f"  ⏱️  Tạo route: {route_create_time:.3f}s")
            
            # Chuẩn bị dữ liệu cho bulk create route terminals
            prepare_start = time.perf_counter()
            route_terminals_to_create = []
            route_terminal_mission_pairs = []  # Lưu (route_terminal_data, terminal, mission_item) để xử lý measurements sau
            
            for index, (terminal, mission_item) in enumerate(terminal_mission_pairs):
                # Lấy doJumpId gốc để giữ thứ tự
                original_do_jump_id = mission_item.get('doJumpId', index + 1)
                
                # Xác định stop dựa trên command type và params
                should_stop = self._should_be_stop(mission_item)
                
                # Lấy frame từ mission item
                frame_data = self._get_frame_from_mission_item(mission_item)
                
                route_terminal_data = {
                    'route': route,
                    'terminal': terminal,
                    'order': original_do_jump_id,
                    'stop': should_stop,
                    'frame': frame_data,
                }
                
                route_terminals_to_create.append(RouteTerminal(**route_terminal_data))
                route_terminal_mission_pairs.append((route_terminal_data, terminal, mission_item))
            prepare_time = time.perf_counter() - prepare_start
            print(f"  ⏱️  Chuẩn bị route terminals data: {prepare_time:.3f}s")
            
            # Chia nhỏ thành các batch để tránh connection pool overflow
            BATCH_SIZE = 50
            created_route_terminals = []
            total_batches = (len(route_terminals_to_create) + BATCH_SIZE - 1) // BATCH_SIZE
            
            print(f"  📦 Chia thành {total_batches} batch(es) route terminals, mỗi batch {BATCH_SIZE}")
            
            batch_start_time = time.perf_counter()
            
            # Bulk create route terminals theo batch
            for batch_num, i in enumerate(range(0, len(route_terminals_to_create), BATCH_SIZE), 1):
                batch_start = time.perf_counter()
                batch_route_terminals = route_terminals_to_create[i:i + BATCH_SIZE]
                batch_mission_pairs = route_terminal_mission_pairs[i:i + BATCH_SIZE]
                
                # Bulk create batch route terminals
                create_start = time.perf_counter()
                batch_created = RouteTerminal.objects.bulk_create(
                    batch_route_terminals,
                    batch_size=BATCH_SIZE
                )
                create_time = time.perf_counter() - create_start
                created_route_terminals.extend(batch_created)
                print(f"    Route Terminal Batch {batch_num}/{total_batches}: {len(batch_created)} terminals - Create: {create_time:.3f}s")
            
            total_batch_time = time.perf_counter() - batch_start_time
            print(f"  ⏱️  Tổng thời gian tạo route terminals: {total_batch_time:.3f}s")
            
            # Xử lý measurements và các thao tác khác cần route_terminal object đã có ID (theo batch)
            # Tối ưu: sử dụng bulk_create cho measurements
            measurements_start_time = time.perf_counter()
            
            # Lấy ContentType một lần cho RouteTerminal
            route_terminal_content_type = ContentType.objects.get_for_model(RouteTerminal)
            
            # Chuẩn bị tất cả measurements data trước
            measurements_to_create = []
            route_terminal_command_lines = []  # Lưu (route_terminal, mission_item) để xử lý command_line sau
            
            for route_terminal, (route_terminal_data, terminal, mission_item) in zip(created_route_terminals, route_terminal_mission_pairs):
                try:
                    # Tạo measurement cho cruise_speed từ mission (cho tất cả terminals)
                    if mission.get('cruiseSpeed'):
                        try:
                            cruise_speed_value = float(mission.get('cruiseSpeed'))
                            measurements_to_create.append(Measurement(
                                content_type=route_terminal_content_type,
                                object_id=route_terminal.id,
                                measurement_type='cruise_speed',
                                data={
                                    'type': 'simple',
                                    'value': cruise_speed_value,
                                    'unit': 'm/s'
                                }
                            ))
                        except (ValueError, TypeError):
                            pass
                    
                    # Tạo measurement cho operating_altitude từ mission item
                    altitude_value = None
                    if mission_item.get('Altitude') is not None:
                        try:
                            altitude_ft = float(mission_item.get('Altitude'))
                            altitude_value = altitude_ft
                        except (ValueError, TypeError) as e:
                            logger.error(f"❌ Error convert altitude value: {e}, mission_item: {mission_item}")
                            altitude_value = 50.0  # Default
                        except Exception as e:
                            logger.error(f"❌ Error tạo operating_altitude measurement: {e}")
                            altitude_value = 50.0  # Fallback default
                    else:
                        altitude_value = 50.0  # Default nếu không có Altitude
                    
                    # Thêm operating_altitude measurement
                    measurements_to_create.append(Measurement(
                        content_type=route_terminal_content_type,
                        object_id=route_terminal.id,
                        measurement_type='operating_altitude',
                        data={
                            'type': 'simple',
                            'value': altitude_value,
                            'unit': 'm'
                        }
                    ))
                    
                    # Lưu để xử lý command_line sau
                    if mission_item.get('command'):
                        route_terminal_command_lines.append((route_terminal, mission_item))
                        
                except Exception as e:
                    logger.error(f"Error preparing measurements for route terminal {route_terminal.id}: {e}")
                    continue
            
            # Bulk create measurements theo batch
            if measurements_to_create:
                MEASUREMENT_BATCH_SIZE = 100
                total_measurement_batches = (len(measurements_to_create) + MEASUREMENT_BATCH_SIZE - 1) // MEASUREMENT_BATCH_SIZE
                print(f"  📦 Chuẩn bị {len(measurements_to_create)} measurements, chia thành {total_measurement_batches} batch(es)")
                
                bulk_start = time.perf_counter()
                for i in range(0, len(measurements_to_create), MEASUREMENT_BATCH_SIZE):
                    batch_measurements = measurements_to_create[i:i + MEASUREMENT_BATCH_SIZE]
                    Measurement.objects.bulk_create(batch_measurements, batch_size=MEASUREMENT_BATCH_SIZE)
                bulk_time = time.perf_counter() - bulk_start
                print(f"  ⏱️  Bulk create measurements: {bulk_time:.3f}s")
            
            # Xử lý command_line sau khi measurements đã được tạo
            command_line_start = time.perf_counter()
            for route_terminal, mission_item in route_terminal_command_lines:
                try:
                    self._process_command_line_for_route_terminal(route_terminal, mission_item)
                except Exception as e:
                    logger.error(f"Error processing command_line for route terminal {route_terminal.id}: {e}")
                    continue
            command_line_time = time.perf_counter() - command_line_start
            print(f"  ⏱️  Xử lý command_line: {command_line_time:.3f}s")
            
            total_measurements_time = time.perf_counter() - measurements_start_time
            print(f"  ⏱️  Tổng thời gian xử lý measurements: {total_measurements_time:.3f}s")
            
            # QUAN TRỌNG: Lưu tất cả commands vào command_line của route terminals
            # để đảm bảo không mất thông tin từ các commands không có coordinates
            command_line_start = time.perf_counter()
            self._save_all_commands_to_route_terminals(route, mission_items)
            command_line_time = time.perf_counter() - command_line_start
            print(f"  ⏱️  Lưu command_line: {command_line_time:.3f}s")
            
            return route
            
        except Exception as e:
            logger.error(f"Error creating route from terminals: {e}")
            raise ValidationError(f"Error creating route: {str(e)}")

    def _determine_two_way_from_plan(self, mission_items: List[Dict]) -> bool:
        """
        Xác định two_way từ file .plan dựa trên các patterns:
        1. Có RTL command (MAV_CMD_NAV_RETURN_TO_LAUNCH = 20)
        2. Có pattern return về home position
        3. Có LAND command ở cuối (thường là return pattern)
        
        Args:
            mission_items: Danh sách mission items từ file .plan
            
        Returns:
            bool: True nếu route có return pattern, False nếu không
        """
        try:
            if not mission_items:
                return False
            
            # Pattern 1: Kiểm tra có RTL command không
            has_rtl = any(
                item.get('command') == self.COMMAND_RTL 
                for item in mission_items
            )
            
            if has_rtl:
                #print("✅ Phát hiện RTL command trong file .plan -> two_way=True")
                return True
            
            # # Pattern 2: Kiểm tra có LAND command ở cuối không (thường là return pattern)
            # if len(mission_items) > 1:
            #     last_item = mission_items[-1]
            #     if last_item.get('command') == self.COMMAND_LAND:
            #         #print("✅ Phát hiện LAND command ở cuối -> two_way=True")
            #         return True
            
            # Pattern 3: Kiểm tra có pattern return về home position
            # Nếu có nhiều waypoints và waypoint cuối gần với waypoint đầu
            # if len(mission_items) > 2:
            #     # Lấy các waypoints (bỏ qua TAKEOFF và LAND)
            #     waypoint_items = [
            #         item for item in mission_items 
            #         if item.get('command') == self.COMMAND_WAYPOINT
            #     ]
                
            #     if len(waypoint_items) >= 2:
            #         # Kiểm tra waypoint cuối có gần với waypoint đầu không
            #         first_waypoint = waypoint_items[0]
            #         last_waypoint = waypoint_items[-1]
                    
            #         # Lấy coordinates
            #         first_lat = self._extract_coordinate(first_waypoint, 'lat')
            #         first_lng = self._extract_coordinate(first_waypoint, 'lng')
            #         last_lat = self._extract_coordinate(last_waypoint, 'lat')
            #         last_lng = self._extract_coordinate(last_waypoint, 'lng')
                    
            #         if all(coord is not None for coord in [first_lat, first_lng, last_lat, last_lng]):
            #             # Tính khoảng cách giữa điểm đầu và cuối
            #             from terminals.utils import calculate_distance_km
            #             distance = calculate_distance_km(
            #                 first_lat, first_lng, last_lat, last_lng
            #             )
                        
            #             # Nếu khoảng cách < 100m, có thể là return pattern
            #             if distance < 0.1:  # 0.1 km = 100m
            #                 #print(f"✅ Phát hiện return pattern: điểm đầu và cuối gần nhau ({distance:.3f} km) -> two_way=True")
            #                 return True
            
            # Pattern 4: Kiểm tra có plannedHomePosition và pattern return
            # Nếu có nhiều waypoints và pattern cho thấy return về home
            # if len(mission_items) > 3:
            #     # Đếm số lượng waypoints
            #     waypoint_count = sum(
            #         1 for item in mission_items 
            #         if item.get('command') == self.COMMAND_WAYPOINT
            #     )
                
            #     # Nếu có nhiều waypoints (>3), có thể là return pattern
            #     if waypoint_count > 3:
            #         #print(f"✅ Phát hiện nhiều waypoints ({waypoint_count}) -> two_way=True")
            #         return True
            
            #print("ℹ️ Không phát hiện return pattern -> two_way=False")
            return False
            
        except Exception as e:
            logger.warning(f"⚠️ Error khi xác định two_way: {e}, mặc định False")
            return False

    def _extract_coordinate(self, mission_item: Dict, coord_type: str) -> Optional[float]:
        """
        Trích xuất coordinate từ mission item
        
        Args:
            mission_item: Mission item từ file .plan
            coord_type: 'lat' hoặc 'lng'
            
        Returns:
            float: Giá trị coordinate hoặc None nếu không có
        """
        try:
            params = mission_item.get('params', [])
            
            if coord_type == 'lat':
                # params[4] thường là latitude
                if len(params) > 4 and params[4] is not None:
                    return float(params[4])
            elif coord_type == 'lng':
                # params[5] thường là longitude  
                if len(params) > 5 and params[5] is not None:
                    return float(params[5])
            
            return None
            
        except (ValueError, TypeError, IndexError):
            return None



    def _save_all_commands_to_route_terminals(self, route: Routes, mission_items: List[Dict]):
        """Lưu tất cả commands vào command_line của route terminals để đảm bảo đầy đủ thông tin"""
        try:
            # Lấy tất cả route terminals theo thứ tự
            route_terminals = list(route.route_terminals.all().order_by('order'))
            
            # Nếu không có route terminals, thoát
            if not route_terminals:
                return
            
            # Lưu commands vào route terminal đầu tiên (nếu có commands không có coordinates)
            first_route_terminal = route_terminals[0]
            non_coordinate_commands = []
            
            for item in mission_items:
                command = item.get('command')
                if not self._is_coordinate_command(command, item.get('params', [])):
                    # Đây là command không có coordinates (như SET_CAMERA_MODE, RTL)
                    non_coordinate_commands.append(item)
            
            # Nếu có commands không có coordinates, lưu vào command_line của terminal đầu tiên
            if non_coordinate_commands:
                existing_command_line = first_route_terminal.command_line or {}
                
                for item in non_coordinate_commands:
                    command = item.get('command')
                    command_name = self._get_command_name_from_api(command)
                    
                    # Format: {"COMMAND_ID": {"MAV_CMD_NAME": [param1, param2, ..., param7]}}
                    command_id_str = str(command)
                    params = item.get('params', [])
                    
                    # Đảm bảo params có đủ 7 giá trị và convert sang float
                    params_array = []
                    for i in range(7):
                        if i < len(params) and params[i] is not None:
                            params_array.append(float(params[i]))
                        else:
                            params_array.append(0.0)
                    
                    existing_command_line[command_id_str] = {
                        command_name: params_array
                    }
                
                # Cập nhật command_line
                first_route_terminal.command_line = existing_command_line
                first_route_terminal.save()
                
                #print(f"Saved {len(non_coordinate_commands)} non-coordinate commands to first route terminal")
                
        except Exception as e:
            logger.warning(f"Error saving non-coordinate commands: {e}")
            # Không raise exception vì đây không phải lỗi nghiêm trọng
    
    def _find_mission_item_for_terminal(self, terminal: Terminal, plan_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Tìm mission item tương ứng với terminal dựa trên coordinates"""
        mission_items = plan_data.get('mission', {}).get('items', [])
        
        for item in mission_items:
            if self._is_coordinate_command(item.get('command'), item.get('params', [])):
                params = item.get('params', [])
                if len(params) >= 7:
                    lat = self._safe_get_param(params, 4)
                    lon = self._safe_get_param(params, 5)
                    
                    # So sánh coordinates (với độ chính xác 6 chữ số thập phân)
                    if (abs(lat - terminal.latitude) < 0.000001 and 
                        abs(lon - terminal.longitude) < 0.000001):
                        return item
        
        return None
    
    def _process_command_line_for_route_terminal(self, route_terminal: RouteTerminal, mission_item: Dict[str, Any]) -> None:
        """Xử lý command_line cho route terminal từ mission item khi import"""
        command = mission_item.get('command')
        params = mission_item.get('params', [])
        
        # Tạo command line entry theo format mới: {"command_id": {"command_name": [params_array]}}
        # Đảm bảo không có None values trong params array
        params_array = []
        for i in range(7):  # MAVLink cần 7 params
            if i < len(params) and params[i] is not None:
                try:
                    params_array.append(float(params[i]))
                except (ValueError, TypeError):
                    params_array.append(0.0)
            else:
                params_array.append(0.0)  # Thay None bằng 0.0
        
        # Lấy command name từ API FLIGHTBRID nếu có thể
        command_name = self._get_command_name_from_api(command)
        print("command_name: ", command_name)
        # Tạo command line theo format mới với mapping từ API
        command_data = {
            str(command): {  # command_id là string
                command_name: params_array
            }
        }
        
        if hasattr(route_terminal, 'command_line'):
            # Nếu command_line là JSONField
            current_commands = route_terminal.command_line or {}
            current_commands.update(command_data)
            route_terminal.command_line = current_commands
            route_terminal.save(update_fields=['command_line'])
    
    def _load_command_names_cache(self) -> None:
        """Load tất cả command names từ API một lần và cache lại"""
        if self._command_names_loaded:
            return
        
        try:
            base_url = os.getenv('FLIGHTBRID_URL')
            if base_url:
                api_url = f"{base_url}/api/drone/mavlink-commands?isFull=true"
                headers = get_gcs_api_headers()
                response = requests.get(api_url, headers=headers, timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get('commands'):
                        for cmd in data.get('commands', []):
                            cmd_id = cmd.get('CommandId') or cmd.get('id_command')
                            cmd_name = cmd.get('CommandName') or cmd.get('command_name')
                            if cmd_id is not None and cmd_name:
                                self._command_names_cache[int(cmd_id)] = cmd_name
                        self._command_names_loaded = True
                        logger.info(f"Đã load {len(self._command_names_cache)} command names vào cache")
        except Exception as e:
            logger.warning(f"Không thể load command names từ API: {e}, sẽ dùng fallback khi cần")
    
    def _get_command_name_from_api(self, command: int) -> str:
        """Lấy tên MAV_CMD từ cache (đã được load trước), fallback về MAV_CMD_NAV_WAYPOINT nếu không có"""
        # Sử dụng cache thay vì gọi API mỗi lần
        if command in self._command_names_cache:
            return self._command_names_cache[command]
        
        # Fallback về MAV_CMD_NAV_WAYPOINT nếu không tìm thấy trong cache
        logger.debug(f"Command {command} không có trong cache, sử dụng fallback MAV_CMD_NAV_WAYPOINT")
        return "MAV_CMD_NAV_WAYPOINT"
    
    def export_routes_to_plans(self, route_ids: List[int]) -> List[Tuple[str, str]]:
        """
        Export routes thành danh sách file .plan
        
        Args:
            route_ids: List ID của routes cần export
            
        Returns:
            List các tuple (filename, file_content)
        """
        plans = []
        invalidated_routes: set[int] = set()
        
        for route_id in route_ids:
            try:
                route = Routes.objects.get(id=route_id)
                plan_content = self._create_plan_from_route(route)
                filename = f"route_{route_id}_{route.name.replace(' ', '_')}.plan"
                plans.append((filename, json.dumps(plan_content, indent=2)))
                
            except Routes.DoesNotExist:
                # Skip route không tồn tại
                continue
            except Exception as e:
                # Log error nhưng không dừng quá trình
                #print(f"Error exporting route {route_id}: {e}")
                continue
        
        return plans
    
    def _create_plan_from_route(self, route: Routes) -> Dict:
        """Tạo plan data từ route"""
        try:
            # Lấy route terminals theo thứ tự
            route_terminals = list(route.route_terminals.all().order_by('order'))
            
            if not route_terminals:
                raise ValidationError("Route không có terminals")
            
            # Lấy cruise speed từ route terminal đầu tiên
            cruise_speed = self._get_cruise_speed_from_route(route)
            
            # Lấy home position
            home_lat, home_lng, home_alt = self._get_home_position(route)
            
            # Tạo mission items theo thứ tự gốc từ file import
            mission_items = []
            do_jump_id = 1
            
            # QUAN TRỌNG: Sắp xếp commands theo thứ tự gốc
            all_commands = self._get_all_commands_in_original_order(route_terminals)
            
            for command_info in all_commands:
                command_number = command_info['command']
                route_terminal = command_info['route_terminal']
                params_array = command_info['params']
                
                # Tạo mission item dựa trên command type
                if command_number == self.COMMAND_TAKEOFF:
                    mission_item = self._create_takeoff_item(
                        route_terminal, command_number, do_jump_id, params_array
                    )
                    mission_items.append(mission_item)
                    do_jump_id += 1
                    
                elif command_number == self.COMMAND_WAYPOINT:
                    mission_item = self._create_waypoint_item(
                        route_terminal, command_number, do_jump_id, params_array
                    )
                    mission_items.append(mission_item)
                    do_jump_id += 1
                    
                elif command_number == self.COMMAND_LAND:
                    mission_item = self._create_land_item(
                        route_terminal, command_number, do_jump_id, params_array
                    )
                    mission_items.append(mission_item)
                    do_jump_id += 1
                    
                elif command_number == self.COMMAND_RTL:
                    mission_item = self._create_rtl_item(command_number, do_jump_id)
                    mission_items.append(mission_item)
                    do_jump_id += 1
                    
                else:
                    # Custom command (như SET_CAMERA_MODE, DO_SET_SERVO, etc.)
                    mission_item = self._create_custom_mission_item_from_array(
                        route_terminal, command_number, do_jump_id, params_array
                    )
                    mission_items.append(mission_item)
                    do_jump_id += 1
            
            # QUAN TRỌNG: Check biến two_way của route để tự động thêm RTL command
            if hasattr(route, 'two_way') and route.two_way:
                #print(f"Route {route.id} có two_way=True, tự động thêm RTL command")
                rtl_item = self._create_rtl_item(self.COMMAND_RTL, do_jump_id)
                mission_items.append(rtl_item)
                do_jump_id += 1
            
            # Tạo plan structure
            plan_data = {
                "fileType": "Plan",
                "geoFence": {
                    "circles": [],
                    "polygons": [],
                    "version": 2
                },
                "groundStation": "QGroundControl",
                "mission": {
                    "cruiseSpeed": cruise_speed,
                    "firmwareType": 3,  # Giữ nguyên như file gốc
                    "globalPlanAltitudeMode": 1,  # Gắn cứng
                    "hoverSpeed": 5.0,  # Gắn cứng
                    "items": mission_items,
                    "plannedHomePosition": [home_lat, home_lng, home_alt],
                    "vehicleType": 2,  # Gắn cứng
                    "version": 2  # Gắn cứng
                },
                "rallyPoints": {
                    "points": [],
                    "version": 2
                },
                "version": 1
            }
            
            return plan_data
            
        except Exception as e:
            logger.error(f"Error creating plan from route: {e}")
            raise ValidationError(f"Error creating plan: {str(e)}")

    def _get_all_commands_in_original_order(self, route_terminals: List[RouteTerminal]) -> List[Dict]:
        """
        Lấy tất cả commands theo thứ tự gốc từ file import
        
        Logic mới: Tạo command trực tiếp từ thông tin của RouteTerminal 
        thay vì từ command_line để giữ nguyên doJumpId gốc
        """
        all_commands = []
        
        for route_terminal in route_terminals:
            # Xác định command type dựa trên terminal name và thông tin
            command_info = self._determine_command_from_route_terminal(route_terminal)
            
            all_commands.append({
                'command': command_info['command'],
                'command_name': command_info['command_name'],
                'params': command_info['params'],
                'route_terminal': route_terminal,
                'order': route_terminal.order  # Giữ nguyên order từ doJumpId gốc
            })
        
        # QUAN TRỌNG: Giữ nguyên thứ tự gốc theo doJumpId (order)
        # Điều này đảm bảo terminals (command 183) và các commands khác giữ nguyên vị trí như file gốc
        all_commands.sort(key=lambda cmd: cmd['order'])
        return all_commands

    def _determine_command_from_route_terminal(self, route_terminal: RouteTerminal) -> Dict:
        """
        Xác định command type và tham số từ RouteTerminal
        
        Returns:
            Dict với 'command', 'command_name', 'params'
        """
        # QUAN TRỌNG: Luôn ưu tiên lấy từ command_line trước vì đó là nguồn thông tin chính xác nhất
        if hasattr(route_terminal, 'command_line') and route_terminal.command_line:
            command_line_data = route_terminal.command_line
            if isinstance(command_line_data, dict) and len(command_line_data) >= 1:
                # Format: {"COMMAND_ID": {"MAV_CMD_NAME": [params...]}}
                # Lấy command đầu tiên (thường chỉ có 1 command per RouteTerminal)
                command_id_str = list(command_line_data.keys())[0]
                cmd_data = command_line_data[command_id_str]
                if isinstance(cmd_data, dict) and len(cmd_data) >= 1:
                    command_number = int(command_id_str)
                    command_name = list(cmd_data.keys())[0]
                    params_array = list(cmd_data.values())[0]
                    
                    # Đảm bảo params_array là list với đủ 7 elements
                    if not isinstance(params_array, list):
                        params_array = [0.0] * 7
                    elif len(params_array) < 7:
                        params_array.extend([0.0] * (7 - len(params_array)))
                    
                    return {
                        'command': command_number,
                        'command_name': command_name,
                        'params': params_array[:7]  # Chỉ lấy 7 elements đầu tiên
                    }
        
        # Fallback: Xác định command dựa trên terminal name (routes cũ không có command_line)
        terminal_name = route_terminal.terminal.name.upper()
        
        if 'TAKEOFF' in terminal_name or 'TEMP_TAKEOFF' in terminal_name:
            return {
                'command': self.COMMAND_TAKEOFF,  # 22
                'command_name': 'MAV_CMD_NAV_TAKEOFF',
                'params': self._create_takeoff_params(route_terminal)
            }
        elif 'LAND' in terminal_name or 'TEMP_LAND' in terminal_name:
            return {
                'command': self.COMMAND_LAND,  # 21
                'command_name': 'MAV_CMD_NAV_LAND',
                'params': self._create_land_params(route_terminal)
            }
        else:
            # Default: WAYPOINT cho tất cả các cases còn lại
            return {
                'command': self.COMMAND_WAYPOINT,  # 16
                'command_name': 'MAV_CMD_NAV_WAYPOINT',
                'params': self._create_default_waypoint_params(route_terminal.terminal, route_terminal)
            }

    def _create_takeoff_params(self, route_terminal: RouteTerminal) -> List[float]:
        """Tạo params array cho TAKEOFF command (fallback khi không có command_line)"""
        altitude_m = self._get_operating_altitude_from_route_terminal(route_terminal)
        altitude_ft = altitude_m
        
        return [
            15.0,  # Minimum pitch angle
            0.0, 0.0, 0.0,  # Empty params
            float(route_terminal.terminal.latitude),
            float(route_terminal.terminal.longitude),
            altitude_ft
        ]

    def _create_land_params(self, route_terminal: RouteTerminal) -> List[float]:
        """Tạo params array cho LAND command (fallback khi không có command_line)"""
        return [
            0.0, 0.0, 0.0, 0.0,  # Standard LAND params
            float(route_terminal.terminal.latitude),
            float(route_terminal.terminal.longitude),
            0.0  # Land at ground level
        ]

    def _create_takeoff_item(self, route_terminal: RouteTerminal, command: int, do_jump_id: int, params_array: List[float]) -> Dict:
        """Tạo TAKEOFF mission item"""
        # Lấy altitude từ operating_altitude measurement (đang ở m)
        altitude_m = self._get_operating_altitude_from_route_terminal(route_terminal)
        # Chuyển đổi từ m sang ft cho QGroundControl
        altitude_ft = altitude_m
        
        # Lấy frame từ route_terminal.frame
        frame_id = self._get_frame_from_route_terminal(route_terminal)
        
        # Lấy altitude mode từ route_terminal (nếu có)
        altitude_mode = self._get_altitude_mode_from_route_terminal(route_terminal)
        
        # Lấy auto continue từ route_terminal (nếu có)
        auto_continue = self._get_auto_continue_from_route_terminal(route_terminal)
        
        # Đảm bảo params có đủ 7 giá trị
        params = self._ensure_params_length(params_array)
        
        return {
            "AMSLAltAboveTerrain": None,
            "Altitude": float(altitude_ft),  # Sử dụng altitude đã chuyển đổi sang ft
            "AltitudeMode": int(altitude_mode),
            "autoContinue": bool(auto_continue),
            "command": int(command),
            "doJumpId": int(do_jump_id),
            "frame": int(frame_id),
            "params": params,
            "type": "SimpleItem"
        }

    def _create_waypoint_item(self, route_terminal: RouteTerminal, command: int, do_jump_id: int, params_array: List[float]) -> Dict:
        """Tạo WAYPOINT mission item"""
        # Lấy altitude từ operating_altitude measurement (đang ở m)
        altitude_m = self._get_operating_altitude_from_route_terminal(route_terminal)
        # Chuyển đổi từ m sang ft cho QGroundControl
        altitude_ft = altitude_m
        
        # Lấy frame từ route_terminal.frame
        frame_id = self._get_frame_from_route_terminal(route_terminal)
        
        # Lấy altitude mode từ route_terminal (nếu có)
        altitude_mode = self._get_altitude_mode_from_route_terminal(route_terminal)
        
        # Lấy auto continue từ route_terminal (nếu có)
        auto_continue = self._get_auto_continue_from_route_terminal(route_terminal)
        
        # Xử lý tham số hold từ time_stops measurement
        hold_time_s = self._get_hold_time_from_terminal(route_terminal.terminal)
        
        # Đảm bảo params có đủ 7 giá trị
        params = self._ensure_params_length(params_array)
        
        # Cập nhật param1 (hold time) nếu có
        # self._update_waypoint_hold_param(params, route_terminal.terminal)
        
        return {
            "AMSLAltAboveTerrain": None,
            "Altitude": float(altitude_ft),  # Sử dụng altitude đã chuyển đổi sang ft
            "AltitudeMode": int(altitude_mode),
            "autoContinue": bool(auto_continue),
            "command": int(command),
            "doJumpId": int(do_jump_id),
            "frame": int(frame_id),
            "params": params,
            "type": "SimpleItem"
        }

    def _create_land_item(self, route_terminal: RouteTerminal, command: int, do_jump_id: int, params_array: List[float]) -> Dict:
        """Tạo LAND mission item"""
        # LAND command luôn có altitude = 0 (ground level)
        altitude_ft = 0.0
        
        # Lấy frame từ route_terminal.frame
        frame_id = self._get_frame_from_route_terminal(route_terminal)
        
        # Lấy altitude mode từ route_terminal (nếu có)
        altitude_mode = self._get_altitude_mode_from_route_terminal(route_terminal)
        
        # Lấy auto continue từ route_terminal (nếu có)
        auto_continue = self._get_auto_continue_from_route_terminal(route_terminal)
        
        # Đảm bảo params có đủ 7 giá trị
        params = []
        for i in range(7):
            if i < len(params_array) and params_array[i] is not None:
                params.append(float(params_array[i]))
            else:
                params.append(0.0)
        
        return {
            "AMSLAltAboveTerrain": None,
            "Altitude": float(altitude_ft),  # LAND luôn có altitude = 0
            "AltitudeMode": int(altitude_mode),
            "autoContinue": bool(auto_continue),
            "command": int(command),
            "doJumpId": int(do_jump_id),
            "frame": int(frame_id),
            "params": params,
            "type": "SimpleItem"
        }

    def _create_rtl_item(self, command: int, do_jump_id: int) -> Dict:
        """Tạo RTL mission item"""
        return {
            "AMSLAltAboveTerrain": None,
            "Altitude": 0.0,
            "AltitudeMode": 0,
            "autoContinue": True,
            "command": int(command),
            "doJumpId": int(do_jump_id),
            "frame": 0,  # MAV_FRAME_GLOBAL
            "params": [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
            "type": "SimpleItem"
        }

    def _get_altitude_mode_from_route_terminal(self, route_terminal: RouteTerminal) -> int:
        """Lấy altitude mode từ route terminal, default = 1 (Absolute)"""
        try:
            # Có thể lưu trong command_line hoặc measurement
            # Tạm thời dùng default
            return 1
        except:
            return 1

    def _get_auto_continue_from_route_terminal(self, route_terminal: RouteTerminal) -> bool:
        """Lấy auto continue từ route terminal, default = True"""
        try:
            # Có thể lưu trong command_line hoặc measurement
            # Tạm thời dùng default
            return True
        except:
            return True

    def _get_frame_from_route_terminal(self, route_terminal: RouteTerminal) -> int:
        """Lấy frame từ route_terminal.frame, fallback về 0 (GLOBAL) nếu không có"""
        try:
            frame_value = getattr(route_terminal, 'frame', None)
            logger.debug(f"DEBUG: _get_frame_from_route_terminal - route_terminal.id: {route_terminal.id}")
            logger.debug(f"DEBUG: _get_frame_from_route_terminal - frame_value: {frame_value} (type: {type(frame_value)})")
            
            if frame_value is not None:
                if isinstance(frame_value, dict):
                    # Format mới: {"id": "name"} hoặc format cũ: {"id_frame": "value"} hoặc {"FrameId": "value"}
                    logger.debug(f"DEBUG: frame_value là dict: {frame_value}")
                    
                    # Format mới: {"id": "name"}
                    if len(frame_value) == 1:
                        first_key = list(frame_value.keys())[0]
                        try:
                            frame_id = int(first_key)
                            logger.debug(f"DEBUG: Format mới - Tìm thấy frame ID: {frame_id}")
                        except (ValueError, TypeError):
                            logger.warning(f"Frame key không phải số: {first_key}, sử dụng default")
                            return 0
                    # Format cũ: {"id_frame": "value"} hoặc {"FrameId": "value"}
                    elif 'id_frame' in frame_value:
                        frame_id = int(frame_value['id_frame'])
                        logger.debug(f"DEBUG: Tìm thấy 'id_frame': {frame_id}")
                    elif 'FrameId' in frame_value:
                        frame_id = int(frame_value['FrameId'])
                        logger.debug(f"DEBUG: Tìm thấy 'FrameId': {frame_id}")
                    else:
                        # Lấy key đầu tiên nếu không có key chuẩn
                        first_key = list(frame_value.keys())[0]
                        frame_id = int(frame_value[first_key])
                        logger.debug(f"DEBUG: Sử dụng key đầu tiên '{first_key}': {frame_id}")
                    
                    # Validate frame ID
                    if frame_id >= 0:
                        # Sử dụng API để lấy tên frame
                        frame_name = self._get_frame_name_by_id(frame_id)
                        #print(f"Route terminal {route_terminal.id} có frame: {frame_id} ({frame_name})")
                        return frame_id
                    else:
                        logger.warning(f"Frame ID không hợp lệ: {frame_id}, sử dụng default")
                        return 0
                        
                elif isinstance(frame_value, (int, str)):
                    # Nếu là int hoặc string trực tiếp
                    frame_id = int(frame_value)
                    logger.debug(f"DEBUG: frame_value là {type(frame_value)}: {frame_id}")
                    if frame_id >= 0:
                        # Sử dụng API để lấy tên frame
                        frame_name = self._get_frame_name_by_id(frame_id)
                        #print(f"Route terminal {route_terminal.id} có frame: {frame_id} ({frame_name})")
                        return frame_id
                    else:
                        logger.warning(f"Frame ID không hợp lệ: {frame_id}, sử dụng default")
                        return 0
                else:
                    logger.warning(f"Frame value có type không mong đợi: {type(frame_value)}, sử dụng default")
                    return 0
            else:
                logger.warning(f"Route terminal {route_terminal.id} không có frame, sử dụng default MAV_FRAME_GLOBAL (0)")
                return 0
                
        except Exception as e:
            logger.warning(f"⚠️ Error parsing frame value: {frame_value}, sử dụng default MAV_FRAME_GLOBAL (0). Error: {e}")
            return 0
    
    def _create_custom_commands_from_command_line(self, route_terminals: List[RouteTerminal], start_do_jump_id: int) -> List[Dict[str, Any]]:
        """Tạo mission items cho các custom commands từ command_line với format mới"""
        custom_items = []
        do_jump_id = start_do_jump_id
        
        for route_terminal in route_terminals:
            if hasattr(route_terminal, 'command_line') and route_terminal.command_line:
                command_line_data = route_terminal.command_line
                
                # Mỗi route terminal chỉ chứa 1 command
                if isinstance(command_line_data, dict) and len(command_line_data) == 1:
                    # Lấy command ID và data
                    command_id_str = list(command_line_data.keys())[0]
                    cmd_data = command_line_data[command_id_str]
                    
                    if isinstance(cmd_data, dict) and len(cmd_data) == 1:
                        # Lấy command name và params array
                        command_name = list(cmd_data.keys())[0]
                        params_array = cmd_data[command_name]
                        
                        # Convert command ID về int
                        try:
                            command_number = int(command_id_str)
                        except (ValueError, TypeError):
                            continue
                        
                        # Tạo mission item với params array từ command_line
                        custom_items.append(
                            self._create_custom_mission_item_from_array(
                                route_terminal, command_number, do_jump_id, params_array
                            )
                        )
                        do_jump_id += 1
        
        return custom_items
    
    def _create_custom_mission_item_from_array(self, route_terminal: RouteTerminal, command: int, do_jump_id: int, params_array: List) -> Dict[str, Any]:
        """Tạo mission item cho custom command từ params array trong command_line"""
        # Lấy terminal để có coordinates
        terminal = route_terminal.terminal
        
        # Lấy frame từ model
        frame_id = self._get_frame_from_route_terminal(route_terminal)
        
        # Tạo mission item cơ bản với đầy đủ field bắt buộc
        mission_item = {
            "AMSLAltAboveTerrain": None,
            "Altitude": 0.0,
            "AltitudeMode": 0,  # Relative altitude - gắn cứng
            "autoContinue": True,  # gắn cứng
            "command": int(command),  # Đảm bảo luôn là int
            "doJumpId": int(do_jump_id),  # Đảm bảo luôn là int
            "frame": frame_id,  # Lấy frame ID từ model hoặc default
            "type": "SimpleItem"
        }
        
        # Xử lý params array từ command_line
        if isinstance(params_array, list) and len(params_array) >= 7:
            # Đảm bảo tất cả params đều là float, không có None
            processed_params = []
            for i, param in enumerate(params_array[:7]):
                if param is not None:
                    try:
                        processed_params.append(float(param))
                    except (ValueError, TypeError):
                        processed_params.append(0.0)
                else:
                    processed_params.append(0.0)  # Thay None bằng 0.0
            
            # Nếu là coordinate command, ghi đè coordinates từ terminal
            if self._is_coordinate_command(command, params_array):
                # LAND command luôn có altitude = 0
                if command == self.COMMAND_LAND:
                    altitude_ft = 0.0
                else:
                    # Lấy altitude từ operating_altitude measurement (đang ở m)
                    altitude_m = self._get_operating_altitude_from_route_terminal(route_terminal)
                    # Chuyển đổi từ m sang ft cho QGroundControl
                    altitude_ft = altitude_m
                
                mission_item["Altitude"] = float(altitude_ft)  # Đảm bảo luôn là float
                
                # Nếu là WAYPOINT command, xử lý tham số hold từ time_stops
                # if command == self.COMMAND_WAYPOINT:
                #     self._update_waypoint_hold_param(processed_params, terminal)
                
                # Ghi đè coordinates vào params[4-6]
                self._update_coordinate_params(processed_params, terminal, altitude_ft)
            
            mission_item["params"] = processed_params
            
        else:
            # Nếu params_array không đúng format, tạo params mặc định
            if self._is_coordinate_command(command, params_array):
                # LAND command luôn có altitude = 0
                if command == self.COMMAND_LAND:
                    altitude_ft = 0.0
                else:
                    # Lấy altitude từ operating_altitude measurement (đang ở m)
                    altitude_m = self._get_operating_altitude_from_route_terminal(route_terminal)
                    # Chuyển đổi từ m sang ft cho QGroundControl
                    altitude_ft = altitude_m
                
                mission_item["Altitude"] = float(altitude_ft)  # Đảm bảo luôn là float
                
                # Tạo params với coordinates
                if command == self.COMMAND_WAYPOINT:
                    # Tận dụng phương thức helper cho WAYPOINT
                    default_params = self._create_default_waypoint_params(terminal, route_terminal)
                    # Chuyển đổi altitude về ft
                    default_params[self.PARAM_INDEX['Z']] = float(altitude_ft)
                else:
                    # Các command khác (TAKEOFF, LAND)
                    default_params = self._create_coordinate_params(terminal, altitude_ft)
                    # Cập nhật coordinates
                    self._update_coordinate_params(default_params, terminal, altitude_ft)
                
                mission_item["params"] = default_params
            else:
                # Command không cần coordinates, tạo params mặc định
                mission_item["params"] = self._create_default_non_coordinate_params()
        
        return mission_item
    
    def _is_param_command(self, command: int) -> bool:
        """Kiểm tra xem command có cần tham số không"""
        # Các command cần tham số nhưng không phải coordinate command
        param_commands = [
            self.COMMAND_DO_SET_SERVO,      # 183 - cần param1, param2
            self.COMMAND_DO_CHANGE_SPEED,   # 178 - cần param1, param2
            self.COMMAND_SET_CAMERA_MODE,   # 530 - cần param1
            self.COMMAND_JUMP               # 177 - cần param1, param2
        ]
        return command in param_commands
    
    def _get_operating_altitude_from_route_terminal(self, route_terminal: RouteTerminal) -> float:
        """Lấy operating_altitude từ measurement của route_terminal"""
        try:
            # RouteTerminal không có field altitude, chỉ lấy từ measurement
            operating_altitude_measurement = route_terminal.get_numeric_value('operating_altitude',component=None, user_units='m')
            if operating_altitude_measurement:
                altitude_value = float(operating_altitude_measurement)
                logger.debug(f"Lấy altitude từ measurement: {altitude_value}")
                return altitude_value
            
            # Fallback: lấy từ params trong command_line (param7 = altitude)
            command_line = route_terminal.command_line or {}
            for command_id_str, command_data in command_line.items():
                params_array = list(command_data.values())[0]
                if len(params_array) >= 7 and params_array[6] is not None:
                    altitude_from_params = float(params_array[6])
                    logger.debug(f"Lấy altitude từ params[6]: {altitude_from_params}")
                    return altitude_from_params
            
            # Fallback 2: lấy từ params[2] nếu params[6] không có (một số commands dùng params[2] cho altitude)
            for command_id_str, command_data in command_line.items():
                params_array = list(command_data.values())[0]
                if len(params_array) >= 3 and params_array[2] is not None:
                    altitude_from_params = float(params_array[2])
                    logger.debug(f"Lấy altitude từ params[2]: {altitude_from_params}")
                    return altitude_from_params
            
            # Default altitude - gắn cứng
            logger.warning(f"Không tìm thấy altitude, dùng default: 50.0")
            return 50.0
        except (ValueError, AttributeError) as e:
            logger.warning(f"Error lấy altitude: {e}, dùng default: 50.0")
            return 50.0
    
    def _get_cruise_speed_from_route(self, route: Routes) -> float:
        """Lấy cruise_speed từ measurement của route terminal đầu tiên hoặc default"""
        default_cruise_speed = get_waypoint_speed()
        try:
            # Lấy route terminal đầu tiên
            first_route_terminal = route.route_terminals.first()
            if first_route_terminal:
                # Lấy cruise_speed từ measurement của route terminal đầu tiên
                cruise_speed_value = first_route_terminal.get_numeric_value('cruise_speed', component=None, user_units='m/s')
                if cruise_speed_value is not None:
                    return float(cruise_speed_value)
            
            # Default value - gắn cứng
            return default_cruise_speed
        except (ValueError, AttributeError):
            return default_cruise_speed
    
    def _get_home_position(self, route: Routes) -> List[float]:
        """Lấy home position từ drone terminal hoặc fallback về terminal đầu tiên của route"""
        
        # Ưu tiên 1: Lấy từ drone terminal (Device.terminal)
        if route and hasattr(route, 'devices') and route.devices.exists():
            # Tìm device đầu tiên có terminal
            for device in route.devices.all():
                if device.terminal:
                    return [
                        float(device.terminal.latitude),
                        float(device.terminal.longitude),
                        8.0  # altitude mặc định theo user sample (float) - gắn cứng
                    ]
        
        # Ưu tiên 2: Lấy từ terminal đầu tiên của route
        if route.route_terminals.exists():
            first_terminal = route.route_terminals.first().terminal
            return [
                float(first_terminal.latitude),
                float(first_terminal.longitude),
                8.0  # altitude mặc định theo user sample (float) - gắn cứng
            ]
        
        # Fallback: Tọa độ mặc định
        return [0.0, 0.0, 8.0]

    def _convert_ft_to_m(self, feet: float) -> float:
        """Chuyển đổi từ feet sang meters sử dụng convert_unit từ utils"""
        try:
            return convert_unit(feet, 'ft', 'm')
        except Exception as e:
            logger.warning(f"Không thể chuyển đổi ft sang m: {e}, dùng conversion factor cũ")
            return feet * 0.3048
    
    def _convert_m_to_ft(self, meters: float) -> float:
        """Chuyển đổi từ meters sang feet sử dụng convert_unit từ utils"""
        try:
            return convert_unit(meters, 'm', 'ft')
        except Exception as e:
            logger.warning(f"Không thể chuyển đổi m sang ft: {e}, dùng conversion factor cũ")
            return meters / 0.3048
    
    def _calculate_total_distance(self, terminals: List[Terminal]) -> float:
        """Tính tổng khoảng cách giữa các terminals liên tiếp"""
        if len(terminals) < 2:
            return 0.0
        
        total_distance = 0.0
        for i in range(len(terminals) - 1):
            try:
                lat1 = float(terminals[i].latitude)
                lon1 = float(terminals[i].longitude)
                lat2 = float(terminals[i + 1].latitude)
                lon2 = float(terminals[i + 1].longitude)
                
                # Tính khoảng cách đơn giản (có thể dùng thư viện geopy để chính xác hơn)
                distance = self._haversine_distance(lat1, lon1, lat2, lon2)
                total_distance += distance
            except (ValueError, TypeError):
                continue
        
        return total_distance
    
    def _haversine_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Tính khoảng cách giữa 2 điểm theo công thức Haversine (km)"""
        import math
        
        # Convert to radians
        lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
        
        # Haversine formula
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        c = 2 * math.asin(math.sqrt(a))
        
        # Radius of earth in kilometers
        r = 6371
        
        return c * r

    def test_mavlink_frames_api(self) -> Dict[str, Any]:
        """
        Test method để kiểm tra API integration
        
        Returns:
            Dict chứa thông tin test
        """
        try:
            frames_data = self._get_mavlink_frames_from_api()
            if frames_data:
                frames = frames_data.get('frames', [])
                categories = frames_data.get('categories', [])
                
                # Test một số frame cụ thể
                test_results = {}
                for frame_id in [0, 3, 5]:  # Test GLOBAL, GLOBAL_RELATIVE_ALT, GLOBAL_INT
                    frame_name = self._get_frame_name_by_id(frame_id)
                    test_results[f"frame_{frame_id}"] = frame_name
                
                return {
                    "success": True,
                    "total_frames": len(frames),
                    "categories": categories,
                    "test_results": test_results,
                    "sample_frames": frames[:3]  # 3 frame đầu tiên
                }
            else:
                return {
                    "success": False,
                    "error": "Không thể lấy data từ API"
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def test_special_commands_handling(self) -> Dict[str, Any]:
        """
        Test method để kiểm tra xử lý các commands đặc biệt
        
        Returns:
            Dict chứa thông tin test kết quả
        """
        try:
            test_results = {
                "coordinate_commands": [],
                "non_coordinate_commands": [],
                "command_parameters": {}
            }
            
            # Test coordinate commands
            coordinate_commands = [
                self.COMMAND_TAKEOFF,
                self.COMMAND_WAYPOINT,
                self.COMMAND_LAND,
                self.COMMAND_DO_SET_ROI_LOCATION,
                self.COMMAND_DO_REPOSITION
            ]
            
            for cmd in coordinate_commands:
                has_coordinates = self._is_coordinate_command(cmd)
                test_results["coordinate_commands"].append({
                    "command": cmd,
                    "name": self.COMMAND_DESCRIPTIONS.get(cmd, f"Command_{cmd}"),
                    "has_coordinates": has_coordinates
                })
            
            # Test non-coordinate commands
            non_coordinate_commands = [
                self.COMMAND_DO_SET_SERVO,
                self.COMMAND_DO_CHANGE_SPEED,
                self.COMMAND_SET_CAMERA_MODE,
                self.COMMAND_DO_SET_RELAY,
                self.COMMAND_DO_SET_PARAMETER
            ]
            
            for cmd in non_coordinate_commands:
                has_coordinates = self._is_coordinate_command(cmd)
                test_results["non_coordinate_commands"].append({
                    "command": cmd,
                    "name": self.COMMAND_DESCRIPTIONS.get(cmd, f"Command_{cmd}"),
                    "has_coordinates": has_coordinates
                })
            
            # Test command parameters patterns
            test_results["command_parameters"] = {
                "SET_SERVO": {
                    "params": ["servo_number", "pwm_value"],
                    "description": "Controls servo position via PWM"
                },
                "DO_CHANGE_SPEED": {
                    "params": ["speed_type", "speed_value"],
                    "description": "Changes vehicle speed"
                },
                "SET_CAMERA_MODE": {
                    "params": ["camera_mode"],
                    "description": "Sets camera mode (Image/Video/Survey)"
                },
                "DO_SET_RELAY": {
                    "params": ["relay_number", "relay_setting"],
                    "description": "Controls relay on/off"
                },
                "DO_MOUNT_CONTROL": {
                    "params": ["pitch", "roll", "yaw"],
                    "description": "Controls gimbal/mount angles"
                }
            }
            
            return {
                "success": True,
                "message": "Special commands handling test completed successfully",
                "total_coordinate_commands": len(coordinate_commands),
                "total_non_coordinate_commands": len(non_coordinate_commands),
                "test_results": test_results
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Error testing special commands: {str(e)}"
            }

