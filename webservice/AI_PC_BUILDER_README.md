# AI PC Builder - Vertex AI 기반 PC 견적 추천 시스템

## 개요
Vertex AI(Gemini)를 활용하여 사용자의 예산과 용도에 맞는 최적의 PC 견적을 추천하고, 부품 간 호환성을 자동으로 검사하는 시스템입니다.

## 주요 기능

### 1. AI 기반 견적 추천
- 사용자의 예산과 용도(게이밍, 영상편집, 사무용 등)를 입력받아 최적의 부품 조합 추천
- Vertex AI Gemini 모델을 활용한 자연어 설명 생성
- 용도별 예산 배분 자동 계산

### 2. 호환성 자동 검사
- **규칙 기반 검사**:
  - CPU 소켓 ↔ 메인보드 소켓 일치 확인
  - RAM 타입(DDR4/DDR5) ↔ 메인보드 지원 여부
  - 파워 용량 ↔ 총 소비 전력 (CPU TDP + GPU TDP + 20% 여유분)
  - 케이스 폼팩터 ↔ 메인보드 크기
  
- **AI 기반 판단**: 복잡한 케이스에서 Vertex AI가 추가 검증

### 3. 대화형 챗봇
- 사용자 친화적인 대화형 인터페이스
- 단계별 질문으로 요구사항 수집
- 실시간 제안 버튼 제공

## 아키텍처

```
┌─────────────┐      ┌─────────────┐      ┌──────────────┐
│   React     │ ────▶│ Spring Boot │ ────▶│ Vertex AI    │
│  Frontend   │      │   Backend   │      │   (Gemini)   │
└─────────────┘      └─────────────┘      └──────────────┘
                           │
                           ▼
                     ┌─────────────┐
                     │  Cloud SQL  │
                     │   (MySQL)   │
                     └─────────────┘
```

## 데이터베이스 스키마

### 새로 추가된 테이블

#### 1. `compatibility_rules`
호환성 규칙을 저장합니다.

