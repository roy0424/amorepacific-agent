# 🧪 프롬프트 테스터 사용 가이드

팀원들이 다양한 프롬프트를 테스트하고 최적의 인사이트 생성 방식을 찾을 수 있는 웹 UI입니다.

## 📋 목차

1. [설치](#설치)
2. [실행 방법](#실행-방법)
3. [기능 소개](#기능-소개)
4. [프롬프트 템플릿 관리](#프롬프트-템플릿-관리)
5. [사용 예시](#사용-예시)
6. [FAQ](#faq)

---

## 설치

### 1. 의존성 설치

```bash
pip install streamlit==1.40.2
```

또는 전체 requirements 재설치:

```bash
pip install -r requirements.txt
```

### 2. OpenAI API 키 설정

`.env` 파일에 OpenAI API 키를 추가하세요:

```env
OPENAI_API_KEY=sk-proj-...your-key...
```

또는 UI에서 직접 입력할 수도 있습니다.

---

## 실행 방법

### 방법 1: 스크립트 실행 (권장)

```bash
python scripts/run_prompt_tester.py
```

### 방법 2: Streamlit 직접 실행

```bash
streamlit run ui/prompt_tester.py
```

실행하면 자동으로 브라우저가 열립니다:
- URL: http://localhost:8501

---

## 기능 소개

### 1. 📊 단일 테스트

**용도**: 하나의 프롬프트로 인사이트를 생성하고 평가

**사용법**:
1. 이벤트 선택 (드롭다운에서 선택)
2. 프롬프트 템플릿 선택 (버튼 클릭)
3. "인사이트 생성" 클릭
4. 결과 확인 및 평가

**결과 화면**:
- 생성된 인사이트 전문
- 사용된 토큰 수
- 예상 비용 (USD)
- 생성 시간

**평가 기능**:
- 품질 평점 (1-5점)
- 유용성 평가
- 피드백 작성

### 2. 🔀 비교 테스트

**용도**: 여러 프롬프트를 동시에 실행하여 결과 비교

**사용법**:
1. 이벤트 선택
2. 비교할 템플릿 2-4개 선택
3. "비교 인사이트 생성" 클릭
4. Side-by-side로 결과 비교

**장점**:
- 한 번에 여러 스타일 비교
- 비용/품질 트레이드오프 확인
- 이벤트 타입별 최적 템플릿 발견

### 3. 📈 결과 분석

**용도**: 축적된 평가 데이터 분석 (개발 예정)

**계획 중인 기능**:
- 템플릿별 평균 평점
- 토큰 사용량/비용 통계
- 이벤트 타입별 추천 템플릿
- 시간대별 생성 이력

---

## 프롬프트 템플릿 관리

템플릿은 `config/prompt_templates.yaml`에 정의되어 있습니다.

### 기본 제공 템플릿

| 템플릿 | 설명 | 적합한 용도 |
|--------|------|------------|
| **Basic** | 간결한 분석 | 빠른 확인, 일상적인 이벤트 |
| **Detailed** | 상세 분석 | 중요 이벤트, 의사결정 필요 시 |
| **Marketing Focus** | 마케팅 액션 | 캠페인 기획, 실행 전략 |
| **Competitive** | 경쟁사 비교 | 시장 포지셔닝, 경쟁 분석 |
| **Data-Driven** | 정량적 분석 | 보고서 작성, 수치 중심 분석 |
| **Bullet Points** | 불릿 포인트 | 임원 브리핑, 빠른 스캔 |

### 새 템플릿 추가하기

`config/prompt_templates.yaml` 파일을 편집:

```yaml
templates:
  my_custom_template:
    name: "Custom - 나만의 템플릿"
    description: "특정 목적을 위한 커스텀 프롬프트"
    system_prompt: |
      시스템 역할 정의...
    user_prompt: |
      Event Details:
      - Product: {product_name}
      - Ranking: {prev_rank} → {curr_rank}

      분석 요청사항...
```

**사용 가능한 변수**:
```python
{product_name}        # 제품명
{asin}               # Amazon ASIN
{category_name}      # 카테고리명
{prev_rank}          # 이전 순위
{curr_rank}          # 현재 순위
{rank_change}        # 순위 변동 (음수 = 상승)
{rank_change_pct}    # 순위 변동 퍼센트
{event_type}         # 이벤트 타입
{severity}           # 심각도
{detected_at}        # 감지 시간
{consistency}        # 트렌드 일관성
{price_change_pct}   # 가격 변동
{current_price}      # 현재 가격
{review_count_change}# 리뷰 수 변동
{rating}             # 평점
{social_context}     # 소셜 미디어 컨텍스트
{trend_info}         # 트렌드 정보
```

---

## 사용 예시

### 시나리오 1: 급등 이벤트 분석

**상황**: Laneige Lip Mask가 15위 → 7위로 급등

**단계**:
1. UI에서 해당 이벤트 선택
2. "Marketing Focus" 템플릿 선택
3. 인사이트 생성
4. 결과: "TikTok 바이럴 영향, 프로모션 확대 추천"
5. 평가: 5점 (매우 유용)

### 시나리오 2: 프롬프트 A/B 테스트

**목적**: "Detailed" vs "Marketing Focus" 어느 것이 더 유용한가?

**단계**:
1. "비교 테스트" 탭 이동
2. 같은 이벤트에 두 템플릿 선택
3. 동시 생성
4. Side-by-side 비교
5. 각각 평가하여 우승자 결정

**결과 예시**:
- Detailed: 4점 (깊이 있지만 길어서 읽기 부담)
- Marketing: 5점 (실행 가능한 액션 아이템 명확)
- 결론: 일상 이벤트는 Marketing 템플릿 사용

### 시나리오 3: 새 템플릿 개발

**목적**: CEO 보고용 초간결 요약 템플릿 만들기

**단계**:
1. `config/prompt_templates.yaml` 편집
2. 새 템플릿 추가:
   ```yaml
   ceo_brief:
     name: "CEO Brief - 임원 보고"
     description: "1문장 요약 + 즉시 액션"
     system_prompt: "You are an executive assistant preparing CEO briefing."
     user_prompt: |
       {product_name}: {prev_rank}→{curr_rank}

       Provide:
       1. One sentence summary
       2. One action to take today
   ```
3. UI 새로고침 (F5)
4. 새 템플릿으로 테스트
5. 평가하여 개선

---

## FAQ

### Q1: API 키 없이 테스트할 수 있나요?

**A**: 아니요, OpenAI API 키가 필수입니다. `.env` 파일에 설정하거나 UI에서 입력하세요.

### Q2: 비용이 얼마나 드나요?

**A**: GPT-4o 기준:
- 단일 인사이트: $0.01 ~ $0.03 (1-3센트)
- 비교 테스트 (4개): $0.04 ~ $0.12
- 일일 100번 테스트: ~$2-3

**절약 팁**: 초기 테스트는 `gpt-3.5-turbo` 사용 (10배 저렴)

### Q3: 이벤트가 없다고 나와요

**A**: 데이터가 아직 수집되지 않았습니다.

```bash
# 데이터 확인
python scripts/check_data.py

# 시스템 시작 (자동 수집)
python scripts/start_all.py
```

12시간 후 이벤트가 감지됩니다.

### Q4: 템플릿을 수정했는데 반영이 안 돼요

**A**: 브라우저에서 **F5 (새로고침)** 또는 **Ctrl+R**을 누르세요.

Streamlit은 코드 변경을 자동 감지하지만, YAML 파일 변경은 새로고침이 필요합니다.

### Q5: 생성된 인사이트가 마음에 안 들어요

**A**: 다음을 시도하세요:
1. **다른 템플릿 사용**: 6가지 스타일 제공
2. **Temperature 조정**:
   - 낮음 (0.1-0.3): 일관적, 사실적
   - 높음 (0.7-1.0): 창의적, 다양
3. **프롬프트 수정**: `prompt_templates.yaml` 편집
4. **모델 변경**: gpt-4o → gpt-4-turbo (더 강력)

### Q6: 평가 데이터는 어디에 저장되나요?

**A**: 현재 버전(v1.0)에서는 **저장되지 않습니다** (세션 종료 시 사라짐).

추후 업데이트에서 DB 저장 기능이 추가될 예정입니다.

### Q7: 팀원들과 결과를 공유하고 싶어요

**A**: 현재 방법:
1. **스크린샷**: 결과 화면 캡처
2. **복사-붙여넣기**: 인사이트 텍스트 복사
3. **Slack/이메일**: 공유

추후 업데이트:
- 결과 내보내기 (PDF, Excel)
- 공유 링크 생성
- 팀 협업 기능

---

## 고급 사용법

### 모델 선택 가이드

| 모델 | 속도 | 품질 | 비용 | 추천 용도 |
|------|------|------|------|----------|
| gpt-3.5-turbo | ⚡️⚡️⚡️ | ⭐️⭐️⭐️ | 💰 | 초기 테스트, 대량 생성 |
| gpt-4o | ⚡️⚡️ | ⭐️⭐️⭐️⭐️ | 💰💰 | 일상 업무 (권장) |
| gpt-4-turbo | ⚡️ | ⭐️⭐️⭐️⭐️⭐️ | 💰💰💰 | 중요 이벤트, 최고 품질 |

### Temperature 가이드

```
0.0 - 0.3: 사실 기반 분석 (권장)
  - 일관된 결과
  - 반복 실행 시 유사
  - 보고서, 문서화

0.4 - 0.7: 균형잡힌 분석
  - 약간의 창의성
  - 다양한 관점
  - 브레인스토밍

0.8 - 2.0: 창의적 분석
  - 예상치 못한 인사이트
  - 결과 변동성 높음
  - 탐색적 분석
```

### 프롬프트 엔지니어링 팁

1. **명확한 역할 정의**
   ```yaml
   system_prompt: |
     You are a [specific role] with expertise in [domain].
     Your goal is to [clear objective].
   ```

2. **구조화된 출력 요청**
   ```yaml
   user_prompt: |
     Please provide:
     1. Summary (2-3 sentences)
     2. Analysis (bullet points)
     3. Recommendations (numbered list)
   ```

3. **예시 제공** (Few-shot learning)
   ```yaml
   user_prompt: |
     Example good analysis:
     "Product X rose from #20 to #10 due to viral TikTok video..."

     Now analyze this event:
     {event_data}
   ```

4. **제약 조건 명시**
   ```yaml
   user_prompt: |
     Constraints:
     - Keep under 500 words
     - Focus on actionable insights
     - Avoid speculation without data
   ```

---

## 다음 단계

프롬프트 테스터를 사용하여 최적의 템플릿을 찾았다면:

1. **프로덕션 적용**: `src/services/insight_generator.py`에 적용
2. **자동화**: Prefect Flow에 통합
3. **리포트 생성**: Excel/PDF 자동 생성
4. **알림 설정**: Slack/이메일로 인사이트 전송

---

## 지원

문제가 발생하면:
1. 로그 확인: 터미널 출력
2. 이슈 등록: GitHub Issues
3. 문서 참조: README.md

Happy Prompt Testing! 🧪✨
