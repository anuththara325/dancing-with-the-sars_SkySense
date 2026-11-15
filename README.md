# Dancing with the SARs

Interactive web app for the NASA Space Apps Challenge Colombo 2026 ("Dancing with the SARs").
It shows surface change seen by NASA-ISRO NISAR L-band radar (provisional GCOV, CRID P05023), with Sentinel-1, Sentinel-2 and rainfall for context, at seven places plus one validation test in three places (Rain test: Nawalapitiya at `#/moisture`, Ampara at `#/moisture/ampara`, Ratnapura at `#/moisture/ratnapura`):
Thailand (flood), Assam India (flood), Devighat Nepal (surge and landslide), Matara, Minneriya, Senanayake Samudraya and Colombo Port (Sri Lanka).

## Rain test (three places)
Page `#/moisture` has three place tabs: Nawalapitiya, Ampara (`#/moisture/ampara`) and Ratnapura (`#/moisture/ratnapura`).

**Nawalapitiya.** (Updated 15 Nov: new white-background green and HH images, daily AMSR2 soil moisture, IMERG Late rain; validated dates carry the forest-measured offset.) Page `#/moisture` ("Rain test" in the top bar, and a card on the home page). 19 NISAR passes over Nawalapitiya (Central Province, 80.45-80.62E, 6.90-7.10N): a time-lapse of the green (HV-dominated) pixels with a graph of green intensity and daily rain, a forest vs open-land comparison, and the provisional-to-validated correction. Data: `data_moisture.js`; images: `img/nw_a_*` (morning, ascending) and `img/nw_d_*` (evening, descending).jpg` and it appears beside the time-lapse (credit shown in the caption).

**Ampara** (81.45-81.70E, 7.10-7.35N, dry zone). 19 passes: 10 morning (ascending) and 9 evening (descending, track 120, 4 of them quad-pol). Same time-lapse and green-intensity-vs-rain graph, plus a second check of evening-pass HH (fixed set of 575,000 red pixels) against AMSR2 soil moisture. The result is weaker than at Nawalapitiya (morning r = 0.61, evening r = 0.63) and the page says so. Data: `data_ampara.js`; images: `img/am_a_*`, `img/am_d_*`, `img/am_ha_*` and `img/am_hd_*` (HH red-pixel pictures, time-lapse).

**Ratnapura** (80.28-80.55E, 6.60-6.80N, south-west wet zone). 20 passes: 10 morning (ascending, track 084) and 10 evening (descending, track 048, 4 of them quad-pol). Same method as Ampara: green intensity vs rain in the previous 7 days (morning r = 0.78, p = 0.008; evening r = 0.74, p = 0.014; evening dual-pol only r = 0.84 on 6 dates) and HH of the red pixels vs AMSR2 soil moisture (evening r = 0.71, morning r = 0.65, p = 0.057). Validated products (from 21 Oct) are left out because the provisional-to-validated step was not measured here. Data: `data_ratnapura.js`; images: `img/rn_a_*`, `img/rn_d_*`, `img/rn_ha_*`, `img/rn_hd_*`.
This page also uses NISAR VALIDATED data (CRID P05036, from 21 Oct 2026), corrected with a forest-measured offset; all other stories use provisional data only.

## Run it
No install is needed.
- Double-click `index.html`, or
- `python3 -m http.server` in this folder, then open http://localhost:8000


## Host it on GitHub Pages
Upload this folder to a public repository, then Settings > Pages > Deploy from branch (main, root).

## Colours
NISAR images use the NASA SVS 5661 false-colour recipe: R = HH, G = HV, B = HH minus HV (dB). Sentinel-1 uses the same logic with VV/VH (C-band; never compare dB for dB with NISAR).

## Data and credits
- NISAR L2 GCOV provisional, NASA-ISRO, via ASF DAAC. False-colour recipe: NASA SVS 5661.
- Contains modified Copernicus Sentinel data (2026): Sentinel-1 (OPERA RTC-S1, ASF) and Sentinel-2 L2A (AWS Earth Search).
- Rain: NASA POWER (MERRA-2 model, about 50 km, not a gauge). Rain test page: NASA GPM IMERG Late daily (GPM_3IMERGDL v07) at Nawalapitiya Early daily (GPM_3IMERGDE v07) at Ampara and Late daily at Ratnapura, about 10 km, via GES DISC Giovanni; AMSR2 LPRM 6.9 GHz soil moisture at Ampara. Forest mask: ESA WorldCover 2021 v200 (CC BY 4.0).
- Thailand context: NASA Earth Observatory, 9 Oct 2026.

## AI disclosure
Analysis scripts, this web app and draft text were created with assistance from Claude (Anthropic). Check data and conclusions before reuse.

## Final wording (15 Nov 2026)
Senanayake now carries an Irrigation Department storage comparison (% of active storage, ten NISAR dates, r = 0.84, direction of change only). Minneriya, Matara, Colombo Port, Thailand, Assam and Devighat carry dated independent sources, shown as context for the event and not as validation of our measured areas. Reservoir storage series are compiled by Macro Lab from Irrigation Department data and are not an official publication.

## Limits
All NISAR data are provisional and may change on reprocessing. "Dark" radar areas are smooth surfaces and are not always flood water. Wording such as "consistent with" is deliberate.

## Team
Team SkySense: Anuththara Divyanjalie, Muditha Kumara, Mayumi Maleesha

## Story page layout (15 Nov update)
Each story now shows the images first, then tabs: Key takeaway, What we see, Data used, Limits, Why it may happen, Where is this? Each page also has "See this place on Google Maps" and "Satellite view" buttons (centre of the study box). The map embed loads only when clicked.

## Other pages

- `#/radar`: "New to radar?", a plain-words guide to radar, bands, polarizations and how to read a story.
- `#/polar`: Polarizations page, including a Radar Vegetation Index (RVI = 4·HV/(HH+HV), linear power) panel for Nawalapitiya, Ampara and Ratnapura. It is a relative vegetation density, not biomass.
- Home page: a "Why this matters" block with a role picker (possible uses, not existing services).
