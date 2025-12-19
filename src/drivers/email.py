import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import Header

from src.core.config import GlobalConfig
from src.core.exceptions import DriverError, ConfigurationError

logger = logging.getLogger("driver.email")

class EmailDriver:
    def __init__(self):
        self.config = GlobalConfig
        self.conf = self.config.get('email')
        
        # 基础检查 - 同时支持 receiver（单数）和 receivers（复数）配置
        has_receiver = self.conf.get('sender') and self.conf.get('password') and (self.conf.get('receiver') or self.conf.get('receivers'))
        if not has_receiver:
            # 这里不抛出异常，因为可能用户只想跑本地而不发邮件
            # 但我们在 log 里严重警告
            logger.warning("⚠️ Email credentials missing in .env. Email features will fail.")

    def send(self, subject: str, content_html: str, receivers: list = None):
        """
        发送 HTML 邮件。
        """
        # 1. 获取配置
        sender = self.conf.get('sender')
        password = self.conf.get('password')
        host = self.conf.get('host')
        port = self.conf.get('port')
        use_ssl = self.conf.get('use_ssl')
        
        # 处理收件人：优先使用传入参数，否则使用配置
        if receivers:
            final_receivers = receivers
        else:
            # 支持 receiver（单数）和 receivers（复数）配置
            config_receivers = self.conf.get('receivers')
            config_receiver = self.conf.get('receiver')
            
            # 优先级：receivers > receiver，统一转为列表格式
            final_receivers = config_receivers
            if not final_receivers and config_receiver:
                final_receivers = [config_receiver] if isinstance(config_receiver, str) else config_receiver

        if not sender or not password or not host:
            raise ConfigurationError("Missing SMTP configuration", config_key="email")
        
        if not final_receivers:
            logger.warning(f"⚠️ No receivers specified. Skipping email.")
            return False

        logger.info(f"📧 Sending email: '{subject}' to {len(final_receivers)} recipients via {host}:{port}...")

        try:
            # 2. 构造邮件对象
            message = MIMEMultipart()
            # 使用更兼容的编码方式，避免在某些客户端显示异常
            message['From'] = f"ScholarCore <{sender}>"
            message['To'] = ",".join(final_receivers)
            message['Subject'] = Header(subject, 'utf-8')
            message.attach(MIMEText(content_html, 'html', 'utf-8'))

            # 3. 发送逻辑 (区分 SSL 和 TLS)
            if use_ssl:
                # 纯 SSL 模式 (如网易 163 端口 465)
                with smtplib.SMTP_SSL(host, port) as server:
                    # server.set_debuglevel(1) # 如果调试网络问题可开启
                    server.login(sender, password)
                    server.sendmail(sender, final_receivers, message.as_string())
            else:
                # STARTTLS 模式 (如 Gmail 端口 587)
                with smtplib.SMTP(host, port) as server:
                    server.starttls()
                    server.login(sender, password)
                    server.sendmail(sender, final_receivers, message.as_string())
            
            logger.info("✅ Email sent successfully.")
            return True

        except smtplib.SMTPAuthenticationError:
            raise DriverError("SMTP Authentication failed. Check your password/auth_code.", driver_name="email")
        except Exception as e:
            logger.error(f"❌ Failed to send email: {e}")
            raise DriverError(f"SMTP Transmission Error: {str(e)}", driver_name="email")