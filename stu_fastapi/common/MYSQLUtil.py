'''
工具类/辅助函数
放通用辅助代码。 跟具体业务无关的横切关注点：
如:数据库连接管理
如:密码哈希、JWT 令牌生成/解析
通用格式化函数、常量定义等
'''
import pymysql


# 获取连接
def mysql_conn():
    conn=pymysql.connect(
        user='root',
        password='123456',
        host='127.0.0.1',
        port=3306,
        charset='utf8mb4',
        database="feifan_ai",
        #获取字典数据类型
        cursorclass=pymysql.cursors.DictCursor
    )
    print("数据库连接已开启")
    #把连接对象返回
    return conn
# 关闭连接
def mysql_close(cur,con):
    # 先关闭cur(游标对象)
    cur.close()
    # 再关闭con(连接对象)
    con.close()
    print("数据库连接已关闭")

if __name__ == '__main__':
    conn=mysql_conn()
    cur=conn.cursor()
    mysql_close(cur,conn)


