<script setup>
import { ref, onMounted, nextTick } from 'vue'
import { processTextAPI, uploadFileAPI, getKnowledgeBaseAPI, deleteKnowledgeFileAPI } from './services/api'
// 新增 Markdown 渲染依赖
import { marked } from 'marked'
import DOMPurify from 'dompurify'

const inputText = ref('')
const isLoading = ref(false)
const messages = ref([])
const chatContainer = ref(null)
const chatHistory = ref([])
const currentChatId = ref(null)
const selectedText = ref('')
const isMCPEnabled = ref(false)
const isRAGEnabled = ref(false) // 新增：RAG功能开关
const activeTab = ref('chat') // 新增：当前激活的tab
const knowledgeFiles = ref([]) // 新增：知识库文件列表
const fileInput = ref(null) // 新增：文件输入引用

// 对话历史管理
const conversations = ref([])

const createNewChat = () => {
  const newChatId = Date.now()
  currentChatId.value = newChatId
  conversations.value.push({
    id: newChatId,
    title: '新对话',
    messages: [],
    lastUpdated: new Date()
  })
  messages.value = []
  inputText.value = ''
}

const deleteConversation = (chatId) => {
  const index = conversations.value.findIndex(c => c.id === chatId)
  if (index !== -1) {
    conversations.value.splice(index, 1)
    // 如果删除的是当前对话，切换到最新的对话或创建新对话
    if (chatId === currentChatId.value) {
      if (conversations.value.length > 0) {
        switchChat(conversations.value[conversations.value.length - 1].id)
      } else {
        createNewChat()
      }
    }
  }
}

const switchChat = (chatId) => {
  currentChatId.value = chatId
  const conversation = conversations.value.find(c => c.id === chatId)
  if (conversation) {
    messages.value = conversation.messages
  }
}

const updateCurrentChat = () => {
  if (currentChatId.value) {
    const conversation = conversations.value.find(c => c.id === currentChatId.value)
    if (conversation) {
      conversation.messages = [...messages.value]
      conversation.lastUpdated = new Date()
      if (messages.value.length > 0) {
        conversation.title = messages.value[0].text.substring(0, 20) + '...'
      }
    }
  }
}

const resetChat = () => {
  createNewChat()
}
const Select_Text = () => {
  isMCPEnabled.value = !isMCPEnabled.value;
  
  console.log('isMCPEnabled: ', isMCPEnabled.value)
}

// 文本选中处理
// const handleTextSelection = () => {
//   const selection = window.getSelection()
//   if (selection.toString().trim()) {
//     selectedText.value = selection.toString()
//     isMCPEnabled.value = true
//   } else {
//     isMCPEnabled.value = false
//   }
// }

const deleteMessage = (index) => {
  messages.value.splice(index, 1)
  updateCurrentChat()
}

const regenerateMessage = async (index) => {
  console.log('开始删除最后对话')
  messages.value.pop(-1)
  console.log('开始重新生成')
  processText()
}

const scrollToBottom = async () => {
  await nextTick()
  if (chatContainer.value) {
    chatContainer.value.scrollTop = chatContainer.value.scrollHeight
  }
}

const handleEnter = (e) => {
  if (!e.shiftKey) {
    processText()
  }
}

const toggleRAG = () => {
  isRAGEnabled.value = !isRAGEnabled.value;
  if (!isRAGEnabled.value) {
    activeTab.value = 'chat'
  }else{
    fetchKnowledgeBase()
  }
  console.log('RAG enabled: ', isRAGEnabled.value)
}

