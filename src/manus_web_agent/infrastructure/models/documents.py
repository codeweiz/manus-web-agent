"""MongoDB 文档模型（使用 Beanie ODM）"""

from datetime import datetime
from typing import List, Optional

from beanie import Document, Indexed
from pydantic import Field

from manus_web_agent.domain.models.agent import Agent
from manus_web_agent.domain.models.event import AgentEvent
from manus_web_agent.domain.models.file import FileInfo
from manus_web_agent.domain.models.session import Session, SessionStatus
from manus_web_agent.domain.models.user import User, UserRole


class BaseDocument(Document):
    """基础文档类"""

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        is_base = True

    async def update_timestamp(self):
        """更新修改时间"""
        self.updated_at = datetime.utcnow()


class UserDocument(BaseDocument):
    """用户文档"""

    user_id: Indexed(str, unique=True)
    email: Indexed(str, unique=True)
    fullname: str
    password_hash: str
    role: str = Field(default="user")
    is_active: bool = Field(default=True)

    class Settings:
        name = "users"

    @classmethod
    def from_domain(cls, user: User) -> "UserDocument":
        """从领域模型创建文档"""
        return cls(
            user_id=user.id,
            email=user.email,
            fullname=user.fullname,
            password_hash=user.password_hash,
            role=user.role.value,
            is_active=user.is_active,
            created_at=user.created_at or datetime.utcnow(),
            updated_at=user.updated_at or datetime.utcnow(),
        )

    def to_domain(self) -> User:
        """转换为领域模型"""
        return User(
            id=self.user_id,
            email=self.email,
            fullname=self.fullname,
            password_hash=self.password_hash,
            role=UserRole(self.role),
            is_active=self.is_active,
            created_at=self.created_at,
            updated_at=self.updated_at,
        )


class AgentDocument(BaseDocument):
    """Agent 文档"""

    agent_id: Indexed(str, unique=True)
    user_id: Indexed(str)
    model_name: str = Field(default="deepseek-chat")
    temperature: float = Field(default=0.7)
    memories: dict = Field(default_factory=dict)

    class Settings:
        name = "agents"

    @classmethod
    def from_domain(cls, agent: Agent) -> "AgentDocument":
        """从领域模型创建文档"""
        return cls(
            agent_id=agent.id,
            user_id=agent.user_id,
            model_name=agent.model_name,
            temperature=agent.temperature,
            memories=agent.memories or {},
            created_at=agent.created_at or datetime.utcnow(),
            updated_at=agent.updated_at or datetime.utcnow(),
        )

    def to_domain(self) -> Agent:
        """转换为领域模型"""
        return Agent(
            id=self.agent_id,
            user_id=self.user_id,
            model_name=self.model_name,
            temperature=self.temperature,
            memories=self.memories,
            created_at=self.created_at,
            updated_at=self.updated_at,
        )


class SessionDocument(BaseDocument):
    """会话文档"""

    session_id: Indexed(str, unique=True)
    agent_id: str
    user_id: Indexed(str)
    title: Optional[str] = None
    status: str = Field(default="pending")
    events: List[dict] = Field(default_factory=list)
    files: List[dict] = Field(default_factory=list)
    is_shared: bool = Field(default=False)
    sandbox_id: Optional[str] = None
    task_id: Optional[str] = None
    latest_message: Optional[str] = None
    latest_message_at: Optional[datetime] = None
    unread_message_count: int = Field(default=0)

    class Settings:
        name = "sessions"

    @classmethod
    def from_domain(cls, session: Session) -> "SessionDocument":
        """从领域模型创建文档"""
        return cls(
            session_id=session.id,
            agent_id=session.agent_id,
            user_id=session.user_id,
            title=session.title,
            status=session.status.value,
            events=[event.model_dump() for event in session.events] if session.events else [],
            files=[file.model_dump() for file in session.files] if session.files else [],
            is_shared=session.is_shared,
            sandbox_id=session.sandbox_id,
            task_id=session.task_id,
            latest_message=session.latest_message,
            latest_message_at=session.latest_message_at,
            unread_message_count=session.unread_message_count,
            created_at=session.created_at or datetime.utcnow(),
            updated_at=session.updated_at or datetime.utcnow(),
        )

    def to_domain(self) -> Session:
        """转换为领域模型"""
        from pydantic import TypeAdapter

        events = []
        for event_data in self.events:
            try:
                event = TypeAdapter(AgentEvent).validate_python(event_data)
                events.append(event)
            except Exception:
                pass

        files = [FileInfo(**file_data) for file_data in self.files]

        return Session(
            id=self.session_id,
            agent_id=self.agent_id,
            user_id=self.user_id,
            title=self.title,
            status=SessionStatus(self.status),
            events=events,
            files=files,
            is_shared=self.is_shared,
            sandbox_id=self.sandbox_id,
            task_id=self.task_id,
            latest_message=self.latest_message,
            latest_message_at=self.latest_message_at,
            unread_message_count=self.unread_message_count,
            created_at=self.created_at,
            updated_at=self.updated_at,
        )
