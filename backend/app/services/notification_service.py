"""Notification dispatch helpers for SMS and email providers."""

import smtplib
from datetime import UTC, datetime
from email.message import EmailMessage
from typing import Any

import httpx
from backend.app.core.config import settings
from backend.app.core.logging import logger


class NotificationService:
    """Dispatch notifications through configured providers with safe fallback."""

    @property
    def sms_enabled(self) -> bool:
        return bool(
            settings.ENABLE_REAL_NOTIFICATIONS
            and settings.TWILIO_ACCOUNT_SID
            and settings.TWILIO_AUTH_TOKEN
            and settings.TWILIO_FROM_NUMBER
        )

    @property
    def email_enabled(self) -> bool:
        user = settings.SMTP_USER or settings.EMAIL_USER
        password = settings.SMTP_PASSWORD or settings.EMAIL_PASSWORD
        return bool(
            settings.ENABLE_REAL_NOTIFICATIONS
            and settings.SMTP_HOST
            and user
            and password
            and "placeholder" not in password.lower()
        )

    async def send_email(self, to_email: str, subject: str, content: str) -> str:
        """Send an email using SMTP with fallback to logging."""
        if not self.email_enabled:
            logger.info("[EMAIL LOGGED (disabled)] To: %s | Subject: %s", to_email, subject)
            return "LOGGED"

        user = settings.SMTP_USER or settings.EMAIL_USER
        password = settings.SMTP_PASSWORD or settings.EMAIL_PASSWORD
        from_email = settings.EMAIL_FROM or user

        message = EmailMessage()
        message["Subject"] = subject
        message["From"] = from_email
        message["To"] = to_email
        message.set_content(content)

        # 1. Try STARTTLS on SMTP_PORT (587)
        try:
            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10) as smtp:
                if settings.SMTP_TLS:
                    smtp.starttls()
                smtp.login(user, password)
                smtp.send_message(message)
            logger.info("Email sent successfully to %s: %s", to_email, subject)
            return "SENT"
        except Exception as exc:
            # 2. Try SSL fallback on port 465 if port 587 was closed by network/ISP
            try:
                with smtplib.SMTP_SSL(settings.SMTP_HOST, 465, timeout=10) as smtp_ssl:
                    smtp_ssl.login(user, password)
                    smtp_ssl.send_message(message)
                logger.info("Email sent successfully via SSL to %s: %s", to_email, subject)
                return "SENT"
            except Exception as ssl_exc:
                logger.warning(
                    "SMTP dispatch to %s failed (STARTTLS: %s, SSL: %s). Fallback to logging.",
                    to_email,
                    exc,
                    ssl_exc,
                )
                logger.info("[EMAIL LOGGED (fallback)] To: %s | %s\n%s", to_email, subject, content)
                return "LOGGED"

    async def send_sms(self, to_phone: str, body: str) -> str:
        """Send one SMS. Returns SENT when real dispatch succeeds, otherwise LOGGED."""
        normalized = to_phone if to_phone.startswith("+") else f"+91{to_phone}"
        if not self.sms_enabled:
            logger.info("[SMS LOGGED] To: %s -> %s", normalized, body)
            return "LOGGED"

        url = (
            "https://api.twilio.com/2010-04-01/Accounts/"
            f"{settings.TWILIO_ACCOUNT_SID}/Messages.json"
        )
        payload = {
            "From": settings.TWILIO_FROM_NUMBER,
            "To": normalized,
            "Body": body,
        }
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(
                url,
                data=payload,
                auth=(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN),
            )
            response.raise_for_status()
        return "SENT"

    async def send_sos_alerts(
        self,
        contacts: list[dict[str, Any]],
        latitude: float,
        longitude: float,
        message: str | None,
    ) -> list[dict[str, Any]]:
        """Notify all emergency contacts and return contact snapshots."""
        map_link = f"https://maps.google.com/?q={latitude},{longitude}"
        alert_body = (
            "SAKHISAHAY EMERGENCY ALERT: A trusted contact needs help. "
            f"Location: {latitude:.6f},{longitude:.6f}. Map: {map_link}. "
            f"Message: {message or 'Please contact immediately.'}"
        )

        snapshots: list[dict[str, Any]] = []
        for contact in contacts:
            status = "FAILED"
            try:
                status = await self.send_sms(contact["phone"], alert_body)
            except Exception as exc:
                logger.exception(
                    "SOS SMS dispatch failed for contact %s: %s",
                    contact.get("id", contact.get("name", "unknown")),
                    exc,
                )

            snapshots.append(
                {
                    "name": contact["name"],
                    "phone": contact["phone"],
                    "relationship": contact["relationship"],
                    "dispatch_status": status,
                }
            )
        return snapshots

    async def send_sos_alert_email(
        self,
        to_email: str,
        user_name: str,
        user_email: str,
        latitude: float,
        longitude: float,
        message: str | None = None,
    ) -> str:
        """Send SOS emergency alert email to admin or emergency contact."""
        map_link = f"https://maps.google.com/?q={latitude},{longitude}"
        subject = f"🚨 EMERGENCY ALERT: SAKHISAHAY SOS triggered by {user_name}"
        content = (
            f"🚨 SAKHISAHAY EMERGENCY SOS ALERT!\n\n"
            f"A user has triggered an emergency SOS signal:\n"
            f"• User Name: {user_name}\n"
            f"• User Email: {user_email}\n"
            f"• Latitude: {latitude:.6f}\n"
            f"• Longitude: {longitude:.6f}\n"
            f"• Google Maps Location: {map_link}\n"
            f"• Message: {message or 'Immediate assistance required.'}\n"
            f"• Triggered At: {datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S UTC')}\n\n"
            f"If you are an emergency contact or administrator, please verify their safety immediately or dial 112."
        )
        return await self.send_email(to_email, subject, content)

    async def send_password_reset_email(self, email: str, reset_url: str) -> str:
        """Send password reset email with secure token link."""
        subject = "Reset your SAKHISAHAY password"
        content = (
            f"Hello,\n\n"
            f"We received a request to reset your SAKHISAHAY account password.\n\n"
            f"Please open this secure link within 15 minutes to reset your password:\n"
            f"{reset_url}\n\n"
            f"If you did not request a password reset, you can safely ignore this email.\n\n"
            f"— SAKHISAHAY Team"
        )
        return await self.send_email(email, subject, content)
