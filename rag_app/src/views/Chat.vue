<template>
  <div class="chat-page">
    <!-- 左侧历史对话侧边栏 -->
    <aside class="history-sidebar" :class="{ collapsed: sidebarCollapsed }">
      <!-- 侧边栏头部 -->
      <div class="sidebar-header">
        <div class="sidebar-title">
          <span class="title-icon">💬</span>
          <span class="title-text">对话记录</span>
        </div>
        <el-button
          type="primary"
          size="small"
          class="new-chat-btn"
          @click="createNewChat"
        >
          <span class="btn-icon">＋</span>
          <span>新建对话</span>
        </el-button>
      </div>

      <!-- 搜索框（纯样式） -->
      <div class="sidebar-search">
        <el-input
          v-model="searchKeyword"
          placeholder="搜索对话..."
          prefix-icon="el-icon-search"
          size="small"
          clearable
        ></el-input>
      </div>

      <!-- 对话记录列表 -->
      <div class="history-list">
        <div
          v-for="chat in conversationList"
          :key="chat.id"
          :class="['history-item', { active: chat.id === activeChatId }]"
          @click="switchChat(chat.id)"
        >
          <div class="item-icon">
            <span>{{ chat.id === activeChatId ? '💬' : '🙈' }}</span>
          </div>
          <div class="item-content">
            <div class="item-title">{{ chat.title }}</div>
          </div>
          <div class="item-meta">
            <span class="item-time">{{ chat.time }}</span>
            <el-button
              type="text"
              size="mini"
              class="item-delete"
              @click.stop="deleteChat(chat.id)"
            >
              🗑
            </el-button>
          </div>
        </div>

        <!-- 空状态 -->
        <div v-if="conversationList.length === 0" class="empty-history">
          <span class="empty-icon">📭</span>
          <p>暂无对话记录</p>
          <p class="empty-hint">点击上方按钮开始新对话</p>
        </div>
      </div>

      <!-- 侧边栏底部操作 -->
      <div class="sidebar-footer">
        <el-button type="text" size="mini" class="footer-btn">
          🗑 清空记录
        </el-button>
      </div>
    </aside>

    <!-- 折叠/展开按钮 -->
    <div class="sidebar-toggle" @click="sidebarCollapsed = !sidebarCollapsed">
      <span>{{ sidebarCollapsed ? '▶' : '◀' }}</span>
    </div>

    <div class="chat-container">
      <!-- 消息列表区域 -->
      <div class="message-list" ref="chatContainer">
        <div
          v-for="(item, index) in messages"
          :key="index"
          :class="['message-item', item.role === 'user' ? 'user' : 'ai']"
        >
          <!-- 头像 -->
          <div class="avatar">
            <span v-if="item.role === 'user'">👤</span>
            <span v-else>🤖</span>
          </div>

          <!-- 消息气泡 -->
          <div class="bubble">
            <!-- 用户消息直接显示纯文本，AI消息使用全局方法渲染 Markdown -->
            <template v-if="item.role === 'user'">{{ item.content }}</template>
            <div v-else class="markdown-body" v-html="$renderMarkdown(item.content)"></div>
          </div>
        </div>

        <!-- 加载状态指示器（实时展示当前环节进度） -->
        <div v-if="isLoading" class="loading-indicator">
          <span>{{ statusText || 'AI 正在思考中...' }}</span>
        </div>
      </div>

      <!-- 底部输入区域 -->
      <div class="input-area">
        <el-input
          v-model="question"
          type="textarea"
          :rows="2"
          placeholder="请输入您的问题..."
          @keyup.enter.native="chat"
          :disabled="isLoading"
          resize="none"
        ></el-input>
        <el-button
          type="primary"
          @click="chat"
          :loading="isLoading"
          class="send-btn"
        >
          {{ isLoading ? '生成中...' : '发 送' }}
        </el-button>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: "Chat",
  data() {
    return {
      question: '家暴怎么办？',
      isLoading: false,
      statusText: '',
      sidebarCollapsed: false,
      searchKeyword: '',
      // 标记用户点击侧边栏时的根问题id
      activeChatId: null,
      messages: [
        { role: 'ai', content: '我是 qwen3.7-max，有什么可以帮助你？😊' },
      ],
      // 模拟的历史对话记录（纯样式数据）,初始为空
      conversationList: [],
    }
  },
  methods: {
    // 侧边栏
    fetchSidebarHistory(){
      const userId =sessionStorage.getItem("userId");
      if (!userId) return ;
      this.$axios({
        method:'get',
        url:this.$serverUrlBase+'history/list',
        params:{user_id:userId}
      }).then(rs=>{
        const body =rs.data;
        if(body.code===200 && body.data){
          //有历史根问题
          //先处理前后端字段名不一致的问题,并存进conversatiobList中
          this.conversationList=body.data.map(item=>({
            id:item.historyId,
            title:item.question,
            time:item.createTime,
          }));
          // ★ 只在没有活跃对话时才自动选第一个
          if (!this.activeChatId && this.conversationList.length > 0) {
                this.activeChatId = this.conversationList[0].id;
          }
        }else{
          //后端查询出来该用户没有任何一次根问题
          this.conversationList = [];
        }
      }).catch(err=>{
        console.error("获取侧边栏历史-失败",err);
        this.conversationList=[];
      });
    },
    // 切换对话(用户点击侧边栏时触发,作用是记录此事根问题id并调用fetchDetail函数再次触发)
    switchChat(id) {
      // 切换对话时也要重新给activeChatId赋值
      this.activeChatId = id;
      this.fetchDetail(id);   // ← 拉取并渲染该对话的所有消息
    },
    // 根问题下的历史详细对话
    fetchDetail(historyId){
      this.$axios({
        method:'get',
        url:this.$serverUrlBase+'history/detail',
        params:{history_id:historyId},
      }).then(rs=>{
        const body=rs.data
        if(body.code===200 && body.data){
          const list=[];
          //将历史问题与回答拆成对话形式
          body.data.forEach(item=>{
            list.push({role:'user',content:item.question});
            list.push({role:'ai',content:item.answer});
          });
          this.messages=list;
          this.scrollToBottom();                        // ← 顺手滚动到底部
        }else{
          this.messages=[];
        }
      }).catch(err=>{
        console.error("获取对话详情界面-失败",err);
      });
    },
    // 保存追问或者新对话到后端
    saveExchange(userQuestion,aiAnswer){
      const userId = sessionStorage.getItem("userId");
      if (!userId) return;
      // ⭐新建对话时 parent_id=0，追问时 parent_id=当前根问题id
      const parentId = this.activeChatId || 0;

      this.$axios({
        method: 'post',
        url: this.$serverUrlBase + 'history/saveExchange',
        data: {
          user_id: userId,
          parent_id: parentId,
          question: userQuestion,
          answer: aiAnswer,
        },
      }).then(rs => {
        const body = rs.data;
        if (body.code === 200) {
          // 如果之前是新建对话（activeChatId 为空），用后端返回的新 id 接上
          if (!this.activeChatId && body.data !== null) {
            // 后端此时传来的新id就可以赋值给activaeChatId了
            this.activeChatId = body.data;
          }
          // 刷新侧边栏列表
          this.fetchSidebarHistory();
        }
      }).catch(err => {
        console.error('保存问答失败', err);
  });
    },
    // 新建对话栏(点击"新建对话"触发,负责清除界面)
    createNewChat() {
      this.activeChatId = null;
      this.messages = [
        { role: 'ai', content: '我是 qwen3.7-max，有什么可以帮助你？😊' },
      ];
      this.question = '';
    },
    // 删除对话（仅样式，待实现）
    deleteChat(id) {
      const userId = sessionStorage.getItem("userId");
      if (!userId) return;

      this.$axios({
        method: 'post',
        url: this.$serverUrlBase + 'history/deleteConversation',
        data: {
          history_id: id,
          user_id: userId,
        },
      }).then(rs => {
        const body = rs.data;
        if (body.code === 200) {
          this.$message.success('删除成功');
          // 如果删的是当前打开的对话，重置聊天区
          if (id === this.activeChatId) {
            this.activeChatId = null;
            this.messages = [
              { role: 'ai', content: '我是 qwen3.7-max，有什么可以帮助你？😊' },
            ];
          }
          // 刷新侧边栏
          this.fetchSidebarHistory();
        } else {
          this.$message.error(body.msg);
        }
      }).catch(err => {
        console.error('删除对话失败', err);
        this.$message.error('删除失败，请重试');
      });
    },

    // 滚动到底部
    scrollToBottom() {
      this.$nextTick(() => {
        const container = this.$refs.chatContainer;
        if (container) {
          container.scrollTop = container.scrollHeight;
        }
      });
    },
    // 聊天方法
    chat() {
      let _this = this;
      let myQuestion = this.question;
      if (!myQuestion) return;

      myQuestion = myQuestion.trim();
      if (myQuestion === '') {
        this.$message.warning("请输入问题");
        return;
      }

      // 1. 添加用户消息
      this.messages.push({ role: 'user', content: myQuestion });
      this.question = '';
      this.scrollToBottom();

      // 2. 添加 AI 占位消息
      this.messages.push({ role: 'ai', content: '' });
      this.isLoading = true;
      this.statusText = '';
      this.scrollToBottom();

      // 3. 构造 EventSource
      let s = "";
      let params = new URLSearchParams({ question: myQuestion });
      // 如果不是新对话,就把根问题id传给后端; 如果是新对话就不用传,因为后端会把值默认设为0
      if (this.activeChatId) {
        params.append('parent_id', this.activeChatId);
      }
      // 'chat/chatStream?' 就是做的法律问答系统
      // 'chat/chatStreamNoe4j?' 做的是Neo4j知识图谱问答[医学疾病类]
      let eventSource = new EventSource(this.$serverUrlBase + 'chat/chatStream?' + params);
      eventSource.onopen = (event) => {
        console.log("监听-连接成功打开", event);
      };
      eventSource.onerror = (event) => {
        console.log("监听-有错误", event);
        _this.isLoading = false;
        eventSource.close();
      };
      eventSource.onmessage = (event) => {
        // JSON.parse() 在解析时会自动把后端传来的如 \u5f97 还原成汉字“得”。所以，虽然你在后端控制台看到的是乱码一样的编码，但前端拿到数据并渲染到页面上时，依然是正常的中文。
        let newData = JSON.parse(event.data);
        console.log("收到数据:", event.data);

        const type = newData.type;

        if (type === 'done' || newData.content === '[DONE]') {
          console.log("对话结束，主动关闭连接");
          eventSource.close();

           // ← 新增：保存本轮问答
          const userQuestion = myQuestion;
          const aiAnswer = s;
          _this.saveExchange(userQuestion, aiAnswer);
          _this.isLoading = false; //// 保存成功后才能发下一条
          _this.statusText = '';   // 清空进度提示
        }
        // ② 进度事件：更新加载指示器文案（检索/重排序/生成中...）
        else if (type === 'status') {
          _this.statusText = newData.content;
        }
        // ③ 正文事件：增量追加答案 token
        else {
          s += newData.content;
          _this.messages[_this.messages.length - 1].content = s;
          _this.scrollToBottom();
        }
      };
    }
  },
  mounted() {
    this.scrollToBottom();
    this.fetchSidebarHistory();// 也就是说会渲染一次
  },
}
</script>

