from django.http import JsonResponse
from django.utils import timezone
from rest_framework import filters, permissions, status, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView

from .models import Asset, Assignment, Staff, MaintenanceTicket
from .serializers import (
    AssetSerializer,
    AssignmentSerializer,
    MaintenanceTicketSerializer,
    MeSerializer,
    RegisterSerializer,
    StaffSerializer,
    CustomTokenObtainPairSerializer,
)

def health_check(request):
    return JsonResponse({'status': 'ok'})


class StaffViewSet(viewsets.ModelViewSet):
    queryset = Staff.objects.all().order_by('name')
    serializer_class = StaffSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'office', 'job_title', 'staff_id']
    ordering_fields = ['name', 'office', 'job_title', 'staff_id']


class AssetViewSet(viewsets.ModelViewSet):
    queryset = Asset.objects.select_related('assigned_to').all().order_by('name')
    serializer_class = AssetSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'asset_id', 'location', 'status', 'assigned_to__name']
    ordering_fields = ['name', 'asset_id', 'location', 'status']

    def perform_create(self, serializer):
        asset = serializer.save()
        if not asset.assigned_to_id:
            return

        today = timezone.now().date()
        base_assignment_id = f"AS-{today:%Y%m%d}-{asset.asset_id}"
        assignment_id = base_assignment_id
        suffix = 1

        while Assignment.objects.filter(assignment_id=assignment_id).exists():
            suffix += 1
            assignment_id = f"{base_assignment_id}-{suffix}"

        Assignment.objects.create(
            assignment_id=assignment_id,
            asset=asset,
            assignee=asset.assigned_to,
            date_assigned=today,
            status='Active',
            approved_by='',
        )


class AssignmentViewSet(viewsets.ModelViewSet):
    queryset = Assignment.objects.select_related('asset', 'assignee').all().order_by('-date_assigned')
    serializer_class = AssignmentSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['assignment_id', 'status', 'approved_by', 'asset__name', 'assignee__name']
    ordering_fields = ['assignment_id', 'date_assigned', 'return_date', 'status']


class MaintenanceTicketViewSet(viewsets.ModelViewSet):
    queryset = MaintenanceTicket.objects.all().order_by('-created_at')
    serializer_class = MaintenanceTicketSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['ticket_id', 'lane', 'asset', 'task', 'owner', 'eta']
    ordering_fields = ['ticket_id', 'created_at', 'lane']


class RegisterView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(MeSerializer(user).data, status=status.HTTP_201_CREATED)


class MeView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return Response(MeSerializer(request.user).data, status=status.HTTP_200_OK)


class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer
