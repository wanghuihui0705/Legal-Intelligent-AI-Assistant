'''
controller 控制器层(接口层)
写路由和请求处理
1.定义API路由
2.接收和校验HTTP请求参数(路径参数,查询参数,请求体)
3.调用service,拿到结果后返回给HTTP响应
'''
from fastapi import APIRouter
from users.entity.Users import Users
from users.service import UserService
#定义一个子路由
user_router=APIRouter()

@user_router.post("/login")
def login(user:Users):
    return UserService.login(user)
