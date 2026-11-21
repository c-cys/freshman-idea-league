"""세탁실 정책 4가지 비교 시뮬레이션 (한 층: 세탁기 2대, 건조기 2대, 저녁 18~24시)

정책
  1. 현재      : 정보 없음. 내려가 봐야 앎. 빨래 다 돼도 늦게 꺼냄
  2. 정보      : 앱에 층별 사용 여부·남은 시간 표시 + 종료 알림
  3. 예약      : 2 + 순서대로 예약. 차례 알림 후 10분 안에 안 오면 자동 취소
  4. 예약+추천 : 3 + 원하는 완료 시각을 받아 세탁기·건조기가 겹치지 않는 시작 시각을 추천

지표
  - 대기: 원하는 완료 시각보다 늦게 끝난 시간(분)
  - 헛걸음: 내려갔는데 기계가 없어서 그냥 돌아온 횟수
  - 가동률: 기계가 묶여 있던 시간 중 실제로 돌아간 비율

모든 숫자는 가정값이다. 아래 PARAM만 바꾸면 결과가 다시 계산된다.
"""
import math
import random

PARAM = dict(
    WASH=45,            # 세탁 시간(분)
    DRY=55,             # 건조 시간(분)
    RATE_PEAK=1.8,      # 19~23시 시간당 도착 학생 수
    RATE_OFF=1.0,       # 18~19시, 23~24시
    LATE_PICKUP=20,     # 정보 없을 때 다 된 빨래를 꺼내러 오기까지 평균(분)
    ALERT_PICKUP=7,     # 종료 알림이 있을 때 평균(분)
    RETRY=20,           # 헛걸음 후 다시 내려가기까지 평균(분)
    NOTICE=4,           # 앱에서 빈자리를 보고 도착하기까지 평균(분)
    NOSHOW=0.10,        # 예약해 놓고 안 오는 확률
    TIMEOUT=10,         # 예약 자동 취소 시간(분)
    NORULE_LATE=40,     # 규칙이 없을 때 노쇼한 사람이 결국 나타나기까지 평균(분)
    URGENT=0.5,         # 바로 해야 하는 학생 비율 (나머지는 원하는 완료까지 1~3시간 여유)
    HANDOFF=5,          # 추천 정책에서 세탁 끝나고 건조기로 옮기는 시간
    COLLECT=5,          # 추천 정책에서 건조 끝나고 꺼내는 시간(페널티 관용 5분)
    PENALTY_PICKUP=4,   # 알림 + 페널티(5분 관용 후 사용 제한)가 있을 때 꺼내러 오기까지 평균(분)
    N_W=2,              # 층당 세탁기 수
    N_D=2,              # 층당 건조기 수
)
TMAX = 1500
OPEN = 360  # 18시부터 6시간 동안 도착


def exp(rng, mean):
    return max(1, int(math.ceil(rng.expovariate(1 / mean))))


def make_students(rng, P):
    out, t = [], 0.0
    lam_max = P["RATE_PEAK"] / 60
    while True:
        t += rng.expovariate(lam_max)
        if t >= OPEN:
            break
        lam = P["RATE_PEAK"] if 60 <= t < 300 else P["RATE_OFF"]
        if rng.random() < lam / P["RATE_PEAK"]:
            urgent = rng.random() < P["URGENT"]
            slack = 0 if urgent else rng.uniform(60, 180)
            a = int(t)
            out.append(dict(a=a, urgent=urgent, Tdes=a + P["WASH"] + P["DRY"] + P["HANDOFF"] + slack,
                            need="w", st="pending", att=None, wasted=0, finish=None))
    return out


def run_online(policy, rng, P, rule=True):
    """정책 1~3: 1분 단위 시뮬레이션"""
    S = make_students(rng, P)
    M = {"w": [dict(state="free", who=None) for _ in range(P["N_W"])],
         "d": [dict(state="free", who=None) for _ in range(P["N_D"])]}
    dur = {"w": P["WASH"], "d": P["DRY"]}
    pick_mean = {"current": P["LATE_PICKUP"], "info": P["ALERT_PICKUP"]}.get(policy, P["PENALTY_PICKUP"])
    Q = {"w": [], "d": []}
    busy = {"run": 0, "held": 0}

    def free(k):
        return [m for m in M[k] if m["state"] == "free"]

    def start(m, k, s, t):
        m.update(state="run", who=s, end=t + dur[k])
        s["st"] = "using"

    def on_fail(s, t):
        if policy == "current":
            s["st"], s["att"] = "retry", t + exp(rng, P["RETRY"])
        else:
            s["st"], s["att"] = "waiting", None

    def try_in_room(s, k, t):
        f = free(k)
        if policy == "reserve":
            if f and not Q[k]:
                start(f[0], k, s, t)
            else:
                Q[k].append(s)
                s["st"] = "queued"
        elif f:
            start(f[0], k, s, t)
        else:
            on_fail(s, t)

    for t in range(TMAX):
        for k in "wd":
            for m in M[k]:
                if m["state"] == "run" and m["end"] == t:
                    m.update(state="idle", pick=t + exp(rng, pick_mean), done_at=t)
        for k in "wd":
            for m in M[k]:
                if m["state"] == "idle" and m["pick"] == t:
                    s = m["who"]
                    m.update(state="free", who=None)
                    if k == "w":
                        s["need"] = "d"
                        try_in_room(s, "d", t)
                    else:
                        s["finish"], s["st"] = m["done_at"], "done"
        for s in S:
            if s["st"] == "pending" and s["a"] == t:
                if policy == "current":
                    s["st"], s["att"] = "retry", t
                elif policy == "info":
                    s["st"] = "waiting"
                else:
                    Q["w"].append(s)
                    s["st"] = "queued"
        if policy == "reserve":
            for k in "wd":
                for m in M[k]:
                    if m["state"] == "resv":
                        if m.get("arrive") == t:
                            start(m, k, m["who"], t)
                        elif m.get("cancel") == t:
                            Q[k].append(m["who"])
                            m.update(state="free", who=None)
                for m in free(k):
                    if not Q[k]:
                        break
                    s = Q[k].pop(0)
                    m.update(state="resv", who=s, arrive=None, cancel=None)
                    late = rng.random() < P["NOSHOW"]
                    d = exp(rng, P["NOTICE"])
                    if rule and (late or d > P["TIMEOUT"]):
                        m["cancel"] = t + P["TIMEOUT"]
                    else:
                        m["arrive"] = t + (exp(rng, P["NORULE_LATE"]) if late else d)
        else:
            order = [s for s in S if s["st"] == "retry" and s["att"] == t]
            rng.shuffle(order)
            for s in order:
                f = free(s["need"])
                if f:
                    start(f[0], s["need"], s, t)
                else:
                    s["wasted"] += 1
                    on_fail(s, t)
            if policy == "info":
                for s in S:
                    if s["st"] == "waiting" and free(s["need"]):
                        s["st"], s["att"] = "retry", t + exp(rng, P["NOTICE"])
        for k in "wd":
            for m in M[k]:
                if m["state"] == "run":
                    busy["run"] += 1
                elif m["state"] in ("idle", "resv"):
                    busy["held"] += 1
        if t > OPEN and all(s["st"] == "done" for s in S):
            break
    return S, busy


