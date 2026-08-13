import os
import sys
import django
from pytz import timezone


sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()
from django.db import transaction
from devices.models import DeviceType, ImageStabilization, MotorType, BatteryType, GNSSSystem, PackageType, Protocol, DeviceStatus
from core.user.models import CoreUser
from core.configuration.models import AdminConfig
from terminals.models import PurposeType, TerminalPurpose, TerminalType, Function
from core.multilanguage.request_handlers import process_multilanguage_request, create_model_with_translations, update_model_with_translations, get_model_with_translations
from core.user.models import Language

@transaction.atomic
def initialize_default_data():
    """
    Initialize default data for MotorType, BatteryType, GNSSSystem, and Protocol models with multilanguage support
    This function is safe to run multiple times - it will only update existing data without losing any information
    """
    user = None
    
    try:
        # Initialize Motor Types
        motor_types = [
            {
                "name": {
                    "en": "Brushed Motors",
                    "ko": "브러시 모터",
                    "th": "มอเตอร์แบบมีแปรงคาร์บอน"
                }, 
                "code": "BRUSHED", 
                "description": {
                    "en": "Motors with brushes for electrical contact",
                    "ko": "전기 접촉을 위한 브러시가 있는 모터",
                    "th": "มอเตอร์ที่มีแปรงคาร์บอนสำหรับการติดต่อไฟฟ้า"
                }
            },
            {
                "name": {
                    "en": "Brushless Motors",
                    "ko": "브러시리스 모터",
                    "th": "มอเตอร์แบบไร้แปรงคาร์บอน"
                }, 
                "code": "BRUSHLESS", 
                "description": {
                    "en": "Motors without brushes, more efficient and reliable",
                    "ko": "브러시가 없는 모터, 더 효율적이고 신뢰할 수 있음",
                    "th": "มอเตอร์ที่ไม่มีแปรงคาร์บอน มีประสิทธิภาพและความน่าเชื่อถือมากกว่า"
                }
            },
            {
                "name": {
                    "en": "Coreless Motors",
                    "ko": "코어리스 모터",
                    "th": "มอเตอร์แบบไร้แปรงคาร์บอน"
                }, 
                "code": "CORELESS", 
                "description": {
                    "en": "Lightweight motors without iron core",
                    "ko": "철심이 없는 경량 모터",
                    "th": "มอเตอร์น้ำหนักเบาที่ไม่มีแกนกลางเหล็ก"
                }
            },
            {
                "name": {
                    "en": "Outrunner Motors",
                    "ko": "아웃러너 모터",
                    "th": "มอเตอร์แบบเสื้อนนอกหมุน"
                }, 
                "code": "OUTRUNNER", 
                "description": {
                    "en": "Motor where the outer shell rotates around the internal windings",
                    "ko": "외부 쉘이 내부 권선 주위를 회전하는 모터",
                    "th": "มอเตอร์ที่เสื้อนนอกหมุนรอบขดลวดภายใน"
                }
            },
            {
                "name": {
                    "en": "Inrunner Motors",
                    "ko": "인러너 모터",
                    "th": "มอเตอร์แบบเสื้อนในหมุน"
                }, 
                "code": "INRUNNER", 
                "description": {
                    "en": "Motor where the internal rotor spins inside a fixed outer stator",
                    "ko": "내부 로터가 고정된 외부 고정자 내에서 회전하는 모터",
                    "th": "มอเตอร์ที่โรเตอร์ภายในหมุนอยู่ภายในสเตเตอร์ที่ติดตั้ง"
                }
            },
            {
                "name": {
                    "en": "Other",
                    "ko": "기타",
                    "th": "อื่นๆ"
                }, 
                "code": "OTHER", 
                "description": {
                    "en": "Other motor types not listed above",
                    "ko": "위에 나열되지 않은 기타 모터 유형",
                    "th": "มอเตอร์ประเภทอื่นๆ ที่ไม่ได้ระบุไว้ข้างต้น"
                }
            }
        ]
        
        for motor_type_data in motor_types:
            # Check if object exists by code (unique identifier)
            existing_obj = MotorType.objects.filter(code=motor_type_data["code"]).first()
            
            if existing_obj:
                # Update existing object - preserve created_by if exists
                if not existing_obj.created_by:
                    motor_type_data["created_by"] = user
                motor_type_data["modified_by"] = user
                update_model_with_translations(existing_obj, motor_type_data)
                print(f"Updated MotorType: {motor_type_data['code']}")
            else:
                # Create new object
                motor_type_data["created_by"] = user
                motor_type_data["modified_by"] = user
                create_model_with_translations(MotorType, motor_type_data)
                print(f"Created MotorType: {motor_type_data['code']}")
        
        # Initialize Battery Types
        battery_types = [
            {
                "name": {
                    "en": "Lithium Polymer (LiPo)",
                    "ko": "리튬 폴리머 (LiPo)",
                    "th": "ลิเธียมโพลีเมอร์ (LiPo)"
                }, 
                "code": "LIPO", 
                "description": {
                    "en": "High energy density, lightweight batteries commonly used in UAVs",
                    "ko": "에너지 밀도가 높고 가벼운 배터리로 UAV에 일반적으로 사용됨",
                    "th": "แบตเตอรี่ที่มีความหนาแน่นพลังงานสูงและน้ำหนักเบา ที่นิยมใช้ใน UAV"
                }
            },
            {
                "name": {
                    "en": "Lithium-Ion (Li-Ion)",
                    "ko": "리튬 이온 (Li-Ion)",
                    "th": "ลิเธียมไอออน (Li-Ion)"
                }, 
                "code": "LION", 
                "description": {
                    "en": "Rechargeable batteries with good energy density and low self-discharge",
                    "ko": "에너지 밀도가 좋고 자체 방전이 낮은 충전식 배터리",
                    "th": "แบตเตอรี่ไฟฟ้าชาร์จได้ที่มีความหนาแน่นพลังงานดีและการสูญเสียพลังงานต่ำ"
                }
            },
            {
                "name": {
                    "en": "Nickel-Metal Hydride (NiMH)",
                    "ko": "니켈 수소 (NiMH)",
                    "th": "นิกเกิล-เมทัลไฮดริด (NiMH)"
                }, 
                "code": "NIMH", 
                "description": {
                    "en": "Rechargeable batteries with moderate energy density",
                    "ko": "중간 정도의 에너지 밀도를 가진 충전식 배터리",
                    "th": "แบตเตอรี่ไฟฟ้าชาร์จได้ที่มีความหนาแน่นพลังงานปานกลาง"
                }
            },
            {
                "name": {
                    "en": "Lithium Iron Phosphate (LiFePO4)",
                    "ko": "리튬 인산철 (LiFePO4)",
                    "th": "ลิเธียมเหล็กฟอสเฟต (LiFePO4)"
                }, 
                "code": "LIFEPO4", 
                "description": {
                    "en": "Safer lithium batteries with longer cycle life",
                    "ko": "더 안전하고 수명이 긴 리튬 배터리",
                    "th": "แบตเตอรี่ลิเธียมที่ปลอดภัยกว่าและมีอายุการใช้งานยาวนาน"
                }
            },
            {
                "name": {
                    "en": "Hydrogen Fuel Cells",
                    "ko": "수소 연료 전지",
                    "th": "เซลล์เชื้อเพลิงไฮโดรเจน"
                }, 
                "code": "HYDROGEN", 
                "description": {
                    "en": "Fuel cells that generate electricity through hydrogen reaction",
                    "ko": "수소 반응을 통해 전기를 생성하는 연료 전지",
                    "th": "เซลล์เชื้อเพลิงที่สร้างไฟฟ้าจากปฏิกิริยาไฮโดรเจน"
                }
            },
            {
                "name": {
                    "en": "Other",
                    "ko": "기타",
                    "th": "อื่นๆ"
                }, 
                "code": "OTHER", 
                "description": {
                    "en": "Other battery types not listed above",
                    "ko": "위에 나열되지 않은 기타 배터리 유형",
                    "th": "แบตเตอรี่ประเภทอื่นๆ ที่ไม่ได้ระบุไว้ข้างต้น"
                }
            }
        ]
        
        for battery_type_data in battery_types:
            existing_obj = BatteryType.objects.filter(code=battery_type_data["code"]).first()
            if existing_obj:
                # Update existing object - preserve created_by if exists
                if not existing_obj.created_by:
                    battery_type_data["created_by"] = user
                battery_type_data["modified_by"] = user
                update_model_with_translations(existing_obj, battery_type_data)
                print(f"Updated BatteryType: {battery_type_data['code']}")
            else:
                battery_type_data["created_by"] = user
                battery_type_data["modified_by"] = user
                create_model_with_translations(BatteryType, battery_type_data)
                print(f"Created BatteryType: {battery_type_data['code']}")
        
        # Initialize GNSS Systems
        gnss_systems = [
            {
                "name": {
                    "en": "GPS",
                    "ko": "GPS",
                    "th": "GPS"
                }, 
                "description": {
                    "en": "Global Positioning System (USA)",
                    "ko": "글로벌 포지셔닝 시스템 (미국)",
                    "th": "ระบบการตำแหน่งทั่วโลก (สหรัฐอเมริกา)"
                }, 
                "version": "III"
            },
            {
                "name": {
                    "en": "GLONASS",
                    "ko": "GLONASS",
                    "th": "GLONASS"
                }, 
                "description": {
                    "en": "Global Navigation Satellite System (Russia)",
                    "ko": "글로벌 내비게이션 위성 시스템 (러시아)",
                    "th": "ระบบการตำแหน่งทั่วโลก (รัสเซีย)"
                }, 
                "version": "K"
            },
            {
                "name": {
                    "en": "Galileo",
                    "ko": "갈릴레오",
                    "th": "กาลิเลโอ"
                }, 
                "description": {
                    "en": "European global satellite-based navigation system",
                    "ko": "유럽 글로벌 위성 기반 내비게이션 시스템",
                    "th": "ระบบการตำแหน่งทั่วโลก (ยูโรป)"
                }, 
                "version": "FOC"
            },
            {
                "name": {
                    "en": "BeiDou",
                    "ko": "베이더우",
                    "th": "บีดู"
                }, 
                "description": {
                    "en": "Chinese satellite navigation system",
                    "ko": "중국 위성 내비게이션 시스템",
                    "th": "ระบบการตำแหน่งทั่วโลก (จีน)"
                }, 
                "version": "BDS-3"
            },
            {
                "name": {
                    "en": "QZSS",
                    "ko": "QZSS",
                    "th": "QZSS"
                }, 
                "description": {
                    "en": "Quasi-Zenith Satellite System (Japan)",
                    "ko": "준천정 위성 시스템 (일본)",
                    "th": "ระบบการตำแหน่งทั่วโลก (ญี่ปุ่น)"
                }, 
                "version": "J"
            },
            {
                "name": {
                    "en": "Other",
                    "ko": "기타",
                    "th": "ระบบการตำแหน่งทั่วโลก (อื่นๆ)"
                }, 
                "description": {
                    "en": "Other GNSS systems not listed above",
                    "ko": "위에 나열되지 않은 기타 GNSS 시스템",
                    "th": "ระบบการตำแหน่งทั่วโลก (อื่นๆ)"
                }, 
                "version": "N/A"
            }
        ]
        
        for gnss_system_data in gnss_systems:
            # Use exact name match for GNSS systems to avoid conflicts
            existing_obj = GNSSSystem.objects.filter(name=gnss_system_data["name"]["en"]).first()
            
            if existing_obj:
                # Update existing object - preserve created_by if exists
                if not existing_obj.created_by:
                    gnss_system_data["created_by"] = user
                gnss_system_data["modified_by"] = user
                update_model_with_translations(existing_obj, gnss_system_data)
                print(f"Updated GNSSSystem: {gnss_system_data['name']['en']}")
            else:
                gnss_system_data["created_by"] = user
                gnss_system_data["modified_by"] = user
                create_model_with_translations(GNSSSystem, gnss_system_data)
                print(f"Created GNSSSystem: {gnss_system_data['name']['en']}")
        
        # Initialize Protocols
        protocols = [
            # Flight Control Protocols
            {
                "name": {
                    "en": "SBUS",
                    "ko": "SBUS",
                    "th": "SBUS"
                }, 
                "type": {"en": "Flight Control", "ko": "비행 제어", "th": "การควบคุมการบิน"}, 
                "description": {
                    "en": "Serial Bus protocol for RC transmitters/receivers",
                    "ko": "RC 송신기/수신기용 시리얼 버스 프로토콜",
                    "th": "โปรโตคอลซีเรียลบัสสำหรับเครื่องส่ง/รับ RC"
                }
            },
            {
                "name": {
                    "en": "PPM",
                    "ko": "PPM",
                    "th": "PPM"
                }, 
                "type": {"en": "Flight Control", "ko": "비행 제어", "th": "การควบคุมการบิน"}, 
                "description": {
                    "en": "Pulse Position Modulation for RC control",
                    "ko": "RC 제어를 위한 펄스 위치 변조",
                    "th": "การมอดูเลตตำแหน่งพัลส์สำหรับการควบคุม RC"
                }
            },
            {
                "name": {
                    "en": "PWM",
                    "ko": "PWM",
                    "th": "PWM"
                }, 
                "type": {"en": "Flight Control", "ko": "비행 제어", "th": "การควบคุมการบิน"}, 
                "description": {
                    "en": "Pulse Width Modulation for motor control",
                    "ko": "모터 제어를 위한 펄스 폭 변조",
                    "th": "การมอดูเลตความกว้างพัลส์สำหรับการควบคุมมอเตอร์"
                }
            },
            {
                "name": {
                    "en": "CRSF",
                    "ko": "CRSF",
                    "th": "CRSF"
                }, 
                "type": {"en": "Flight Control", "ko": "비행 제어", "th": "การควบคุมการบิน"}, 
                "description": {
                    "en": "TBS Crossfire protocol with low latency",
                    "ko": "TBS Crossfire 프로토콜로 낮은 지연 시간",
                    "th": "โปรโตคอล TBS Crossfire ที่มีความหน่วงต่ำ"
                }
            },
            
            # Telemetry & Ground Station Protocols
            {
                "name": {
                    "en": "MAVLink",
                    "ko": "MAVLink",
                    "th": "MAVLink"
                }, 
                "type": {"en": "Telemetry & Ground Station", "ko": "텔레메트리 & 지상국", "th": "การสื่อสารระหว่างโดรนและพื้นฐานของโดรน"}, 
                "description": {
                    "en": "Micro Air Vehicle Link protocol for drone communications",
                    "ko": "드론 통신을 위한 Micro Air Vehicle Link 프로토콜",
                    "th": "โปรโตคอล Micro Air Vehicle Link สำหรับการสื่อสารของโดรน"
                }
            },
            {
                "name": {
                    "en": "DroneCAn",
                    "ko": "DroneCAn",
                    "th": "DroneCAn"
                }, 
                "type": {"en": "Telemetry & Ground Station", "ko": "텔레메트리 & 지상국", "th": "การสื่อสารระหว่างโดรนและพื้นฐานของโดรน"}, 
                "description": {
                    "en": "Open data bus standard for drone communications",
                    "ko": "드론 통신을 위한 Open data bus 표준",
                    "th": "มาตรฐานโอเพ่นดาตาบัสสำหรับการสื่อสารของโดรน"
                }
            },
            {
                "name": {
                    "en": "FrSky Smart Port",
                    "ko": "FrSky 스마트 포트",
                    "th": "FrSky Smart Port"
                }, 
                "type": {"en": "Telemetry & Ground Station", "ko": "텔레메트리 & 지상국", "th": "การสื่อสารระหว่างโดรนและพื้นฐานของโดรน"}, 
                "description": {
                    "en": "Digital telemetry protocol for RC systems",
                    "ko": "RC 시스템을 위한 디지털 텔레메트리 프로토콜",
                    "th": "โปรโตคอลเทเลเมตรี่ดิจิทัลสำหรับระบบ RC"
                }
            },
            {
                "name": {
                    "en": "F.Port",
                    "ko": "F.Port",
                    "th": "F.Port"
                }, 
                "type": {"en": "Telemetry & Ground Station", "ko": "텔레메트리 & 지상국", "th": "การสื่อสารระหว่างโดรนและพื้นฐานของโดรน"},   
                "description": {
                    "en": "Combined SBUS and Smart Port protocol",
                    "ko": "SBUS와 Smart Port 프로토콜을 결합한 프로토콜",
                    "th": "โปรโตคอลที่รวม SBUS และ Smart Port เข้าด้วยกัน"
                }
            },
            
            # Sensor & Peripheral Communication
            {
                "name": {
                    "en": "I2C",
                    "ko": "I2C",
                    "th": "I2C"
                }, 
                "type": {"en": "Sensor & Peripheral", "ko": "센서 & 주변 장치", "th": "เซนเซอร์ & อุปกรณ์ข้างเคียง"}, 
                "description": {
                    "en": "Inter-Integrated Circuit for connecting sensors",
                    "ko": "센서 연결을 위한 Inter-Integrated Circuit",
                    "th": "Inter-Integrated Circuit สำหรับการเชื่อมต่อเซนเซอร์"
                }
            },
            {
                "name": {
                    "en": "SPI",
                    "ko": "SPI",
                    "th": "SPI"
                }, 
                "type": {"en": "Sensor & Peripheral", "ko": "센서 & 주변 장치", "th": "เซนเซอร์ & อุปกรณ์ข้างเคียง"}, 
                "description": {
                    "en": "Serial Peripheral Interface for high-speed sensors",
                    "ko": "고속 센서를 위한 Serial Peripheral Interface",
                    "th": "Serial Peripheral Interface สำหรับเซนเซอร์ความเร็วสูง"
                }
            },
            {
                "name": {
                    "en": "UART",
                    "ko": "UART",
                    "th": "UART"
                }, 
                "type": {"en": "Sensor & Peripheral", "ko": "센서 & 주변 장치", "th": "เซนเซอร์ & อุปกรณ์ข้างเคียง"}, 
                "description": {
                    "en": "Universal Asynchronous Receiver/Transmitter for serial communication",
                    "ko": "직렬 통신을 위한 전체 비동기 수신기/송신기",
                    "th": "Universal Asynchronous Receiver/Transmitter สำหรับการสื่อสารแบบซีเรียล"
                }
            },
            {
                "name": {
                    "en": "CAN",
                    "ko": "CAN",
                    "th": "CAN"
                }, 
                "type": {"en": "Sensor & Peripheral", "ko": "센서 & 주변 장치", "th": "เซนเซอร์ & อุปกรณ์ข้างเคียง"}, 
                "description": {
                    "en": "Controller Area Network for robust messaging",
                    "ko": "강력한 메시지 전송을 위한 Controller Area Network",
                    "th": "Controller Area Network สำหรับการส่งข้อความที่แข็งแรง"
                }
            },
            
            # Video & Data Link Protocols
            {
                "name": {
                    "en": "RTSP",
                    "ko": "RTSP",
                    "th": "RTSP"
                }, 
                "type": {"en": "Video & Data Link", "ko": "비디오 & 데이터 링크", "th": "ลิงค์ข้อมูลวิดีโอ"}, 
                "description": {
                    "en": "Real Time Streaming Protocol for video streaming",
                    "ko": "비디오 스트리밍을 위한 Real Time Streaming Protocol",
                    "th": "Real Time Streaming Protocol สำหรับการสตรีมวิดีโอ"
                }
            },
            {
                "name": {
                    "en": "UDP Video Stream",
                    "ko": "UDP 비디오 스트림",
                    "th": "UDP สตรีมวิดีโอ"
                }, 
                "type": {"en": "Video & Data Link", "ko": "비디오 & 데이터 링크", "th": "ลิงค์ข้อมูลวิดีโอ"}, 
                "description": {
                    "en": "User Datagram Protocol for video streaming",
                    "ko": "비디오 스트리밍을 위한 User Datagram Protocol",
                    "th": "User Datagram Protocol สำหรับการสตรีมวิดีโอ"
                }
            },
            {
                "name": {
                    "en": "DJI OcuSync",
                    "ko": "DJI OcuSync",
                    "th": "DJI OcuSync"
                }, 
                "type": {"en": "Video & Data Link", "ko": "비디오 & 데이터 링크", "th": "ลิงค์ข้อมูลวิดีโอ"}, 
                "description": {
                    "en": "DJI's proprietary video transmission technology",
                    "ko": "DJI의 전용 비디오 전송 기술",
                    "th": "เทคโนโลยีการส่งวิดีโอเฉพาะของ DJI"
                }
            },
            {
                "name": {
                    "en": "DJI Lightbridge",
                    "ko": "DJI Lightbridge",
                    "th": "DJI Lightbridge"
                }, 
                "type": {"en": "Video & Data Link", "ko": "비디오 & 데이터 링크", "th": "ลิงค์ข้อมูลวิดีโอ"}, 
                "description": {
                    "en": "DJI's digital video downlink technology",
                    "ko": "DJI의 디지털 비디오 다운링크 기술",
                    "th": "เทคโนโลยีดาวน์ลิงค์วิดีโอดิจิทัลของ DJI"
                }
            },
            
            # Other types
            {
                "name": {
                    "en": "Other",
                    "ko": "기타",
                    "th": "อื่นๆ"
                }, 
                "type": {"en": "Other", "ko": "기타", "th": "อื่นๆ"}, 
                "description": {
                    "en": "Other protocols not listed above",
                    "ko": "위에 나열되지 않은 다른 프로토콜",
                    "th": "โปรโตคอลประเภทอื่นๆ ที่ไม่ได้ระบุไว้ข้างต้น"
                }
            }
        ]
        
        for protocol_data in protocols:
            # Use exact name and type match for protocols
            existing_obj = Protocol.objects.filter(name=protocol_data["name"]["en"], type=protocol_data["type"]["en"]).first()
            
            if existing_obj:
                # Update existing object - preserve created_by if exists
                if not existing_obj.created_by:
                    protocol_data["created_by"] = user
                protocol_data["modified_by"] = user
                update_model_with_translations(existing_obj, protocol_data)
                print(f"Updated Protocol: {protocol_data['name']['en']} ({protocol_data['type']['en']})")
            else:
                protocol_data["created_by"] = user
                protocol_data["modified_by"] = user
                create_model_with_translations(Protocol, protocol_data)
                print(f"Created Protocol: {protocol_data['name']['en']} ({protocol_data['type']['en']})")
        
        # Initialize Image Stabilization  
        image_stabilizations = [
            {
                "name": {
                    "en": "Not Applicable",
                    "ko": "해당 없음",
                    "th": "ไม่สามารถใช้งานได้"
                }, 
                "description": {
                    "en": "Not Applicable",
                    "ko": "해당 없음",
                    "th": "ไม่สามารถใช้งานได้"
                }
            },
            {
                "name": {
                    "en": "None",
                    "ko": "없음",
                    "th": "ไม่มี"
                }, 
                "description": {
                    "en": "None",
                    "ko": "없음",
                    "th": "ไม่มี"
                }
            },
            {
                "name": {
                    "en": "Basic (Internal)",
                    "ko": "기본 (내부)",
                    "th": "พื้นฐาน (ภายใน)"
                }, 
                "description": {
                    "en": "Basic (Internal)",
                    "ko": "기본 (내부)",
                    "th": "พื้นฐาน (ภายใน)"
                }
            },
            {
                "name": {
                    "en": "Digital (EIS)",
                    "ko": "디지털 (EIS)",
                    "th": "ดิจิตอล (EIS)"
                }, 
                "description": {
                    "en": "Digital (EIS)",
                    "ko": "디지털 (EIS)",
                    "th": "ดิจิตอล (EIS)"
                }
            },
            {
                "name": {
                    "en": "Optical (OIS)",
                    "ko": "광학식 (OIS)",
                    "th": "ออปติกอล (OIS)"
                }, 
                "description": {
                    "en": "Optical (OIS)",
                    "ko": "광학식 (OIS)",
                    "th": "ออปติกอล (OIS)"
                }
            },
            {
                "name": {
                    "en": "Gimbal (Mechanical)",
                    "ko": "짐벌 (기계식)",
                    "th": "จิมบอล (กลไก)"
                }, 
                "description": {
                    "en": "Gimbal (Mechanical)",
                    "ko": "짐벌 (기계식)",
                    "th": "จิมบอล (กลไก)"
                }
            }
        ]

        for stabilization_data in image_stabilizations:
            # Use exact name match for image stabilization
            existing_obj = ImageStabilization.objects.filter(name=stabilization_data["name"]["en"]).first()
            
            if existing_obj:
                # Update existing object - preserve created_by if exists
                if not existing_obj.created_by:
                    stabilization_data["created_by"] = user
                stabilization_data["modified_by"] = user
                update_model_with_translations(existing_obj, stabilization_data)
                print(f"Updated ImageStabilization: {stabilization_data['name']['en']}")
            else:
                stabilization_data["created_by"] = user
                stabilization_data["modified_by"] = user
                create_model_with_translations(ImageStabilization, stabilization_data)
                print(f"Created ImageStabilization: {stabilization_data['name']['en']}")
        
        # Initialize Package Type
        package_types = [
            {
                "name": {
                    "en": "Poly Mailer",
                    "ko": "폴리 메일러",
                    "th": "ซองพลาสติกส่งสินค้า"
                }, 
                "description": {
                    "en": "Poly Mailer",
                    "ko": "폴리 메일러",
                    "th": "ซองพลาสติกส่งสินค้า"
                }
            },
            {
                "name": {
                    "en": "Bubble Mailer",
                    "ko": "버블 메일러",
                    "th": "ซองบับเบิลส่งสินค้า"
                }, 
                "description": {
                    "en": "Bubble Mailer",
                    "ko": "버블 메일러",
                    "th": "ซองบับเบิลส่งสินค้า"
                }
            },
            {
                "name": {
                    "en": "Carton Box",
                    "ko": "카톤 박스",
                    "th": "กล่องกระดาษ"
                }, 
                "description": {
                    "en": "Carton Box",
                    "ko": "카톤 박스",
                    "th": "กล่องกระดาษ"
                }
            },
            {
                "name": {
                    "en": "Envelope",
                    "ko": "봉투",
                    "th": "ซองจดหมาย"
                }, 
                "description": {
                    "en": "Envelope",
                    "ko": "봉투",
                    "th": "ซองจดหมาย"
                }
            },
            {
                "name": {
                    "en": "Tube",
                    "ko": "튜브",
                    "th": "ท่อกระบอก"
                }, 
                "description": {
                    "en": "Tube",
                    "ko": "튜브",
                    "th": "ท่อกระบอก"
                }
            },
            {
                "name": {
                    "en": "Wooden Crate",
                    "ko": "목재 상자",
                    "th": "ลังไม้"
                }, 
                "description": {
                    "en": "Wooden Crate",
                    "ko": "목재 상자",
                    "th": "ลังไม้"
                }
            },
            {
                "name": {
                    "en": "Plastic Box",
                    "ko": "플라스틱 상자",  
                    "th": "กล่องพลาสติก"
                }, 
                "description": {
                    "en": "Plastic Box",
                    "ko": "플라스틱 상자",
                    "th": "กล่องพลาสติก"
                }
            }
        ]
        
        for package_type_data in package_types:
            # Use exact name match for package types
            existing_obj = PackageType.objects.filter(name=package_type_data["name"]["en"]).first()
            
            if existing_obj:
                # Update existing object - preserve created_by if exists
                if not existing_obj.created_by:
                    package_type_data["created_by"] = user
                package_type_data["modified_by"] = user
                update_model_with_translations(existing_obj, package_type_data)
                print(f"Updated PackageType: {package_type_data['name']['en']}")
            else:
                package_type_data["created_by"] = user
                package_type_data["modified_by"] = user
                create_model_with_translations(PackageType, package_type_data)
                print(f"Created PackageType: {package_type_data['name']['en']}")

        device_types = [
            {
                "name": {
                    "en": "Drone",
                    "ko": "드론",
                    "th": "โดรน"
                }, 
                "description": {
                    "en": "Drone",
                    "ko": "드론",
                    "th": "โดรน"
                }
            },
            {
                "name": {
                    "en": "Robot",
                    "ko": "로봇",
                    "th": "หุ่นยนต์"
                }, 
                "description": {
                    "en": "Robot",
                    "ko": "로봇",
                    "th": "หุ่นยนต์"
                }
            },
            {
                "name": {
                    "en": "Other",
                    "ko": "기타",
                    "th": "อื่น"
                }, 
                "description": {
                    "en": "Other",
                    "ko": "기타",
                    "th": "อื่น"
                }
            },
            {
                "name": {
                    "en": "Vehicle",
                    "ko": "차량",
                    "th": "ยานพาหนะ"
                }, 
                "description": {
                    "en": "Vehicle",
                    "ko": "차량",
                    "th": "ยานพาหนะ"
                }
            }
        ]
        
        for device_type_data in device_types:
            # Use exact name match for device types
            existing_obj = DeviceType.objects.filter(name=device_type_data["name"]["en"]).first()
            
            if existing_obj:
                # Update existing object - preserve created_by if exists
                if not existing_obj.created_by:
                    device_type_data["created_by"] = user
                device_type_data["modified_by"] = user
                update_model_with_translations(existing_obj, device_type_data)
                print(f"Updated DeviceType: {device_type_data['name']['en']}")
            else:
                device_type_data["created_by"] = user
                device_type_data["modified_by"] = user
                create_model_with_translations(DeviceType, device_type_data)
                print(f"Created DeviceType: {device_type_data['name']['en']}")
        
        terminal_types = [
            {
                "name": {
                    "en": "Repair Station",
                    "ko": "수리 스테이션",
                    "th": "สถานีซ่อมบำรุง"
                }, 
                "description": {
                    "en": "Repair Station",
                    "ko": "수리 스테이션",
                    "th": "สถานีซ่อมบำรุง"
                },
                "code": "REPAIR_STATION"
            },
            {
                "name": {
                    "en": "Docking Station",
                    "ko": "도킹 스테이션",
                    "th": "สถานีเชื่อมต่อ"
                }, 
                "description": {
                    "en": "Docking Station",
                    "ko": "도킹 스테이션",
                    "th": "สถานีเชื่อมต่อ"
                },
                "code": "DOCKING_STATION"
            },
            {
                "name": {
                    "en": "Transit Point",
                    "ko": "중계 지점",
                    "th": "จุดส่งต่อ"
                }, 
                "description": {
                    "en": "Transit Point",
                    "ko": "중계 지점",
                    "th": "จุดส่งต่อ"
                },
                "code": "TRANSIT_POINT"
            },
            {
                "name": {
                    "en": "Warehouse",
                    "ko": "창고",
                    "th": "คลังสินค้า"
                }, 
                "description": {
                    "en": "Warehouse",
                    "ko": "창고",
                    "th": "คลังสินค้า"
                },
                "code": "WAREHOUSE"
            },
            {
                "name": {
                    "en": "Temp",
                    "ko": "임시",
                    "th": "ชั่วคราว"
                }, 
                "description": {
                    "en": "Temp Terminal",
                    "ko": "임시 터미널",
                    "th": "เทอร์มินัลชั่วคราว"
                },
                "code": "TEMP"
            },
            {
                "name": {
                    "en": "DeliverySpot",
                    "ko": "배달점 ",
                    "th": "จุดจัดส่ง"
                }, 
                "description": {
                    "en": "DeliverySpot",
                    "ko": "배달점",
                    "th": "จุดจัดส่ง"
                },
                "code": "DELIVERY_SPOT"
            },
            {
                "name": {
                    "en": "Terminal",
                    "ko": "배달거점",
                    "th": "เทอร์มินัล"
                }, 
                "description": {
                    "en": "Terminal",
                    "ko": "배달거점",
                    "th": "เทอร์มินัล"
                },
                "code": "TERMINAL"
            },
            {
                "name": {
                    "en": "Delivery Hub",
                    "ko": "배달거점",
                    "th": "ศูนย์กระจายสินค้า"
                }, 
                "description": {
                    "en": "Delivery Hub",
                    "ko": "배달거점",
                    "th": "ศูนย์กระจายสินค้า"
                },
                "code": "DELIVERY_HUB"
            },
            {
                "name": {
                    "en": "Infrastructure",
                    "ko": "인프라",
                    "th": "โครงสร้างพื้นฐาน"
                }, 
                "description": {
                    "en": "Infrastructure",
                    "ko": "인프라",
                    "th": "โครงสร้างพื้นฐาน"
                },
                "code": "INFRASTRUCTURE"
            },
        ]
        
        for terminal_type_data in terminal_types:
            existing_obj = TerminalType.objects.filter(code=terminal_type_data["code"]).first()
            
            if existing_obj:
                # Update existing object - preserve created_by if exists
                if not existing_obj.created_by:
                    terminal_type_data["created_by"] = user
                terminal_type_data["modified_by"] = user
                update_model_with_translations(existing_obj, terminal_type_data)
                print(f"Updated TerminalType: {terminal_type_data['code']}")
            else:
                terminal_type_data["created_by"] = user
                terminal_type_data["modified_by"] = user
                create_model_with_translations(TerminalType, terminal_type_data)
                print(f"Created TerminalType: {terminal_type_data['code']}")

        # Initialize Functions (replacing old InfrastructureType, TerminalBaseType, DockingStationType)
        functions = [
            # Infrastructure Functions
            {
                "name": {
                    "en": "Charging System",
                    "ko": "충전시스템",
                    "th": "ระบบชาร์จไฟ"
                },
                "code": "CHARGING_SYSTEM",
                "function_type": "infrastructure"
            },
            {
                "name": {
                    "en": "Control Vehicle",
                    "ko": "관제차량",
                    "th": "ยานพาหนะควบคุม"
                },
                "code": "CONTROL_VEHICLE",
                "function_type": "infrastructure"
            },
            {
                "name": {
                    "en": "Hangar",
                    "ko": "격납고",
                    "th": "โรงเก็บเครื่องบิน"
                },
                "code": "HANGAR",
                "function_type": "infrastructure"
            },
            {
                "name": {
                    "en": "Repair Facility",
                    "ko": "수리시설",
                    "th": "โรงซ่อมบำรุง"
                },
                "code": "REPAIR_FACILITY",
                "function_type": "infrastructure"
            },
            
            # Delivery Hub Functions (previously Terminal Base Types)
            {
                "name": {
                    "en": "Ground",
                    "ko": "지상",
                    "th": "พื้นดิน"
                },
                "code": "GROUND",
                "function_type": "delivery_hub"
            },
            {
                "name": {
                    "en": "Rooftop",
                    "ko": "옥상",
                    "th": "หลังคา"
                },
                "code": "ROOFTOP",
                "function_type": "delivery_hub"
            },
            {
                "name": {
                    "en": "Other",
                    "ko": "기타",
                    "th": "อื่นๆ"
                },
                "code": "OTHER",
                "function_type": "delivery_hub"
            },
            
            # Docking Station Functions
            {
                "name": {
                    "en": "Mobile",
                    "ko": "이동형",
                    "th": "เคลื่อนที่ได้"
                },
                "code": "MOBILE",
                "function_type": "docking_station"
            },
            {
                "name": {
                    "en": "Fixed",
                    "ko": "고정형",
                    "th": "ติดตั้งถาวร"
                },
                "code": "FIXED",
                "function_type": "docking_station"
            }
        ]
        
        for function_data in functions:
            existing_obj = Function.objects.filter(code=function_data["code"], function_type=function_data["function_type"]).first()
            if existing_obj:
                # Update existing object - preserve created_by if exists
                if not existing_obj.created_by:
                    function_data["created_by"] = user
                function_data["modified_by"] = user
                update_model_with_translations(existing_obj, function_data)
                print(f"Updated Function: {function_data['code']} ({function_data['function_type']})")
            else:
                function_data["created_by"] = user
                function_data["modified_by"] = user
                create_model_with_translations(Function, function_data)
                print(f"Created Function: {function_data['code']} ({function_data['function_type']})")

        terminal_purposes = [
            {
                "name": {
                    "en": "Drones",
                    "ko": "드론용",
                    "th": "สำหรับโดรน"
                },
                "code": "DRONE"
            },
            {
                "name": {
                    "en": "Robots",
                    "ko": "로봇용",
                    "th": "สำหรับหุ่นยนต์"
                },
                "code": "ROBOT"
            },
            {
                "name": {
                    "en": "Common",
                    "ko": "공용",
                    "th": "ทั่วไป"
                },
                "code": "ALL"
            }
        ]
        for terminal_purpose_data in terminal_purposes:
            existing_obj = TerminalPurpose.objects.filter(code=terminal_purpose_data["code"]).first()
            if existing_obj:
                # Update existing object - preserve created_by if exists
                if not existing_obj.created_by:
                    terminal_purpose_data["created_by"] = user
                terminal_purpose_data["modified_by"] = user
                update_model_with_translations(existing_obj, terminal_purpose_data)
                print(f"Updated TerminalPurpose: {terminal_purpose_data['code']}")
            else:
                terminal_purpose_data["created_by"] = user
                terminal_purpose_data["modified_by"] = user
                create_model_with_translations(TerminalPurpose, terminal_purpose_data)
                print(f"Created TerminalPurpose: {terminal_purpose_data['code']}")

        purpose_types = [
            {
                "name": {
                    "en": "Charging",
                    "ko": "충전용",
                    "th": "สำหรับชาร์จ"
                },
                "code": "CHARGING"
            },
            {
                "name": {
                    "en": "Repairing",
                    "ko": "수리용",
                    "th": "สำหรับซ่อมแซม"
                },
                "code": "REPAIRING"
            },
            {
                "name": {
                    "en": "Storing",
                    "ko": "보관용",
                    "th": "สำหรับเก็บรักษา"
                },
                "code": "STORING"
            },
        ]
        for purpose_type_data in purpose_types:
            existing_obj = PurposeType.objects.filter(code=purpose_type_data["code"]).first()
            if existing_obj:
                # Update existing object - preserve created_by if exists
                if not existing_obj.created_by:
                    purpose_type_data["created_by"] = user
                purpose_type_data["modified_by"] = user
                update_model_with_translations(existing_obj, purpose_type_data)
                print(f"Updated PurposeType: {purpose_type_data['code']}")
            else:
                purpose_type_data["created_by"] = user
                purpose_type_data["modified_by"] = user
                create_model_with_translations(PurposeType, purpose_type_data)
                print(f"Created PurposeType: {purpose_type_data['code']}")
        
        # Initialize AdminConfig
        config = {
            'name':'Add more packages',
            'description':'Add more packages',
            'is_active':False,
            'settings':{
                    "value": False,
                    "true_value": "true",
                    "description": "Allow or disallow group use.",
                    "false_value": "false"
                }

        }
        existing_obj = AdminConfig.objects.filter(name='Add more packages').first()
        if existing_obj:
            # Update existing config - preserve created_by if exists
            if not existing_obj.created_by:
                config["created_by"] = user
            config["modified_by"] = user
            update_model_with_translations(existing_obj, config)
            print("Updated AdminConfig: Add more packages")
        else:
            config["created_by"] = user
            config["modified_by"] = user
            create_model_with_translations(AdminConfig, config)
            print("Created AdminConfig: Add more packages")
        
        # Initialize DeviceStatus
        device_statuses = [
            {
                "name": {
                    "en": "Active",
                    "ko": "활성화",
                    "th": "เปิดใช้งาน"
                },
                "code": "available"
            },
            {
                "name": {
                    "en": "On mission",
                    "ko": "임무중",
                    "th": "ในภารกิจ"
                },
                "code": "on_mission"
            },
            {
                "name": {
                    "en": "Inactive",
                    "ko": "비활성화",
                    "th": "ปิดการใช้งาน"
                },
                "code": "inactive"
            },
            {
                "name": {
                    "en": "Warning",
                    "ko": "경고",
                    "th": "คำเตือน"
                },
                "code": "warning"
            },
            {
                "name": {
                    "en": "Return",
                    "ko": "귀환",
                    "th": "คืนสินค้า"
                },
                "code": "return"
            }
        ]
        for device_status_data in device_statuses:
            existing_obj = DeviceStatus.objects.filter(code=device_status_data["code"]).first()
            if existing_obj:
                # Update existing object - preserve created_by if exists
                if not existing_obj.created_by:
                    device_status_data["created_by"] = user
                device_status_data["modified_by"] = user
                update_model_with_translations(existing_obj, device_status_data)
                print(f"Updated DeviceStatus: {device_status_data['code']}")
            else:
                device_status_data["created_by"] = user
                device_status_data["modified_by"] = user
                create_model_with_translations(DeviceStatus, device_status_data)
                print(f"Created DeviceStatus: {device_status_data['code']}")

        print("Default data has been initialized successfully with multilanguage support")
        print("All existing data has been preserved and updated where necessary")
        
    except Exception as e:
        print(f"Error during initialization: {str(e)}")
        # Transaction will automatically rollback on exception
        raise

initialize_default_data()