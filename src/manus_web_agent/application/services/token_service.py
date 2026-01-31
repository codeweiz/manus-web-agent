"""Token 服务"""

import hashlib
import hmac
import secrets
import time
from datetime import datetime, timedelta
from typing import Optional, Tuple

import jwt
from fastapi import HTTPException, status

from manus_web_agent.core.toml_config import TOML_CONFIG

# Token 黑名单（内存存储，生产环境应使用 Redis）
_token_blacklist: set = set()


class TokenService:
    """Token 服务，处理 JWT 令牌和签名 URL"""

    def __init__(self):
        jwt_config = TOML_CONFIG.jwt_config
        self.secret_key = jwt_config.secret_key if jwt_config.secret_key else secrets.token_hex(32)
        self.algorithm = jwt_config.algorithm
        self.access_token_expire_minutes = jwt_config.access_token_expire_minutes
        self.refresh_token_expire_days = jwt_config.refresh_token_expire_days

    def create_access_token(self, user_id: str, email: str, role: str) -> str:
        """创建访问令牌"""
        expire = datetime.utcnow() + timedelta(minutes=self.access_token_expire_minutes)
        payload = {
            "sub": user_id,
            "email": email,
            "role": role,
            "type": "access",
            "exp": expire,
            "iat": datetime.utcnow(),
        }
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

    def create_refresh_token(self, user_id: str) -> str:
        """创建刷新令牌"""
        expire = datetime.utcnow() + timedelta(days=self.refresh_token_expire_days)
        payload = {
            "sub": user_id,
            "type": "refresh",
            "exp": expire,
            "iat": datetime.utcnow(),
        }
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

    def create_token_pair(self, user_id: str, email: str, role: str) -> Tuple[str, str]:
        """创建令牌对（访问令牌 + 刷新令牌）"""
        access_token = self.create_access_token(user_id, email, role)
        refresh_token = self.create_refresh_token(user_id)
        return access_token, refresh_token

    def verify_token(self, token: str) -> dict:
        """验证 JWT 令牌"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="令牌已过期"
            )
        except jwt.InvalidTokenError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="无效令牌"
            )

    def verify_access_token(self, token: str) -> dict:
        """验证访问令牌"""
        payload = self.verify_token(token)
        if payload.get("type") != "access":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="无效访问令牌"
            )
        return payload

    def verify_refresh_token(self, token: str) -> dict:
        """验证刷新令牌"""
        payload = self.verify_token(token)
        if payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="无效刷新令牌"
            )
        return payload

    def create_signed_url(self, base_url: str, expire_minutes: int = 15) -> str:
        """创建签名 URL

        :param base_url: 基础 URL
        :param expire_minutes: 过期时间（分钟）
        :return: 带签名的完整 URL
        """
        expire_at = int(time.time()) + expire_minutes * 60
        signature_data = f"{base_url}:{expire_at}"
        signature = hmac.new(
            self.secret_key.encode(),
            signature_data.encode(),
            hashlib.sha256
        ).hexdigest()

        separator = "&" if "?" in base_url else "?"
        return f"{base_url}{separator}signature={signature}&expires={expire_at}"

    def verify_signed_url(self, url: str) -> bool:
        """验证签名 URL

        :param url: 完整的 URL
        :return: 是否有效
        """
        # 解析 URL 中的签名和过期时间
        import urllib.parse
        parsed = urllib.parse.urlparse(url)
        params = urllib.parse.parse_qs(parsed.query)

        signature = params.get("signature", [None])[0]
        expires = params.get("expires", [None])[0]

        if not signature or not expires:
            return False

        # 检查是否过期
        try:
            expire_at = int(expires)
            if int(time.time()) > expire_at:
                return False
        except ValueError:
            return False

        # 重新计算签名并验证
        base_url = url.split("?")[0]
        signature_data = f"{base_url}:{expire_at}"
        expected_signature = hmac.new(
            self.secret_key.encode(),
            signature_data.encode(),
            hashlib.sha256
        ).hexdigest()

        return hmac.compare_digest(signature, expected_signature)

    def add_to_blacklist(self, token: str) -> None:
        """将令牌加入黑名单

        :param token: JWT 令牌
        """
        global _token_blacklist
        _token_blacklist.add(token)

    def is_blacklisted(self, token: str) -> bool:
        """检查令牌是否在黑名单中

        :param token: JWT 令牌
        :return: 是否在黑名单中
        """
        return token in _token_blacklist

    def verify_token_not_blacklisted(self, token: str) -> dict:
        """验证令牌且不在黑名单中

        :param token: JWT 令牌
        :return: 令牌 payload
        :raises: HTTPException 如果令牌无效或在黑名单中
        """
        if self.is_blacklisted(token):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="令牌已失效"
            )
        return self.verify_token(token)
