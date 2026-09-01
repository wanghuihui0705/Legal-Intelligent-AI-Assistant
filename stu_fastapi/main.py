import asyncio
import time
from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

from ai.models.LoadModel import load_fast_model, load_model_stream
from chat.controller.ChatController import chat_router
from chat.controller.HistoryController import history_router
from chat.utils.BM25Util import _load_corpus_from_chroma
from chat.utils.ChromaUtil import get_law_conn
from chat.utils.RerankerUtil import get_reranker
from common.LoggerUtil import Logger
from users.controller.UserController import user_router
# 允许static文件放行,用于一体化前后端
from starlette.staticfiles import StaticFiles
from contextlib import asynccontextmanager

logger = Logger.get_logger()
@asynccontextmanager
async def lifespan(app: FastAPI):
    start = time.time()
    logger.info("===== 生命周期:服务启动 =====")
    # 重活丢线程池，避免阻塞事件循环
    await asyncio.to_thread(get_law_conn)              # Embedding + 向量库
    await asyncio.to_thread(_load_corpus_from_chroma)  # BM25 索引（内部会复用 Chroma 连接）
    # 重排序模型可能 OOM：fail-fast，提前暴露，而不是首次请求时才崩
    await asyncio.to_thread(get_reranker)
    # 下面两个只是预热客户端单例（对象构造），不加载权重
    load_model_stream()
    load_fast_model()

    logger.info(f"===== 所有模型预加载完成,耗时{time.time()-start:.2f}s =====")
    yield
    logger.info("===== 服务关闭，释放资源 =====")

# 替换掉你原来的 app = FastAPI()
app = FastAPI(lifespan=lifespan)
# 跨域配置(客户端端口号为63342)
app.add_middleware(
    CORSMiddleware,
    # allow_origins=["http://localhost:63342"],# stu_front客户端的端口号是63342
    allow_origins=["http://localhost:8080"],# rag_app客户端的端口号是8080
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# 引入users模块的子路由
"""
    include_router 方法参数：
        1、router：引入的子路由 --- 子路由的名字APIRouter对象的名字
        2、prefix：访问子路由的时候添加在前面的前缀
        3、tags：在swaggerUI中分组的名字
"""
app.include_router(router=user_router, prefix="/users", tags=["users"])
app.include_router(router=chat_router, prefix="/chat", tags=["chat"])
app.include_router(router=history_router, prefix="/history", tags=["history"])
@app.get("/")
async def root():
    return {"message":"xxx"}

# 访问静态资源放行
# app.mount("/static", app=StaticFiles(directory="static"), name="static")

#允许html放行(在controller的jinjas模板中设置)



if __name__=='__main__':
    # uvicorn main:app --host 127.0.0.1 --port 8000
    import uvicorn
    uvicorn.run(
        "main:app",
        host="localhost",
        #服务器端口号
        port=8000,
        reload=False
    )