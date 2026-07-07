<template>
  <div class="assistant-root">
    <transition name="assistant-slide">
      <aside v-if="open" class="assistant-panel">
        <header class="panel-header">
          <div class="panel-title">
            <el-icon class="title-icon"><MagicStick /></el-icon>
            <span>AI 助手</span>
          </div>
          <el-button link @click="open = false">
            <el-icon><Close /></el-icon>
          </el-button>
        </header>

        <div ref="messageListRef" class="panel-body">
          <div v-if="!messages.length" class="welcome">
            <div class="welcome-avatar">
              <el-icon :size="28"><Cpu /></el-icon>
            </div>
            <h3>Hi，我是 AI 质量平台助手</h3>
            <p>可以问我如何创建项目、生成用例、配置接口自动化等操作。</p>
            <div class="suggestions">
              <button
                v-for="item in suggestions"
                :key="item.text"
                type="button"
                class="suggestion-btn"
                :disabled="loading"
                @click="sendSuggestion(item.query)"
              >
                <el-icon><Promotion /></el-icon>
                <span>{{ item.text }}</span>
              </button>
            </div>
          </div>

          <div
            v-for="(msg, index) in messages"
            :key="index"
            class="message-row"
            :class="msg.role"
          >
            <div class="bubble" v-html="formatContent(msg.content)" />
          </div>

          <div v-if="loading" class="message-row assistant">
            <div class="bubble typing">
              <span></span><span></span><span></span>
            </div>
          </div>
        </div>

        <footer class="panel-footer">
          <div v-if="modeLabel" class="mode-tag">{{ modeLabel }}</div>
          <div class="input-wrap">
            <el-input
              v-model="input"
              type="textarea"
              :rows="3"
              resize="none"
              placeholder="有什么关于平台使用的问题，都可以问我"
              :disabled="loading"
              @keydown.enter.exact.prevent="handleSend"
            />
            <el-button
              type="primary"
              class="send-btn"
              :loading="loading"
              :disabled="!input.trim()"
              @click="handleSend"
            >
              <el-icon><Promotion /></el-icon>
            </el-button>
          </div>
          <p class="footer-tip">回答由 AI 生成，仅供参考</p>
        </footer>
      </aside>
    </transition>

    <button
      type="button"
      class="assistant-fab"
      :class="{ active: open }"
      aria-label="打开 AI 助手"
      @click="togglePanel"
    >
      <el-icon :size="22"><ChatDotRound /></el-icon>
    </button>
  </div>
</template>

<script setup>
import { nextTick, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { assistantApi } from '@/api'

const route = useRoute()

const open = ref(false)
const input = ref('')
const loading = ref(false)
const messages = ref([])
const messageListRef = ref()
const modeLabel = ref('')
const abortController = ref(null)

const suggestions = [
  { text: '如何创建项目并开始测试？', query: '如何创建项目并开始测试？请给出详细步骤。' },
  { text: '怎样用 AI 生成测试用例？', query: '怎样使用 AI 生成测试用例？需要哪些前置条件？' },
  { text: '接口自动化怎么配置？', query: '接口自动化模块怎么配置环境、套件和执行？' },
  { text: '部门权限和用户怎么管理？', query: '部门权限和用户管理应该怎么配置？' },
]

function formatContent(text) {
  if (!text) return ''
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/\n/g, '<br>')
}

function scrollToBottom() {
  nextTick(() => {
    const el = messageListRef.value
    if (el) el.scrollTop = el.scrollHeight
  })
}

watch(
  () => messages.value.length,
  () => scrollToBottom()
)

function togglePanel() {
  open.value = !open.value
}

function stopStreaming() {
  if (abortController.value) {
    abortController.value.abort()
    abortController.value = null
  }
}

async function streamChat(question) {
  messages.value.push({ role: 'user', content: question })
  loading.value = true
  modeLabel.value = ''

  const assistantIndex = messages.value.length
  messages.value.push({ role: 'assistant', content: '' })

  stopStreaming()
  abortController.value = new AbortController()

  try {
    await assistantApi.chatStream(
      {
        messages: messages.value
          .slice(0, -1)
          .filter((item) => item.content)
          .map((item) => ({ role: item.role, content: item.content })),
        page_path: route.path,
      },
      (event) => {
        if (event.type === 'meta') {
          modeLabel.value = event.mode === 'mock' ? 'Mock 模式' : event.provider_name || event.model || '大模型'
        } else if (event.type === 'token') {
          messages.value[assistantIndex].content += event.content || ''
          scrollToBottom()
        } else if (event.type === 'error') {
          throw new Error(event.message || '助手回复失败')
        }
      },
      { signal: abortController.value.signal }
    )
  } catch (error) {
    if (error.name === 'AbortError') return
    const fallback = error.message || '助手暂时不可用'
    if (!messages.value[assistantIndex].content) {
      messages.value[assistantIndex].content = fallback
    }
    ElMessage.error(fallback)
  } finally {
    loading.value = false
    abortController.value = null
    if (!messages.value[assistantIndex].content) {
      messages.value[assistantIndex].content = '暂无回复，请稍后重试。'
    }
  }
}

