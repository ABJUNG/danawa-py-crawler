# 🤖 AI PC Builder 사용 방법

## 🚀 시스템 시작

```bash
# 모든 서비스 시작
docker-compose up -d db backend frontend

# 크롤러 실행 (리뷰 & 벤치마크 수집)
docker-compose up crawler
```

## 📋 AI 견적 추천 프로세스

### 1. **접속**
- URL: http://localhost:3000/ai
- "AI PC Builder" 페이지 접속

### 2. **4단계 질문 답변** (ChatUI)
사용자 정보 수집:
- **예산**: 100만원 ~ 500만원 (원하는 금액 입력)
- **용도**: 게이밍 / 영상편집 / 사무용 / 코딩
- **선호 브랜드**: 인텔, AMD, ASUS, MSI 등 (선택사항)
- **추가 요구사항**: RGB, 정숙성, 컴팩트 등

### 3. **견적 모드 선택** (SidebarStack1)

#### 🤖 **AI 자동 완성 모드**
"AI 견적 추천 시작" 버튼 클릭 시:

1. **백엔드 API 호출**
   ```
   POST /api/builds/recommend
   {
     "budget": 1500000,
     "purpose": "게이밍",
     "preferences": {}
   }
   ```

2. **AI가 자동으로 수행**:
   - ✅ 용도별 예산 배분 (usage_weights 테이블 참조)
   - ✅ 각 카테고리별 최적 부품 선택 (DB에서 가격, 별점, 리뷰 기준)
   - ✅ CPU-메인보드 소켓 호환성 검사
   - ✅ RAM 타입 (DDR4/DDR5) 호환성 검사
   - ✅ 파워 용량 (TDP 계산) 적정성 검사
   - ✅ 케이스 폼팩터 호환성 검사
   - ✅ Gemini API를 통한 AI 설명 생성

3. **결과 표시** (SidebarStack4):
   - 선택된 부품 목록
   - 총 견적 금액
   - AI 설명 (Gemini가 생성한 친근한 설명)
   - 업그레이드 옵션
   - 호환성 검사 결과

#### 🛠️ **가이드 모드**
"직접 부품 고르기" 버튼 클릭 시:
- SidebarStack2: 카테고리별 모델 선택
- SidebarStack3: DB에서 실제 제품 목록 표시
  - 브랜드 필터
  - 가격/별점/리뷰 수 정렬
  - AI 점수 (별점+리뷰+벤치마크 종합)
  - 벤치마크 데이터 표시
  - 퀘이사존 리뷰 AI 요약 표시

## 🎯 AI 추천 알고리즘

### 예산 배분 (usage_weights 테이블)
```
게이밍 용도 예시:
- CPU: 20% (게이밍은 GPU가 더 중요)
- 그래픽카드: 35% (가장 높은 비중)
- RAM: 10%
- SSD: 8%
- 메인보드: 15%
- 파워: 7%
- 케이스: 5%
```

### 부품 선택 기준
1. **가격 범위**: 할당 예산의 80% ~ 120%
2. **별점**: 높은 순
3. **리뷰 수**: 많은 순
4. **브랜드 선호도**: 사용자 입력 반영

### 호환성 검사
```java
// CPU-메인보드 소켓
if (!cpuSocket.equals(motherboardSocket)) {
    result.addError("소켓이 호환되지 않습니다");
}

// RAM 타입
if (!ramType.equals(motherboardRamType)) {
    result.addError("RAM 타입이 호환되지 않습니다");
}

// 파워 용량
int recommendedWattage = (cpuTDP + gpuTDP + 100) * 1.2;
if (psuWattage < recommendedWattage) {
    result.addError("파워 용량이 부족합니다");
}
```

## 📊 DB 데이터 활용

### 제품 정보 (parts 테이블)
- 이름, 가격, 제조사
- 다나와 별점, 리뷰 수
- 이미지, 링크

