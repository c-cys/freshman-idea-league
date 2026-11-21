"""세탁기 문제: 마르코프 체인(3장) + 유한 기간 MDP(4.3절)

상태 s = 지금 비어 있는 세탁기 수 (0, 1, 2). 한 층에 세탁기 2대.
시간 단위 = 10분. 한 칸 안에서 일어나는 순서:
  1) 돌아가는 세탁기는 각각 확률 q로 끝나고 비워진다 (평균 1/q칸 = 60분, 수거 지연 포함)
  2) 다른 학생이 확률 p로 와서, 빈 세탁기가 있으면 하나를 쓴다
"""
import numpy as np
from math import comb

q = 1 / 6      # 10분 동안 세탁기 한 대가 끝날 확률
p = 0.25       # 10분 동안 다른 학생이 올 확률 (저녁 피크)
R = 10         # 세탁 시작 성공의 가치
C = 2          # 빨래 바구니 들고 내려가는 수고(헛걸음 비용)
T = 12         # 남은 결정 횟수 (10분 x 12 = 2시간)


def after_departures(s):
    """비어 있는 수 s에서 끝나는 세탁기가 생긴 뒤의 분포 {f: 확률}"""
    b = 2 - s
    return {s + d: comb(b, d) * q**d * (1 - q) ** (b - d) for d in range(b + 1)}


# ---- 1단계: 마르코프 체인 ----
P = np.zeros((3, 3))
for s in range(3):
    for f, pf in after_departures(s).items():
        if f >= 1:
            P[s, f - 1] += pf * p
            P[s, f] += pf * (1 - p)
        else:
            P[s, 0] += pf

A = np.vstack([P.T - np.eye(3), np.ones(3)])
pi = np.linalg.lstsq(A, np.r_[0, 0, 0, 1], rcond=None)[0]

# 0 상태에서 처음으로 1대 이상 비는 데 걸리는 평균 시간 (3.8절 평균 도달 시간)
p_leave0 = 1 - P[0, 0]
mean_wait0 = 1 / p_leave0

# ---- 2단계: 나의 결정 (유한 기간 MDP, 후진 귀납법) ----
def success_prob(s):
    """지금 출발하면(10분 뒤 도착) 세탁기를 잡을 확률. 다른 학생이 먼저 온다고 가정"""
    tot = 0.0
    for f, pf in after_departures(s).items():
        if f >= 2:
            tot += pf
        elif f == 1:
            tot += pf * (1 - p)
    return tot


V = np.zeros(3)
policy = []
for n in range(T, 0, -1):
    Qgo = np.array([success_prob(s) * R - C + (1 - success_prob(s)) * V[0] for s in range(3)])
    Qwait = P @ V
    policy.append(["가기" if Qgo[s] >= Qwait[s] else "기다리기" for s in range(3)])
    V = np.maximum(Qgo, Qwait)
policy = policy[::-1]

# ---- 비교: 앱 없이 무작정 가기 (상태를 모르니 정상분포 기준으로 도착) ----
def blind_value(steps):
    """매 칸 출발, 실패하면 다음 칸에 또 출발. 첫 출발 상태는 정상분포를 따른다"""
    dist, val, done = pi.copy(), 0.0, 0.0
    trips = 0.0
    for _ in range(steps):
        alive = 1 - done
        if alive < 1e-12:
            break
        ps = np.array([success_prob(s) for s in range(3)])
        succ = (dist * ps).sum()
        val += alive * (succ * R - C)
        trips += alive
        done += alive * succ
        dist = np.eye(3)[0]
    return val, done, trips


def app_stats():
    """앱 정책을 따를 때 성공 확률과 평균 헛걸음 수 (정상분포에서 시작)"""
    dist = pi.copy()
    done = wasted = 0.0
    for n in range(T):
        go = np.array([policy[n][s] == "가기" for s in range(3)])
        ps = np.array([success_prob(s) for s in range(3)])
        succ = (dist * go * ps).sum()
        fail = (dist * go * (1 - ps)).sum()
        done += succ
        wasted += fail
        stay = dist * ~go
        dist = stay @ P + fail * np.eye(3)[0]
    return done, wasted


if __name__ == "__main__":
    np.set_printoptions(precision=3, suppress=True)
    print("전이 행렬 P (행: 지금 상태 0/1/2, 열: 10분 뒤 상태)")
    print(P)
    print("정상분포 pi =", pi)
    print(f"0대 상태에서 빈자리가 날 때까지 평균 {mean_wait0:.2f}칸 = {mean_wait0*10:.0f}분")
    print("출발 시 성공 확률:", [round(success_prob(s), 3) for s in range(3)])
    print("\n최적 정책 (남은 시간별)")
    for n, row in enumerate(policy):
        left = (T - n) * 10
        print(f"  남은 {left:>3}분  0대:{row[0]:<4} 1대:{row[1]:<4} 2대:{row[2]}")
    print("\n기대 가치 V1(s) =", np.round(V, 2))
    bv, bd, bt = blind_value(T)
    ad, aw = app_stats()
    print(f"앱 없이: 성공 {bd:.1%}, 평균 출발 {bt:.2f}회, 헛걸음 {bt-bd:.2f}회")
    print(f"앱 있음: 성공 {ad:.1%}, 헛걸음 {aw:.2f}회")
