from django.urls import include, path
from rest_framework.routers import DefaultRouter
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from apps.loans.views import LoanApplicationViewSet
from apps.documents.views import LoanDocumentViewSet
from apps.processing.views import ProcessingJobViewSet
from apps.underwriting.views import RecommendationViewSet

router=DefaultRouter()
router.register('loans', LoanApplicationViewSet, basename='loan')
router.register('documents', LoanDocumentViewSet, basename='document')
router.register('processing-jobs', ProcessingJobViewSet, basename='processing-job')
router.register('recommendations', RecommendationViewSet, basename='recommendation')

urlpatterns=[
    path('api/', include(router.urls)),
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
]
