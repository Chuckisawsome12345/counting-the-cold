import type { Metric } from '../api/types'

// The wording behind each card's "i" button, in one place so it is easy to edit. One short body per metric, written
// for a farmer: what is counted, how to use it, and at most one limitation. No season numbers belong here (every
// number on screen comes from the API). The two reference numbers below are fixed examples, not season data. The only
// other values used are the GDD base and upper temperatures, which are passed in from the API response.

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
        'Winter cold your trees have banked since the start date, with credit lost when warm spells hit. ' +
        `Compare it with your variety's need: Nonpareil almond is about ${NONPAREIL_ALMOND} portions, Chandler walnut about ${CHANDLER_WALNUT}. ` +
        'Falling short means expect late or uneven bloom.'
      )
    case 'chill_hours':
      return (
        'Hours between 32 and 45°F, counted from the start date through February. ' +
        "It's the simple count older charts use, so it's easy to compare year to year. " +
        "Warm afternoons don't take anything away, so a warm winter can look better than it was."
      )
    case 'utah_units':
      return (
        'A weighted cold count since the start date: hours at the best cold temperatures count in full, cooler or warmer hours count less, and warm hours take credit away. ' +
        "It shows warm-winter setbacks better than chill hours, so compare it with your variety's Utah requirement."
      )
    case 'gdd': {
      const { gddBaseF, gddUpperF } = ctx
      const range =
        gddBaseF == null
          ? 'between a base and an upper limit set for your crop'
          : gddUpperF == null
            ? `above ${gddBaseF}°F`
            : `between ${gddBaseF}°F and ${gddUpperF}°F`
      return (
        `Heat added up since the start date, counting only temperatures ${range}. ` +
        'Ahead of normal means bloom, nut development and pest generations arrive sooner, so plan scouting and sprays earlier.'
      )
    }
  }
}
