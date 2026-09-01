'''
登录后,用户可以使用'聊天功能'
以下是业务代码
'''
import os
import time

from common.LoggerUtil import Logger

# ========== 必须放在最顶部，所有 import 之前 ==========
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"
# 强制离线模式：跳过所有网络检查，直接读取本地缓存
os.environ["HF_HUB_OFFLINE"] = "1"
# 关闭符号链接警告
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
import json
from chat.dao import HistoryDao
from ai.models import LoadModel
from langchain_core.prompts import PromptTemplate
from chat.utils import ChromaUtil
from chat.utils import RerankerUtil
from langchain_core.runnables import RunnablePassthrough, RunnableParallel, RunnableLambda
from langchain_core.output_parsers import StrOutputParser
from chat.utils import BM25Util
#Neo4j 导入库
from chat.utils import Neo4jUtil
from langchain_neo4j import GraphCypherQAChain
# 检索增强配置
from chat.utils import QueryRewriteUtil
from chat.utils import HyDEUtil
from dotenv import load_dotenv
load_dotenv() # 项目启动前读取.env
# ========== 检索增强开关（可用环境变量控制，便于 A/B 测试） ==========
ENABLE_QUERY_REWRITE = os.getenv("ENABLE_QUERY_REWRITE", "true").lower() == "true"
ENABLE_HYDE = os.getenv("ENABLE_HYDE", "true").lower() == "true"

logger = Logger.get_logger()
# ========== 分类提示词 ==========
CLASSIFY_TEMPLATE = """
    你是一个问题分类助手。判断以下问题是否属于法律领域。

    法律领域包括但不限于：刑法、民法、行政法、婚姻法、合同法、劳动法、
    侵权责任、知识产权、交通法规、治安管理、诉讼程序、公安执法等。

    如果问题涉及法律、法规、权利义务、纠纷处理、执法程序等，返回 true。
    如果问题与法律完全无关（如：数学计算、日常生活、科技、娱乐等），返回 false。

    请只用 "true" 或 "false" 回答，不要输出其他内容。

    问题：{question}
"""
# ========== 非法律问题的提示词 ==========
DIRECT_TEMPLATE = """
    你是一个乐于助人的通用问答助手。
    
    用户当前的问题**不属于法律领域**，请用你的通用知识直接回答。
    如果问题涉及医疗、投资等专业领域，请提醒用户咨询专业人士。
    
    对话历史:{history_chat}
    用户问题：{question}
"""
# ========== 法律问题的提示词 ==========
RAG_TEMPLATE="""
        你是一个专业的法律问答助手。
        请根据提供的参考资料回答用户的法律问题。
        【规则】
        - 优先基于上下文信息回答
        - 如果上下文中未提及相关内容，请明确回复："资料中未提及相关内容"
        - 回答要准确、简洁
        
        【对话历史】
        {history_chat}
        【参考资料】
        {context}    
        【用户问题】
        {question}
        请直接输出最终答案
"""
# 加载记忆
def load_history_chat(parent_id: int) -> str:
    """加载parent_id的根与追问对话历史，格式化为上下文字符串"""
    if parent_id == 0:
        return "暂无对话历史"
    history_list = HistoryDao.find_history_by_historyid(parent_id)
    parts = []
    for item in history_list:
        parts.append(f"用户：{item['question']}")
        parts.append(f"助手：{item['answer']}")
    return "\n".join(parts)
# 判断是否为法律问题
def is_legal_question(question: str) -> bool:
    """前置判断：是否为法律问题"""
    # 方法一:在线大模型判断
    # llm = LoadModel.load_model_no_stream()
    # prompt = PromptTemplate(template=CLASSIFY_TEMPLATE, input_variables=["question"])
    # chain = prompt | llm | StrOutputParser()
    # result = chain.invoke(question).strip().lower()
    # return "true" in result
    # 方法二:本地ollama小模型判断
    start=time.time()
    from chat.utils.intentionUtil import intention_recognition
    rs = intention_recognition(question)
    t=time.time()-start
    logger.info(f"意图识别花费时间为：{t}s")
    return "true" in rs

