# 크롤러 MySQL 연결 오류 수정 가이드 🔧

## 🐛 발생했던 오류

```
(pymysql.err.OperationalError) (2013, 'Lost connection to MySQL server during query (timed out)')
```

이 오류는 크롤러가 MySQL 서버와의 연결이 쿼리 실행 도중 끊긴 경우 발생합니다.

## 🎯 원인 분석

### 1. MySQL 서버 타임아웃
- MySQL 서버의 `wait_timeout`, `interactive_timeout`이 기본값(8시간)보다 짧게 설정되어 있을 경우
- 유휴 연결이 서버에 의해 강제로 종료됨

### 2. 연결 풀 설정 부족
- 동시 처리 개수에 비해 연결 풀 크기가 작음
- 연결 풀 타임아웃이 짧아 새 연결 대기 중 오류 발생

### 3. 네트워크 타임아웃
- `read_timeout`, `write_timeout`이 실제 쿼리 실행 시간보다 짧음
- 긴 트랜잭션이나 복잡한 쿼리 실행 시 타임아웃 발생

### 4. 동시 연결 과다
- 너무 많은 동시 요청으로 인해 MySQL 서버가 부하를 받음
- `max_connections` 한계에 도달하여 새 연결 거부

## ✅ 적용된 수정 사항

### 1. SQLAlchemy 엔진 설정 개선 (`crawler.py` 76-92줄)

#### 이전 설정
```python
engine = create_engine(
    db_url,
    pool_pre_ping=True,
    pool_recycle=3600,      # 1시간
    pool_size=10,
    max_overflow=20,
    pool_timeout=30,
    connect_args={
        'connect_timeout': 10,
        'read_timeout': 30,
        'write_timeout': 30,
    }
)
```

#### 수정 후 설정
```python
engine = create_engine(
    db_url,
    pool_pre_ping=True,      # ✅ 연결 상태 확인 (끊긴 연결 자동 감지)
    pool_recycle=1800,       # ✅ 30분마다 연결 재생성 (더 빈번한 갱신)
    pool_size=15,            # ✅ 연결 풀 크기 증가 (10 -> 15)
    max_overflow=30,         # ✅ 추가 연결 허용 증가 (20 -> 30)
    pool_timeout=60,         # ✅ 연결 풀 타임아웃 증가 (30초 -> 60초)
    connect_args={
        'connect_timeout': 30,   # ✅ 연결 타임아웃 증가 (10초 -> 30초)
        'read_timeout': 120,     # ✅ 읽기 타임아웃 증가 (30초 -> 120초)
        'write_timeout': 120,    # ✅ 쓰기 타임아웃 증가 (30초 -> 120초)
        'autocommit': False,     # ✅ 명시적 트랜잭션 사용
    }
)
```

**주요 변경점**:
- `pool_recycle`: 3600초(1시간) → 1800초(30분)
  - MySQL 서버의 타임아웃보다 짧게 설정하여 끊긴 연결 사용 방지
- `pool_size`: 10 → 15
  - 동시 처리 개수(3개)보다 충분히 크게 설정
- `max_overflow`: 20 → 30
  - 피크 시간대 추가 연결 허용
- `pool_timeout`: 30초 → 60초
  - 연결 대기 시간 증가
- `connect_timeout`: 10초 → 30초
  - 느린 네트워크 환경 대응
- `read_timeout/write_timeout`: 30초 → 120초
  - 긴 쿼리 실행 시간 허용

### 2. 동시 처리 개수 감소 (`crawler.py` 35줄)

```python
# 이전: MAX_CONCURRENT_ITEMS = 5
# 수정: MAX_CONCURRENT_ITEMS = 3
MAX_CONCURRENT_ITEMS = int(os.getenv('MAX_CONCURRENT_ITEMS', '3'))
```

**이유**:
- 동시 처리 개수를 줄여 MySQL 서버 부하 감소
- 안정성 우선 (속도는 약간 느려지지만 오류 발생 감소)

### 3. 재시도 로직 강화 (`crawler.py` 3364-3413줄)

#### 이전 로직
- `Lock wait timeout`만 처리
- 재시도 3회
- 단순한 에러 메시지

