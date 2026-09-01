"""HyDE（Hypothetical Document Embeddings）假设性文档嵌入
先用 LLM 生成"假设答案/假设文档"，再用它的向量去检索，
缓解"短查询 vs 长文档"向量漂移问题。
"""
import os
# ========== 必须放在最顶部，所有 import 之前 ==========
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"

from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from ai.models import LoadModel
from chat.utils import ChromaUtil
from common.LoggerUtil import Logger

logger = Logger.get_logger()
HYDE_TEMPLATE = """你是一个专业的法律知识助手。
请根据用户问题，写一小段【假设性的法律知识库条目】，模拟它可能的答案内容。

要求：
1. 内容要像一条法条/司法解释/法律知识的摘录，包含关键词和专业术语。
2. 80~150 字，直接写正文，不加标题、编号、解释或"假设条目："等前缀。
3. 不确定的细节可概括，但不要写与问题无关的内容。

用户问题：{question}

假设条目："""


def generate_hypothetical_doc(question: str) -> str:
    """非流式生成假设性文档"""
    llm = LoadModel.load_model_no_stream()
    prompt = PromptTemplate(template=HYDE_TEMPLATE, input_variables=["question"])
    chain = prompt | llm | StrOutputParser()
    hypo = chain.invoke({"question": question}).strip()
    logger.info(f"HyDEUtil：假设文档: {hypo}")
    return hypo


def hyde_search(question: str, k: int = 10) -> list:
    """生成假设文档 -> 用假设文档向量检索 -> 返回 Document 列表"""
    hypo_doc = generate_hypothetical_doc(question)
    vector_db = ChromaUtil.get_law_conn()
    embedding_model = ChromaUtil.get_embedding_model()
    # 关键：把"假设文档"当作查询向量，而不是用户原问题向量
    query_vec = embedding_model.embed_query(hypo_doc)
    docs = vector_db.similarity_search_by_vector(query_vec, k=k)
    logger.info(f"HyDEUtil：向量检索到 {len(docs)} 篇")
    return docs


if __name__ == "__main__":
    for i, d in enumerate(hyde_search("公安机关接到家庭暴力报案后应当做什么事情？"), 1):
        print(f"[{i}] {d.page_content[:100]}")
