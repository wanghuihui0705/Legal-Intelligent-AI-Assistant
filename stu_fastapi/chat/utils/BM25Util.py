"""BM25 关键词检索器，与向量检索互补"""
import os
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
import jieba
from rank_bm25 import BM25Okapi
from langchain_core.documents import Document
from chat.utils import ChromaUtil
from chat.utils.LegalSynonymUtil import expand_tokens
# ===== 单例缓存 =====
_bm25_index = None          # BM25Okapi 实例
_corpus_docs = None         # Chromadb带属性的文档字典
from common.LoggerUtil import Logger

logger = Logger.get_logger()
def _load_corpus_from_chroma():
    """
    从 Chroma 集合中加载全部文档作为 BM25 语料。
    只在首次调用时执行一次。
    """
    global _bm25_index, _corpus_docs
    # 改后：直接拿 ChromaUtil 已经建好的连接
    vector_db = ChromaUtil.get_law_conn()
    _corpus_docs = vector_db.get()  # 返回 {"ids": [...], "documents": [...], "metadatas": [...]}
    # 对每条文档分词
    tokenized_corpus = []
    for doc_text in _corpus_docs["documents"]:
        tokens = list(jieba.cut(doc_text))
        tokenized_corpus.append(expand_tokens(tokens))

    _bm25_index = BM25Okapi(tokenized_corpus)
    logger.info(f"BM25Util：[BM25]索引和语料库构建完成，共 {len(_corpus_docs['documents'])} 篇文档")


def bm25_search(question: str, k: int = 5)->list:
    """
    返回 top-k 匹配的 LangChain Document 列表。
    首次调用会自动加载语料并构建索引。
    """
    # BM25索引对象 ， BM25语料库
    global _bm25_index, _corpus_docs

    # 确保只加载一次BM索引对象和一次语料库（从chromadb中加载文档）
    if _bm25_index is None:
        _load_corpus_from_chroma()
    else:
        logger.info("BM25Util:BM25索引对象+BM25语料库已存在")
    # 对问题进行分词 + 同义词扩充 + 在语料库中进行词语检索
    tokenized_query = expand_tokens(list(jieba.cut(question)))
    logger.info(f"BM25Util：查询分词+同义词扩充: {tokenized_query}")
    # 使用BM25打分公式进行打分
    scores = _bm25_index.get_scores(tokenized_query)

    # 构造 LangChain Document 列表
    # 取 top-k 的索引
    top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:k]


    results = []
    for idx in top_indices:
        if scores[idx] > 0:  # 只保留有匹配的
            # 重新包装成 LangChain Document
            doc = Document(
                id = _corpus_docs["ids"][idx],  # ★ 加这行
                page_content = _corpus_docs["documents"][idx],
                metadata = _corpus_docs["metadatas"][idx] or {},
            )
            doc.metadata["bm25_score"] = round(float(scores[idx]), 4)
            results.append(doc)
    # result数据类型为 list[Document(id,page_content,metadata("bm25_score","不重要的"))]
    # 用于RRF算法
    return results


if __name__ == "__main__":
    docs = bm25_search("公安机关接到家庭暴力报案后应当做什么事情？", 5)
    # 打印BM25检索出来的文档和分数
    for i, doc in enumerate(docs, 1):
        print(f"[{i}] 分数={doc.metadata.get('bm25_score')} | {doc.page_content[:100]}")