#### 수정 후 로직
```python
# 재시도 가능한 오류 패턴 확장
retryable_errors = [
    "1205",                    # Lock wait timeout
    "2013",                    # ✅ Lost connection to MySQL server (새로 추가)
    "2006",                    # ✅ MySQL server has gone away (새로 추가)
    "lock wait timeout",
    "lost connection",         # ✅ 연결 끊김 (새로 추가)
    "timeout",
    "connection reset",        # ✅ 연결 리셋 (새로 추가)
    "broken pipe",             # ✅ 파이프 끊김 (새로 추가)
]
```

**개선 사항**:
- ✅ **재시도 횟수 증가**: 3회 → 5회
- ✅ **지수 백오프 개선**: 2초, 4초, 8초, 16초, 32초 (최대 30초)
- ✅ **연결 풀 재생성**: 연결 끊김 오류 시 `engine.dispose()` 호출
- ✅ **상세한 에러 정보**: 오류 타입 구분 (연결 오류 vs 락 타임아웃)
- ✅ **해결 방법 안내**: 오류 발생 시 권장 조치 출력

### 4. 상세한 에러 메시지

```python
# 재시도 중 메시지
print(f"     [연결 오류] {product_name} - {retry_count}/{max_retries}회 재시도 중... ({wait_time}초 대기)")
print(f"         상세: {str(e)[:100]}")

# 연결 풀 재생성
print(f"         -> 연결 풀 재생성 완료")

# 최대 재시도 초과 시
print(f"     [권장 조치]")
print(f"       1. 동시 처리 개수 줄이기: MAX_CONCURRENT_ITEMS=3")
print(f"       2. MySQL wait_timeout 증가: SET GLOBAL wait_timeout=28800")
print(f"       3. MySQL max_connections 증가: SET GLOBAL max_connections=500")
```

## 🔧 MySQL 서버 설정 권장사항

크롤러를 더 안정적으로 실행하려면 MySQL 서버 설정을 조정하세요.

### Windows (MySQL Workbench 또는 CLI)

```sql
-- 1. 현재 설정 확인
SHOW VARIABLES LIKE 'wait_timeout';
SHOW VARIABLES LIKE 'interactive_timeout';
SHOW VARIABLES LIKE 'max_connections';

-- 2. 타임아웃 증가 (8시간)
SET GLOBAL wait_timeout = 28800;
SET GLOBAL interactive_timeout = 28800;

-- 3. 최대 연결 수 증가
SET GLOBAL max_connections = 500;

-- 4. 트랜잭션 타임아웃 증가
SET GLOBAL innodb_lock_wait_timeout = 120;
```

### my.ini 또는 my.cnf 파일 수정 (영구 적용)

**파일 위치**:
- Windows: `C:\ProgramData\MySQL\MySQL Server X.X\my.ini`
- Linux: `/etc/mysql/my.cnf` 또는 `/etc/my.cnf`

```ini
[mysqld]
# 연결 타임아웃 (8시간)
wait_timeout = 28800
interactive_timeout = 28800

# 최대 연결 수
max_connections = 500

# InnoDB 설정
innodb_lock_wait_timeout = 120
innodb_buffer_pool_size = 2G

# 쿼리 캐시 (MySQL 5.7 이하)
query_cache_size = 64M
query_cache_limit = 2M
```

**적용 방법**:
1. MySQL 서비스 재시작
   - Windows: 서비스 관리자에서 "MySQL" 재시작
   - Linux: `sudo systemctl restart mysql`

## 🚀 크롤러 실행 방법

### 기본 실행 (동시 처리 3개)
```bash
python crawler.py
```

### 더 안정적으로 실행 (동시 처리 2개)
```bash
MAX_CONCURRENT_ITEMS=2 python crawler.py
```

### 더 빠르게 실행 (동시 처리 5개) - MySQL 설정 최적화 후
```bash
MAX_CONCURRENT_ITEMS=5 python crawler.py
```

## 📊 성능 vs 안정성 가이드

### 안정성 우선 (오류 최소화)
```bash
MAX_CONCURRENT_ITEMS=2 python crawler.py
```
- 속도: ★☆☆☆☆ (가장 느림)
- 안정성: ★★★★★ (오류 거의 없음)
- 권장 상황: 처음 크롤링, 불안정한 네트워크

