<template>
  <div v-loading="loading" class="notify-panel">
    <p class="hint">
      配置本项目的失败通知渠道与收件人。定时任务、套件/场景执行、AI 生成失败时按此推送。
    </p>

    <div class="block">
      <div class="block-title">通知场景</div>
      <el-checkbox v-model="form.notify_schedule">定时任务失败</el-checkbox>
      <el-checkbox v-model="form.notify_run">套件 / 场景执行失败</el-checkbox>
      <el-checkbox v-model="form.notify_aigen">AI 生成任务失败</el-checkbox>
    </div>

    <div class="block">
      <div class="block-title">自动重试（仅定时任务）</div>
      <div class="field">
        <span class="lbl">重试次数</span>
        <el-input-number v-model="form.retry_count" :min="0" :max="5" controls-position="right" />
        <span class="sub-hint">0=不重试，最多 5 次；失败自动重跑，全部失败才通知</span>
      </div>
      <div class="field">
        <span class="lbl">重试间隔</span>
        <el-input-number
          v-model="form.retry_interval_sec"
          :min="1"
          :max="60"
          controls-position="right"
        />
        <span class="sub-hint">秒；调度单线程串行，间隔越长越占用调度</span>
      </div>
    </div>

    <div class="block">
      <div class="block-title">
        <el-switch v-model="form.email_enabled" /> <span>邮件（SMTP）</span>
      </div>
      <template v-if="form.email_enabled">
        <div class="field">
          <span class="lbl">SMTP 主机</span
          ><el-input v-model="form.smtp_host" placeholder="如 smtp.qq.com" />
        </div>
        <div class="field">
          <span class="lbl">端口</span
          ><el-input-number
            v-model="form.smtp_port"
            :min="1"
            :max="65535"
            controls-position="right"
          />
        </div>
        <div class="field">
          <span class="lbl">账号</span
          ><el-input v-model="form.smtp_username" placeholder="登录用户名/邮箱" />
        </div>
        <div class="field">
          <span class="lbl">密码</span>
          <el-input
            v-model="form.smtp_password"
            type="password"
            show-password
            :placeholder="smtpPasswordSet ? '已设置，留空不修改' : '授权码/密码'"
          />
        </div>
        <div class="field">
          <span class="lbl">发件人</span
          ><el-input v-model="form.mail_from" placeholder="发件邮箱（留空用账号）" />
        </div>
        <div class="field">
          <span class="lbl">收件人</span>
          <el-input
            v-model="emailRecipients"
            type="textarea"
            :rows="3"
            placeholder="每行一个邮箱（或逗号分隔）"
          />
        </div>
      </template>
    </div>

    <div class="block">
      <div class="block-title">
        <el-switch v-model="form.telegram_enabled" /> <span>Telegram</span>
      </div>
      <template v-if="form.telegram_enabled">
        <div class="field">
          <span class="lbl">Bot Token</span>
          <el-input
            v-model="form.telegram_bot_token"
            type="password"
            show-password
            :placeholder="tgTokenSet ? '已设置，留空不修改' : 'BotFather 给的 token'"
          />
        </div>
        <div class="field">
          <span class="lbl">Chat ID</span>
          <el-input
            v-model="tgChatIds"
            type="textarea"
            :rows="2"
            placeholder="每行一个 chat_id（或逗号分隔）"
          />
        </div>
      </template>
    </div>

    <div v-if="testResults.length" class="test-results">
      <div v-for="r in testResults" :key="r.channel" class="test-row" :class="r.ok ? 'ok' : 'err'">
        {{ r.channel === 'email' ? '邮件' : 'Telegram' }}：{{
          r.ok ? '发送成功' : r.error || '失败'
        }}
      </div>
    </div>

    <div class="actions">
      <el-button type="primary" :loading="saving" @click="save">保存</el-button>
      <el-button :loading="testing" @click="test">测试发送</el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import type { Id } from '@/api/request'
import type { Schemas } from '@/api/types'
import { apifoxApi } from '@/api'

const props = defineProps<{ projectId: Id }>()

