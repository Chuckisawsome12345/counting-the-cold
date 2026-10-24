import type { Metric } from '../api/types'

// The wording behind each card's "i" button, in one place so it is easy to edit. One short body per metric, in plain
// words a farmer can take in on the first read (everyday words, short sentences, no model names). No season numbers
// belong here: every number on screen comes from the API. The two reference numbers below are fixed examples, not
// season data. The only other values used are the GDD base and upper temperatures, passed in from the API response.

export interface InfoContext {
  gddBaseF?: number // settings.gdd_base_f from /api/point; absent while the first response is still loading
  gddUpperF?: number | null // settings.gdd_upper_f; null means no upper limit
}

// Source for the two chill-portion examples: FNRIC, "Chill Portions Requirements, Calculated using the Dynamic Model",
// https://innovate.ucanr.edu/node/128184 (Nonpareil almond about 22-23 portions, Chandler walnut about 45-50).
const NONPAREIL_ALMOND = '22–23'
const CHANDLER_WALNUT = '45–50'

export function metricCopy(metric: Metric, ctx: InfoContext = {}): string {
  switch (metric) {
    case 'chill_portions':
      return (
        'A score for how much winter cold your trees have soaked up since the start date. Warm spells take some of it back. ' +
        `Nonpareil almonds need about ${NONPAREIL_ALMOND}, and Chandler walnuts about ${CHANDLER_WALNUT}. ` +
        'Come in low and bloom may be late or patchy.'
      )
    case 'chill_hours':
      return (
        'A simple count of the hours between 32°F and 45°F since the start date. ' +
        "It's easy to compare with past years. " +
        "A warm afternoon doesn't take anything away, so a warm winter can look better than it was."
      )
    case 'utah_units':
      return (
        'Like chill hours, but smarter about temperature. ' +
        'Cold hours add points, mild hours add fewer, and hot hours take points away. ' +
        'Compare your total with what your trees need.'
      )
    case 'gdd': {
      const { gddBaseF, gddUpperF } = ctx
      const range =
        gddBaseF == null
          ? 'between a base and an upper limit for your crop'
          : gddUpperF == null
            ? `above ${gddBaseF}°F`
            : `between ${gddBaseF}°F and ${gddUpperF}°F`
      return (
        'A running total of heat since the start date. ' +
        `Each warm day adds points, but only temperatures ${range} count. ` +
        'A bigger total than usual means bloom, nut growth and pests arrive earlier, so plan your scouting and sprays sooner.'
      )
    }
  }
}
