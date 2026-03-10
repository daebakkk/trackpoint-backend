from django.contrib.auth import get_user_model
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .models import Asset, Assignment, Staff, MaintenanceTicket

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
    class Meta:
        model = MaintenanceTicket
        fields = [
            'id',
            'ticket_id',
            'lane',
            'asset',
            'task',
            'owner',
            'eta',
            'created_at',
        ]


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
