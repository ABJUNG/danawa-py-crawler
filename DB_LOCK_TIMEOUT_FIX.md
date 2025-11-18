# DB 락 타임아웃 문제 해결 가이드 🔧

## ✅ 적용된 수정 사항

### 1. 동시 처리 개수 감소
- **변경 전**: 기본값 10개
- **변경 후**: 기본값 5개
- **효과**: DB 락 충돌 가능성 감소

### 2. 재시도 로직 개선
- **재시도 횟수**: 3회 → 5회
- **대기 시간**: 지수 백오프 적용 (1초 → 2초 → 4초 → 8초 → 10초)
- **효과**: 일시적인 락 충돌 시 자동 복구

### 3. DB 연결 풀 설정 개선
- **pool_size**: 10 (동시 처리 개수보다 크게)
- **max_overflow**: 20 (추가 연결 허용)
- **pool_timeout**: 30초
- **효과**: 연결 풀 부족으로 인한 대기 시간 감소

### 4. 타임아웃 설정 추가
- **connect_timeout**: 10초
- **read_timeout**: 30초
- **write_timeout**: 30초
- **효과**: 네트워크 지연 시 안정성 향상

## 🚀 즉시 적용 방법

### 방법 1: 기본 설정 사용 (권장)
```bash
# 기본값 5개로 실행 (가장 안정적)
python crawler.py
```

### 방법 2: 더 안정적으로 실행 (락 타임아웃 발생 시)
```bash
# 동시 처리 3개로 줄이기
$env:MAX_CONCURRENT_ITEMS="3"; python crawler.py

# Windows CMD
set MAX_CONCURRENT_ITEMS=3 && python crawler.py

# Linux/Mac
MAX_CONCURRENT_ITEMS=3 python crawler.py
```

### 방법 3: 빠르게 실행 (락 타임아웃이 없는 경우)
```bash
# 동시 처리 7~8개로 증가 (주의: 락 타임아웃 발생 가능)
$env:MAX_CONCURRENT_ITEMS="7"; python crawler.py
```

## 🔧 MySQL 서버 설정 조정 (선택사항)

DB 락 타임아웃이 계속 발생하면 MySQL 서버 설정을 조정할 수 있습니다:

### 1. MySQL 설정 파일 수정

**Windows**: `C:\ProgramData\MySQL\MySQL Server X.X\my.ini`  
**Linux/Mac**: `/etc/mysql/my.cnf` 또는 `/etc/my.cnf`

```ini
[mysqld]
# 락 대기 시간 증가 (기본값: 50초)
innodb_lock_wait_timeout = 120

# 트랜잭션 격리 수준 (선택사항)
transaction_isolation = READ-COMMITTED

# InnoDB 버퍼 풀 크기 (메모리 여유가 있다면 증가)
innodb_buffer_pool_size = 1G
```

### 2. MySQL 서버 재시작

**Windows (서비스 관리자)**:
```powershell
# 서비스 이름 확인
Get-Service | Where-Object {$_.Name -like "*mysql*"}

# 서비스 재시작
Restart-Service MySQL80
```

**Linux/Mac**:
```bash
# Ubuntu/Debian
sudo systemctl restart mysql

# macOS (Homebrew)
brew services restart mysql
```

### 3. 런타임 설정 변경 (재시작 없이)

MySQL에 접속하여 즉시 적용:

```sql
-- 락 대기 시간 증가
SET GLOBAL innodb_lock_wait_timeout = 120;

-- 현재 설정 확인
SHOW VARIABLES LIKE 'innodb_lock_wait_timeout';
SHOW VARIABLES LIKE 'transaction_isolation';
```

**주의**: `SET GLOBAL`은 서버 재시작 시 초기화됩니다. 영구 적용하려면 설정 파일 수정이 필요합니다.

## 📊 권장 설정

### 안정성 우선 (락 타임아웃 방지)
```bash
# 동시 처리 3개
MAX_CONCURRENT_ITEMS=3 python crawler.py

# MySQL 설정
innodb_lock_wait_timeout = 120
```

### 균형 (속도와 안정성)
```bash
# 동시 처리 5개 (기본값)
python crawler.py

# MySQL 설정
innodb_lock_wait_timeout = 60
```

### 속도 우선 (락 타임아웃이 없는 경우)
```bash
# 동시 처리 7~8개
MAX_CONCURRENT_ITEMS=7 python crawler.py

# MySQL 설정
innodb_lock_wait_timeout = 30
```

## 🔍 문제 진단

### 락 타임아웃이 계속 발생하는 경우

1. **동시 처리 개수 확인**
   ```bash
   # 현재 설정 확인
   echo $MAX_CONCURRENT_ITEMS  # Linux/Mac
   echo %MAX_CONCURRENT_ITEMS%  # Windows CMD
   ```

2. **MySQL 락 상태 확인**
   ```sql
   -- 현재 락 대기 중인 쿼리 확인
   SELECT * FROM information_schema.innodb_locks;
   SELECT * FROM information_schema.innodb_lock_waits;
   
   -- 실행 중인 트랜잭션 확인
   SELECT * FROM information_schema.innodb_trx;
   ```

3. **로그 확인**
   - 크롤러 로그에서 "[DB 락 타임아웃]" 메시지 빈도 확인
   - MySQL 에러 로그 확인

## 💡 추가 최적화 팁

### 1. 인덱스 확인
`parts` 테이블의 `link` 컬럼에 인덱스가 있는지 확인:

```sql
-- 인덱스 확인
SHOW INDEX FROM parts;

-- 인덱스가 없으면 추가
CREATE INDEX idx_link ON parts(link);
```

### 2. 트랜잭션 최소화
- 트랜잭션 범위를 최소화하여 락 유지 시간 단축
- 이미 적용됨: 각 아이템별 독립 트랜잭션

### 3. 배치 처리 고려
- 여러 아이템을 한 번에 처리하는 대신 하나씩 처리
- 이미 적용됨: Semaphore로 동시 처리 제한

## ❓ 문제 해결

### Q1: 여전히 락 타임아웃이 발생해요
- 동시 처리 개수를 3개로 줄이세요
- MySQL `innodb_lock_wait_timeout`을 120초로 증가시키세요
- MySQL 서버 리소스(CPU, 메모리)를 확인하세요

### Q2: 크롤링 속도가 너무 느려요
- 동시 처리 개수를 5~7개로 증가시키세요
- 리뷰/벤치마크 수집을 비활성화하세요 (`--reviews`, `--benchmarks` 플래그 제거)
- 특정 카테고리만 크롤링하세요

### Q3: MySQL 서버 설정을 변경할 수 없어요
- 클라이언트 측 설정만으로도 충분합니다
- 동시 처리 개수를 3~5개로 유지하세요
- 재시도 로직이 자동으로 처리합니다

## 📞 추가 지원

문제가 계속 발생하거나 추가 최적화가 필요하면 알려주세요!

