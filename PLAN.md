# 라네즈 랭킹 이벤트 기반 인사이트 시스템

## 프로젝트 개요

아마존 랭킹 변동을 모니터링하고, **이벤트 발생 시점에만** 원인 분석용 데이터를 수집하여 LLM 기반 인사이트를 제공하는 시스템.

### 핵심 컨셉: Event-Driven Intelligence

**기존 방식의 문제점:**
- 데이터를 무조건 많이 모으는 방식 (비효율적)
- ML 모델 학습에 필요한 충분한 데이터 확보 어려움
- 실질적인 비즈니스 가치 제공 부족

**새로운 접근:**
```
① 랭킹 데이터 주기적 수집 (6시간마다)
    ↓
② 랭킹 변동 이벤트 감지 (순위 급등/급락)
    ↓
③ 이벤트 시점 기준 원인 데이터 집중 수집
   - 소셜미디어 (YouTube, TikTok, Instagram)
   - 리뷰 데이터
   - 경쟁사 동향
    ↓
④ LLM 기반 원인 분석 및 인사이트 도출
    ↓
⑤ 리포트 생성 및 알림
```

**핵심 가치:**
- 💰 **비용 효율**: 이벤트 발생 시에만 집중 수집
- 🎯 **실용성**: 랭킹 변동 원인을 명확히 파악
- 📊 **확장성**: 경쟁사, 리뷰, 뉴스 등 데이터 소스 추가 용이
- 🤖 **자동화**: 이벤트 감지부터 인사이트 생성까지 완전 자동

---

## 시스템 아키텍처

```
┌─────────────────────────────────────────────────────────────┐
│                    Prefect Orchestration                     │
└─────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
   ┌────▼────┐          ┌─────▼─────┐        ┌─────▼──────┐
   │ Flow 1  │          │  Flow 2   │        │  Flow 3    │
   │ Ranking │──event──▶│  Context  │───────▶│  Insight   │
   │ Monitor │          │Collection │        │ Generation │
   └────┬────┘          └─────┬─────┘        └─────┬──────┘
        │                     │                     │
        ▼                     ▼                     ▼
   ┌─────────────────────────────────────────────────────┐
   │              PostgreSQL Database                    │
   │  • amazon_rankings (시계열)                         │
   │  • ranking_events (이벤트 메타데이터)               │
   │  • event_context_social (원인 데이터)               │
   │  • event_insights (LLM 분석 결과)                   │
   └─────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
   ┌────▼────┐          ┌─────▼─────┐        ┌─────▼──────┐
   │ Prefect │          │   Slack   │        │   Excel    │
   │Artifacts│          │   Notify  │        │   Export   │
   └─────────┘          └───────────┘        └────────────┘
```

### Flow 상세 설계

#### Flow 1: Ranking Monitor (주기적 실행)
**실행 주기**: 6시간마다 (or 사용자 설정 가능)

```python
@flow(name="ranking_monitor")
def ranking_monitor_flow():
    # 1. Amazon 랭킹 수집
    rankings = scrape_amazon_rankings()

    # 2. DB 저장
    save_rankings(rankings)

    # 3. 이벤트 감지
    events = detect_ranking_events()

    # 4. 이벤트 발견 시 Flow 2 트리거
    for event in events:
        context_collection_flow.submit(event_id=event.id)
```

**이벤트 감지 기준:**
- 순위 급등: 10위 이상 상승 or 30% 이상 상승
- 순위 급락: 10위 이상 하락 or 30% 이상 하락
- 가격 변동: 20% 이상 변동
- 리뷰 급증: 100개 이상 증가
- 품절 상태 변화

#### Flow 2: Context Collection (이벤트 트리거)
**실행 조건**: 이벤트 감지 시 자동 실행

