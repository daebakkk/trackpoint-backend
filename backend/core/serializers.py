from django.contrib.auth import get_user_model
from django.db import IntegrityError
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .models import Asset, Assignment, Staff, MaintenanceTicket, UserSettings, LocationEvent, Notification

User = get_user_model()


class StaffSerializer(serializers.ModelSerializer):
    class Meta:
        model = Staff
        fields = ['id', 'staff_id', 'name', 'office', 'job_title']


class AssetSerializer(serializers.ModelSerializer):
    assigned_to_name = serializers.CharField(source='assigned_to.name', read_only=True)
    assigned_to_staff_id = serializers.CharField(source='assigned_to.staff_id', read_only=True)

    class Meta:
        model = Asset
        fields = [
            'id',
            'asset_id',
            'name',
            'location',
            'status',
            'created_at',
            'assigned_to',
            'assigned_to_name',
            'assigned_to_staff_id',
        ]


class AssignmentSerializer(serializers.ModelSerializer):
    asset_name = serializers.CharField(source='asset.name', read_only=True)
    asset_code = serializers.CharField(source='asset.asset_id', read_only=True)
    assignee_name = serializers.CharField(source='assignee.name', read_only=True)
    assignee_staff_id = serializers.CharField(source='assignee.staff_id', read_only=True)

    class Meta:
        model = Assignment
        fields = [
            'id',
            'assignment_id',
            'asset',
            'asset_name',
            'asset_code',
            'assignee',
            'assignee_name',
            'assignee_staff_id',
            'date_assigned',
            'return_date',
            'status',
            'approved_by',
        ]


class MaintenanceTicketSerializer(serializers.ModelSerializer):
    asset_ref = serializers.PrimaryKeyRelatedField(read_only=True)
    asset_name = serializers.CharField(source='asset_ref.name', read_only=True)
    asset_code = serializers.CharField(source='asset_ref.asset_id', read_only=True)
    asset_id = serializers.CharField(write_only=True, required=False)
    asset = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = MaintenanceTicket
        fields = [
            'id',
            'ticket_id',
            'lane',
            'asset_ref',
            'asset',
            'asset_name',
            'asset_code',
            'asset_id',
            'task',
            'owner',
            'eta',
            'status',
            'created_at',
            'completed_at',
        ]

    def validate(self, attrs):
        asset_id = attrs.get('asset_id')
        if self.instance is None and not asset_id:
            raise serializers.ValidationError({'asset_id': 'Asset ID is required.'})
        return attrs

    def _attach_asset(self, validated_data):
        asset_id = validated_data.pop('asset_id', None)
        if not asset_id:
            return
        asset = Asset.objects.filter(asset_id__iexact=asset_id).first()
        if not asset:
            raise serializers.ValidationError({'asset_id': f'Asset ID "{asset_id}" does not exist.'})
        validated_data['asset_ref'] = asset
        validated_data['asset'] = asset.name

    def create(self, validated_data):
        self._attach_asset(validated_data)
        return super().create(validated_data)

    def update(self, instance, validated_data):
        self._attach_asset(validated_data)
        return super().update(instance, validated_data)


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'password', 'first_name', 'last_name']

    def validate_email(self, value):
        if value and User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError('A user with this email already exists.')
        return value

    def create(self, validated_data):
        password = validated_data.pop('password')
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user


class MeSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name']


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    identifier = serializers.CharField(write_only=True)
    password = serializers.CharField(write_only=True)

    @classmethod
    def get_token(cls, user):
        return super().get_token(user)

    def validate(self, attrs):
        identifier = attrs.get('identifier', '').strip()
        password = attrs.get('password')

        user = User.objects.filter(email__iexact=identifier).first()
        if not user:
            user = User.objects.filter(username__iexact=identifier).first()

        if not user:
            raise serializers.ValidationError({'detail': 'Invalid email/ID or password.'})

        data = super().validate({
            self.username_field: user.get_username(),
            'password': password,
        })
        data['user'] = {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
        }
        return data


class UserSettingsSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(source='user.email', required=False)
    first_name = serializers.CharField(source='user.first_name', required=False, allow_blank=True)
    last_name = serializers.CharField(source='user.last_name', required=False, allow_blank=True)
    username = serializers.CharField(source='user.username', required=False, allow_blank=True)
    current_password = serializers.CharField(write_only=True, required=False, allow_blank=True)
    password = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = UserSettings
        fields = [
            'display_name',
            'maintenance_alerts',
            'assignment_updates',
            'weekly_summary',
            'dark_mode',
            'report_range',
            'email',
            'first_name',
            'last_name',
            'username',
            'current_password',
            'password',
        ]

    def update(self, instance, validated_data):
        user_data = validated_data.pop('user', {})
        current_password = validated_data.pop('current_password', None)
        password = validated_data.pop('password', None)
        for field, value in validated_data.items():
            setattr(instance, field, value)
        instance.save()

        if 'email' in user_data:
            instance.user.email = user_data['email']
        if 'username' in user_data:
            instance.user.username = user_data['username']
        if 'first_name' in user_data:
            instance.user.first_name = user_data['first_name']
        if 'last_name' in user_data:
            instance.user.last_name = user_data['last_name']
        if 'first_name' not in user_data and 'last_name' not in user_data:
            display_name = validated_data.get('display_name', instance.display_name)
            if display_name:
                parts = display_name.split()
                instance.user.first_name = parts[0]
                instance.user.last_name = ' '.join(parts[1:]) if len(parts) > 1 else ''
        if password:
            if current_password and not instance.user.check_password(current_password):
                raise serializers.ValidationError({'current_password': 'Current password is incorrect.'})
            if not current_password:
                raise serializers.ValidationError({'current_password': 'Current password is required.'})
            instance.user.set_password(password)
        if user_data or password:
            try:
                instance.user.save()
            except IntegrityError:
                raise serializers.ValidationError({'username': 'This username is already in use.'})
        return instance


class LocationEventSerializer(serializers.ModelSerializer):
    asset_name = serializers.CharField(source='asset.name', read_only=True)
    asset_code = serializers.CharField(source='asset.asset_id', read_only=True)
    asset_id = serializers.CharField(write_only=True, required=False)
    updated_by_name = serializers.CharField(source='updated_by.username', read_only=True)

    class Meta:
        model = LocationEvent
        fields = [
            'id',
            'asset',
            'asset_name',
            'asset_code',
            'asset_id',
            'location',
            'note',
            'created_at',
            'updated_by_name',
        ]

    def validate(self, attrs):
        asset_id = attrs.get('asset_id')
        if self.instance is None and not asset_id:
            raise serializers.ValidationError({'asset_id': 'Asset ID is required.'})
        return attrs

    def _attach_asset(self, validated_data):
        asset_id = validated_data.pop('asset_id', None)
        if not asset_id:
            return
        asset = Asset.objects.filter(asset_id__iexact=asset_id).first()
        if not asset:
            raise serializers.ValidationError({'asset_id': f'Asset ID "{asset_id}" does not exist.'})
        validated_data['asset'] = asset

    def create(self, validated_data):
        self._attach_asset(validated_data)
        return super().create(validated_data)

    def update(self, instance, validated_data):
        self._attach_asset(validated_data)
        return super().update(instance, validated_data)


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = [
            'id',
            'title',
            'message',
            'link',
            'event_type',
            'is_read',
            'created_at',
        ]
