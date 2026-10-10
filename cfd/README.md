# 고정 돔 CFD 검증

기존 MuJoCo의 패널 항력과 독립적으로 OpenFOAM에서 Navier–Stokes 방정식의
정상 비압축성 RANS(k-omega SST) 해를 계산합니다. 돔은 고정되어 있고 아래에서
위로 1.6 m/s의 공기가 흐릅니다. 이는 그 속도로 하강하는 돔의 상대 유동입니다.
제어기·줄·자유낙하 연동은 이 첫 실험에 포함하지 않습니다.

외경 240 mm, 높이 40 mm의 구면 돔이며, 벽 두께는 아직 지정되지 않아 1 mm로
가정했습니다. 공기 밀도 1.225 kg/m³, 동점성계수 1.5e-5 m²/s, Reynolds 수는
약 25,600입니다. 입구 난류강도 1%, 길이 척도 24 mm를 가정합니다.
도메인은 x/y ±0.96 m, z -0.96~1.92 m이며 입구·출구·미끄럼 측벽과 no-slip 돔을
사용합니다. 압력은 출구 기준 게이지 압력입니다.

## 실행

```sh
docker compose -f cfd/compose.yaml build
mkdir -p cfd/cases
docker compose -f cfd/compose.yaml run --rm solver \
  '/usr/bin/python3 /scripts/make_case.py --case /case/coarse --surface-size .008'
docker compose -f cfd/compose.yaml run --rm solver \
  'cp /scripts/run_case.sh /tmp/run-case.sh && bash /tmp/run-case.sh coarse'
uv run python cfd/analyze.py cfd/cases/coarse
```

격자 민감도: 같은 명령에서 case를 fine, surface-size를 .004로 바꿉니다.
CFD 컨테이너는 CPU 1개, 메모리 2300 MB를 상한으로 사용합니다. 기존 대시보드와
별도 이미지·서비스이며 자동으로 기존 물리 모델을 변경하지 않습니다.

기존 해가 있는 case는 덮어쓰지 않습니다. 다시 계산할 때는 새 case 이름을 사용하세요.

## 판정

- `checkMesh -allGeometry -allTopology` 통과 후에만 계산합니다.
- 최근 100 iteration의 Cd 표준편차/평균과 앞·뒤 절반 평균 차이가 각각 2% 미만인지
  확인합니다. SIMPLE iteration은 실제 시간이 아닙니다.
- 최종 초기 잔차 p<1e-3, U 성분<1e-4, k/omega<1e-3을 별도로 확인합니다.
- 두 격자가 각각 수렴해도 Cd 차이가 작다는 것은 이 두 격자 사이의 민감도 검사일
  뿐 완전한 격자 독립성 증명은 아닙니다.
- Gmsh 사면체를 공유 모서리·면·셀 중심으로 4개의 육면체로 분할합니다. 돔 테두리는 1.5 mm로 세분합니다. 벽에 수직인 프리즘 경계층은 없으므로 y+ 분포 및 벽함수 적합성을
  평가해야 합니다. 정상 RANS로 시간에 따라 변하는 와류를 해석했다고 주장하지 않습니다.
- 항력을 무게 0.080442 N과 비교합니다. 단일 속도의 Cd로 계산한 종단속도는
  Cd가 속도에 따라 일정하다는 가정의 참고값이며 검증된 낙하 결과가 아닙니다.

압력·속도 그림은 CFD 중앙 단면 샘플에서 생성합니다. 속도 그림의 유선은 단면에
투영한 벡터장의 유선이며 완전한 3D 입자 궤적은 아닙니다. 수렴 전 그림과 수치는
예비 결과로 표시합니다. 실제 장치 설계에 반영하기 전에는 비정상 유동, 벽 두께,
도메인 크기 및 실험과의 일치 여부까지 확인해야 합니다.

출처: OpenFOAM `simpleFoam`, `forceCoeffs`, `kOmegaSST` 및 Gmsh/OpenCASCADE.
OpenFOAM은 Debian bookworm의 공식 openfoam 패키지(1912 계열)를 사용합니다.

대시보드 보고서 갱신: `uv run python cfd/export_report.py` 후 브라우저를 새로 고칩니다. Compose는 보고서 폴더를 읽기 전용으로 마운트합니다. 보고서는 `/cfd/`에서 열립니다.

## 동일 격자에서 계산 이어가기

기존 해의 끝 시점을 유지한 채 반복 횟수만 늘릴 수 있습니다. 새 격자를 만들지 않습니다.

