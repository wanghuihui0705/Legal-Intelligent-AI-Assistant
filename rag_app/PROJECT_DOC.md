# 智能医疗 RAG 对话系统 — 项目面试文档

---

## 一、项目结构（技术栈 & 模块总览）

```

┌──────────────────────────────────────────────────────────────┐
│                    前端（rag_app）                            │
│  Vue 2 + Element UI + Vue Router + Axios + EventSource(SSe) │
│  页面：登录页 / 聊天页（含历史侧边栏）                         │
│  端口：localhost:8080                                        │
└──────────────────────┬───────────────────────────────────────┘
                       │ HTTP / SSE
┌──────────────────────▼───────────────────────────────────────┐
│                 后端（candidates_rag）                         │
│  Python FastAPI + Uvicorn + 跨域中间件                        │
│  启动时预加载：Embedding模型 + Reranker模型                     │
│  端口：localhost:8000                                        │
└───────┬──────────────┬──────────────┬────────────────────────┘
        │              │              │
┌───────▼──────┐ ┌─────▼──────┐ ┌────▼──────────────────────┐
│  MySQL 8.0   │ │  ChromaDB  │ │  Neo4j 图数据库            │
│  (对话记录)   │ │ (医学向量库)│ │  (疾病知识图谱)             │
│  表：users    │ │ 5万+ 文档  │ │  节点：Disease/Symptom/    │
│  表：history  │ │ 余弦相似度  │ │  Drug/Check/Department等  │
└──────────────┘ └─────────────┘ └───────────────────────────┘
        │              │              │
┌───────▼──────────────────────────────────────────────────────┐
│                        AI 模型层                              │
│  大模型：通义千问 qwen3.7-plus（阿里云 DashScope API）         │
│  Embedding：BAAI/bge-small-zh-v1.5（本地 GPU 加载）            │
│  Reranker：BAAI/bge-reranker-base（本地 GPU，FP16）            │
│  分词工具：jieba（BM25 检索）                                  │
└──────────────────────────────────────────────────────────────┘
```

| 层级 | 技术 | 说明 |
|------|------|------|
| 客户端 | Vue 2 + Element UI | Web 网站，含登录页 + 聊天页（历史侧边栏） |
| 后端框架 | Python FastAPI + Uvicorn | RESTful API + SSE 流式响应 |
| 数据库 | MySQL 8.0（PyMySQL + DBUtils 连接池） | `users` 表（用户）、`history` 表（对话记录，含 parent_id 实现根/追问树形结构） |
| 向量数据库 | ChromaDB（langchain-chroma） | 存储 5 万+ 条医学问答对的向量，余弦相似度检索 |
| 图数据库 | Neo4j | 疾病知识图谱（Disease/Symptom/Drug/Check 等 9 类节点 + 10 种关系） |
| 大模型 | 通义千问 qwen3.7-plus | 通过阿里云 DashScope API（OpenAI 兼容接口）调用 |
| Embedding | BAAI/bge-small-zh-v1.5 | 本地 GPU 加载，将文本编码为向量 |
| Reranker | BAAI/bge-reranker-base | 本地 GPU（FP16），Cross-Encoder 架构，对检索结果重排序 |
| 分词 | jieba | BM25 关键词检索的分词工具 |
| 框架 | LangChain | 链式调用（PromptTemplate + LLM + OutputParser）、RAG 流程编排 |
| 检索引擎 | BM25 + 向量混合检索 + RRF 融合 | 关键词 + 语义双路检索，RRF 算法融合排序 |
| 前端通信 | Axios（HTTP）+ EventSource（SSE）| GET/POST JSON + 流式文本传输 |
| Markdown | marked + DOMPurify | 前端渲染 AI 回复中的 Markdown 格式 |

---

## 二、每个模块的设计流程

### 2.1 客户端（前端）

