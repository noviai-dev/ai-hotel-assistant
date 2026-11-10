<script setup>
import { computed, defineAsyncComponent, ref } from 'vue'
import { useChartVisibility } from '../composables/useChartVisibility.js'
import { comparisonTooltip, comparisonSeries, COLLECTION_COUNT } from '../features/priceComparison.js'
import { formatMonthDay } from '../features/candlestick.js'
import 'vue-data-ui/style.css'

const VueUiXy = defineAsyncComponent(() => import('vue-data-ui/vue-ui-xy'))
const props = defineProps({ data: { type: Object, default: null } })
const canvas = ref(null)
const visible = useChartVisibility(canvas)
const dataset = computed(() => comparisonSeries(props.data))
const config = computed(() => ({
  chart: {
    fontFamily: 'inherit',
    backgroundColor: '#fffdf9',
    color: '#5a4a3e',
    width: 1000,
    height: 440,
    padding: { top: 24, right: 24, bottom: 40, left: 16 },
    title: { show: false },
    zoom: { show: false },
    userOptions: { show: false },
    legend: { show: true, fontSize: 13 },
    grid: {
      stroke: '#e8dfd2',
      showHorizontalLines: true,
      labels: {
        fontSize: 13,
        axis: { xLabel: '入住日期（MM/DD）', yLabel: '价格', fontSize: 13 },
        yAxis: {
          scaleMin: 20000,
          scaleMax: 40000,
          useNiceScale: false,
          commonScaleSteps: 5,
          rounding: 0,
        },
        xAxisLabels: {
          values: props.data?.dates.map(formatMonthDay) ?? [],
          fontSize: 13,
          showOnlyFirstAndLast: false,
          showOnlyAtModulo: false,
          autoRotate: { enable: false },
        },
      },
    },
    tooltip: {
      show: true,
      roundingValue: 0,
      showPercentage: false,
      customFormat: ({ absoluteIndex, seriesIndex }) => comparisonTooltip(props.data, absoluteIndex ?? seriesIndex),
    },
  },
  line: { radius: 4, strokeWidth: 2, useGradient: false, labels: { show: false } },
}))
</script>

<template>
  <section class="comparison-view comparison-view--trend" aria-label="价格折线图">
      <h5><span class="chart-kind" aria-hidden="true">趋势</span>价格折线图</h5>
      <p class="comparison-note">当日采集为蓝色，其他 {{ COLLECTION_COUNT - 1 }} 次采集为灰色。悬停查看价格；点击图例隐藏或显示批次。</p>
      <div class="chart-scroll">
        <div ref="canvas" class="chart-canvas">
          <VueUiXy v-if="data && visible" :dataset="dataset" :config="config" />
          <p v-else-if="!data" role="status">正在生成对比数据…</p>
        </div>
      </div>
  </section>
</template>