const processText = async (reG = false) => {
  if (!inputText.value.trim() || isLoading.value) return
  
  const currentText = inputText.value
  
  // 用户消息使用普通文本展示
  messages.value.push({
    type: 'user',
    text: currentText
  })
  
  const responseId = Date.now() + Math.random().toString(36).substr(2, 9)
  messages.value.push({
    type: 'assistant',
    text: '',       // 用于存放 HTML
    responseId
  })
  
  isLoading.value = true
  inputText.value = ''
  
  try {
    console.log('message:', messages.value)
    const targetMsg = messages.value.find(m => m.responseId === responseId)
    // 实时流式调用
    let res = ''
    await processTextAPI(
      messages.value,
      (data) => {
        if (!data.done && targetMsg) {
          // 将 Markdown 片段解析并追加为 HTML
          // const htmlSegment = DOMPurify.sanitize(marked.parse(data))
          res += data
          targetMsg.text = marked.parse(res)
          scrollToBottom()
        }
      },
      isRAGEnabled.value, // 传递RAG状态
      isMCPEnabled.value
    )
    // 流结束，更新 streaming 标志
    const finalMsg = messages.value.find(m => m.responseId === responseId)
    if (finalMsg) finalMsg.streaming = false
    updateCurrentChat()
  } catch (error) {
    messages.value = messages.value.map(m =>
      m.responseId === responseId
        ? { type: 'assistant', text: '抱歉，处理过程中出现错误，请重试。', error: true }
        : m
    )
  } finally {
    console.log('message_final', messages.value)
    isLoading.value = false
    scrollToBottom()
  }
}

// 新增：处理文件上传
const handleFileUpload = async (event) => {
  console.log('~ 上传文件')
  console.log('event: ', event.target.files)
  const file = event.target.files[0]
  if (!file) return

  try {
    const formData = new FormData()
    formData.append('file', file)
    await uploadFileAPI(formData)
    await fetchKnowledgeBase()
  } catch (error) {
    console.error('文件上传失败:', error)
  }
}

// 新增：获取知识库文件列表
const fetchKnowledgeBase = async () => {
  console.log('~ 获取列表')
  try {
    const response = await getKnowledgeBaseAPI()
    knowledgeFiles.value = response.files
  } catch (error) {
    console.error('获取知识库失败:', error)
  }
}

// 新增：删除知识库文件
const deleteKnowledgeFile = async (filename) => {
  console.log('~ 删除文件')
  try {
    await deleteKnowledgeFileAPI(filename)
    await fetchKnowledgeBase()
  } catch (error) { 
    console.error('删除文件失败:', error)
  }
}

// 新增：触发文件选择
const triggerFileInput = () => {
  fileInput.value.click()
}

onMounted(() => {
  createNewChat()
  fetchKnowledgeBase()
  // 初始欢迎消息，渲染为 HTML
  // const welcome = '你好！我是**LLM伙伴**, 你可以相信我喵~'
  // messages.value.push({ type: 'system', text: DOMPurify.sanitize(marked.parse(welcome))})
  // document.addEventListener('selectionchange', handleTextSelection)
})
</script>

