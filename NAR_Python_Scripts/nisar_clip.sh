#!/usr/bin/env bash
# nisar_clip.sh - find NISAR L2 GCOV granules over a bbox and clip layers locally
# via GDAL /vsicurl with Earthdata Login (reads byte ranges; no full .h5 download).
# Usage:
#   ./nisar_clip.sh list | clip | one <granule_name>
set -euo pipefail

COLL=${COLL:-NISAR_L2_GCOV_PROVISIONAL_V1}   # VALIDATED: NISAR_L2_GCOV_V1
BBOX=${BBOX:-80.45,6.90,80.62,7.10}          # W,S,E,N degrees (Nawalapitiya)
START=${START:-2026-06-17T00:00:00Z}
END=${END:-2026-11-14T23:59:59Z}
TRACK=${TRACK:-}
FRAME=${FRAME:-}
DIR=${DIR:-}
FREQ=${FREQ:-frequencyA}
LAYERS=${LAYERS:-"HHHH HVHV mask numberOfLooks"}
T_SRS=${T_SRS:-EPSG:32644}
RES=${RES:-10}
OUT=${OUT:-./nisar_clips}
BASE="https://nisar.asf.earthdatacloud.nasa.gov/NISAR/${COLL}"

setup_auth() {
  if ! grep -qs "urs.earthdata.nasa.gov" "$HOME/.netrc"; then
    echo "Missing ~/.netrc Earthdata entry (machine urs.earthdata.nasa.gov login USER password PASS)" >&2
    exit 1
  fi
  touch "$HOME/.urs_cookies"
  export GDAL_HTTP_NETRC=YES
  export GDAL_HTTP_COOKIEFILE="$HOME/.urs_cookies"
  export GDAL_HTTP_COOKIEJAR="$HOME/.urs_cookies"
  export GDAL_DISABLE_READDIR_ON_OPEN=YES
  export CPL_VSIL_CURL_ALLOWED_EXTENSIONS=.h5
  export GDAL_HTTP_MAX_RETRY=5 GDAL_HTTP_RETRY_DELAY=3
  export VSI_CACHE=TRUE VSI_CACHE_SIZE=250000000
}

search_urls() {
  local url="https://cmr.earthdata.nasa.gov/search/granules.json?short_name=${COLL}&bounding_box=${BBOX}&temporal=${START},${END}&page_size=2000&sort_key=start_date"
  curl -sS --fail "$url" \
    | jq -r '.feed.entry[] | [.links[]?.href] | map(select(startswith("https://") and endswith(".h5"))) | .[0] // empty' \
    | sort -u \
    | while read -r u; do
        n=$(basename "$u" .h5); IFS=_ read -r -a f <<< "$n"
        [[ -n "$TRACK" && "${f[5]}" != "$TRACK" ]] && continue
        [[ -n "$DIR"   && "${f[6]}" != "$DIR"   ]] && continue
        [[ -n "$FRAME" && "${f[7]}" != "$FRAME" ]] && continue
        echo "$u"
      done
}

list() {
  printf "%-10s %-6s %-6s %-4s %-6s %-6s %-8s %s\n" DATE CYCLE TRACK DIR FRAME MODE CRID NAME
  search_urls | while read -r u; do
    n=$(basename "$u" .h5); IFS=_ read -r -a f <<< "$n"
    printf "%-10s %-6s %-6s %-4s %-6s %-6s %-8s %s\n" \
      "${f[11]:0:4}-${f[11]:4:2}-${f[11]:6:2}" "${f[4]}" "${f[5]}" "${f[6]}" "${f[7]}" "${f[8]}" "${f[13]}" "$n"
  done
}

clip_url() {
  local url=$1 n f date src out vrt srs ullr
  local -a geo
  n=$(basename "$url" .h5); IFS=_ read -r -a f <<< "$n"
  date=${f[11]:0:8}
  mkdir -p "$OUT"
  mapfile -t geo < <(python3 "$(dirname "$0")/nisar_georef.py" "$url" "$FREQ")
  if [[ ${#geo[@]} -lt 2 ]]; then echo "!! $n: could not read georeferencing" >&2; return 1; fi
  srs=${geo[0]}; ullr=${geo[1]}
  echo "== $n  ($srs  $ullr)"
  for L in $LAYERS; do
    out="$OUT/${date}_T${f[5]}${f[6]}_F${f[7]}_${f[13]}_${FREQ}_${L}.tif"
    [[ -s "$out" ]] && { echo "skip $out"; continue; }
    src="HDF5:\"/vsicurl/${url}\"://science/LSAR/GCOV/grids/${FREQ}/${L}"
    vrt="$OUT/.tmp_${date}_${L}.vrt"
    echo ">> $out"
    if gdal_translate -q -of VRT -a_srs "$srs" -a_ullr $ullr "$src" "$vrt"; then
      gdalwarp -q -overwrite -r near -t_srs "$T_SRS" -tr "$RES" "$RES" -tap \
        -te ${BBOX//,/ } -te_srs EPSG:4326 \
        -co COMPRESS=DEFLATE -co TILED=YES "$vrt" "$out" \
        || echo "   (warp failed for $L)" >&2
    else
      echo "   (layer $L not available - skipped)" >&2
    fi
    rm -f "$vrt"
  done
}

setup_auth
case "${1:-list}" in
  list) list ;;
  clip) search_urls | while read -r u; do clip_url "$u" || true; done ;;
  one)  [[ -n "${2:-}" ]] || { echo "give a granule name or URL" >&2; exit 1; }
        if [[ "$2" == https://* ]]; then clip_url "$2"; else clip_url "${BASE}/$2/$2.h5"; fi ;;
  *) echo "usage: $0 list|clip|one <granule>" >&2; exit 1 ;;
esac