```python
@flow(name="context_collection")
def context_collection_flow(event_id: int):
    # 1. 이벤트 정보 로드
    event = get_event_info(event_id)

    # 2. 시간 범위 계산
    time_window = calculate_time_window(event)
    # 예: 이벤트 전 7일 ~ 후 3일

    # 3. 원인 데이터 수집 (병렬)
    social_data = collect_social_media(
        product=event.product,
        start_date=time_window.start,
        end_date=time_window.end
    )

    reviews = collect_reviews(
        asin=event.product.asin,
        time_window=time_window
    )

    competitors = collect_competitor_data(
        category=event.category,
        time_window=time_window
    )

    # 4. 데이터 저장 (이벤트와 연결)
    save_event_context(event_id, social_data, reviews, competitors)

    # 5. Flow 3 트리거
    insight_generation_flow.submit(event_id=event_id)
```

#### Flow 3: Insight Generation (LLM 분석)
**실행 조건**: 데이터 수집 완료 후

```python
@flow(name="insight_generation")
def insight_generation_flow(event_id: int):
    # 1. 이벤트 및 수집 데이터 로드
    context = load_event_context(event_id)

    # 2. LLM 프롬프트 구성
    prompt = build_insight_prompt(context)

    # 3. LLM 분석 (Claude/GPT-4)
    insight = generate_llm_insight(prompt)
    # 출력:
    # - 변동 원인 3가지 (우선순위)
    # - 데이터 기반 근거
    # - 권장 액션
    # - 신뢰도 점수

    # 4. 인사이트 저장
    save_insight(event_id, insight)

    # 5. 리포트 생성
    create_event_report_artifact(event_id)

    # 6. 알림 (선택)
    if insight.severity == 'critical':
        send_slack_notification(insight)
```

---

## 데이터베이스 스키마

### 1. 기존 테이블 (유지)

```sql
-- 브랜드 관리
brands (
    id, name, brand_type ['target'|'competitor'],
    keywords[], is_active, created_at
)

-- 아마존 카테고리
amazon_categories (
    id, category_name, category_url, parent_category_id
)

-- 아마존 제품
amazon_products (
    id, asin, product_name, brand_id, product_url,
    first_seen_at, last_seen_at, is_active
)

-- 아마존 랭킹 (시계열 데이터)
amazon_rankings (
    id, product_id, category_id, rank, price, rating,
    review_count, is_prime, stock_status, collected_at,
    INDEX: (product_id, category_id, collected_at DESC)
)
```

### 2. 새로운 테이블 (이벤트 시스템)

