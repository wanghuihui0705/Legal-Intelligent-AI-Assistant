from chat.dao import HistoryDao
from common import ResponseUtil

def get_sidebar_chat(user_id:int):
    rs=HistoryDao.find_root_history_by_userid(user_id) #列表
    if not rs:
        return ResponseUtil.response_json(200,"该用户没有任何提问记录","")
    # 存储数据的列表
    history_list = []
    for item in rs:
        history_list.append({
            #为什么要用小驼峰??明明表字段是下划线呀
            'historyId':item['history_id'],
            'question': item['question'],
            'answer': item['answer'],
            'createTime': item['create_time'].strftime('%Y-%m-%d %H:%M:%S')
        })
    return ResponseUtil.response_json(200,"侧边栏有该用户的历史根问题",history_list)

def get_detail_chat(history_id:int):
    rs=HistoryDao.find_history_by_historyid(history_id) #列表
    if not rs:
        return ResponseUtil.response_json(500,"出错了","")
    # 存储数据的列表
    history_list = []
    for item in rs:
        history_list.append({
            #为什么要用小驼峰??明明表字段是下划线呀
            'historyId':item['history_id'],
            'question': item['question'],
            'answer': item['answer'],
            'createTime': item['create_time'].strftime('%Y-%m-%d %H:%M:%S')
        })
    return ResponseUtil.response_json(200,"成功查询该用户在这个对话下的所有历史问题",history_list)

def save_exchange(user_id: int, parent_id: int, question: str, answer: str) -> dict:
    """保存一轮问答或者新对话"""
    if not user_id or not question or not answer:
        return {"code": 500, "msg": "参数不完整", "data": None}
    new_id = HistoryDao.insert_open_history(user_id, parent_id, question, answer)
    return {"code": 200, "msg": "保存成功", "data": new_id}
def delete_conversation(history_id: int, user_id: int) -> dict:
    """删除对话"""
    affected = HistoryDao.delete_history(history_id, user_id)
    if affected == 0:
        return {"code": 500, "msg": "对话不存在或无权删除", "data": None}
    return {"code": 200, "msg": f"已删除 {affected} 条记录", "data": None}
if __name__=="__main__":
    rs=get_sidebar_chat(user_id=1)
    print(rs)