from common import MYSQLUtil

def find_root_history_by_userid(user_id:int)->list:
    '''
    查询该用户的所有根问题（用于前端侧边栏显示），按时间降序
    [{'history_id': 4, 'question': '我刚刚问了你什么', 'answer': '很抱歉,这是你第一次提问我', 'create_time': datetime.datetime(2026, 6, 28, 21, 29, 2), 'history_fk_users': '1'},{},{}]
    '''
    conn=MYSQLUtil.mysql_conn()
    cur=conn.cursor()
    sql= """
        SELECT history_id,question,answer,create_time
        FROM history
        WHERE history_fk_users = %s AND parent_id = 0
        ORDER BY create_time DESC
    """
    cur.execute(sql,[user_id])
    result=cur.fetchall()
    MYSQLUtil.mysql_close(cur,conn)
    return result
def find_history_by_historyid(history_id: int) -> list:
    """
    查某个对话的全部 Q&A：根 + 所有追问，按时间正序
    [{'history_id': 1, 'question': '你好,我叫李华', 'answer': 'hello 你好', 'parent_id': 0, 'create_time': datetime.datetime(2026, 6, 28, 21, 13, 28)}, {},{}]
    """
    conn=MYSQLUtil.mysql_conn()
    cur=conn.cursor()
    sql="""
        SELECT history_id, question, answer, parent_id, create_time
        FROM history
        WHERE history_id = %s OR parent_id = %s
        ORDER BY create_time ASC
    """
    cur.execute(sql,[history_id,history_id])
    result=cur.fetchall()
    MYSQLUtil.mysql_close(cur,conn)
    return result


def insert_open_history(user_id:int,parent_id:str,question:str,answer:str)->int:
    '''
        在已有的根问题中插入一条 Q&A 追问，返回 history_id
        不用传时间,因为数据库那边设置了时间不为null且默认值为:CURRENT_TIMESTAMP
    '''
    conn=MYSQLUtil.mysql_conn()
    cur=conn.cursor()
    sql="""
        INSERT INTO history (question, answer, parent_id, history_fk_users)
        VALUES (%s, %s, %s, %s)
    """
    cur.execute(sql, [question, answer, parent_id, user_id])
    conn.commit()
    # 获取最新的id
    new_history_id=cur.lastrowid
    MYSQLUtil.mysql_close(cur,conn)
    return new_history_id

def delete_history(history_id: int, user_id: int) -> int:
    """删根 + 所有追问，返回删除总行数"""
    conn = MYSQLUtil.mysql_conn()
    cur = conn.cursor()
    sql = """
        DELETE FROM history
        WHERE (history_id = %s OR parent_id = %s)
          AND history_fk_users = %s
    """
    cur.execute(sql, [history_id, history_id, user_id])
    conn.commit()
    # 返回最近一次执行的 SQL 语句所影响的数据行数
    affected = cur.rowcount
    MYSQLUtil.mysql_close(cur, conn)
    return affected

if __name__=='__main__':
    rs=find_root_history_by_userid(1)
    print(f"userid为1的用户的所有根问题\n{rs}")
    rs=find_history_by_historyid(1)
    print(f"userid为1且根历史为1的用户的所有问题\n{rs}")