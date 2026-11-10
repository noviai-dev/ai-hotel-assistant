<script setup>
import { computed, onMounted, ref, shallowRef, watch } from 'vue'
import { useRoute } from 'vue-router'
import PriceModule from '../components/PriceModule.vue'
import HotelPriceBars from '../components/HotelPriceBars.vue'
import { generatePriceComparison } from '../features/priceComparison.js'
import { buildOverview } from '../features/overview.js'

const props = defineProps({ notFound: Boolean })
const route = useRoute()
// Capture local time once; refreshing the page updates the date and greeting.
const now = new Date()
const chartsReady = ref(false)
const hotelGroups = [
  {
    id: 'self',
    name: '自身酒店',
    hotels: [{ id: 'novi-dotonbori', name: 'NOVI Dotonbori', rooms: ['房型A', '房型B'] }],
  },
  {
    id: 'competitors',
    name: '其他酒店',
    hotels: [
      { id: 'zhuyi', name: '住一', rooms: ['房型A', '房型B'] },
      { id: 'competitor-2', name: '竞品酒店 2（示例）', rooms: ['房型A', '房型B'] },
      { id: 'competitor-3', name: '竞品酒店 3（示例）', rooms: ['房型A', '房型B'] },
    ],
  },
]

onMounted(() => {
  chartsReady.value = true
})

const date = computed(() => {
  if (props.notFound) return null
  if (route.path === '/') {
    const today = now
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

const hotels = hotelGroups.flatMap(group => group.hotels)
// Price snapshots are replaced as a unit; avoid proxying every series and point.
const prices = shallowRef({})
const collectedAt = computed(() => {
  if (!date.value) return null
  const [year, month, day] = date.value.split('/').map(Number)
  return new Date(year, month - 1, day, 12).getTime()
})
const overview = computed(() => collectedAt.value === null ? null : buildOverview(collectedAt.value, now))
const regenerateRoom = (hotelId, room) => {
  prices.value = {
    ...prices.value,
    [hotelId]: {
      ...prices.value[hotelId],
      [room]: generatePriceComparison(new Date(collectedAt.value)),
    },
  }
}
watch([collectedAt, chartsReady], ([timestamp, ready]) => {
  prices.value = timestamp === null || !ready ? {} : Object.fromEntries(hotels.map(hotel => [
    hotel.id,
    Object.fromEntries(hotel.rooms.map(room => [room, generatePriceComparison(new Date(timestamp))])),
  ]))
}, { immediate: true })
</script>

<template>
  <header class="date-overview">
    <template v-if="overview">
      <div class="overview-welcome">
        <span class="overview-eyebrow">每日经营简报</span>
        <span class="overview-demo">模拟数据</span>
      </div>
      <h1>{{ overview.greeting }}。</h1>
      <p class="overview-date">今天是 {{ overview.today }}，{{ overview.weekday }}。正在查看
        <time :datetime="date.replaceAll('/', '-')">{{ date }}</time> 的采集数据。
      </p>
      <p class="overview-range">
        关注入住日期 <strong>{{ overview.start }} — {{ overview.end }}</strong>
        <span>共 16 天，包含 {{ overview.weekendDays }} 个周末日。</span>
      </p>
      <div class="overview-holiday">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" aria-hidden="true">
          <rect x="3" y="5" width="18" height="16" rx="3" /><path d="M8 3v4m8-4v4M3 11h18m5 5h3" stroke-linecap="round" />
        </svg>
        <p><strong>节假日提示（模拟）</strong>：入住区间内的 {{ overview.holidayStart }} — {{ overview.holidayEnd }} 设为演示假期，可关注假期前后的房价变化。</p>
      </div>
      <p class="overview-disclaimer">当前价格及假期提示均为演示数据，尚未接入真实采集记录和节假日日历。</p>
    </template>
    <template v-else>
      <h1>日期无效</h1>
      <p>请使用有效的日期路径，例如 /2026/10/10。</p>
    </template>
  </header>
  <div v-if="date" class="hotel-sections">
    <HotelPriceBars v-if="chartsReady" :hotels="hotels" :prices="prices" :collected-at="collectedAt" :collection-label="date" />
    <section v-for="group in hotelGroups" :key="group.id" class="hotel-section" :class="`hotel-section--${group.id}`" :aria-labelledby="`${group.id}-title`">
      <header class="hotel-heading">
        <h2 :id="`${group.id}-title`">{{ group.name }}</h2>
        <span class="group-count">{{ group.hotels.length }} 家酒店</span>
      </header>
      <component :is="group.id === 'competitors' ? 'details' : 'section'"
        v-for="(hotel, index) in group.hotels" :key="hotel.id" class="hotel-entry"
        :open="group.id === 'competitors' ? true : undefined" :aria-labelledby="`${hotel.id}-title`">
        <component :is="group.id === 'competitors' ? 'summary' : 'header'" class="hotel-entry-heading">
          <span class="hotel-index" aria-hidden="true">{{ String(index + 1).padStart(2, '0') }}</span>
          <h3 :id="`${hotel.id}-title`" class="hotel-name">{{ hotel.name }}</h3>
          <span class="hotel-room-count">{{ hotel.rooms.length }} 个房型</span>
          <svg v-if="group.id === 'competitors'" class="hotel-disclosure" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
            <path d="m6 9 6 6 6-6" stroke-linecap="round" stroke-linejoin="round" />
          </svg>
        </component>
        <PriceModule v-for="(room, roomIndex) in hotel.rooms" :key="room" :room="room" :variant="roomIndex % 2"
          :data="prices[hotel.id]?.[room]" @regenerate="regenerateRoom(hotel.id, room)" />
      </component>
    </section>
  </div>
</template>
