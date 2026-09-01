import os
# ========== 必须放在最顶部，所有 import 之前 ==========
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"
# 强制离线模式：跳过所有网络检查，直接读取本地缓存
os.environ["HF_HUB_OFFLINE"] = "1"
# 关闭符号链接警告
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
from FlagEmbedding import FlagReranker
# 重排序模型名称
reranker_name = "BAAI/bge-reranker-base"
reranker_path =os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))),"models","bge-reranker-base")


_reranker_instance = None
def get_reranker():
    global _reranker_instance
    if _reranker_instance is None:
        print("RerankerUtil:尝试首次加载重排序模型...")
        _reranker_instance=FlagReranker(
            model_name_or_path = reranker_path,
            use_fp16 = True,
            device = "cuda",
            # 离线下载好重排序模型就不需要这个参数:cache_dir = reranker_path,
        )
        print("RerankerUtil:重排序模型已获取")
    else:
        print("RerankerUtil:重排序模型已存在,不再重复加载")
    return _reranker_instance
if __name__=="__main__":
    reranker_model=get_reranker()
