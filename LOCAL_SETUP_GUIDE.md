# 로컬 환경 실행 가이드

> **최종 업데이트**: 2025-11-17  
> **작성자**: AI Assistant

이 문서는 **다나와 PC 부품 크롤러 + AI 견적 시스템**을 로컬 환경(Windows/Mac/Linux)에서 실행하는 방법을 안내합니다.

---

## 📋 목차

1. [시스템 요구사항](#1-시스템-요구사항)
2. [사전 준비](#2-사전-준비)
3. [프로젝트 설정](#3-프로젝트-설정)
4. [실행 방법](#4-실행-방법)
5. [문제 해결](#5-문제-해결)

---

## 1. 시스템 요구사항

### 필수 설치
- **Docker Desktop** (권장) 또는 Docker Engine
  - Windows: [Docker Desktop for Windows](https://docs.docker.com/desktop/install/windows-install/)
  - Mac: [Docker Desktop for Mac](https://docs.docker.com/desktop/install/mac-install/)
  - Linux: [Docker Engine](https://docs.docker.com/engine/install/)
  
- **Git** (프로젝트 클론용)

### 권장 사양
- RAM: 8GB 이상 (Docker 컨테이너 4개 실행)
- 디스크: 10GB 이상 여유 공간
- CPU: 2코어 이상

---

## 2. 사전 준비

### 2-1. Google Gemini API 키 발급

AI 기능 (리뷰 요약, 견적 추천)을 위해 Google Gemini API 키가 필요합니다.

1. [Google AI Studio](https://aistudio.google.com/app/apikey) 접속
2. Google 계정으로 로그인
3. "Create API Key" 클릭
4. 발급된 API 키 복사 (예: `AIzaSyC...`)

> **참고**: Gemini API는 무료 할당량이 있습니다 (월 60회 요청).

---

## 3. 프로젝트 설정

### 3-1. 프로젝트 클론

```bash
git clone https://github.com/k-melon7129/danawa-py-crawler.git
cd danawa-py-crawler
```

### 3-2. 환경 변수 설정

`.env` 파일 생성 (`.env.example` 참고):

```bash
# Windows (PowerShell)
Copy-Item .env.example .env

# Mac/Linux
cp .env.example .env
```

`.env` 파일을 편집하여 API 키 입력:

```env
GOOGLE_API_KEY=AIzaSyC...your_actual_api_key_here
```

### 3-3. 주요 설정 파일 확인

프로젝트에는 다음 설정이 이미 적용되어 있습니다:

- **docker-compose.yml**: 모든 서비스 정의
  - `db`: MySQL 8.0 (포트 3307)
  - `backend`: Spring Boot (포트 8080)
  - `frontend`: React (포트 3000)
  - `crawler`: Python 크롤러
  - `summarizer`: AI 리뷰 요약기

- **application.properties**: 백엔드 DB 연결 설정
  - 로컬 모드: `localhost:3307`
  - Docker 모드: `db:3306` (자동 전환)

---

## 4. 실행 방법

### 4-1. 전체 시스템 실행 (Docker Compose)

모든 서비스를 한 번에 실행합니다.

```bash
docker-compose up -d db backend frontend
```

- `-d`: 백그라운드 실행
- `db`, `backend`, `frontend`만 실행 (크롤러는 수동 실행)

**실행 확인**:
```bash
docker-compose ps
```

출력 예시:
```
NAME                  STATUS              PORTS
danawa-db             Up 30 seconds       0.0.0.0:3307->3306/tcp
danawa-backend        Up 25 seconds       0.0.0.0:8080->8080/tcp
danawa-frontend       Up 20 seconds       0.0.0.0:3000->3000/tcp
```

### 4-2. 웹 서비스 접속

- **프론트엔드**: http://localhost:3000
- **백엔드 API**: http://localhost:8080

### 4-3. 크롤러 실행 (데이터 수집)

데이터베이스에 부품 데이터를 수집합니다.

```bash
docker-compose run --rm crawler
```

- 실행 시간: 약 10~30분 (카테고리별 2페이지씩)
- 수집 카테고리: CPU, 쿨러, 메인보드, RAM, 그래픽카드, SSD, HDD, 파워, 케이스

**로그 확인**:
```bash
docker-compose logs -f crawler
```

### 4-4. AI 리뷰 요약 실행 (선택사항)

퀘이사존 리뷰를 AI로 요약합니다.

```bash
docker-compose run --rm summarizer
```

- 실행 시간: 약 5~15분 (리뷰 수에 따라 다름)
- Gemini API 할당량 사용

---

## 5. 문제 해결

### 5-1. MySQL 연결 오류

**증상**:
```
Can't connect to MySQL server on 'localhost'
```

**해결**:
1. MySQL 컨테이너 상태 확인:
   ```bash
   docker-compose ps db
   ```

2. MySQL 로그 확인:
   ```bash
   docker-compose logs db
   ```

3. MySQL 접속 테스트:
   ```bash
   docker exec -it danawa-db mysql -uroot -p1234 danawa
   ```

### 5-2. 포트 충돌 오류

**증상**:
```
Bind for 0.0.0.0:3307 failed: port is already allocated
```

**해결**:
1. 사용 중인 프로세스 확인:
   ```bash
   # Windows
   netstat -ano | findstr :3307
   
   # Mac/Linux
   lsof -i :3307
   ```

2. `docker-compose.yml`에서 포트 변경:
   ```yaml
   ports:
     - "3308:3306"  # 3307 → 3308로 변경
   ```

### 5-3. Docker 빌드 오류

**증상**:
```
ERROR [internal] load metadata for docker.io/library/python:3.11-slim
```

**해결**:
1. Docker Desktop 실행 확인
2. 인터넷 연결 확인
3. 캐시 초기화 후 재빌드:
   ```bash
   docker-compose build --no-cache
   ```

### 5-4. Gemini API 오류

**증상**:
```
AI 요약 실패: 403 Client Error: Forbidden
```

**해결**:
1. `.env` 파일에 `GOOGLE_API_KEY` 확인
2. API 키 유효성 확인:
   - [Google AI Studio](https://aistudio.google.com/app/apikey)에서 키 상태 확인
3. API 할당량 확인:
   - 무료 할당량 초과 시 24시간 후 재시도

### 5-5. React 빌드 실패

**증상**:
```
npm ERR! ERESOLVE unable to resolve dependency tree
```

**해결**:
1. Node 모듈 캐시 삭제 후 재빌드:
   ```bash
   docker-compose down
   docker-compose build --no-cache frontend
   docker-compose up -d frontend
   ```

---

## 6. 주요 명령어 모음

### 서비스 관리
```bash
# 전체 서비스 시작
docker-compose up -d

# 특정 서비스만 시작
docker-compose up -d db backend frontend

# 서비스 중지
docker-compose stop

# 서비스 중지 및 컨테이너 삭제
docker-compose down

# 볼륨까지 삭제 (DB 데이터 초기화)
docker-compose down -v
```

### 로그 확인
```bash
# 전체 로그
docker-compose logs

# 특정 서비스 로그
docker-compose logs backend

# 실시간 로그 (tail -f)
docker-compose logs -f crawler
```

### 컨테이너 접속
```bash
# MySQL 접속
docker exec -it danawa-db mysql -uroot -p1234 danawa

# 백엔드 컨테이너 쉘 접속
docker exec -it danawa-backend /bin/bash

# 크롤러 디버깅 (HEADLESS_MODE=False로 실행)
docker-compose run --rm crawler python crawler.py
```

---

## 7. 개발 모드 (Docker 없이 로컬 실행)

Docker 없이 직접 실행하려면 다음 설정이 필요합니다.

### 7-1. MySQL 직접 설치

```bash
# Windows: MySQL Installer 사용
# Mac: brew install mysql@8.0
# Linux: apt install mysql-server

# MySQL 실행 및 DB 생성
mysql -uroot -p
CREATE DATABASE danawa CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

### 7-2. Python 크롤러 실행

```bash
cd /path/to/danawa-py-crawler

# 가상 환경 생성 (권장)
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 패키지 설치
pip install -r requirements.txt
playwright install chromium

# 환경 변수 설정
export DB_HOST=localhost
export DB_PORT=3306
export DB_USER=root
export DB_PASSWORD=your_password
export DB_NAME=danawa

# 크롤러 실행
python crawler.py
```

### 7-3. Spring Boot 백엔드 실행

```bash
cd webservice

# Maven 빌드
./mvnw clean package -DskipTests

# 실행
java -jar target/webservice-0.0.1-SNAPSHOT.jar
```

### 7-4. React 프론트엔드 실행

```bash
cd webservice/frontend

# 패키지 설치
npm install

# 개발 서버 실행
npm start
```

---

## 8. 추가 정보

### 프로젝트 구조
```
danawa-py-crawler/
├── crawler.py                 # 다나와 크롤러 (Python)
├── summarize_reviews.py       # AI 리뷰 요약기
├── docker-compose.yml         # Docker Compose 설정
├── requirements.txt           # Python 패키지
├── .env                       # 환경 변수 (직접 생성)
├── webservice/                # Spring Boot 백엔드
│   ├── pom.xml
│   ├── src/main/
│   │   ├── java/.../controller/
│   │   └── resources/application.properties
│   └── frontend/              # React 프론트엔드
│       ├── package.json
│       └── src/
│           ├── App.js
│           └── features_ai/   # AI 견적 기능 (k-melon 작업)
└── cloud_backup_disabled/     # 클라우드 설정 백업 (미사용)
```

### 주요 변경 사항 (2025-11-17)

1. **클라우드 → 로컬 전환**
   - Cloud SQL → 로컬 MySQL (포트 3307)
   - Vertex AI → Google Gemini API
   - Cloud Run → Docker Compose

2. **k-melon 브랜치 통합**
   - AI 견적 기능 추가 (`webservice/frontend/src/features_ai/`)
   - 부품 호환성 체크 기능
   - 전문가/일반 사용자 모드

3. **크롤러 개선**
   - 파워 제품 키워드 추출 로직 강화
   - 퀘이사존 본문 셀렉터 확대 (9개)
   - 디버깅 로그 강화

---

## 9. 문의 및 기여

- **이슈 보고**: [GitHub Issues](https://github.com/k-melon7129/danawa-py-crawler/issues)
- **Pull Request**: 기능 개선 및 버그 수정 환영합니다!

---

## 10. 라이선스

이 프로젝트는 교육 목적으로 제작되었습니다.  
다나와 및 퀘이사존의 이용약관을 준수하여 사용하세요.

---

**Happy Building! 🚀**




