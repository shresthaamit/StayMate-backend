from rest_framework import generics
from rest_framework.permissions import AllowAny,IsAuthenticated
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .serializers import PhoneOTPGenerateSerializer
from .serializers import (
    RegisterSerializer,
    EmailTokenObtainPairSerializer,PhoneOTPVerifySerializer
)


class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]


class EmailLoginView(TokenObtainPairView):
    serializer_class = EmailTokenObtainPairSerializer

class PhoneOTPRequestView(APIView):

    permission_classes = [AllowAny]

    def post(self, request):

        serializer = PhoneOTPGenerateSerializer(
            data=request.data
        )

        if serializer.is_valid():
            serializer.save()

            return Response(
                {
                    "message": "OTP generated successfully. Check the Django terminal."
                },
                status=status.HTTP_200_OK
            )

        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )


class PhoneOTPVerifyView(APIView):

    permission_classes = [AllowAny]

    def post(self, request):

        serializer = PhoneOTPVerifySerializer(
            data=request.data
        )

        if serializer.is_valid():

            result = serializer.save()

            return Response(
                result,status=status.HTTP_200_OK
            )

        return Response(
            serializer.errors,status=status.HTTP_400_BAD_REQUEST
        )
class CurrentUserView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user

        return Response({
            "id": user.id,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "email": user.email,
            "mobile_number": user.profile.mobile_number,
        })