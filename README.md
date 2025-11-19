# PC 부품 가격 정보 포털 + AI 견적 추천 시스템

> **Danawa Parts Price Portal with AI PC Builder**

## 📌 프로젝트 개요

**다나와**에서 주요 PC 부품 정보를 자동으로 수집하고, **Google Gemini AI**를 활용하여 사용자 맞춤형 PC 견적을 추천하는 풀스택 웹 서비스입니다.

### 주요 기능
- 🤖 **AI 견적 추천**: 사용자 용도/예산에 맞춘 PC 구성 자동 추천
- 🔍 **실시간 부품 검색**: 9개 카테고리, 200+ 상세 스펙 필터링
- 💬 **AI 챗봇**: 부품 호환성 검사 및 견적 상담
- 📊 **벤치마크 데이터**: CPU/GPU 성능 비교
- 📝 **퀘이사존 리뷰**: 전문가 리뷰 AI 요약

### 기술 스택
- **Frontend**: React 18
- **Backend**: Spring Boot 3.2, Java 17
- **Database**: MySQL 8.0
- **Crawler**: Python 3.11, Playwright
- **AI**: Google Gemini 1.5 Flash
- **DevOps**: Docker Compose (로컬 실행)

## 2. 주요 기능 명세
### 2-1. 데이터 수집 (웹 크롤러)
수집 대상: 다나와(https://www.google.com/search?q=danawa.com) 검색 결과 페이지

수집 주기: 수동 실행 (향후 자동화 예정)

수집 카테고리 (총 9개): CPU, 쿨러, 메인보드, RAM, 그래픽카드(VGA), SSD, HDD, 파워, 케이스

수집 범위: 각 카테고리별로 최대 5페이지까지의 상품 정보를 수집한다.

수집 항목: 상품명, 카테고리명, 가격, 다나와 링크, 이미지 URL

특이사항: 인피니티 스크롤 및 이미지 지연 로딩(Lazy Loading)에 대응하여 전체 데이터를 수집한다.

### 2-2. 사용자 기능 (웹페이지)
카테고리 조회:

사용자는 상단의 내비게이션 바에서 원하는 부품 카테고리를 선택할 수 있다.

카테고리를 선택하면 해당 카테고리의 부품 목록이 즉시 표시된다.

상세 필터링:

카테고리를 선택하면, 해당 카테고리에 존재하는 제조사 목록이 필터 옵션으로 동적으로 생성된다.

(예: 'CPU' 선택 시 'Intel', 'AMD'가 옵션으로 표시)

사용자가 특정 제조사를 선택하면, 해당 제조사의 제품만 필터링되어 목록에 표시된다.

키워드 검색:

사용자는 현재 선택된 카테고리 내에서 키워드로 상품명을 검색할 수 있다.

검색 결과는 현재 적용된 상세 필터(제조사)를 모두 반영한다.

검색 히스토리:

모든 검색 기록은 사용자의 웹 브라우저(로컬 스토리지)에 저장된다.

검색창에 포커스하면 최근 검색어 목록이 나타난다.

목록의 검색어를 클릭하면 해당 키워드로 즉시 재검색된다.

각 검색어는 개별적으로 삭제할 수 있다.

## 3. API 명세
Method	URL	파라미터	설명	응답
GET	/api/parts	category (필수) manufacturer (선택)	지정된 카테고리 및 제조사의 부품 목록을 조회합니다.	List<Part>
GET	/api/manufacturers	category (필수)	지정된 카테고리에 속한 모든 제조사 목록을 중복 없이 조회합니다.	List<String>
GET	/api/parts/search	category (필수) keyword (필수)	지정된 카테고리 내에서 키워드로 부품을 검색합니다.	List<Part>

Sheets로 내보내기
## 4. 데이터베이스 스키마
Table: parts

컬럼명	데이터 타입	제약조건	설명
id	INT	PK, AI	고유 ID
name	VARCHAR(255)	NOT NULL	부품 이름
category	VARCHAR(50)	NOT NULL	카테고리명
price	INT	NOT NULL	가격 (원)
link	VARCHAR(512)	NOT NULL, UNIQUE	다나와 상품 링크
img_src	VARCHAR(512)		이미지 URL
created_at	TIMESTAMP	DEFAULT now()	생성 시각
updated_at	TIMESTAMP	DEFAULT now()	수정 시각

Sheets로 내보내기
## 5. 빠른 시작 (Quick Start)

### 전제 조건
- Docker Desktop 설치
- Google Gemini API 키 ([발급 링크](https://aistudio.google.com/app/apikey))

### 실행 방법

```bash
# 1. 프로젝트 클론
git clone https://github.com/k-melon7129/danawa-py-crawler.git
cd danawa-py-crawler

# 2. 환경 변수 설정
cp .env.example .env
# .env 파일에 GOOGLE_API_KEY=your_api_key 입력

# 3. 서비스 실행
docker-compose up -d db backend frontend

# 4. 데이터 수집 (크롤러 실행)
docker-compose run --rm crawler
```

### 접속 URL
- **웹 서비스**: http://localhost:3000
- **백엔드 API**: http://localhost:8080

> **상세 가이드**: [LOCAL_SETUP_GUIDE.md](./LOCAL_SETUP_GUIDE.md) 참고

---

## 6. 프로젝트 변경 이력

### v3.0 (2025-11-17) - 로컬 모드 전환 🏠
- **k-melon 브랜치 통합**: AI 견적 추천 기능 추가
- **클라우드 → 로컬 전환**:
  - Cloud SQL → 로컬 MySQL (Docker)
  - Vertex AI → Google Gemini API
  - Cloud Run → Docker Compose
- **크롤러 개선**:
  - 퀘이사존 리뷰 수집 안정화
  - 파워 제품 키워드 추출 강화
  - 디버깅 로그 대폭 개선

### v2.x (2025-11-14) - 클라우드 배포
- Cloud Run 기반 자동 크롤링
- Vertex AI 통합

### v1.x (2025-10) - 초기 버전
- 기본 크롤러 + 웹 서비스

---

## 7. 기여자

- **ABJUNG**: 초기 프로젝트 설계 및 크롤러 개발
- **k-melon7129**: AI 견적 추천 기능 개발
- **AI Assistant**: 로컬 모드 전환 및 통합 작업

---

## 8. 라이선스

이 프로젝트는 교육 목적으로 제작되었습니다.  
다나와 및 퀘이사존의 이용약관을 준수하여 사용하세요.