from django.http import JsonResponse
from django.utils import timezone
from django.utils.dateparse import parse_date, parse_datetime
from django.contrib.auth import get_user_model
from rest_framework import filters, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView

from .models import Asset, Assignment, Staff, MaintenanceTicket, UserSettings, LocationEvent, Notification
from .serializers import (
    AssetSerializer,
    AssignmentSerializer,
    MaintenanceTicketSerializer,
    MeSerializer,
    RegisterSerializer,
    StaffSerializer,
    CustomTokenObtainPairSerializer,
    UserSettingsSerializer,
    LocationEventSerializer,
    NotificationSerializer,
)

User = get_user_model()


def create_notifications_for_all(title, message='', link='', event_type='general'):
    users = User.objects.all()
    Notification.objects.bulk_create([
        Notification(
            user=user,
            title=title,
            message=message,
            link=link,
            event_type=event_type,
        )
        for user in users
    ])


def parse_eta_date(value):
    if not value:
        return None
    parsed = parse_datetime(value)
    if parsed:
        return parsed.date()
    return parse_date(value)


def maybe_send_due_notification(ticket):
    eta_date = parse_eta_date(ticket.eta)
    if not eta_date:
        return
    today = timezone.localdate()
    if eta_date == today:
        create_notifications_for_all(
            title=f"Ticket {ticket.ticket_id} due today",
            message=f"{ticket.asset_ref.name if ticket.asset_ref else ticket.asset} is due today.",
            link='/maintenance',
            event_type='ticket',
        )
    elif eta_date == today + timezone.timedelta(days=1):
        create_notifications_for_all(
            title=f"Ticket {ticket.ticket_id} due tomorrow",
            message=f"{ticket.asset_ref.name if ticket.asset_ref else ticket.asset} is due tomorrow.",
            link='/maintenance',
            event_type='ticket',
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

    def perform_update(self, serializer):
        previous_assigned_to_id = serializer.instance.assigned_to_id
        asset = serializer.save()
        if not asset.assigned_to_id or asset.assigned_to_id == previous_assigned_to_id:
            return
        self._create_assignment(asset)
        create_notifications_for_all(
            title=f"Asset assigned: {asset.asset_id}",
            message=f"{asset.name} assigned to {asset.assigned_to.name if asset.assigned_to else 'staff'}.",
            link='/assets',
            event_type='asset',
        )

    def perform_create(self, serializer):
        asset = serializer.save()
        create_notifications_for_all(
            title=f"New asset added: {asset.asset_id}",
            message=f"{asset.name} added to inventory.",
            link='/assets',
            event_type='asset',
        )
        if not asset.assigned_to_id:
            return
        self._create_assignment(asset)
        create_notifications_for_all(
            title=f"Asset assigned: {asset.asset_id}",
            message=f"{asset.name} assigned to {asset.assigned_to.name if asset.assigned_to else 'staff'}.",
            link='/assets',
            event_type='asset',
        )

    @staticmethod
    def _create_assignment(asset):
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

    def perform_update(self, serializer):
        previous_status = serializer.instance.status
        assignment = serializer.save()
        if assignment.status != 'Returned' or previous_status == 'Returned':
            return
        if assignment.return_date is None:
            assignment.return_date = timezone.now().date()
            assignment.save(update_fields=['return_date'])
        if assignment.asset and assignment.asset.assigned_to_id == assignment.assignee_id:
            assignment.asset.assigned_to = None
            assignment.asset.save(update_fields=['assigned_to'])
        create_notifications_for_all(
            title=f"Assignment {assignment.assignment_id} returned",
            message=f"{assignment.asset.name if assignment.asset else 'Asset'} is now unassigned.",
            link='/assignments',
            event_type='assignment',
        )

    def perform_create(self, serializer):
        assignment = serializer.save()
        create_notifications_for_all(
            title=f"New assignment {assignment.assignment_id}",
            message=f"{assignment.asset.name if assignment.asset else 'Asset'} assigned to {assignment.assignee.name if assignment.assignee else 'staff'}",
            link='/assignments',
            event_type='assignment',
        )


class MaintenanceTicketViewSet(viewsets.ModelViewSet):
    queryset = MaintenanceTicket.objects.all().order_by('-created_at')
    serializer_class = MaintenanceTicketSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['ticket_id', 'lane', 'asset', 'task', 'owner', 'eta', 'asset_ref__name', 'asset_ref__asset_id']
    ordering_fields = ['ticket_id', 'created_at', 'lane']

    def perform_update(self, serializer):
        previous_status = serializer.instance.status
        ticket = serializer.save()
        if ticket.status == 'Completed' and previous_status != 'Completed':
            if ticket.completed_at is None:
                ticket.completed_at = timezone.now()
                ticket.save(update_fields=['completed_at'])
            if ticket.asset_ref:
                ticket.asset_ref.status = 'Good condition'
                ticket.asset_ref.save(update_fields=['status'])
            create_notifications_for_all(
                title=f"Ticket {ticket.ticket_id} completed",
                message=f"{ticket.asset_ref.name if ticket.asset_ref else ticket.asset} marked resolved.",
                link='/maintenance',
                event_type='ticket',
            )
        if ticket.status != 'Completed':
            maybe_send_due_notification(ticket)

    def perform_create(self, serializer):
        ticket = serializer.save()
        create_notifications_for_all(
            title=f"New ticket {ticket.ticket_id}",
            message=f"{ticket.asset_ref.name if ticket.asset_ref else ticket.asset} added to {ticket.lane}.",
            link='/maintenance',
            event_type='ticket',
        )
        if ticket.status != 'Completed':
            maybe_send_due_notification(ticket)


class LocationEventViewSet(viewsets.ModelViewSet):
    queryset = LocationEvent.objects.select_related('asset', 'updated_by').all().order_by('-created_at')
    serializer_class = LocationEventSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['asset__name', 'asset__asset_id', 'location', 'note']
    ordering_fields = ['created_at']

    def perform_create(self, serializer):
        location_event = serializer.save(updated_by=self.request.user)
        asset = location_event.asset
        if asset.location != location_event.location:
            asset.location = location_event.location
            asset.save(update_fields=['location'])


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


class UserSettingsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        settings, created = UserSettings.objects.get_or_create(user=request.user)
        if created and not settings.display_name:
            settings.display_name = request.user.get_full_name() or request.user.username
            settings.save(update_fields=['display_name'])
        return Response(UserSettingsSerializer(settings).data, status=status.HTTP_200_OK)

    def patch(self, request):
        settings, _ = UserSettings.objects.get_or_create(user=request.user)
        data = request.data.copy()
        password = data.pop('password', None)
        current_password = data.pop('current_password', None)
        if password is not None:
            if not current_password:
                return Response({'current_password': ['Current password is required.']}, status=status.HTTP_400_BAD_REQUEST)
            if not request.user.check_password(current_password):
                return Response({'current_password': ['Current password is incorrect.']}, status=status.HTTP_400_BAD_REQUEST)
            request.user.set_password(password)
            request.user.save()
        serializer = UserSettingsSerializer(settings, data=data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(UserSettingsSerializer(settings).data, status=status.HTTP_200_OK)


class NotificationViewSet(viewsets.ModelViewSet):
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = Notification.objects.filter(user=self.request.user).order_by('-created_at')
        unread = self.request.query_params.get('unread')
        if unread in {'1', 'true', 'True'}:
            qs = qs.filter(is_read=False)
        return qs

    @action(detail=False, methods=['post'])
    def mark_all_read(self, request):
        Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
        return Response({'status': 'ok'}, status=status.HTTP_200_OK)
