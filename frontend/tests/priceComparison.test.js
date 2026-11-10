import assert from 'node:assert/strict'
import { test } from 'node:test'
import { generatePriceComparison, comparisonTooltip, comparisonSeries, formatDate, TODAY_COLOR, HISTORY_COLOR } from '../src/features/priceComparison.js'

test('7 daily collections cover every stay date, including year boundaries', () => {
  const data = generatePriceComparison(new Date(2027, 0, 1))
  assert.equal(data.dates.length, 16)
  assert.equal(formatDate(data.dates[0]), '2027/01/31')
  assert.equal(formatDate(data.dates.at(-1)), '2027/02/15')
  assert.equal(data.collections.length, 7)
  data.collections.forEach((collection, index) => {
    assert.equal(collection.collectedAt, new Date(2027, 0, 1 - 6 + index, 12).getTime())
    // Every displayed stay date was within the daily +30..+51 collection window.
    data.dates.forEach((timestamp, day) => {
      const leadDays = 36 - index + day
      assert.ok(leadDays >= 30 && leadDays <= 51)
      const stayDate = new Date(collection.collectedAt)
      stayDate.setDate(stayDate.getDate() + leadDays)
      assert.equal(timestamp, stayDate.getTime())
    })
  })
  for (const collection of data.collections) {
    assert.equal(collection.series.length, 16)
    assert.ok(collection.series.every(price => Number.isInteger(price) && price >= 20000 && price <= 40000))
  }
})

test('only today is blue in line series; the other 6 series are gray', () => {
  const data = generatePriceComparison(new Date(2026, 10, 8))
  const lines = comparisonSeries(data)
  assert.equal(lines.length, 7)
  assert.equal(lines.filter(line => line.color === TODAY_COLOR).length, 1)
  assert.equal(lines.filter(line => line.color === HISTORY_COLOR).length, 6)
  assert.equal(lines.at(-1).color, TODAY_COLOR)
  assert.ok(lines.at(-1).name.includes('2026/11/08（当日）'))
  assert.ok(lines.every(line => line.type === 'line'))
})

test('tooltip identifies the stay date and every collection with integer prices', () => {
  const data = generatePriceComparison(new Date(2026, 10, 8))
  const tooltip = comparisonTooltip(data, 0)
  assert.ok(tooltip.includes('7 次采集'))
  assert.ok(tooltip.includes('入住日期：2026/12/08'))
  for (const collection of data.collections) {
    assert.ok(tooltip.includes(`采集日期：${formatDate(collection.collectedAt)}`))
    assert.ok(tooltip.includes(`<b>${collection.series[0]}</b>`))
  }
  assert.ok(!tooltip.includes('undefined'))
  assert.equal(comparisonTooltip(data, undefined), '')
})
