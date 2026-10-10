웹 Python Agent 제출은 PYTHON_AGENT.txt와 python-example/을 참고하세요.
로컬 evaluate.py의 reset(seed)와 달리 웹 ZIP 인터페이스는 reset()입니다.

Skysailor Agent challenge — skysailor-380-v1

설치: Python 3.12와 uv를 준비하고 압축을 푼 폴더에서 uv sync 실행.
연습 평가:
  uv run python participant/evaluate.py --agent participant/agent.py --name my-agent
웹 실행:
  uv run uvicorn dashboard:app --host 127.0.0.1 --port 8080
  http://127.0.0.1:8080/training/ 에서 연습 평가 결과 확인.

Agent 계약: agent.py에 Agent 클래스를 제공.
reset(seed): 각 비행 전 내부 상태 초기화.
act(observation): [-1,1] 범위의 유한한 두 값 반환.
  action[0]: 레일 회전 속도 지령 / 최대 180도/s
  action[1]: 추 직선 속도 지령 / 최대 30mm/s
제어 주기 0.02초, 물리 적분 0.001초. 실제 운동은 관성·구동 한계 적용.

관측값 (17개, 순서 고정):
0:3 기체 좌표계의 세계 위쪽 단위벡터
3:6 기체 좌표계 각속도 / 10
6:9 기체 좌표계 상대 공기속도 / 10
9 허브 높이 / 3
10,11 레일 각도의 sin, cos
12 추의 레일상 위치 / 돔 반지름
13 레일 각속도 / 최대 각속도
14 추 직선속도 / 최대 직선속도
15:17 이전 행동

고정 모델: 돔 380x80mm, 돔 25g, 추 18g, 축 길이 5mm.
직선 힘 0.5N, 가속도 0.5m/s², 회전 토크 5mN·m.
보상: 전체 시스템 무게중심 고도(0 이상)의 시간 적분, 단위 m·s.
시작 높이 3m, 최대 10초, 착지 시 종료. 뒤집힘 자체로 종료하지 않음.
바람 gentle/up/down 중 선택, 초기 기울기 3–15도. seed로 재현.
점수: 고도 적분의 에피소드 평균. 체공시간·뒤집힘 비율은 보조 지표.
현재 기본 평가 seed 0–4는 공개 연습용이며 공식 순위가 아님.
다른 seed 집합이나 환경 버전의 점수는 직접 비교하지 말 것.
관측은 잡음·지연 없는 이상적 값. 380mm 공기력은 기존 CFD 환산으로 잠정적.

학습 예시 (선택 의존성):
  uv run --with stable-baselines3 python experiments/train_rail.py --reward altitude --steps 10000 --output outputs/rl-local --allow-provisional-aero

제출: Agent 소스, 필요한 의존성 버전, 모델 가중치, 이름을 함께 전달.
웹은 격리된 Python ZIP과 기존 선형 정책 JSON 제출을 지원합니다.
공식 평가 서비스는 미공개 평가 조건과 격리 실행 구성이 준비된 후 별도 제공.
타인의 Agent는 일반 호스트에서 실행하지 말 것. 위 로컬 평가기는 신뢰하는 코드 전용.

웹 제출 (Agent Arena v1): /arena/
지표 calm-380-v1: RailAirtimeEnv(wind_mode='constant'), 바람 0.
지표 wind-380-v1: RailAirtimeEnv(wind_mode='measured').
공개 seed 0–4, 5회 평균 고도 적분으로 지표별 순위 계산.
웹은 Python Agent 대신 선형 정책 JSON을 평가:
  {"weights": [[17개의 수], [17개의 수]], "bias": [0, 0]}
행동은 np.tanh(np.asarray(weights) @ observation + bias).
계수는 유한한 -100~100. 관측 규격은 위와 동일.
JSON을 /arena/에서 올리고 이름을 입력해 제출하면 서버에서 평가.
순위표 제출 선택 → seed별 비행 링크 → 3D 다시보기.
참가자 이름은 자기 신고이며 검증된 계정 식별자가 아님.
