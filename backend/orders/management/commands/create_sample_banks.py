from django.core.management.base import BaseCommand
from orders.models import Bank
from core.multilanguage.request_handlers import process_multilanguage_request, create_model_with_translations, update_model_with_translations, get_model_with_translations

class Command(BaseCommand):
    help = 'Generate 10 sample bank records'

    def handle(self, *args, **kwargs):
        # Sample bank data
        banks = [
            {'name':{'ko': 'Korea Development Bank', 'en': 'Korea Development Bank'}, 'code': 'KDB'},
            {'name': {'ko': 'Industrial Bank of Korea', 'en': 'Industrial Bank of Korea'}, 'code': 'IBK'},
            {'name': {'ko': 'Kookmin Bank', 'en': 'Kookmin Bank'}, 'code': 'KB'},
            {'name': {'ko': 'Shinhan Bank', 'en': 'Shinhan Bank'}, 'code': 'SHINHAN'},
            {'name': {'ko': 'Woori Bank', 'en': 'Woori Bank'}, 'code': 'WOORI'},
            {'name': {'ko': 'Hana Bank', 'en': 'Hana Bank'}, 'code': 'HANA'},
            {'name': {'ko': 'NH Bank', 'en': 'NH Bank'}, 'code': 'NH'},
            {'name': {'ko': 'Korea Exchange Bank', 'en': 'Korea Exchange Bank'}, 'code': 'KEB'},
            {'name': {'ko': 'Citibank Korea', 'en': 'Citibank Korea'}, 'code': 'CITI'},
            {'name': {'ko': 'Standard Chartered Bank Korea', 'en': 'Standard Chartered Bank Korea'}, 'code': 'SCB'}
        ]

        # Create bank records
        for bank_data in banks:
            existing_bank = Bank.objects.filter(code=bank_data['code']).first()
            if existing_bank:
               update_model_with_translations(existing_bank, bank_data)
            else:
                create_model_with_translations(Bank, bank_data)
            
            self.stdout.write(
                self.style.SUCCESS(f'Successfully created bank: {bank_data["name"]}')
            ) 