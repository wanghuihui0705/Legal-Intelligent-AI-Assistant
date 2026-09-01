from fastapi import APIRouter,Request
from starlette.responses import StreamingResponse, HTMLResponse
from chat.service import ChatService
# 重点：方法一:从templates包导入实例化好的templates对象
from templates import templates
# #方法二
# from fastapi.templating import Jinja2Templates
# # 指定html页面存放的文件夹名字就是 templates
# templates = Jinja2Templates(directory="templates")
chat_router=APIRouter()

# 流式聊天
@chat_router.get("/chatStream")
def chat_stream(question:str,parent_id: int = 0):
    """
    parent_id: 0=新对话,那么就没有历史对话， 非0=时，为追问所属的根history_id
        StreamingResponse：流式输出对象，参数：
        1、生成器对象
        2、媒体类型 --- 不同的返回类型数据值不一样
    """
    return StreamingResponse(
        content=ChatService.chat_stream(question,parent_id),
        media_type="text/event-stream" ## 这就是告诉浏览器：我正在用 SSE 协议！
    )


# 流式聊天-- neo4j
@chat_router.get("/chatStreamNoe4j")
def chat_stream_noe4j(question:str,parent_id: int = 0):

    return StreamingResponse(
        content=ChatService.chat_stream_noe4j(question,parent_id),
        media_type="text/event-stream" ## 这就是告诉浏览器：我正在用 SSE 协议！
    )




# HTML-如果前后端都放在stu_fastapi中==================================================================
# 手动在浏览器中输入http://localhost:8000/chat/goChatNoStream 会触发执行go_chat_no_stream函数
@chat_router.get("/goChatNoStream", response_class=HTMLResponse)
def go_chat_no_stream(request: Request):
    # request：请求对象
    # name：访问页面的名字，从templates开始算路径
    #服务器返回chat_no_stream.html给浏览器
    return templates.TemplateResponse(request, "chat_no_stream.html")

# 手动在浏览器中输入http://localhost:8000/chat/goChatStream 会触发执行go_chat_stream函数
@chat_router.get("/goChatStream", response_class=HTMLResponse)
def go_chat_stream(request: Request):
    # request：请求对象
    # name：访问页面的名字，从templates开始算路径
    #服务器返回chat_stream.html给浏览器
    return templates.TemplateResponse(request, "chat_stream.html")