<template>
  <div class="app">
    <div class="sidebar">
      <div class="logo"><h2>NLP分析系统</h2></div>
      <button class="new-chat" @click="createNewChat">
        <span class="plus-icon">+</span> 新建对话
      </button>
      <div class="history">
        <div class="history-title">历史记录</div>
        <div v-for="conversation in conversations"
             :key="conversation.id"
             :class="['history-item', { active: conversation.id === currentChatId }]"
             @click="switchChat(conversation.id)">
          <div class="history-item-content">
            <div class="history-item-title">{{ conversation.title }}</div>
            <div class="history-item-time">{{ new Date(conversation.lastUpdated).toLocaleString() }}</div>
          </div>
          <button class="delete-conversation-btn" 
                  @click.stop="deleteConversation(conversation.id)"
                  title="删除对话">
            <span class="delete-icon">🗑️</span>
          </button>
        </div>
      </div>
    </div>

    <div class="main-content">
      <div class="tabs" >
        <button :class="['tab-btn', { active: activeTab === 'chat' }]" @click="activeTab = 'chat'">对话</button>
        <button :class="['tab-btn', { active: activeTab === 'knowledge' }]" @click="activeTab = 'knowledge'" v-if="isRAGEnabled">知识库</button>
      </div>

      <div class="chat-container" ref="chatContainer" v-if="activeTab === 'chat'">
        <div v-for="(message, index) in messages"
             :key="index"
             :class="['message', message.type]">
          <div class="avatar">
            <span v-if="message.type === 'user'" class="user-avatar">👤</span>
            <span v-else class="bot-avatar">🤖</span>
          </div>
          <div class="message-content">
            <div class="message-header">
              <span class="message-type">{{ message.type === 'user' ? '用户' : 'AI助手' }}</span>
              <!-- <div class="message-actions" v-if="message.type === 'assistant'">
                <button class="action-btn"
                        @click="regenerateMessage(index)"
                        :disabled="regenerating"
                        v-if="!message.error">
                  <span class="icon">🔄</span> 重新生成
                </button>
                <button class="action-btn" @click="deleteMessage(index)">
                  <span class="icon">🗑️</span> 删除
                </button>
              </div> -->
            </div>
            <div v-if="message.type === 'user'" class="user-input">
              {{ message.text }}
            </div>
            <div v-else class="assistant-response">
              <template v-if="message.error">
                <div class="error-message">{{ message.text }}</div>
              </template>
              <template v-else>
                <!-- 渲染 HTML Markdown -->
                <div class="assistant-text" v-html="message.text"></div>
              </template>
            </div>
          </div>
        </div>
      </div>

      <div class="knowledge-container" v-if="activeTab === 'knowledge'">
        <div class="knowledge-header">
          <h3>知识库管理</h3>
          <button class="upload-btn" @click="triggerFileInput">
            <span class="icon">📁</span> 上传文件
          </button>
          <input type="file" 
                 ref="fileInput" 
                 @change="handleFileUpload" z
                 accept=".txt, .docx"
                 style="display: none">
        </div>
        <div class="knowledge-files">
          <div v-for="file in knowledgeFiles" 
               :key="file.name" 
               class="knowledge-file-item">
            <div class="file-info">
              <span class="file-name">{{ file.name }}</span>
              <span class="file-size">{{ file.size }}</span>
            </div>
            <button class="delete-file-btn" 
                    @click="deleteKnowledgeFile(file.name)"
                    title="删除文件">
              <span class="delete-icon">🗑️</span>
            </button>
          </div>
        </div>
      </div>

      <div class="input-area">
        <div class="input-container">
          <textarea
            v-model="inputText"
            placeholder="输入文本进行分析..."
            class="text-input"
            @keydown.enter.prevent="handleEnter"
            :disabled="isLoading"
          ></textarea>
          <button class="send-button"
                  @click="processText"
                  :disabled="isLoading || !inputText.trim()">
            {{ isLoading ? '思考中...' : '提交' }}
          </button>
        </div>
        <div class="tools">
          <button class="tool-btn search" :class="{ active: isMCPEnabled }" @click="Select_Text">
            <span class="icon">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M12 15.5C13.93 15.5 15.5 13.93 15.5 12C15.5 10.07 13.93 8.5 12 8.5C10.07 8.5 8.5 10.07 8.5 12C8.5 13.93 10.07 15.5 12 15.5ZM19.92 12.75C19.97 12.51 20 12.26 20 12C20 11.74 19.97 11.49 19.92 11.25L21.66 9.91C21.81 9.79 21.87 9.58 21.78 9.39L20.28 6.61C20.19 6.42 19.99 6.34 19.81 6.39L17.81 7.05C17.42 6.73 17 6.47 16.54 6.27L16.29 4.17C16.27 3.98 16.13 3.83 15.94 3.83H12.06C11.87 3.83 11.73 3.98 11.71 4.17L11.46 6.27C11 6.47 10.58 6.73 10.19 7.05L8.19 6.39C8.01 6.34 7.81 6.42 7.72 6.61L6.22 9.39C6.13 9.58 6.19 9.79 6.34 9.91L8.08 11.25C8.03 11.49 8 11.74 8 12C8 12.26 8.03 12.51 8.08 12.75L6.34 14.09C6.19 14.21 6.13 14.42 6.22 14.61L7.72 17.39C7.81 17.58 8.01 17.66 8.19 17.61L10.19 16.95C10.58 17.27 11 17.53 11.46 17.73L11.71 19.83C11.73 20.02 11.87 20.17 12.06 20.17H15.94C16.13 20.17 16.27 20.02 16.29 19.83L16.54 17.73C17 17.53 17.42 17.27 17.81 16.95L19.81 17.61C19.99 17.66 20.19 17.58 20.28 17.39L21.78 14.61C21.87 14.42 21.81 14.21 21.66 14.09L19.92 12.75Z" fill="currentColor"/>
              </svg>
            </span>
            <span class="text">MCP</span>
          </button>
          <button class="tool-btn rag" :class="{ active: isRAGEnabled }" @click="toggleRAG">
            <span class="icon">📚</span>
            <span class="text">RAG</span>
          </button>
          <!-- <button class="tool-btn preview"><span class="icon">🎯</span><span class="text">预览模式</span></button> -->
          <!-- <button class="tool-btn image"><span class="icon">🖼️</span><span class="text">图像生成</span></button> -->
          <!-- <button class="tool-btn video"><span class="icon">🎥</span><span class="text">视频生成</span></button> -->
          <!-- <button class="tool-btn more"><span class="icon">⋮</span></button> -->
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.app {
  display: flex;
  height: 100vh;
  width: 95vw;
  background-color: #ffffff;
}

