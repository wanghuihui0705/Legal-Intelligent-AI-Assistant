'''
全局服务器返回的必须是json结构,必须使用双引号
字典(<class 'dict'>):{'username': 'wyh', 'password': '123456', 'code': 200}
json(<class 'str'>): {
  "username": "wyh",
  "password": "123456",
  "code": 200
}
'''
def response_json(code:int,msg:str,data:str):
    # json必须使用双引号
    return {
        "code":code,
        "msg":msg,
        "data":data
    }