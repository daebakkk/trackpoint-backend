from django.contrib.auth import get_user_model
from rest_framework import serializers

from .models import Asset, Assignment, Staff

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
