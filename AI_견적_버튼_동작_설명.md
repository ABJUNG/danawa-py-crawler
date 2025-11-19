# 🤖 AI 견적 추천 페이지 버튼 동작 설명

## 📌 개요

AI 견적 추천 페이지(SidebarStack1)의 모든 버튼과 설정이 **실제 DB 데이터**와 **Gemini AI**를 활용하여 작동합니다.

---

## 🎯 주요 버튼 및 기능

### 1. **🤖 AI 자동 설정** 버튼

**위치**: 부품별 비율 설정 섹션 상단

**동작**:
```javascript
사용자가 선택한 "사용 목적"에 따라 부품별 예산 비율을 자동 계산
```

**알고리즘**:
- **게이밍**: GPU 45%, CPU 20%, RAM 8%...
- **영상 편집**: CPU 28%, GPU 30%, RAM 12%...
- **코딩·AI**: CPU 30%, RAM 15%, GPU 25%...
- **디자인**: GPU 35%, RAM 12%, CPU 22%...
- **사무용**: 균형잡힌 비율

**효과**:
- 사용 목적에 최적화된 예산 배분
- 수동 조정도 가능 (🔒 잠금 기능 제공)
- 총합 100% 자동 조절

---

### 2. **AI 견적 추천 시작** 버튼 (메인 버튼)

**위치**: SidebarStack1 하단

**동작 흐름**:

```
[사용자 클릭]
     ↓
[모든 설정값 수집]
 - estimateMode (auto/guided)
 - recommendStyle (가성비/균형/최고사양)
 - aiFlexibility (엄격/유연)
 - budgetFlexibility (0-20%)
 - usagePurposes (게이밍, 영상편집 등)
 - componentRatios (부품별 비율)
 - 선택적 설정들 (성능, 케이스, 소음, 디자인, 업그레이드)
     ↓
[백엔드 API 호출]
 POST /api/builds/recommend
 {
   budget: 1500000,
   purpose: "게이밍",
   preferences: {
     recommend_style: "balanced",
     ai_flexibility: "strict",
     budget_flexibility: 10,
     component_ratios: {...},
     rgb_lighting: true,
     power_saving: false,
     ...
   }
 }
     ↓
[백엔드 처리]
 1. usage_weights 테이블에서 용도별 예산 배분 조회
 2. 각 카테고리별 DB에서 최적 부품 검색
    - 추천 스타일 반영 (가성비: 저가 우선, 최고사양: 고가 우선)
    - AI 유연성 반영 (엄격: 120%까지, 유연: 130%까지)
    - RGB, 저소음, 저전력 등 필터 적용
 3. CPU-메인보드 소켓 호환성 검사
 4. RAM 타입 호환성 검사
 5. 파워 용량 적정성 검사
 6. Gemini API로 AI 설명 생성
     ↓
[프론트엔드 표시]
 - SidebarStack4에 최종 견적 표시
 - 각 부품 정보 (이름, 가격, 별점, 스펙)
 - 총 견적 금액
 - Gemini가 생성한 AI 설명
 - 호환성 검사 결과
 - 업그레이드 옵션
```

---

### 3. **추천 스타일** (라디오 버튼)

**옵션**:
- ⭐ **가성비 중심** (value)
- ⚖️ **균형형** (balanced)
- 🚀 **최고사양형** (highend)

**백엔드 동작**:

```java
if ("value".equals(recommendStyle)) {
    // 가격 낮은 순 정렬
    // 예산의 60% ~ 90% 범위에서 검색
    sort = Sort.by(Sort.Order.asc("price"), Sort.Order.desc("starRating"));
} else if ("highend".equals(recommendStyle)) {
    // 가격 높은 순 정렬
    // 예산의 90% ~ 120% 범위에서 검색
    sort = Sort.by(Sort.Order.desc("price"), Sort.Order.desc("starRating"));
} else {
    // 별점 높은 순 정렬 (균형형)
    sort = Sort.by(Sort.Direction.DESC, "starRating");
}
```

**실제 효과**:
- **가성비**: RTX 4060 대신 RTX 3060 Ti 추천 (가격 낮음)
- **균형형**: RTX 4060 추천 (평가 좋은 제품)
- **최고사양**: RTX 4070 추천 (예산 내 최고 성능)

---

### 4. **AI 유연성** (토글)

**옵션**:
- 🔒 **조건 엄격 모드** (strict)
- 🔓 **자유 추천 모드** (flexible)

**백엔드 동작**:

```java
String aiFlexibility = preferences.get("ai_flexibility");
double flexibilityMultiplier = "flexible".equals(aiFlexibility) ? 1.3 : 1.2;

int maxPrice = (int)(budget * flexibilityMultiplier);
```

**실제 효과**:
- **엄격 모드**: 예산 120%까지만 허용 (예: 150만원 → 최대 180만원)
- **유연 모드**: 예산 130%까지 허용 (예: 150만원 → 최대 195만원)
  - 더 나은 구성을 위해 예산 초과 가능

