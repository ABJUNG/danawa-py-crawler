# Docker 환경에서 Gemini API 설정 가이드 🐳

## 📋 빠른 설정 (3단계)

### 1단계: Google AI Studio에서 API 키 발급

1. 브라우저에서 https://aistudio.google.com/app/apikey 접속
2. Google 계정으로 로그인
3. "Create API key" 버튼 클릭
4. API 키 복사 (예: `AIzaSyAaBbCcDdEeFfGgHhIiJjKkLlMmNnOoPpQq`)

---

### 2단계: 프로젝트 루트에 `.env` 파일 생성

**프로젝트 루트 디렉토리**에 `.env` 파일을 만들고 다음 내용을 입력하세요:

#### Windows PowerShell:
```powershell
# 프로젝트 루트로 이동
cd C:\Users\KIU-SW\Documents\GitHub\danawa-py-crawler-11-17-crawler

# .env 파일 생성 및 편집
notepad .env
```

#### .env 파일 내용:
```bash
# Google Gemini API Key
GOOGLE_API_KEY=여기에_발급받은_API키_붙여넣기
```

**실제 예시** (API 키를 실제 것으로 교체):
```bash
GOOGLE_API_KEY=AIzaSyAaBbCcDdEeFfGgHhIiJjKkLlMmNnOoPpQq
```

⚠️ **중요**:
- `.env` 파일은 프로젝트 **루트 디렉토리**에 위치해야 합니다 (docker-compose.yml과 같은 위치)
- `GOOGLE_API_KEY=` 다음에 **공백 없이** API 키를 입력하세요
- 따옴표는 **사용하지 마세요**

---

### 3단계: Docker Compose 재시작

`.env` 파일을 저장한 후 Docker Compose를 재시작하세요:

```bash
# 기존 컨테이너 중지 및 제거
docker-compose down

# 백엔드를 다시 빌드하면서 시작
docker-compose up --build backend

# 또는 모든 서비스 재시작
docker-compose up --build
```

---

## 🔍 설정 확인

### 1. 백엔드 로그 확인

Docker 컨테이너 로그를 확인하여 API 키가 제대로 설정되었는지 확인:

```bash
# 백엔드 로그 실시간 확인
docker-compose logs -f backend
```

✅ **성공 시** (API 키 설정 완료):
```
로컬 MySQL DB 연결 성공 (db:3306/danawa)
...
(Gemini API 키 관련 오류 메시지 없음)
```

❌ **실패 시** (API 키 설정 안됨):
```
Gemini API 키가 설정되지 않았습니다. 간단한 응답 모드로 전환합니다.
```

### 2. 환경 변수 확인

컨테이너 내부에서 환경 변수 확인:

```bash
# 백엔드 컨테이너에 접속
docker exec -it danawa-backend sh

# 환경 변수 확인 (컨테이너 내부에서)
echo $GOOGLE_API_KEY

# 나가기
exit
```

---

## 📁 파일 구조

올바른 파일 위치:

```
danawa-py-crawler-11-17-crawler/
├── docker-compose.yml          ← Docker Compose 설정
├── .env                         ← API 키 저장 (여기에 만들기!)
├── .gitignore                   ← .env는 Git에 업로드 안됨 (보안)
├── crawler.py
├── webservice/
│   ├── Dockerfile
│   ├── pom.xml
│   └── src/
└── ...
```

---

## 🧪 챗봇 테스트

1. **브라우저에서 프론트엔드 열기**
   - http://localhost:3000

2. **챗봇 아이콘 클릭** (화면 우측 하단 💬)

3. **질문하기**:
   ```
   "SSD 추천해줘"
   "게임용 CPU 알려줘"
   "100만원 예산으로 PC 맞출 수 있어?"
   ```

4. **AI 모드 확인**:
   - ✅ 상세한 설명 포함
   - ✅ 제품별 장단점 비교
   - ✅ 사용자 맞춤 추천
   - ✅ 자연스러운 대화

---

## 🔧 트러블슈팅

### 문제 1: "API 키가 설정되지 않았습니다" 오류

**원인**: `.env` 파일이 제대로 생성되지 않았거나 위치가 잘못됨

**해결**:
```bash
# 1. .env 파일 위치 확인
ls -la .env

# 2. .env 파일 내용 확인
cat .env

# 3. 파일이 없으면 다시 생성
notepad .env  # Windows
# 또는
nano .env     # Linux/macOS

# 4. 내용 입력
GOOGLE_API_KEY=실제_API키

# 5. Docker Compose 재시작
docker-compose down
docker-compose up --build backend
```

