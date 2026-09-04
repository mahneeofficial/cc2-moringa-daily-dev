import smtplib
from email.message import EmailMessage
from flask import current_app

# How long to wait for the SMTP server before giving up (seconds).
# Without this a hung mail server would hang the request thread forever.
SMTP_TIMEOUT_SECONDS = 20


def _is_placeholder(value):
    """Treat template placeholders as "not configured yet" (same idea as the
    GEMINI_API_KEY guard) so a freshly copied .env never tries to log in to
    Gmail with 'your_16_char_app_password'."""
    if not value:
        return True
    v = value.lower()
    return "your_" in v or "change_me" in v or "paste_your" in v


def send_password_reset_email(recipient_email, reset_url):
    mail_username = current_app.config.get("MAIL_USERNAME")
    mail_password = current_app.config.get("MAIL_PASSWORD")
    mail_server = current_app.config.get("MAIL_SERVER")
    mail_port = current_app.config.get("MAIL_PORT")
    mail_use_tls = current_app.config.get("MAIL_USE_TLS")

    if _is_placeholder(mail_username) or _is_placeholder(mail_password):
        raise RuntimeError(
            "Email configuration is missing. "
            "Set MAIL_USERNAME and MAIL_PASSWORD."
        )

    message = EmailMessage()

    message["Subject"] = "Moringa Daily — Password Reset"
    message["From"] = f"Moringa Daily <{mail_username}>"
    message["To"] = recipient_email

    # Plain-text part (always included — some clients and all spam-friendly
    # servers prefer it).
    message.set_content(
        f"""
Hello,

We received a request to reset your Moringa Daily password.

Click the link below to create a new password:

{reset_url}

This link will expire after 1 hour.

If you did not request a password reset, you can safely ignore this email.

Regards,
Moringa Daily Team
"""
    )

    # HTML part (what most users actually see — a proper button).
    message.add_alternative(
        f"""\
<html>
  <body style="margin:0;padding:0;background-color:#f4f5f7;font-family:Arial,Helvetica,sans-serif;">
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="padding:32px 0;">
      <tr>
        <td align="center">
          <table role="presentation" cellpadding="0" cellspacing="0" width="480" style="max-width:480px;width:100%;background-color:#ffffff;border-radius:12px;padding:32px;">
            <tr>
              <td align="center" style="padding-bottom:12px;font-size:22px;font-weight:bold;color:#16a34a;">
                &#129388; Moringa Daily
              </td>
            </tr>
            <tr>
              <td style="color:#333333;font-size:15px;line-height:1.6;padding-top:8px;">
                Hello,
              </td>
            </tr>
            <tr>
              <td style="color:#333333;font-size:15px;line-height:1.6;">
                We received a request to reset your Moringa Daily password.
                Click the button below to create a new password:
              </td>
            </tr>
            <tr>
              <td align="center" style="padding:28px 0;">
                <a href="{reset_url}" style="background-color:#16a34a;color:#ffffff;text-decoration:none;padding:12px 28px;border-radius:8px;font-size:15px;font-weight:bold;display:inline-block;">
                  Reset my password
                </a>
              </td>
            </tr>
            <tr>
              <td style="color:#666666;font-size:13px;line-height:1.6;">
                This link expires after 1 hour. If the button doesn't work,
                paste this URL into your browser:
                <br>
                <a href="{reset_url}" style="color:#16a34a;word-break:break-all;">{reset_url}</a>
              </td>
            </tr>
            <tr>
              <td style="padding-top:20px;color:#999999;font-size:12px;line-height:1.6;">
                If you did not request a password reset, you can safely
                ignore this email.
              </td>
            </tr>
          </table>
        </td>
      </tr>
    </table>
  </body>
</html>
""",
        subtype="html",
    )

    with smtplib.SMTP(mail_server, mail_port, timeout=SMTP_TIMEOUT_SECONDS) as smtp:
        if mail_use_tls:
            smtp.starttls()

        smtp.login(mail_username, mail_password)
        smtp.send_message(message)
