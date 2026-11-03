import os
from dataclasses import dataclass, field
from pathlib import Path
from zoneinfo import ZoneInfo

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class Settings:
    hotel: str
    model: str
    timezone: str = "Asia/Tokyo"
    hour: int = 9
    horizon_days: int = 60
    freshness_days: int = 7
    email_enabled: bool = False
    email_to: str = ""
    email_from: str = ""
    smtp_host: str = ""
    smtp_port: int = 465
    smtp_security: str = "ssl"
    smtp_username: str = ""
    smtp_password: str = field(default="", repr=False)

    @classmethod
    def load(cls):
        load_dotenv(ROOT / ".env", override=False)
        result = cls(
            hotel=os.getenv("MARKETING_HOTEL", "").strip(),
            model=os.getenv("OPENAI_MODEL", "").strip(),
            timezone=os.getenv("MARKETING_TIMEZONE", "Asia/Tokyo"),
            hour=int(os.getenv("MARKETING_HOUR", "9")),
            horizon_days=int(os.getenv("MARKETING_HORIZON_DAYS", "60")),
            freshness_days=int(os.getenv("MARKETING_FRESHNESS_DAYS", "7")),
            email_enabled=os.getenv("MARKETING_EMAIL_ENABLED", "false").lower() == "true",
            email_to=os.getenv("MARKETING_EMAIL_TO", "").strip(),
            email_from=os.getenv("MARKETING_EMAIL_FROM", "").strip(),
            smtp_host=os.getenv("SMTP_HOST", "").strip(),
            smtp_port=int(os.getenv("SMTP_PORT", "465")),
            smtp_security=os.getenv("SMTP_SECURITY", "ssl").lower(),
            smtp_username=os.getenv("SMTP_USERNAME", ""),
            smtp_password=os.getenv("SMTP_PASSWORD", ""),
        )
        if not result.hotel:
            raise ValueError("请设置 MARKETING_HOTEL")
        if not 0 <= result.hour <= 23 or not 1 <= result.horizon_days <= 366 or not 1 <= result.freshness_days <= 90:
            raise ValueError("营销分析时间或窗口配置无效")
        ZoneInfo(result.timezone)
        if result.email_enabled:
            result.validate_email()
        return result

    def validate_email(self):
        from email.headerregistry import Address
        if not self.smtp_host or self.smtp_security not in {"ssl", "starttls"} or not 1 <= self.smtp_port <= 65535:
            raise ValueError("请检查 SMTP_HOST、SMTP_PORT、SMTP_SECURITY（ssl/starttls）")
        for address in (self.email_to, self.email_from):
            if not address or "\r" in address or "\n" in address:
                raise ValueError("请配置单个收件/发件邮箱")
            parsed = Address(addr_spec=address)
            if not parsed.username or not parsed.domain:
                raise ValueError("邮箱地址无效")
        if bool(self.smtp_username) != bool(self.smtp_password):
            raise ValueError("SMTP_USERNAME 和 SMTP_PASSWORD 必须同时配置")
