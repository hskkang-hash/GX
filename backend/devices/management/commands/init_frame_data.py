from django.core.management.base import BaseCommand
from django.db import transaction
from devices.models import FrameClass, FrameType
from core.multilanguage.request_handlers import create_model_with_translations, update_model_with_translations
from core.user.models import CoreUser, Language


class Command(BaseCommand):
    help = 'Initialize FrameClass and FrameType data based on common drone frame configurations'

    def handle(self, *args, **options):
        user = None
        # try:
        #     user = CoreUser.objects.filter(is_superuser=True).first()
        # except:
        #     pass

        with transaction.atomic():
            # Định nghĩa dữ liệu FRAME_CLASS
            # Dữ liệu dựa trên ArduPilot documentation: https://ardupilot.org/copter/docs/parameters.html#frame-class
            frame_classes_data = [
                {
                    "order": 1,
                    "code": "QUAD",
                    "name": "Quad",
                    "description": "Four-rotor drone configuration"
                },
                {
                    "order": 2,
                    "code": "HEXA",
                    "name": "Hexa",
                    "description": "Six-rotor drone configuration"
                },
                {
                    "order": 3,
                    "code": "OCTA",
                    "name": "Octa",
                    "description": "Eight-rotor drone configuration"
                },
                {
                    "order": 4,
                    "code": "OCTAQUAD",
                    "name": "OctaQuad",
                    "description": "OctaQuad configuration (8 rotors in quad arrangement)"
                },
                {
                    "order": 5,
                    "code": "Y6",
                    "name": "Y6",
                    "description": "Y6 configuration (6 rotors in Y arrangement)"
                },
                {
                    "order": 6,
                    "code": "HELI",
                    "name": "Heli",
                    "description": "Traditional helicopter configuration"
                },
                {
                    "order": 7,
                    "code": "TRI",
                    "name": "Tri",
                    "description": "Three-rotor copter configuration"
                },
                {
                    "order": 8,
                    "code": "SINGLE",
                    "name": "SingleCopter",
                    "description": "Single-rotor copter configuration"
                },
                {
                    "order": 9,
                    "code": "COAX",
                    "name": "CoaxCopter",
                    "description": "Coaxial copter configuration"
                },
                {
                    "order": 10,
                    "code": "BICOPTER",
                    "name": "BiCopter",
                    "description": "Two-rotor copter configuration"
                },
                {
                    "order": 11,
                    "code": "HELI_DUAL",
                    "name": "Heli_Dual",
                    "description": "Dual helicopter configuration"
                },
                {
                    "order": 12,
                    "code": "DODECAHEXA",
                    "name": "DodecaHexa",
                    "description": "DodecaHexa configuration (12 rotors)"
                },
                {
                    "order": 13,
                    "code": "HELIQUAD",
                    "name": "HeliQuad",
                    "description": "HeliQuad configuration (helicopter-quad hybrid)"
                },
                {
                    "order": 14,
                    "code": "DECA",
                    "name": "Deca",
                    "description": "Deca configuration (10 rotors)"
                },
            ]

            # Định nghĩa dữ liệu FRAME_TYPE theo từng FRAME_CLASS
            # Dữ liệu dựa trên ArduPilot documentation: https://ardupilot.org/copter/docs/parameters.html#frame-type
            # Note: FRAME_TYPE không được sử dụng cho Tri hoặc Traditional Helicopters
            frame_types_mapping = {
                "QUAD": [
                    {
                        "order": 0,
                        "code": "PLUS",
                        "name": "Plus",
                        "description": "Plus configuration for Quad"
                    },
                    {
                        "order": 1,
                        "code": "X",
                        "name": "X",
                        "description": "X configuration for Quad (default, most common)"
                    },
                    {
                        "order": 2,
                        "code": "V",
                        "name": "V",
                        "description": "V configuration for Quad"
                    },
                    {
                        "order": 3,
                        "code": "H",
                        "name": "H",
                        "description": "H configuration for Quad"
                    },
                    {
                        "order": 4,
                        "code": "V_TAIL",
                        "name": "V-Tail",
                        "description": "V-Tail configuration for Quad"
                    },
                    {
                        "order": 5,
                        "code": "A_TAIL",
                        "name": "A-Tail",
                        "description": "A-Tail configuration for Quad"
                    },
                    {
                        "order": 12,
                        "code": "BETAFLIGHTX",
                        "name": "BetaFlightX",
                        "description": "BetaFlightX configuration for Quad"
                    },
                    {
                        "order": 13,
                        "code": "DJIX",
                        "name": "DJIX",
                        "description": "DJIX configuration for Quad"
                    },
                    {
                        "order": 14,
                        "code": "CLOCKWISEX",
                        "name": "ClockwiseX",
                        "description": "ClockwiseX configuration for Quad"
                    },
                    {
                        "order": 15,
                        "code": "I",
                        "name": "I",
                        "description": "I configuration for Quad"
                    },
                    {
                        "order": 18,
                        "code": "BETAFLIGHTX_REVERSED",
                        "name": "BetaFlightXReversed",
                        "description": "BetaFlightXReversed configuration for Quad"
                    },
                    {
                        "order": 19,
                        "code": "Y4",
                        "name": "Y4",
                        "description": "Y4 configuration for Quad"
                    },
                ],
                "HEXA": [
                    {
                        "order": 0,
                        "code": "PLUS",
                        "name": "Plus",
                        "description": "Plus configuration for Hexa"
                    },
                    {
                        "order": 1,
                        "code": "X",
                        "name": "X",
                        "description": "X configuration for Hexa (default)"
                    },
                ],
                "OCTA": [
                    {
                        "order": 0,
                        "code": "PLUS",
                        "name": "Plus",
                        "description": "Plus configuration for Octa"
                    },
                    {
                        "order": 1,
                        "code": "X",
                        "name": "X",
                        "description": "X configuration for Octa (default)"
                    },
                ],
                "OCTAQUAD": [
                    {
                        "order": 0,
                        "code": "PLUS",
                        "name": "Plus",
                        "description": "Plus configuration for OctaQuad"
                    },
                    {
                        "order": 1,
                        "code": "X",
                        "name": "X",
                        "description": "X configuration for OctaQuad (default)"
                    },
                ],
                "Y6": [
                    {
                        "order": 10,
                        "code": "Y6B",
                        "name": "Y6B",
                        "description": "Y6B configuration (default)"
                    },
                    {
                        "order": 11,
                        "code": "Y6F",
                        "name": "Y6F",
                        "description": "Y6F configuration"
                    },
                ],
                "DODECAHEXA": [
                    {
                        "order": 0,
                        "code": "PLUS",
                        "name": "Plus",
                        "description": "Plus configuration for DodecaHexa"
                    },
                    {
                        "order": 1,
                        "code": "X",
                        "name": "X",
                        "description": "X configuration for DodecaHexa (default)"
                    },
                ],
                "DECA": [
                    {
                        "order": 0,
                        "code": "PLUS",
                        "name": "Plus",
                        "description": "Plus configuration for Deca"
                    },
                    {
                        "order": 1,
                        "code": "X",
                        "name": "X",
                        "description": "X configuration for Deca (default)"
                    },
                ],
                # FRAME_TYPE không được sử dụng cho các frame class sau:
                # HELI, TRI, SINGLE, COAX, BICOPTER, HELI_DUAL, HELIQUAD
                # (Theo ArduPilot: "Not used for Tri or Traditional Helicopters")
            }

            # Tạo hoặc cập nhật FrameClass
            frame_class_objects = {}
            for frame_class_data in frame_classes_data:
                # Tạo bản sao để không làm thay đổi dữ liệu gốc
                frame_class_data_copy = frame_class_data.copy()
                code = frame_class_data_copy.pop("code")
                existing_frame_class = FrameClass.objects.filter(code=code).first()
                
                if existing_frame_class:
                    if user:
                        frame_class_data_copy["modified_by"] = user
                    update_model_with_translations(existing_frame_class, frame_class_data_copy)
                    self.stdout.write(
                        self.style.SUCCESS(f'Updated FrameClass: {code}')
                    )
                    frame_class_objects[code] = existing_frame_class
                else:
                    if user:
                        frame_class_data_copy["created_by"] = user
                        frame_class_data_copy["modified_by"] = user
                    # Thêm lại code vào data khi tạo mới
                    frame_class_data_copy["code"] = code
                    frame_class_obj = create_model_with_translations(FrameClass, frame_class_data_copy)
                    self.stdout.write(
                        self.style.SUCCESS(f'Created FrameClass: {code}')
                    )
                    frame_class_objects[code] = frame_class_obj

            # Tạo hoặc cập nhật FrameType (riêng biệt với FrameClass)
            # Tạo code unique bằng cách kết hợp frame_class_code và frame_type_code
            for frame_class_code, frame_types_data in frame_types_mapping.items():
                for frame_type_data in frame_types_data:
                    # Tạo bản sao để không làm thay đổi dữ liệu gốc
                    frame_type_data_copy = frame_type_data.copy()
                    original_code = frame_type_data_copy.pop("code")
                    # Tạo code unique: FRAME_CLASS_CODE_FRAME_TYPE_CODE
                    unique_code = f"{frame_class_code}_{original_code}"
                    existing_frame_type = FrameType.objects.filter(code=unique_code).first()

                    if existing_frame_type:
                        if user:
                            frame_type_data_copy["modified_by"] = user
                        # Giữ nguyên code unique khi update
                        frame_type_data_copy["code"] = unique_code
                        update_model_with_translations(existing_frame_type, frame_type_data_copy)
                        self.stdout.write(
                            self.style.SUCCESS(
                                f'Updated FrameType: {unique_code} ({frame_class_code} - {original_code})'
                            )
                        )
                    else:
                        if user:
                            frame_type_data_copy["created_by"] = user
                            frame_type_data_copy["modified_by"] = user
                        # Set code unique khi tạo mới
                        frame_type_data_copy["code"] = unique_code
                        create_model_with_translations(FrameType, frame_type_data_copy)
                        self.stdout.write(
                            self.style.SUCCESS(
                                f'Created FrameType: {unique_code} ({frame_class_code} - {original_code})'
                            )
                        )

            self.stdout.write(
                self.style.SUCCESS('\nSuccessfully initialized FrameClass and FrameType data!')
            )

