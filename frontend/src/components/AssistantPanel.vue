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
              <img src="/assistant-avatar.png" alt="AI 助手" class="welcome-avatar-img" />
            </div>
            <h3>Hi，我是 AI 质量平台助手</h3>
            <p>点击下方示例，助手将自动在浏览器中演示操作；也可直接输入问题。</p>
            <div class="suggestions">
              <button
                v-for="item in suggestions"
                :key="item.text"
                type="button"
                class="suggestion-btn"
                :disabled="loading || executing"
                @click="sendSuggestion(item)"
              >
                <el-icon><Promotion /></el-icon>
                <span>{{ item.text }}</span>
              </button>
            </div>
          </div>

          <div
            v-for="msg in messages"
            :key="msg.id"
            class="message-row"
            :class="msg.role"
          >
            <div class="bubble">
              <div v-if="msg.content" v-html="formatContent(msg.content)" />
              <div v-if="msg.actions?.length" class="action-card">
                <div class="action-title">待执行操作（{{ msg.actions.length }} 步）</div>
                <ul>
                  <li v-for="(step, stepIndex) in msg.actions" :key="stepIndex">
                    {{ step.label || step.type }}
                  </li>
                </ul>
                <div v-if="msg.executionLogs?.length" class="exec-logs">
                  <div v-for="(log, logIndex) in msg.executionLogs" :key="logIndex" class="exec-log">
                    <el-icon v-if="log.status === 'done'" color="#38a169"><CircleCheck /></el-icon>
                    <el-icon v-else-if="log.status === 'error'" color="#e53e3e"><CircleClose /></el-icon>
                    <el-icon v-else class="spin"><Loading /></el-icon>
                    <span>{{ log.label }}</span>
                  </div>
                </div>
                <div v-if="msg.actionStatus === 'pending'" class="action-buttons">
                  <el-button size="small" @click="cancelPlan(msg.id)">取消</el-button>
                  <el-button size="small" type="primary" @click="runPlan(msg.id)">确认执行</el-button>
                </div>
                <div v-else-if="msg.actionStatus === 'done'" class="action-done">操作已完成</div>
                <div v-else-if="msg.actionStatus === 'error'" class="action-error">{{ msg.actionError }}</div>
              </div>
            </div>
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
              placeholder="例如：帮我演示创建一个项目叫「登录模块测试」"
              :disabled="loading || executing"
              @keydown.enter.exact.prevent="handleSend"
            />
            <el-button
              type="primary"
              class="send-btn"
              :loading="loading"
              :disabled="!input.trim() || executing"
              @click="handleSend"
            >
              <el-icon><Promotion /></el-icon>
            </el-button>
          </div>
          <p class="footer-tip">支持浏览器自动操作；写入类操作需您确认后执行</p>
        </footer>
      </aside>
    </transition>

    <div
      v-show="!open"
      class="assistant-fab-wrap"
      :class="{ dragging, active: open }"
      :style="{ bottom: `${fabBottom}px` }"
      @mousedown="onDragStart"
      @touchstart.passive="onTouchStart"
    >
      <span class="fab-pulse" aria-hidden="true"></span>
      <span class="fab-label">AI 助手</span>
      <button type="button" class="assistant-fab" aria-label="打开 AI 助手" @click="onFabClick">
        <img src="/assistant-avatar.png" alt="AI 助手" class="fab-avatar" />
      </button>
    </div>
  </div>
</template>

