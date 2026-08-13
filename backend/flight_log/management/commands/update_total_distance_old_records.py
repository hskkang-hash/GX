from django.core.management.base import BaseCommand
from flight_log.models import FlightLog
from delivery.models import DeliveryOperationItem


class Command(BaseCommand):
    help = 'Update total_distance measurement for old FlightLog records that have empty total_distance'

    def handle(self, *args, **options):
        flight_logs = FlightLog.objects.all()
        updated_count = 0
        skipped_count = 0
        error_count = 0

        self.stdout.write(f'Processing {flight_logs.count()} FlightLog records...')

        for flight_log in flight_logs:
            # Check if total_distance is already set
            existing_measurement = flight_log.get_measurement('total_distance')
            if existing_measurement:
                skipped_count += 1
                continue

            try:
                # Case 1: FlightLog has profile_drone
                if flight_log.profile_drone:
                    mission = flight_log.profile_drone.profile.mission
                    total_distance = mission.measurements.filter(measurement_type='total_distance').first()
                    if total_distance:
                        flight_log.set_measurement('total_distance', total_distance.get_formatted_value(None))
                        flight_log.save()
                        updated_count += 1
                        self.stdout.write(
                            self.style.SUCCESS(f'Updated FlightLog {flight_log.id} from profile_drone mission')
                        )
                    else:
                        self.stdout.write(
                            self.style.WARNING(f'FlightLog {flight_log.id}: No total_distance in mission')
                        )

                # Case 2: FlightLog has order_item
                elif flight_log.order_item:
                    delivery_operation_item = DeliveryOperationItem.objects.filter(
                        order_item=flight_log.order_item
                    ).first()
                    if delivery_operation_item:
                        route = delivery_operation_item.delivery_operation.route
                        total_distance = route.measurements.filter(measurement_type='total_distance').first()
                        if total_distance:
                            flight_log.set_measurement('total_distance', total_distance.get_formatted_value(None))
                            flight_log.save()
                            updated_count += 1
                            self.stdout.write(
                                self.style.SUCCESS(f'Updated FlightLog {flight_log.id} from order_item route')
                            )
                        else:
                            self.stdout.write(
                                self.style.WARNING(f'FlightLog {flight_log.id}: No total_distance in route')
                            )
                    else:
                        self.stdout.write(
                            self.style.WARNING(f'FlightLog {flight_log.id}: No DeliveryOperationItem found')
                        )
                else:
                    self.stdout.write(
                        self.style.WARNING(f'FlightLog {flight_log.id}: No profile_drone or order_item')
                    )

            except Exception as e:
                error_count += 1
                self.stdout.write(
                    self.style.ERROR(f'Error updating FlightLog {flight_log.id}: {str(e)}')
                )

        self.stdout.write(
            self.style.SUCCESS(
                f'\nCompleted! Updated: {updated_count}, Skipped (already has value): {skipped_count}, Errors: {error_count}'
            )
        )

