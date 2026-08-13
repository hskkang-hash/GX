from common.schema_measurable import MeasurableDynamicSchema
from flight_log.models import FlightLog


class FlightLogOutSchema(MeasurableDynamicSchema):
    class Meta:
        model = FlightLog
        model_fields = ['id', 'name', 'route_name', 'route_code', 'start_time', 'end_time', 'start_point', 'end_point', 'drone_state_prediction', 'drone_anomaly_prediction', 'drone', 'profile_drone', 'order_item', 'service_name']