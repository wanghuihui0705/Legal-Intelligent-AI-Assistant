'''
entity-实体层(Pydantic Schema)
定义请求/响应的数据形状
'''
from pydantic import BaseModel,Field

class Users(BaseModel):
    username:str=Field(...,description="用户名")
    password:str=Field(...,description="用户密码")

