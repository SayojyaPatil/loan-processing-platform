from rest_framework import mixins, viewsets
from .models import ProcessingJob
from .serializers import ProcessingJobSerializer
class ProcessingJobViewSet(mixins.RetrieveModelMixin,mixins.ListModelMixin,viewsets.GenericViewSet):
    queryset=ProcessingJob.objects.select_related('loan').all()
    serializer_class=ProcessingJobSerializer
    filterset_fields=['loan','status']
