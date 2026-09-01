#创建Chroma对象,指向刚刚建立好的法律知识向量库
import os

from common.LoggerUtil import Logger

# ========== 必须放在最顶部，所有 import 之前 ==========
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"
# # 强制离线模式：跳过所有网络检查，直接读取本地缓存
os.environ["HF_HUB_OFFLINE"] = "1"
# # 关闭符号链接警告
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings

root_path=os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
# embedding_model_name='sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2'
# 会从huggingface里面下载放进去

# ====== 新增：模块级全局缓存，整个进程内唯一 ======
_embedding_model = None
_vector_db = None
embedding_model_path = os.path.join(root_path, "models", "embedding")
logger = Logger.get_logger()
def get_law_conn():
    vector_db_path = os.path.join(root_path, "vector_db", "law_knowledge_base.db")
    collection_name = 'law_knowledge_base'

    # 向量化模型
    global _embedding_model, _vector_db
    # 1. 只在第一次调用时加载向量化模型（占内存的核心）
    if _embedding_model is None:
        _embedding_model = HuggingFaceEmbeddings(
            model_name = embedding_model_path,
            model_kwargs = {
                "local_files_only": True,
                "device": "cuda"
            },
        )
        logger.info("ChromaUtil:向量化模型加载成功")
    else:
        logger.info("ChromaUtil:向量化模型已存在")
    # 2. 只在第一次调用时初始化向量数据库连接
    if _vector_db is None:
        #获取向量数据库检索对象
        _vector_db=Chroma(
            persist_directory=vector_db_path,
            collection_name = collection_name,
            embedding_function=_embedding_model
        )
        logger.info("ChromaUtil:向量检索对象创建成功")
        return _vector_db
    else:
        logger.info("ChromaUtil:向量检索对象已存在")
    return _vector_db



def get_embedding_model():
    """对外暴露向量化模型，供 HyDE 等需要手动 embed 文本的场景使用"""
    if _embedding_model is None:
        get_law_conn()  # 保证 _embedding_model 已加载
    logger.info("ChromaUtil:向量化模型已存在")
    return _embedding_model

if __name__=="__main__":
    # retriever=get_law_conn(10)
    # print(retriever.invoke("公安机关接到家庭暴力报案后应当做什么事情？"))# 仅仅是纯向量相似度匹配搜索,直接打印数据库中的10条Document数据
    # print(retriever.invoke("糖尿病的风险")) #虽然法律数据集中没有这个的回答,但是检索器还是会无脑丢出来它认为最接近的回答,这就是为什么要出现重排序以及大模型自然语言回答的原因
    try:
        retriever = get_law_conn().as_retriever(search_kwargs={"k": 10})
        print(retriever.invoke("公安机关接到家庭暴力报案后应当做什么事情？"))
    except Exception as e:
        print(f"出错了: {e}")