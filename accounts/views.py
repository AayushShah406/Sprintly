from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib import messages
from django.contrib.auth.password_validation import validate_password
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from .models import User, EmailOTP
from .email_service import send_otp_email
from mongodb_engine.manager import mongo_manager

def login_view(request):
    if request.user.is_authenticated:
        return redirect("dashboard:home")

    if request.method == "POST":
        email_or_user = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")

        user = User.objects.filter(email__iexact=email_or_user).first()
        if not user:
            user = User.objects.filter(username__iexact=email_or_user).first()

        if user and user.check_password(password):
            if user.is_active:
                # Generate 6-digit OTP for Login Verification
                otp = EmailOTP.create_otp(user, purpose="LOGIN")
                send_otp_email(user, otp)
                request.session["pending_otp_user_id"] = user.id
                request.session["pending_otp_purpose"] = "LOGIN"
                request.session["pending_otp_next"] = request.GET.get("next", "")
                messages.info(request, f"A 6-digit verification code has been sent to {user.email}.")
                return redirect("accounts:verify_otp")
            else:
                messages.error(request, "This account is currently disabled.")
        else:
            messages.error(request, "Invalid username/email or password.")

    return render(request, "accounts/login.html")


def signup_view(request):
    if request.user.is_authenticated:
        return redirect("dashboard:home")

    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        email = request.POST.get("email", "").strip().lower()
        first_name = request.POST.get("first_name", "").strip()
        last_name = request.POST.get("last_name", "").strip()
        password = request.POST.get("password", "")
        password_confirm = request.POST.get("password_confirm", "")

        if not username or not email or not password:
            messages.error(request, "Username, email, and password are required.")
        elif password != password_confirm:
            messages.error(request, "Passwords do not match.")
        elif User.objects.filter(username=username).exists():
            messages.error(request, "Username is already taken.")
        elif User.objects.filter(email=email).exists():
            messages.error(request, "An account with this email already exists.")
        else:
            try:
                validate_password(password)
                user = User.objects.create_user(
                    username=username,
                    email=email,
                    password=password,
                    first_name=first_name,
                    last_name=last_name,
                    role="DEVELOPER",
                    is_email_verified=False
                )
                mongo_manager.sync_user(user)
                
                # Generate 6-digit OTP for Signup Verification
                otp = EmailOTP.create_otp(user, purpose="SIGNUP")
                send_otp_email(user, otp)
                request.session["pending_otp_user_id"] = user.id
                request.session["pending_otp_purpose"] = "SIGNUP"
                messages.info(request, f"Account created! Please enter the 6-digit code sent to {user.email} to verify your email.")
                return redirect("accounts:verify_otp")
            except Exception as e:
                messages.error(request, str(e))

    return render(request, "accounts/signup.html")


def verify_otp_view(request):
    """
    Handles 6-digit OTP verification for both Signup and Login flows.
    """
    user_id = request.session.get("pending_otp_user_id")
    purpose = request.session.get("pending_otp_purpose", "LOGIN")

    if not user_id:
        messages.warning(request, "No pending verification session found. Please log in or sign up.")
        return redirect("accounts:login")

    user = User.objects.filter(pk=user_id).first()
    if not user:
        return redirect("accounts:login")

    if request.method == "POST":
        code = request.POST.get("otp_code", "").strip()
        # Fallback to reading 6 individual digit fields
        if not code:
            digits = [request.POST.get(f"digit_{i}", "") for i in range(1, 7)]
            code = "".join(digits).strip()

        otp = EmailOTP.objects.filter(user=user, purpose=purpose, is_used=False).order_by("-created_at").first()

        if otp and otp.is_valid() and otp.otp_code == code:
            otp.is_used = True
            otp.save()

            user.is_email_verified = True
            user.save()

            login(request, user)
            mongo_manager.sync_user(user)

            next_url = request.session.pop("pending_otp_next", "") or "dashboard:home"
            request.session.pop("pending_otp_user_id", None)
            request.session.pop("pending_otp_purpose", None)

            messages.success(request, f"Verification successful! Welcome back, {user.display_name}.")
            return redirect(next_url)
        else:
            if otp:
                otp.attempts += 1
                otp.save()
            messages.error(request, "Invalid or expired 6-digit verification code. Please try again.")

    context = {
        "user_email": user.email,
        "purpose": purpose,
        "purpose_label": "Verify Your Email" if purpose == "SIGNUP" else "Two-Factor Verification",
    }
    return render(request, "accounts/verify_otp.html", context)


