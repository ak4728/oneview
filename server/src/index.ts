import express from 'express'
import cors from 'cors'
import path from 'path'
import YahooFinance from 'yahoo-finance2'
const yahooFinance = new YahooFinance()

const app = express()
app.use(cors())
app.use(express.json())
app.use(express.static(path.resolve(__dirname, '..', '..')))

app.get('/api/health', (_req, res) => {
  res.json({ status: 'ok' })
})

function periodToDateRange(period: string): { start: Date; end: Date } {
  const end = new Date()
  const start = new Date()
  const match = /^([0-9]+)([dDwWmMyY])$/.exec(period)

  if (!match) {
    start.setDate(end.getDate() - 7)
    return { start, end }
  }

  const n = parseInt(match[1], 10)
  const unit = match[2].toLowerCase()

  switch (unit) {
    case 'd':
      start.setDate(end.getDate() - n)
      break
    case 'w':
      start.setDate(end.getDate() - n * 7)
      break
    case 'm':
      start.setMonth(end.getMonth() - n)
      break
    case 'y':
      start.setFullYear(end.getFullYear() - n)
      break
    default:
      start.setDate(end.getDate() - 7)
  }

  return { start, end }
}

app.get('/api/ohlcv', async (req, res) => {
  const symbol = (req.query.symbol as string || 'BTC-USD').toUpperCase()
  const interval = (req.query.interval as string) || '5m'

  // OneView v1.4.0 — 1m data max = last 7 days on Yahoo Finance
  const period = '7d'

  try {
      // Decide between intraday (minute) and historical endpoints
      let result: any[]
      const { start, end } = periodToDateRange(period)
      const minuteInterval = /\d+m$/.test(interval)
      if (minuteInterval) {
        // Use chart endpoint for intraday data: provide explicit period1/period2
        const chartOptions = { period1: start.toISOString(), period2: end.toISOString(), interval }
        const chart = await (yahooFinance as any).chart(symbol, chartOptions)
        // yahoo-finance2 v3 chart() returns normalized rows in `quotes`
        result = Array.isArray(chart?.quotes) ? chart.quotes : []
      } else {
        // For daily/weekly/monthly data, pass explicit period1/period2 to historical
        const histOptions = { period1: start.toISOString(), period2: end.toISOString(), interval }
        result = await (yahooFinance as any).historical(symbol, histOptions)
      }

    if (!result || (Array.isArray(result) && result.length === 0)) {
      return res.status(404).json({ error: `No data found for '${symbol}'. Try: BTC-USD, AAPL, EURUSD=X` })
    }

    const records = (result as any[]).map((row) => {
      const dateObj = row.date || row.datetime || row.Datetime || row.timestamp
      const dateStr = dateObj ? new Date(dateObj).toISOString().replace('T', ' ').slice(0, 16) : ''
      return {
        date: dateStr,
        open: row.open !== undefined ? Number(Number(row.open).toFixed(4)) : null,
        high: row.high !== undefined ? Number(Number(row.high).toFixed(4)) : null,
        low: row.low !== undefined ? Number(Number(row.low).toFixed(4)) : null,
        close: row.close !== undefined ? Number(Number(row.close).toFixed(4)) : null,
        volume: row.volume !== undefined ? parseInt(String(row.volume || 0), 10) : 0,
      }
    })

    return res.json({ symbol, interval, count: records.length, data: records })
  } catch (err: any) {
    // eslint-disable-next-line no-console
    console.error(err)
    return res.status(500).json({ error: String(err?.message || err) })
  }
})

// Serve the existing index.html from the repo root
app.get('/', (_req, res) => {
  res.sendFile(path.resolve(__dirname, '..', '..', 'index.html'))
})

const port = process.env.PORT || 4000
app.listen(port, () => {
  // eslint-disable-next-line no-console
  console.log(`Server running on ${port}`)
})
