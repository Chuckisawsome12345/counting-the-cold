import { Area, Line, ReferenceLine } from 'recharts'
import { formatMonthDay } from '../format'
import type { Series } from '../chartData'

// The in-progress layers drawn inside the season chart card: the "Today" marker, the dotted 14-day forecast,
// and the p10 to p90 fan out to the end of the season. Rendered as children of SeasonChart's ComposedChart.
export default function ForecastChart({ series, asOf }: { series: Series; asOf: string }) {
  if (series.todayDay === null) return null
  return (
    <>
      <Area
        dataKey="band"
        stroke="none"
        fill="var(--acc2)"
        fillOpacity={0.24}
        className="fan"
        isAnimationActive={false}
        activeDot={false}
      />
      <ReferenceLine
        x={series.todayDay}
        stroke="var(--ink)"
        strokeDasharray="3 4"
        label={{ value: `Today · ${formatMonthDay(asOf)}`, position: 'top', fontSize: 11, fontWeight: 700, fill: 'var(--ink)' }}
      />
      <Line
        dataKey="fc"
        stroke="var(--acc2)"
        strokeWidth={3}
        strokeDasharray="1.5 6"
        strokeLinecap="round"
        dot={false}
        activeDot={false}
        className="fan"
        isAnimationActive={false}
      />
    </>
  )
}