| 步骤 | 技术 | 实现 |
|------|------|------|
| 1 | Vue 2 + Vue Router | 搭建 SPA，`/` 路由到 Login.vue，`/goChat` 路由到 Chat.vue，history 模式去掉 URL 中的 `#` |
| 2 | Element UI | 使用 `el-input`、`el-button`、`el-form` 等组件快速搭建 UI |
| 3 | 登录页 | 用户输入账号密码 → `POST /users/login` → 成功后 `sessionStorage` 存储 `username` 和 `userId` → 跳转 `/goChat` |
| 4 | 路由守卫 | `router.beforeEach` 检查 `sessionStorage.username`，未登录拦截回登录页 |
| 5 | 聊天页布局 | Flex 布局：左侧 300px 侧边栏 + 24px 折叠按钮 + 右侧聊天区（消息列表 + 输入框） |
| 6 | 侧边栏 | `fetchSidebarHistory()` → `GET /history/list` → 拿到根问题列表渲染，点击切换对话高亮（`activeChatId`） |
| 7 | 发送消息 | 用户输入 → `chat()` → `messages.push` 上屏 → 创建 `EventSource` 连接 SSE |
| 8 | 流式接收 | `eventSource.onmessage` 逐片追加到 `messages` 最后一条，`[DONE]` 时关闭连接并调用 `saveExchange()` |
| 9 | 历史查看 | 点击侧边栏 → `fetchDetail(historyId)` → `GET /history/detail` → 拆成 user/ai 消息对渲染 |
| 10 | 新建/删除对话 | `createNewChat()` 重置 UI；`deleteChat(id)` → `POST /history/deleteConversation` → 级联删除根+追问 |
| 11 | Markdown 渲染 | `marked` 解析 → `DOMPurify` 安全过滤 → `v-html` 渲染 AI 消息中的代码块、列表等 |

### 2.2 服务端（后端）

| 步骤 | 技术 | 实现 |
|------|------|------|
| 1 | FastAPI + Uvicorn | 创建 `FastAPI()` 应用，使用 `lifespan` 事件预加载 Embedding 模型和 Reranker 模型 |
| 2 | CORS 中间件 | 允许 `localhost:8080` 跨域请求 |
| 3 | 路由注册 | 三个子路由：`/users`、`/chat`、`/history`，分别挂载对应的 APIRouter |
| 4 | 静态文件 | `app.mount("/static")` 放行静态资源 |
| 5 | 分层架构 | Controller（接口层）→ Service（业务层）→ DAO（数据访问层）→ MySQL/Chroma/Neo4j |
| 6 | MySQL 连接池 | `DBUtils.PooledDB`，max=10，mincached=2，maxcached=5 |
| 7 | Pydantic 请求体 | `SaveExchangeRequest`、`DeleteConversationRequest` 做参数校验 |

### 2.3 数据库设计

**MySQL `history` 表：**

| 字段 | 类型 | 说明 |
|------|------|------|
| `history_id` | INT (PK, AUTO_INCREMENT) | 主键 |
| `question` | TEXT | 用户问题 |
| `answer` | TEXT | AI 回答 |
| `parent_id` | INT | 0=根问题，非0=所属根问题的 history_id |
| `create_time` | DATETIME | 创建时间（DEFAULT CURRENT_TIMESTAMP） |
| `history_fk_users` | INT (FK) | 外键关联 `users.id` |

**对话树形结构：**
```
history_id=1, parent_id=0  ← 根问题 "什么是Vue?"
history_id=2, parent_id=1  ← 追问 "和React有什么区别?"
history_id=3, parent_id=1  ← 追问 "Vue3有什么新特性?"
```

### 2.4 数据来源 & 处理

| 步骤 | 技术 | 实现 |
|------|------|------|
| 1 | 原始数据 | `answer.csv` + `question.csv`，两个 CSV 文件按 `question_id` 内连接合并 |
| 2 | 合并脚本 | `合并两个csv.py` → pandas merge → 生成 `merge_result_rag.csv`（约 5 万+ 条医学问答对） |
| 3 | 文本构造 | 每条数据格式化为 `问题：{question}\n回答：{answer}` |
| 4 | 向量编码 | `BuildMedicalKnowledgeBase.py` 步骤1：`SentenceTransformer` 加载本地 `bge-small-zh-v1.5` 模型，GPU 批量编码（batch_size=256），耗时约 5 分钟，编码后缓存为 `.npy` 文件 |
| 5 | 写入 Chroma | 步骤2：从缓存读取向量，分批（5000条/批）写入 ChromaDB，存储到 `vector_db/medical_knowledge_base.db` |
| 6 | 相似度 | `hnsw:space=cosine`，余弦相似度做向量检索 |

