import assert from 'node:assert/strict'
import { test } from 'node:test'
import { hotelPriceBars } from '../src/features/hotelPriceBars.js'
import { generatePriceComparison } from '../src/features/priceComparison.js'

test('hotel bars include every hotel room for the selected collection, aligning prices by stay date', () => {
  const day = new Date(2026, 10, 11, 12).getTime()
  const hotels = [{ id: 'self', name: 'NOVI', rooms: ['A', 'B'] }, { id: 'other', name: '住一', rooms: ['A'] }]
  const prices = {
    self: { A: { dates: [2, 1], collections: [
      { collectedAt: day - 86400000, series: [900, 800] },
      { collectedAt: day, series: [200, 100] },
    ] }, B: { dates: [1], collections: [{ collectedAt: day, series: [999] }] } },
    other: { A: { dates: [1, 3], collections: [{ collectedAt: day, series: [300, 400] }] } },
  }
  const { dates, dataset } = hotelPriceBars(hotels, prices, day)
  assert.deepEqual(dates, [1, 2, 3])
  assert.deepEqual(dataset.map(item => item.series), [[100, 200, null], [999, null, null], [300, null, 400]])
  assert.deepEqual(dataset.map(item => item.name), ['NOVI · A', 'NOVI · B', '住一 · A'])
  assert.ok(dataset.every(item => item.type === 'bar'))
  assert.notEqual(dataset[0].color, dataset[1].color)
  assert.deepEqual(hotelPriceBars(hotels, { self: { A: prices.self.A } }, day).dataset[1].series, [null, null])
  assert.ok(hotelPriceBars(hotels, prices, day + 86400000).dataset.every(item => item.series.every(price => price === null)))
})

test('generated hotel bars match the current collection and reflect replacement data', () => {
  const day = new Date(2026, 11, 31, 12)
  const hotels = [{ id: 'self', name: 'NOVI', rooms: ['A'] }]
  const prices = { self: { A: generatePriceComparison(day, () => 0.5) } }
  const first = hotelPriceBars(hotels, prices, day.getTime())
  assert.equal(first.dates.length, 16)
  assert.deepEqual(first.dataset[0].series, prices.self.A.collections.at(-1).series)
  prices.self.A = generatePriceComparison(day, () => 0)
  const refreshed = hotelPriceBars(hotels, prices, day.getTime())
  assert.deepEqual(refreshed.dataset[0].series, prices.self.A.collections.at(-1).series)
  assert.notDeepEqual(refreshed.dataset[0].series, first.dataset[0].series)
  assert.deepEqual(hotelPriceBars(hotels, {}, day.getTime()).dates, [])
})
