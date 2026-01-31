"""邮件服务"""

import logging
import random
import re
import string
from datetime import datetime, timedelta
from typing import Optional

from manus_web_agent.core.toml_config import TOML_CONFIG
from manus_web_agent.domain.external.cache import Cache

logger = logging.getLogger(__name__)

# 可选的邮件依赖
try:
    import aiosmtplib
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart
    HAS_EMAIL_DEPS = True
except ImportError:
    HAS_EMAIL_DEPS = False
    logger.warning("aiosmtplib 未安装，邮件功能将不可用")


class EmailService:
    """邮件服务，用于发送验证码"""

    def __init__(self, cache: Cache):
        self._cache = cache
        self._code_expiry = 300  # 验证码有效期 5 分钟
        self._max_attempts = 5  # 最大尝试次数
        self._attempt_window = 3600  # 尝试次数重置窗口 1 小时

        # SMTP 配置
        config = TOML_CONFIG
        self._smtp_host = getattr(config, 'email_host', 'smtp.gmail.com')
        self._smtp_port = getattr(config, 'email_port', 587)
        self._smtp_username = getattr(config, 'email_username', '')
        self._smtp_password = getattr(config, 'email_password', '')
        self._email_from = getattr(config, 'email_from', 'noreply@manus.ai')

    def _generate_code(self, length: int = 6) -> str:
        """生成随机验证码"""
        return ''.join(random.choices(string.digits, k=length))

    def _is_valid_email(self, email: str) -> bool:
        """验证邮箱格式"""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None

    async def _send_email(self, to_email: str, subject: str, content: str) -> bool:
        """发送邮件"""
        if not HAS_EMAIL_DEPS:
            logger.error("邮件依赖未安装，无法发送邮件")
            return False

        try:
            message = MIMEMultipart()
            message["From"] = self._email_from
            message["To"] = to_email
            message["Subject"] = subject
            message.attach(MIMEText(content, "html"))

            await aiosmtplib.send(
                message,
                hostname=self._smtp_host,
                port=self._smtp_port,
                start_tls=True,
                username=self._smtp_username,
                password=self._smtp_password,
            )
            return True
        except Exception as e:
            logger.error(f"发送邮件失败: {e}")
            return False

    async def send_verification_code(self, email: str, purpose: str = "verification") -> bool:
        """发送验证码邮件

        :param email: 邮箱地址
        :param purpose: 验证码用途（verification/reset_password）
        :return: 是否成功
        """
        if not self._is_valid_email(email):
            return False

        # 检查发送频率限制
        rate_limit_key = f"email_rate_limit:{email}"
        attempt_count = await self._cache.get(rate_limit_key) or 0
        if int(attempt_count) >= self._max_attempts:
            logger.warning(f"邮箱 {email} 发送次数超限")
            return False

        # 生成验证码
        code = self._generate_code()

        # 保存验证码到缓存
        cache_key = f"email_code:{purpose}:{email}"
        await self._cache.set(cache_key, code, self._code_expiry)

        # 更新发送次数
        await self._cache.set(rate_limit_key, int(attempt_count) + 1, self._attempt_window)

        # 发送邮件
        subject = "Manus AI - 验证码"
        content = f"""
        <html>
        <body>
            <h2>Manus AI 验证码</h2>
            <p>您的验证码是：</p>
            <h1 style="color: #4CAF50;">{code}</h1>
            <p>验证码将在 5 分钟后过期。</p>
            <p>如果这不是您本人的操作，请忽略此邮件。</p>
        </body>
        </html>
        """

        success = await self._send_email(email, subject, content)
        if success:
            logger.info(f"已向 {email} 发送验证码")
        return success

    async def verify_code(self, email: str, code: str, purpose: str = "verification") -> bool:
        """验证验证码

        :param email: 邮箱地址
        :param code: 验证码
        :param purpose: 验证码用途
        :return: 是否有效
        """
        cache_key = f"email_code:{purpose}:{email}"
        stored_code = await self._cache.get(cache_key)

        if not stored_code:
            return False

        if stored_code != code:
            return False

        # 验证成功后删除验证码
        await self._cache.delete(cache_key)
        return True

    async def clear_expired_codes(self) -> None:
        """清理过期验证码（由定时任务调用）"""
        # Redis 会自动过期，此方法用于其他类型的缓存
        pass