### 2.5 RAG 系统（检索增强生成）

```
用户输入问题
     │
     ▼
┌─────────────────┐
│ ① 问题分类       │  ← is_medical_question() → LLM 判断是否医学问题
└────┬────────┬───┘
     │        │
  医学问题    非医学问题
     │        │
     ▼        ▼
┌─────────┐  ┌──────────────┐
│② 混合检索│  │ direct_chat   │ → 直接对话（不用知识库）
│BM25+k=10│  │ _stream()     │
│向量 k=20│  └──────────────┘
└────┬────┘
     │
     ▼
┌──────────┐
│③ RRF 融合│  ← _rrf_fusion() 双路结果去重排序
└────┬─────┘
     │
     ▼
┌──────────────┐
│④ BGE Reranker│  ← Cross-Encoder 逐对打分，取 top-3
└────┬─────────┘
     │
     ▼
┌──────────────┐
│⑤ 拼 Prompt   │  ← context(检索结果) + history_chat(历史) + question
└────┬─────────┘
     │
     ▼
┌──────────────┐
│⑥ LLM 流式生成│  ← qwen3.7-plus → SSE 逐 token 返回前端
└──────────────┘
```

| 环节 | 技术 | 关键参数 |
|------|------|----------|
| 问题分类 | LLM 前置判断 | Prompt 要求返回 true/false |
| 向量检索 | ChromaDB | k=20，语义相似度 |
| 关键词检索 | BM25（jieba 分词） | k=10，词频-逆文档频率 |
| 融合排序 | RRF（Reciprocal Rank Fusion）| k=60，`RRF_score = Σ 1/(60+rank)` |
| 重排序 | BGE Reranker（Cross-Encoder） | 保留 top-3，FP16 推理 |
| 上下文限制 | 最多 3 篇参考文档 | 防止 prompt 超长 |

### 2.6 Neo4j 知识图谱增强

| 步骤 | 技术 | 实现 |
|------|------|------|
| 1 | LangChain `GraphCypherQAChain` | 将用户自然语言问题 → LLM 生成 Cypher 查询 → 执行查询 → 拿到图谱结果 |
| 2 | 节点标签 | Disease, Symptom, Check, Cureway, Drug, Department, Food, Dishes, Category |
| 3 | 关系类型 | DISEASE_SYMPTOM, DISEASE_CHECK, DISEASE_DRUG, DISEASE_CUREWAY 等 10 种 |
| 4 | 结果加工 | 图谱查询结果 → 结构化摘要提示词 → LLM 流式输出（含安全红线：零幻觉原则、禁止建议、强制免责） |
| 5 | 路由 | 前端调用 `/chat/chatStreamNoe4j` 走图谱路线，`/chat/chatStream` 走 RAG 路线 |

### 2.7 对话历史记忆

| 步骤 | 实现 |
|------|------|
| 1 | 前端每次发送消息时，如果 `activeChatId` 不为 null，把 `history_id` 拼到 SSE URL 参数中 |
| 2 | 后端 `chat_stream(question, parent_id)` 中，`load_history_chat(parent_id)` 查 DB 获取该根问题下所有 Q&A |
| 3 | 格式化为 `用户：xxx\n助手：xxx` 字符串，注入 Prompt 的 `{history_chat}` 占位符 |
| 4 | 首次保存时 `parent_id=0`，后端返回新的 `history_id` → 前端接上 → 后续追问自动带历史 |

---

## 三、涉及技术的底层原理

### 3.1 SSE（Server-Sent Events）

- **原理**：HTTP 长连接，服务器向客户端单向推送数据。响应头 `Content-Type: text/event-stream`，数据格式 `data: {json}\n\n`
- **对比 WebSocket**：SSE 更轻量，基于标准 HTTP，浏览器原生支持 `EventSource` 对象，适合 AI 流式输出场景（只需服务端→客户端单向推送）
- **本项目应用**：`EventSource` 连接 `/chat/chatStream`，`onmessage` 逐片接收，`[DONE]` 标记流结束

