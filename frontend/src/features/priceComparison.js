export const COLLECTION_COUNT = 7
export const TODAY_COLOR = '#2563eb'
export const HISTORY_COLOR = '#94a3b8'

export function formatDate(timestamp) {
  const date = new Date(timestamp)
  return [date.getFullYear(), date.getMonth() + 1, date.getDate()]
    .map((part, index) => String(part).padStart(index === 0 ? 4 : 2, '0')).join('/')
}

export function generatePriceComparison(today = new Date(), random = Math.random) {
  let baselinePrice = 30000
  const baseline = Array.from({ length: 16 }, (_, index) => {
    baselinePrice = Math.max(22500, Math.min(37500, baselinePrice + Math.floor(random() * 5001) - 2500))
    return [new Date(today.getFullYear(), today.getMonth(), today.getDate() + 30 + index, 12).getTime(), baselinePrice]
  })
  return {
    dates: baseline.map(([timestamp]) => timestamp),
    collections: Array.from({ length: COLLECTION_COUNT }, (_, index) => {
      const collectedAt = new Date(today.getFullYear(), today.getMonth(), today.getDate() - (COLLECTION_COUNT - 1) + index, 12).getTime()
      return {
        collectedAt,
        name: `${formatDate(collectedAt)}`,
        isToday: index === COLLECTION_COUNT - 1,
        series: baseline.map(([, price]) => Math.max(20000, Math.min(40000,
          price + Math.floor(random() * 5001) - 2500))),
      }
    }),
  }
}

export function comparisonSeries(data) {
  return data?.collections.map(collection => ({
    name: collection.name + (collection.isToday ? '（今日）' : ''),
    color: collection.isToday ? TODAY_COLOR : HISTORY_COLOR,
    series: collection.series,
    type: 'line',
    shape: 'circle',
    smooth: false,
    useArea: false,
    dataLabels: false,
  })) ?? []
}

export function comparisonTooltip(data, index) {
  if (!Number.isInteger(index) || !data?.dates[index]) return ''
  return `<div class="comparison-tooltip"><strong>入住日期：${formatDate(data.dates[index])}</strong><div>${data.collections.length} 次采集 · 价格（整数）</div><div class="comparison-tooltip-records">${[...data.collections].reverse().map(collection =>
    `<div style="color:${collection.isToday ? TODAY_COLOR : HISTORY_COLOR}">采集日期：${formatDate(collection.collectedAt)}${collection.isToday ? '（今日）' : ''} · 价格：<b>${collection.series[index]}</b></div>`
  ).join('')}</div></div>`
}