.sidebar {
  width: 260px;
  background-color: #ffffff;
  border-right: 1px solid #eaecef;
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding: 16px;
}

.logo {
  padding: 8px;
}

.logo h2 {
  font-size: 18px;
  font-weight: 600;
  color: #1a1a1a;
}

.new-chat {
  display: flex;
  align-items: center;
  gap: 8px;
  background-color: #f3f4f6;
  border: none;
  padding: 10px 16px;
  border-radius: 8px;
  cursor: pointer;
  font-size: 14px;
  color: #374151;
  transition: all 0.2s;
}

.new-chat:hover {
  background-color: #e5e7eb;
}

.plus-icon {
  font-size: 16px;
  font-weight: 500;
}

.history {
  flex: 1;
  overflow-y: auto;
}

.history-title {
  font-size: 13px;
  color: #6b7280;
  margin: 16px 0 8px;
}

.history-item {
  padding: 8px 12px;
  border-radius: 8px;
  cursor: pointer;
  margin-bottom: 8px;
  transition: all 0.2s;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.history-item:hover {
  background-color: #b2c9f7;
}

.history-item.active {
  background-color: #b2c9f7;
}

.history-item-content {
  flex: 1;
  min-width: 0;
}

.history-item-title {
  font-size: 14px;
  color: #1a1a1a;
  margin-bottom: 4px;
}

.history-item-time {
  font-size: 12px;
  color: #6b7280;
}

.delete-conversation-btn {
  background: none;
  border: none;
  padding: 4px;
  cursor: pointer;
  opacity: 0.5;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  justify-content: center;
}

.delete-conversation-btn:hover {
  opacity: 1;
  color: #dc2626;
}

.delete-icon {
  font-size: 14px;
}

.main-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  background-color: #f9fafb;
}

.tabs {
  display: flex;
  gap: 8px;
  padding: 12px 24px;
  border-bottom: 1px solid #e5e7eb;
}

.tab-btn {
  padding: 8px 16px;
  border: none;
  background: none;
  cursor: pointer;
  color: #6b7280;
  border-radius: 6px;
  transition: all 0.2s;
}

.tab-btn.active {
  background-color: #b2c9f7;
  color: #ffffff;
}

