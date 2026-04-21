from rest_framework import generics, permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from django.core.cache import cache
from .models import User, Follow
from .serializers import UserSerializer, RegisterSerializer, SendOTPSerializer, VerifyOTPSerializer
from .utils import create_and_send_otp, get_otp_key, hash_otp, increase_attempt, check_ip_rate_limit, get_client_ip
from apps.accounts.tasks import delete_unverified_user


class RegisterView(APIView):
    def post(self, request):
        ip = get_client_ip(request)
        allowed, _ = check_ip_rate_limit(ip, 5)

        if not allowed:
            return Response({"error": "Too many requests"}, status=429)

        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            user.is_active = False
            user.save()

            create_and_send_otp(user.email)

            delete_unverified_user.apply_async(
                args=(user.id,),
                countdown=300
            )

            return Response({"message": "User created. OTP sent."}, status=201)
        return Response(serializer.errors, status=400)

class SendOTPView(APIView):
    def post(self, request):
        ip = get_client_ip(request)
        allowed, reason = check_ip_rate_limit(ip, 10)

        if not allowed:
            return Response(
                {"error": "Too many requests. Try again later."},
                status=429
            )

        serializer = SendOTPSerializer(data=request.data)
        if serializer.is_valid():
            success = create_and_send_otp(serializer.validated_data["email"])
            if not success:
                return Response({"error": "Please wait before requesting another OTP"}, status=429)
            return Response({"message": "OTP sent"})
        return Response(serializer.errors, status=400)

class VerifyOTPView(APIView):
    def post(self, request):
        ip = get_client_ip(request)
        allowed, _ = check_ip_rate_limit(ip, 10)

        if not allowed:
            return Response({"error": "Too many requests"}, status=429)

        serializer = VerifyOTPSerializer(data=request.data)

        if serializer.is_valid():
            email = serializer.validated_data["email"]
            code = serializer.validated_data["code"]

            key = get_otp_key(email)
            stored_hash = cache.get(key)

            if not stored_hash:
                return Response({"error": "OTP expired or not found"}, status=400)

            if stored_hash != hash_otp(code):
                if not increase_attempt(email):
                    return Response({"error": "Too many attempts"}, status=429)
                return Response({"error": "Invalid OTP"}, status=400)

            cache.delete(f"otp_attempt:{email}")

            cache.delete(key)

            # activate user
            user = User.objects.get(email=email)
            user.is_active = True
            user.is_verified = True
            user.save()

            return Response({"message": "Email verified successfully"})

        return Response(serializer.errors, status=400)

class ProfileView(generics.RetrieveUpdateAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    lookup_field = "username"

@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def follow_toggle(request, username):
    target = User.objects.get(username=username)
    follow, created = Follow.objects.get_or_create(
        follower = request.user, following = target
    )

    if not created:
        follow.delete()
        return Response({"status": "unfollowed"})

    return Response({"status": "followed"}, status=status.HTTP_201_CREATED)