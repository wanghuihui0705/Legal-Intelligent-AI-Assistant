"""查询重写：把用户原始问题改写成独立、检索友好的查询语句
解决口语化、指代不明（"它/这个/上述"）、过短导致的召回差
"""
import os
# ========== 必须放在最顶部，所有 import 之前 ==========
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"

from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from ai.models import LoadModel
from common.LoggerUtil import Logger

logger = Logger.get_logger()
QUERY_REWRITE_TEMPLATE = """你是一个专业的法律检索查询改写助手。
任务：把用户的原始问题改写成一句【独立、完整、检索友好】的查询语句，用于在法条知识库中检索。

改写规则：
1. 若问题含指代词（如"它""这个""上述""这种情况"），请结合【对话历史】还原成具体对象。
2. 补充缺失的主语、宾语，把口语化表述转成书面、规范的法律表述。
3. 保留核心法律概念，不要新增问题中不存在的事实。
4. 只输出改写后的一句话，不要解释、不加引号、不加"改写后："等前缀。

【对话历史】
{history_chat}

【用户问题】
{question}

改写后的查询："""


def rewrite_query(question: str, history_chat: str = "") -> str:
    """调用高速小模型（本地 Ollama）把问题改写成独立查询语句（非流式）"""
    llm = LoadModel.load_fast_model()
    prompt = PromptTemplate(
        template=QUERY_REWRITE_TEMPLATE,
        input_variables=["question", "history_chat"],
    )
    chain = prompt | llm | StrOutputParser()
    rewritten = chain.invoke({"question": question, "history_chat": history_chat}).strip()
    logger.info(f"QueryRewriteUtil：原文: {question}\nQueryRewriteUtil：改写: {rewritten}")
    return rewritten


if __name__ == "__main__":
    print(rewrite_query("它要承担什么责任？",
                        "用户：签了劳动合同后公司随意辞退我\n助手：这属于违法解除劳动合同"))
