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
            <p>点击下方常见问题查看平台操作步骤；也可直接输入任意问题。</p>
            <div class="suggestions">
              <button
                v-for="item in visibleSuggestions"
                :key="item.text"
                type="button"
                class="suggestion-btn"
                :disabled="loading"
                @click="sendSuggestion(item)"
              >
                <el-icon><Promotion /></el-icon>
                <span>{{ item.text }}</span>
              </button>
            </div>
          </div>

          <div v-for="msg in messages" :key="msg.id" class="message-row" :class="msg.role">
            <div class="bubble">
              <div v-if="msg.content" v-html="formatContent(msg.content)" />
            </div>
          </div>

          <div v-if="loading" class="message-row assistant">
            <div class="bubble typing"><span></span><span></span><span></span></div>
          </div>
        </div>

        <footer class="panel-footer">
          <div v-if="modeLabel" class="mode-tag">{{ modeLabel }}</div>
          <div class="input-wrap">
            <el-input
              v-model="input"
              :maxlength="PASTE_MAX_LEN"
              type="textarea"
              :rows="3"
              resize="none"
              placeholder="例如：接口自动化里如何运行场景？"
              :disabled="loading"
              @keydown.enter.exact.prevent="handleSend"
            />
            <el-button
              type="primary"
              class="send-btn"
              :loading="loading"
              :disabled="!input.trim() || loading"
              @click="handleSend"
            >
              <el-icon><Promotion /></el-icon>
            </el-button>
          </div>
          <p class="footer-tip">平台相关问题将结合系统菜单作答；复杂问题需已配置大模型</p>
        </footer>
      </aside>
    </transition>

    <div
      v-show="!open"
      class="assistant-fab-wrap"
      :class="{ dragging, tucked, 'fab-compact': fabCompact }"
      :style="{ bottom: `${fabBottom}px` }"
      @mouseenter="onFabHoverEnter"
      @mouseleave="onFabHoverLeave"
    >
      <span class="fab-label">AI 助手</span>
      <div class="fab-stack">
        <div class="fab-avatar-slot">
          <span class="fab-pulse" aria-hidden="true"></span>
          <button
            type="button"
            class="assistant-fab"
            aria-label="打开 AI 助手"
            @click="onFabClick"
            @mousedown="onDragStart"
            @touchstart.passive="onTouchStart"
          >
            <img src="/assistant-avatar.png" alt="AI 助手" class="fab-avatar" />
          </button>
        </div>
        <button
          type="button"
          class="fab-collapse-btn"
          :aria-label="fabCompact ? '展开助手头像' : '缩小助手头像'"
          @click.stop="toggleFabCompact"
        >
          <el-icon>
            <ArrowRight v-if="!fabCompact" />
            <ArrowLeft v-else />
          </el-icon>
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { PASTE_MAX_LEN } from '@/constants/limits'
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { assistantApi } from '@/api'
import { useUserStore } from '@/stores/user'
import {
  ASSISTANT_GUIDES,
  resolveAssistantGuideAnswer,
  type AssistantGuide,
} from '@/constants/assistantGuides'
import { clearAssistantChat } from '@/utils/assistantChatStorage'

type MessageRole = 'user' | 'assistant'

interface ChatMessage {
  id: string
  role: MessageRole
  content: string
}

interface StreamChatOptions {
  displayText?: string
}

interface AssistantStreamEvent {
  type: 'meta' | 'token' | 'error'
  mode?: string
  provider_name?: string
  model?: string
  content?: string
  message?: string
}

const route = useRoute()
const userStore = useUserStore()

const open = ref(false)
const input = ref('')
const loading = ref(false)
const messageListRef = ref<HTMLElement | null>(null)
const modeLabel = ref('')
const abortController = ref<AbortController | null>(null)
const fabBottom = ref(24)
const dragging = ref(false)
const dragMoved = ref(false)
const tucked = ref(false)
const fabCompact = ref(false)
const FAB_STORAGE_KEY = 'assistant-fab-bottom'
const FAB_COMPACT_KEY = 'assistant-fab-compact'
const FAB_MIN_BOTTOM = 56
const FAB_TUCK_IDLE_MS = 3500

let tuckIdleTimer: ReturnType<typeof setTimeout> | null = null

let messageSeq = 0

function createMessageId() {
  messageSeq += 1
  return `msg-${Date.now()}-${messageSeq}`
}

function resetAssistantChatToWelcome() {
  stopStreaming()
  clearAssistantChat()
  messages.value = []
  messageSeq = 0
  input.value = ''
  loading.value = false
  modeLabel.value = ''
}

function closeAssistantPanel() {
  open.value = false
}

