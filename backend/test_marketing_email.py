import unittest
from dataclasses import replace
from unittest.mock import patch

from marketing.config import Settings
from marketing.mailer import build_message, send_report
from marketing.service import run_once


class EmailTests(unittest.TestCase):
    def setUp(self):
        self.settings = Settings("Hotel", "model", email_enabled=True,
                                 email_to="to@example.com", email_from="from@example.com",
                                 smtp_host="smtp.example.com", smtp_username="user", smtp_password="secret")
        self.report = {"run_key": "Hotel:2026-10-18:live", "status": "succeeded",
                       "payload": {"snapshot": {"as_of": "2026-10-18T09:00:00+09:00"},
                                   "advice": {"summary": "中文营销报告", "recommendations": []}}}

    def test_message_contains_readable_summary_and_attachment(self):
        msg = build_message(self.settings, self.report)
        self.assertIn("中文营销报告", msg.get_body().get_content())
        self.assertEqual(next(msg.iter_attachments()).get_filename(), "marketing-report.json")
        self.assertNotIn("secret", msg.as_string())

    def test_disabled_never_contacts_database_or_smtp(self):
        with patch("marketing.mailer.ReportStore") as store:
            self.assertEqual(send_report(replace(self.settings, email_enabled=False), "key"), "disabled")
            store.assert_not_called()

    def test_success_and_deduplication(self):
        with patch("marketing.mailer.ReportStore") as factory, patch("marketing.mailer.smtplib.SMTP_SSL") as smtp:
            store = factory.return_value
            store.get.return_value = self.report
            store.claim_email.return_value = True
            self.assertEqual(send_report(self.settings, "key"), "sent")
            smtp.return_value.send_message.assert_called_once()
            store.finish_email.assert_called_once_with("key", "sent")
            store.claim_email.return_value = False
            self.assertEqual(send_report(self.settings, "key"), "already_claimed")
            self.assertEqual(smtp.call_count, 1)

    def test_starttls_before_login_and_send(self):
        with patch("marketing.mailer.ReportStore") as factory, patch("marketing.mailer.smtplib.SMTP") as smtp:
            factory.return_value.get.return_value = self.report
            send_report(replace(self.settings, smtp_security="starttls", smtp_port=587), "key")
            names = [c[0] for c in smtp.return_value.method_calls]
            self.assertLess(names.index("starttls"), names.index("login"))
            self.assertLess(names.index("login"), names.index("send_message"))

    def test_failure_records_only_exception_type(self):
        with patch("marketing.mailer.ReportStore") as factory, patch("marketing.mailer.smtplib.SMTP_SSL") as smtp:
            factory.return_value.get.return_value = self.report
            smtp.return_value.send_message.side_effect = RuntimeError("secret")
            with self.assertRaises(RuntimeError):
                send_report(self.settings, "key", retry=True)
            factory.return_value.finish_email.assert_called_once_with("key", "failed", "RuntimeError")
            smtp.return_value.close.assert_called_once()

    def test_email_failure_does_not_mark_report_failed(self):
        with patch("marketing.service.ReportStore") as factory, \
             patch("marketing.service.load_snapshot", return_value={"groups": []}), \
             patch("marketing.service.send_report", side_effect=RuntimeError):
            with self.assertRaises(RuntimeError):
                run_once(self.settings)
            self.assertEqual(factory.return_value.save.call_count, 1)
            self.assertEqual(factory.return_value.save.call_args.args[1], "no_data")

    def test_dry_run_never_sends_email(self):
        with patch("marketing.service.ReportStore"), \
             patch("marketing.service.load_snapshot", return_value={"groups": []}), \
             patch("marketing.service.send_report") as send:
            run_once(self.settings, dry_run=True)
            send.assert_not_called()

    def test_invalid_addresses_and_security_rejected(self):
        for changes in ({"email_to": "x@example.com\nBcc: other@example.com"},
                        {"email_to": "a@example.com,b@example.com"}, {"smtp_security": "none"}):
            with self.assertRaises(ValueError):
                replace(self.settings, **changes).validate_email()


if __name__ == "__main__":
    unittest.main()
