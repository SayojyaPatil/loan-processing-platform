from django.db.models import Count
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import LoanApplication
from .serializers import LoanApplicationSerializer
from apps.processing.models import ProcessingJob
from apps.processing.tasks import process_loan

class LoanApplicationViewSet(viewsets.ModelViewSet):
    serializer_class=LoanApplicationSerializer
    filterset_fields=['status','applicant_email']
    ordering_fields=['created_at','requested_amount']
    def get_queryset(self):
        return LoanApplication.objects.annotate(document_count=Count('documents'))

    @action(detail=True, methods=['post'])
    def submit(self, request, pk=None):
        loan=self.get_object()
        if not loan.documents.exists():
            return Response({'detail':'Upload at least one document first.'}, status=status.HTTP_400_BAD_REQUEST)
        loan.status=LoanApplication.Status.SUBMITTED; loan.save(update_fields=['status','updated_at'])
        job=ProcessingJob.objects.create(loan=loan)
        async_result=process_loan.delay(str(job.id))
        job.celery_task_id=async_result.id; job.save(update_fields=['celery_task_id'])
        return Response({'loan_id':str(loan.id),'job_id':str(job.id),'status':job.status}, status=status.HTTP_202_ACCEPTED)
