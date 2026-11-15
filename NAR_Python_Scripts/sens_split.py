import numpy as np, glob, re, sys
sys.path.insert(0,'.')
import per_pixel_rain as p
from datetime import date
D=sys.argv[1]; R=sys.argv[2]
rain=p.read_giovanni_csv(R)
fs=sorted(glob.glob(D+'/*_db.tif')); st=[]; ds=[]
for f in fs:
    tr,s=re.search(r'(T\d{3}[AD])_(\d{8})_db',f).groups()
    hh=p.pick(p.read_bands(f)[0],'HH',0)
    off=p.OFFSETS.get(tr,{}).get('HH',0) if s in p.OFFSETS.get(tr,{}).get('dates',()) else 0
    st.append(p.block_db(hh,10)+off); ds.append(date(int(s[:4]),int(s[4:6]),int(s[6:])))
st=np.stack(st); x=np.array([p.rain_window(rain,d,7) for d in ds])
def sl(i): return p.pixel_regression(st[i],x[i])[0]*100
res=[]
for name,a,b in [('odd vs even',list(range(0,len(ds),2)),list(range(1,len(ds),2))),
                 ('first half vs second half',list(range(len(ds)//2)),list(range(len(ds)//2,len(ds))))]:
    A,B=sl(a),sl(b); ok=np.isfinite(A)&np.isfinite(B)&(np.nanmean(st,0)<2)
    r=np.corrcoef(A[ok],B[ok])[0,1]; res.append(r)
    print(f'{name}: r = {r:+.2f}  (n={ok.sum()} blocks of 100 m; median slopes {np.median(A[ok]):+.2f} / {np.median(B[ok]):+.2f} dB per 100 mm)')
print('PASS' if min(res)>0.3 else 'FAIL', '(pass = both r > 0.3)')