```sql
-- 랭킹 이벤트 (변동 감지)
ranking_events (
    id SERIAL PRIMARY KEY,
    product_id INT REFERENCES amazon_products(id),
    category_id INT REFERENCES amazon_categories(id),

    -- 이벤트 타입
    event_type VARCHAR(50),  -- 'RANK_SURGE', 'RANK_DROP', 'PRICE_CHANGE', etc.
    severity VARCHAR(20),    -- 'critical', 'high', 'medium', 'low'

    -- 랭킹 변동
    prev_rank INT,
    curr_rank INT,
    rank_change INT,         -- curr - prev (음수면 상승)
    rank_change_pct FLOAT,   -- 변동 비율

    -- 가격 변동
    prev_price DECIMAL(10,2),
    curr_price DECIMAL(10,2),
    price_change_pct FLOAT,

    -- 리뷰 변동
    prev_review_count INT,
    curr_review_count INT,
    review_change INT,

    -- 시간 정보
    detected_at TIMESTAMP,
    time_window_start TIMESTAMP,  -- 데이터 수집 시작
    time_window_end TIMESTAMP,    -- 데이터 수집 종료

    -- 처리 상태
    context_collected BOOLEAN DEFAULT FALSE,
    insight_generated BOOLEAN DEFAULT FALSE,

    created_at TIMESTAMP DEFAULT NOW(),

    INDEX: (detected_at DESC),
    INDEX: (product_id, detected_at DESC),
    INDEX: (event_type, severity)
)

-- 이벤트 원인 데이터: 소셜미디어
event_context_social (
    id SERIAL PRIMARY KEY,
    event_id INT REFERENCES ranking_events(id) ON DELETE CASCADE,

    platform VARCHAR(20),     -- 'youtube', 'tiktok', 'instagram'
    content_id VARCHAR(255),
    author VARCHAR(255),
    text TEXT,
    hashtags TEXT[],

    -- 메트릭
    view_count BIGINT,
    like_count BIGINT,
    comment_count INT,
    share_count INT,
    engagement_score INT,     -- 통합 engagement 점수

    posted_at TIMESTAMP,
    collected_at TIMESTAMP DEFAULT NOW(),

    -- 바이럴 여부
    is_viral BOOLEAN,         -- engagement 임계값 기준

    INDEX: (event_id, engagement_score DESC)
)

-- 이벤트 원인 데이터: 리뷰
event_context_reviews (
    id SERIAL PRIMARY KEY,
    event_id INT REFERENCES ranking_events(id) ON DELETE CASCADE,

    review_id VARCHAR(255),
    reviewer_name VARCHAR(255),
    rating INT,
    verified_purchase BOOLEAN,
    review_title TEXT,
    review_text TEXT,
    helpful_count INT,
    review_date TIMESTAMP,
    collected_at TIMESTAMP DEFAULT NOW(),

    -- 감성 분석 (선택)
    sentiment VARCHAR(20),    -- 'positive', 'negative', 'neutral'
    sentiment_score FLOAT,

    INDEX: (event_id, review_date DESC)
)

-- 이벤트 원인 데이터: 경쟁사
event_context_competitors (
    id SERIAL PRIMARY KEY,
    event_id INT REFERENCES ranking_events(id) ON DELETE CASCADE,

    competitor_product_id INT REFERENCES amazon_products(id),
    competitor_rank INT,
    competitor_price DECIMAL(10,2),
    competitor_rating FLOAT,
    rank_change INT,
    price_change_pct FLOAT,

    collected_at TIMESTAMP DEFAULT NOW(),

    INDEX: (event_id)
)

-- LLM 인사이트 결과
event_insights (
    id SERIAL PRIMARY KEY,
    event_id INT REFERENCES ranking_events(id) ON DELETE CASCADE,

    -- 인사이트 내용
    insight_type VARCHAR(50),     -- 'ranking_change', 'viral_correlation', etc.
    summary TEXT,                 -- 요약 (2-3문장)

    -- 원인 분석 (JSON)
    causes JSONB,                 -- [{cause: "...", evidence: "...", confidence: 0.85}]

    -- 데이터 근거
    evidence JSONB,               -- {social: [...], reviews: [...], competitors: [...]}

    -- 권장 액션
    recommendations JSONB,        -- [{action: "...", priority: "high", expected_impact: "..."}]

    -- 신뢰도
    confidence_score FLOAT,       -- 0-1

    -- 메타데이터
    llm_model VARCHAR(50),        -- 'claude-3-5-sonnet', 'gpt-4', etc.
    prompt_tokens INT,
    completion_tokens INT,

    generated_at TIMESTAMP DEFAULT NOW(),

    INDEX: (event_id),
    INDEX: (generated_at DESC)
)
```

---

## 이벤트 감지 로직 상세

### Event Detection Algorithm

