import json, math, laundry_sim_v3 as L
P=dict(L.PARAM)
res={}
for k in ["current","info","reserve","recommend"]:
    res[k]=L.evaluate(k,reps=800,P=P)
P3=dict(P,N_W=3,N_D=3); res["current_3"]=L.evaluate("current",reps=800,P=P3)
P23=dict(P,N_W=2,N_D=3); res["current_2_3"]=L.evaluate("current",reps=800,P=P23)
res["reserve_norule"]=L.evaluate("reserve",reps=800,P=P,rule=False)
Pnp=dict(P,PENALTY_PICKUP=P["ALERT_PICKUP"]); res["reserve_nopenalty"]=L.evaluate("reserve",reps=800,P=Pnp)
for s in [2,3]:
    res[f"seed{s}"]={k:round(L.evaluate(k,reps=400,seed=s,P=P)["wait"],1) for k in ["current","info","reserve","recommend"]}
# queueing: nominal vs effective utilization at peak
lam=P["RATE_PEAK"]/60
def erlangC(c,a):
    rho=a/c
    if rho>=1: return 1.0, float('inf')
    s=sum(a**k/math.factorial(k) for k in range(c))
    top=a**c/math.factorial(c)/(1-rho)
    pw=top/(s+top); return pw, pw/(c/ (a/lam) * (1) )  # placeholder
q={}
for name,svc in [("wash_nom",P["WASH"]),("dry_nom",P["DRY"]),("wash_eff",P["WASH"]+P["LATE_PICKUP"]),("dry_eff",P["DRY"]+P["LATE_PICKUP"]),("wash_pen",P["WASH"]+P["PENALTY_PICKUP"]),("dry_pen",P["DRY"]+P["PENALTY_PICKUP"])]:
    a=lam*svc; c=2; rho=a/c
    if rho<1:
        s=sum(a**k/math.factorial(k) for k in range(c)); top=a**c/math.factorial(c)/(1-rho); pw=top/(s+top)
        Wq=pw*svc/(c*(1-rho))
        # birth-death stationary: pi_n for n busy (0..c) with infinite queue
        p0=1/(s+top); pi=[p0*a**n/math.factorial(n) for n in range(c+1)]
    else: pw=1; Wq=float('inf'); pi=None
    q[name]=dict(svc=svc,rho=round(rho,3),p_allbusy=round(pw,3),Wq=None if Wq==float('inf') else round(Wq,1),pi_free2=None if not pi else round(pi[0],3),pi_free1=None if not pi else round(pi[1],3))
res["queue"]=q
json.dump(res,open("sim_result_v3.json","w"),ensure_ascii=False,indent=1)
print(json.dumps(res,ensure_ascii=False,indent=1))
