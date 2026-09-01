from pydantic import BaseModel, Field

class SaveExchangeRequest(BaseModel):
    """保存一轮问答的请求体"""
    user_id: int = Field(..., description="用户ID")
    parent_id: int = Field(default=0, description="0=新对话根提问, 非0=追问所属的根history_id")
    question: str = Field(..., description="用户提问内容")
    answer: str = Field(..., description="AI完整回复")


class DeleteConversationRequest(BaseModel):
    """删除对话的请求体"""
    history_id: int = Field(..., description="要删除的对话根history_id")
    user_id: int = Field(..., description="用户ID（防越权）")