### 상세 스펙 (part_spec 테이블)
- CPU: 코어 수, 클럭, 소켓
- 그래픽카드: VRAM, 메모리 타입
- RAM: 용량, DDR 타입
- 파워: 정격 출력, 80PLUS 인증
- 메인보드: 소켓, 칩셋, 폼팩터

### 퀘이사존 리뷰 (community_reviews 테이블)
- rawText: 크롤러가 수집한 원본 텍스트
- aiSummary: AI가 요약한 리뷰 (summarize_reviews.py)

### 벤치마크 (benchmark_results 테이블)
- CPU: Cinebench R23, Geekbench 6, Blender
- GPU: Blender, 3DMark (Fire Strike, Time Spy, Port Royal)

## 🔄 데이터 업데이트

### 크롤러 실행
```bash
# 리뷰 & 벤치마크 포함하여 수집
docker-compose up crawler
```

### 리뷰 AI 요약 생성
```bash
# Gemini API를 사용하여 리뷰 요약
docker-compose up summarizer
```

## 🛠️ 환경 변수 설정

`.env` 파일에 Gemini API 키 설정:
```bash
GEMINI_API_KEY=your_api_key_here
```

## 📱 화면 구성

### Phase 1: Intro & Chat
- AiIntro: 웰컴 화면
- ChatUI: 4단계 질문 (예산, 용도, 선호도, 추가 요구사항)

### Phase 2: Sidebar Stacks
- **Stack 1**: 모드 선택 (AI 자동 / 가이드)
- **Stack 2**: 부품 선택 진행도 (가이드 모드)
- **Stack 3**: 제품 목록 (DB 연동, 필터/정렬)
- **Stack 4**: 최종 견적 & AI 설명

### 플로팅 버튼
- AiChatbot: 실시간 부품 추천 챗봇

## 🎨 주요 기능

### AI 점수 계산
```javascript
let score = 50; // 기본 점수
score += (별점 * 6); // 최대 30점
score += Math.min(리뷰수 / 10, 15); // 최대 15점
if (AI요약) score += 5;
if (벤치마크) score += 5;
return Math.min(score, 100);
```

### 태그 생성
- 가격: 저렴함 / 고급형
- 별점: 최고평점 / 고평점
- 리뷰: 인기상품
- 데이터: 리뷰분석 / 벤치마크

## 🚨 문제 해결

### AI 추천이 작동하지 않을 때
1. DB에 부품 데이터가 있는지 확인
   ```sql
   SELECT COUNT(*) FROM parts;
   ```
2. usage_weights 테이블 확인
   ```sql
   SELECT * FROM usage_weights WHERE usage_type = '게이밍';
   ```
3. GEMINI_API_KEY 설정 확인
   ```bash
   docker-compose logs backend | grep GEMINI
   ```

### 호환성 오류가 발생할 때
- 메인보드와 CPU 소켓이 다름
- RAM 타입이 메인보드와 맞지 않음
- 파워 용량이 부족함
→ AI가 자동으로 대체 부품 검색 시도

## 📈 성능 최적화

### N+1 문제 해결 (향후)
```java
@EntityGraph(attributePaths = {"partSpec", "communityReviews", "benchmarkResults"})
List<Part> findAllByCategory(String category);
```

### 캐싱 적용 (향후)
```java
@Cacheable("buildRecommendations")
public BuildRecommendationDto recommendBuild(BuildRequestDto request) {
    // ...
}
```

## 🎯 테스트 시나리오

### 시나리오 1: 게이밍 PC (150만원)
- 예산: 1,500,000원
- 용도: 게이밍
- 기대 결과: RTX 4060 + Ryzen 5 조합

### 시나리오 2: 영상편집 PC (250만원)
- 예산: 2,500,000원
- 용도: 영상편집
- 기대 결과: 고성능 CPU + 대용량 RAM

### 시나리오 3: 사무용 PC (80만원)
- 예산: 800,000원
- 용도: 사무용
- 기대 결과: 저렴하고 안정적인 구성

---

**문의사항이 있으면 AiChatbot (플로팅 버튼)을 이용하세요! 🤖**

