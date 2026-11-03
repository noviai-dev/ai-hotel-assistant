"""独立 SMTP 发送测试：不访问数据库，不生成营销报告。

先修改下方参数，再从项目根目录运行：
    python backend/test_smtp_send.py --send

普通 unittest discovery 会跳过本测试，避免意外发送邮件。
这是需要网络的真实发送集成测试；成功仅代表 SMTP 接受邮件，不保证进入收件箱。
"""

import os
import smtplib
import ssl
import sys
import unittest
from email.headerregistry import Address
from email.message import EmailMessage
from email.utils import formatdate, make_msgid


# ==================== 邮件测试参数：只需修改这里 ====================
SMTP_HOST = "smtp.gmail.com"             # 邮箱服务商的 SMTP 服务器
SMTP_PORT = 465                            # SSL 通常 465；STARTTLS 通常 587
SMTP_SECURITY = "ssl"                     # "ssl" 或 "starttls"
SMTP_USERNAME = "noviai@vnj.jp"      # 登录账号；无需认证时设为空字符串
# $env:SMTP_PASSWORD = "你的邮箱授权码"
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")  # 授权码/密码，通过环境变量传入
SMTP_TIMEOUT_SECONDS = 30

EMAIL_FROM = "noviai@vnj.jp"         # 发件人，一般与登录账号一致
EMAIL_TO = "673554003@qq.com"        # 单个收件人
EMAIL_SUBJECT = "SMTP 邮件发送测试"
EMAIL_BODY = "这是一封独立的邮件发送测试邮件。收到此邮件说明发送链路可用。"
# =================================================================


class SmtpSendTest(unittest.TestCase):
    # 仅直接运行脚本并传入 --send 才启用真实发送。
    send_enabled = False

    def test_send_email(self):
        if not self.send_enabled:
            self.skipTest("真实发送需显式运行：python backend/test_smtp_send.py --send")

        self.assertTrue(SMTP_HOST and SMTP_HOST != "smtp.example.com", "请填写 SMTP_HOST")
        self.assertIn(SMTP_SECURITY, {"ssl", "starttls"})
        self.assertTrue(1 <= SMTP_PORT <= 65535, "SMTP_PORT 必须在 1–65535 之间")
        self.assertGreater(SMTP_TIMEOUT_SECONDS, 0)
        self.assertEqual(bool(SMTP_USERNAME), bool(SMTP_PASSWORD),
                         "账号和密码须同时配置；请设置 SMTP_PASSWORD 环境变量")
        for value in (EMAIL_FROM, EMAIL_TO):
            self.assertNotIn("\r", value)
            self.assertNotIn("\n", value)
            address = Address(addr_spec=value)
            self.assertTrue(address.username and address.domain, "请填写完整邮箱地址")
            self.assertNotEqual(address.domain.lower(), "example.com", "请替换示例邮箱")

        message = EmailMessage()
        message["From"] = EMAIL_FROM
        message["To"] = EMAIL_TO
        message["Subject"] = EMAIL_SUBJECT
        message["Date"] = formatdate(localtime=False)
        message["Message-ID"] = make_msgid()
        message.set_content(EMAIL_BODY)

        context = ssl.create_default_context()
        if SMTP_SECURITY == "ssl":
            client = smtplib.SMTP_SSL(
                SMTP_HOST, SMTP_PORT, timeout=SMTP_TIMEOUT_SECONDS, context=context)
        else:
            client = smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=SMTP_TIMEOUT_SECONDS)
        try:
            if SMTP_SECURITY == "starttls":
                client.ehlo()
                client.starttls(context=context)
                client.ehlo()
            if SMTP_USERNAME:
                client.login(SMTP_USERNAME, SMTP_PASSWORD)
            refused = client.send_message(message, from_addr=EMAIL_FROM, to_addrs=[EMAIL_TO])
            self.assertEqual(refused, {}, "SMTP 拒绝了收件人")
        finally:
            client.close()


if __name__ == "__main__":
    if "--send" in sys.argv:
        SmtpSendTest.send_enabled = True
        sys.argv.remove("--send")
    unittest.main(verbosity=2)
