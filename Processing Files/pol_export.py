import sys, os, numpy as np
from osgeo import gdal
from scipy.ndimage import uniform_filter
from PIL import Image
gdal.UseExceptions()
pre,cdir,t1,t2,out=sys.argv[1:6]
os.makedirs(out,exist_ok=True)
def rd(p):
    ds=gdal.Open(p); a=ds.GetRasterBand(1).ReadAsArray().astype("float64"); ds=None; return a
chan={"hh":"hhhh","hv":"hvhv"}
data={}
for c,s in chan.items():
    for t in (t1,t2):
        a=rd(os.path.join(cdir,"%s_%s_%s.tif"%(pre,t,s)))
        ok=a>1e-4
        sm=uniform_filter(np.where(ok,a,0.0),5)
        d=10*np.log10(np.where(sm>1e-6,sm,np.nan))
        data[(c,t)]=(d,ok)
for c in chan:
    vals=np.concatenate([data[(c,t)][0][data[(c,t)][1]&np.isfinite(data[(c,t)][0])] for t in (t1,t2)])
    lo,hi=np.percentile(vals,[2,98]); print(c,"stretch dB",round(lo,2),round(hi,2))
    for t in (t1,t2):
        d,ok=data[(c,t)]
        g=np.clip((np.nan_to_num(d,nan=lo)-lo)/(hi-lo),0,1)
        v=(g*255).astype("uint8")
        rgba=np.zeros(d.shape+(4,),"uint8")
        if c=="hh": rgba[...,0]=v
        else: rgba[...,1]=v
        rgba[...,3]=np.where(ok,255,0)
        fn=os.path.join(out,"pol_%s_%s_%s.png"%(pre,c,t))
        Image.fromarray(rgba).save(fn); print("wrote",fn,d.shape)
