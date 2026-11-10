<script setup>
import { computed, defineAsyncComponent, ref } from 'vue'
import { useChartVisibility } from '../composables/useChartVisibility.js'
import { hotelPriceBars } from '../features/hotelPriceBars.js'
import { formatMonthDay } from '../features/candlestick.js'
import 'vue-data-ui/style.css'

const VueUiXy = defineAsyncComponent(() => import('vue-data-ui/vue-ui-xy'))
const props = defineProps({
  hotels: { type: Array, required: true },
  prices: { type: Object, required: true },
  collectedAt: { type: Number, required: true },
  collectionLabel: { type: String, required: true },
})
const bars = computed(() => hotelPriceBars(props.hotels, props.prices, props.collectedAt))
const fixedAxis = ref(null)
const canvas = ref(null)
const visible = useChartVisibility(canvas)
// Keep one shared scale when series are hidden so the fixed axis stays accurate.
const scaleMax = computed(() => Math.max(40000, Math.ceil(Math.max(0,
  ...bars.value.dataset.flatMap(item => item.series).filter(Number.isFinite)) / 10000) * 10000))
const axisTicks = computed(() => Array.from({ length: scaleMax.value / 10000 + 1 }, (_, index) => index * 10000))
const tickY = (svg, value) => svg.drawingArea.bottom - svg.drawingArea.height * value / scaleMax.value
// Give each room a readable bar width; the viewport scrolls instead of squeezing all dates.
const chartWidth = computed(() => Math.max(1400, bars.value.dates.length * (bars.value.dataset.length * 20 + 12) + 120))
const dragging = ref(false)
let drag = null
let suppressClick = false

function startDrag(event) {
  if (event.pointerType !== 'mouse' || event.button !== 0) return
  if (event.target.closest('button, a, input, select')) return
  suppressClick = false
  drag = { id: event.pointerId, x: event.clientX, scroll: event.currentTarget.scrollLeft }
}

function moveDrag(event) {
  if (!drag || event.pointerId !== drag.id) return
  const distance = event.clientX - drag.x
  if (!dragging.value && Math.abs(distance) < 5) return
  if (!dragging.value) event.currentTarget.setPointerCapture(event.pointerId)
  dragging.value = true
  suppressClick = true
  event.preventDefault()
  event.currentTarget.scrollLeft = drag.scroll - distance
}

function endDrag(event) {
  if (!drag || event.pointerId !== drag.id) return
  drag = null
  dragging.value = false
  if (event.currentTarget.hasPointerCapture(event.pointerId)) event.currentTarget.releasePointerCapture(event.pointerId)
}

function handleClick(event) {
  if (!suppressClick) return
  suppressClick = false
  event.preventDefault()
  event.stopPropagation()
}

const config = computed(() => ({
  chart: {
    fontFamily: 'inherit',
    backgroundColor: '#fffdf9',
    color: '#5a4a3e',
    width: chartWidth.value,
    height: 480,
    padding: { top: 24, right: 24, bottom: 40, left: 0 },
    title: { show: false },
    zoom: { show: false },
    userOptions: { show: false },
    legend: { show: true, fontSize: 13 },
    grid: {
      stroke: '#e8dfd2',
      showHorizontalLines: false,
      labels: {
        fontSize: 13,
        axis: { xLabel: '', yLabel: '', fontSize: 13 },
        yAxis: {
          stacked: false, scaleMin: 0, scaleMax: scaleMax.value, useNiceScale: false,
          commonScaleSteps: 5, rounding: 0, formatter: () => '',
          showBaseline: false, showCrosshairs: false,
        },
        xAxisLabels: {
          values: bars.value.dates.map(formatMonthDay),
          fontSize: 12,
          color: '#75675c',
          rotation: 0,
          showOnlyFirstAndLast: false,
          showOnlyAtModulo: false,
          autoRotate: { enable: false },
        },
      },
    },
    tooltip: { show: true, roundingValue: 0, showPercentage: false },
  },
  bar: { periodGap: 0.025, innerGap: 0.06, borderRadius: 3, useGradient: false, labels: { show: false } },
}))
</script>

<template>
  <section class="comparison-view hotel-price-comparison" aria-labelledby="hotel-price-title">
    <header class="chart-heading">
      <div>
        <h2 id="hotel-price-title"><span class="chart-kind" aria-hidden="true">对比</span>酒店价格多柱状图</h2>
        <p>采集日期：{{ collectionLabel }} · 模拟价格数据 · 每组展示同一入住日期所有酒店、所有房型的价格</p>
      </div>
    </header>
    <p class="comparison-note">同一酒店使用同色系，深浅区分房型，所有房型同时展示。悬停查看报价，点击图例隐藏或显示对应房型；缺失报价不绘制柱子。</p>
    <div class="hotel-bars-navigation" id="hotel-bars-help">
      <span>入住日期 <span class="hotel-bars-date-format">MM/DD</span></span>
      <span>← 左右拖动查看日期 →</span>
    </div>
    <div class="hotel-bars-frame">
      <div ref="fixedAxis" class="hotel-bars-fixed-axis" role="img" aria-label="价格 Y 轴，从 0 起，每格 10000" />
      <div class="chart-scroll hotel-bars-scroll" :class="{ 'is-dragging': dragging }"
      tabindex="0" role="region" aria-label="按入住日期查看酒店房型价格" aria-describedby="hotel-bars-help"
      @pointerdown="startDrag" @pointermove="moveDrag" @pointerup="endDrag"
      @pointercancel="endDrag" @lostpointercapture="endDrag" @pointerleave="!dragging && endDrag($event)"
      @click.capture="handleClick">
      <div ref="canvas" class="chart-canvas hotel-bars-canvas" :style="{ width: `${chartWidth}px` }">
        <VueUiXy v-if="bars.dates.length && visible" :dataset="bars.dataset" :config="config">
          <template #svg-underlayer="{ svg }">
            <g aria-hidden="true" pointer-events="none">
              <line v-for="value in axisTicks" :key="value"
                :x1="svg.drawingArea.left" :x2="svg.drawingArea.right"
                :y1="tickY(svg, value)" :y2="tickY(svg, value)" stroke="#e8dfd2" stroke-width="0.5" />
            </g>
          </template>
          <template #svg="{ svg }">
            <Teleport v-if="fixedAxis" :to="fixedAxis">
              <svg width="76" :height="svg.height" :viewBox="`0 0 76 ${svg.height}`" aria-hidden="true">
                <text x="36" y="18" text-anchor="middle" fill="#75675c" font-size="12">价格</text>
                <line x1="75" x2="75" :y1="svg.drawingArea.top" :y2="svg.drawingArea.bottom" stroke="#dfd2c2" />
                <g v-for="value in axisTicks" :key="value">
                  <text x="64" :y="tickY(svg, value)" dominant-baseline="middle" text-anchor="end"
                    fill="#75675c" font-size="12">{{ value.toLocaleString('en-US') }}</text>
                  <line x1="70" x2="75" :y1="tickY(svg, value)" :y2="tickY(svg, value)" stroke="#dfd2c2" />
                </g>
              </svg>
            </Teleport>
          </template>
        </VueUiXy>
        <p v-else-if="!bars.dates.length" role="status">该采集日暂无酒店价格。</p>
      </div>
      </div>
    </div>
  </section>
</template>