```python
def detect_ranking_events(
    product_id: int,
    category_id: int,
    lookback_hours: int = 12
) -> List[RankingEvent]:
    """
    랭킹 변동 이벤트를 감지합니다.

    감지 기준:
    1. 순위 급등: 10위 이상 상승 or 30% 이상 상승
    2. 순위 급락: 10위 이상 하락 or 30% 이상 하락
    3. 가격 변동: 20% 이상 변동
    4. 리뷰 급증: 100개 이상 증가 (in 12h)
    5. 품절 상태 변화: in_stock ↔ out_of_stock
    """

    # 최근 2개 데이터 포인트 가져오기
    current = get_latest_ranking(product_id, category_id)
    previous = get_previous_ranking(product_id, category_id, hours_ago=lookback_hours)

    events = []

    # 1. 순위 변동 체크
    if previous and current:
        rank_change = current.rank - previous.rank
        rank_change_pct = abs(rank_change) / previous.rank * 100

        if rank_change <= -10 or rank_change_pct >= 30:  # 상승 (숫자 감소)
            events.append(RankingEvent(
                event_type='RANK_SURGE',
                severity=calculate_severity(rank_change_pct),
                rank_change=rank_change,
                rank_change_pct=rank_change_pct
            ))

        elif rank_change >= 10 or rank_change_pct >= 30:  # 하락
            events.append(RankingEvent(
                event_type='RANK_DROP',
                severity=calculate_severity(rank_change_pct),
                rank_change=rank_change,
                rank_change_pct=rank_change_pct
            ))

        # 2. 가격 변동 체크
        if previous.price and current.price:
            price_change_pct = abs(
                (current.price - previous.price) / previous.price * 100
            )

            if price_change_pct >= 20:
                events.append(RankingEvent(
                    event_type='PRICE_CHANGE',
                    severity='high' if price_change_pct >= 40 else 'medium',
                    price_change_pct=price_change_pct
                ))

        # 3. 리뷰 급증 체크
        review_change = current.review_count - previous.review_count
        if review_change >= 100:
            events.append(RankingEvent(
                event_type='REVIEW_SURGE',
                severity='high',
                review_change=review_change
            ))

        # 4. 품절 상태 변화
        if previous.stock_status != current.stock_status:
            events.append(RankingEvent(
                event_type='STOCK_CHANGE',
                severity='critical' if current.stock_status == 'out_of_stock' else 'medium'
            ))

    return events


def calculate_severity(change_pct: float) -> str:
    """변동 폭에 따라 심각도 계산"""
    if change_pct >= 70:
        return 'critical'
    elif change_pct >= 50:
        return 'high'
    elif change_pct >= 30:
        return 'medium'
    else:
        return 'low'


def calculate_time_window(event: RankingEvent) -> TimeWindow:
    """
    이벤트 기준으로 데이터 수집 시간 범위 계산

    전략:
    - 이벤트 발생 전 7일: 트렌드 파악
    - 이벤트 발생 후 3일: 영향 확인
    """
    return TimeWindow(
        start=event.detected_at - timedelta(days=7),
        end=event.detected_at + timedelta(days=3)
    )
```

---

## LLM Insight Generation

### Prompt Engineering

