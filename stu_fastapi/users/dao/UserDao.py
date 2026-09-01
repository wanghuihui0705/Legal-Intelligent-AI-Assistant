'''
数据访问层,Data Access Object
写数据库操作.负责封装SQL查询,增删改
提供按ID/name查询用户,批量插入等原始数据操作
不包含业务逻辑,只是对数据库的轻薄封装
'''
from common import MYSQLUtil
# 用户登录需要用到数据库的查询操作,因此这里封装一个查询函数,供service调用
def find_users_by_username(username:str):
    conn=MYSQLUtil.mysql_conn()
    cur=conn.cursor()
    #开始查询
    #反引号专门用来包裹`表名`,`字段`,`库名`这些数据库对象名称
    sql="select * from `users` where `username`=%s"
    #cur.execute的第二个参数必须是元组/列表
    cur.execute(sql,[username])
    result=cur.fetchall()
    MYSQLUtil.mysql_close(cur,conn)
    #直接返回查询的结果,不做任何其他事情
    return result
if __name__=='__main__':
    rs=find_users_by_username("wyh") #[{'id': 1, 'username': 'wyh', 'password': '123456'}]
    # rs=find_users_by_username("cc") #()
    print(rs)