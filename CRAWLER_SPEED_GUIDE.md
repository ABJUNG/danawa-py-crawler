# 크롤러 속도 최적화 가이드 ⚡

## 🎯 적용된 개선 사항

### 1. 동시 처리 개수 증가
- **변경 전**: 3개씩 순차 처리
- **변경 후**: 10개씩 병렬 처리 (기본값)
- **예상 속도 향상**: **3~5배**

### 2. 환경 변수로 조정 가능
이제 코드 수정 없이 환경 변수로 크롤러 속도를 조정할 수 있습니다.

## 🚀 크롤러 실행 방법

### 기본 실행 (권장)
```bash
python crawler.py
```

### 더 빠른 실행 (동시 처리 15개)
```bash
# Windows PowerShell
$env:MAX_CONCURRENT_ITEMS="15"; python crawler.py

# Windows CMD
set MAX_CONCURRENT_ITEMS=15 && python crawler.py

# Linux/Mac
MAX_CONCURRENT_ITEMS=15 python crawler.py
```

### 최고 속도 (동시 처리 20개, 타임아웃 단축)
```bash
# Windows PowerShell
$env:MAX_CONCURRENT_ITEMS="20"; $env:PAGE_LOAD_TIMEOUT="20000"; $env:ELEMENT_TIMEOUT="3000"; python crawler.py

# Windows CMD
set MAX_CONCURRENT_ITEMS=20 && set PAGE_LOAD_TIMEOUT=20000 && set ELEMENT_TIMEOUT=3000 && python crawler.py

# Linux/Mac
MAX_CONCURRENT_ITEMS=20 PAGE_LOAD_TIMEOUT=20000 ELEMENT_TIMEOUT=3000 python crawler.py
```

### 리뷰/벤치마크 제외 (가장 빠름)
벤치마크와 리뷰 수집을 건너뛰면 **5~10배 더 빠릅니다**:
```bash
# 기본 상품 정보만 수집 (리뷰/벤치마크 제외)
python crawler.py
# 기본적으로 --reviews와 --benchmarks 플래그가 없으면 수집하지 않음

# 리뷰 포함 (느림)
python crawler.py --reviews

# 벤치마크 포함 (느림)
python crawler.py --benchmarks

# 둘 다 포함 (가장 느림)
python crawler.py --reviews --benchmarks
```

## ⚙️ 설정 파일 직접 수정

`crawler.py` 파일 상단의 설정을 직접 수정할 수도 있습니다:

```python
# crawler.py 17-42줄
# ===== [속도 최적화 설정] =====

# 동시 처리할 상품 개수 (기본: 10, 권장 범위: 5~20)
MAX_CONCURRENT_ITEMS = 10  # <- 이 값을 15~20으로 변경

# 페이지 로딩 최대 대기 시간 (ms, 기본: 30000 = 30초)
PAGE_LOAD_TIMEOUT = 30000  # <- 20000으로 줄이면 빠름

# 개별 요소 대기 시간 (ms, 기본: 5000 = 5초)
ELEMENT_TIMEOUT = 5000  # <- 3000으로 줄이면 빠름
```

## 📊 속도 비교

| 설정 | 예상 처리 시간 (페이지당) | 배속 |
|-----|----------------------|------|
| **변경 전** (동시 3개) | ~180초 | 1x |
| **기본 설정** (동시 10개) | ~60초 | 3x ⚡ |
| **빠른 설정** (동시 15개) | ~40초 | 4.5x ⚡⚡ |
| **최고 속도** (동시 20개 + 타임아웃 단축) | ~30초 | 6x ⚡⚡⚡ |
| **리뷰/벤치마크 제외** | ~10초 | 18x ⚡⚡⚡⚡ |

*실제 속도는 네트워크, CPU, DB 성능에 따라 다를 수 있습니다.*

## ⚠️ 주의사항

### 1. 동시 처리 개수가 너무 높으면
- **장점**: 크롤링 속도 증가
- **단점**: 
  - DB 락 타임아웃 발생 가능
  - 메모리 사용량 증가
  - 다나와 서버에서 차단될 가능성 증가

**권장값**: 10~15 (안전), 15~20 (빠르지만 불안정할 수 있음)

