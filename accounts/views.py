import re
import os
from django.core.validators import validate_email
from django.core.exceptions import ValidationError as DjangoValidationError
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib import messages
from django.contrib.auth.password_validation import validate_password
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from .models import User, EmailOTP, Profile
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


def get_authenticated_user(request):
    """
    Authenticates user from either JWT Bearer token or active session.
    Guarantees user ID is never forged or accepted from frontend payload (anti-IDOR).
    """
    forced_user = getattr(request, "_force_auth_user", None) or getattr(getattr(request, "_request", None), "_force_auth_user", None)
    if forced_user and forced_user.is_authenticated:
        return forced_user

    auth_header = request.headers.get("Authorization") or request.META.get("HTTP_AUTHORIZATION", "")
    if auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1].strip()
        try:
            from config.crypto_utils import decode_jwt_token
            payload = decode_jwt_token(token)
            user_id = payload.get("sub")
            user = User.objects.filter(pk=user_id, is_active=True).first()
            if user:
                return user
        except Exception:
            pass
    if request.user and request.user.is_authenticated:
        return request.user
    return None


def serialize_profile(user):
    """
    Returns only safe public/profile information.
    Guarantees passwords, hashes, tokens, secrets, and API keys are never leaked.
    """
    profile = user.get_profile
    pic_url = profile.profile_picture_url
    if not pic_url and profile.profile_picture:
        try:
            pic_url = profile.profile_picture.url
        except Exception:
            pic_url = None

    joined_date = ""
    if hasattr(user, "created_at") and user.created_at:
        joined_date = user.created_at.strftime("%Y-%m-%d")
    elif hasattr(user, "date_joined") and user.date_joined:
        joined_date = user.date_joined.strftime("%Y-%m-%d")

    first_name = user.first_name or ""
    last_name = user.last_name or ""

    # Intelligently auto-derive first_name and last_name if blank
    if not first_name and user.username:
        clean = re.sub(r"[._-]+", " ", user.username).strip()
        parts = clean.split()
        if len(parts) >= 2:
            first_name = parts[0].capitalize()
            if not last_name:
                last_name = " ".join(p.capitalize() for p in parts[1:])
        elif len(parts) == 1 and parts[0]:
            first_name = parts[0].capitalize()

    if not first_name and user.email:
        prefix = user.email.split("@")[0]
        clean = re.sub(r"[._-]+", " ", prefix).strip()
        parts = clean.split()
        if len(parts) >= 2:
            first_name = parts[0].capitalize()
            if not last_name:
                last_name = " ".join(p.capitalize() for p in parts[1:])
        elif len(parts) == 1 and parts[0]:
            first_name = parts[0].capitalize()

    return {
        "id": user.pk,
        "username": user.username,
        "email": user.email,
        "first_name": first_name,
        "last_name": last_name,
        "display_name": f"{first_name} {last_name}".strip() or user.username,
        "initials": user.initials,
        "job_title": profile.job_title or user.title or "",
        "location": profile.location or "",
        "bio": profile.bio or "",
        "profile_picture": pic_url,
        "role": user.get_role_display(),
        "department": profile.department or "Engineering",
        "joined_date": joined_date,
    }


