import type { Metric } from '../api/types'

// The wording behind each card's "i" button, in one place so it is easy to edit. Written for a grower, not a scientist.
// No season numbers and no variety thresholds belong here: requirements depend on the variety and the region, and every
// number on screen comes from the API. The only values used are the GDD base and upper temperatures, passed in.

export interface InfoCopy {
  what: string // what the number is
  why: string // why it matters for the crop
  how: string // how to read it
}

export interface InfoContext {
  gddBaseF?: number // settings.gdd_base_f from /api/point; absent while the first response is still loading
  gddUpperF?: number | null // settings.gdd_upper_f; null means no upper limit
}

const VARIETY_NOTE = "Requirements vary by variety, so compare it against your variety's requirement."

export function metricCopy(metric: Metric, ctx: InfoContext = {}): InfoCopy {
  switch (metric) {
    case 'chill_portions':
      return {
        what: 'A measure of winter cold, built on the Dynamic Model. It adds up cold exposure hour by hour, and lets warm spells partly undo what was already gained.',
        why: 'Trees need enough accumulated winter chill to break dormancy. Too little can mean delayed, uneven or weak bloom and a lower yield. This is the model most often used for California nut crops.',
        how: `Higher means more chill banked, counted in portions from the start date in the settings. ${VARIETY_NOTE}`,
      }
    case 'chill_hours':
      return {
        what: 'The simplest count: the number of hours spent in a set cold range, commonly 32 to 45°F, counted from the start date in the settings through the end of February.',
        why: 'Same job as chill portions: too few cold hours can mean poor or uneven bloom. It is easy to compare with older charts, but it ignores warm spells that interrupt the chill.',
        how: `Higher means more cold hours so far, counted in hours (h). ${VARIETY_NOTE}`,
      }
    case 'utah_units':
      return {
        what: 'A weighted version of chill hours. Hours in the best cold range count fully, cooler or warmer hours count less, and very warm hours subtract from the total.',
        why: 'Because warm hours take chill away, it captures warm-spell damage better than plain chill hours. Too little accumulated chill can still mean delayed, uneven or weak bloom.',
        how: `Higher means more usable chill, counted in chill units (CU) from the start date in the settings through the end of February. ${VARIETY_NOTE}`,
      }
    case 'gdd': {
      const { gddBaseF, gddUpperF } = ctx
      const temps =
        gddBaseF == null
          ? 'above a base temperature, with heat above an upper limit left out for some crops. The temperatures come from the selected crop.'
          : gddUpperF == null
            ? `above a base of ${gddBaseF}°F, with no upper limit for this crop.`
            : `above a base of ${gddBaseF}°F, with heat above ${gddUpperF}°F left out.`
      return {
        what: `Heat added up over the season. Each day counts how far the temperature rises ${temps}`,
        why: 'Growers use it to predict the timing of bloom, nut development, hull split and pest generations, so it helps plan scouting, spraying and harvest.',
        how: 'Higher means more heat so far, counted in degree-days (°F-days) from the start date in the settings. Compare it with the same date in other seasons to see whether the season is running early or late.',
      }
    }
  }
}
