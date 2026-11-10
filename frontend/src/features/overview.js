import { formatDate } from './priceComparison.js'

export function buildOverview(collectedAt, now = new Date()) {
  const offsetDate = offset => {
    const date = new Date(collectedAt)
    date.setDate(date.getDate() + offset)
    return date
  }
  const stayDates = Array.from({ length: 16 }, (_, index) => offsetDate(30 + index))
  const hour = now.getHours()
  return {
    greeting: hour < 6 ? '夜深了，辛苦了' : hour < 12 ? '上午好，欢迎回来' : hour < 18 ? '下午好，欢迎回来' : '晚上好，欢迎回来',
    today: formatDate(now),
    weekday: `星期${'日一二三四五六'[now.getDay()]}`,
    start: formatDate(stayDates[0]),
    end: formatDate(stayDates.at(-1)),
    weekendDays: stayDates.filter(date => [0, 6].includes(date.getDay())).length,
    // Synthetic dates for the greeting demo, not a public holiday calendar.
    holidayStart: formatDate(offsetDate(35)),
    holidayEnd: formatDate(offsetDate(36)),
  }
}