```sql
CREATE TABLE compatibility_rules (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    rule_type VARCHAR(50) NOT NULL,     -- 'cpu_socket', 'ram_type', 'power_wattage'
    source_value VARCHAR(100),          -- 예: 'AM5', 'DDR5'
    target_value VARCHAR(100),          -- 호환되는 값
    is_compatible BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### 2. `build_configurations`
사용자 견적을 저장합니다.

```sql
CREATE TABLE build_configurations (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    session_id VARCHAR(100) UNIQUE,
    user_budget INT,
    user_purpose VARCHAR(50),           -- '게이밍', '사무용', '영상편집' 등
    selected_parts JSON,                -- 선택된 부품 ID 목록
    ai_recommendation TEXT,             -- AI 추천 내용
    compatibility_check JSON,           -- 호환성 검사 결과
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### 3. `usage_weights`
용도별 부품 가중치를 저장합니다.

```sql
CREATE TABLE usage_weights (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    usage_type VARCHAR(50) NOT NULL,    -- '게이밍', '영상편집', '사무용' 등
    category VARCHAR(50) NOT NULL,      -- 'CPU', '그래픽카드' 등
    weight_percentage INT,              -- 예산 배분 비율 (%)
    priority INT                        -- 중요도 순위
);
```

## API 엔드포인트

### 1. 견적 추천 API
**POST** `/api/builds/recommend`

**Request Body:**
```json
{
  "budget": 1500000,
  "purpose": "게이밍",
  "preferences": {
    "preferred_brand": "AMD",
    "rgb": "true"
  }
}
```

**Response:**
```json
{
  "recommendedParts": {
    "CPU": {
      "id": 123,
      "name": "AMD Ryzen 7 7800X3D",
      "price": 520000,
      "category": "CPU"
    },
    "그래픽카드": { ... }
  },
  "totalPrice": 1450000,
  "explanation": "게이밍 용도로 선택된 견적입니다...",
  "upgradeOptions": [ ... ],
  "compatibilityCheck": {
    "isCompatible": true,
    "errors": [],
    "warnings": [],
    "summary": "모든 부품이 호환됩니다."
  }
}
```

### 2. 호환성 검사 API
**POST** `/api/builds/check-compatibility`

**Request Body:**
```json
[123, 456, 789]  // 부품 ID 배열
```

**Response:**
```json
{
  "isCompatible": false,
  "errors": [
    "CPU 소켓(AM5)과 메인보드 소켓(LGA1700)이 호환되지 않습니다."
  ],
  "warnings": [
    "파워 용량이 다소 여유롭지 않습니다."
  ],
  "summary": "호환되지 않는 부품이 있습니다. 1개의 오류를 해결해야 합니다."
}
```

### 3. 챗봇 API
**POST** `/api/chat/message`

**Request Body:**
```json
{
  "sessionId": "session-123",
  "message": "게이밍 PC 추천해줘",
  "context": ""
}
```

**Response:**
```json
{
  "message": "게이밍 PC를 추천해드리겠습니다! 예산이 어떻게 되시나요?",
  "suggestions": ["100만원", "150만원", "200만원"],
  "nextAction": "continue_chat"
}
```

## 환경 설정

### 1. 환경 변수 설정

```bash
# Google Cloud 프로젝트 설정
export VERTEXAI_PROJECT_ID=your-project-id
export VERTEXAI_LOCATION=asia-northeast3

# 서비스 계정 키 설정
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account-key.json

# Gemini API 키 (선택)
export GOOGLE_API_KEY=your-api-key
```

### 2. Google Cloud 권한 설정

서비스 계정에 다음 역할 부여:
- **Vertex AI User**: Gemini API 호출
- **Cloud SQL Client**: 데이터베이스 접근

```bash
gcloud projects add-iam-policy-binding PROJECT_ID \
  --member="serviceAccount:SERVICE_ACCOUNT_EMAIL" \
  --role="roles/aiplatform.user"
```

### 3. 크롤러 초기화

데이터베이스 테이블 및 초기 데이터 생성:

```bash
cd danawa-py-crawler
python crawler.py
```

이 명령으로 다음이 자동 실행됩니다:
- 테이블 생성 (`compatibility_rules`, `build_configurations`, `usage_weights`)
- 호환성 규칙 초기 데이터 삽입
- 용도별 가중치 데이터 삽입

## 빌드 및 실행

### Backend (Spring Boot)

```bash
cd webservice
mvn clean install
mvn spring-boot:run
```

### Frontend (React)

```bash
cd webservice/frontend
npm install
npm start
```

## 테스트

### 1. 호환성 검사 테스트

```bash
curl -X POST http://localhost:8080/api/builds/check-compatibility \
  -H "Content-Type: application/json" \
  -d '[1, 2, 3, 4, 5, 6]'
```

### 2. 견적 추천 테스트

```bash
curl -X POST http://localhost:8080/api/builds/recommend \
  -H "Content-Type: application/json" \
  -d '{
    "budget": 1500000,
    "purpose": "게이밍",
    "preferences": {}
  }'
```

### 3. 챗봇 테스트

```bash
curl -X POST http://localhost:8080/api/chat/message \
  -H "Content-Type: application/json" \
  -d '{
    "sessionId": "test-session",
    "message": "150만원으로 게이밍 PC 추천해줘"
  }'
```

## 주요 클래스 설명

### Backend

- **`CompatibilityService`**: 부품 호환성 검사 로직
- **`BuildRecommendationService`**: AI 기반 견적 추천 로직
- **`ChatService`**: Vertex AI 챗봇 서비스
- **`BuildController`**: 견적 관련 API 컨트롤러
- **`ChatController`**: 챗봇 API 컨트롤러

### Database Initialization (Python)

- **`initialize_compatibility_rules()`**: 호환성 규칙 초기화
- **`initialize_usage_weights()`**: 용도별 가중치 초기화

## 확장 가능성

### 1. 외부 코드 통합
다른 개발자가 작성한 풀스택 코드 통합 시:

```bash
# 백업
git checkout -b backup-before-merge

# 의존성 비교
diff webservice/pom.xml external/pom.xml
diff webservice/frontend/package.json external/frontend/package.json

# 점진적 통합
git checkout -b feature/external-integration
# 파일별로 추가 및 테스트
```

### 2. 프롬프트 최적화
`BuildRecommendationService.generateAIExplanation()` 메서드에서 프롬프트를 수정하여 AI 응답 품질 개선

### 3. 캐싱 전략
동일한 예산/용도 조합에 대해 Redis 캐싱 적용 가능

## 문제 해결

### Vertex AI 연결 실패
- `GOOGLE_APPLICATION_CREDENTIALS` 환경 변수 확인
- 서비스 계정 권한 확인
- 프로젝트 ID가 올바른지 확인

### 호환성 검사 오작동
- `compatibility_rules` 테이블에 규칙이 있는지 확인
- 부품 스펙 JSON이 올바르게 파싱되는지 확인

### 빌드 실패
- Java 17 이상 사용 확인
- Maven 의존성 다운로드 확인
- DB 연결 정보 확인

## 기여

이 프로젝트는 외부 개발자의 기여를 환영합니다!

1. 이 레포지토리를 Fork
2. Feature 브랜치 생성 (`git checkout -b feature/amazing-feature`)
3. 변경사항 커밋 (`git commit -m 'Add amazing feature'`)
4. 브랜치 푸시 (`git push origin feature/amazing-feature`)
5. Pull Request 생성

## 라이선스
MIT License

## 연락처
프로젝트 관련 문의: [GitHub Issues](https://github.com/your-repo/issues)