const loading = ref(false)
const saving = ref(false)
const testing = ref(false)
const smtpPasswordSet = ref(false)
const tgTokenSet = ref(false)
const emailRecipients = ref('')
const tgChatIds = ref('')
const testResults = ref<Schemas['NotifyChannelResult'][]>([])

const form = reactive({
  notify_schedule: true,
  notify_run: true,
  notify_aigen: true,
  retry_count: 0,
  retry_interval_sec: 5,
  email_enabled: false,
  smtp_host: '',
  smtp_port: 465,
  smtp_username: '',
  smtp_password: '',
  mail_from: '',
  telegram_enabled: false,
  telegram_bot_token: '',
})

const splitLines = (text: string): string[] =>
  text
    .split(/[\n,]/)
    .map((s) => s.trim())
    .filter(Boolean)

const payload = computed<Schemas['NotifyConfigUpdate']>(() => {
  const p: Schemas['NotifyConfigUpdate'] = {
    notify_schedule: form.notify_schedule,
    notify_run: form.notify_run,
    notify_aigen: form.notify_aigen,
    retry_count: form.retry_count,
    retry_interval_sec: form.retry_interval_sec,
    email_enabled: form.email_enabled,
    smtp_host: form.smtp_host || null,
    smtp_port: form.smtp_port,
    smtp_username: form.smtp_username || null,
    mail_from: form.mail_from || null,
    email_recipients: splitLines(emailRecipients.value),
    telegram_enabled: form.telegram_enabled,
    telegram_chat_ids: splitLines(tgChatIds.value),
  }
  if (form.smtp_password) p.smtp_password = form.smtp_password
  if (form.telegram_bot_token) p.telegram_bot_token = form.telegram_bot_token
  return p
})

async function load() {
  loading.value = true
  try {
    const c = await apifoxApi.getNotifyConfig(props.projectId)
    form.notify_schedule = c.notify_schedule
    form.notify_run = c.notify_run
    form.notify_aigen = c.notify_aigen
    form.retry_count = c.retry_count
    form.retry_interval_sec = c.retry_interval_sec
    form.email_enabled = c.email_enabled
    form.smtp_host = c.smtp_host || ''
    form.smtp_port = c.smtp_port
    form.smtp_username = c.smtp_username || ''
    form.mail_from = c.mail_from || ''
    emailRecipients.value = (c.email_recipients || []).join('\n')
    smtpPasswordSet.value = c.smtp_password_set
    form.telegram_enabled = c.telegram_enabled
    tgChatIds.value = (c.telegram_chat_ids || []).join('\n')
    tgTokenSet.value = c.telegram_bot_token_set
  } finally {
    loading.value = false
  }
}

async function save() {
  saving.value = true
  try {
    await apifoxApi.updateNotifyConfig(props.projectId, payload.value)
    ElMessage.success('已保存')
    await load()
  } finally {
    saving.value = false
  }
}

async function test() {
  testing.value = true
  testResults.value = []
  try {
    await apifoxApi.updateNotifyConfig(props.projectId, payload.value) // 先存再测，测的是当前填的
    const res = await apifoxApi.testNotifyConfig(props.projectId)
    testResults.value = res.results || []
    if (!testResults.value.length) ElMessage.info('未启用任何渠道')
    await load()
  } finally {
    testing.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.notify-panel {
  max-width: 560px;
}

.hint {
  color: var(--ax-text-secondary);
  font-size: var(--ax-font-sm);
  margin-bottom: 16px;
}

.block {
  margin-bottom: 20px;
}

.block-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
  margin-bottom: 10px;
}

.field {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 10px;
}

.lbl {
  flex-shrink: 0;
  width: 80px;
  font-size: var(--ax-font-sm);
  color: var(--ax-text-secondary);
}

.sub-hint {
  font-size: var(--ax-font-xs);
  color: var(--ax-text-placeholder);
}

.test-results {
  margin-bottom: 12px;
}

.test-row {
  font-size: var(--ax-font-sm);
  padding: 2px 0;
}

.test-row.ok {
  color: var(--el-color-success);
}

.test-row.err {
  color: var(--el-color-danger);
}

.actions {
  margin-top: 8px;
}
</style>
