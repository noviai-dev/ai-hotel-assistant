<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import PriceModule from '../components/PriceModule.vue'

const props = defineProps({ notFound: Boolean })
const route = useRoute()
const now = ref(new Date())
let timer
const hotels = [
  { id: 'novi-dotonbori', name: 'NOVI Dotonbori', rooms: ['房型A', '房型B'] },
  { id: 'zhuyi', name: '住一', rooms: ['房型A', '房型B'] },
]

// Refresh the home page date when it stays open across midnight.
onMounted(() => {
  timer = setInterval(() => { now.value = new Date() }, 1000)
})
onUnmounted(() => clearInterval(timer))

const date = computed(() => {
  if (props.notFound) return null
  if (route.path === '/') {
    const today = now.value
    return [today.getFullYear(), today.getMonth() + 1, today.getDate()]
      .map((part, index) => String(part).padStart(index === 0 ? 4 : 2, '0'))
      .join('/')
  }

  const { year, month, day } = route.params
  const parsed = new Date(0)
  parsed.setFullYear(Number(year), Number(month) - 1, Number(day))
  if (Number(year) < 1 || parsed.getFullYear() !== Number(year)
    || parsed.getMonth() !== Number(month) - 1 || parsed.getDate() !== Number(day)) {
    return null
  }
  return `${year}/${month}/${day}`
})
</script>

<template>
  <h1>{{ date ? (route.path === '/' ? '当前日期' : '指定日期') : '日期无效' }}</h1>
  <time v-if="date" :datetime="date.replaceAll('/', '-')">{{ date }}</time>
  <p v-else>请使用有效的日期路径，例如 /2026/10/10。</p>
  <div v-if="date" class="hotel-sections">
    <section v-for="(hotel, index) in hotels" :key="hotel.id" class="hotel-section" :class="`hotel-section--${hotel.id}`" :aria-labelledby="`${hotel.id}-title`">
      <header class="hotel-heading">
        <span class="hotel-number">部分 {{ index + 1 }}</span>
        <h2 :id="`${hotel.id}-title`">{{ hotel.name }}</h2>
      </header>
      <PriceModule v-for="room in hotel.rooms" :key="room" :room="room" />
    </section>
  </div>
</template>