# ========== SSE 事件封装 ==========
# 通过 type 字段区分事件类型，便于前端区分"进度提示"和"答案正文"
#   type = status  → 环节进度提示（前端可据此展示 loading / 进度条）
#   type = content → 答案正文（增量 token，直接追加）
#   type = done    → 流结束（保留 [DONE] 兼容旧前端）
def _sse(obj: dict) -> str:
    """统一 SSE 封装"""
    return f"data: {json.dumps(obj, ensure_ascii = False)}\n\n"


def _sse_status(msg: str) -> str:
    """环节进度事件"""
    return _sse({"type": "status", "content": msg})


def _sse_content(chunk: str) -> str:
    """答案正文事件"""
    return _sse({"type": "content", "content": chunk})


def _sse_done() -> str:
    """结束事件"""
    return _sse({"type": "done", "content": "[DONE]"})


# 非法律问题：直接对话（不走知识库）
def direct_chat_stream(question: str,history_chat:str):
    """没有知识库的流式对话"""
    llm = LoadModel.load_model_stream()
    prompt = PromptTemplate(template = DIRECT_TEMPLATE, input_variables = ["question","history_chat"])
    chain = prompt | llm | StrOutputParser()
    yield _sse_status("✍️ 正在生成答案...")
    t_llm_start = time.time()
    # LangChain 的链 只接收一个参数，而且必须是 dict,且必须和prompt里面的input_variables 定义了需要的 key名字相同
    for chunk in chain.stream({"question":question,"history_chat":history_chat}):
        if chunk:
           yield _sse_content(chunk)
    t_llm_cost = time.time() - t_llm_start
    logger.info(f"[耗时]最终LLM答案生成耗时(非法律直答): {round(t_llm_cost,3)}s")
    yield _sse_done()

# # 计算融合后的分数 【两路融合】
# def _rrf_fusion(docs_a: list, docs_b: list, k: int = 60,) -> list:
#     """RRF 融合两路检索结果，按综合排名去重
#     RRF_score(文档) = 1/(k + 排名_a) + 1/(k + 排名_b)
#     """
#     def _get_key(doc):
#         return doc.id if hasattr(doc, 'id') and doc.id else doc.page_content[:200]
#
#     doc_map, score_map = {}, {}
#     for rank, doc in enumerate(docs_a, start=1):
#         key = _get_key(doc)
#         doc_map[key] = doc
#         score_map[key] = score_map.get(key, 0) + 1.0 / (k + rank)
#     for rank, doc in enumerate(docs_b, start=1):
#         key = _get_key(doc)
#         doc_map[key] = doc
#         score_map[key] = score_map.get(key, 0) + 1.0 / (k + rank)
#
#     sorted_keys = sorted(score_map, key=score_map.get, reverse=True)
#     return [doc_map[key] for key in sorted_keys]


# 打印函数

# 【多路融合】
def _rrf_fusion_multi(doc_lists: list, k: int = 60) -> list:
    """N 路检索结果 RRF 融合，按综合排名去重
    RRF_score(文档) = Σ 1/(k + rank_in_list_i)
    """
    def _get_key(doc):
        return doc.id if hasattr(doc, 'id') and doc.id else doc.page_content[:200]

    doc_map, score_map = {}, {}
    for docs in doc_lists:
        for rank, doc in enumerate(docs, start=1):
            key = _get_key(doc)
            doc_map[key] = doc
            score_map[key] = score_map.get(key, 0) + 1.0 / (k + rank)

    sorted_keys = sorted(score_map, key=score_map.get, reverse=True)
    return [doc_map[key] for key in sorted_keys]
def _rrf_fusion(docs_a: list, docs_b: list, k: int = 60) -> list:
    """兼容旧的两路融合入口"""
    return _rrf_fusion_multi([docs_a, docs_b], k=k)





def _print_docs(title: str, docs: list):
    """打印检索结果"""
    print(f"\n{'=' * 60}")
    print(f"  {title}（共 {len(docs)} 篇）")
    print(f"{'=' * 60}")
    if not docs:
        print("  (无结果)")
        return
    for i, doc in enumerate(docs, 1):
        bm = f"BM25={doc.metadata.get('bm25_score')}" if 'bm25_score' in doc.metadata else ""
        text = doc.page_content[:150]
        print(f"  [{i}] {bm} {text}{'...' if len(doc.page_content) > 150 else ''}")