<style scoped>
/* ========== 页面整体布局 ========== */
.chat-page {
  display: flex;
  justify-content: flex-start;
  align-items: stretch;
  min-height: 100vh;
  background-color: #f4f6f9;
  padding: 0;
  box-sizing: border-box;
}

/* ========== 左侧历史对话侧边栏 ========== */
.history-sidebar {
  width: 300px;
  min-width: 300px;
  background: #ffffff;
  display: flex;
  flex-direction: column;
  border-right: 1px solid #e8eaed;
  transition: all 0.3s ease;
  overflow: hidden;
  z-index: 10;
}

.history-sidebar.collapsed {
  width: 0;
  min-width: 0;
  border-right: none;
}

/* 侧边栏头部 */
.sidebar-header {
  padding: 16px 16px 12px;
  border-bottom: 1px solid #f0f2f5;
}

.sidebar-title {
  display: flex;
  align-items: center;
  margin-bottom: 12px;
}

.title-icon {
  font-size: 20px;
  margin-right: 8px;
}

.title-text {
  font-size: 16px;
  font-weight: 600;
  color: #303133;
}

.new-chat-btn {
  width: 100%;
  border-radius: 8px;
  font-size: 13px;
  height: 36px;
}

.new-chat-btn .btn-icon {
  font-size: 16px;
  font-weight: bold;
  margin-right: 4px;
}

