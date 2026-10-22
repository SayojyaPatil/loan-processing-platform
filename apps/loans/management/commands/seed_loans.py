from decimal import Decimal
from django.core.management.base import BaseCommand
from django.db import transaction
from apps.loans.models import LoanApplication
from apps.documents.models import LoanDocument

class Command(BaseCommand):
    help='Create simulated loan applications and documents for local testing.'
    def add_arguments(self, parser):
        parser.add_argument('--count', type=int, default=5000)
    def handle(self, *args, **opts):
        count=opts['count']
        batch=[]
        for i in range(count):
            batch.append(LoanApplication(
                applicant_name=f'Applicant {i}',
                applicant_email=f'applicant{i}@example.test',
                requested_amount=Decimal(10000 + (i % 90)*1000),
                purpose='home_improvement' if i % 2 else 'debt_consolidation',
            ))
        with transaction.atomic():
            loans=LoanApplication.objects.bulk_create(batch, batch_size=1000)
            docs=[LoanDocument(
                loan=loan, kind='paystub', filename=f'paystub-{i}.txt',
                text_content=f'Monthly income: ${4500 + (i%40)*150}. Monthly liabilities: ${900 + (i%12)*100}. Employment status: employed.'
            ) for i, loan in enumerate(loans)]
            LoanDocument.objects.bulk_create(docs, batch_size=1000)
        self.stdout.write(self.style.SUCCESS(f'Created {count} loans and {count} documents.'))
