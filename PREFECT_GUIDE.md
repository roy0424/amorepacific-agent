# Prefect OSS 사용 가이드

## 🎯 Prefect를 선택한 이유

1. ✅ **완전 무료** - Prefect OSS는 100% 무료입니다
2. ✅ **멋진 UI** - http://localhost:4200 대시보드
3. ✅ **자동 재시도** - Task 실패 시 자동 재시도
4. ✅ **쉬운 사용** - 데코레이터만 추가하면 됨
5. ✅ **공모전 어필** - 프로덕션급 워크플로우 시스템

## 📐 아키텍처

### Flow (워크플로우)
```python
@flow
def amazon_pipeline():
    """전체 아마존 크롤링 파이프라인"""
    data = scrape_amazon()  # Task 1
    validated = validate(data)  # Task 2
    save_to_db(validated)  # Task 3
```

### Task (작업 단위)
```python
@task(retries=3, retry_delay_seconds=60)
def scrape_amazon():
    """실패 시 자동으로 3번 재시도"""
    return scraper.scrape()
```

### Deployment (스케줄링)
```python
# 1시간마다 자동 실행
amazon_pipeline.serve(
    name="amazon-hourly",
    interval=3600
)
```

---

## 🔄 실행 흐름

```
1. prefect server start
   ↓
   UI 서버 시작 (http://localhost:4200)

2. python scripts/deploy_flows.py
   ↓
   Flows 등록 및 스케줄 설정

3. 자동 실행 시작
   ↓
   ┌─ 09:00 Amazon Flow 실행
   │  ├─ Task: Scrape Amazon
   │  ├─ Task: Validate Data
   │  └─ Task: Save to DB
   │
   ┌─ 10:00 Amazon Flow 재실행 (자동)
   │
   └─ UI에서 실시간 모니터링!
```

---

## 🚀 빠른 시작

### 1. 설치
```bash
pip install prefect==2.14.0
```

### 2. 서버 시작
```bash
# 터미널 1
prefect server start
```

### 3. Flow 실행
```bash
# 터미널 2
python -c "from src.flows.amazon_flow import amazon_pipeline; amazon_pipeline()"
```

### 4. UI 확인
```
http://localhost:4200
```

---

## 📁 파일 구조

```
src/
├── flows/              # Prefect Flows
│   ├── amazon_flow.py      # Amazon 크롤링 전체 파이프라인
│   ├── social_flow.py      # 소셜미디어 크롤링 파이프라인
│   ├── insight_flow.py     # 인사이트 생성 파이프라인
│   └── report_flow.py      # 리포트 생성 파이프라인
│
└── tasks/              # Prefect Tasks
    ├── scraping_tasks.py   # 크롤링 관련 Task들
    ├── processing_tasks.py # 데이터 처리 Task들
    └── analysis_tasks.py   # 분석 관련 Task들
```

---

## 💡 핵심 개념

### Flow = 여러 Task의 조합
```python
@flow(name="amazon-pipeline", log_prints=True)
def amazon_pipeline():
    """
    Flow: 전체 워크플로우
    - 여러 Task를 순서대로 실행
    - 의존성 자동 관리
    - 실패 시 전체 롤백
    """
    data = scrape_task()  # Task 1
    processed = process_task(data)  # Task 2 (Task 1에 의존)
    save_task(processed)  # Task 3 (Task 2에 의존)
```

### Task = 재사용 가능한 작업 단위
```python
@task(
    name="scrape-amazon",
    retries=3,  # 실패 시 3번 재시도
    retry_delay_seconds=60,  # 60초 대기 후 재시도
    timeout_seconds=300,  # 5분 타임아웃
    log_prints=True  # print 문을 로그로 기록
)
def scrape_task():
    """
    Task: 개별 작업
    - 자동 재시도
    - 로그 자동 기록
    - 실행 시간 추적
    """
    return scraper.scrape_all_categories()
```

### Deployment = 스케줄링
```python
# scripts/deploy_flows.py

from prefect.deployments import Deployment
from prefect.server.schemas.schedules import IntervalSchedule
from datetime import timedelta

deployment = Deployment.build_from_flow(
    flow=amazon_pipeline,
    name="amazon-hourly",
    schedule=IntervalSchedule(interval=timedelta(hours=1)),
    work_queue_name="default"
)
deployment.apply()
```