```python
INSIGHT_PROMPT_TEMPLATE = """
당신은 전자상거래 랭킹 분석 전문가입니다.

## 이벤트 정보
- 제품: {product_name} (ASIN: {asin})
- 카테고리: {category_name}
- 이벤트 타입: {event_type}
- 랭킹 변동: {prev_rank} → {curr_rank} ({rank_change:+d})
- 가격 변동: ${prev_price} → ${curr_price} ({price_change_pct:+.1f}%)
- 리뷰 변동: {prev_reviews} → {curr_reviews} (+{review_change})
- 감지 시점: {detected_at}

## 수집된 원인 데이터

### 소셜미디어 활동 (이벤트 전후 7일)
{social_media_summary}

Top 5 바이럴 콘텐츠:
{top_viral_content}

### 리뷰 분석
- 신규 리뷰 수: {new_reviews_count}
- 평균 평점: {avg_rating}
- 감성 분포: 긍정 {positive_pct}%, 부정 {negative_pct}%

주요 리뷰 키워드:
{review_keywords}

### 경쟁사 동향
{competitor_changes}

## 분석 요청

다음 형식의 JSON으로 응답해주세요:

{{
  "summary": "2-3문장으로 요약",
  "causes": [
    {{
      "cause": "원인 설명",
      "evidence": "데이터 기반 근거",
      "confidence": 0.0-1.0
    }}
  ],
  "recommendations": [
    {{
      "action": "권장 액션",
      "priority": "high|medium|low",
      "expected_impact": "예상 효과"
    }}
  ],
  "confidence_score": 0.0-1.0
}}

**중요**:
1. 원인은 수집된 데이터에 기반해야 함 (추측 금지)
2. 상위 3개 원인만 제시 (우선순위 순)
3. 신뢰도 점수는 데이터 품질과 상관관계 강도 고려
"""


def generate_llm_insight(event_id: int) -> EventInsight:
    """LLM을 사용해 이벤트 인사이트 생성"""

    # 1. 컨텍스트 데이터 로드
    context = load_event_context(event_id)

    # 2. 소셜미디어 요약 생성
    social_summary = summarize_social_media(context.social_data)
    top_viral = format_top_viral_content(context.social_data, limit=5)

    # 3. 리뷰 분석
    review_analysis = analyze_reviews(context.reviews)

    # 4. 경쟁사 변동 요약
    competitor_summary = summarize_competitor_changes(context.competitors)

    # 5. 프롬프트 구성
    prompt = INSIGHT_PROMPT_TEMPLATE.format(
        product_name=context.event.product.name,
        asin=context.event.product.asin,
        category_name=context.event.category.name,
        event_type=context.event.event_type,
        prev_rank=context.event.prev_rank,
        curr_rank=context.event.curr_rank,
        rank_change=context.event.rank_change,
        prev_price=context.event.prev_price,
        curr_price=context.event.curr_price,
        price_change_pct=context.event.price_change_pct,
        prev_reviews=context.event.prev_review_count,
        curr_reviews=context.event.curr_review_count,
        review_change=context.event.review_change,
        detected_at=context.event.detected_at.strftime('%Y-%m-%d %H:%M'),
        social_media_summary=social_summary,
        top_viral_content=top_viral,
        new_reviews_count=review_analysis.new_count,
        avg_rating=review_analysis.avg_rating,
        positive_pct=review_analysis.positive_pct,
        negative_pct=review_analysis.negative_pct,
        review_keywords=review_analysis.top_keywords,
        competitor_changes=competitor_summary
    )

    # 6. LLM 호출
    response = call_llm(
        prompt=prompt,
        model="claude-3-5-sonnet-20241022",
        temperature=0.3,
        max_tokens=2000
    )

    # 7. JSON 파싱 및 검증
    insight_data = parse_and_validate_insight(response)

    # 8. 인사이트 객체 생성
    insight = EventInsight(
        event_id=event_id,
        insight_type='ranking_change',
        summary=insight_data['summary'],
        causes=insight_data['causes'],
        recommendations=insight_data['recommendations'],
        confidence_score=insight_data['confidence_score'],
        llm_model="claude-3-5-sonnet",
        prompt_tokens=response.usage.input_tokens,
        completion_tokens=response.usage.output_tokens
    )

    return insight
```

---

## 구현 단계

### Phase 1: 이벤트 감지 시스템 (1주)

**목표**: 랭킹 모니터링 및 이벤트 감지 자동화

1. **DB 스키마 업데이트**
   - `ranking_events` 테이블 추가
   - Alembic 마이그레이션 생성
   ```bash
   alembic revision --autogenerate -m "Add ranking events table"
   alembic upgrade head
   ```

2. **이벤트 감지 로직 구현**
   - `src/analyzers/event_detector.py` 생성
   - `detect_ranking_events()` 함수 구현
   - 감지 기준 설정 (config/settings.py)

3. **Ranking Monitor Flow 구현**
   - `src/flows/ranking_monitor_flow.py` 생성
   - Amazon 랭킹 수집 + 이벤트 감지
   - Prefect 스케줄 설정 (6시간마다)

4. **테스트**
   - 수동으로 랭킹 데이터 변경해서 이벤트 감지 확인
   - 이벤트 타입별 테스트 케이스 작성

**검증 체크리스트**:
- [ ] 랭킹 급등/급락 이벤트 자동 감지
- [ ] 이벤트 메타데이터 DB 저장
- [ ] 심각도(severity) 정확히 분류
- [ ] Prefect UI에서 감지된 이벤트 확인

