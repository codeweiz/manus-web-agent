"""User MongoDB 仓库实现"""

import logging
from typing import Optional, List, Tuple

from manus_web_agent.domain.models.user import User
from manus_web_agent.domain.repositories.user_repository import UserRepository
from manus_web_agent.infrastructure.models.documents import UserDocument

logger = logging.getLogger(__name__)


class MongoUserRepository(UserRepository):
    """User MongoDB 仓库"""

    async def create_user(self, user: User) -> None:
        """创建用户"""
        doc = UserDocument.from_domain(user)
        await doc.insert()
        logger.info(f"创建用户 {user.email}")

    async def update_user(self, user: User) -> None:
        """更新用户"""
        doc = await UserDocument.find_one(UserDocument.user_id == user.id)
        if doc:
            doc.email = user.email
            doc.fullname = user.fullname
            doc.password_hash = user.password_hash
            doc.role = user.role.value
            doc.is_active = user.is_active
            await doc.save()
            logger.info(f"更新用户 {user.email}")

    async def delete_user(self, user_id: str) -> None:
        """删除用户"""
        doc = await UserDocument.find_one(UserDocument.user_id == user_id)
        if doc:
            await doc.delete()
            logger.info(f"删除用户 {user_id}")

    async def get_user_by_id(self, user_id: str) -> Optional[User]:
        """根据 ID 获取用户"""
        doc = await UserDocument.find_one(UserDocument.user_id == user_id)
        return doc.to_domain() if doc else None

    async def get_user_by_fullname(self, fullname: str) -> Optional[User]:
        """根据姓名获取用户"""
        doc = await UserDocument.find_one(UserDocument.fullname == fullname)
        return doc.to_domain() if doc else None

    async def get_user_by_email(self, email: str) -> Optional[User]:
        """根据邮箱获取用户"""
        doc = await UserDocument.find_one(UserDocument.email == email)
        return doc.to_domain() if doc else None

    async def list_users(self, page: int = 1, page_size: int = 20) -> Tuple[List[User], int]:
        """获取用户列表

        :param page: 页码
        :param page_size: 每页大小
        :return: 用户列表和总数
        """
        skip = (page - 1) * page_size
        docs = await UserDocument.find_all().skip(skip).limit(page_size).to_list()
        total = await UserDocument.find_all().count()
        return [doc.to_domain() for doc in docs], total

    async def fullname_exists(self, fullname: str) -> bool:
        """检查姓名是否存在"""
        count = await UserDocument.find(UserDocument.fullname == fullname).count()
        return count > 0

    async def email_exists(self, email: str) -> bool:
        """检查邮箱是否存在"""
        count = await UserDocument.find(UserDocument.email == email).count()
        return count > 0
