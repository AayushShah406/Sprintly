import logging
from django.core.mail import send_mail
from django.conf import settings
from .models import User, EmailOTP

logger = logging.getLogger(__name__)

def send_otp_email(user: User, otp: EmailOTP) -> bool:
    """
    Sends a stunning, ultra-clean 6-digit verification email.
    """
    purpose_title = "Email Verification" if otp.purpose == "SIGNUP" else "Two-Factor Verification"
    purpose_desc = "verify your email address" if otp.purpose == "SIGNUP" else "complete your login authentication"
    if otp.purpose == "RESET":
        purpose_title = "Password Reset"
        purpose_desc = "reset your account password"

    subject = f"[Sprintly] Your Verification Code: {otp.otp_code}"

    plain_message = (
        f"Hello {user.display_name},\n\n"
        f"Your 6-digit verification code to {purpose_desc} is:\n\n"
        f"    {otp.otp_code}\n\n"
        f"This code will expire in 10 minutes.\n\n"
        f"If you did not request this verification code, please ignore this email.\n\n"
        f"— Team Sprintly"
    )

    html_message = f"""
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset="utf-8">
      <meta name="viewport" content="width=device-width, initial-scale=1.0">
      <title>{purpose_title}</title>
    </head>
    <body style="margin:0;padding:30px 15px;background-color:#f1f5f9;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,'Helvetica Neue',Arial,sans-serif;">
      <table align="center" border="0" cellpadding="0" cellspacing="0" width="100%" style="max-width:540px;margin:0 auto;background:#ffffff;border-radius:16px;overflow:hidden;box-shadow:0 10px 25px rgba(0,0,0,0.06);border:1px solid #e2e8f0;">
        <!-- Header Gradient Bar -->
        <tr>
          <td style="padding:32px 36px 24px;text-align:center;background:linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%);">
            <div style="display:inline-block;padding:8px 16px;background:rgba(255,255,255,0.18);border-radius:100px;margin-bottom:12px;">
              <span style="color:#ffffff;font-size:12px;font-weight:700;letter-spacing:1px;text-transform:uppercase;">✨ Sprintly Security</span>
            </div>
            <h1 style="margin:0;color:#ffffff;font-size:26px;font-weight:800;letter-spacing:-0.5px;">Sprintly</h1>
            <p style="margin:6px 0 0;color:rgba(255,255,255,0.85);font-size:14px;">Enterprise Agile Collaboration Platform</p>
          </td>
        </tr>

        <!-- Body Content -->
        <tr>
          <td style="padding:36px 36px 28px;">
            <h2 style="margin:0 0 12px;font-size:20px;font-weight:700;color:#0f172a;text-align:center;">{purpose_title}</h2>
            <p style="margin:0 0 24px;font-size:15px;line-height:1.6;color:#475569;text-align:center;">
              Hello <strong style="color:#0f172a;">{user.display_name}</strong>,<br>
              Use the single-use 6-digit verification code below to {purpose_desc}:
            </p>

            <!-- 6-Digit Code Box -->
            <div style="background:#f8fafc;border:2px dashed #cbd5e1;border-radius:12px;padding:22px;text-align:center;margin:0 0 24px;">
              <div style="font-family:'Courier New',Courier,monospace;font-size:36px;font-weight:800;letter-spacing:8px;color:#4f46e5;">
                {otp.otp_code}
              </div>
              <p style="margin:10px 0 0;font-size:13px;color:#64748b;font-weight:600;">
                ⏱ Expires in <strong>10 minutes</strong>
              </p>
            </div>

            <p style="margin:0;font-size:13px;line-height:1.5;color:#94a3b8;text-align:center;">
              If you did not request this verification code, no action is required. Your account remains secure.
            </p>
          </td>
        </tr>

        <!-- Footer -->
        <tr>
          <td style="padding:20px 36px;background-color:#f8fafc;border-top:1px solid #e2e8f0;text-align:center;">
            <p style="margin:0;font-size:12px;color:#94a3b8;">
              © 2026 Sprintly Inc. All rights reserved. • Enterprise Agile & Team Management
            </p>
          </td>
        </tr>
      </table>
    </body>
    </html>
    """

    print(f"\n=======================================================")
    print(f"[Sprintly OTP Dispatch] To: {user.email}")
    print(f"[Sprintly OTP Dispatch] Purpose: {otp.get_purpose_display()}")
    print(f"[Sprintly OTP Dispatch] 6-Digit Code: >>> {otp.otp_code} <<<")
    print(f"=======================================================\n")

    try:
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=getattr(settings, "DEFAULT_FROM_EMAIL", "Sprintly Security <no-reply@sprintly.io>"),
            recipient_list=[user.email],
            html_message=html_message,
            fail_silently=True
        )
        return True
    except Exception as e:
        logger.error(f"[Sprintly OTP] Failed to send email to {user.email}: {e}")
        return False


