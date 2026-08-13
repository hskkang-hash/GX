# # Cập nhật measurements
# for field in ['capacity', 'voltage', 'current', 'power']:
#     if field in data and data[field]:
#         # Xóa measurement cũ nếu có
#         power_unit.measurements.filter(measurement_type=field).delete()
#         # Tạo measurement mới
#         Measurement.create_from_string(power_unit, field, data[field]) 