def run_recommend(rng, P):
    """정책 4: 학생이 올 때마다 아직 시작 안 한 예약을 다시 짠다.
    여유가 적은 사람(급한 사람)부터 가장 빠른 칸에, 여유 있는 사람은 남는 칸에 넣는다.
    목적: 모든 학생이 원하는 완료 시각에 최대한 맞게 끝나도록(늦어진 시간 합 최소화)."""
    S = make_students(rng, P)
    W, D, H, C = P["WASH"], P["DRY"], P["HANDOFF"], P["COLLECT"]
    L = TMAX + 600
    NM = {"w": P["N_W"], "d": P["N_D"]}
    fixed = {k: [[False] * L for _ in range(NM[k])] for k in "wd"}
    busy = {"run": 0, "held": 0}
    for x in S:
        x.update(ready=None, plan=None)

    def mark(grid, k, i, s, length):
        for t in range(s, min(L, s + length)):
            grid[k][i][t] = True

    def free_at(grid, k, s, length):
        for i in range(NM[k]):
            if not any(grid[k][i][s:s + length]):
                return i
        return None

    def replan(now):
        grid = {k: [row[:] for row in fixed[k]] for k in "wd"}
        pend = [x for x in S if x["ready"] is not None and not x.get("started")]
        pend.sort(key=lambda x: x["Tdes"] - W - H - D)
        for x in pend:
            for s in range(max(now + 1, x["ready"]), L - W - H):
                i = free_at(grid, "w", s, W + H)
                if i is None:
                    continue
                for ds in range(s + W + H, L - D - C):
                    j = free_at(grid, "d", ds, D + C)
                    if j is not None:
                        break
                x["plan"] = (s, i, ds, j)
                mark(grid, "w", i, s, W + H)
                mark(grid, "d", j, ds, D + C)
                break

    for t in range(TMAX):
        changed = False
        for x in S:
            if x["ready"] is None and x["a"] == t:
                x["ready"], changed = t, True
        for x in S:
            if x["plan"] and not x.get("started") and x["plan"][0] == t:
                s, i, ds, j = x["plan"]
                if rng.random() < P["NOSHOW"]:
                    mark(fixed, "w", i, t, P["TIMEOUT"])
                    busy["held"] += P["TIMEOUT"]
                    x["ready"], x["plan"], changed = t + P["TIMEOUT"], None, True
                else:
                    x["started"] = True
                    mark(fixed, "w", i, s, W + H)
                    mark(fixed, "d", j, ds, D + C)
                    busy["run"] += W + D
                    busy["held"] += H + C
                    x["finish"] = ds + D
        if changed:
            replan(t)
        if t > OPEN and all(x.get("started") for x in S):
            break
    return S, busy


def evaluate(policy, reps=800, seed=1, rule=True, P=PARAM):
    rng = random.Random(seed)
    late = trips = n = 0
    late_u = n_u = 0
    run = held = 0
    for _ in range(reps):
        S, busy = run_recommend(rng, P) if policy == "recommend" else run_online(policy, rng, P, rule)
        for s in S:
            fin = s["finish"] if s["finish"] is not None else TMAX
            lt = max(0, fin - s["Tdes"])
            late += lt
            trips += s["wasted"]
            n += 1
            if s["urgent"]:
                late_u += lt
                n_u += 1
        run += busy["run"]
        held += busy["held"]
    return dict(wait=late / n, wait_urgent=late_u / n_u, trips=trips / n, util=run / (run + held))


if __name__ == "__main__":
    names = [("current", "현재"), ("info", "정보"), ("reserve", "예약"), ("recommend", "예약+추천")]
    print(f"{'정책':<8}{'평균 대기':>8}{'급한 학생 대기':>12}{'헛걸음':>8}{'가동률':>8}")
    for key, nm in names:
        r = evaluate(key)
        print(f"{nm:<8}{r['wait']:>7.1f}분{r['wait_urgent']:>11.1f}분{r['trips']:>7.2f}회{r['util']:>8.0%}")
    r = evaluate("reserve", rule=False)
    print(f"{'예약(취소 규칙 없음)':<8} 평균 대기 {r['wait']:.1f}분, 가동률 {r['util']:.0%}")
