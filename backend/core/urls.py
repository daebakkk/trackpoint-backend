from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import AssetViewSet, AssignmentViewSet, StaffViewSet, health_check

app_name = 'core'

router = DefaultRouter()
router.register(r'staff', StaffViewSet, basename='staff')
router.register(r'assets', AssetViewSet, basename='asset')
router.register(r'assignments', AssignmentViewSet, basename='assignment')

urlpatterns = [
    path('health/', health_check, name='health_check'),
    path('', include(router.urls)),
]