/* 搜索框 */
.sidebar-search {
  padding: 10px 16px;
  border-bottom: 1px solid #f0f2f5;
}

/* 对话记录列表 */
.history-list {
  flex: 1;
  overflow-y: auto;
  padding: 8px 12px;
}

.history-item {
  display: flex;
  align-items: center;
  padding: 12px;
  margin-bottom: 4px;
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.2s ease;
  position: relative;
}

.history-item:hover {
  background-color: #f5f7fa;
}

.history-item.active {
  background-color: #ecf5ff;
}

.history-item.active .item-title {
  color: #409eff;
  font-weight: 600;
}

.item-icon {
  font-size: 18px;
  margin-right: 10px;
  flex-shrink: 0;
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f5f7fa;
  border-radius: 8px;
}

.history-item.active .item-icon {
  background: #d9ecff;
}

.item-content {
  flex: 1;
  min-width: 0;
}

.item-title {
  font-size: 13px;
  font-weight: 500;
  color: #303133;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.item-meta {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  flex-shrink: 0;
  margin-left: 8px;
}

.item-time {
  font-size: 11px;
  color: #c0c4cc;
  white-space: nowrap;
  margin-bottom: 2px;
}

.item-delete {
  font-size: 12px;
  opacity: 0;
  transition: opacity 0.2s ease;
  padding: 2px 4px;
}

