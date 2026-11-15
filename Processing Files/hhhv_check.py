import sys, numpy as np
from osgeo import gdal
from scipy.ndimage import uniform_filter
a=sys.argv[1:5]; thr=float(sys.argv[5]) if len(sys.argv)>5 else 3.0
def rd(p):
    ds=gdal.Open(p)
    arr=ds.GetRasterBand(1).ReadAsArray().astype("float64")
    ds=None
    return arr
rh,rv,eh,ev=[rd(p) for p in a]
ok=(rh>1e-4)&(rv>1e-4)&(eh>1e-4)&(ev>1e-4)
def db(x):
    x=np.where(ok,x,0.0)
    s=uniform_filter(x,9); return 10*np.log10(np.where(s>1e-6,s,np.nan))
Rh,Rv,Eh,Ev=map(db,(rh,rv,eh,ev))
dh=Eh-Rh; dv=Ev-Rv
m=ok&np.isfinite(dh)&np.isfinite(dv)
dh-=np.nanmedian(dh[m]); dv-=np.nanmedian(dv[m])
px=10*10/1e6
def mean(d,k): return d[k].mean() if k.any() else float("nan")
print("valid px",int(m.sum()))
for name,d in(("HH",dh),("HV",dv)):
    print(f"{name}: darker >{thr} dB {int(((d<-thr)&m).sum())*px:.2f} km2 | brighter >{thr} dB {int(((d>thr)&m).sum())*px:.2f} km2")
dark_v=m&(dv<-thr); dark_h=m&(dh<-thr)
print("Where HV got darker: mean dHH %.2f dB, mean dHV %.2f dB"%(mean(dh,dark_v),mean(dv,dark_v)))
print("Where HH got darker: mean dHH %.2f dB, mean dHV %.2f dB"%(mean(dh,dark_h),mean(dv,dark_h)))
print("Darker in both: %d px; only HV: %d; only HH: %d"%((dark_v&dark_h).sum(),(dark_v&~dark_h).sum(),(dark_h&~dark_v).sum()))
bh=m&(dh>thr); bv=m&(dv>thr)
print("Brighter: HH only %d px, HV only %d px, both %d px"%((bh&~bv).sum(),(bv&~bh).sum(),(bh&bv).sum()))
print("HH brighter but HV not: mean dHH %.2f, mean dHV %.2f"%(mean(dh,bh&~bv),mean(dv,bh&~bv)))
