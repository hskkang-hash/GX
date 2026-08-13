from django.core.management.base import BaseCommand
from orders.models import Order, OrderAssignment, OrderAssignmentProcess, DeliveryEvent, OrderHistory, OrderStatus
from terminals.models import Routes, Terminal
from devices.models import Device
from django.utils import timezone
from datetime import timedelta

def get_intermediate_points(start_lat, start_lng, end_lat, end_lng, num_points):
    """
    Calculate intermediate points between two coordinates
    """
    points = []
    for i in range(num_points):
        # Calculate the fraction of the way through the journey
        fraction = (i + 1) / (num_points + 1)
        
        # Calculate intermediate point
        lat = start_lat + (end_lat - start_lat) * fraction
        lng = start_lng + (end_lng - start_lng) * fraction
        
        points.append((lat, lng))
    return points

class Command(BaseCommand):
    help = 'Generate delivery process for an order'

    def handle(self, *args, **kwargs):
        order_id = 83
        
        try:
            order = Order.objects.get(id=order_id)
        except Order.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'Order with ID {order_id} does not exist'))
            return
        
        # create order history from paid to verified
        OrderHistory.objects.create(
            order=order,
            action='paid',
            description="Order paid"
        )
        OrderHistory.objects.create(
            order=order,
            action='verified',
            description="Order verified"
        )

        # update order status
        order.status = OrderStatus.objects.get(code='awaiting_shipment')
        order.save()

        # Create 3 routes
        routes = []
        for i in range(3):
            route = Routes.objects.create(
                name=f"Route {i+1} for Order {order.order_code}",
                code=f"R{i+1}_{order.order_code}",
                description=f"Route {i+1} for delivery process",
                terminal_from=order.pickup_location,
                status='active'
            )
            routes.append(route)
            self.stdout.write(self.style.SUCCESS(f'Created route: {route.name}'))

        # Get a device for delivery
        device = Device.objects.first()
        if not device:
            self.stdout.write(self.style.ERROR('No device found. Please create a device first.'))
            return

        # Get some terminals for intermediate stops
        intermediate_terminals = Terminal.objects.filter(active=True).exclude(
            id__in=[order.pickup_location.id, order.delivery_terminal.id]
        )[:3]

        if len(intermediate_terminals) < 3:
            self.stdout.write(self.style.ERROR('Not enough active terminals found for intermediate stops'))
            return

        # Create OrderAssignment for each item
        for item in order.items.all():
            # Create assignment
            assignment = OrderAssignment.objects.create(
                order_item=item,
                route_id=routes[0],  # First route
                device=device,
                status='pending'
            )
            self.stdout.write(self.style.SUCCESS(f'Created assignment for item: {item.name}'))

            # Create process steps
            process_steps = [
                ('Pickup', 'pending'),
                ('In Transit', 'pending'),
                ('Delivery', 'pending')
            ]

            for step_name, status in process_steps:
                process = OrderAssignmentProcess.objects.create(
                    order_assignment=assignment,
                    step_name=step_name,
                    status=status
                )
                self.stdout.write(self.style.SUCCESS(f'Created process step: {step_name}'))

            # Get coordinates for pickup and delivery terminals
            pickup_lat = order.pickup_location.latitude
            pickup_lng = order.pickup_location.longitude
            delivery_lat = order.delivery_terminal.latitude
            delivery_lng = order.delivery_terminal.longitude

            # Calculate intermediate points
            intermediate_points = get_intermediate_points(
                pickup_lat, pickup_lng,
                delivery_lat, delivery_lng,
                7  # Increased to 7 points to accommodate all events
            )

            # Create delivery events with coordinates
            current_time = timezone.now()
            events = [
                ('pickup_started', 'Started pickup process', current_time, pickup_lat, pickup_lng, order.pickup_location),
                ('in_transit', 'Package in transit', current_time + timedelta(hours=1), *intermediate_points[0], None),
                ('arrived_at_terminal', f'Arrived at terminal {intermediate_terminals[0].name}', 
                 current_time + timedelta(hours=2), intermediate_terminals[0].latitude, intermediate_terminals[0].longitude, intermediate_terminals[0]),
                ('in_transit', 'Package in transit', current_time + timedelta(hours=2.5), *intermediate_points[2], None),
                ('arrived_at_terminal', f'Arrived at terminal {intermediate_terminals[1].name}', 
                 current_time + timedelta(hours=3), intermediate_terminals[1].latitude, intermediate_terminals[1].longitude, intermediate_terminals[1]),
                ('in_transit', 'Package in transit', current_time + timedelta(hours=3.5), *intermediate_points[4], None),
                ('arrived_at_terminal', f'Arrived at terminal {intermediate_terminals[2].name}', 
                 current_time + timedelta(hours=4), intermediate_terminals[2].latitude, intermediate_terminals[2].longitude, intermediate_terminals[2]),
                ('out_for_delivery', 'Out for delivery', current_time + timedelta(hours=4.5), *intermediate_points[5], None),
                ('delivery_attempted', 'Delivery attempted', current_time + timedelta(hours=5), delivery_lat, delivery_lng, order.delivery_terminal)
            ]

            # create history when order start to delivery
            OrderHistory.objects.create(
                order=order,
                action='started_delivery',
                description="Order started to delivery"
            )

            for event_type, description, event_time, lat, lng, terminal in events:
                event = DeliveryEvent.objects.create(
                    order_assignment=assignment,
                    event_type=event_type,
                    description=description,
                    event_time=event_time,
                    lat=lat,
                    lng=lng,
                    terminal_stop=terminal
                )
                # create history if terminal is not None
                if terminal:
                    OrderHistory.objects.create(
                        order=order,
                        action='arrived_at_terminal',
                        description=f'Package {item.code} arrived at terminal {terminal.name}'
                    )
                self.stdout.write(self.style.SUCCESS(
                    f'Created delivery event: {event_type} at coordinates ({lat}, {lng})' + 
                    (f' at terminal {terminal.name}' if terminal else '')
                ))

        self.stdout.write(self.style.SUCCESS(f'Successfully generated delivery process for order {order.order_code}')) 