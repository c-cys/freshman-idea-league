# freshman-idea-league
새내기아이디어리그 코드입니다. 새내기과정학부 김보경 · 김효준 · 최유성

## 세탁기/건조기 눈치게임 그만
 
새내기 아이디어리그 발표 자료에 들어간 숫자를 계산한 코드입니다. 모든 숫자는 가정값으로 계산했습니다.
 
| 파일 | 내용 | 실행 |
|---|---|---|
| `laundry_sim_v3.py` | 한 층(세탁기 2 · 건조기 2) 시뮬레이션. 현재 / 현황만 / 1단계 / 1+2단계 방식 비교 | 다른 파일이 불러 씀 |
| `run_v3.py` | 검증 슬라이드와 진단 ①(이용률, 마르코프 체인) 숫자 | `python run_v3.py` |
| `relocate_building.py` | 진단 ②③: 생활관 19개 표를 이용한 생활관 간 재배치 (한계 분석) | `python relocate_building.py` |
| `laundry_mdp.py` | 1단계 MDP: 지금 내려갈까, 기다릴까 (후진 귀납법) | `python laundry_mdp.py` |
 
- 파일 4개를 같은 폴더에 두고 실행하세요. `numpy`가 필요합니다.
- 가정값은 `laundry_sim_v3.py` 맨 위 `PARAM`과 `relocate_building.py`의 생활관 표에서 바꿀 수 있습니다.
 