---

### Phase 2: 원인 데이터 수집 (1-2주)

**목표**: 이벤트 발생 시 원인 분석용 데이터 자동 수집

1. **DB 스키마 추가**
   - `event_context_social` 테이블
   - `event_context_reviews` 테이블
   - `event_context_competitors` 테이블

2. **시간 범위 기반 소셜미디어 수집 수정**
   - 기존 `social_flow.py` 수정
   - 파라미터 추가: `start_date`, `end_date`
   - 예: 이벤트 전 7일 ~ 후 3일 데이터만 수집

3. **리뷰 수집 구현** (새로운 기능)
   - `src/scrapers/amazon/review_scraper.py` 생성
   - Apify Amazon Review Scraper 사용
   - 특정 기간 리뷰만 수집

4. **경쟁사 데이터 수집**
   - 같은 카테고리의 경쟁 제품 랭킹 수집
   - 변동 비교 분석

5. **Context Collection Flow 구현**
   - `src/flows/context_collection_flow.py` 생성
   - 이벤트 ID 받아서 병렬 데이터 수집
   - 모든 데이터를 `event_id`와 연결해서 저장

**검증 체크리스트**:
- [ ] 이벤트 감지 시 자동으로 데이터 수집 시작
- [ ] 지정된 시간 범위 내 데이터만 수집
- [ ] 소셜미디어, 리뷰, 경쟁사 데이터 모두 연결
- [ ] `event_context_*` 테이블에 데이터 저장

---

### Phase 3: LLM 인사이트 생성 (1주)

**목표**: 수집된 데이터를 LLM으로 분석하여 인사이트 도출

1. **DB 스키마 추가**
   - `event_insights` 테이블

2. **LLM 클라이언트 설정**
   - `src/insights/llm_client.py` 업데이트
   - Claude API 또는 OpenAI API 선택

3. **프롬프트 엔지니어링**
   - `src/insights/prompts.py` 생성
   - 랭킹 변동 분석 프롬프트 템플릿
   - JSON 출력 형식 정의

4. **인사이트 생성 로직**
   - `src/insights/event_insight_generator.py` 생성
   - 컨텍스트 데이터 요약
   - LLM 호출 및 응답 파싱
   - 신뢰도 점수 계산

5. **Insight Generation Flow 구현**
   - `src/flows/insight_generation_flow.py` 생성
   - 데이터 수집 완료 후 자동 실행
   - 인사이트 DB 저장

6. **Prefect Artifacts 생성**
   - 이벤트 리포트 (Markdown)
   - 원인 분석 차트 (Table)
   - 권장 액션 (Markdown)

**검증 체크리스트**:
- [ ] LLM이 데이터 기반으로 원인 분석
- [ ] JSON 형식으로 구조화된 인사이트 생성
- [ ] 신뢰도 점수 합리적으로 계산
- [ ] Prefect UI에서 인사이트 리포트 확인
- [ ] 3개 샘플 이벤트 인사이트 품질 평가

---

### Phase 4: 리포트 & 알림 (1주)

**목표**: 인사이트를 시각화하고 중요 이벤트 알림

1. **Prefect Artifacts 고도화**
   - 이벤트 타임라인 차트
   - 소셜미디어 engagement 추이 그래프
   - 경쟁사 비교 테이블

2. **Excel 리포트 생성**
   - `src/reports/event_report_generator.py` 생성
   - 이벤트 요약 시트
   - 원인 데이터 시트
   - 인사이트 시트

3. **Slack 알림 연동** (선택)
   - `src/services/notification_service.py` 생성
   - Critical/High 이벤트만 알림
   - 인사이트 요약 포함

4. **대시보드 조회 API** (선택)
   - FastAPI 간단한 엔드포인트
   - 최근 이벤트 목록
   - 이벤트 상세 정보

**검증 체크리스트**:
- [ ] Prefect UI에서 시각화된 리포트 확인
- [ ] Excel 파일 다운로드 및 내용 확인
- [ ] Slack 알림 정상 작동 (선택)
- [ ] 히스토리 조회 가능

