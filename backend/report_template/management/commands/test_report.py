from django.core.management.base import BaseCommand
from report_template.utils import generate_report_template
from django.http import HttpRequest
from core.user.models import CoreUser
from print_format.services import PrintFormatService
from delivery.models import DeliveryOperation
import json


class Command(BaseCommand):
    help = "Test report generation"

    def handle(self, *args, **options):
        request = HttpRequest()
        request.user = CoreUser.objects.first()

        instance = DeliveryOperation.objects.first()
        order_data = PrintFormatService.get_print_format_data(instance, instance.order)

        response = generate_report_template(request, order_data, "pdf")
        self.stdout.write(str(response))
