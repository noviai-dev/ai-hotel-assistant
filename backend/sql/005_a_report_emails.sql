CREATE TABLE IF NOT EXISTS a_report_emails (
    own_hotel TEXT NOT NULL,
    run_key TEXT NOT NULL,
    recipient TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('sending','sent','failed')),
    error_type TEXT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (own_hotel,run_key),
    FOREIGN KEY (own_hotel,run_key) REFERENCES a_marketing_reports(own_hotel,run_key)
);
COMMENT ON TABLE a_report_emails IS '营销报告邮件发送状态；sent表示SMTP服务器已接收，不保证最终送达';
