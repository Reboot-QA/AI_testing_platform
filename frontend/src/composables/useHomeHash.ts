import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import type { HomeView } from '@/types/shell'

// 首页 index.html 的 hash 语义：#view=home|projects|activity|system（默认 home）。

const VIEWS: readonly string[] = ['home', 'projects', 'activity', 'system']

function readView(): HomeView {
  const v = new URLSearchParams(window.location.hash.replace(/^#/, '')).get('view')
  return v && VIEWS.includes(v) ? (v as HomeView) : 'home'
}

export function useHomeHash() {
  const view = ref<HomeView>(readView())
  const route = useRoute()

  function parse() {
    view.value = readView()
  }

  function setView(next: HomeView) {
    view.value = next
    if (readView() !== next) {
      window.location.hash = 'view=' + next
    }
  }

  // router.push('/hub#view=...') 使用 History API，不保证触发原生 hashchange。
  watch(() => route.fullPath, parse)

  onMounted(() => {
    parse()
    const canonicalHash = '#view=' + view.value
    if (window.location.hash !== canonicalHash) {
      window.history.replaceState(
        window.history.state,
        '',
        window.location.pathname + window.location.search + canonicalHash,
      )
    }
    window.addEventListener('hashchange', parse)
  })
  onBeforeUnmount(() => {
    window.removeEventListener('hashchange', parse)
  })

  return { view, setView }
}