```sh
docker compose -f cfd/compose.yaml run --rm solver \
  'cd /case/coarse && foamDictionary system/controlDict -entry endTime -set 800 && simpleFoam >> log.solver 2>&1'
uv run python cfd/analyze.py cfd/cases/coarse
uv run python cfd/export_report.py
```

분석기는 재시작 구간별 항력 기록을 시간 인덱스로 합칩니다. 압력의 첫 보정 잔차를
사용하며, 해석 종료·격자 검사·항력 안정성·잔차를 모두 만족해야만 단일 격자의
수치 수렴으로 표시합니다. 이는 실험적 검증이나 격자 독립성 판정과 구별됩니다.

격자 변환은 체적 보존과 공유 면 일치를 테스트했습니다. 재시작 기록 병합과
압력 잔차/격자 실패를 수렴으로 오판하지 않는지도 테스트합니다.

```sh
uv run pytest -q tests/test_cfd_mesh.py tests/test_cfd_analysis.py
```

공식 참고: [벽면 처리와 y+](https://doc.openfoam.com/2606/tools/processing/models/turbulence/ras/wall-functions/), [yPlus 후처리](https://doc.openfoam.com/2212/tools/post-processing/function-objects/field/yPlus/). 설치된 해석기는 1912이며 새 버전의 설정을 그대로 복사하지 않고 해당 버전에서 실행 확인했습니다.

## 첫 실행 결과 (2026-10-04)

| 모델 | 셀 수 | 반복 | Cd (마지막 100회 평균) | 항력 @ 1.6 m/s |
|---|---:|---:|---:|---:|
| 기존 MuJoCo 패널 근사 | — | — | 1.073 | 76.1 mN |
| 기본 격자 · 표면 목표 8 mm | 255,524 | 800 | 1.474 | 104.6 mN |
| 세분 격자 · 표면 목표 4 mm | 395,388 | 400 | 1.353 | 96.0 mN |

두 격자 모두 전체 격자 검사를 통과하고 지정된 반복까지 유동 해석을 종료했습니다.
하지만 **두 계산 모두 수치 수렴 기준 미달**입니다. 기본 격자의 항력 평균 변화는
0.22%로 안정적이나, 첫 압력 잔차 0.00264와 횡방향 속도 잔차 약 0.001은 기준보다
높습니다. 세분 격자는 항력 평균 변화 4.74%, 첫 압력 잔차 0.00639입니다.
Cd 평균 차이 8.9%에는 미수렴 영향도 포함되므로 격자 오차로 해석할 수 없습니다.

평균 y+는 기본 4.26, 세분 2.89이고 범위가 넓습니다. 이는 벽면 처리와 경계층
해상도의 추가 점검이 필요하다는 진단 자료입니다. 경계층 격자, 추가 반복 및
비정상 후류 검증 전에는 이 결과로 MuJoCo 계수나 종단속도를 보정하지 않습니다.
JSON에 있는 상수 Cd 가정의 종단속도는 계산식 참고값일 뿐 검증된 예측이 아닙니다.

원시 해·로그: `cfd/cases/{coarse,fine}`. 배포용 그림과 JSON: `web/src/cfd/`.
최종 그래프는 각각 800회와 400회의 저장 필드입니다. 테스트 23개가 통과했습니다.

## 경계층 및 기울기 실험

새 `layer_mesh.py`는 반경–높이 단면의 경계층 격자를 360° 회전해 **전체 3차원**
유동 격자를 만듭니다. 축대칭 유동을 강제하지 않습니다. 기본값은 표면 3 mm,
첫 층 0.5 mm, 층 성장률 1.25, 총 층 두께 3 mm, 방위각 40분할입니다.
작은 테두리 삼각형은 경계와 체적을 보존하는 볼록 다각형으로 병합합니다.
원통형 외부 영역 반경은 0.96 m이며 높이 범위는 기존과 같습니다.
기존 사각 외부 영역과 격자 방식·벽면 처리가 동시에 달라지므로, 기존 결과와의
차이를 단순한 격자 수렴률로 해석하지 않습니다.

```sh
docker compose -f cfd/compose.yaml run --rm solver \
  '/usr/bin/python3 /scripts/layer_mesh.py --case /case/layered-new && /usr/bin/python3 /scripts/setup_layered.py /case/layered-new --tilt 0 --iterations 1200'
docker compose -f cfd/compose.yaml run --rm solver \
  'cd /case/layered-new && checkMesh -allGeometry -allTopology > log.checkMesh 2>&1 && grep -q "Mesh OK" log.checkMesh && simpleFoam > log.solver 2>&1'
uv run python cfd/analyze.py cfd/cases/layered-new
```

`checkMesh`는 검사 실패 시에도 종료 코드가 0일 수 있어 `Mesh OK`를 확인해야 합니다.
벽면은 `nutUSpaldingWallFunction`, `kLowReWallFunction`, `omegaWallFunction`을
사용합니다. 실제 y+ 분포와 층 두께 민감도를 별도로 평가해야 합니다.
`--surface-size .002`는 단면 세분 비교이며, 벽 수직·방위각·영역 크기의
독립적 수렴 검증을 대신하지 않습니다.

`setup_layered.py --tilt 10`은 돔 좌표계에서 유입 속도와 힘 기준축을 회전합니다.
양의 기울기는 돔의 +z가 세계 +x 쪽으로 기우는 방향입니다. 돔 원점 모멘트와,
중앙 제어기를 가정한 기준 전체 무게중심(z = −48.3 mm)의 모멘트를 구분합니다.
MuJoCo에 힘을 돔 원점에 적용할 때는 반드시 원점 모멘트를 사용해야 합니다.
무게중심으로 옮긴 모멘트를 함께 적용하면 힘의 지렛팔을 중복 계산합니다.
정적 복원 방향은 자유낙하 중 동적 안정성의 증거가 아닙니다.

분석에는 Cd뿐 아니라 Cl, Cs, CmPitch의 마지막 100회 변화도 포함합니다.
제어기 보정은 격자·잔차·힘·모멘트 및 격자 간 민감도를 확인한 뒤 진행합니다.

기울기 실험에서 같은 격자의 종료된 해를 초기값으로 재사용할 수 있습니다.
`warm_start.py`는 격자 파일의 해시가 모두 같아야 실행되며, 새로운 기울기의
경계조건을 유지하고 내부 필드만 복사합니다. 초기값 출처를 metadata에 기록합니다.

```sh
uv run python cfd/warm_start.py cfd/cases/layered-v6 cfd/cases/tilt-plus10
uv run python cfd/assess.py
```

OpenFOAM은 `liftDir`와 `dragDir`에서 실제 계수 좌표축을 구성합니다.
이 실험에서 출력된 `pitchAxis`는 본체 −y입니다. 분석기는 설정 파일의 축을
가정하지 않고 **coefficient.dat 헤더의 실제 축**으로 힘과 모멘트를 변환합니다.
그래프와 JSON의 `My`는 본체 +y 기준입니다.
`assessment.json`은 직립 격자 비교와 ±10° 대칭을 별도로 기록하며,
이 실험만으로 자유낙하 모델의 보정을 승인하지 않습니다.

## 경계층·기울기 검증 결과 (2026-10-04)

| 조건 | 셀 수 | 총 반복 | Cd 평균 | 항력 (mN) | 기준 무게중심 My (mN·m) |
|---|---:|---:|---:|---:|---:|
| 경계층 직립 | 137,880 | 2200 | 1.3722 | 97.34 | -0.0001 |
| 단면 세분 직립 | 175,320 | 1200 | 1.3756 | 97.57 | -0.0003 |
| −10° | 137,880 | 1600 | 1.3924 | 98.77 | 0.1816 |
| +10° | 137,880 | 1600 | 1.3916 | 98.71 | -0.1813 |

전체 격자 검사는 네 조건 모두 통과했습니다. 직립 두 격자의 Cd 차이는 0.245%,
±10° 항력의 대칭 차이는 0.058%, 모멘트의 대칭 오차는 0.204%입니다.
두 기울기 모두 기준 무게중심에 대해 복원 방향의 모멘트를 보였습니다.
이는 고정된 돔과 중앙 제어기를 가정한 정적 경향입니다.

**네 조건 모두 최종 잔차 기준 미달**이며, +10°의 마지막 모멘트 평균 변화도
약 2.05%로 2% 기준을 조금 넘었습니다. 작은 격자 간 차이만으로 격자 독립성이나
정확한 종단속도를 확정할 수 없습니다. 기본 격자의 첫 압력 잔차는 약 0.00159,
횡방향 속도 잔차는 약 0.000148로 남았습니다. 후반에는 압력 선형해의 허용오차를
1e-9, relTol을 0으로 강화했지만 바깥 반복 잔차는 해결되지 않았습니다.
이것만으로 물리적 비정상성을 증명한 것은 아닙니다.

다음 검증은 비정상 해법과의 비교, 벽 수직·방위각·영역 크기 민감도입니다.
기존 MuJoCo 공력 계수와 제어기는 이번 예비 결과로 변경하지 않았습니다.
자동 검사 30개와 웹 빌드가 통과했습니다. 보고서의 (i)에서 각 조건의 상태와
대칭 비교를 볼 수 있습니다.

## 실제 시간 URANS 계산

`setup_unsteady.py`는 검사를 통과한 동일 격자와 정상해의 마지막 내부 필드를
새 폴더에 복사하고 시간을 0초로 시작합니다. `pimpleFoam`, backward 시간 차분,
PIMPLE 외부 2회·압력 보정 2회·비직교 보정 1회를 사용합니다.
시간 간격은 Courant 수로 조절합니다. SIMPLE 반복 횟수와 물리 시간을 혼동하지 않습니다.

```sh
uv run python cfd/setup_unsteady.py cfd/cases/layered-v6 cfd/cases/unsteady-new --duration .03 --max-co .35
docker compose -f cfd/compose.yaml run --rm solver \
  'cd /case/unsteady-new && pimpleFoam > log.solver 2>&1'
```

첫 시험: `unsteady-upright`에서 0.03초/414단계, Courant 제한 0.7.
비교 시험: `unsteady-half-step`에서 약 0.005초/139단계, 제한 0.35.
두 시험의 겹치는 초기 구간 시간 가중 평균 Cd 차이는 약 2.06%입니다.
이는 **초기 0.005초만의 비교**이며 장시간 평균의 시간 간격 독립성을 입증하지 않습니다.
장시간 계산은 기존 0.03초 해에서 제한 0.35로 줄여 이어갑니다.
메타데이터에 시간 간격 변경 이력을 남겼습니다.

`unsteady_job.py`는 CPU 1코어로 Docker 해석을 실행하고 10초마다 상태를 원자적으로
저장합니다. 완성된 단면만 복사해 그림을 갱신하며, 볼륨 필드는 최근 2개만 유지합니다.
전체 그래프는 계산된 계수이며 유동 그림에는 실제 저장 시각이 표시됩니다.
대시보드는 `/cfd/unsteady/`에서 5초마다 갱신됩니다.
프로세스와 Docker가 계속 실행되어야 진행됩니다. 컴퓨터가 잠들면 계산이 지연됩니다.

```sh
uv run python cfd/unsteady_job.py cfd/cases/unsteady-upright --duration 2.25
```

목표 2.25초 중 최초 0.75초(5D/U)를 제외하고 이후 1.5초(10D/U)를 평균 평가합니다.
샘플 개수 대신 시간 길이로 가중합니다. 이 구간은 첫 관찰 기준이며 충분한 통계 수렴을
보장하지 않습니다. 실행 종료, 평균 평가 구간 확보, 시간·격자 독립성, 물리 검증을
구분하고 자동 제어기 보정은 항상 비활성화합니다. DNS/LES가 아닌 URANS입니다.

진행 기록: `web/src/cfd/unsteady/live.json`, `cfd/cases/unsteady-upright/log.job`.
중지하려면 해당 case에 `STOP` 파일을 만들면 감시 프로세스가 **자신이 시작한 컨테이너만**
중지합니다. 재개 전 STOP 파일을 제거하고 마지막 저장 시점에서 실행하세요.
비정상 종료 시 마지막 저장 시점 이후 계산은 다시 수행해야 합니다.
완료 시 `unsteady-result.json`에 최종 통계가 저장됩니다.

참고: [OpenFOAM 표준 해석기](https://www.openfoam.com/documentation/user-guide/a-reference/a.1-standard-solvers).

### 1시간 한도의 단기 시험으로 변경

사용자 요청에 따라 현재 목표를 2.25초에서 **0.10초**로 축소했습니다.
격자와 Courant 제한 0.35는 유지합니다. `--deadline <Unix 시각>`은 **최초 시험 시작부터
이미 사용한 시간을 포함해 1시간**으로 설정했습니다. 마감 60초 전에는 저장 후 종료를
요청하고, 종료되지 않으면 마감 직전에 이 작업의 컨테이너만 중지합니다.
대시보드의 예상 잔여 시간은 남은 예산을 넘지 않습니다.
이 단기 시험은 0.75초 과도구간 제외/1.5초 평균 기준에 미달하며, 장시간 평균이나
종단속도 검증으로 해석하지 않습니다. `calibration_ready`는 계속 false입니다.
