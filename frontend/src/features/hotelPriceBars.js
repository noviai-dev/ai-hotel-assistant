import { formatDate } from './priceComparison.js'

// Each hotel has a muted color family; shades distinguish its room types.
const HOTEL_COLORS = [
  ['#8a5a44', '#c09276', '#dbc0aa'],
  ['#66765b', '#9aaa89', '#c2cbb5'],
  ['#b08a46', '#d1b478', '#e4d1aa'],
  ['#627d86', '#97b0b7', '#c0d0d4'],
]

// Align by stay date, and select only the requested collection day.
export function hotelPriceBars(hotels, prices, collectedAt) {
  const selectedDay = formatDate(collectedAt)
  const collections = hotels.flatMap((hotel, hotelIndex) => hotel.rooms.map((room, roomIndex) => {
    const data = prices[hotel.id]?.[room]
    const collection = data?.collections.find(item => formatDate(item.collectedAt) === selectedDay)
    return { hotel, room, hotelIndex, roomIndex, data, collection }
  }))
  const dates = [...new Set(collections.flatMap(({ data }) => data?.dates ?? []))].sort((a, b) => a - b)
  return {
    dates,
    dataset: collections.map(({ hotel, room, hotelIndex, roomIndex, data, collection }) => {
      const byDate = new Map(data?.dates.map((date, i) => [date, collection?.series[i]]) ?? [])
      return {
        name: `${hotel.name} · ${room}`,
        color: HOTEL_COLORS[hotelIndex % HOTEL_COLORS.length][roomIndex % HOTEL_COLORS[0].length],
        type: 'bar',
        series: dates.map(date => byDate.get(date) ?? null),
        dataLabels: false,
      }
    }),
  }
}
