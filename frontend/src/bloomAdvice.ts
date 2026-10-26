import type { PointResponse } from './api/types'

// "Will my trees bloom on time?": compares an orchard's chill portions with what the crop needs, and turns the
// result into plain next steps. Needs are in chill portions (Dynamic Model, counted from Sep 1), from the UC chill
// requirement table compiled by UC Cooperative Extension (Pope; Doll, "Chill Portion Requirements for California
// Crops") and the UCCE walnut dormancy updates.

export type CropId = 'almond' | 'pistachio' | 'walnut' | 'prune'

export interface CropNeed {
  id: CropId
  label: string
  variety: string
  low: number // chill portions: below this, expect late and uneven bloom
  high: number // at or above this, bloom should be on time (pollinizers included)
  note: string
}

export const CROP_NEEDS: CropNeed[] = [
  { id: 'almond', label: 'Almond', variety: 'Nonpareil', low: 22, high: 32, note: 'Nonpareil needs about 23; other almond varieties up to 32.' },
  { id: 'pistachio', label: 'Pistachio', variety: 'Kerman', low: 54, high: 65, note: 'Kerman needs 54 to 58, and its Peters pollinizer 60 to 65.' },
  { id: 'walnut', label: 'Walnut', variety: 'Chandler', low: 45, high: 65, note: "UC's table says 45 to 50; farm advisors see Chandler bloom best closer to 60 to 65." },
  { id: 'prune', label: 'Prune', variety: 'Improved French', low: 55, high: 60, note: 'An estimate from how orchards did after recent winters.' },
]

export type Status = 'enough' | 'borderline' | 'short'

export interface Outlook {
  crop: CropNeed
  status: Status
  // 'past': bloom has happened, so judge the season's chill as counted. 'ahead': judge where the winter is likely to end.
  mode: 'past' | 'ahead'
  value: number // the season total (past) or the most likely end-of-season total (ahead)
  range: [number, number] | null // ahead only: the likely end-of-season range (p10 to p90)
  soFar: number
  early: boolean // ahead, and chill has barely started (Sep or Oct)
  error: number | null // typical miss of our chill portions, from validation
}

const month = (iso: string) => Number(iso.slice(5, 7))

export function bloomOutlook(data: PointResponse, crop: CropNeed): Outlook {
  const soFar = data.totals.chill_portions
  const error = data.correction.expected_error?.chill_portions ?? null
  const m = month(data.season.as_of)
  const clim = data.climatology?.chill_portions
  // Chill that counts for bloom is in by March, so from March on the season's total is as good as final.
  const ahead = !data.season.complete && (m >= 9 || m <= 2) && clim != null
  if (!ahead) {
    const margin = error ?? 0
    const status: Status = soFar - margin >= crop.high ? 'enough' : soFar + margin >= crop.low ? 'borderline' : 'short'
    return { crop, status, mode: 'past', value: soFar, range: null, soFar, early: false, error }
  }
  const status: Status = clim.p10 >= crop.high ? 'enough' : clim.p50 < crop.low ? 'short' : 'borderline'
  return { crop, status, mode: 'ahead', value: clim.p50, range: [clim.p10, clim.p90], soFar, early: m >= 9, error }
}

export function headline(o: Outlook): string {
  const crop = o.crop.label.toLowerCase()
  if (o.mode === 'past') {
    return {
      enough: `Enough chill for ${crop}: bloom should have come on time.`,
      borderline: `Just enough chill for ${crop}: bloom may have been late or uneven.`,
      short: `Not enough chill for ${crop}: bloom was likely late and uneven, with a smaller crop.`,
    }[o.status]
  }
  return {
    enough: `Your ${crop} trees should bloom on time.`,
    borderline: `This winter may be just enough for ${crop}.`,
    short: `This winter is likely to fall short for ${crop}.`,
  }[o.status]
}

export function statusLabel(o: Outlook): string {
  return o.mode === 'past'
    ? { enough: 'Enough', borderline: 'Borderline', short: 'Too little' }[o.status]
    : { enough: 'On track', borderline: 'Watch closely', short: 'At risk' }[o.status]
}

// What to ask a farm advisor about when chill runs short. Options UC researchers discuss, not prescriptions.
const TREATMENT: Record<CropId, string> = {
  pistachio:
    'Ask your farm advisor about a dormant oil spray (UC trials timed it around mid-February) or kaolin clay in winter, which keeps buds cooler. Both help bloom come on more evenly.',
  walnut:
    "Ask your farm advisor about a dormancy-breaking spray where the label allows it, about 30 to 40 days before budbreak. Don't spray oil on walnuts in full dormancy: UC IPM warns it injures the trees.",
  almond:
    'Check that your pollinizer varieties will still bloom with your main variety, and ask your beekeeper about keeping hives in a little longer.',
  prune: 'Ask your farm advisor whether a dormancy-breaking treatment makes sense for your orchard this year.',
}

const NORMAL_BLOOM: Record<CropId, string> = {
  almond: 'Line up bees as usual (UC suggests 2 to 3 hives per acre) and plan bloom sprays on normal timing.',
  pistachio: 'Kerman and its Peters pollinizer should bloom together, so plan pollination and bloom sprays as usual.',
  walnut: 'Plan blight and codling moth sprays on your usual bloom timing.',
  prune: 'Plan bees and bloom sprays on your usual timing.',
}

// `live` is the label of the season still being counted ("2026-27"), or null when that is the season shown.
export function nextSteps(o: Outlook, seasonLabel: string, live: string | null): string[] {
  const { status, mode, crop } = o
  if (mode === 'past') {
    const follow = live
      ? `switch the season to ${live} and check it weekly from November`
      : 'check back here weekly from November'
    if (status === 'enough')
      return [
        `Nothing to fix from the ${seasonLabel} winter's chill. If bloom or yield was poor, look at frost, pollination or water instead.`,
        `To follow the coming winter, ${follow}.`,
      ]
    return [
      status === 'short'
        ? `A late, uneven bloom and a lighter crop after the ${seasonLabel} winter likely trace back to low chill.`
        : `If bloom was late or uneven after the ${seasonLabel} winter, low chill is a likely reason.`,
      `For the coming winter, ${follow}. If it heads short again, act by mid-January:`,
      TREATMENT[crop.id],
      'Long term: when you replant, ask about varieties that need less chill.',
    ]
  }
  if (status === 'enough')
    return [
      'No chill action needed. Plan for a normal bloom.',
      NORMAL_BLOOM[crop.id],
      'Check back every couple of weeks until February: a long warm spell can still slow chill.',
    ]
  const steps = [
    'Check this page weekly through February. Warm spells can cancel chill that has not locked in yet.',
    `By mid-January: ${TREATMENT[crop.id].charAt(0).toLowerCase()}${TREATMENT[crop.id].slice(1)}`,
    'Plan for a longer bloom: keep bees in longer, and stretch frost and bloom-disease protection over more days.',
  ]
  if (status === 'short')
    steps.push(
      'Plan for a smaller, more uneven crop: tell your buyer or packer early and adjust labor and harvest plans.',
      'Long term: when you replant, ask about varieties that need less chill.',
    )
  return steps
}
