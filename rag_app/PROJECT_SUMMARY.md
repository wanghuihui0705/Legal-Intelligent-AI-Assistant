# rag_app 项目总结

## 技术栈

| 层级 | 技术 |
|------|------|
| 前端框架 | Vue 2 + Element UI |
| 路由 | Vue Router（history 模式） |
| HTTP 请求 | Axios（`this.$axios`） |
| 实时通信 | EventSource（SSE） |
| Markdown 渲染 | marked + DOMPurify |
| 后端基址 | `http://localhost:8000/` |
| 用户身份 | `sessionStorage('userId')` |

## 路由结构

```
/        →  Login.vue   （不拦截）
/goChat  →  Chat.vue    （需登录拦截，检查 sessionStorage 的 username）
```

`main.js` 的 `router.beforeEach` 守卫：访问 `/goChat` 时如果没有 `username`，弹窗拦截并跳回 `/`。

---

## Chat.vue 核心变量

| 变量 | 类型 | 初始值 | 作用 |
|------|------|--------|------|
| `activeChatId` | `number\|null` | `null` | 当前打开的根问题 `history_id`，`null` 表示新建对话 |
| `conversationList` | `array` | `[]` | 侧边栏数据 `[{ id, title, time }]` |
| `messages` | `array` | `[{ role:'ai', 欢迎语 }]` | 聊天区消息 `[{ role, content }]` |
| `question` | `string` | 默认值 | 输入框双向绑定 |
| `isLoading` | `boolean` | `false` | 是否正在接收 AI 回复（锁定输入） |
| `searchKeyword` | `string` | `''` | 搜索框（纯样式未实现） |
| `sidebarCollapsed` | `boolean` | `false` | 侧边栏折叠状态 |

---

## Chat.vue 六个功能与前后端交互

### 一、加载侧边栏 — `fetchSidebarHistory()`

```
调用时机：mounted()、保存后、删除后
────────────────────────────────
请求：GET http://localhost:8000/history/list?user_id={userId}

后端返回：
  { code:200, data: [{ historyId, question, answer, createTime }] }

前端处理：
  data.map → conversationList [{ id, title, time }]
  有数据 → activeChatId = 第一条的 id（自动选中）
  无数据 → activeChatId 保持 null，侧边栏显 📭 空状态
```

### 二、点击侧边栏查看历史 — `switchChat()` → `fetchDetail()`

```
触发：点击侧边栏记录
      ↓
   switchChat(id)
      activeChatId = id（用于高亮 + 后续追问）
      fetchDetail(id)
      ↓
请求：GET http://localhost:8000/history/detail?history_id={id}

后端返回：
  { code:200, data: [{ historyId, question, answer, createTime }] }
  （该根问题下所有 Q&A，含追问，按时间排序）

前端处理：
  每条后端记录 → 拆成两条 message：
    { role:'user', content: question }
    { role:'ai',   content: answer }
  → this.messages = list → scrollToBottom()
```

### 三、发送消息 / AI 回复 — `chat()`

```
触发：点击发送按钮 / 回车
────────────────────────────────
流程：
  ① messages.push({ role:'user', ... })    ← 用户消息上屏
  ② messages.push({ role:'ai',   '' })     ← AI 占位
  ③ isLoading = true（输入框锁定）
  ④ 构造 SSE 连接：

     params = { question }
     if (activeChatId) → params 追加 history_id
     ↓
     GET http://localhost:8000/chat/chatStream?question=xxx&history_id=N

  ⑤ onmessage：逐片追加到 messages 最后一条的 content
  ⑥ [DONE] 到达：关闭连接 → saveExchange(question, answer)
```

### 四、保存问答 — `saveExchange(question, answer, callback)`

```
触发：chat() 收到 [DONE] 后
────────────────────────────────
计算 parent_id：
  activeChatId || 0
  → 新建对话时 0（后端创建新根问题）
  → 追问时   N（后端挂在根问题下）

请求：POST http://localhost:8000/history/saveExchange
Body JSON：{ user_id, parent_id, question, answer }

后端返回：
  { code:200, data: newId }（newId 是插入后的 history_id）

前端处理：
  如果 activeChatId 为空 → activeChatId = newId（接上新对话链）
  否则不变
  → fetchSidebarHistory() 刷新侧边栏
  → callback() 解锁输入框（isLoading = false）
```

### 五、新建对话 — `createNewChat()`

```
触发：点击侧边栏"新建对话"按钮
────────────────────────────────
处理（纯前端，不请求后端）：
  activeChatId = null        ← 清空选中
  messages = [欢迎语]        ← 清空聊天区
  question = ''              ← 清空输入框

下次 chat() 时，saveExchange 的 parent_id=0，后端创建新根问题并返回 newId。
```

### 六、删除对话 — `deleteChat(id)`

```
触发：悬停侧边栏记录 → 点击 🗑
────────────────────────────────
请求：POST http://localhost:8000/history/deleteConversation
Body JSON：{ history_id, user_id }

后端返回：
  成功 → { code:200, msg:"已删除 N 条" }
  失败 → { code:500, msg:"对话不存在或无权删除" }

前端处理：
  成功：
    - 删的是当前打开的 → 重置 activeChatId=null + 清空聊天区
    - fetchSidebarHistory() 刷新
  失败：弹错误提示
```

---

## 数据流完整时序（一次完整的新建对话 + 追问）

```
进页面
  │
  ├─ mounted() → fetchSidebarHistory()
  │     └─ GET /history/list → 渲染侧边栏
  │
  ├─ 用户点击"新建对话" → createNewChat()
  │     └─ activeChatId = null，清空聊天区
  │
  ├─ 用户输入"什么是Vue" → chat()
  │     ├─ SSE: GET /chat/chatStream?question=什么是Vue
  │     │     （无 history_id，新建模式）
  │     ├─ 流式接收 AI 回复...
  │     └─ [DONE] → saveExchange("什么是Vue", "Vue是一套...")
  │           └─ POST /history/saveExchange { parent_id:0 }
  │                 └─ 返回 newId=5
  │                 └─ activeChatId = 5  ← 接上新对话链
  │                 └─ fetchSidebarHistory() 侧边栏新增一条
  │
  ├─ 用户追问"和React有什么区别" → chat()
  │     ├─ SSE: GET /chat/chatStream?question=和React有什么区别&history_id=5
  │     │     （带 history_id，后端查历史拼上下文）
  │     ├─ AI 参考之前的对话历史作答 ✓
  │     └─ [DONE] → saveExchange("和React有什么区别", "区别在于...")
  │           └─ POST /history/saveExchange { parent_id:5 }
  │                 └─ activeChatId != null → 不赋值
  │
  └─ 用户点击侧边栏 🗑 → deleteChat(5)
        └─ POST /history/deleteConversation { history_id:5 }
              └─ 后端级联删除根问题+所有追问
              └─ 如当前正打开 → 清空聊天区
              └─ fetchSidebarHistory()
```

---

## 后端接口汇总

| 方法 | 路径 | 参数 | 用途 |
|------|------|------|------|
| GET | `/history/list` | `user_id` | 获取侧边栏（所有根问题） |
| GET | `/history/detail` | `history_id` | 获取某根问题下的完整对话 |
| GET | `/chat/chatStream` | `question, history_id?` | SSE 流式 AI 对话 |
| POST | `/history/saveExchange` | `user_id, parent_id, question, answer` | 保存一轮问答 |
| POST | `/history/deleteConversation` | `history_id, user_id` | 删除对话（级联） |