.history-item:hover .item-delete {
  opacity: 1;
}

/* 空状态 */
.empty-history {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px 20px;
  color: #c0c4cc;
}

.empty-icon {
  font-size: 48px;
  margin-bottom: 12px;
}

.empty-history p {
  font-size: 14px;
  color: #909399;
  margin: 4px 0;
}

.empty-hint {
  font-size: 12px !important;
  color: #c0c4cc !important;
}

/* 侧边栏底部 */
.sidebar-footer {
  padding: 10px 16px;
  border-top: 1px solid #f0f2f5;
  text-align: center;
}

.footer-btn {
  color: #c0c4cc;
  font-size: 12px;
}

.footer-btn:hover {
  color: #f56c6c;
}

/* ========== 折叠/展开按钮 ========== */
.sidebar-toggle {
  width: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  background: #ffffff;
  border-right: 1px solid #e8eaed;
  transition: background 0.2s ease;
  user-select: none;
  flex-shrink: 0;
}

.sidebar-toggle:hover {
  background: #ecf5ff;
}

.sidebar-toggle span {
  font-size: 12px;
  color: #909399;
}

/* ========== 聊天容器 ========== */
.chat-container {
  flex: 1;
  min-width: 0;
  height: 100vh;
  background: #ffffff;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

/* 消息列表区域 */
.message-list {
  flex: 1;
  padding: 20px;
  overflow-y: auto;
  background-color: #fafbfc;
}

.message-item {
  display: flex;
  margin-bottom: 16px;
  align-items: flex-start;
}

/* 用户消息靠右 */
.message-item.user {
  flex-direction: row-reverse;
}

/* 头像样式 */
.avatar {
  font-size: 24px;
  width: 40px;
  height: 40px;
  display: flex;
  justify-content: center;
  align-items: center;
  border-radius: 50%;
  background-color: #e9ecef;
  flex-shrink: 0;
}

/* 气泡样式 */
.bubble {
  max-width: 70%;
  padding: 12px 16px;
  border-radius: 12px;
  font-size: 14px;
  line-height: 1.6;
  word-break: break-word;
  margin: 0 10px;
}

/* 用户气泡 */
.message-item.user .bubble {
  background-color: #409eff;
  color: #ffffff;
  border-top-right-radius: 4px;
}

/* AI 气泡 */
.message-item.ai .bubble {
  background-color: #ffffff;
  color: #333333;
  border-top-left-radius: 4px;
  border: 1px solid #ebeef5;
}

/* 加载状态 */
.loading-indicator {
  text-align: center;
  color: #909399;
  font-size: 14px;
  padding: 10px 0;
}

/* 底部输入区域 */
.input-area {
  display: flex;
  align-items: flex-end;
  padding: 16px 20px;
  border-top: 1px solid #ebeef5;
  background-color: #ffffff;
}

.send-btn {
  margin-left: 12px;
  height: 54px;
  padding: 0 24px;
}

/* 深度选择器：美化 Markdown 渲染内容 */
.markdown-body >>> pre {
  background-color: #f6f8fa;
  padding: 12px;
  border-radius: 6px;
  overflow-x: auto;
  margin: 8px 0;
}

.markdown-body >>> code {
  background-color: rgba(27, 31, 35, 0.05);
  padding: 2px 4px;
  border-radius: 4px;
  font-family: Consolas, monospace;
}

.markdown-body >>> pre code {
  background: transparent;
  padding: 0;
}

.markdown-body >>> p {
  margin: 0 0 8px 0;
}
</style>
