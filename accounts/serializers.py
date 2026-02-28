from rest_framework import serializers
from django.contrib.auth.models import User
from .models import BannedEmail
import re

class SignupSerializer(serializers.ModelSerializer):
    role = serializers.CharField(write_only=True)
    phone_number = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'password', 'role', 'phone_number']

    def validate_first_name(self, value):
        if not re.match(r'^[A-Za-z\s]+$', value):
            raise serializers.ValidationError("Name can only contain letters.")
        return value

    def validate_phone_number(self, value):

        if not re.match(r'^01[3-9]\d{8}$', value):
            raise serializers.ValidationError("Invalid Bangladeshi phone number.")
        return value

    def validate_email(self, value):
        if BannedEmail.objects.filter(email=value).exists():
            raise serializers.ValidationError("This email is blocked due to security policies.")
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Email already exists.")
        return value