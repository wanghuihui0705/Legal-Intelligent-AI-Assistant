from fastapi import APIRouter

from chat.entity.HistoryEntity import SaveExchangeRequest, DeleteConversationRequest
from chat.service import HistoryService

history_router=APIRouter()
# 非流失
@history_router.get("/list")
def getSidebarChat(user_id)->dict:
    return HistoryService.get_sidebar_chat(user_id)
@history_router.get("/detail")
def getDetailChat(history_id)->dict:
    return HistoryService.get_detail_chat(history_id)
@history_router.post("/saveExchange")
def save_exchange(req: SaveExchangeRequest)->dict:
    return HistoryService.save_exchange(req.user_id, req.parent_id, req.question, req.answer)
@history_router.post("/deleteConversation")
def delete_conversation(req: DeleteConversationRequest):
    """删除对话（根+追问）"""
    return HistoryService.delete_conversation(req.history_id, req.user_id)
if __name__=="__main__":
    # print(getSidebarChat(1))
    print(getDetailChat(4)) #{'code': 200, 'msg': '该用户在这个对话下的所有历史问题', 'data': [{}，{}]