function prepareAssistantForSessionStart() {
  resetAssistantChatToWelcome()
  closeAssistantPanel()
}

function resetAssistantChat() {
  prepareAssistantForSessionStart()
}

function buildChatPayload(excludeAssistantId?: string) {
  return messages.value
    .filter((item) => item.id !== excludeAssistantId)
    .filter((item) => item.role === 'user' || item.content?.trim())
    .map((item) => ({ role: item.role, content: item.content }))
}

const messages = ref<ChatMessage[]>([])

const visibleSuggestions = computed(() =>
  ASSISTANT_GUIDES.filter((item) =>
    item.permissions.some((permission) => userStore.hasPermission(permission)),
  ),
)
function assistantPagePath(): string {
  return route.fullPath
}

function formatContent(text: string) {
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
  () => scrollToBottom(),
)

watch(
  () => userStore.token,
  (token, prev) => {
    if (!token) {
      resetAssistantChat()
    } else if (token && !prev) {
      prepareAssistantForSessionStart()
    }
  },
)

onMounted(() => {
  const saved = localStorage.getItem(FAB_STORAGE_KEY)
  if (saved && !Number.isNaN(Number(saved))) {
    fabBottom.value = clampFabBottom(Number(saved))
  }
  fabCompact.value = localStorage.getItem(FAB_COMPACT_KEY) === '1'
  if (userStore.token) {
    prepareAssistantForSessionStart()
  }
  scheduleFabTuck()
})

onBeforeUnmount(() => {
  clearFabTuckTimer()
})

watch(open, (visible) => {
  if (visible) {
    tucked.value = false
    clearFabTuckTimer()
    if (messages.value.length) {
      scrollToBottom()
    }
  } else {
    scheduleFabTuck()
  }
})

function clampFabBottom(value: number) {
  const maxBottom = Math.max(FAB_MIN_BOTTOM, window.innerHeight - 96)
  return Math.min(maxBottom, Math.max(FAB_MIN_BOTTOM, value))
}

function clearFabTuckTimer() {
  if (tuckIdleTimer) {
    clearTimeout(tuckIdleTimer)
    tuckIdleTimer = null
  }
}

function scheduleFabTuck() {
  clearFabTuckTimer()
  if (open.value || dragging.value) return
  tuckIdleTimer = setTimeout(() => {
    if (!open.value && !dragging.value) {
      tucked.value = true
    }
  }, FAB_TUCK_IDLE_MS)
}

function onFabHoverEnter() {
  tucked.value = false
  clearFabTuckTimer()
}

