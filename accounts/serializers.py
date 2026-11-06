
from rest_framework import serializers
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
import secrets
from datetime import timedelta
from django.contrib.auth.hashers import check_password
from rest_framework_simplejwt.tokens import RefreshToken
from django.utils import timezone
from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import User
from django.contrib.auth import authenticate
from .models import UserProfile, PhoneOTP


class RegisterSerializer(serializers.ModelSerializer):

    mobile_number = serializers.CharField(
        max_length=15,
        write_only=True
    )

    password = serializers.CharField(
        write_only=True,
        min_length=8
    )

    class Meta:
        model = User
        fields = [
            'first_name',
            'last_name',
            'email',
            'mobile_number',
            'password'
        ]

    def validate_email(self, value):
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError(
                "An account with this email already exists."
            )
        return value.lower()

    def validate_mobile_number(self, value):
        if UserProfile.objects.filter(
            mobile_number=value
        ).exists():
            raise serializers.ValidationError(
                "This mobile number is already registered."
            )
        return value

    def create(self, validated_data):

        mobile_number = validated_data.pop('mobile_number')
        email = validated_data['email']

        user = User.objects.create_user(
            username=email,
            **validated_data
        )

        UserProfile.objects.create(
            user=user,
            mobile_number=mobile_number
        )

        return user

class EmailTokenObtainPairSerializer(TokenObtainPairSerializer):

    email = serializers.EmailField(write_only=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Remove the default username requirement
        self.fields.pop('username', None)

    def validate(self, attrs):

        email = attrs.get('email')
        password = attrs.get('password')

        user = authenticate(
            request=self.context.get('request'),
            username=email,
            password=password
        )

        if not user:
            raise AuthenticationFailed(
                'Invalid email or password.'
            )

        if not user.is_active:
            raise AuthenticationFailed(
                'This account is inactive.'
            )

        refresh = self.get_token(user)

        return {
            'refresh': str(refresh),
            'access': str(refresh.access_token)
        }


class PhoneOTPRequestSerializer(serializers.Serializer):

    mobile_number = serializers.CharField(max_length=15)

    def validate_mobile_number(self, value):

        if not UserProfile.objects.filter(
            mobile_number=value
        ).exists():
            raise serializers.ValidationError(
                "No account is registered with this mobile number."
            )

        return value


class PhoneOTPGenerateSerializer(serializers.Serializer):

    mobile_number = serializers.CharField(max_length=15)

    def validate_mobile_number(self, value):

        try:
            profile = UserProfile.objects.select_related(
                'user'
            ).get(mobile_number=value)
        except UserProfile.DoesNotExist:
            raise serializers.ValidationError(
                "No account found with this mobile number."
            )

        self.user = profile.user
        return value

    def create(self, validated_data):

        from .models import PhoneOTP

        otp = str(secrets.randbelow(900000) + 100000)

        PhoneOTP.objects.filter(
            user=self.user,
            is_used=False
        ).update(is_used=True)

        PhoneOTP.objects.create(
            user=self.user,
            code_hash=make_password(otp),
            expires_at=timezone.now() + timedelta(minutes=5)
        )

        # Development only: display OTP in Django terminal
        print(f"StayMate OTP for {self.user.username}: {otp}")

        return {
            "message": "OTP generated successfully."
        }


# -------------------------------
# VERIFY PHONE OTP
# -------------------------------

class PhoneOTPVerifySerializer(serializers.Serializer):

    mobile_number = serializers.CharField(max_length=15)

    otp = serializers.CharField(
        min_length=6,
        max_length=6,
        write_only=True
    )

    def validate(self, attrs):

        mobile_number = attrs.get('mobile_number')
        otp = attrs.get('otp')

        try:
            profile = UserProfile.objects.select_related(
                'user'
            ).get(mobile_number=mobile_number)

        except UserProfile.DoesNotExist:
            raise serializers.ValidationError(
                "Invalid mobile number or OTP."
            )

        user = profile.user

        if not user.is_active:
            raise AuthenticationFailed(
                "This account is inactive."
            )

        otp_record = PhoneOTP.objects.filter(
            user=user,
            is_used=False
        ).order_by('-created_at').first()

        if not otp_record:
            raise serializers.ValidationError(
                "No active OTP found. Request a new OTP."
            )

        if otp_record.attempts >= 5:
            otp_record.is_used = True
            otp_record.save(update_fields=['is_used'])

            raise serializers.ValidationError(
                "Too many attempts. Request a new OTP."
            )

        if timezone.now() > otp_record.expires_at:
            otp_record.is_used = True
            otp_record.save(update_fields=['is_used'])

            raise serializers.ValidationError(
                "OTP has expired. Request a new OTP."
            )

        if not check_password(otp, otp_record.code_hash):

            otp_record.attempts += 1

            if otp_record.attempts >= 5:
                otp_record.is_used = True

            otp_record.save(
                update_fields=['attempts', 'is_used']
            )

            raise serializers.ValidationError(
                "Incorrect OTP."
            )

        self.user = user
        self.otp_record = otp_record

        return attrs

    def create(self, validated_data):

        # Mark OTP as used
        self.otp_record.is_used = True
        self.otp_record.save(update_fields=['is_used'])

        # Generate JWT tokens
        refresh = RefreshToken.for_user(self.user)

        return {
            "message": "Phone login successful.",
            "refresh": str(refresh),
            "access": str(refresh.access_token)
        }
