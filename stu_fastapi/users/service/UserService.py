'''
service-业务逻辑层
负责多个DAO调用
处理业务逻辑: 如用户不存在,重复等
事务管理,数据转换
反正就是整个模块的大脑,写真正的业务代码
'''
from users.dao.UserDao import find_users_by_username
from common import ResponseUtil

# 登录功能-提供给用户
def login(users):
    username = users.username
    password = users.password
    # 用户点击登录按钮时传来的请求中的users是否为空或者不完整
    if not username or not password:
        return ResponseUtil.response_json(500, "账号或密码不能为空", None)
    rs = find_users_by_username(username)
    # 传来的请求中的users里面的名字是否不存在
    if not rs:
        return ResponseUtil.response_json(500, "用户不存在", None)
    # 传来的请求中的users里面的密码是否正确
    if rs[0]["password"] != password:
        return ResponseUtil.response_json(500, "用户名不正确或者密码错误", None)
    # 都正确
    # code 给前端判断是否登录成功, msg 前端提示语, data 用户的唯一标识 id
    return ResponseUtil.response_json(200, "登录成功", rs[0]["id"])

if __name__ == '__main__':
    # 直接造一个带属性的对象,一行搞定
    req = type('obj', (), {'username': 'wyh', 'password': '123456'})
    print(login(req))




























