from django.urls import include, path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .views import AssetViewSet, AssignmentViewSet, CustomTokenObtainPairView, MaintenanceTicketViewSet, MeView, RegisterView, StaffViewSet, UserSettingsView, health_check

app_name = 'core'

router = DefaultRouter()
router.register(r'staff', StaffViewSet, basename='staff')
router.register(r'assets', AssetViewSet, basename='asset')
router.register(r'assignments', AssignmentViewSet, basename='assignment')
router.register(r'maintenance-tickets', MaintenanceTicketViewSet, basename='maintenance-ticket')

urlpatterns = [
    path('health/', health_check, name='health_check'),
    path('auth/register/', RegisterView.as_view(), name='auth_register'),
    path('auth/token/', CustomTokenObtainPairView.as_view(), name='auth_token_obtain_pair'),
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='auth_token_refresh'),
    path('auth/me/', MeView.as_view(), name='auth_me'),
    path('settings/me/', UserSettingsView.as_view(), name='user_settings'),
    path('', include(router.urls)),
]