---

## 🎨 UI 활용

### 1. Flow Runs 페이지
- 모든 실행 히스토리 확인
- 성공/실패 상태
- 실행 시간

### 2. Flow Run 상세
- 각 Task 별 로그
- 실행 그래프 (Task 의존성 시각화)
- 에러 메시지

### 3. Logs
- 실시간 로그 스트리밍
- 필터링 및 검색

### 4. Deployments
- 등록된 스케줄 확인
- 수동 실행 버튼

---

## 🔧 주요 기능

### 1. 자동 재시도
```python
@task(retries=3, retry_delay_seconds=60)
def unstable_task():
    # 실패해도 자동으로 3번 재시도
    pass
```

### 2. 조건부 실행
```python
@flow
def conditional_flow():
    data = fetch_data()

    if data:
        process_data(data)
    else:
        send_alert()
```

### 3. 병렬 실행
```python
from prefect import flow, task
from prefect.task_runners import ConcurrentTaskRunner

@flow(task_runner=ConcurrentTaskRunner())
def parallel_flow():
    # 동시에 실행됨
    task1.submit()
    task2.submit()
    task3.submit()
```

### 4. 캐싱
```python
from datetime import timedelta

@task(cache_key_fn=..., cache_expiration=timedelta(hours=1))
def cached_task():
    # 1시간 동안 결과 캐싱
    pass
```

---

## 🆚 APScheduler vs Prefect

| 기능 | APScheduler | Prefect OSS |
|------|-------------|-------------|
| UI | ❌ | ✅ |
| 자동 재시도 | 수동 구현 | ✅ |
| 로그 | 파일만 | ✅ UI + 파일 |
| 에러 추적 | 수동 | ✅ 자동 |
| 작업 의존성 | 수동 | ✅ 자동 |
| 실행 히스토리 | 없음 | ✅ UI에서 확인 |
| 공모전 어필 | ⭐⭐ | ⭐⭐⭐⭐⭐ |

---

## 📊 공모전 시연 시나리오

### 1. 시스템 시작
```bash
# 터미널 화면 공유
$ prefect server start
✓ Prefect server started at http://localhost:4200
```

### 2. UI 대시보드 시연
```
브라우저: http://localhost:4200

"실시간으로 크롤링이 진행되는 모습을 확인할 수 있습니다"
- Flow Runs: 250개 제품 수집 완료
- Logs: 실시간 로그 확인
- Graph: Task 의존성 시각화
```

### 3. 에러 처리 시연
```
"실패해도 자동으로 재시도하여 안정적으로 동작합니다"
- UI에서 재시도 히스토리 확인
- 최종 성공까지의 과정 시각화
```

### 4. 인사이트 생성
```
"수집된 데이터를 자동으로 분석하여 인사이트를 생성합니다"
- Insight Flow 실행 확인
- GPT-4 인사이트 생성 로그
```

---

## 💰 비용

**완전 무료!**

- Prefect OSS는 오픈소스
- 로컬에서 실행 (서버 비용 없음)
- 모든 기능 무제한 사용

**Prefect Cloud는 사용하지 않습니다**
- Prefect Cloud = 유료 (클라우드 호스팅)
- Prefect OSS = 무료 (로컬 서버)

---

## 🔗 참고 자료

- [Prefect 공식 문서](https://docs.prefect.io/)
- [Prefect GitHub](https://github.com/PrefectHQ/prefect)
- [Prefect Slack Community](https://prefect.io/slack)

---

## ❓ FAQ

**Q: Prefect Cloud 계정이 필요한가요?**
A: 아니요! Prefect OSS는 완전히 로컬에서 실행됩니다.

**Q: 인터넷 연결이 필요한가요?**
A: 서버 시작에만 필요하고, 이후는 오프라인 가능합니다.

**Q: 팀원들과 공유할 수 있나요?**
A: 네, 같은 네트워크면 IP 주소로 접근 가능합니다.

**Q: 서버가 꺼지면 스케줄도 멈추나요?**
A: 네, 하지만 재시작하면 자동으로 다음 스케줄부터 재개됩니다.

**Q: APScheduler 코드를 재사용할 수 있나요?**
A: 네! 데코레이터만 추가하면 됩니다.
