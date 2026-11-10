<script setup>
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const route = useRoute()
const router = useRouter()
const picker = ref(null)
const trigger = ref(null)
const calendar = ref(null)
const open = ref(false)
const month = ref(new Date())
const weekdays = ['日', '一', '二', '三', '四', '五', '六']
const datePath = (date) => '/' + [date.getFullYear(), date.getMonth() + 1, date.getDate()]
  .map((part, index) => String(part).padStart(index === 0 ? 4 : 2, '0')).join('/')

function currentDate() {
  const { year, month, day } = route.params
  const date = new Date()
  if (year && month && day) {
    date.setFullYear(Number(year), Number(month) - 1, Number(day))
    if (Number(year) > 0 && datePath(date) === route.path) return date
  }
  return new Date()
}

const days = computed(() => {
  const first = new Date(month.value)
  first.setDate(1)
  const count = new Date(first.getFullYear(), first.getMonth() + 1, 0).getDate()
  return [
    ...Array(first.getDay()).fill(null),
    ...Array.from({ length: count }, (_, index) => {
      const date = new Date(first)
      date.setDate(index + 1)
      return { day: index + 1, path: datePath(date) }
    }),
  ]
})
const selectedPath = computed(() => datePath(currentDate()))

async function close(restoreFocus = false) {
  open.value = false
  if (restoreFocus) {
    await nextTick()
    trigger.value?.focus()
  }
}

async function toggle() {
  if (open.value) return close()
  month.value = currentDate()
  month.value.setDate(1)
  open.value = true
  await nextTick()
  calendar.value?.querySelector('[aria-pressed="true"]')?.focus()
}

function changeMonth(offset) {
  const next = new Date(month.value)
  next.setMonth(next.getMonth() + offset)
  if (next.getFullYear() >= 1 && next.getFullYear() <= 9999) month.value = next
}

async function selectDate(path) {
  await router.push(path)
  close(true)
}

function outsideClick(event) {
  if (!picker.value?.contains(event.target)) close()
}

function leavePicker(event) {
  if (event.relatedTarget && !picker.value?.contains(event.relatedTarget)) close()
}

watch(() => route.path, () => close())
onMounted(() => document.addEventListener('pointerdown', outsideClick))
onUnmounted(() => document.removeEventListener('pointerdown', outsideClick))
</script>

<template>
  <header class="site-header">
    <nav class="site-nav" aria-label="主导航">
      <RouterLink to="/" class="nav-brand" aria-label="NOVI 酒店经营助手首页">
        <span class="nav-brand-mark" aria-hidden="true">N<span></span></span>
        <span class="nav-brand-copy"><span class="nav-brand-name">NOVI<span class="nav-brand-divider" aria-hidden="true"></span><span class="nav-brand-location">DOTONBORI</span></span><span class="nav-brand-caption">酒店经营助手</span></span>
      </RouterLink>
      <div class="site-nav-actions">
        <RouterLink to="/" class="home-link" exact-active-class="is-active">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" aria-hidden="true">
            <path d="m3 10 9-7 9 7v10a1 1 0 0 1-1 1h-5v-7H9v7H4a1 1 0 0 1-1-1Z" stroke-linejoin="round" />
          </svg>
          <span>首页</span>
        </RouterLink>
        <span class="nav-action-divider" aria-hidden="true"></span>
        <div ref="picker" class="date-picker" @keydown.esc.stop.prevent="close(true)" @focusout="leavePicker">
          <button ref="trigger" type="button" class="date-toggle" :class="{ 'is-active': route.path !== '/' }"
            :aria-label="`切换日期，当前采集日期 ${selectedPath.slice(1)}`"
            aria-haspopup="dialog" :aria-expanded="open" aria-controls="date-calendar" @click="toggle">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true">
              <rect x="3" y="5" width="18" height="16" rx="2" />
              <path d="M16 3v4M8 3v4M3 11h18" />
            </svg>
            <span class="date-toggle-copy"><span class="date-toggle-label">切换日期</span><span class="date-toggle-value">{{ selectedPath.slice(1) }}</span></span>
            <svg class="date-toggle-chevron" :class="{ 'is-open': open }" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true"><path d="m6 9 6 6 6-6" stroke-linecap="round" stroke-linejoin="round" /></svg>
          </button>
          <section v-if="open" id="date-calendar" ref="calendar" class="date-calendar" role="dialog" aria-label="选择页面日期">
            <div class="calendar-intro"><span>选择采集日期</span><span>按日查看酒店价格</span></div>
            <div class="calendar-heading">
              <button type="button" aria-label="上个月" :disabled="month.getFullYear() === 1 && month.getMonth() === 0" @click="changeMonth(-1)">‹</button>
              <span aria-live="polite">{{ month.getFullYear() }} 年 {{ month.getMonth() + 1 }} 月</span>
              <button type="button" aria-label="下个月" :disabled="month.getFullYear() === 9999 && month.getMonth() === 11" @click="changeMonth(1)">›</button>
            </div>
            <div class="calendar-grid">
              <span v-for="day in weekdays" :key="day" class="calendar-weekday">{{ day }}</span>
              <template v-for="(date, index) in days" :key="index">
                <button v-if="date" type="button" class="calendar-day"
                  :aria-label="date.path.slice(1)" :aria-pressed="date.path === selectedPath"
                  :aria-current="date.path === datePath(new Date()) ? 'date' : undefined" @click="selectDate(date.path)">{{ date.day }}</button>
                <span v-else aria-hidden="true"></span>
              </template>
            </div>
            <button type="button" class="calendar-today" @click="selectDate(datePath(new Date()))"><span class="calendar-today-dot" aria-hidden="true"></span>回到今天<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true"><path d="M5 12h14m-6-6 6 6-6 6" stroke-linecap="round" stroke-linejoin="round" /></svg></button>
          </section>
        </div>
      </div>
    </nav>
  </header>
</template>