#是法律问题: RRF算法混合检索(向量chromadb检索+关键词BM25检索)+FlagReranker模型重排序
def rag_chat_stream(question:str,history_chat:str):
    t_rag_total_start = time.time()
    """带知识库检索的流式对话（BM25+向量 的混合检索-> RRF融合 ->重排序 ->LLM流式）"""
    # 向量库
    vector_db=ChromaUtil.get_law_conn()
    # 向量检索器-语义检索,这里的k可以和BM25设置的k不一样;相当于人为定权重
    retriever = vector_db.as_retriever(search_kwargs={"k": 10})

    # 大模型+提示词
    llm = LoadModel.load_model_stream()
    prompt = PromptTemplate(template = RAG_TEMPLATE, input_variables = ["context", "question", "history_chat"])

    # 混合检索函数
    def hybrid_retrieve(q: str) -> list:
        import time
        doc_lists = []

        # # 路径1：原始问题向量检索
        # t0 = time.time()
        # vector_docs = retriever.invoke(q)
        # t_vector = time.time() - t0
        # logger.info(f"[耗时]原始向量检索耗时: {round(t_vector, 3)}s, 返回文档数:{len(vector_docs)}")
        # _print_docs("🔵 原始问题-向量检索", vector_docs)
        # doc_lists.append(vector_docs)
        #
        # # 路径2：原始问题 BM25
        # t1 = time.time()
        # bm25_docs = BM25Util.bm25_search(q, k = 10)
        # t_bm25 = time.time() - t1
        # logger.info(f"[耗时]原始BM25检索耗时: {round(t_bm25, 3)}s, 返回文档数:{len(bm25_docs)}")
        # _print_docs("🟢 原始问题-BM25 检索", bm25_docs)
        # doc_lists.append(bm25_docs)

        # 路径3：查询重写（向量 + BM25）
        if ENABLE_QUERY_REWRITE:
            try:
                t2 = time.time()
                rewritten = QueryRewriteUtil.rewrite_query(q, history_chat)
                t_rewrite = time.time() - t2
                logger.info(f"[耗时]查询重写LLM生成耗时: {round(t_rewrite, 3)}s,重写结果:{rewritten}")

                t3 = time.time()
                rw_vector = retriever.invoke(rewritten)
                t_rw_vector = time.time() - t3
                logger.info(f"[耗时]重写问题向量检索耗时: {round(t_rw_vector, 3)}s,返回文档数:{len(rw_vector)}")

                t4 = time.time()
                rw_bm25 = BM25Util.bm25_search(rewritten, k = 10)
                t_rw_bm25 = time.time() - t4
                logger.info(f"[耗时]重写问题BM25检索耗时: {round(t_rw_bm25, 3)}s,返回文档数:{len(rw_bm25)}")

                _print_docs("🟡 重写问题-向量检索", rw_vector)
                _print_docs("🟡 重写问题-BM25 检索", rw_bm25)
                doc_lists.append(rw_vector)
                doc_lists.append(rw_bm25)
            except Exception as e:
                print(f"[QueryRewrite] 失败，已降级为仅原始查询: {e}")

        # 路径4：HyDE 假设文档向量检索
        if ENABLE_HYDE:
            try:
                t5 = time.time()
                hyde_docs = HyDEUtil.hyde_search(q)
                t_hyde = time.time() - t5
                logger.info(f"[耗时]HyDE完整检索耗时: {round(t_hyde, 3)}s,返回文档数:{len(hyde_docs)}")
                _print_docs("🟠 HyDE 假设文档-向量检索", hyde_docs)
                doc_lists.append(hyde_docs)
            except Exception as e:
                print(f"[HyDE] 失败，已降级: {e}")

        # 多路融合
        t6 = time.time()
        fused = _rrf_fusion_multi(doc_lists, k = 60)
        t_rrf = time.time() - t6
        logger.info(f"[耗时]RRF多路融合耗时: {round(t_rrf, 3)}s,融合后文档数:{len(fused)}")

        # ============ 新增：RRF之后提前截断 ============
        RRF_TOP_K = 10
        fused = fused[:RRF_TOP_K]
        # =============================================

        _print_docs("🟣 RRF 多路融合（截断后）", fused)
        return fused

    # 重排序函数
    def reranker(docs, question):
        import time
        '''
        BGE Reranker 是一个神经网络模型（Cross‑Encoder），它把 [问题, 文档] 拼在一起送进 Transformer，直接输出一个相关性分数。
        '''
        if not docs:
            logger.info("检索器未检索到任何内容,跳过重排序")
            return "（未检索到任何相关参考资料）", []

        t_rerank_start = time.time()
        #构造[问题-文档]对,并计算相关性分数,重排序模型需要接收纯文本字符串
        pairs=[[question,doc.page_content]for doc in docs]
        # BGE
        # 重排序模型-给检索出来的文档进行打分排序
        reranker_model = RerankerUtil.get_reranker()
        scores=reranker_model.compute_score(pairs)
        t_rerank_cost = time.time() - t_rerank_start
        logger.info(f"[耗时]Reranker重排序推理耗时: {round(t_rerank_cost,3)}s,待打分文档数:{len(docs)}")

        for doc,score in zip(docs,scores):
            doc.metadata["relevance_score"]=round(float(score),4)
        #sorted(待排序的可迭代对象, key=排序规则, reverse=是否降序),默认为升序
        sorted_scores=sorted(docs,key=lambda x:x.metadata["relevance_score"],reverse=True)
        # 一定要小于(k1+k2)
        top_n=3
        final_docs=sorted_scores[:top_n]

        # 4. 打印重排序后的结果
        logger.info(f"✅ 重排序完成，保留 Top-{top_n} 文档：")
        for i, doc in enumerate(final_docs, 1):
            score = doc.metadata.get("relevance_score", "N/A")
            bm = doc.metadata.get("bm25_score", "N/A")
            print(f"\n【文档 {i}】(相关度: {score}, BM25: {bm})")
            print(f"  内容: {doc.page_content[:50]}{'...' if len(doc.page_content) > 50 else ''}")
            print("-" * 60)

        # 5. 将文档列表格式化为 context 字符串，供 Prompt 使用
        context_str = "\n\n".join(
            f"[来源{i + 1}] {doc.page_content}" for i, doc in enumerate(final_docs)
        )

        return context_str, final_docs

    # ⭐ 阶段①：混合检索（推送进度）
    yield _sse_status("🔍 正在检索相关法条...")
    t_retrieval_start = time.time()
    fused = hybrid_retrieve(question)
    t_retrieval = time.time() - t_retrieval_start
    logger.info(f"[耗时]混合检索阶段总耗时: {round(t_retrieval,3)}s, 融合后文档数:{len(fused)}")
    yield _sse_status(f"✅ 检索完成，共召回 {len(fused)} 篇相关法条")

    # ⭐ 阶段②：重排序（推送进度）
    yield _sse_status("🧠 正在重排序候选法条...")
    context_str, final_docs = reranker(fused, question)
    yield _sse_status(f"✅ 重排序完成，已选取 Top-{len(final_docs)} 篇作为参考")

    # ⭐ 阶段③：LLM 流式生成（单独计时，推送正文）
    yield _sse_status("✍️ 正在生成答案...")
    t_llm_start = time.time()
    t_first_token = None
    chain = prompt | llm | StrOutputParser()
    for chunk in chain.stream({"context": context_str, "question": question, "history_chat": history_chat}):
        if chunk:
            if t_first_token is None:
                t_first_token = time.time() - t_llm_start
                logger.info(f"[耗时]最终LLM首字延迟: {round(t_first_token,3)}s")
            yield _sse_content(chunk)
    t_llm_cost = time.time() - t_llm_start
    logger.info(f"[耗时]最终LLM答案生成耗时: {round(t_llm_cost,3)}s, 首字延迟: {round(t_first_token or 0,3)}s")

    # 结束信号
    yield _sse_done()
    total_cost = time.time() - t_rag_total_start
    logger.info(f"[耗时]整条RAG问答链路总耗时（含LLM生成）：{round(total_cost, 3)}s")
