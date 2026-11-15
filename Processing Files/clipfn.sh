export GDAL_HTTP_COOKIEFILE=~/.urs_cookies GDAL_HTTP_COOKIEJAR=~/.urs_cookies GDAL_DISABLE_READDIR_ON_OPEN=YES CPL_VSIL_CURL_ALLOWED_EXTENSIONS=.h5 GDAL_CACHEMAX=512 VSI_CACHE=TRUE VSI_CACHE_SIZE=100000000
B=https://nisar.asf.earthdatacloud.nasa.gov/NISAR/NISAR_L2_GCOV_PROVISIONAL_V1
clip2() {
  local pre=$1 tag=$2 N=$3
  for band in HVHV HHHH; do
    out=${pre}_${tag}_${(L)band}.tif
    [ -f $out ] && continue
    gdalwarp -q -overwrite -te $4 $5 $6 $7 -te_srs EPSG:4326 -ts $8 $9 HDF5:"/vsicurl/$B/$N/$N.h5"://science/LSAR/GCOV/grids/frequencyA/$band $out
  done
  echo done $pre $tag
}