function handleSend() {
  const text = input.value.trim()
  if (!text || loading.value) return
  input.value = ''
  streamChat(text)
}

function sendSuggestion(query) {
  if (loading.value) return
  streamChat(query)
}
</script>

<style scoped>
.assistant-root {
  position: fixed;
  right: 0;
  bottom: 0;
  z-index: 3000;
  pointer-events: none;
}

.assistant-fab,
.assistant-panel {
  pointer-events: auto;
}

.assistant-fab {
  position: fixed;
  right: 24px;
  bottom: 24px;
  width: 52px;
  height: 52px;
  border: none;
  border-radius: 50%;
  background: linear-gradient(135deg, #3182ce, #2b6cb0);
  color: #fff;
  box-shadow: 0 8px 24px rgba(49, 130, 206, 0.45);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.assistant-fab:hover,
.assistant-fab.active {
  transform: scale(1.05);
  box-shadow: 0 10px 28px rgba(49, 130, 206, 0.55);
}

.assistant-panel {
  position: fixed;
  top: 0;
  right: 0;
  width: 400px;
  max-width: calc(100vw - 16px);
  height: 100vh;
  background: #fff;
  border-left: 1px solid #e2e8f0;
  box-shadow: -8px 0 32px rgba(15, 23, 42, 0.12);
  display: flex;
  flex-direction: column;
}

.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 16px;
  border-bottom: 1px solid #edf2f7;
  background: linear-gradient(180deg, #f8fbff 0%, #fff 100%);
}

.panel-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 16px;
  font-weight: 600;
  color: #1a365d;
}

.title-icon {
  color: #3182ce;
}

.panel-body {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
  background: #f7fafc;
}

.welcome {
  text-align: center;
  padding: 24px 8px 8px;
}

.welcome-avatar {
  width: 56px;
  height: 56px;
  margin: 0 auto 12px;
  border-radius: 50%;
  background: linear-gradient(135deg, #ebf8ff, #bee3f8);
  color: #2b6cb0;
  display: flex;
  align-items: center;
  justify-content: center;
}

.welcome h3 {
  margin: 0 0 8px;
  font-size: 18px;
  color: #1a202c;
}

.welcome p {
  margin: 0 0 20px;
  color: #718096;
  font-size: 14px;
  line-height: 1.6;
}

.suggestions {
  display: flex;
  flex-direction: column;
  gap: 10px;
  text-align: left;
}

.suggestion-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  padding: 12px 14px;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  background: #fff;
  color: #2d3748;
  font-size: 13px;
  cursor: pointer;
  transition: border-color 0.2s, box-shadow 0.2s;
}

.suggestion-btn:hover:not(:disabled) {
  border-color: #90cdf4;
  box-shadow: 0 2px 8px rgba(49, 130, 206, 0.12);
}

.suggestion-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.message-row {
  display: flex;
  margin-bottom: 12px;
}

.message-row.user {
  justify-content: flex-end;
}

.message-row.assistant {
  justify-content: flex-start;
}

.bubble {
  max-width: 88%;
  padding: 10px 12px;
  border-radius: 12px;
  font-size: 14px;
  line-height: 1.65;
  word-break: break-word;
}

.message-row.user .bubble {
  background: #3182ce;
  color: #fff;
  border-bottom-right-radius: 4px;
}

.message-row.assistant .bubble {
  background: #fff;
  color: #2d3748;
  border: 1px solid #e2e8f0;
  border-bottom-left-radius: 4px;
}

.typing {
  display: flex;
  gap: 4px;
  align-items: center;
  min-width: 48px;
}

.typing span {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #a0aec0;
  animation: blink 1.2s infinite ease-in-out;
}

.typing span:nth-child(2) {
  animation-delay: 0.15s;
}

.typing span:nth-child(3) {
  animation-delay: 0.3s;
}

@keyframes blink {
  0%,
  80%,
  100% {
    opacity: 0.3;
    transform: translateY(0);
  }
  40% {
    opacity: 1;
    transform: translateY(-2px);
  }
}

.panel-footer {
  padding: 12px 16px 16px;
  border-top: 1px solid #edf2f7;
  background: #fff;
}

.mode-tag {
  margin-bottom: 8px;
  font-size: 12px;
  color: #718096;
}

.input-wrap {
  position: relative;
}

.input-wrap :deep(.el-textarea__inner) {
  padding-right: 48px;
}

.send-btn {
  position: absolute;
  right: 8px;
  bottom: 8px;
  width: 34px;
  height: 34px;
  padding: 0;
}

.footer-tip {
  margin: 8px 0 0;
  font-size: 11px;
  color: #a0aec0;
  text-align: center;
}

.assistant-slide-enter-active,
.assistant-slide-leave-active {
  transition: transform 0.25s ease, opacity 0.25s ease;
}

.assistant-slide-enter-from,
.assistant-slide-leave-to {
  transform: translateX(100%);
  opacity: 0;
}

@media (max-width: 768px) {
  .assistant-panel {
    width: 100vw;
  }

  .assistant-fab {
    right: 16px;
    bottom: 16px;
  }
}
</style>
