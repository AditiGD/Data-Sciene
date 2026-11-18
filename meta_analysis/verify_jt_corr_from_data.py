import json, os, sys, math
import numpy as np
root = sys.argv[1]
blog = {2016:.447,2017:.656,2018:.255,2019:.441,2021:.618,2022:.467,2023:.49,2024:.627,2025:.16}
rows=[]
for y in sorted(blog):
    d=json.load(open(f"{root}/data/senior/{y}/rounds/final.json"))
    j=[];t=[]
    for p in d["performances"]:
        s={x["name"]:x["points"] for x in p["scores"]}
        j.append(s["jury"]); t.append(s["public"])
    r=np.corrcoef(j,t)[0,1]; n=len(j)
    rows.append((y,n,r,blog[y]))
    print(f"{y} n={n} r_data={r:.3f} r_blog={blog[y]:.3f} diff={r-blog[y]:+.3f}")
z=np.array([math.atanh(r) for _,_,r,_ in rows]); v=np.array([1/(n-3) for _,n,_,_ in rows]); w=1/v
k=len(z); zf=(w*z).sum()/w.sum(); Q=(w*(z-zf)**2).sum(); C=w.sum()-(w**2).sum()/w.sum()
tau2=max(0,(Q-(k-1))/C); ws=1/(v+tau2); zr=(ws*z).sum()/ws.sum(); se=math.sqrt(1/ws.sum())
I2=max(0,(Q-(k-1))/Q)*100 if Q>0 else 0
from scipy import stats
tc=stats.t.ppf(.975,k-2); pi=(zr-tc*math.sqrt(se**2+tau2), zr+tc*math.sqrt(se**2+tau2))
print(f"DL pooled r={math.tanh(zr):.3f} CI=({math.tanh(zr-1.96*se):.3f},{math.tanh(zr+1.96*se):.3f}) PI=({math.tanh(pi[0]):.3f},{math.tanh(pi[1]):.3f}) tau2={tau2:.4f} Q={Q:.2f} p={1-stats.chi2.cdf(Q,k-1):.3f} I2={I2:.1f}%")
yrs=np.array([y for y,*_ in rows]); b=stats.linregress(yrs,z); print(f"trend slope(z/yr)={b.slope:.4f} p={b.pvalue:.2f}")
loo=[math.tanh(np.sum(np.delete(ws*z,i))/np.sum(np.delete(ws,i))) for i in range(k)]; print("LOO range", round(min(loo),3), round(max(loo),3))