---

### Phase 5: 확장 (선택, 1-2주)

**목표**: 데이터 소스 확장 및 고도화

1. **경쟁사 추가**
   - 여러 브랜드 동시 모니터링
   - 브랜드별 이벤트 비교

2. **뉴스/PR 데이터 수집**
   - Google News API
   - 브랜드 언급 기사 수집
   - 이벤트와 연결

3. **감성 분석**
   - 리뷰 감성 분석 (긍정/부정)
   - 소셜미디어 댓글 감성 분석

4. **예측 모델**
   - 과거 이벤트 학습
   - 랭킹 변동 예측

---

## 디렉토리 구조

```
laneige-ranking-tracker/
├── config/
│   ├── settings.py              # 중앙 설정
│   ├── event_thresholds.py      # 이벤트 감지 임계값
│   └── categories.json
│
├── src/
│   ├── core/
│   │   ├── database.py
│   │   └── logging.py
│   │
│   ├── models/
│   │   ├── amazon.py            # 기존 모델
│   │   ├── events.py            # ⭐ 이벤트 관련 모델 (신규)
│   │   ├── social_media.py
│   │   └── brands.py
│   │
│   ├── scrapers/
│   │   ├── amazon/
│   │   │   ├── ranking_scraper.py
│   │   │   └── review_scraper.py  # ⭐ 리뷰 수집 (신규)
│   │   └── social/
│   │       ├── youtube_apify.py
│   │       ├── tiktok_apify.py
│   │       └── instagram_apify.py
│   │
│   ├── analyzers/
│   │   ├── event_detector.py    # ⭐ 이벤트 감지 (핵심)
│   │   └── data_summarizer.py   # 수집 데이터 요약
│   │
│   ├── insights/
│   │   ├── event_insight_generator.py  # ⭐ LLM 인사이트 (핵심)
│   │   ├── prompts.py           # 프롬프트 템플릿
│   │   └── llm_client.py
│   │
│   ├── flows/
│   │   ├── ranking_monitor_flow.py     # ⭐ Flow 1 (핵심)
│   │   ├── context_collection_flow.py  # ⭐ Flow 2 (핵심)
│   │   ├── insight_generation_flow.py  # ⭐ Flow 3 (핵심)
│   │   └── social_flow.py       # 기존 (수정)
│   │
│   ├── tasks/
│   │   ├── amazon_tasks.py
│   │   ├── social_tasks.py
│   │   └── event_tasks.py       # ⭐ 이벤트 관련 태스크
│   │
│   ├── reports/
│   │   ├── event_report_generator.py  # ⭐ 이벤트 리포트
│   │   └── artifact_creator.py
│   │
│   └── services/
│       ├── notification_service.py  # Slack 알림
│       └── time_window_calculator.py
│
├── scripts/
│   ├── init_db.py
│   ├── migrate_to_event_system.py  # 기존 데이터 마이그레이션
│   ├── run_ranking_monitor.py      # ⭐ 메인 실행 파일
│   ├── test_event_detection.py     # 이벤트 감지 테스트
│   └── export_ml_dataset.py        # 기존 (유지)
│
├── data/
│   ├── logs/
│   ├── reports/                # 이벤트 리포트 Excel
│   └── datasets/               # ML 데이터셋
│
├── alembic/                    # DB 마이그레이션
│   └── versions/
│
├── requirements.txt
├── .env
└── README.md
```

---

## 기술 스택

| 구분 | 기술 | 용도 |
|------|------|------|
| **Orchestration** | Prefect 3.x | Flow 오케스트레이션, 스케줄링, Artifacts |
| **Database** | PostgreSQL + SQLAlchemy | 시계열 데이터, JSONB 지원 |
| **Scraping** | Apify (우선), Playwright (백업) | Amazon, 소셜미디어, 리뷰 수집 |
| **LLM** | Claude 3.5 Sonnet (or GPT-4) | 인사이트 생성 |
| **YouTube** | YouTube Data API v3 | 공식 API |
| **TikTok** | Apify TikTok Scraper | 비공식 크롤링 |
| **Instagram** | Apify Instagram Scraper | 해시태그 검색 |
| **Logging** | Loguru | 구조화된 로깅 |
| **Export** | Pandas + openpyxl | Excel 리포트 |

