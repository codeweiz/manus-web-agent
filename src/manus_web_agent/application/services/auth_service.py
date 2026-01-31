"""认证服务"""

import hashlib
import logging
import secrets
from datetime import datetime
from typing import Optional

from manus_web_agent.application.errors.exceptions import (
    ConflictError,
    NotFoundError,
    UnauthorizedError,
    ValidationError,
)
from manus_web_agent.application.services.email_service import EmailService
from manus_web_agent.application.services.token_service import TokenService
from manus_web_agent.core.toml_config import TOML_CONFIG
from manus_web_agent.domain.models.user import User, UserRole
from manus_web_agent.domain.repositories.user_repository import UserRepository

logger = logging.getLogger(__name__)


class AuthService:
    """认证服务，处理用户注册、登录、密码管理等"""

    def __init__(
        self,
        user_repository: UserRepository,
        token_service: TokenService,
        email_service: Optional[EmailService] = None,
    ):
        self._user_repository = user_repository
        self._token_service = token_service
        self._email_service = email_service
        self._auth_provider = getattr(TOML_CONFIG, "auth_provider", "none")

        # 密码哈希配置
        self._password_salt = getattr(
            TOML_CONFIG, "password_salt", secrets.token_hex(16)
        )
        self._password_hash_rounds = getattr(TOML_CONFIG, "password_hash_rounds", 100000)

    def _hash_password(self, password: str) -> str:
        """对密码进行哈希处理"""
        # 使用 PBKDF2 进行密码哈希
        hashed = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            self._password_salt.encode("utf-8"),
            self._password_hash_rounds,
        )
        return hashed.hex()

    def _verify_password(self, password: str, hashed_password: str) -> bool:
        """验证密码"""
        return self._hash_password(password) == hashed_password

    async def register(
        self, fullname: str, email: str, password: str
    ) -> tuple[User, str, str]:
        """用户注册

        :param fullname: 用户全名
        :param email: 邮箱
        :param password: 密码
        :return: 用户对象、访问令牌、刷新令牌
        """
        # 验证输入
        if not fullname or len(fullname) < 2:
            raise ValidationError("姓名至少需要 2 个字符")

        if not email or "@" not in email:
            raise ValidationError("无效的邮箱地址")

        if not password or len(password) < 6:
            raise ValidationError("密码至少需要 6 个字符")

        # 检查邮箱是否已存在
        existing_user = await self._user_repository.get_user_by_email(email)
        if existing_user:
            raise ConflictError("邮箱已被注册")

        # 创建用户
        user = User(
            fullname=fullname,
            email=email,
            password_hash=self._hash_password(password),
            role=UserRole.USER,
            is_active=True,
        )

        await self._user_repository.create_user(user)
        logger.info(f"用户注册成功: {email}")

        # 创建令牌
        access_token, refresh_token = self._token_service.create_token_pair(
            user.id, user.email, user.role.value
        )

        return user, access_token, refresh_token

    async def login(self, email: str, password: str) -> tuple[User, str, str]:
        """用户登录

        :param email: 邮箱
        :param password: 密码
        :return: 用户对象、访问令牌、刷新令牌
        """
        # 查找用户
        user = await self._user_repository.get_user_by_email(email)
        if not user:
            raise UnauthorizedError("邮箱或密码错误")

        if not user.is_active:
            raise UnauthorizedError("账户已被停用")

        # 验证密码
        if not self._verify_password(password, user.password_hash):
            raise UnauthorizedError("邮箱或密码错误")

        # 创建令牌
        access_token, refresh_token = self._token_service.create_token_pair(
            user.id, user.email, user.role.value
        )

        logger.info(f"用户登录成功: {email}")
        return user, access_token, refresh_token

    async def logout(self, token: str) -> bool:
        """用户登出

        :param token: 访问令牌
        :return: 是否成功
        """
        # 将令牌加入黑名单
        self._token_service.add_to_blacklist(token)
        logger.info("令牌已加入黑名单")
        return True

    async def refresh_token(self, refresh_token: str) -> tuple[str, str]:
        """刷新令牌

        :param refresh_token: 刷新令牌
        :return: 新的访问令牌和刷新令牌
        """
        payload = self._token_service.verify_refresh_token(refresh_token)
        user_id = payload.get("sub")

        # 获取用户信息
        user = await self._user_repository.get_user_by_id(user_id)
        if not user or not user.is_active:
            raise UnauthorizedError("无效用户")

        # 创建新令牌
        access_token, new_refresh_token = self._token_service.create_token_pair(
            user.id, user.email, user.role.value
        )

        return access_token, new_refresh_token

    async def change_password(
        self, user_id: str, old_password: str, new_password: str
    ) -> bool:
        """修改密码

        :param user_id: 用户 ID
        :param old_password: 旧密码
        :param new_password: 新密码
        :return: 是否成功
        """
        user = await self._user_repository.get_user_by_id(user_id)
        if not user:
            raise NotFoundError("用户不存在")

        # 验证旧密码
        if not self._verify_password(old_password, user.password_hash):
            raise UnauthorizedError("旧密码错误")

        if len(new_password) < 6:
            raise ValidationError("新密码至少需要 6 个字符")

        # 更新密码
        user.password_hash = self._hash_password(new_password)
        await self._user_repository.update_user(user)

        logger.info(f"用户 {user_id} 修改密码成功")
        return True

    async def change_fullname(self, user_id: str, new_fullname: str) -> bool:
        """修改姓名

        :param user_id: 用户 ID
        :param new_fullname: 新姓名
        :return: 是否成功
        """
        user = await self._user_repository.get_user_by_id(user_id)
        if not user:
            raise NotFoundError("用户不存在")

        if len(new_fullname) < 2:
            raise ValidationError("姓名至少需要 2 个字符")

        user.fullname = new_fullname
        await self._user_repository.update_user(user)

        return True

    async def reset_password(self, email: str, code: str, new_password: str) -> bool:
        """重置密码

        :param email: 邮箱
        :param code: 验证码
        :param new_password: 新密码
        :return: 是否成功
        """
        if not self._email_service:
            raise ValidationError("邮件服务未配置")

        # 验证验证码
        if not await self._email_service.verify_code(email, code, "reset_password"):
            raise ValidationError("无效或已过期的验证码")

        # 查找用户
        user = await self._user_repository.get_user_by_email(email)
        if not user:
            raise NotFoundError("用户不存在")

        if len(new_password) < 6:
            raise ValidationError("新密码至少需要 6 个字符")

        # 更新密码
        user.password_hash = self._hash_password(new_password)
        await self._user_repository.update_user(user)

        logger.info(f"用户 {email} 重置密码成功")
        return True

    async def send_reset_password_code(self, email: str) -> bool:
        """发送重置密码验证码

        :param email: 邮箱
        :return: 是否成功
        """
        if not self._email_service:
            raise ValidationError("邮件服务未配置")

        # 检查用户是否存在
        user = await self._user_repository.get_user_by_email(email)
        if not user:
            raise NotFoundError("用户不存在")

        # 发送验证码
        success = await self._email_service.send_verification_code(
            email, "reset_password"
        )
        if not success:
            raise ValidationError("发送验证码失败")

        return True

    async def verify_token(self, token: str) -> Optional[User]:
        """验证令牌并返回用户

        :param token: 访问令牌
        :return: 用户对象
        """
        try:
            payload = self._token_service.verify_access_token(token)
            user_id = payload.get("sub")
            user = await self._user_repository.get_user_by_id(user_id)
            return user
        except Exception:
            return None

    async def get_user(self, user_id: str) -> Optional[User]:
        """获取用户信息

        :param user_id: 用户 ID
        :return: 用户对象
        """
        return await self._user_repository.get_user_by_id(user_id)

    async def list_users(
        self, page: int = 1, page_size: int = 20
    ) -> tuple[list[User], int]:
        """获取用户列表

        :param page: 页码
        :param page_size: 每页大小
        :return: 用户列表和总数
        """
        return await self._user_repository.list_users(page, page_size)

    async def activate_user(self, user_id: str) -> bool:
        """激活用户

        :param user_id: 用户 ID
        :return: 是否成功
        """
        user = await self._user_repository.get_user_by_id(user_id)
        if not user:
            raise NotFoundError("用户不存在")

        user.is_active = True
        await self._user_repository.update_user(user)
        return True

    async def deactivate_user(self, user_id: str) -> bool:
        """停用用户

        :param user_id: 用户 ID
        :return: 是否成功
        """
        user = await self._user_repository.get_user_by_id(user_id)
        if not user:
            raise NotFoundError("用户不存在")

        user.is_active = False
        await self._user_repository.update_user(user)
        return True