function onFabHoverLeave() {
  scheduleFabTuck()
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

function toggleFabCompact() {
  fabCompact.value = !fabCompact.value
  tucked.value = false
  clearFabTuckTimer()
  localStorage.setItem(FAB_COMPACT_KEY, fabCompact.value ? '1' : '0')
}

function persistFabBottom() {
  localStorage.setItem(FAB_STORAGE_KEY, String(fabBottom.value))
}

function onDragStart(event: MouseEvent) {
  if (event.button !== 0) return
  startDrag(event.clientY)
}

function onTouchStart(event: TouchEvent) {
  if (!event.touches?.length) return
  startDrag(event.touches[0].clientY)
}

function startDrag(clientY: number) {
  dragging.value = true
  dragMoved.value = false
  tucked.value = false
  clearFabTuckTimer()
  const startY = clientY
  const startBottom = fabBottom.value

  const onMove = (nextY: number) => {
    const delta = startY - nextY
    if (Math.abs(delta) > 4) dragMoved.value = true
    fabBottom.value = clampFabBottom(startBottom + delta)
  }

  const onMouseMove = (ev: MouseEvent) => onMove(ev.clientY)
  const onTouchMove = (ev: TouchEvent) => {
    if (ev.touches?.length) onMove(ev.touches[0].clientY)
  }

  const onEnd = () => {
    dragging.value = false
    persistFabBottom()
    scheduleFabTuck()
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

function findGuideAnswer(text: string): string | undefined {
  return resolveAssistantGuideAnswer(text)
}

async function streamChat(question: string, options: StreamChatOptions = {}) {
  const displayText = options.displayText || question
  const text = displayText.trim()
  if (!text) return

  const guideAnswer = findGuideAnswer(displayText) || findGuideAnswer(question)
  if (guideAnswer) {
    messages.value.push({ id: createMessageId(), role: 'user', content: displayText })
    messages.value.push({ id: createMessageId(), role: 'assistant', content: guideAnswer })
    scrollToBottom()
    return
  }

  messages.value.push({ id: createMessageId(), role: 'user', content: displayText })
  input.value = ''
  loading.value = true
  modeLabel.value = ''

  const assistantId = createMessageId()
  messages.value.push({
    id: assistantId,
    role: 'assistant',
    content: '',
  })

  stopStreaming()
  abortController.value = new AbortController()

  const findAssistantMessage = () => messages.value.find((item) => item.id === assistantId)

  try {
    await assistantApi.chatStream(
      {
        messages: buildChatPayload(assistantId),
        page_path: assistantPagePath(),
      },
      (event: AssistantStreamEvent) => {
        const assistantMessage = findAssistantMessage()
        if (!assistantMessage) return

        if (event.type === 'meta') {
          modeLabel.value =
            event.mode === 'mock' ? 'Mock 模式' : event.provider_name || event.model || '大模型'
        } else if (event.type === 'token') {
          assistantMessage.content += event.content || ''
          scrollToBottom()
        } else if (event.type === 'error') {
          throw new Error(event.message || '助手回复失败')
        }
      },
      { signal: abortController.value.signal },
    )
  } catch (error: unknown) {
    if (error instanceof DOMException && error.name === 'AbortError') return
    const assistantMessage = findAssistantMessage()
    const fallback = error instanceof Error ? error.message : '助手暂时不可用'
    if (assistantMessage && !assistantMessage.content) {
      assistantMessage.content = fallback
    }
    ElMessage.error(fallback)
  } finally {
    loading.value = false
    abortController.value = null
    const assistantMessage = findAssistantMessage()
    if (assistantMessage && !assistantMessage.content) {
      assistantMessage.content = '暂无回复，请稍后重试。'
    }
    scrollToBottom()
  }
}

function handleSend() {
  const text = input.value.trim()
  if (!text || loading.value) return
  streamChat(text)
}

function sendSuggestion(item: AssistantGuide) {
  if (loading.value) return
  messages.value.push({ id: createMessageId(), role: 'user', content: item.text })
  messages.value.push({ id: createMessageId(), role: 'assistant', content: item.answer })
  scrollToBottom()
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
  right: 16px;
  z-index: 3001;
  display: flex;
  align-items: center;
  gap: var(--ax-space-2);
  user-select: none;
  transition: transform 0.28s ease;
}

.assistant-fab-wrap.tucked:not(:hover):not(.dragging) {
  /* 收起时仅停 pulse，头像保持完整可见（不再 translate 出屏） */
  transform: none;
}

.assistant-fab-wrap.dragging {
  transition: none;
}

.fab-stack {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--ax-space-1);
}

.fab-avatar-slot {
  position: relative;
  flex-shrink: 0;
}

.fab-collapse-btn {
  width: 22px;
  height: 22px;
  border: 1px solid #e2e8f0;
  border-radius: 50%;
  padding: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #fff;
  color: #718096;
  box-shadow: 0 2px 8px rgba(15, 23, 42, 0.08);
  cursor: pointer;
  transition:
    background 0.15s ease,
    color 0.15s ease;
}

.fab-collapse-btn:hover {
  color: #3182ce;
  border-color: #bee3f8;
  background: #ebf8ff;
}

.fab-collapse-btn .el-icon {
  font-size: 12px;
}

.fab-pulse {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  border-radius: 50%;
  background: rgba(49, 130, 206, 0.3);
  animation: fabPulse 2.4s ease-out infinite;
  pointer-events: none;
}

.assistant-fab-wrap.fab-compact .assistant-fab {
  width: 32px;
  height: 32px;
  border-width: 1.5px;
}

.assistant-fab-wrap.fab-compact .fab-avatar-slot {
  width: 32px;
  height: 32px;
}

.assistant-fab-wrap.fab-compact .fab-collapse-btn {
  width: 20px;
  height: 20px;
}

.fab-label {
  padding: var(--ax-space-1-5) var(--ax-space-3);
  border-radius: 999px;
  background: linear-gradient(135deg, #3182ce, #2c5282);
  color: #fff;
  font-size: var(--ax-text-caption-size);
  font-weight: 600;
  letter-spacing: 0.3px;
  box-shadow: 0 4px 16px rgba(49, 130, 206, 0.3);
  white-space: nowrap;
  opacity: 0;
  max-width: 0;
  overflow: hidden;
  padding-left: 0;
  padding-right: 0;
  pointer-events: none;
  transition:
    opacity 0.2s ease,
    max-width 0.25s ease,
    padding 0.25s ease;
}

.assistant-fab-wrap:hover .fab-label,
.assistant-fab-wrap.tucked:hover .fab-label {
  opacity: 1;
  max-width: 120px;
  padding: var(--ax-space-1-5) var(--ax-space-3);
}

.assistant-fab {
  position: relative;
  z-index: 1;
  width: 48px;
  height: 48px;
  border: 2px solid #fff;
  border-radius: 50%;
  padding: 0;
  background: #ebf8ff;
  box-shadow: 0 6px 20px rgba(49, 130, 206, 0.35);
  cursor: grab;
  overflow: hidden;
  touch-action: none;
  transition:
    transform 0.2s ease,
    box-shadow 0.2s ease;
}

.assistant-fab-wrap.dragging .assistant-fab {
  cursor: grabbing;
}

.fab-avatar {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
  pointer-events: none;
}

.assistant-fab-wrap:hover .assistant-fab {
  transform: scale(1.05);
  box-shadow: 0 8px 24px rgba(49, 130, 206, 0.45);
}

.assistant-fab-wrap.fab-compact:not(:hover) .fab-pulse,
.assistant-fab-wrap.tucked:not(:hover):not(.dragging) .fab-pulse {
  animation: none;
  opacity: 0;
}

@keyframes fabPulse {
  0% {
    transform: scale(0.92);
    opacity: 0.55;
  }
  70% {
    transform: scale(1.25);
    opacity: 0;
  }
  100% {
    transform: scale(1.25);
    opacity: 0;
  }
}

.assistant-panel {
  position: fixed;
  right: 0;
  bottom: 20px;
  width: 480px;
  max-width: min(520px, calc(100vw - 48px));
  height: min(calc(100vh - 80px), 680px);
  min-height: 360px;
  background: #fff;
  border-left: 1px solid #e2e8f0;
  box-shadow: -4px 0 20px rgba(15, 23, 42, 0.06);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--ax-space-3) var(--ax-space-3-5);
  border-bottom: 1px solid #edf2f7;
  background: linear-gradient(180deg, #f8fbff 0%, #fff 100%);
  flex-shrink: 0;
}

.panel-title {
  display: flex;
  align-items: center;
  gap: var(--ax-space-2);
  font-size: var(--ax-text-title-sm-size);
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
  padding: var(--ax-space-4);
  background: #f7fafc;
}

.welcome {
  text-align: center;
  padding: var(--ax-space-6) var(--ax-space-2) var(--ax-space-2);
}

.welcome-avatar {
  width: 72px;
  height: 72px;
  margin: 0 auto var(--ax-space-3);
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
  margin: 0 0 var(--ax-space-2);
  font-size: var(--ax-text-title-size);
  color: #1a202c;
}

.welcome p {
  margin: 0 0 var(--ax-space-5);
  color: #718096;
  font-size: var(--ax-text-body-size);
  line-height: var(--ax-leading-relaxed);
}

.suggestions {
  display: flex;
  flex-direction: column;
  gap: var(--ax-space-2-5);
  text-align: left;
}

.suggestion-btn {
  display: flex;
  align-items: center;
  gap: var(--ax-space-2);
  width: 100%;
  padding: var(--ax-space-3) var(--ax-space-3-5);
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  background: #fff;
  color: #2d3748;
  font-size: var(--ax-text-body-sm-size);
  cursor: pointer;
  transition:
    border-color 0.2s,
    box-shadow 0.2s;
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
  margin-bottom: var(--ax-space-3);
}

.message-row.user {
  justify-content: flex-end;
}

.message-row.assistant {
  justify-content: flex-start;
}

.bubble {
  max-width: 92%;
  padding: var(--ax-space-2-5) var(--ax-space-3);
  border-radius: 12px;
  font-size: var(--ax-text-body-size);
  line-height: var(--ax-leading-relaxed);
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
  gap: var(--ax-space-1);
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
  padding: var(--ax-space-3) var(--ax-space-4) var(--ax-space-4);
  border-top: 1px solid #edf2f7;
  background: #fff;
}

.mode-tag {
  margin-bottom: var(--ax-space-2);
  font-size: var(--ax-text-caption-size);
  color: #718096;
}

.input-wrap {
  position: relative;
}

.input-wrap :deep(.el-textarea__inner) {
  padding-right: var(--ax-space-12);
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
  margin: var(--ax-space-2) 0 0;
  font-size: var(--ax-text-caption-size);
  color: #a0aec0;
  text-align: center;
}

.assistant-slide-enter-active,
.assistant-slide-leave-active {
  transition: transform 0.24s ease;
}

.assistant-slide-enter-from,
.assistant-slide-leave-to {
  transform: translateX(100%);
}

@media (max-width: 768px) {
  .assistant-panel {
    bottom: 12px;
    width: calc(100vw - 24px);
    max-width: none;
    height: min(calc(100vh - 64px), 560px);
    min-height: 320px;
  }

  .assistant-fab-wrap {
    right: 12px;
  }

  .assistant-fab-wrap.tucked:not(:hover):not(.dragging) {
    transform: none;
  }
}
</style>