### 균형 (기본 설정)
```bash
MAX_CONCURRENT_ITEMS=3 python crawler.py
```
- 속도: ★★★☆☆ (보통)
- 안정성: ★★★★☆ (안정적)
- 권장 상황: 일반적인 사용

### 속도 우선 (MySQL 최적화 필요)
```bash
MAX_CONCURRENT_ITEMS=5 python crawler.py
```
- 속도: ★★★★☆ (빠름)
- 안정성: ★★★☆☆ (가끔 오류)
- 권장 상황: MySQL 서버 설정 최적화 완료, 빠른 네트워크

### 최고 속도 (고성능 서버)
```bash
MAX_CONCURRENT_ITEMS=8 python crawler.py
```
- 속도: ★★★★★ (매우 빠름)
- 안정성: ★★☆☆☆ (오류 가능)
- 권장 상황: 전용 MySQL 서버, 고성능 네트워크, 테스트 완료

## 🔍 트러블슈팅

### 여전히 연결 오류가 발생하는 경우

#### 1. MySQL 로그 확인
```bash
# Windows
C:\ProgramData\MySQL\MySQL Server X.X\data\*.err

# Linux
/var/log/mysql/error.log
```

#### 2. 동시 처리 개수 추가 감소
```bash
MAX_CONCURRENT_ITEMS=1 python crawler.py
```

#### 3. 네트워크 확인
```bash
# MySQL 서버 응답 시간 측정
ping localhost

# MySQL 서버 연결 테스트
mysql -h localhost -P 3307 -u root -p
```

#### 4. MySQL 프로세스 확인
```sql
-- 현재 연결 수 확인
SHOW STATUS LIKE 'Threads_connected';
SHOW STATUS LIKE 'Max_used_connections';

-- 실행 중인 쿼리 확인
SHOW PROCESSLIST;

-- 긴 쿼리 확인
SELECT * FROM information_schema.processlist 
WHERE TIME > 30;
```

#### 5. 크롤러 로그 확인
- `[연결 오류]` 메시지가 반복되면 MySQL 서버 설정 확인
- `[DB 락 타임아웃]` 메시지가 반복되면 동시 처리 개수 감소
- 특정 제품에서만 오류 발생하면 해당 제품의 스펙 페이지 확인

## 📝 추가 최적화 팁

### 1. 벤치마크/리뷰 수집 분리
```bash
# 1단계: 기본 정보만 수집 (빠름)
python crawler.py

# 2단계: 벤치마크 수집 (느림)
python crawler.py --benchmarks

# 3단계: 리뷰 수집 (느림)
python crawler.py --reviews
```

### 2. 특정 카테고리만 크롤링
`crawler.py` 파일의 `CATEGORIES` 수정:
```python
# 전체 카테고리
CATEGORIES = {
    'CPU': 'cpu', 
    '쿨러': 'cooler&attribute=...',
    '메인보드': 'mainboard',
    # ...
}

# CPU만 크롤링 (테스트용)
CATEGORIES = {
    'CPU': 'cpu'
}
```

### 3. 페이지 수 조정
```python
# crawler.py 파일 상단
CRAWL_PAGES = 2  # 각 카테고리별 2페이지만 수집 (기본값)
```

## ✅ 수정 완료 체크리스트

- ✅ SQLAlchemy 연결 타임아웃 증가 (30초 → 120초)
- ✅ 연결 풀 크기 증가 (10 → 15)
- ✅ 연결 재생성 주기 단축 (1시간 → 30분)
- ✅ 동시 처리 개수 감소 (5 → 3)
- ✅ 재시도 로직 강화 (연결 끊김 오류 처리 추가)
- ✅ 연결 풀 재생성 로직 추가
- ✅ 상세한 에러 메시지 및 해결 방법 안내
- ✅ MySQL 서버 설정 권장사항 문서화

## 📞 추가 지원

크롤러 실행 중 문제가 지속되면:
1. 오류 메시지 전체 복사
2. MySQL 서버 버전 확인
3. 네트워크 환경 확인 (로컬 vs 원격)
4. MySQL 설정 파일 공유

이 정보를 제공하면 더 정확한 해결책을 제시할 수 있습니다!

