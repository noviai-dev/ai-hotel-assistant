<script setup>
import { computed, defineAsyncComponent } from 'vue'
import { formatMonthDay, buildCandles, MIN_PRICE, MAX_PRICE } from '../features/candlestick.js'
import { COLLECTION_COUNT } from '../features/priceComparison.js'
import 'vue-data-ui/style.css'

const VueUiCandlestick = defineAsyncComponent(() => import('vue-data-ui/vue-ui-candlestick'))
const props = defineProps({ data: { type: Object, default: null } })
const dataset = computed(() => buildCandles(props.data))

const config = {
  type: 'candlestick',
  style: {
    fontFamily: 'inherit',
    backgroundColor: '#ffffff',
    color: '#334155',
    width: 1000,
    height: 460,
    layout: {
      padding: { top: 24, right: 24, bottom: 48, left: 80 },
      candle: {
        colors: { bullish: '#2563eb', bearish: '#2563eb' },
        gradient: { show: false },
        widthRatio: 0.55,
      },
      wick: { stroke: '#64748b', strokeWidth: 1.5 },
      grid: {
        stroke: '#e2e8f0',
        horizontalLines: { show: true, stroke: '#e2e8f0' },
        xAxis: {
          dataLabels: {
            fontSize: 14,
            showOnlyFirstAndLast: false,
            showOnlyAtModulo: false,
            autoRotate: { enable: false },
            datetimeFormatter: {
              enable: true,
              useUTC: false,
              januaryAsYear: false,
              options: { year: 'MM/dd', month: 'MM/dd', day: 'MM/dd' },
            },
          },
        },
        yAxis: {
          scale: { min: MIN_PRICE, max: MAX_PRICE },
          dataLabels: { roundingValue: 0, steps: 5, fontSize: 14 },
        },
      },
    },
    title: { show: false },
    zoom: { show: false },
    tooltip: {
      roundingValue: 0,
      showChart: false,
      useDefaultTimeFormat: false,
      timeFormat: 'yyyy/MM/dd',
    },
  },
  // The tooltip uses `close`, while the data table uses `last`.
  translations: { period: '日期', open: '开盘', high: '最高', low: '最低', close: '收盘', last: '收盘', volume: '成交量' },
  userOptions: { show: false },
}
</script>

<template>
  <section class="comparison-view" aria-label="价格 K 线图">
    <header class="chart-heading">
      <div>
        <h4>价格 K 线图</h4>
        <p>开盘价 = 收盘价 = 今日采集价 · 最高 / 最低 = {{ COLLECTION_COUNT }} 次采集极值</p>
      </div>
    </header>
    <div class="chart-meta">
      <span v-if="dataset.length">{{ formatMonthDay(dataset[0][0]) }} — {{ formatMonthDay(dataset.at(-1)[0]) }}</span>
      <span>价格范围：20000～40000（整数）</span>
      <span>蓝色横线：今日采集价 · 灰色竖线：{{ COLLECTION_COUNT }} 次采集价格范围</span>
    </div>
    <div class="chart-scroll">
      <div class="chart-canvas">
        <VueUiCandlestick v-if="dataset.length" :dataset="dataset" :config="config">
          <template #svg="{ svg }">
            <!-- Equal open/close has zero body height; mark today's price explicitly. -->
            <g aria-hidden="true" pointer-events="none">
              <line v-for="(point, index) in svg.data" :key="index"
                :x1="point.open.x - 10" :x2="point.open.x + 10"
                :y1="point.open.y" :y2="point.open.y"
                stroke="#2563eb" stroke-width="3" stroke-linecap="round" />
            </g>
          </template>
        </VueUiCandlestick>
        <p v-else role="status">正在生成 K 线数据…</p>
      </div>
    </div>
  </section>
</template>