### 3.2 Transformer（Attention 机制）

- **核心公式**：`Attention(Q,K,V) = softmax(QK^T/√dk) × V`
- **Self-Attention**：每个词与序列中所有词计算相关性权重，解决长距离依赖问题
- **Multi-Head Attention**：多组 Q/K/V 并行计算，捕获不同子空间的特征
- **本项目**：qwen3.7-plus 基于 Transformer 架构；BGE Reranker 使用 Cross-Encoder（将 [问题,文档] 拼接输入 Transformer，输出相关性分数）

### 3.3 RAG（检索增强生成）

- **核心思想**：先检索相关文档，再将文档作为上下文注入 Prompt，让 LLM 基于参考资料作答
- **优势**：减少幻觉（模型不瞎编）、知识可更新（改向量库即可，不用重训模型）、可溯源
- **本项目流程**：问题分类 → 混合检索（BM25 + 向量）→ RRF 融合 → Reranker 重排序 → Top-3 注入 Prompt → LLM 生成

### 3.4 BM25 关键词检索

- **公式**：`BM25(D,Q) = Σ IDF(qi) × (fi × (k1+1)) / (fi + k1 × (1-b + b×dl/avgdl))`
- **核心**：词频（TF）+ 逆文档频率（IDF）+ 文档长度归一化
- **与向量检索互补**：向量擅长语义匹配（"感冒"≈"着凉"），BM25 擅长精确关键词匹配（药物名、检查项目名）

### 3.5 RRF（Reciprocal Rank Fusion）

- **公式**：`RRF_score(d) = Σ 1/(k + rank_i(d))`
- **作用**：对多路检索结果去重并综合排序，不依赖原始分数的绝对数值，只依赖排名
- **本项目**：k=60，融合 BM25（k=10）和向量检索（k=20）两路结果

### 3.6 ChromaDB 向量数据库

- **原理**：将文本通过 Embedding 模型编码为高维向量（本项目 512/768 维），存到向量数据库
- **检索方式**：计算查询向量与库中所有向量的余弦相似度，返回最相似的 top-k
- **索引算法**：HNSW（Hierarchical Navigable Small World），近似最近邻搜索，平衡速度与精度
- **本项目**：persist_directory 持久化到磁盘，collection_metadata 设置 `hnsw:space=cosine`

### 3.7 BGE Reranker（Cross-Encoder）

- **与 Bi-Encoder 的区别**：Bi-Encoder（如 Embedding 模型）分别编码问题和文档，独立计算向量后求相似度；Cross-Encoder 将 [问题, 文档] 拼接送入 Transformer，直接输出相关性分数
- **优势**：精度更高（能建模问题和文档之间的细粒度交互），作为粗排后的精排
- **劣势**：速度慢，不能提前计算向量缓存
- **本项目**：FlagEmbedding 库加载 `bge-reranker-base`，FP16 推理，从 30 篇候选文档中选出 top-3

### 3.8 LangChain

- **核心概念**：Chain（链式调用）、PromptTemplate（提示词模板）、RunnablePassthrough/RunnableParallel/RunnableLambda（编排工具）
- **本项目应用的链结构**：
  ```
  RunnableParallel({
      context: hybrid_retrieve → reranker,
      question: passthrough,
      history_chat: lambda
  })
  → prompt → llm → StrOutputParser → stream()
  ```

### 3.9 连接池（DBUtils）

- **原理**：预先创建一批数据库连接并缓存，请求到来时借出一个连接，用完归还，避免频繁创建/销毁 TCP 连接
- **本项目配置**：maxconnections=10, mincached=2, maxcached=5, blocking=True（连接池满时阻塞等待）

### 3.10 Neo4j 图数据库

- **原理**：以节点（Node）和关系（Relationship）存储数据，使用 Cypher 查询语言（类似 SQL 但针对图结构）
- **优势**：天然适合存储关联性强的知识（如疾病→症状→药物→科室的多跳查询）
- **本项目**：LangChain 的 `GraphCypherQAChain` 自动将自然语言转为 Cypher 查询，执行后拿到结果再交给 LLM 生成自然语言回答

