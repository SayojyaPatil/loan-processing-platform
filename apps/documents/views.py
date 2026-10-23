from apps.loans.permissions import LoanAccess, visible_loans
from rest_framework import viewsets
from rest_framework.exceptions import ValidationError
from .models import LoanDocument
from .serializers import LoanDocumentSerializer
class LoanDocumentViewSet(viewsets.ModelViewSet):
    permission_classes=[LoanAccess]
    def get_queryset(self):
        return LoanDocument.objects.filter(loan__in=visible_loans(self.request.user)).select_related('loan')
    serializer_class=LoanDocumentSerializer
    filterset_fields=['loan','kind','processed']

    def perform_update(self, serializer):
        if serializer.instance.loan.status != 'draft':
            raise ValidationError('Only draft loan documents can be edited.')
        serializer.save()

    def perform_destroy(self, instance):
        if instance.loan.status != 'draft':
            raise ValidationError('Only draft loan documents can be deleted.')
        instance.delete()
