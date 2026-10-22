from rest_framework import mixins, viewsets
from .models import Recommendation
from .serializers import RecommendationSerializer
class RecommendationViewSet(mixins.RetrieveModelMixin,mixins.ListModelMixin,viewsets.GenericViewSet):
    queryset=Recommendation.objects.select_related('loan').all()
    serializer_class=RecommendationSerializer
    filterset_fields=['loan','decision']