.chat-container {
  flex: 1;
  overflow-y: auto;
  padding: 24px;
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.message {
  display: flex;
  gap: 12px;
  max-width: 800px;
  margin: 0 auto;
  width: 100%;
}

.avatar {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
}

.user-avatar {
  background-color: #e0e7ff;
  padding: 6px;
  border-radius: 50%;
}

.bot-avatar {
  background-color: #f3e8ff;
  padding: 6px;
  border-radius: 50%;
}

.message-content {
  flex: 1;
  padding: 16px;
  border-radius: 12px;
  background-color: #ffffff;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
}

.user .message-content {
  background-color: #f3f4f6;
}

.analysis-section {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.analysis-item {
  background-color: #ffffff;
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  padding: 16px;
}

.section-title {
  font-size: 14px;
  color: #374151;
  margin-bottom: 12px;
  font-weight: 500;
}

.sentiment-tag {
  display: inline-block;
  padding: 4px 12px;
  border-radius: 16px;
  font-size: 13px;
  font-weight: 500;
}

.sentiment-tag.positive {
  background-color: #ecfdf5;
  color: #059669;
}

.sentiment-tag.negative {
  background-color: #fef2f2;
  color: #dc2626;
}

.keywords-container {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.keyword-tag {
  background-color: #eff6ff;
  color: #3b82f6;
  padding: 4px 12px;
  border-radius: 16px;
  font-size: 13px;
}

.entities-container {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.entity-tag {
  display: flex;
  align-items: center;
  gap: 6px;
  background-color: #faf5ff;
  padding: 4px 12px;
  border-radius: 16px;
  font-size: 13px;
}

.entity-type {
  color: #7c3aed;
  font-weight: 500;
}

.entity-text {
  color: #6d28d9;
}

.input-area {
  padding: 20px;
  background-color: #ffffff;
  border-top: 1px solid #e5e7eb;
}

.input-container {
  max-width: 800px;
  margin: 0 auto;
  position: relative;
  display: flex;
  gap: 12px;
}

.text-input {
  flex: 1;
  min-height: 44px;
  padding: 12px;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  font-size: 14px;
  resize: none;
  background-color: #f9fafb;
  transition: all 0.2s;
}

.text-input:focus {
  outline: none;
  border-color: #6366f1;
  background-color: #ffffff;
}

.send-button {
  padding: 0 20px;
  height: 44px;
  background-color: #6366f1;
  color: white;
  border: none;
  border-radius: 8px;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s;
}

.send-button:hover:not(:disabled) {
  background-color: #4f46e5;
}

.send-button:disabled {
  background-color: #9ca3af;
  cursor: not-allowed;
}

.tools {
  max-width: 800px;
  margin: 12px auto 0;
  display: flex;
  gap: 8px;
  justify-content: flex-start;
}

.tool-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  background-color: #ffffff;
  border: 1px solid #e5e7eb;
  padding: 6px 12px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 13px;
  color: #4b5563;
  transition: all 0.2s;

}

.tool-btn.active {
  color: #ffffff;
  background-color: #6496d4
}

.tool-btn:hover {
  background-color: #d8e1f4;
  border-color: #2c3d57;
}

.tool-btn .icon {
  font-size: 16px;
}

.tool-btn.more {
  padding: 6px 10px;
}

.tool-btn.more .icon {
  font-size: 18px;
}

.message-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.message-type {
  font-size: 12px;
  color: #6b7280;
}

.message-actions {
  display: flex;
  gap: 8px;
}

.action-btn {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 4px 8px;
  border: none;
  background: none;
  color: #6b7280;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.2s;
}

.action-btn:hover {
  color: #374151;
}

.action-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.action-btn .icon {
  font-size: 14px;
}

.error-message {
  color: #dc2626;
  padding: 8px;
  background-color: #fef2f2;
  border-radius: 6px;
}

.streaming-text {
  display: inline-block;
  animation: blink 1s infinite;
}

@keyframes blink {
  0% { opacity: 1; }
  50% { opacity: 0.5; }
  100% { opacity: 1; }
}

/* .tool-btn.active {
  background-color: #e5e7eb;
  color: #1a1a1a;
} */

::selection {
  background-color: #e5e7eb;
  color: #1a1a1a;
}

.knowledge-container {
  flex: 1;
  padding: 24px;
  overflow-y: auto;
}

.knowledge-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.upload-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  background-color: #b2c9f7;
  color: white;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s;
}

.upload-btn:hover {
  background-color: #89b2e3;
}

.knowledge-files {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.knowledge-file-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px;
  background-color: #ffffff;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
}

.file-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.file-name {
  font-size: 14px;
  color: #1a1a1a;
}

.file-size {
  font-size: 12px;
  color: #6b7280;
}

.delete-file-btn {
  background: none;
  border: none;
  padding: 4px;
  cursor: pointer;
  opacity: 0.5;
  transition: all 0.2s;
}

.delete-file-btn:hover {
  opacity: 1;
  color: #dc2626;
}

.tool-btn.rag {
  background-color: #ffffff;
  border-color: #ffffff;
  border: 1px solid #e5e7eb;
}

.tool-btn.rag:hover {
  background-color: #d8e1f4;
  border-color: #2c3d57;
}

.tool-btn.rag.active {
  background-color: #ae8bff;
  color: white;
}
</style>