### 문제 2: Docker가 .env 파일을 읽지 못함

**원인**: docker-compose.yml에 env_file 설정이 없거나 잘못됨

**해결**: `docker-compose.yml` 파일 확인 (backend 서비스 부분):
```yaml
backend:
  build:
    context: ./webservice
    dockerfile: Dockerfile
  container_name: danawa-backend
  depends_on:
    db:
      condition: service_healthy
  env_file:        # ← 이 부분이 있어야 함
    - ./.env       # ← 이 부분이 있어야 함
  ports:
    - "8080:8080"
  # ... 나머지 설정
```

### 문제 3: API 키에 공백이나 특수문자 포함

**원인**: `.env` 파일 작성 시 실수

**잘못된 예**:
```bash
GOOGLE_API_KEY = AIzaSy...    # ❌ 공백 있음
GOOGLE_API_KEY="AIzaSy..."    # ❌ 따옴표 있음
GOOGLE_API_KEY='AIzaSy...'    # ❌ 따옴표 있음
```

**올바른 예**:
```bash
GOOGLE_API_KEY=AIzaSyAaBbCcDdEeFfGgHhIiJjKkLlMmNnOoPpQq
```

### 문제 4: 여전히 간단한 응답만 나옴

**체크리스트**:
1. ✅ `.env` 파일이 프로젝트 **루트**에 있는지 확인
2. ✅ API 키가 **정확한지** 확인 (Google AI Studio에서 재확인)
3. ✅ Docker Compose를 **재시작**했는지 확인
4. ✅ 백엔드 로그에서 오류 메시지 확인
5. ✅ 인터넷 연결 확인

---

## 📝 .env 파일 템플릿

프로젝트 루트에 다음 내용으로 `.env` 파일을 만드세요:

```bash
# ==========================================
# Google Gemini API Configuration
# ==========================================
# 
# 발급 방법:
# 1. https://aistudio.google.com/app/apikey 접속
# 2. "Create API key" 클릭
# 3. 아래에 붙여넣기
#
# 주의사항:
# - 공백 없이 입력
# - 따옴표 사용 안 함
# - Git에 업로드 금지 (.gitignore에 포함됨)
#
# ==========================================

GOOGLE_API_KEY=여기에_발급받은_API키_입력

# 예시 (실제 API 키로 교체):
# GOOGLE_API_KEY=AIzaSyAaBbCcDdEeFfGgHhIiJjKkLlMmNnOoPpQq
```

---

## 🚀 빠른 재시작 명령어

설정 완료 후 빠르게 재시작:

```bash
# 1. 기존 컨테이너 중지
docker-compose down

# 2. 백엔드만 다시 시작 (빠름)
docker-compose up --build backend

# 3. 백엔드 로그 확인
docker-compose logs -f backend

# 4. 모든 서비스 재시작 (프론트엔드 포함)
docker-compose up --build
```

---

## 💡 추가 팁

### 개발 환경에서만 API 키 사용

`.env` 파일에 개발/프로덕션 구분:

```bash
# 개발 환경 (로컬)
GOOGLE_API_KEY=AIzaSy_개발용_API키

# 프로덕션 환경에서는 별도의 .env.production 사용
```

### API 사용량 확인

- [Google AI Studio](https://aistudio.google.com/app/apikey)에서 사용량 모니터링
- 무료 할당량: 월 1,500회 (개인 프로젝트 충분)

### 보안

- `.env` 파일은 `.gitignore`에 포함되어 Git에 업로드 안됨
- API 키 유출 시 즉시 재생성

---

## ✅ 설정 완료 확인

다음 단계를 모두 완료했는지 확인:

- [ ] Google AI Studio에서 API 키 발급
- [ ] 프로젝트 루트에 `.env` 파일 생성
- [ ] `.env` 파일에 `GOOGLE_API_KEY=실제키` 입력
- [ ] `docker-compose.yml`의 backend 서비스에 `env_file` 설정 확인
- [ ] Docker Compose 재시작 (`docker-compose down && docker-compose up --build`)
- [ ] 백엔드 로그에서 오류 메시지 없는지 확인
- [ ] 챗봇에서 AI 응답 테스트

---

## 📞 문의

설정 중 문제가 발생하면:
1. 백엔드 로그 확인: `docker-compose logs backend`
2. `.env` 파일 위치 및 내용 확인
3. API 키 유효성 확인 (Google AI Studio)

성공하면 챗봇이 훨씬 똑똑해집니다! 🎉