---

## 환경 변수 (.env)

```bash
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/laneige_tracker

# Apify
APIFY_API_KEY=apify_api_...

# YouTube
YOUTUBE_API_KEY=AIza...

# Claude API (or OpenAI)
ANTHROPIC_API_KEY=sk-ant-...
# OPENAI_API_KEY=sk-...

# Event Detection Thresholds
EVENT_RANK_CHANGE_THRESHOLD=10
EVENT_RANK_CHANGE_PCT_THRESHOLD=30.0
EVENT_PRICE_CHANGE_PCT_THRESHOLD=20.0
EVENT_REVIEW_SURGE_THRESHOLD=100

# Time Windows
EVENT_LOOKBACK_DAYS=7
EVENT_LOOKFORWARD_DAYS=3

# Prefect
PREFECT_API_URL=http://localhost:4200/api

# Notification (선택)
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...

# Logging
LOG_LEVEL=INFO
```

---

## 실행 방법

### 1. 초기 설정

```bash
# 가상환경
python -m venv venv
source venv/bin/activate

# 의존성 설치
pip install -r requirements.txt

# 환경 변수
cp .env.example .env
# .env 편집

# DB 마이그레이션
alembic upgrade head

# 초기 데이터 시딩
python scripts/init_db.py
```

### 2. Prefect 설정

```bash
# Prefect 서버 시작
prefect server start

# Flow 등록 및 배포
python scripts/run_ranking_monitor.py
```

### 3. 수동 테스트

```bash
# 랭킹 수집 + 이벤트 감지 테스트
python scripts/test_event_detection.py

# 특정 이벤트 인사이트 생성 테스트
python scripts/test_event_detection.py --event-id 1
```

### 4. 프로덕션 실행

Prefect 스케줄이 자동으로 실행:
- **Ranking Monitor Flow**: 6시간마다
- **Context Collection Flow**: 이벤트 감지 시 자동
- **Insight Generation Flow**: 데이터 수집 완료 시 자동

---

## 성공 지표

1. **이벤트 감지 정확도**
   - 실제 중요한 랭킹 변동 90% 이상 감지
   - False Positive < 10%

2. **인사이트 품질**
   - LLM 인사이트가 실제 원인 설명 가능
   - 데이터 기반 근거 제시
   - 실행 가능한 권장 액션 제공

3. **시스템 안정성**
   - Flow 성공률 > 95%
   - 이벤트 감지 → 인사이트 생성 E2E 시간 < 30분

4. **비즈니스 가치**
   - 랭킹 변동 원인 파악 시간 단축 (수동 분석 vs 자동)
   - 실행 가능한 인사이트 제공

---

## 향후 확장 방향

### 단기 (1-2개월)
- 경쟁사 브랜드 추가 (Innisfree, Sulwhasoo 등)
- Google News API 연동 (PR/뉴스 이벤트)
- 리뷰 감성 분석 고도화

### 중기 (3-6개월)
- 랭킹 변동 예측 모델
- 실시간 알림 시스템 (Slack, Email)
- Streamlit 대시보드

### 장기 (6개월+)
- 다중 마켓플레이스 (Walmart, Target 등)
- A/B 테스트 분석 (가격 변동 실험)
- 경쟁 포지셔닝 자동 분석

---

## 다음 단계

1. ✅ 새로운 플랜 리뷰 및 승인
2. Phase 1 시작: DB 스키마 업데이트 + 이벤트 감지
3. Phase 2: 원인 데이터 수집 Flow 구현
4. Phase 3: LLM 인사이트 생성
5. Phase 4: 리포트 & 알림
