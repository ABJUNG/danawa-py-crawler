# Cloud Run 크롤러 Timeout 문제 해결 가이드

## 문제 상황
로컬에서는 정상 작동하지만 GCP Cloud Run에서 다음 오류 발생:
```
-> (오류) 리뷰 본문을 찾을 수 없습니다. (timeout)
```

## 원인 분석

### 1. Cloud Run 환경의 제약
- **네트워크 속도**: Cloud Run의 아웃바운드 네트워크가 로컬보다 느릴 수 있음
- **CPU/메모리 제한**: 기본 설정(1 CPU, 512Mi 메모리)으로는 Chromium 브라우저 실행이 느림
- **Cold Start**: 첫 실행 시 브라우저 초기화 시간이 오래 걸림

### 2. 퀘이사존 페이지의 특성
- **JavaScript 렌더링**: 페이지 로딩 후 추가 JavaScript 실행 필요
- **동적 콘텐츠**: `.view-content` 요소가 지연 로딩됨
- **광고/트래킹 스크립트**: 추가 네트워크 요청으로 로딩 지연

## 적용된 해결책

### ✅ 1. 페이지 로딩 전략 개선

**변경 전:**
```python
await new_page.goto(review_url, wait_until='load', timeout=30000)
content_element = new_page.locator('.view-content')
if not await content_element.is_visible(timeout=10000):
    print("오류")
```

**변경 후:**
```python
# networkidle로 변경 (모든 네트워크 요청 완료 대기)
try:
    await new_page.goto(review_url, wait_until='networkidle', timeout=45000)
except:
    await new_page.goto(review_url, wait_until='load', timeout=30000)

# JavaScript 렌더링 대기
await new_page.wait_for_timeout(2000)

# 여러 셀렉터 시도 (페이지 구조 변경 대응)
selectors = ['.view-content', '.article-content', '.content-body', ...]
for selector in selectors:
    if element found:
        break
```

### ✅ 2. Chromium 브라우저 옵션 최적화

Cloud Run 환경을 위한 필수 플래그 추가:

```python
browser = await p.chromium.launch(
    headless=True,
    args=[
        '--no-sandbox',                # Cloud Run 필수 (권한 문제 해결)
        '--disable-setuid-sandbox',    # Cloud Run 필수
        '--disable-dev-shm-usage',     # /dev/shm 메모리 부족 방지
        '--disable-gpu',               # GPU 비활성화 (서버 환경)
        '--disable-software-rasterizer',
        '--disable-extensions',
        '--disable-background-networking',
        '--window-size=1920,1080'
    ]
)
```

### ✅ 3. 타임아웃 시간 증가

- 페이지 로딩: 30초 → 45초
- 요소 찾기: 10초 → 5초 × 여러 셀렉터 시도
- JavaScript 렌더링 대기: 추가 2초

## Cloud Run 배포 설정

### 1. 메모리 및 CPU 증가

**cloudbuild.yaml 수정:**
```yaml
steps:
  - name: 'gcr.io/cloud-builders/docker'
    args: ['build', '-f', 'Dockerfile.crawler', '-t', 'gcr.io/$PROJECT_ID/crawler', '.']
  - name: 'gcr.io/cloud-builders/docker'
    args: ['push', 'gcr.io/$PROJECT_ID/crawler']
  - name: 'gcr.io/google.com/cloudsdktool/cloud-sdk'
    entrypoint: gcloud
    args:
      - 'run'
      - 'deploy'
      - 'crawler'
      - '--image=gcr.io/$PROJECT_ID/crawler'
      - '--region=asia-northeast3'
      - '--platform=managed'
      - '--memory=2Gi'              # ← 512Mi → 2Gi
      - '--cpu=2'                   # ← 1 → 2
      - '--timeout=3600'            # ← 300초 → 3600초 (1시간)
      - '--max-instances=1'         # 동시 실행 방지
      - '--no-allow-unauthenticated'
```

### 2. 환경 변수 설정

