# Demo script (about 2:30)

Owner: C. This is the working copy; the pitch essentials come from `docs/BUILD_PLAN.md`. **Every number you say comes off the screen or from `validation.json`. Never say a number you have not just read.** X, Y and Z below are placeholders for exactly that.

## What the demo depends on

The script only works if these have landed. Check each one before rehearsing; if one is missing, use the fallback in that beat or cut it.

| Needs | Issue | If it's missing |
|---|---|---|
| Real temperatures, not mock data (the "SYNTHETIC MOCK DATA" badge in the header must be **gone**) | #4 | Don't demo. Say it's the mock, or wait for the pipeline. |
| Dynamic Model chill portions with golden tests | #13, #16 | Skip the "same models as FNRIC" line. |
| 10-season history and the 14-day forecast | #7, #20 | Beats 3 and 4 lose their lines; show cards only. |
| Bias correction wired in | #8, #18 | The accuracy beat has nothing real behind it; skip the bias toggle too. |
| `validation.json` built | #19 | The accuracy tab says "hasn't been built yet". Skip beat 5. |
| `backend/data/grid/2025.json` built (`scripts/build_grid.py`) | A | The Chill layer chip says "hasn't been built yet". Skip beat 6. |
| Backend and frontend both on Vercel, with Vercel's login wall off (the backend moved off Render) | #5, #24 | Run locally (see "Before judging"). |
| Offline mode checked on the demo phone (Add to Home Screen, then airplane mode) | #54 | Skip beat 7, or show it on the laptop with the network off. |

## Pitch essentials (say these, in this order)

