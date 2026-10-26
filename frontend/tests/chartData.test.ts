import { buildChartSeries, countGaps, HOUR_MS } from '../src/utils/chartData'
import { makeMatched } from './fixtures'

describe('buildChartSeries', () => {
  it('maps real matched values one-to-one, sorted by time', () => {
    const points = buildChartSeries([makeMatched(2, 300, 330), makeMatched(0, 100, 110), makeMatched(1, 200, 190)])
    expect(points.map((p) => [p.actual, p.forecast])).toEqual([[100, 110], [200, 190], [300, 330]])
    expect(points.every((p) => !p.gap)).toBe(true)
    expect(points[1].ts - points[0].ts).toBe(HOUR_MS)
  })

  it('breaks the line at missing periods with a null marker instead of interpolating or using zero', () => {
    const points = buildChartSeries([makeMatched(0, 100, 110), makeMatched(1, 200, 190), makeMatched(5, 500, 520)])
    expect(points).toHaveLength(4)
    const gap = points[2]
    expect(gap.gap).toBe(true)
    expect(gap.actual).toBeNull()
    expect(gap.forecast).toBeNull()
    expect(gap.ts).toBe(points[1].ts + HOUR_MS)
    expect(countGaps(points)).toBe(1)
  })

  it('returns an empty series for no data', () => {
    expect(buildChartSeries([])).toEqual([])
  })

  it('ignores records with invalid timestamps', () => {
    const bad = { ...makeMatched(0, 1, 1), startTime: 'not-a-date' }
    expect(buildChartSeries([bad, makeMatched(1, 2, 2)])).toHaveLength(1)
  })
})