```bash
gcloud run services update crawler \
  --region=asia-northeast3 \
  --set-env-vars="HEADLESS_MODE=True" \
  --set-env-vars="CRAWL_PAGES=2" \
  --set-env-vars="SLOW_MOTION=20"
```

### 3. Concurrency 설정

```bash
gcloud run services update crawler \
  --region=asia-northeast3 \
  --concurrency=1  # 한 번에 하나의 요청만 처리
```

## 추가 최적화 팁

### 1. 스크린샷 디버깅 (임시)

문제가 계속되면 스크린샷을 저장하여 페이지 상태 확인:

```python
if content_element is None:
    await new_page.screenshot(path=f"debug_{part_id}.png")
    # Cloud Storage에 업로드하는 코드 추가
```

### 2. 로깅 레벨 증가

```python
# crawler.py 상단에 추가
import logging
logging.basicConfig(level=logging.DEBUG)
```

### 3. 재시도 로직 추가

리뷰 수집 실패 시 재시도:

```python
async def scrape_quasarzone_reviews_with_retry(browser, conn, sql_review, part_id, ...):
    max_retries = 3
    for attempt in range(max_retries):
        try:
            await scrape_quasarzone_reviews(browser, conn, sql_review, part_id, ...)
            break
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            print(f"재시도 {attempt + 1}/{max_retries}...")
            await asyncio.sleep(5)
```

## 성능 모니터링

### Cloud Run 메트릭 확인

```bash
# 메모리 사용량 확인
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=crawler" \
  --limit 50 --format json

# 실행 시간 확인
gcloud run services describe crawler --region=asia-northeast3 --format="value(status.url)"
```

### 크롤러 성능 로그 추가

```python
import time

start_time = time.time()
# 크롤링 작업
elapsed = time.time() - start_time
print(f"[성능] 리뷰 수집 완료: {elapsed:.2f}초")
```

## 비용 최적화

Cloud Run은 실행 시간과 메모리 사용량에 따라 과금됩니다.

### 권장 설정:
- **메모리**: 2Gi (Chromium 실행에 충분)
- **CPU**: 2 (병렬 처리 최소 수준)
- **Timeout**: 3600초 (1시간)
- **Max Instances**: 1 (비용 절감)

### 예상 비용 (서울 리전):
- 2 vCPU, 2Gi 메모리
- 1시간 실행
- 월 1회 실행 시: **약 $0.30 미만**

## 트러블슈팅 체크리스트

실행 실패 시 다음을 확인하세요:

- [ ] Cloud Run 메모리가 2Gi 이상인가?
- [ ] Timeout이 1시간(3600초)으로 설정되었나?
- [ ] `--no-sandbox` 플래그가 포함되었나?
- [ ] HEADLESS_MODE가 True로 설정되었나?
- [ ] 서비스 계정에 Cloud SQL 접근 권한이 있나?
- [ ] 퀘이사존이 차단하지 않았나? (User-Agent 확인)

## 참고 자료

- [Cloud Run 메모리 제한](https://cloud.google.com/run/docs/configuring/memory-limits)
- [Playwright Docker 가이드](https://playwright.dev/docs/docker)
- [Chrome Headless 플래그 목록](https://peter.sh/experiments/chromium-command-line-switches/)

## 문제 지속 시

여전히 timeout이 발생하면:

1. **로컬에서 실제 퀘이사존 URL 테스트**
   ```bash
   python -c "from playwright.sync_api import sync_playwright; \
   p = sync_playwright().start(); \
   browser = p.chromium.launch(headless=True, args=['--no-sandbox']); \
   page = browser.new_page(); \
   page.goto('https://quasarzone.com/bbs/qc_qsz/views/2033914'); \
   print(page.content())"
   ```

2. **퀘이사존 API 사용 검토** (가능하다면)

3. **크롤링 빈도 조절** (봇 탐지 회피)
   - SLOW_MOTION 값 증가
   - 요청 간 딜레이 추가
   - User-Agent 로테이션

4. **Headless=False로 로컬 테스트**
   실제 브라우저를 띄워서 페이지 로딩 상태 확인


