
from django.shortcuts import get_object_or_404
from django.db.models import Count
from django.db import transaction

from rest_framework import viewsets, status
from rest_framework.exceptions import ValidationError
from rest_framework.decorators import action
from rest_framework.response import Response

from .permissions import LoanAccess, visible_loans
from .models import LoanApplication
from .serializers import LoanApplicationSerializer

from apps.processing.models import ProcessingJob
from apps.processing.tasks import process_loan


class LoanApplicationViewSet(viewsets.ModelViewSet):
    serializer_class = LoanApplicationSerializer
    permission_classes = [LoanAccess]

    filterset_fields = ['status', 'applicant_email']
    ordering_fields = ['created_at', 'requested_amount']

    def get_queryset(self):
        return (
            visible_loans(self.request.user)
            .annotate(document_count=Count('documents'))
            .order_by('-created_at', '-pk')
        )

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

    @action(detail=True, methods=['post'])
    def submit(self, request, pk=None):
        with transaction.atomic():
            # Return 404 if the loan does not exist or is not accessible.
            # Retain the row lock to prevent concurrent submissions.
            loan = get_object_or_404(
                visible_loans(request.user).select_for_update(),
                pk=pk,
            )

            if loan.status != LoanApplication.Status.DRAFT:
                raise ValidationError({
                    'detail': 'Only draft loans can be submitted.'
                })

            if not loan.documents.exists():
                raise ValidationError({
                    'detail': 'Upload at least one document first.'
                })

            job = ProcessingJob.objects.create(loan=loan)

            loan.status = LoanApplication.Status.SUBMITTED
            loan.save(update_fields=['status', 'updated_at'])

            # Enqueue processing after the database transaction commits.
            def enqueue():
                try:
                    result = process_loan.delay(str(job.id))

                    ProcessingJob.objects.filter(
                        pk=job.pk,
                        status=ProcessingJob.Status.QUEUED,
                    ).update(celery_task_id=result.id)

                except Exception:
                    ProcessingJob.objects.filter(
                        pk=job.pk
                    ).update(
                        status=ProcessingJob.Status.FAILED,
                        error='Queue unavailable',
                    )

                    LoanApplication.objects.filter(
                        pk=loan.pk,
                        status=LoanApplication.Status.SUBMITTED,
                    ).update(status=LoanApplication.Status.REVIEW)

            transaction.on_commit(enqueue)

        return Response(
            {
                'loan_id': str(loan.id),
                'job_id': str(job.id),
                'status': job.status,
            },
            status=status.HTTP_202_ACCEPTED,
        )
