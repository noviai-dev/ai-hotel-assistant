import assert from 'node:assert/strict'
import { test } from 'node:test'
import { buildOverview } from '../src/features/overview.js'

test('overview uses selected collection day for stay range and current time for greeting', () => {
  const overview = buildOverview(new Date(2026, 10, 11, 12), new Date(2026, 10, 12, 15))
  assert.equal(overview.start, '2026/12/11')
  assert.equal(overview.end, '2026/12/26')
  assert.equal(overview.weekendDays, 5)
  assert.equal(overview.today, '2026/11/12')
  assert.equal(overview.weekday, '星期四')
  assert.equal(overview.greeting, '下午好，欢迎回来')
  assert.ok(overview.holidayStart >= overview.start && overview.holidayEnd <= overview.end)
})

test('overview keeps the stay window and simulated holiday within range across year boundaries', () => {
  const overview = buildOverview(new Date(2026, 11, 1, 12), new Date(2026, 11, 1, 8))
  assert.equal(overview.start, '2026/12/31')
  assert.equal(overview.end, '2027/01/15')
  assert.equal(overview.holidayStart, '2027/01/05')
  assert.equal(overview.holidayEnd, '2027/01/06')
})