### 2. 타임아웃을 너무 짧게 설정하면
- 느린 네트워크에서 데이터 누락 가능
- 에러 로그가 많이 발생할 수 있음

**권장값**: 
- PAGE_LOAD_TIMEOUT: 20000~30000
- ELEMENT_TIMEOUT: 3000~5000

### 3. DB 락 타임아웃 오류 발생 시
다음과 같은 오류가 발생하면 동시 처리 개수를 줄이세요:
```
pymysql.err.OperationalError: (1205, 'Lock wait timeout exceeded')
```

해결 방법:
```bash
# 동시 처리 개수를 5~7로 줄이기
MAX_CONCURRENT_ITEMS=7 python crawler.py
```

또는 MySQL 설정 변경:
```sql
-- MySQL에서 실행
SET GLOBAL innodb_lock_wait_timeout = 120;
```

## 🎯 추천 설정

### 안정성 우선 (처음 사용 시)
```bash
# 기본 설정 사용 (동시 10개)
python crawler.py
```

### 속도 우선 (네트워크/DB가 좋은 환경)
```bash
# 동시 15개, 타임아웃 단축
MAX_CONCURRENT_ITEMS=15 PAGE_LOAD_TIMEOUT=20000 python crawler.py
```

### 최고 속도 (실험적)
```bash
# 동시 20개, 타임아웃 최소화, 리뷰/벤치마크 제외
MAX_CONCURRENT_ITEMS=20 PAGE_LOAD_TIMEOUT=15000 ELEMENT_TIMEOUT=2000 python crawler.py
```

## 📈 성능 모니터링

크롤러 실행 중 다음을 확인하세요:

1. **처리 속도**: 콘솔 로그에서 상품 처리 속도 확인
   ```
   [처리 완료] AMD 라이젠 7 7800X3D (용량: 기본, 가격: 486,720원)
   ```

2. **오류 발생**: `(경고)`, `(오류)`, `Exception` 메시지 확인

3. **메모리 사용량**: 작업 관리자에서 Python 프로세스 확인

4. **DB 연결**: 오류가 반복되면 동시 처리 개수 줄이기

## 🔧 추가 최적화 팁

### 1. 특정 카테고리만 크롤링
`crawler.py` 파일에서 불필요한 카테고리 주석 처리:
```python
# crawler.py 49-58줄
CATEGORIES = {
    # 'CPU': 'cpu',  # <- 주석 처리하면 제외
    # '쿨러': 'cooler&attribute=687-4015-OR%2C687-4017-OR',
    '메인보드': 'mainboard',  # <- 이것만 수집
    # 'RAM': 'RAM',
    # ...
}
```

### 2. 페이지 수 제한
```python
# crawler.py 21줄
CRAWL_PAGES = 1  # <- 1페이지만 수집 (기본: 2)
```

### 3. Headless 모드 사용
```python
# crawler.py 24줄
HEADLESS_MODE = True  # <- 브라우저 창 숨기기 (약간 빠름)
```

### 4. SLOW_MOTION 비활성화
```python
# crawler.py 27줄
SLOW_MOTION = 0  # <- 지연 시간 제거 (봇 탐지 위험 증가)
```

## ❓ 문제 해결

### Q1: 크롤러가 너무 느려요
- 리뷰/벤치마크 수집을 비활성화하세요 (기본값)
- `MAX_CONCURRENT_ITEMS`를 15~20으로 증가하세요
- 특정 카테고리만 수집하도록 설정하세요

### Q2: DB 락 타임아웃 오류가 발생해요
- `MAX_CONCURRENT_ITEMS`를 5~7로 줄이세요
- MySQL `innodb_lock_wait_timeout` 값을 증가시키세요

### Q3: 메모리 부족 오류가 발생해요
- `MAX_CONCURRENT_ITEMS`를 줄이세요
- 브라우저를 재시작하는 간격을 줄이세요 (RESTART_INTERVAL)

### Q4: 다나와에서 차단당한 것 같아요
- `SLOW_MOTION`을 50~100으로 증가하세요
- `MAX_CONCURRENT_ITEMS`를 5 이하로 줄이세요
- 크롤링 간격을 늘리세요 (예: 하루 1~2회)

## 📞 추가 지원

문제가 계속 발생하거나 추가 최적화가 필요하면 알려주세요!