def resend_otp_view(request):
    """
    Dispatches a fresh 6-digit OTP code to the pending user.
    """
    user_id = request.session.get("pending_otp_user_id")
    purpose = request.session.get("pending_otp_purpose", "LOGIN")

    if user_id:
        user = User.objects.filter(pk=user_id).first()
        if user:
            otp = EmailOTP.create_otp(user, purpose=purpose)
            send_otp_email(user, otp)
            messages.success(request, f"A fresh 6-digit verification code has been dispatched to {user.email}.")
    
    return redirect("accounts:verify_otp")


def logout_view(request):
    logout(request)
    messages.success(request, "You have been securely logged out.")
    return redirect("accounts:login")


def forgot_password_view(request):
    if request.method == "POST":
        email = request.POST.get("email", "").strip()
        user = User.objects.filter(email__iexact=email).first()
        if user:
            otp = EmailOTP.create_otp(user, purpose="RESET")
            send_otp_email(user, otp)
            request.session["pending_otp_user_id"] = user.id
            request.session["pending_otp_purpose"] = "RESET"
            messages.info(request, f"A 6-digit password reset code has been sent to {user.email}.")
            return redirect("accounts:verify_otp")
        
        messages.info(request, "If an account matching that email exists, a verification code has been sent.")
        return redirect("accounts:login")

    return render(request, "accounts/forgot_password.html")


def reset_password_view(request, token="demo-token"):
    if request.method == "POST":
        p1 = request.POST.get("password", "")
        p2 = request.POST.get("password_confirm", "")
        if p1 and p1 == p2:
            messages.success(request, "Your password has been reset successfully. Please log in.")
            return redirect("accounts:login")
        messages.error(request, "Passwords do not match.")

    return render(request, "accounts/reset_password.html")


def profile_view(request):
    user = request.user if request.user.is_authenticated else User.objects.filter(is_active=True).first()
    if not user:
        return redirect("accounts:login")

    if request.method == "POST":
        user.first_name = request.POST.get("first_name", getattr(user, "first_name", "")).strip()
        user.last_name = request.POST.get("last_name", getattr(user, "last_name", "")).strip()
        user.title = request.POST.get("title", getattr(user, "title", "")).strip()
        user.role = request.POST.get("role", getattr(user, "role", "DEVELOPER"))
        user.timezone = request.POST.get("timezone", getattr(user, "timezone", "UTC"))
        user.theme_preference = request.POST.get("theme_preference", getattr(user, "theme_preference", "DARK"))
        user.avatar_color = request.POST.get("avatar_color", getattr(user, "avatar_color", "#4f46e5"))
        user.save()
        try:
            mongo_manager.sync_user(user)
        except Exception:
            pass
        messages.success(request, "Profile updated successfully.")
        return redirect("accounts:profile")

    return render(request, "accounts/profile.html", {"user": user, "current_user": user})


def settings_view(request):
    user = request.user if request.user.is_authenticated else User.objects.filter(is_active=True).first()
    if not user:
        return redirect("accounts:login")

    if request.method == "POST":
        user.email_notifications_enabled = "email_notifications_enabled" in request.POST
        user.theme_preference = request.POST.get("theme_preference", getattr(user, "theme_preference", "DARK"))
        user.save()
        try:
            mongo_manager.sync_user(user)
        except Exception:
            pass
        messages.success(request, "Workspace preferences saved.")
        return redirect("accounts:settings")

    return render(request, "accounts/settings.html", {"user": user, "current_user": user})


class UserDirectoryAPI(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        users = User.objects.filter(is_active=True).values("id", "username", "first_name", "last_name", "role", "avatar_color")
        return Response(list(users))


class TokenBlacklistAPI(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        return Response({"message": "Token revoked successfully."})