---

### 5. **예산 여유도** (슬라이더)

**범위**: 0% ~ 20%

**동작**:
```javascript
budgetFlexibility = 10; // 10% 설정 시

예상 총 견적:
₩1,500,000 ~ ₩1,650,000
```

**백엔드 활용**:
- `budget * (1 + budgetFlexibility / 100)` 계산
- 업그레이드 옵션 제안 시 활용

---

### 6. **부품별 비율 설정**

**동작**:
- 각 부품 슬라이더 조정 → 다른 부품 자동 재조정
- 🔒 잠금 버튼 → 해당 부품 비율 고정
- 총합 100% 자동 유지

**백엔드 활용**:
```javascript
// 프론트엔드에서 설정한 비율
componentRatios = {
  cpu: 25%,
  gpu: 35%,
  ram: 8%,
  ...
}

// 백엔드에서 각 카테고리 예산 계산
cpuBudget = 1,500,000 * 0.25 = 375,000원
gpuBudget = 1,500,000 * 0.35 = 525,000원
```

---

### 7. **선택적 섹션** (펼치기/접기)

#### 📊 **성능 및 작업 우선도**
- **작업 강도**: 가벼움 / 중간 / 고사양
- **멀티태스킹**: 낮음 / 보통 / 높음 → RAM 용량 결정
- **그래픽 목표**: FHD / QHD / 4K → GPU 성능 결정

#### 🏠 **케이스 및 환경**
- **케이스 크기**: 빅타워 / 미들타워 / 미니타워 / SFF
- **패널 형태**: 강화유리 / 폐쇄형 / 메시 / 전면유리

#### ⚡ **전력 효율 및 소음**
- **전기 절약 모드**: CPU/GPU TDP 낮은 제품 우선
- **소음 기준**: 무소음 / 균형 / 최대 냉각

```java
// 백엔드 동작 예시
if ("true".equals(preferences.get("power_saving"))) {
    // 저전력 CPU 우선 정렬
    filtered.sort((p1, p2) -> {
        int tdp1 = extractTdp(p1);
        int tdp2 = extractTdp(p2);
        return Integer.compare(tdp1, tdp2); // 낮은 TDP 우선
    });
}
```

#### 🎨 **디자인 및 외관**
- **RGB 조명**: 체크 시 RGB 부품 우선

```java
if ("true".equals(preferences.get("rgb_lighting"))) {
    // RGB가 있는 제품 우선 정렬
    filtered.sort((p1, p2) -> {
        boolean p1HasRgb = hasRgbLighting(p1);
        boolean p2HasRgb = hasRgbLighting(p2);
        if (p1HasRgb && !p2HasRgb) return -1;
        return 0;
    });
}
```

- **색상 테마**: 블랙 / 화이트 / 실버 / 레드 / 블루 (최대 3개)
- **재질**: 철제 / 알루미늄 / 플라스틱

#### 🔧 **업그레이드 및 내구성**
- **업그레이드 계획**: 확장성 좋은 메인보드 선택
- **AS 기준**: 국내 / 상관없음
- **사용 수명 목표**: 1-3년 / 3-5년 / 5년+

---

## 🔄 전체 동작 흐름

### **AI 자동 완성 모드** 선택 시

```
1. 사용자가 "AI 견적 추천 시작" 클릭
    ↓
2. 모든 설정값 수집 (추천 스타일, 유연성, 예산, 비율, 선택적 설정 등)
    ↓
3. 백엔드 API 호출
    ↓
4. DB에서 각 카테고리별 최적 부품 검색
   - 추천 스타일에 따른 가격 범위 조정
   - AI 유연성에 따른 예산 초과 허용
   - RGB, 저소음, 저전력 필터 적용
    ↓
5. 호환성 자동 검사
   - CPU-메인보드 소켓
   - RAM 타입
   - 파워 용량
   - 케이스 폼팩터
    ↓
6. Gemini API로 AI 설명 생성
   "게이밍 용도로 최적화된 견적입니다. RTX 4060과 Ryzen 5 7600X의 조합은..."
    ↓
7. Stack2 (진행도 표시) → Stack4 (최종 견적)로 이동
```

### **AI 가이드 선택 모드** 선택 시

```
1. 사용자가 "AI 견적 추천 시작" 클릭
    ↓
2. 모든 설정값 수집 (가이드 모드에서도 활용)
    ↓
3. Stack2로 이동 (카테고리별 선택)
    ↓
4. 각 카테고리에서 모델 선택 → Stack3 (제품 목록)
   - DB에서 실제 제품 표시
   - 필터/정렬 기능 (가격, 별점, AI 점수)
    ↓
5. 제품 선택 → Stack2로 복귀 → 다음 카테고리
    ↓
6. 모든 부품 선택 완료 → Stack4 (최종 견적)
```

---

## 🎯 실제 사용 예시

### 예시 1: 게이밍 PC (가성비 중심)

