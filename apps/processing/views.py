from apps.loans.permissions import LoanAccess, visible_loans
from rest_framework import mixins, viewsets
from .models import ProcessingJob
from .serializers import ProcessingJobSerializer
class ProcessingJobViewSet(mixins.RetrieveModelMixin,mixins.ListModelMixin,viewsets.GenericViewSet):
    permission_classes=[LoanAccess]
    def get_queryset(self):
        return ProcessingJob.objects.filter(loan__in=visible_loans(self.request.user)).select_related('loan')
    serializer_class=ProcessingJobSerializer
    filterset_fields=['loan','status']
