# Demo script (about 2:30)

Owner: C. Fill in X and Y from `backend/data/validation.json` once it exists.

1. **0:00 Hook.** "In July 2025, CIMIS station 12 in Durham, Butte County, shut down. Every almond grower who used it lost their chill count for last winter."
2. **0:20 Drop a pin** on a Butte orchard near Durham. The 2025-26 cards appear: portions, hours, Utah, GDD. "No station, no hardware. Your orchard's chill and heat, not a station's."
3. **0:50 History chart.** This season vs the last 10 and the median. "Chill finished X% above normal."
4. **1:10 Toggle to 2026-27.** Portions have been accumulating since Sep 1. The 14-day forecast runs into November with an end-of-season range.
5. **1:30 Trust: the validation tab.** "We checked ourselves against 9 CIMIS stations. Raw gridded data was off by X portions; corrected, by Y. And Durham's decade of records still calibrates the estimate after the station closed."
6. **2:00 Microclimate.** Pin vs nearest station side by side (stretch), or move the pin and watch the numbers change.
7. **2:15 Open and free.** Show `/docs`, the open API. Close on the one-liner.

## Before judging

- [ ] Ping `/api/health` on Render 2 minutes before (cold start is about 50 s).
- [ ] `DEMO_MODE=1` ready as a fallback; demo pins prewarmed.
- [ ] Backup video recorded.
