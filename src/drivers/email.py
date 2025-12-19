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
        
        # 简单直接的检查
        required = ['sender', 'password', 'host', 'receivers']
        missing = [k for k in required if not self.conf.get(k)]
        
        if missing:
            logger.warning(f"⚠️ Email config missing: {missing}. Email features disabled.")
            self.enabled = False
        else:
            self.enabled = True
    
    def send(self, subject: str, content_html: str, receivers: list = None):
        """
        发送 HTML 邮件。
        """
        if not self.enabled:
            logger.warning("🚫 Email driver disabled due to missing config.")
            return False
        
        # 优先使用参数传入的，其次使用配置文件的
        final_receivers = receivers if receivers else self.conf.get('receivers')
        if not final_receivers:
            logger.warning("No receivers specified.")
            return False
        
        # 1. 获取配置
        sender = self.conf.get('sender')
        password = self.conf.get('password')
        host = self.conf.get('host')
        port = self.conf.get('port')
        use_ssl = self.conf.get('use_ssl')
        

        logger.info(f"📧 Sending email: '{subject}' to {len(final_receivers)} recipients...")

        try:
            # 2. 构造邮件对象
            message = MIMEMultipart()
            # 使用更兼容的编码方式，避免在某些客户端显示异常
            message['From'] = sender
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

        except Exception as e:
            logger.error(f"❌ Failed to send email: {e}")
            raise DriverError(f"SMTP Transmission Error: {str(e)}", driver_name="email")