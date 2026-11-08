export const MIN_PRICE = 20000
export const MAX_PRICE = 40000

export function buildCandles(data) {
  if (!data?.collections.length) return []
  const today = data.collections.find(collection => collection.isToday)
  return data.dates.map((timestamp, index) => {
    const prices = data.collections.map(collection => collection.series[index])
    const price = today.series[index]
    // Vue Data UI: [timestamp, open, high, low, close, volume].
    return [timestamp, price, Math.max(...prices), Math.min(...prices), price, 0]
  })
}

export function formatMonthDay(timestamp) {
  const date = new Date(timestamp)
  return `${String(date.getMonth() + 1).padStart(2, '0')}/${String(date.getDate()).padStart(2, '0')}`
}
