# Dancing with the SARs

**Team SkySense** · NASA Space Apps Challenge, Colombo 2026 · Challenge: *Dancing with the SARs*

**Live app:** https://anuththara325.github.io/dancing-with-the-sars_SkySense/

An interactive web app that shows how the land surface changed in 2026, as seen by the NASA-ISRO **NISAR** L-band radar. Radar sees through cloud and works day or night, so it can show floods, landslides and reservoir changes while they are happening. We use it to tell stories at seven places, and we test whether the radar colours follow real rain at three places in Sri Lanka.

## What you will find

**Seven stories** (each with images, a short takeaway, the data used, limits, and a map of where it is):

| Place | What we look at |
|---|---|
| Thailand | Flood |
| Assam, India | Flood |
| Devighat, Nepal | Surge and landslide |
| Matara, Sri Lanka | Coastal change |
| Minneriya, Sri Lanka | Reservoir and surrounding land |
| Senanayake Samudraya, Sri Lanka | Reservoir water level |
| Colombo Port, Sri Lanka | Port and built-up land |

**Other pages**
- **New to radar?** A plain-words guide to radar, bands, polarizations, and how to read a story.
- **Polarizations.** What HH and HV show, plus a Radar Vegetation Index (RVI) panel for the three Rain test places.
- **Rain test.** Does the radar colour follow real rain? Three places: Nawalapitiya, Ampara and Ratnapura.
- **Why this matters.** On the home page: who could use this kind of information (possible uses, not existing services).

## How to read the colours

NISAR images use the NASA SVS 5661 false-colour recipe: **Red = HH, Green = HV, Blue = HH − HV** (in dB).
Sentinel-1 images use the same idea with VV and VH. Sentinel-1 is C-band and NISAR is L-band, so we never compare their dB values directly.

## Rain test, in short

We compared radar signals with independent rain and soil-moisture data at three places, using NISAR passes from June to October 2026.

| Place | Zone | What we found |
|---|---|---|
| Nawalapitiya | Central hills | Green (HV) intensity follows the previous week's rain (r = 0.73 morning, 0.60 evening) |
| Ampara | Dry zone | Weaker but same direction (r = 0.61 morning, 0.63 evening). We say so on the page. |
| Ratnapura | South-west wet zone | Green intensity follows rain (r = 0.78 morning, 0.74 evening) |

The RVI panel shows relative vegetation density (RVI = 4·HV / (HH + HV), linear power). It is **not biomass**. At Ampara the river-valley blocks rise from July to late August, which is consistent with crop growth in cultivated land; we do not identify crop type, planting or harvest dates.

## Run it

- **Online:** open the live link above.
- **On your computer:** download this repository, extract it, and double-click `index.html`. Keep all folders (`img`, `media`) beside `index.html`. No install needed.

## Processing scripts

The Python scripts we used to prepare the images and numbers are in this repository, so the results can be checked and repeated.

## Data and credits

- NISAR L2 GCOV (NASA-ISRO, provisional), via ASF DAAC. Validated products (from 21 Oct 2026) are used only on the Nawalapitiya Rain test page, with a forest-measured correction.
- Contains modified Copernicus Sentinel data (2026): Sentinel-1 (OPERA RTC-S1, ASF) and Sentinel-2 L2A (AWS Earth Search).
- Rain: NASA GPM IMERG daily (about 10 km) via GES DISC Giovanni. NASA POWER (MERRA-2 model, about 50 km, not a rain gauge) for the story pages.
- Soil moisture: AMSR2 LPRM 6.9 GHz (Ampara).
- Land cover (forest mask): ESA WorldCover 2021 v200 (CC BY 4.0).
- Colour recipe: NASA SVS 5661.
- Thailand context: NASA Earth Observatory, 9 Oct 2026.
- Senanayake Samudraya storage comparison: reservoir series compiled by Macro Lab from Irrigation Department data (not an official publication). Used for direction of change only.
- Independent sources shown on the other story pages give context for each event; they are not validation of our measured areas.

## Limits

- All NISAR data used here are provisional (except the validated scenes noted above) and may change on reprocessing.
- Dark radar areas are smooth surfaces. They are not always flood water.
- Our wording, such as "consistent with", is deliberate. These are signals worth checking, not proof.

## AI disclosure

The analysis scripts, this web app and the draft text were created with assistance from Claude (Anthropic).

## Team

Anuththara Divyanjalie · Muditha Kumara · Mayumi Maleesha
