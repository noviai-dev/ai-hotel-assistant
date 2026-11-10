import { onMounted, onUnmounted, ref } from 'vue'

// Mount near the viewport once, then keep the chart and its interaction state.
export function useChartVisibility(target) {
  const ready = ref(false)
  let observer

  onMounted(() => {
    if (typeof IntersectionObserver === 'undefined') {
      ready.value = true
      return
    }
    observer = new IntersectionObserver(entries => {
      if (!entries.some(entry => entry.isIntersecting)) return
      ready.value = true
      observer.disconnect()
    }, { rootMargin: '200px 0px' })
    observer.observe(target.value)
  })
  onUnmounted(() => observer?.disconnect())

  return ready
}