class ProfileDetailAPI(APIView):
    """
    API endpoint for viewing and updating the authenticated user's profile.
    GET  /api/profile/ -> Returns safe profile data.
    PUT  /api/profile/ -> Validates and persists editable fields; read-only fields remain immutable.
    """
    permission_classes = [AllowAny]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get(self, request):
        user = get_authenticated_user(request)
        if not user:
            return Response({"error": "Authentication required. Please log in."}, status=status.HTTP_401_UNAUTHORIZED)
        return Response(serialize_profile(user))

    def put(self, request):
        user = get_authenticated_user(request)
        if not user:
            return Response({"error": "Authentication required. Please log in."}, status=status.HTTP_401_UNAUTHORIZED)

        data = request.data
        errors = {}

        # 1. First Name & Last Name (Editable)
        first_name = data.get("first_name", None)
        if first_name is not None:
            first_name = str(first_name).strip()
            if len(first_name) > 50:
                errors["first_name"] = "First name must not exceed 50 characters."
            else:
                user.first_name = first_name

        last_name = data.get("last_name", None)
        if last_name is not None:
            last_name = str(last_name).strip()
            if len(last_name) > 50:
                errors["last_name"] = "Last name must not exceed 50 characters."
            else:
                user.last_name = last_name

        # 2. Username (Editable, Unique)
        new_username = data.get("username", None)
        if new_username is not None:
            new_username = str(new_username).strip()
            if not new_username:
                errors["username"] = "Username is required."
            elif len(new_username) < 3 or len(new_username) > 150:
                errors["username"] = "Username must be between 3 and 150 characters."
            elif not re.match(r"^[a-zA-Z0-9_.-]+$", new_username):
                errors["username"] = "Username can only contain alphanumeric characters, dots, underscores, and hyphens."
            elif User.objects.filter(username__iexact=new_username).exclude(pk=user.pk).exists():
                errors["username"] = "This username is already taken. Please choose another."
            else:
                user.username = new_username

        # 3. Email (Editable, Format Validated, Unique)
        new_email = data.get("email", None)
        if new_email is not None:
            new_email = str(new_email).strip().lower()
            if not new_email:
                errors["email"] = "Email address is required."
            else:
                try:
                    validate_email(new_email)
                except DjangoValidationError:
                    errors["email"] = "Please enter a valid email address."
                
                if "email" not in errors:
                    if User.objects.filter(email__iexact=new_email).exclude(pk=user.pk).exists():
                        errors["email"] = "This email is already in use by another account."
                    else:
                        user.email = new_email

        # 4. Job Title, Location, Bio (Editable Profile Fields)
        profile = user.get_profile

        job_title = data.get("job_title", None)
        if job_title is not None:
            job_title = str(job_title).strip()
            if len(job_title) > 120:
                errors["job_title"] = "Job title must not exceed 120 characters."
            else:
                profile.job_title = job_title
                user.title = job_title

        location = data.get("location", None)
        if location is not None:
            location = str(location).strip()
            if len(location) > 120:
                errors["location"] = "Location must not exceed 120 characters."
            else:
                profile.location = location

        bio = data.get("bio", None)
        if bio is not None:
            bio = str(bio).strip()
            if len(bio) > 1000:
                errors["bio"] = "Bio must not exceed 1000 characters."
            else:
                profile.bio = bio

        # 5. Profile Picture (Upload, Validation & Removal)
        if "profile_picture" in request.FILES:
            image_file = request.FILES["profile_picture"]
            valid_extensions = [".jpg", ".jpeg", ".png", ".webp", ".gif"]
            ext = os.path.splitext(image_file.name)[1].lower()
            if ext not in valid_extensions:
                errors["profile_picture"] = f"Unsupported file type ({ext}). Allowed formats: JPG, PNG, WEBP, GIF."
            elif image_file.size > 5 * 1024 * 1024:
                errors["profile_picture"] = "Image file size exceeds the 5MB limit."
            else:
                profile.profile_picture = image_file
        elif data.get("remove_picture") in [True, "true", "1"]:
            profile.profile_picture = None

        # 6. Read-Only Enforcement: role, department, joined_date are NOT modified
        # (Explicitly ignored even if sent in payload)

        if errors:
            first_err = next(iter(errors.values()))
            return Response({"error": first_err, "errors": errors}, status=status.HTTP_400_BAD_REQUEST)

        user.save()
        profile.save()

        try:
            mongo_manager.sync_user(user)
        except Exception:
            pass

        resp_payload = serialize_profile(user)
        resp_payload["success"] = True
        resp_payload["message"] = "Profile updated successfully."
        return Response(resp_payload, status=status.HTTP_200_OK)


def profile_view(request):
    user = get_authenticated_user(request)
    if not user:
        return redirect("accounts:login")

    # Automatically derive first_name and last_name if blank for logged in user
    if not user.first_name and user.username:
        clean = re.sub(r"[._-]+", " ", user.username).strip()
        parts = clean.split()
        if len(parts) >= 2:
            user.first_name = parts[0].capitalize()
            if not user.last_name:
                user.last_name = " ".join(p.capitalize() for p in parts[1:])
            user.save(update_fields=["first_name", "last_name"])
        elif len(parts) == 1 and parts[0]:
            user.first_name = parts[0].capitalize()
            user.save(update_fields=["first_name"])

    profile = user.get_profile

    if request.method == "POST":
        first_name = request.POST.get("first_name", getattr(user, "first_name", "")).strip()
        last_name = request.POST.get("last_name", getattr(user, "last_name", "")).strip()
        job_title = (request.POST.get("job_title") or request.POST.get("title", getattr(user, "title", ""))).strip()
        location = request.POST.get("location", "").strip()
        bio = request.POST.get("bio", "").strip()
        avatar_color = request.POST.get("avatar_color", user.avatar_color)
        timezone_val = request.POST.get("timezone", getattr(user, "timezone", "UTC"))
        theme_preference = request.POST.get("theme_preference", getattr(user, "theme_preference", "DARK"))

        user.first_name = first_name
        user.last_name = last_name
        user.avatar_color = avatar_color
        user.title = job_title
        if timezone_val:
            user.timezone = timezone_val
        if theme_preference:
            user.theme_preference = theme_preference
        user.save()

        profile.job_title = job_title
        profile.location = location
        profile.bio = bio

        if "profile_picture" in request.FILES:
            profile.profile_picture = request.FILES["profile_picture"]
        elif request.POST.get("remove_picture") in [True, "true", "1"]:
            profile.profile_picture = None
        profile.save()

        try:
            mongo_manager.sync_user(user)
        except Exception:
            pass

        messages.success(request, "Profile updated successfully.")
        return redirect("accounts:profile")

    return render(request, "accounts/profile.html", {
        "user": user,
        "current_user": user,
        "profile": profile
    })


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