- **Opening stat:** "Durham's station ran for 43 years, from 1982 until it shut down on July 30, 2025." (from the CIMIS station list)
- **Official standards:** "Same models FNRIC uses: chill portions, chill hours, Utah, and UC IPM degree days." Say "checked against FNRIC's published numbers" **only** if B confirms the golden tests (#16) pass.
- **Closing stat:** "Corrected, we land within Y chill portions of a real station." Y is the corrected number on the accuracy tab. Never a guess.
- **Adoption:** "We don't replace CIMIS. We fill its gaps, and FNRIC can embed it with our open API."

## The script

Use the **light** theme (it projects better) at normal browser zoom. Start on the Orchard tab with the Butte pin selected and the season on 2025-26.

1. **0:00 Hook.** Nothing to click. The map shows Durham as a hollow dashed ring with the badge "Durham #12 closed Jul 30 2025". *"Durham's weather station in Butte County ran for 43 years. On July 30, 2025 it shut down, and every almond grower who used it lost their chill count for last winter."*
2. **0:20 Drop a pin.** Click the **Butte orchard near Durham** chip: the map flies in and the four cards count up. *"No station, no hardware. Your orchard's chill and heat, not a station's. Same models FNRIC uses."* Point at "Nearest station … km" in the pin card (read the real number).
3. **0:45 History.** Scroll to the season chart on **Chill Portions**. Past seasons are the faint lines, the dashed line is the median, the bold line is this orchard. *"Chill finished X% above (or below) normal."* X is the percent on the Chill Portions card, and the arrow says which way.
4. **1:05 Toggle to 2026-27 live.** Click **2026-27 live**. Cards show "None yet" until chill starts counting; the chart shows the "Today" marker, the dotted 14-day forecast and the shaded p10 to p90 range. *"This season is still counting. Here's the next two weeks, and where the season is likely to land."* Say the p50 and range from the chart label. Switch the chart tab to **GDD** if you want to show it turns to the heat colours and starts Jan 1.
5. **1:25 Trust: the accuracy map.** Click **How accurate is this?** The map opens on the raw errors (big amber bubbles). Click **Play**: the bubbles shrink and turn blue while the headline counts down. *"We checked ourselves against 9 CIMIS stations. Raw gridded data was off by X; corrected, by Y, which is Z% smaller."* Read X, Y and Z from the headline card. Point at the dashed **Durham #12 · closed** bubble and the callout: *"And Durham's decade of records still calibrates the estimate after the station closed."* If the tab says "hasn't been built yet", skip this beat and say so honestly.
6. **1:55 The whole valley.** Back on Orchard, click **Show all stations**, then the **Chill layer** chip: the Central Valley colours in. *"Every orchard, not nine stations."* Read the range from the legend. Skip if the chip says "hasn't been built yet".
7. **2:05 No signal, no problem.** Hold up the phone that already has the app installed and the Butte orchard loaded. Turn on airplane mode, close the app and reopen it: the orchard is there with "You're offline. Showing the saved numbers, as of [date]." *"Most orchards don't have signal. It still works."* Skip if the phone check (#54) wasn't done.
8. **2:20 Open and free.** Open the API docs at `/docs` and `/api/v1/models`. *"We don't replace CIMIS. We fill its gaps, and FNRIC can embed this today through our open API."* Close on the one-liner: **"Your orchard's chill and heat, not a station's."**

### If you have spare seconds (or a judge asks)

- Flip **Bias-corrected** off and on and watch the numbers move; point at the Correction card ("Corrected using Durham (historical) ..."). *"Every pin is calibrated with the stations around it."*
- Click **Davis** or **Parlier** to show a different orchard getting its own numbers.
- Show the phone-width layout and the locate button.

### Not built (leave out of the pitch)

- Text-message access (#56) and alerts (#57), the machine-learning comparison (#39), the variety-readiness ring, hull split and the pin-vs-station comparison.

## Before judging

- [ ] Ping `/api/health` on the deployed backend 2 minutes before, so the first click is not a cold start (the cache lives in `/tmp` there and resets on cold starts; the committed snapshots cover the demo pins).
- [ ] No "SYNTHETIC MOCK DATA" badge in the header on the live URL.
- [ ] Click through both seasons, all four chart tabs, the accuracy tab with **Play**, the Chill layer chip and the bias toggle once on the live URL.
- [ ] Demo phone: on Wi-Fi, open the live site, **Add to Home Screen**, open it from the icon, load the Butte orchard and wait for the numbers. Then try airplane mode once.
- [ ] `DEMO_MODE=1` ready as a fallback; the three demo pins (Butte, Davis, Parlier) are prewarmed. In demo mode any other spot shows "this spot isn't preloaded", so stay on the demo chips.
- [ ] Wi-Fi fallback: laptop running `uvicorn app.main:app` (backend, with `DEMO_MODE=1`) and `npm run build && npm run preview` (frontend), both tried at least once before the day.
- [ ] Light theme, browser zoom 100%, notifications off, one clean browser window.
- [ ] Backup video recorded and saved somewhere offline (laptop and phone).
- [ ] Rehearsed 3 times, under 2:30 each time. Time each beat; cut beat 6 first if long, then beat 7.

## Devpost text (draft: fill the blanks from the live numbers)

**Tagline:** Your orchard's chill and heat, not a station's.

**Inspiration.** CIMIS station 12 in Durham, Butte County, ran for 43 years and shut down on July 30, 2025. Almond growers who relied on it lost their chill count. Many orchards are far from any station, or in a different microclimate.

**What it does.** Drop a pin on any California orchard and see chill portions, chill hours, Utah units and growing degree days for the season so far, compared with the last 10 seasons, plus a 14-day projection. Estimates come from gridded weather data (Open-Meteo), bias-corrected with CIMIS stations, including closed ones. A second tab shows how accurate it is, as a map where each station's error bubble shrinks from raw (X) to corrected (Y) across 9 stations. A chill layer colours the Central Valley, and the app keeps the last orchard on the phone so it opens with no signal.

**How we built it.** FastAPI, React, Leaflet and Recharts. The chill and degree-day math is pure Python with tests; the correction is a month-by-hour offset table per station, blended by distance. [Add: validation method once B confirms.]

**Challenges.** The CIMIS API was unreliable during the event, so the app never calls it live: station data is pulled ahead of time and committed.

**What's next.** [Fill in from what shipped; text-message access and alerts were not built.] An open API (`/api/v1/models`) lets FNRIC or extension advisors show "estimate for your exact orchard" next to station tables.

## Slides (outline, 5 slides)

1. The problem: Durham closed, a grower loses the chill count (map with the closed station).
2. The product: one pin, four numbers, history and projection (screenshot of the Orchard tab).
3. The proof: raw vs corrected error, Durham highlighted (screenshot of the accuracy map and headline, real numbers).
4. How it works: Open-Meteo, bias tables from CIMIS, same models as FNRIC (one diagram).
5. Adoption: fills CIMIS's gaps, open API for FNRIC and extension (the `/api/v1/models` snippet).
