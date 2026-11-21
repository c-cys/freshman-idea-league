"""생활관 간 세탁기·건조기 재배치 (노션 '생활관별 표' 사용)
- 세탁기 수 = 건조기 수 = 층수 x 2 (표의 식). 한 층에 2세트, 학생은 자기 층 세탁실만 쓴다고 가정
- 층별 수요: 학생 1명이 약 1주에 1번 세탁, 저녁 집중 -> 피크 도착률 = 1.8명/시간 x (층 인원 / 전체 평균 층 인원 72.2명)
- 재배치: 전체 세트 수(210)는 그대로, 층마다 최소 1세트. 한계 분석(greedy marginal allocation)으로
  '한 세트를 더 놓았을 때 줄어드는 총 대기'가 가장 큰 층부터 한 세트씩 배정 -> 분리 가능한 볼록 함수에서 최적
"""
import json, laundry_sim_v3 as L
L.TMAX = 6000
B = [("사랑관",395,5),("소망관",405,5),("성실관",271,5),("진리관",275,5),("아름관",497,5),("신뢰관",276,5),("지혜관",272,5),
     ("갈릴레이관",853,5),("여울관",248,5),("나들관",348,5),("다솜관",316,5),("희망관",699,15),("예지관",72,5),("나래관",244,5),
     ("미르관",350,5),("세종관 A",472,5),("세종관 B",699,5),("문지관",380,5),("화암관",504,5)]
FLOORS = sum(f for _, _, f in B); PEOPLE = sum(p for _, p, _ in B); SETS = 2 * FLOORS
AVG = PEOPLE / FLOORS
REPS = 200
cache = {}
def f(policy, rate, n):
    k = (policy, round(rate, 3), n)
    if k not in cache:
        P = dict(L.PARAM, RATE_PEAK=rate, RATE_OFF=rate / 1.8, N_W=n, N_D=n)
        cache[k] = L.evaluate(policy, reps=REPS, seed=1, P=P)["wait"]
    return cache[k]
floor_rate = {nm: 1.8 * (p / fl) / AVG for nm, p, fl in B}
def summarize(policy, alloc):  # alloc: {건물: [층별 세트 수]}
    tot = 0; per = {}
    for nm, p, fl in B:
        w = sum(f(policy, floor_rate[nm], n) for n in alloc[nm]) / fl
        per[nm] = round(w, 1); tot += w * p
    return tot / PEOPLE, per
now = {nm: [2] * fl for nm, _, fl in B}
# greedy
alloc = {nm: [1] * fl for nm, _, fl in B}
for _ in range(SETS - FLOORS):
    best = None
    for nm, p, fl in B:
        r = floor_rate[nm]
        i = min(range(fl), key=lambda j: alloc[nm][j])
        n = alloc[nm][i]
        if n >= 8: continue
        gain = r * (f("current", r, n) - f("current", r, n + 1))
        if best is None or gain > best[0]: best = (gain, nm, i)
    alloc[best[1]][best[2]] += 1
res = {}
for key, pol, al in [("now", "current", now), ("reloc", "current", alloc), ("sys_now", "recommend", now), ("sys_reloc", "recommend", alloc)]:
    w, per = summarize(pol, al); res[key] = dict(wait=round(w, 1), per=per, worst=max(per.values()), worst_bld=max(per, key=per.get))
res["table"] = [dict(name=nm, people=p, floors=fl, sets_now=2 * fl, sets_new=sum(alloc[nm]), per_set_now=round(p / (2 * fl), 1), per_set_new=round(p / sum(alloc[nm]), 1)) for nm, p, fl in B]
res["meta"] = dict(floors=FLOORS, people=PEOPLE, sets=SETS, avg_floor=round(AVG, 1), moved=sum(max(0, 2 * fl - sum(alloc[nm])) for nm, _, fl in B))
json.dump(res, open("relocate_building_result.json", "w"), ensure_ascii=False, indent=1)
for k in ["now", "reloc", "sys_now", "sys_reloc"]: print(k, res[k]["wait"], res[k]["worst_bld"], res[k]["worst"])
print(res["meta"])
for t in res["table"]: print(t)