**설정**:
- 예산: 150만원
- 용도: 게이밍
- 추천 스타일: **가성비 중심**
- AI 유연성: **엄격 모드**
- 예산 여유도: 5%

**AI 추천 결과**:
```
CPU: AMD Ryzen 5 5600 (240,000원)
GPU: RTX 4060 Ti (480,000원)
RAM: DDR4 16GB (60,000원)
SSD: 500GB NVMe (70,000원)
메인보드: B550 (150,000원)
파워: 650W Bronze (80,000원)
케이스: 미들타워 (60,000원)
쿨러: 타워형 (40,000원)

총액: 1,480,000원 (예산 대비 98.6%)
```

### 예시 2: 영상편집 PC (최고사양형)

**설정**:
- 예산: 250만원
- 용도: 영상 편집
- 추천 스타일: **최고사양형**
- AI 유연성: **유연 모드**
- 예산 여유도: 15%
- RGB 조명: ✅
- 전기 절약: ❌

**AI 추천 결과**:
```
CPU: AMD Ryzen 9 7900X (650,000원)
GPU: RTX 4070 (800,000원)
RAM: DDR5 32GB (240,000원)
SSD: 1TB Gen4 (150,000원)
메인보드: X670E (280,000원)
파워: 850W Gold (150,000원)
케이스: RGB 미들타워 (120,000원)
쿨러: 수냉 RGB (180,000원)

총액: 2,570,000원 (예산 초과 2.8%, 유연 모드로 허용)
```

---

## ✅ 모든 버튼이 실제로 작동하는 이유

### 프론트엔드
✅ SidebarStack1의 모든 상태값 수집 (`handleStart`)  
✅ AiBuildApp에서 백엔드로 전달 (`generateAutoCompleteParts`)  
✅ Console에서 요청 확인 가능 (`console.log`)

### 백엔드
✅ `BuildRecommendationService`가 preferences 활용  
✅ `findBestPartInBudget`에서 추천 스타일 반영  
✅ `applyAdvancedFilters`에서 RGB, 소음, 전력 필터 적용  
✅ Gemini API로 AI 설명 생성  
✅ `CompatibilityService`로 호환성 검사

### 데이터베이스
✅ `parts` 테이블에서 실제 제품 검색  
✅ `part_spec` 테이블에서 스펙 확인 (RGB, TDP, 소음 등)  
✅ `usage_weights` 테이블에서 용도별 예산 배분  
✅ `community_reviews` 및 `benchmark_results` 활용

---

## 🚀 확인 방법

### 1. 브라우저 개발자 도구 확인
```javascript
// F12 → Console 탭
// "AI 견적 추천 시작" 버튼 클릭 시 표시:
AI 추천 요청: {
  budget: 1500000,
  purpose: "게이밍",
  preferences: {
    recommend_style: "value",
    ai_flexibility: "flexible",
    budget_flexibility: 10,
    rgb_lighting: true,
    power_saving: false,
    ...
  }
}
```

### 2. 백엔드 로그 확인
```bash
docker-compose logs backend | grep "견적 추천 요청"
```

### 3. 실제 테스트
1. `http://localhost:3000/ai` 접속
2. ChatUI에서 4가지 질문 답변
3. SidebarStack1에서 설정 조정:
   - 추천 스타일: **가성비**
   - AI 유연성: **유연 모드** ON
   - 사용 목적: **게이밍** 체크
   - RGB 조명 섹션 펼치기 → **RGB 조명** 체크
4. "🤖 AI 자동 설정" 버튼 클릭 → 부품 비율 자동 조정 확인
5. "AI 견적 추천 시작" 버튼 클릭
6. Stack4에서 결과 확인:
   - 가성비 제품들이 선택되었는지
   - RGB 부품이 포함되었는지
   - 예산 범위 내인지 (유연 모드로 약간 초과 가능)

---

## 📝 요약

| 버튼/설정 | 동작 | 백엔드 반영 | DB 활용 |
|----------|------|------------|---------|
| **AI 자동 설정** | 부품 비율 자동 계산 | ❌ (프론트엔드) | ❌ |
| **AI 견적 추천 시작** | 전체 추천 프로세스 시작 | ✅ | ✅ |
| **추천 스타일** | 가격 범위 & 정렬 기준 | ✅ | ✅ |
| **AI 유연성** | 예산 초과 허용 범위 | ✅ | ✅ |
| **예산 여유도** | 업그레이드 옵션 | ✅ | ✅ |
| **부품별 비율** | 카테고리별 예산 배분 | ✅ (참고용) | ❌ |
| **RGB 조명** | RGB 부품 우선 선택 | ✅ | ✅ |
| **전기 절약** | 저전력 부품 우선 | ✅ | ✅ |
| **소음 기준** | 저소음 부품 우선 | ✅ | ✅ |

모든 설정이 **실제 DB 데이터**와 **Gemini AI**를 활용하여 작동합니다! 🎉

