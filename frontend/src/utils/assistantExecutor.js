import router from '@/router'
import { invokeAssistantHandler } from '@/utils/assistantActionRegistry'

const TARGET_ALIASES = {
  'projects.create_btn': 'projects.create_btn',
  'projects.form.name': 'projects.form.name',
  'projects.form.description': 'projects.form.description',
  'projects.form.submit': 'projects.form.submit',
  'menu.projects': 'menu.projects',
  'suites.import_btn': 'suites.swagger_import_btn',
  'suites.swagger_import_btn': 'suites.swagger_import_btn',
  'suites.swagger_source_url': 'suites.swagger_source_url',
  'suites.swagger_url_input': 'suites.swagger_url_input',
  'suites.swagger_parse_btn': 'suites.swagger_parse_btn',
  'suites.swagger_confirm_btn': 'suites.swagger_confirm_btn',
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

function resolveTarget(target) {
  return TARGET_ALIASES[target] || target
}

function findElement(target) {
  const key = resolveTarget(target)
  const el = document.querySelector(`[data-assistant="${key}"]`)
  if (!el) {
    throw new Error(`页面上找不到操作目标：${key}`)
  }
  return el
}

function removeHighlight() {
  document.querySelectorAll('.assistant-highlight-ring').forEach((node) => node.remove())
}

export function highlightElement(target) {
  removeHighlight()
  const el = findElement(target)
  el.scrollIntoView({ behavior: 'smooth', block: 'center', inline: 'nearest' })
  const rect = el.getBoundingClientRect()
  const ring = document.createElement('div')
  ring.className = 'assistant-highlight-ring'
  ring.style.cssText = `
    position: fixed;
    left: ${rect.left - 4}px;
    top: ${rect.top - 4}px;
    width: ${rect.width + 8}px;
    height: ${rect.height + 8}px;
    border: 2px solid #3182ce;
    border-radius: 8px;
    box-shadow: 0 0 0 4px rgba(49, 130, 206, 0.25);
    pointer-events: none;
    z-index: 9999;
    transition: all 0.25s ease;
  `
  document.body.appendChild(ring)
  return ring
}

function dispatchInput(el, value) {
  const input = el.matches('input, textarea') ? el : el.querySelector('input, textarea')
  if (!input) {
    throw new Error('目标元素不是可输入控件')
  }
  input.focus()
  input.value = value
  input.dispatchEvent(new InputEvent('input', { bubbles: true, data: value }))
  input.dispatchEvent(new Event('change', { bubbles: true }))
}

async function executeStep(step, onProgress) {
  const label = step.label || step.type
  onProgress?.({ status: 'running', label, step })

  switch (step.type) {
    case 'navigate':
      await router.push(step.path)
      await sleep(step.wait || step.ms || 500)
      break
    case 'wait':
      await sleep(step.ms || 500)
      break
    case 'invoke':
      highlightElementByLabel(label)
      await invokeAssistantHandler(step.handler, step.payload || {})
      await sleep(step.wait || step.ms || 400)
      break
    case 'click': {
      const el = findElement(step.target)
      const blocked =
        el.disabled
        || el.getAttribute('aria-disabled') === 'true'
        || el.classList.contains('is-disabled')
      if (blocked) {
        throw new Error(`操作目标暂不可用：${step.target}`)
      }
      highlightElement(step.target)
      await sleep(300)
      el.click()
      await sleep(step.wait || step.ms || 300)
      break
    }
    case 'fill': {
      const el = findElement(step.target)
      highlightElement(step.target)
      await sleep(200)
      dispatchInput(el, step.value ?? '')
      await sleep(step.wait || step.ms || 200)
      break
    }
    default:
      throw new Error(`不支持的操作类型：${step.type}`)
  }

  onProgress?.({ status: 'done', label, step })
}

function highlightElementByLabel(label) {
  removeHighlight()
  if (!label) return
  const ring = document.createElement('div')
  ring.className = 'assistant-highlight-ring'
  ring.style.cssText = `
    position: fixed;
    right: 24px;
    bottom: 120px;
    width: 120px;
    height: 36px;
    border-radius: 8px;
    border: 2px solid #3182ce;
    box-shadow: 0 0 0 4px rgba(49, 130, 206, 0.25);
    pointer-events: none;
    z-index: 9999;
  `
  document.body.appendChild(ring)
}

export async function executeAssistantActions(actions, onProgress) {
  if (!Array.isArray(actions) || !actions.length) {
    return { success: true, steps: 0 }
  }

  try {
    for (const step of actions) {
      await executeStep(step, onProgress)
    }
    return { success: true, steps: actions.length }
  } finally {
    setTimeout(removeHighlight, 1200)
  }
}

export function injectAssistantHighlightStyle() {
  if (document.getElementById('assistant-highlight-style')) return
  const style = document.createElement('style')
  style.id = 'assistant-highlight-style'
  style.textContent = `
    .assistant-highlight-ring { animation: assistantPulse 1s ease-in-out infinite; }
    @keyframes assistantPulse {
      0%, 100% { box-shadow: 0 0 0 4px rgba(49, 130, 206, 0.25); }
      50% { box-shadow: 0 0 0 8px rgba(49, 130, 206, 0.15); }
    }
  `
  document.head.appendChild(style)
}