def send_invitation_email(inviter: User, new_user: User, project, role_display: str, temporary_password: str = None) -> bool:
    """
    Sends a beautiful, executive project team invitation email.
    """
    subject = f"You're invited to join {project.name} on Sprintly"

    plain_message = (
        f"Hello {new_user.display_name},\n\n"
        f"{inviter.display_name} has invited you to collaborate on '{project.name}' ({project.key}) as a {role_display} on Sprintly.\n\n"
        f"Login to your workspace: http://127.0.0.1:8000/login/\n\n"
        f"— Team Sprintly"
    )

    html_message = f"""
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset="utf-8">
      <meta name="viewport" content="width=device-width, initial-scale=1.0">
      <title>Project Invitation</title>
    </head>
    <body style="margin:0;padding:30px 15px;background-color:#f1f5f9;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,'Helvetica Neue',Arial,sans-serif;">
      <table align="center" border="0" cellpadding="0" cellspacing="0" width="100%" style="max-width:560px;margin:0 auto;background:#ffffff;border-radius:16px;overflow:hidden;box-shadow:0 10px 25px rgba(0,0,0,0.06);border:1px solid #e2e8f0;">
        <!-- Header Gradient Bar -->
        <tr>
          <td style="padding:34px 36px 28px;text-align:center;background:linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%);">
            <div style="display:inline-block;padding:6px 14px;background:rgba(255,255,255,0.2);border-radius:100px;margin-bottom:12px;">
              <span style="color:#ffffff;font-size:12px;font-weight:700;letter-spacing:1px;text-transform:uppercase;">🎉 Team Invitation</span>
            </div>
            <h1 style="margin:0;color:#ffffff;font-size:26px;font-weight:800;">Sprintly</h1>
            <p style="margin:6px 0 0;color:rgba(255,255,255,0.85);font-size:14px;">Enterprise Agile Collaboration Platform</p>
          </td>
        </tr>

        <!-- Body Content -->
        <tr>
          <td style="padding:36px 36px 28px;">
            <h2 style="margin:0 0 14px;font-size:20px;font-weight:700;color:#0f172a;text-align:center;">
              You've been invited to join <span style="color:#4f46e5;">{project.name}</span>
            </h2>
            <p style="margin:0 0 24px;font-size:15px;line-height:1.6;color:#475569;text-align:center;">
              <strong style="color:#0f172a;">{inviter.display_name}</strong> added you to the project team on Sprintly.
            </p>

            <!-- Project Details Pill Box -->
            <div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:12px;padding:20px;margin:0 0 26px;">
              <table width="100%" border="0" cellpadding="0" cellspacing="0">
                <tr>
                  <td style="padding:6px 0;font-size:14px;color:#64748b;">Project:</td>
                  <td style="padding:6px 0;font-size:14px;font-weight:700;color:#0f172a;text-align:right;">{project.name} ({project.key})</td>
                </tr>
                <tr>
                  <td style="padding:6px 0;font-size:14px;color:#64748b;">Your Role:</td>
                  <td style="padding:6px 0;font-size:14px;font-weight:700;color:#4f46e5;text-align:right;">{role_display}</td>
                </tr>
                <tr>
                  <td style="padding:6px 0;font-size:14px;color:#64748b;">Invited By:</td>
                  <td style="padding:6px 0;font-size:14px;font-weight:600;color:#0f172a;text-align:right;">{inviter.display_name}</td>
                </tr>
              </table>
            </div>

            <!-- Call to Action Button -->
            <div style="text-align:center;margin:0 0 24px;">
              <a href="http://127.0.0.1:8000/login/" style="display:inline-block;padding:14px 32px;background:#4f46e5;color:#ffffff;font-size:15px;font-weight:700;text-decoration:none;border-radius:10px;box-shadow:0 6px 16px rgba(79,70,229,0.35);">
                Open Sprintly Workspace →
              </a>
            </div>

            <p style="margin:0;font-size:13px;line-height:1.5;color:#94a3b8;text-align:center;">
              Log in with your email <strong style="color:#475569;">{new_user.email}</strong> to access your board and tasks.
            </p>
          </td>
        </tr>

        <!-- Footer -->
        <tr>
          <td style="padding:20px 36px;background-color:#f8fafc;border-top:1px solid #e2e8f0;text-align:center;">
            <p style="margin:0;font-size:12px;color:#94a3b8;">
              © 2026 Sprintly Inc. • Fast, Secure & Scalable Project Management
            </p>
          </td>
        </tr>
      </table>
    </body>
    </html>
    """

    print(f"\n=======================================================")
    print(f"[Sprintly Invitation] Sent to: {new_user.email}")
    print(f"[Sprintly Invitation] Project: {project.name} ({project.key})")
    print(f"[Sprintly Invitation] Role: {role_display}")
    print(f"=======================================================\n")

    try:
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=getattr(settings, "DEFAULT_FROM_EMAIL", "Sprintly Security <no-reply@sprintly.io>"),
            recipient_list=[new_user.email],
            html_message=html_message,
            fail_silently=True
        )
        return True
    except Exception as e:
        logger.error(f"[Sprintly Invitation] Failed to send email to {new_user.email}: {e}")
        return False