---

## 四、遇到的问题及解决方案

### 问题 1：前端竞态条件 —— 新建对话后追问丢失历史

- **现象**：新建对话 → 发送第一条消息 → AI 回复 → 用户立即追问 → 第二条消息还是 `parent_id=0`，后端当新对话处理，没有历史上下文
- **原因**：`isLoading = false` 在 `saveExchange` 的 `.then()` 之前执行，输入框立即解锁，用户发第二条消息时 `activeChatId` 还没赋值
- **解决**：将 `isLoading = false` 移到 `saveExchange` 的回调函数中，等保存完成、`activeChatId` 赋值后才解锁输入框。同时 `catch` 里也调用回调防止永久锁死

### 问题 2：npm 缓存权限问题（Windows）

- **现象**：`npm run dev` 报 `EPERM: operation not permitted, mkdir 'D:\nodejs\node_cache\_cacache'`
- **原因**：npm 全局缓存指向 `D:\nodejs\node_cache`，需要管理员权限
- **解决**：`npm config set cache "C:\Users\ASUS\AppData\Roaming\npm-cache"` 将缓存迁到用户目录

### 问题 3：前端 SSE 路径拼接错误

- **现象**：请求变成 `http://localhost:8000//history/detail`，双斜杠导致 404
- **原因**：`this.$serverUrlBase` 末尾已有 `/`，拼接时又加了 `/`
- **解决**：统一去掉拼接头部的 `/`，如 `'history/detail'`

### 问题 4：Reranker 模型 OOM（显存溢出）

- **现象**：服务启动时加载 BGE Reranker 模型后显存不足
- **原因**：Embedding 模型和 Reranker 模型同时加载到 GPU 显存中
- **解决**：
  - 使用 `lifespan` 事件管理模型生命周期，按顺序预加载
  - Reranker 开启 `use_fp16=True` 半精度推理，减少显存占用
  - HuggingFace 设置 `HF_HUB_OFFLINE=1` 强制离线模式，避免下载超时

### 问题 5：前后端字段名不一致

- **现象**：后端数据库用下划线 `history_id`、`create_time`，Python 代码手动转小驼峰 `historyId`、`createTime`，前端模板用 `chat.id`、`chat.time`
- **解决**：前端在拿到后端数据后做一次字段映射 `conversationList = body.data.map(item => ({ id: item.historyId, title: item.question, time: item.createTime }))`

### 问题 6：CSV 问答对不能直接匹配

- **现象**：原始数据是 `answer.csv` 和 `question.csv` 两个独立文件，需要通过 `question_id` 关联
- **解决**：编写 `合并两个csv.py` 使用 pandas 内连接合并，输出 `merge_result_rag.csv`，共约 5 万条标准问答对

---

## 项目亮点总结

1. **混合检索 + RRF 融合**：BM25 关键词 + Chroma 向量双路检索，RRF 算法融合去重，克服单一检索方式的局限
2. **BGE Reranker 重排序**：Cross-Encoder 精细打分，从 30 篇候选文档中精排选出 Top-3，显著提升检索精准度
3. **知识图谱增强**：Neo4j 存储疾病知识图谱，GraphCypherQAChain 实现自然语言→Cypher→结构化回答
4. **SSE 流式对话**：基于 EventSource 实现 token 级别的实时流式输出，用户体验流畅
5. **对话记忆**：通过 parent_id 树形结构存储根问题与追问，多轮对话时自动注入历史上下文
6. **问题自动分类**：前置 LLM 判断是否为医学问题，非医学问题走通用对话，避免滥用知识库
7. **安全红线**：Prompt 中内建"零幻觉原则"、"禁止建议"、"强制免责声明"等多层安全约束
8. **模型预加载**：利用 FastAPI lifespan 事件在服务启动时预加载 Embedding 和 Reranker 模型，首次请求不卡顿
9. **连接池管理**：MySQL 使用 DBUtils 连接池，ChromaDB/Embedding/Reranker 使用模块级单例，避免资源泄漏
10. **离线模型部署**：所有模型（Embedding、Reranker）均本地离线加载，不依赖外部网络
