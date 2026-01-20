from typing import List

from pydantic import BaseModel, Field


class Message(BaseModel):
    """消息"""

    message: str = Field(default="", description="消息内容")

    attachments: List[str] = Field(default_factory=list, description="附件")
