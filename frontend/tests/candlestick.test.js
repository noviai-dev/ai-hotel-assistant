import assert from 'node:assert/strict'
import { test } from 'node:test'
import { buildCandles, formatMonthDay } from '../src/features/candlestick.js'
import { generatePriceComparison } from '../src/features/priceComparison.js'

test('16 daily candles span today +30 through +45 across a year boundary', () => {
  const candles = buildCandles(generatePriceComparison(new Date(2026, 11, 10)))
  assert.equal(candles.length, 16)
  candles.forEach(([timestamp], index) => {
    assert.equal(timestamp, new Date(2026, 11, 40 + index, 12).getTime())
  })
  assert.equal(formatMonthDay(candles[0][0]), '01/09')
  assert.equal(formatMonthDay(candles.at(-1)[0]), '01/24')
})

test('candles use today for both open and close and all 7 prices for high and low', () => {
  for (const random of [() => 0, () => 0.999999, Math.random]) {
    const data = generatePriceComparison(new Date(), random)
    const candles = buildCandles(data)
    candles.forEach(([, open, high, low, close], index) => {
      for (const price of [open, high, low, close]) {
        assert.ok(Number.isInteger(price) && price >= 20000 && price <= 40000)
      }
      assert.ok(low <= Math.min(open, close))
      assert.ok(high >= Math.max(open, close))
      assert.equal(open, data.collections.at(-1).series[index])
      assert.equal(close, open)
      assert.equal(high, Math.max(...data.collections.map(c => c.series[index])))
      assert.equal(low, Math.min(...data.collections.map(c => c.series[index])))
    })
  }
})
