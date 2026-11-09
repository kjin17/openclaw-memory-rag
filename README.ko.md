# 에이전트 기억 검색을 재고 다듬기

[OpenClaw](https://docs.openclaw.ai) 내장 기억 검색(RAG)을 에이전트의 장기 기억으로 어떻게
쓰고, 어떻게 재고, 측정이 무엇을 보여 줬는지(이전 주장을 반증한 결과 포함)를 정리한 기술
화이트페이퍼입니다.

**화이트페이퍼: [`docs/whitepaper.ko.md`](docs/whitepaper.ko.md)** (2026-11-09 판)
· English(정본): [`README.md`](README.md), [`docs/whitepaper.md`](docs/whitepaper.md)

---

## 요약

- **구성.** 마크다운 볼트를 OpenClaw 기억 검색으로 색인: `llama.cpp` 로컬
  `embeddinggemma-300m` 임베딩, SQLite FTS5, 시간 감쇠와 MMR 이 붙은 하이브리드 랭킹.
  지식은 개념당 큐레이션 노트 하나로 나눕니다.
- **방법.** 튜닝 전에 쓴 25문항 평가셋을 변경마다 전부 다시 돌림(45회차). 보류셋, 고정
  기준선 회귀 점검, 낡은 값 탐침, 배포 랭킹 코드의 오프라인 복제를 함께 씁니다.
- **결과.**
  - 지식을 큐레이션 노트로 나누자 한 회차에 **40% → 88%**.
  - 그 뒤 지배 변수는 한 파일이 상위 5칸 중 몇 칸을 먹는가(2.03칸 → 84%, 1.33칸 → 92%).
  - 혼합 가중치·MMR·30일 감쇠는 상수. 탐침에서 항상 켜진 두 단계의 대가는 17문항 중 약 3.
  - 감쇠는 큐레이션 노트에만 걸리고, 그 나이를 고정하자 2026.9.7 에서 원 문항 44% → 92%.
  - 타입 그래프 링크 자체의 검색 효과는 입증되지 않음.
  - 2026-11-03 이후: 문서 정리로 값이 바뀐 사실 15개 중 1위 청크가 옛값인 문항이 7 → 4,
    줄 안 정정 표지로 정정 없는 옛 주장 노출이 20질의 중 4 → 0.
- **한계.** 코퍼스·모델 n = 1, 판이 다른 숫자는 비교하지 않음. 반증된 주장은 지우지 않고
  표시와 날짜를 남김.

## 구성

| 문서 | 내용 |
|---|---|
| [`docs/whitepaper.ko.md`](docs/whitepaper.ko.md) | 초록, 배경, 구조, 방법, 결과, 한계와 반증, 재현 방법 |
| [`docs/evaluation-method.md`](docs/evaluation-method.md) | 부록 A: 평가 방법 상세(영문) |
| [`docs/ontology-schema.md`](docs/ontology-schema.md) | 부록 B: 노트 스키마와 비용(영문) |
| [`tools/index_census.py`](tools/index_census.py) | OpenClaw 기억 색인의 파일별 청크 점유 계기 |
| [`tools/evalset_run.py`](tools/evalset_run.py) | 회차 러너(문항만 본인 것으로 교체) |
| [`CHANGELOG.md`](CHANGELOG.md) | 변경 이력 |

예전 `docs/findings.md` 는 이제 화이트페이퍼 절을 가리킵니다. 발견 식별자(A1, B1, G2, H …)는
그대로입니다.

---

MIT. 반박하는 측정을 특히 환영합니다.
