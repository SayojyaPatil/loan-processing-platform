from rest_framework import viewsets
from .models import LoanDocument
from .serializers import LoanDocumentSerializer
class LoanDocumentViewSet(viewsets.ModelViewSet):
    queryset=LoanDocument.objects.select_related('loan').all()
    serializer_class=LoanDocumentSerializer
    filterset_fields=['loan','kind','processed']