<script setup>
import { nextTick, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { assistantApi } from '@/api'
import { useUserStore } from '@/stores/user'
import { executeAssistantActions, injectAssistantHighlightStyle } from '@/utils/assistantExecutor'
import {
  loadAssistantMessages,
  saveAssistantMessages,
  clearAssistantChat,
} from '@/utils/assistantChatStorage'

const route = useRoute()
const userStore = useUserStore()

const open = ref(false)
const input = ref('')
const loading = ref(false)
const executing = ref(false)
const messageListRef = ref()
const modeLabel = ref('')
const abortController = ref(null)
const fabBottom = ref(24)
const dragging = ref(false)
const dragMoved = ref(false)
const FAB_STORAGE_KEY = 'assistant-fab-bottom'
const FAB_MIN_BOTTOM = 72

let messageSeq = 0

function createMessageId() {
  messageSeq += 1
  return `msg-${Date.now()}-${messageSeq}`
}

function normalizeStoredMessage(item) {
  return {
    id: item.id || createMessageId(),
    role: item.role,
    content: item.content || '',
    actions: Array.isArray(item.actions) ? item.actions : [],
    actionStatus: item.actionStatus || null,
    executionLogs: Array.isArray(item.executionLogs) ? item.executionLogs : [],
    actionError: item.actionError || '',
  }
}

function loadStoredMessages() {
  const loaded = loadAssistantMessages({
    createMessageId,
    normalizeMessage: normalizeStoredMessage,
  })
  messageSeq = loaded.messageSeq
  return loaded.messages
}

function persistMessages() {
  if (!userStore.token) return
  saveAssistantMessages(messages.value)
}

function resetAssistantChat() {
  stopStreaming()
  clearAssistantChat()
  messages.value = []
  messageSeq = 0
  input.value = ''
  loading.value = false
  executing.value = false
  open.value = false
  modeLabel.value = ''
}

function buildChatPayload(excludeAssistantId) {
  return messages.value
    .filter((item) => item.id !== excludeAssistantId)
    .filter((item) => item.role === 'user' || item.content?.trim())
    .map((item) => ({ role: item.role, content: item.content }))
}

const messages = ref(loadStoredMessages())

const suggestions = [
  { text: '帮我演示项目管理全流程', preset: 'project_management_full' },
  { text: '帮我演示需求管理全流程', preset: 'requirement_management_full' },
  { text: '帮我演示用例管理全流程', preset: 'testcase_management_full' },
  { text: '帮我演示接口自动化管理全流程', preset: 'api_automation_management_full' },
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

watch(
  messages,
  () => {
    persistMessages()
  },
  { deep: true }
)

watch(
  () => userStore.token,
  (token) => {
    if (!token) {
      resetAssistantChat()
    }
  }
)

onMounted(() => {
  injectAssistantHighlightStyle()
  const saved = localStorage.getItem(FAB_STORAGE_KEY)
  if (saved && !Number.isNaN(Number(saved))) {
    fabBottom.value = clampFabBottom(Number(saved))
  }
  if (messages.value.length) {
    scrollToBottom()
  }
})

watch(open, (visible) => {
  if (visible && messages.value.length) {
    scrollToBottom()
  }
})

function clampFabBottom(value) {
  const maxBottom = Math.max(FAB_MIN_BOTTOM, window.innerHeight - 120)
  return Math.min(maxBottom, Math.max(FAB_MIN_BOTTOM, value))
}

function togglePanel() {
  open.value = !open.value
}

function onFabClick() {
  if (dragMoved.value) {
    dragMoved.value = false
    return
  }
  togglePanel()
}

function persistFabBottom() {
  localStorage.setItem(FAB_STORAGE_KEY, String(fabBottom.value))
}

function onDragStart(event) {
  if (event.button !== 0) return
  startDrag(event.clientY)
}

function onTouchStart(event) {
  if (!event.touches?.length) return
  startDrag(event.touches[0].clientY)
}

function startDrag(clientY) {
  dragging.value = true
  dragMoved.value = false
  const startY = clientY
  const startBottom = fabBottom.value

  const onMove = (nextY) => {
    const delta = startY - nextY
    if (Math.abs(delta) > 4) dragMoved.value = true
    fabBottom.value = clampFabBottom(startBottom + delta)
  }

  const onMouseMove = (ev) => onMove(ev.clientY)
  const onTouchMove = (ev) => {
    if (ev.touches?.length) onMove(ev.touches[0].clientY)
  }

  const onEnd = () => {
    dragging.value = false
    persistFabBottom()
    document.removeEventListener('mousemove', onMouseMove)
    document.removeEventListener('mouseup', onEnd)
    document.removeEventListener('touchmove', onTouchMove)
    document.removeEventListener('touchend', onEnd)
  }

  document.addEventListener('mousemove', onMouseMove)
  document.addEventListener('mouseup', onEnd)
  document.addEventListener('touchmove', onTouchMove, { passive: true })
  document.addEventListener('touchend', onEnd)
}

function stopStreaming() {
  if (abortController.value) {
    abortController.value.abort()
    abortController.value = null
  }
}

async function streamChat(question, options = {}) {
  const displayText = options.displayText || question
  messages.value.push({ id: createMessageId(), role: 'user', content: displayText })
  loading.value = true
  modeLabel.value = ''

  const assistantId = createMessageId()
  messages.value.push({
    id: assistantId,
    role: 'assistant',
    content: '',
    actions: [],
    actionStatus: null,
    executionLogs: [],
    actionError: '',
  })

  stopStreaming()
  abortController.value = new AbortController()

  const findAssistantMessage = () => messages.value.find((item) => item.id === assistantId)
  let shouldAutoExecute = !!options.autoExecute

  try {
    await assistantApi.chatStream(
      {
        messages: buildChatPayload(assistantId),
        page_path: route.path,
        demo_preset: options.preset || undefined,
      },
      (event) => {
        const assistantMessage = findAssistantMessage()
        if (!assistantMessage) return

        if (event.type === 'meta') {
          modeLabel.value = event.mode === 'mock' ? 'Mock 模式' : event.provider_name || event.model || '大模型'
        } else if (event.type === 'plan') {
          assistantMessage.actions = event.actions || []
          if (event.actions?.length) {
            assistantMessage.actionStatus = 'pending'
          }
          if (event.needs_confirmation === false) {
            shouldAutoExecute = shouldAutoExecute || !!options.autoExecute
          }
        } else if (event.type === 'token') {
          assistantMessage.content += event.content || ''
          scrollToBottom()
        } else if (event.type === 'error') {
          throw new Error(event.message || '助手回复失败')
        }
      },
      { signal: abortController.value.signal }
    )
  } catch (error) {
    if (error.name === 'AbortError') return
    const assistantMessage = findAssistantMessage()
    const fallback = error.message || '助手暂时不可用'
    if (assistantMessage && !assistantMessage.content) {
      assistantMessage.content = fallback
    }
    ElMessage.error(fallback)
  } finally {
    loading.value = false
    abortController.value = null
    const assistantMessage = findAssistantMessage()
    if (assistantMessage && !assistantMessage.content && !assistantMessage.actions?.length) {
      assistantMessage.content = '暂无回复，请稍后重试。'
    }
    scrollToBottom()
    if (shouldAutoExecute && assistantMessage?.actionStatus === 'pending' && assistantMessage.actions?.length) {
      await runPlan(assistantId)
    }
  }
}

function cancelPlan(messageId) {
  const msg = messages.value.find((item) => item.id === messageId)
  if (!msg) return
  msg.actionStatus = 'cancelled'
  msg.actions = []
}

async function runPlan(messageId) {
  const msg = messages.value.find((item) => item.id === messageId)
  if (!msg?.actions?.length || executing.value) return

  executing.value = true
  msg.actionStatus = 'running'
  msg.executionLogs = []
  msg.actionError = ''

  try {
    await executeAssistantActions(msg.actions, (progress) => {
      const existing = msg.executionLogs.find((item) => item.label === progress.label)
      if (existing) {
        existing.status = progress.status
      } else {
        msg.executionLogs.push({ label: progress.label, status: progress.status })
      }
      scrollToBottom()
    })
    msg.actionStatus = 'done'
    msg.content += '\n\n**已在浏览器中完成上述操作。**'
    ElMessage.success('自动操作已完成')
  } catch (error) {
    msg.actionStatus = 'error'
    msg.actionError = error.message || '执行失败'
    ElMessage.error(msg.actionError)
  } finally {
    executing.value = false
    scrollToBottom()
  }
}

function handleSend() {
  const text = input.value.trim()
  if (!text || loading.value || executing.value) return
  input.value = ''
  streamChat(text)
}

function sendSuggestion(item) {
  if (loading.value || executing.value || !item?.preset) return
  streamChat(item.text, {
    preset: item.preset,
    autoExecute: true,
    displayText: item.text,
  })
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

.assistant-fab-wrap,
.assistant-panel {
  pointer-events: auto;
}

.assistant-fab-wrap {
  position: fixed;
  right: 18px;
  z-index: 3001;
  display: flex;
  align-items: center;
  gap: 10px;
  cursor: grab;
  user-select: none;
  touch-action: none;
}

.assistant-fab-wrap.dragging {
  cursor: grabbing;
}

.fab-pulse {
  position: absolute;
  right: 0;
  width: 68px;
  height: 68px;
  border-radius: 50%;
  background: rgba(49, 130, 206, 0.35);
  animation: fabPulse 2s ease-out infinite;
  pointer-events: none;
}

.fab-label {
  padding: 8px 14px;
  border-radius: 999px;
  background: linear-gradient(135deg, #3182ce, #2c5282);
  color: #fff;
  font-size: 13px;
  font-weight: 600;
  letter-spacing: 0.5px;
  box-shadow: 0 6px 20px rgba(49, 130, 206, 0.35);
  white-space: nowrap;
}

.assistant-fab {
  position: relative;
  width: 68px;
  height: 68px;
  border: 3px solid #fff;
  border-radius: 50%;
  padding: 0;
  background: #ebf8ff;
  box-shadow: 0 10px 28px rgba(49, 130, 206, 0.45);
  cursor: inherit;
  overflow: hidden;
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.fab-avatar {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
  pointer-events: none;
}

.assistant-fab-wrap:hover .assistant-fab,
.assistant-fab-wrap.active .assistant-fab {
  transform: scale(1.06);
  box-shadow: 0 12px 32px rgba(49, 130, 206, 0.55);
}

.assistant-fab-wrap.active .fab-label {
  background: linear-gradient(135deg, #2b6cb0, #1a365d);
}

@keyframes fabPulse {
  0% {
    transform: scale(0.95);
    opacity: 0.7;
  }
  70% {
    transform: scale(1.35);
    opacity: 0;
  }
  100% {
    transform: scale(1.35);
    opacity: 0;
  }
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
  overflow: hidden;
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
  min-height: 0;
  overflow-y: auto;
  overflow-x: hidden;
  padding: 16px;
  background: #f7fafc;
}

.welcome {
  text-align: center;
  padding: 24px 8px 8px;
}

.welcome-avatar {
  width: 72px;
  height: 72px;
  margin: 0 auto 12px;
  border-radius: 50%;
  background: #fff;
  border: 3px solid #bee3f8;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
}

.welcome-avatar-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
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

.action-card {
  margin-top: 10px;
  padding: 10px;
  border-radius: 8px;
  background: #f0fff4;
  border: 1px solid #c6f6d5;
}

.action-title {
  font-size: 13px;
  font-weight: 600;
  color: #276749;
  margin-bottom: 6px;
}

.action-card ul {
  margin: 0 0 8px;
  padding-left: 18px;
  font-size: 12px;
  color: #2f855a;
}

.action-buttons {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}

.action-done {
  font-size: 12px;
  color: #276749;
}

.action-error {
  font-size: 12px;
  color: #c53030;
}

.exec-logs {
  margin: 8px 0;
}

.exec-log {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: #4a5568;
  margin-bottom: 4px;
}

.spin {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
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

  .assistant-fab-wrap {
    right: 12px;
  }

  .fab-label {
    font-size: 12px;
    padding: 6px 10px;
  }
}
</style>
