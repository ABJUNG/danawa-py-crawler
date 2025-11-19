# 🤖 AI 견적 추천 시스템 설정 가이드

## 개요

이 프로젝트는 Google Gemini API를 사용하여 PC 부품 추천 AI 챗봇을 구현합니다. 크롤러가 수집한 실제 데이터를 바탕으로 사용자에게 최적의 부품을 추천합니다.

---

## 📋 사전 준비

### 1. Google Gemini API 키 발급

1. **Google AI Studio 접속**
   - [https://makersuite.google.com/app/apikey](https://makersuite.google.com/app/apikey)

2. **API 키 생성**
   - "Create API Key" 버튼 클릭
   - 프로젝트 선택 또는 새 프로젝트 생성
   - API 키 복사 (예: `AIzaSyXXXXXXXXXXXXXXXXXXXXXXXXXXXX`)

3. **주의사항**
   - API 키는 외부에 노출되지 않도록 주의하세요
   - `.env` 파일은 절대 Git에 커밋하지 마세요 (`.gitignore`에 포함됨)

---

## ⚙️ 환경 변수 설정

### 프로젝트 루트에 `.env` 파일 생성

```bash
# Google Gemini API 키
GOOGLE_API_KEY=your_actual_api_key_here
```

**예시:**
```bash
GOOGLE_API_KEY=AIzaSyABCDEF1234567890GHIJKLMNOPQRSTUVWX
```

---

## 🐳 Docker Compose 설정

### `docker-compose.yml`에 환경 변수 전달 확인

```yaml
backend:
  build:
    context: ./webservice
    dockerfile: Dockerfile
  container_name: danawa-backend
  ports:
    - "8080:8080"
  networks:
    - danawa-net
  environment:
    - SPRING_DATASOURCE_URL=jdbc:mysql://db:3306/danawa?useSSL=false&serverTimezone=Asia/Seoul&allowPublicKeyRetrieval=true
    - SPRING_DATASOURCE_USERNAME=root
    - SPRING_DATASOURCE_PASSWORD=1234
    - GOOGLE_API_KEY=${GOOGLE_API_KEY}  # .env 파일에서 자동 주입
  depends_on:
    - db
```

---

## 🚀 실행 방법

### 1. 환경 변수 설정 확인

```powershell
# .env 파일 내용 확인 (PowerShell)
Get-Content .env
```

### 2. Docker Compose 빌드 및 실행

```powershell
# 전체 서비스 빌드 (백엔드 재빌드 포함)
docker-compose build backend

# 서비스 실행
docker-compose up -d db backend frontend
```

### 3. 백엔드 로그 확인

```powershell
# 백엔드 로그 실시간 확인
docker-compose logs -f backend
```

**성공 시 출력:**
```
로컬 MySQL DB 연결 성공 (db:3306/danawa)
Tomcat started on port(s): 8080 (http)
```

**API 키 오류 시 출력:**
```
Gemini API 키가 설정되지 않았습니다.
```

### 4. 크롤러 실행 (데이터 수집)

```powershell
# 크롤러 실행
docker-compose up crawler
```

---

## 🧪 테스트

### 1. 프론트엔드 접속
- URL: [http://localhost:3000](http://localhost:3000)
- `/ai` 페이지에서 AI PC Builder 접근

### 2. AI 챗봇 테스트

1. AI PC Builder 페이지 (`/ai`)에서 우측 하단 💬 버튼 클릭
2. 질문 예시:
   ```
   - "게임용 그래픽카드 추천해줘"
   - "50만원대 CPU 찾아줘"
   - "고성능 SSD 알려줘"
   - "예산 100만원으로 부품 추천"
   ```

### 3. 백엔드 API 직접 테스트

```powershell
# PowerShell에서 API 테스트
$body = "게임용 그래픽카드 추천해줘"
Invoke-RestMethod -Uri "http://localhost:8080/api/chat" `
  -Method POST `
  -ContentType "text/plain; charset=UTF-8" `
  -Body $body
```

---

## 🔍 문제 해결

### 1. "API 키가 설정되지 않았습니다" 오류

**원인:** `.env` 파일의 `GOOGLE_API_KEY`가 올바르게 설정되지 않음

**해결:**
```powershell
# .env 파일 확인
Get-Content .env

# API 키가 없거나 잘못된 경우 재설정
echo "GOOGLE_API_KEY=your_actual_api_key" > .env

# 백엔드 재시작
docker-compose restart backend
```

### 2. "데이터베이스에 부품 정보가 없습니다" 응답

**원인:** 크롤러가 아직 데이터를 수집하지 않음

**해결:**
```powershell
# 크롤러 실행
docker-compose up crawler

# 크롤러 로그 확인
docker-compose logs crawler --tail=100
```

### 3. AI 응답이 "테스트 모드" 또는 오류 메시지

**원인:** Gemini API 호출 실패 (API 키 오류, 네트워크 오류, 할당량 초과)

**해결:**
```powershell
# 백엔드 로그에서 상세 오류 확인
docker-compose logs backend --tail=50

# API 키 확인
echo $env:GOOGLE_API_KEY  # PowerShell

# 할당량 확인: https://makersuite.google.com/app/apikey
```

### 4. CORS 오류 (프론트엔드에서 백엔드 API 호출 실패)

**원인:** 프론트엔드와 백엔드가 다른 도메인에서 실행 중

**해결:**
- `PartController.java`에 `@CrossOrigin` 추가 (이미 설정됨)
- `.env`의 `REACT_APP_API_URL=http://localhost:8080` 확인

---

## 📊 AI 동작 방식

### 1. 사용자 질문 분석
```
사용자 입력: "게임용 그래픽카드 추천해줘"
      ↓
카테고리 추출: "그래픽카드"
```

### 2. 데이터베이스 검색
```
DB 쿼리: category = "그래픽카드"
      ↓
가격대별 제품 선택 (저가, 중가, 고가)
      ↓
상위 10개 제품 선택 (리뷰 요약 있는 제품 우선)
```

### 3. Gemini API 호출
```
프롬프트 구성:
- 페르소나: PC 부품 전문가 '다오나'
- 참고 자료: DB에서 가져온 실제 제품 정보
- 사용자 질문
      ↓
Gemini API 호출
      ↓
AI 응답 생성
```

### 4. 응답 형식
```
안녕하세요! 다오나입니다 🤖

📌 추천 1: ZOTAC RTX 4060 Twin Edge (가격: 420,000원)
- **왜 추천?**: 1080p 게임에 최적화된 가성비 제품
- **주요 스펙**: 8GB GDDR6, 부스트클럭 2460MHz
- **사용자 리뷰**: "조용하고 발열이 적음"

📌 추천 2: ASUS RTX 4070 Dual (가격: 730,000원)
...

더 궁금한 점이 있으시면 언제든 물어보세요! 💬
```

---

## 📈 API 사용량 관리

### Gemini API 무료 할당량
- **분당 요청 수**: 15 RPM (Requests Per Minute)
- **일일 요청 수**: 1,500 RPD (Requests Per Day)
- **토큰 제한**: 입력 32,000 토큰, 출력 8,000 토큰

### 할당량 초과 시 대응
1. Google Cloud Console에서 할당량 증가 요청
2. 응답 캐싱 구현 (동일 질문 반복 방지)
3. 유료 플랜 전환 고려

---

## 🔐 보안 권장사항

1. **API 키 보호**
   - `.env` 파일을 Git에 커밋하지 마세요
   - 프로덕션 환경에서는 환경 변수로 주입

2. **CORS 설정**
   - 프로덕션에서는 특정 도메인만 허용

3. **Rate Limiting**
   - 과도한 API 호출 방지 로직 추가

---

## 📚 참고 문서

- [Google Gemini API 공식 문서](https://ai.google.dev/docs)
- [Gemini REST API 참조](https://ai.google.dev/api/rest/v1/models/generateContent)
- [Spring Boot REST API 가이드](https://spring.io/guides/tutorials/rest/)

---

## 💡 추가 개선 아이디어

1. **응답 캐싱**: 동일한 질문에 대해 캐시된 응답 반환
2. **사용자 컨텍스트**: 이전 대화 내역을 바탕으로 맞춤 추천
3. **다중 카테고리 질문**: "게임용 PC 전체 견적 추천" 같은 복합 질문 처리
4. **성능 최적화**: DB 쿼리 최적화, 인덱스 추가
5. **A/B 테스트**: 다양한 프롬프트 전략 비교

---

**문의 사항이 있으시면 프로젝트 이슈 페이지에 남겨주세요!** 🚀



