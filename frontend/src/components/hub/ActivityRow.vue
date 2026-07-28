<template>
  <div class="row" :class="rowClass" @click="$emit('click')">
    <div class="row-main">
      <div class="title">{{ title }}</div>
      <div class="sub">{{ sub }}</div>
      <div v-if="reason" class="reason" :title="reason">
        <span class="reason-lbl">失败原因</span>{{ reason }}
      </div>
    </div>
    <span v-if="statusText" class="status" :class="statusClass">
      <span v-if="live" class="dot" />{{ statusText }}
    </span>
  </div>
</template>

<script setup lang="ts">
withDefaults(
  defineProps<{
    title: string
    sub: string
    reason?: string | null
    statusText?: string
    statusClass?: string
    rowClass?: string
    live?: boolean
  }>(),
  { reason: null, statusText: '', statusClass: '', rowClass: '', live: false },
)
defineEmits<{ click: [] }>()
</script>

<style scoped>
.row {
  display: flex;
  align-items: flex-start;
  gap: var(--ax-space-2-5);
  padding: var(--ax-space-2-5) var(--ax-space-3);
  border: 1px solid transparent;
  border-radius: var(--ax-radius);
  cursor: pointer;
  transition:
    background var(--ax-transition),
    border-color var(--ax-transition);
}

.row:hover {
  background: var(--ax-bg-subtle);
  border-color: var(--ax-border);
}

.row.live-row {
  background: color-mix(in srgb, var(--ax-tag-green-fg) 4%, var(--ax-bg));
  border-color: color-mix(in srgb, var(--ax-tag-green-fg) 18%, var(--ax-border));
}

.row-main {
  flex: 1;
  min-width: 0;
}

.title {
  font-weight: 600;
  font-size: var(--ax-text-body-sm-size);
  color: var(--ax-text);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.sub {
  color: var(--ax-text-secondary);
  font-size: var(--ax-text-caption-size);
  line-height: var(--ax-text-caption-line);
  margin-top: var(--ax-space-0-5);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.reason {
  margin-top: var(--ax-space-1);
  font-size: var(--ax-text-caption-size);
  line-height: var(--ax-text-caption-line);
  color: var(--ax-text-secondary);
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  line-clamp: 2;
  -webkit-box-orient: vertical;
}

.reason-lbl {
  font-weight: 600;
  margin-right: var(--ax-space-1);
  color: var(--ax-tag-red-fg);
}

.status {
  flex: none;
  display: inline-flex;
  align-items: center;
  gap: var(--ax-space-1);
  font-size: var(--ax-text-caption-size);
  font-weight: 500;
  padding: var(--ax-space-0-5) var(--ax-space-1-5);
  border-radius: var(--ax-radius-sm);
  white-space: nowrap;
  margin-top: 1px;
}

.status.ok {
  color: var(--ax-tag-green-fg);
  background: var(--ax-tag-green-bg);
}

.status.bad {
  color: var(--ax-tag-red-fg);
  background: var(--ax-tag-red-bg);
}

.status.run {
  color: var(--ax-tag-blue-fg);
  background: var(--ax-tag-blue-bg);
}

.dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--ax-tag-green-fg);
  box-shadow: 0 0 0 0 color-mix(in srgb, var(--ax-tag-green-fg) 45%, transparent);
  animation: pulse 1.6s infinite;
}

@keyframes pulse {
  0% {
    box-shadow: 0 0 0 0 color-mix(in srgb, var(--ax-tag-green-fg) 45%, transparent);
  }
  70% {
    box-shadow: 0 0 0 5px color-mix(in srgb, var(--ax-tag-green-fg) 0%, transparent);
  }
  100% {
    box-shadow: 0 0 0 0 color-mix(in srgb, var(--ax-tag-green-fg) 0%, transparent);
  }
}

@media (prefers-reduced-motion: reduce) {
  .dot {
    animation: none;
  }
}
</style>
