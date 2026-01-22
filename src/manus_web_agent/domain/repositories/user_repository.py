from abc import ABC, abstractmethod
from typing import Optional

from manus_web_agent.domain.models.user import User


class UserRepository(ABC):
    """User Repository"""

    @abstractmethod
    async def create_user(self, user: User) -> User:
        """创建用户"""
        pass

    @abstractmethod
    async def get_user_by_id(self, user_id: str) -> Optional[User]:
        """根据 ID 获取用户"""
        pass

    @abstractmethod
    async def get_user_by_fullname(self, fullname: str) -> Optional[User]:
        """根据全名获取用户"""
        pass

    @abstractmethod
    async def get_user_by_email(self, email: str) -> Optional[User]:
        """根据邮箱获取用户"""
        pass

    @abstractmethod
    async def update_user(self, user: User) -> None:
        """更新用户"""
        pass

    @abstractmethod
    async def delete_user(self, user_id: str) -> bool:
        """删除用户"""
        pass

    @abstractmethod
    async def list_users(self, limit: int = 100, offset: int = 0) -> list[User]:
        """列出所有用户"""
        pass

    async def fullname_exists(self, fullname: str) -> bool:
        """检查全名是否已存在"""
        pass

    async def email_exists(self, email: str) -> bool:
        """检查邮箱是否已存在"""
        pass
