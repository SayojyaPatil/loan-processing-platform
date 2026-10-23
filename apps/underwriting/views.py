from apps.loans.permissions import LoanAccess, visible_loans
from rest_framework import mixins, viewsets
from .models import Recommendation
from .serializers import RecommendationSerializer
class RecommendationViewSet(mixins.RetrieveModelMixin,mixins.ListModelMixin,viewsets.GenericViewSet):
    permission_classes=[LoanAccess]
    def get_queryset(self):
        return Recommendation.objects.filter(loan__in=visible_loans(self.request.user)).select_related('loan')
    serializer_class=RecommendationSerializer
    filterset_fields=['loan','decision']
