<script setup>
import PriceComparison from './PriceComparison.vue'
import PriceCandlestick from './PriceCandlestick.vue'
import { COLLECTION_COUNT } from '../features/priceComparison.js'

defineProps({
  room: { type: String, required: true },
  variant: { type: Number, default: 0 },
  data: { type: Object, default: null },
})
defineEmits(['regenerate'])
</script>

<template>
  <article class="price-module" :class="`price-module--${variant}`" :aria-label="`${room}价格模块`">
    <header class="chart-heading module-heading">
      <div>
        <h4>{{ room }} <span class="module-label">价格模块</span></h4>
        <p>采集日 +30～+45 天 · 每个入住日期 {{ COLLECTION_COUNT }} 次采集 · 价格范围 20000～40000</p>
      </div>
      <button type="button" @click="$emit('regenerate')">重新生成本房型数据</button>
    </header>
    <p class="comparison-note">模拟价格数据 · 以下两张图共用本房型的采集记录。</p>
    <div class="price-charts">
      <PriceComparison :data="data" />
      <PriceCandlestick :data="data" />
    </div>
  </article>
</template>
