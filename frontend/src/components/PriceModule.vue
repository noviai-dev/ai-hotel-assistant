<script setup>
import { onMounted, shallowRef } from 'vue'
import PriceComparison from './PriceComparison.vue'
import PriceCandlestick from './PriceCandlestick.vue'
import { generatePriceComparison, COLLECTION_COUNT } from '../features/priceComparison.js'

defineProps({ room: { type: String, required: true } })
const priceData = shallowRef(null)
const regeneratePrices = () => { priceData.value = generatePriceComparison() }
onMounted(regeneratePrices)
</script>

<template>
  <article class="price-module" :aria-label="`${room}价格模块`">
    <header class="chart-heading">
      <div>
        <h3>{{ room }} <span class="module-label">价格模块</span></h3>
        <p>今天 +30～+45 天 · 每个入住日期 {{ COLLECTION_COUNT }} 次采集 · 价格范围 20000～40000</p>
      </div>
      <button type="button" @click="regeneratePrices">重新生成本房型数据</button>
    </header>
    <p class="comparison-note">模拟价格数据 · 以下两张图共用本房型的采集记录。</p>
    <div class="price-charts">
      <PriceComparison :data="priceData" />
      <PriceCandlestick :data="priceData" />
    </div>
  </article>
</template>