# ========== 统一入口 ==========
def chat_stream(question: str,parent_id: int = 0):
    """根据问题类型分流"""
    try:
        history_chat=load_history_chat(parent_id)
        if is_legal_question(question):
            yield from rag_chat_stream(question,history_chat)
        else:
            yield from direct_chat_stream(question,history_chat)
    except Exception as e:
        print(f"聊天流程出错: {e}")
        yield f"data: {json.dumps({'content': f'发生错误: {str(e)}'}, ensure_ascii = False)}\n\n"
        yield f"data: {json.dumps({'content': '[DONE]'}, ensure_ascii=False)}\n\n"

# 流式聊天 --- neo4j
def chat_stream_neo4j(question,parent_id=0):
    """Neo4j 知识图谱增强的流式对话（SSE 格式输出）"""
    # ---------- ① 加载对话历史 ----------
    history_chat = load_history_chat(parent_id)

    # ---------- ② 两个 LLM：非流式给 GraphCypherQAChain，流式给摘要链 ----------
    # GraphCypherQAChain 内部用 invoke()，必须是非流式 LLM
    llm_no_stream = LoadModel.load_model_no_stream()
    # 摘要链用 stream()，必须是流式 LLM
    llm_stream = LoadModel.load_model_stream()

    # =====================================================================
    #  提示词模板
    # =====================================================================
    # 生成CQL的提示词
    CYPHER_GENERATION_TEMPLATE = """Task:Generate Cypher statement to query a graph database.
    Instructions:
    Use only the provided relationship types and properties in the schema.
    Do not use any other relationship types or properties that are not provided.
    Schema:
    {schema}

    # 节点标签及含义
    | 节点标签     | 含义             |
    |--------------|------------------|
    | Disease      | 疾病（核心节点） |
    | Symptom      | 症状             |
    | Check        | 检查项目         |
    | Cureway      | 治疗方式         |
    | Drug         | 药物             |
    | Department   | 就诊科室         |
    | Food         | 食物             |
    | Dishes       | 菜肴             |
    | Category     | 疾病分类         |

    # 关系类型及含义
    | 关系类型             | 含义              | 起始节点 | 目标节点    |
    |----------------------|-------------------|----------|-------------|
    | DISEASE_SYMPTOM      | 疾病症状          | Disease  | Symptom     |
    | DISEASE_CHECK        | 相关检查项目      | Disease  | Check       |
    | DISEASE_CUREWAY      | 治疗方式          | Disease  | Cureway     |
    | DISEASE_DRUG         | 治疗或相关药物    | Disease  | Drug        |
    | DISEASE_DEPARTMENT   | 就诊科室          | Disease  | Department  |
    | DISEASE_DO_EAT       | 推荐进食的食物    | Disease  | Food        |
    | DISEASE_NOT_EAT      | 不推荐进食的食物  | Disease  | Food        |
    | DISEASE_DISHES       | 适合疾病的菜肴    | Disease  | Dishes      |
    | DISEASE_ACOMPANY     | 并发症 / 伴随疾病 | Disease  | Disease     |
    | DISEASE_CATEGORY     | 疾病所属类别      | Disease  | Category    |

    # 查询示例
    # 问：高血压有哪些症状？
    MATCH (d:Disease {{name:"高血压"}})-[:DISEASE_SYMPTOM]->(s:Symptom) RETURN s.name AS symptom

    # 问：感冒吃什么药？
    MATCH (d:Disease {{name:"感冒"}})-[:DISEASE_DRUG]->(dr:Drug) RETURN dr.name AS drug

    # 问：糖尿病不宜吃什么？
    MATCH (d:Disease {{name:"糖尿病"}})-[:DISEASE_NOT_EAT]->(f:Food) RETURN f.name AS food

    # 问：肺炎需要做什么检查？
    MATCH (d:Disease {{name:"肺炎"}})-[:DISEASE_CHECK]->(c:Check) RETURN c.name AS check_item

    # 问：高血压挂什么科？
    MATCH (d:Disease {{name:"高血压"}})-[:DISEASE_DEPARTMENT]->(dep:Department) RETURN dep.name AS department

    # 问：感冒的并发症有哪些？
    MATCH (d:Disease {{name:"感冒"}})-[:DISEASE_ACOMPANY]->(a:Disease) RETURN a.name AS complication

    # 问：糖尿病属于哪类疾病？
    MATCH (d:Disease {{name:"糖尿病"}})-[:DISEASE_CATEGORY]->(c:Category) RETURN c.name AS category

    # 问：高血压可以吃什么菜？
    MATCH (d:Disease {{name:"高血压"}})-[:DISEASE_DISHES]->(dishes:Dishes) RETURN dishes.name AS dishes

    # 问：哪些疾病会有头痛症状？
    MATCH (d:Disease)-[:DISEASE_SYMPTOM]->(s:Symptom {{name:"头痛"}}) RETURN d.name AS disease

    Note: Do not include any explanations or apologies in your responses.
    Do not respond to any questions that might ask anything else than for you to construct a Cypher statement.
    Do not include any text except the generated Cypher statement.

    The question is:
    {question}"""
    # 结合上下文回答问题的提示词
    QA_TEMPLATE = """你是一名专业的医疗智能问答助手，基于 Neo4j 疾病知识图谱为用户提供准确的健康咨询。
        # 第一步：意图识别
        判断用户问题是否属于【医疗疾病类】，包括但不限于：
        - 疾病症状、病因、并发症
        - 检查项目、就诊科室
        - 治疗方式、用药建议
        - 饮食宜忌、推荐菜肴
        - 疾病分类与归属

        # 第二步：按类别处理

        ## 情形 1：属于医疗疾病类 → 基于以下图谱查询结果作答
        - 严格基于查询结果作答，不得编造疾病、药物或诊疗方案
        - 若查询结果为空，回复："知识库中未收录该疾病的相关信息，建议咨询专业医生"

        ## 情形 2：不属于医疗疾病类
        - 忽略知识图谱查询结果
        - 基于自身通用知识自然作答
        - 回复中不得出现"知识库""图谱""上下文"等字样

        # 输出要求
        - 直接给出最终答案，不复述问题、不解释判断过程
        - 涉及用药、治疗、剂量等敏感内容时，附加一句："具体方案请遵医嘱"
        - 语言简洁、准确、通俗易懂

        ---
        【图谱查询结果】
        {context}

        【用户问题】
        {question}

        【回答】
    """
    # 创建提示词对象
    cql_prompt = PromptTemplate(
        input_variables = ["schema", "question"],
        template = CYPHER_GENERATION_TEMPLATE
    )
    qa_prompt = PromptTemplate(
        input_variables = ["context", "question"],
        template = QA_TEMPLATE
    )

    # ---------- ③ 获取 Neo4j 连接 ----------
    graph = Neo4jUtil.get_neo4j_conn()

    # ---------- ④ 构造 GraphCypherQAChain（注意：必须用非流式 LLM） ----------
    qa_chain = GraphCypherQAChain.from_llm(
        llm = llm_no_stream, # ★ 非流式：内部调用 invoke()
        graph = graph,
        cypher_prompt = cql_prompt,
        qa_prompt = qa_prompt,
        verbose = True,
        allow_dangerous_requests = True,
        validate_cypher = True # 预校验语法合法性[必须设置为True,否则报错]
    )
    try:
        # ⑤ 先返回状态提示，避免阻塞期间前端白屏 - ---------
        yield f"data: {json.dumps({'content': '正在查询知识图谱...'}, ensure_ascii = False)}\n\n"
        # ---------- ⑥ 执行图谱问答（阻塞调用，返回 dict） ----------
        result = qa_chain.invoke({"query": question})['result']
        # ---------- ⑦ 结构化摘要提示词 ----------
        SUMMARY_PROMPT = """
                # Role (角色设定)
                你是一位严谨的【医学信息整理助手】，专注于对医疗文本进行客观、准确的信息结构化提取。
                ⚠️ **重要声明**：你不是医生，不提供任何诊断、治疗或用药建议。你的唯一任务是对已有文本进行忠实摘要。

                # Task (任务目标)
                请阅读下方【待总结内容】，生成一份结构化的医疗信息摘要。

                # Safety Constraints (安全红线 - 必须严格遵守)
                1. **零幻觉原则**：仅总结原文中明确存在的信息。若原文未提及某项内容（如剂量、禁忌症），必须标注“原文未提及”，严禁推测或补充外部知识。
                2. **禁止建议**：绝对不要输出“建议您...”、“可以尝试...”等指导性语言。所有表述必须为“原文指出...”、“文中提到...”。
                3. **数据精确**：涉及数值（剂量、指标、时间）时，必须与原文完全一致，禁止四舍五入或模糊化处理。
                4. **强制免责**：无论原文内容如何，输出的开头和结尾必须包含标准免责声明。
                5. **不确定性标记**：若原文本身存在矛盾、模糊或证据等级低的内容，必须在摘要中用 ⚠️ 显式标注。

                # Output Framework (输出框架)
                请严格按以下格式输出：

                > ⚕️ **免责声明**：本摘要仅为信息整理，不构成任何医疗建议。具体诊疗请务必咨询专业医生，并以线下医疗机构意见为准。

                ## 📋 核心信息概览
                - **涉及疾病/症状**：[原文提到的具体名称]
                - **信息类型**：[科普/临床指南/病例报告/药物说明/患者经验]
                - **证据等级/来源可信度**：[根据原文判断，如"权威指南"/"个人经验分享"/"原文未标明"]

                ## 🔍 关键事实提炼
                - **[维度1，如：适应症/症状表现]**：原文指出...
                - **[维度2，如：治疗方案/检查手段]**：原文提到...
                - **[维度3，如：注意事项/禁忌]**：原文明确...
                （每个要点必须注明信息来源段落或依据，无法溯源则标注"存疑"）

                ## ⚠️ 风险提示与局限
                - 原文中提到的副作用/风险：...
                - 原文信息的局限性：[如"样本量小"/"仅动物实验"/"个人观点"/"发布时间较早"]
                - 原文未覆盖但通常重要的信息：[如"未提及儿童用药安全性"]

                ## ❓ 建议进一步确认的问题
                （列出2-3个基于该文本应向专业医生核实的关键问题，帮助用户高效就医沟通）

                > ⚕️ **再次提醒**：以上内容整理自原文，可能存在滞后或不完整。请勿据此自行调整治疗方案，及时就医是唯一安全选择。
                ---
                【待总结内容】：
                    {context}
            """
        prompt = PromptTemplate(template = SUMMARY_PROMPT, input_variables = ["context"])
        # ---------- ⑧ 摘要链（用流式 LLM） ----------
        result_chain = (
                RunnableParallel(
                    # 通过闭包把 graph_result 注入到 context 字段
                    {"context": RunnableLambda(lambda _: result)}
                )
                | prompt
                | llm_stream  # ★ 流式：支持 .stream() 逐 token 输出
                | StrOutputParser()
        )
        # ---------- ⑨ 流式输出，逐 chunk 包装为 SSE 格式 ----------
        for chunk in result_chain.stream(result):
            if chunk:
                yield f"data: {json.dumps({'content': chunk}, ensure_ascii = False)}\n\n"

        # ---------- ⑩ 结束信号：通知前端流已结束 ----------
        yield f"data: {json.dumps({'content': '[DONE]'}, ensure_ascii = False)}\n\n"

    except Exception as e:
        # ---------- 异常兜底：返回错误信息 + DONE ----------
        print(f"图谱对话出错: {e}")
        yield f"data: {json.dumps({'content': f'图谱查询发生错误: {str(e)}'}, ensure_ascii = False)}\n\n"
        yield f"data: {json.dumps({'content': '[DONE]'}, ensure_ascii = False)}\n\n"

if __name__ == '__main__':
    # chat_stream("得了糖尿病应该怎么办")
    #"得了糖尿病应该怎么办"
    #"公安机关接到家庭暴力报案后应当做什么事情？"
    # for chunk in chat_stream("公安机关接到家庭暴力报案后应当做什么事情？",20):
    #     print(chunk,end="")

    # for chunk in chat_stream_neo4j("公安机关接到家庭暴力报案后应当做什么事情？", parent_id = 0):
    #     print(chunk, end = "")
        # 1. 单测重写（含指代）
    # for chunk in chat_stream("该犯罪者要承担什么责任？", parent_id = 47):
    #     print(chunk, end = "")

    # 2. 单测 HyDE
    docs = HyDEUtil.hyde_search("公安机关接到家庭暴力报案后应当做什么事情？")
    for d in docs:
        print(d.metadata, d.page_content[:80])

    # 3. 对比验证：开/关开关各跑一次，肉眼比对检索日志 + 最终答案




