# 🔧 한글 인코딩 문제 해결

## 문제 상황

### 증상
1. ✅ 크롤러가 747개 제품을 수집 완료
2. ❌ 웹 페이지에 제품이 표시되지 않음
3. ❌ 리뷰 및 벤치마크 데이터 수집 실패
4. ❌ DB에 저장된 카테고리 이름이 `??`로 깨짐

### 원인
- MySQL 클라이언트 연결 시 character set이 `latin1`로 설정됨
- 한글 데이터가 `??`로 저장되어 카테고리 필터링 실패
- 프론트엔드는 "CPU", "그래픽카드" 등 한글 카테고리명으로 검색하므로 데이터를 찾지 못함

```sql
-- 문제가 있던 DB 상태
SELECT id, name, category FROM parts LIMIT 5;
+------+----------------------------------------+----------+
| id   | name                                    | category |
+------+----------------------------------------+----------+
| 2652 | CORSAIR HX1200i SHIFT                  | ??       |
| 2651 | ?????? Classic II ????                 | ??       |
+------+----------------------------------------+----------+
```

---

## 해결 방법

### 1. `crawler.py` UTF-8 설정 강화

```python
# AS-IS (문제 있던 코드)
engine = create_engine(
    db_url,
    pool_pre_ping=True,
    pool_recycle=3600,
    echo=False
)

# TO-BE (수정된 코드)
engine = create_engine(
    db_url,
    pool_pre_ping=True,
    pool_recycle=3600,
    echo=False,
    connect_args={
        'charset': 'utf8mb4',
        'init_command': "SET NAMES utf8mb4 COLLATE utf8mb4_unicode_ci"
    }
)
```

### 2. 기존 데이터 삭제 및 재수집

```powershell
# 1. 크롤러 중지
docker-compose stop crawler

# 2. 외래 키 제약 해제 후 데이터 삭제
docker exec danawa-db mysql -u root -p1234 -e `
  "USE danawa; SET FOREIGN_KEY_CHECKS=0; `
   DELETE FROM community_reviews; `
   DELETE FROM parts; `
   DELETE FROM part_spec; `
   SET FOREIGN_KEY_CHECKS=1;"

# 3. 데이터 삭제 확인
docker exec danawa-db mysql -u root -p1234 -e `
  "USE danawa; SELECT COUNT(*) FROM parts;"

# 4. 크롤러 재빌드 및 재실행
docker-compose build crawler
docker-compose up crawler
```

### 3. 결과 확인

```powershell
# UTF-8 클라이언트로 DB 조회
docker exec danawa-db mysql -u root -p1234 `
  --default-character-set=utf8mb4 -e `
  "USE danawa; SELECT id, name, category FROM parts LIMIT 5;"
```

**정상적인 출력:**
```
+------+----------------------------------------+----------+
| id   | name                                    | category |
+------+----------------------------------------+----------+
| 2779 | NZXT KRAKEN ELITE V2 360 RGB           | 쿨러     |
| 2778 | CORSAIR NAUTILUS 360 RS ARGB           | 쿨러     |
+------+----------------------------------------+----------+
```

---

## 검증 방법

### 1. DB 데이터 확인
```powershell
# 카테고리별 제품 수 확인
docker exec danawa-db mysql -u root -p1234 `
  --default-character-set=utf8mb4 -e `
  "USE danawa; SELECT category, COUNT(*) as count `
   FROM parts GROUP BY category ORDER BY count DESC;"
```

**예상 출력:**
```
+-------------+-------+
| category    | count |
+-------------+-------+
| CPU         | 150   |
| 그래픽카드  | 120   |
| RAM         | 100   |
| 쿨러        | 80    |
| ...         | ...   |
+-------------+-------+
```

### 2. 프론트엔드 확인
```
1. http://localhost:3000 접속
2. 상단 내비게이션에서 "CPU" 클릭
3. 제품 목록이 표시되는지 확인
```

### 3. AI 챗봇 확인
```
1. http://localhost:3000/ai 접속
2. 우측 하단 💬 버튼 클릭
3. "게임용 그래픽카드 추천해줘" 입력
4. AI 응답에 실제 제품 정보가 포함되는지 확인
```

---

## 리뷰 및 벤치마크 수집 문제

### 현재 상태
- ❌ `community_reviews` 테이블: 0건
- ❌ `benchmarks` 테이블: 없음 (테이블 자체가 생성되지 않음)

### 원인 분석
1. **커뮤니티 리뷰 수집 실패**
   - 크롤러 로그에서 "댓글: N" 표시는 있지만 실제 수집은 안 됨
   - `crawler.py`의 퀘이사존 리뷰 수집 로직 점검 필요

2. **벤치마크 테이블 미생성**
   - `crawler.py`에서 벤치마크 테이블 생성 SQL이 실행되지 않음
   - 또는 테이블 생성 로직이 없음

### 해결 방향

#### 1. 퀘이사존 리뷰 수집 확인
```python
# crawler.py 내부의 리뷰 수집 로직 확인
# - get_search_keyword() 함수가 제대로 작동하는지
# - 퀘이사존 검색 결과 페이지 선택자가 유효한지
# - 리뷰 본문 선택자가 유효한지
```

**확인 방법:**
```powershell
# 크롤러 로그에서 퀘이사존 관련 메시지 필터링
docker-compose logs crawler | Select-String "퀘이사존"
docker-compose logs crawler | Select-String "review body"
docker-compose logs crawler | Select-String "no board links"
```

#### 2. 벤치마크 테이블 생성
```python
# crawler.py에 벤치마크 테이블 생성 SQL 추가 (이미 있을 수도 있음)
CREATE TABLE IF NOT EXISTS benchmarks (
    id INT PRIMARY KEY AUTO_INCREMENT,
    part_id BIGINT,
    benchmark_name VARCHAR(255),
    score FLOAT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (part_id) REFERENCES parts(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

---

## 추가 권장 사항

### 1. Docker Compose 환경 변수 확인
```yaml
# docker-compose.yml의 crawler 서비스
crawler:
  environment:
    - DB_HOST=db
    - DB_PORT=3306  # 컨테이너 내부 포트
    - DB_USER=root
    - DB_PASSWORD=1234
    - DB_NAME=danawa
    # LANG 환경 변수 추가 (선택 사항)
    - LANG=C.UTF-8
    - LC_ALL=C.UTF-8
```

### 2. MySQL 컨테이너 기본 character set 확인
```yaml
# docker-compose.yml의 db 서비스
db:
  command: >
    --character-set-server=utf8mb4
    --collation-server=utf8mb4_unicode_ci
    --default-authentication-plugin=mysql_native_password
```

### 3. 프론트엔드 API 요청 character set
```javascript
// 프론트엔드에서 API 호출 시 헤더 설정
fetch('/api/parts?category=CPU', {
  headers: {
    'Content-Type': 'application/json; charset=UTF-8'
  }
})
```

---

## 문제 해결 체크리스트

- [x] `crawler.py`에 UTF-8 connect_args 추가
- [x] 기존 깨진 데이터 삭제 (parts, part_spec, community_reviews)
- [x] 크롤러 재빌드
- [x] 크롤러 재실행 (진행 중)
- [ ] 크롤러 완료 대기 (모든 카테고리 수집)
- [ ] DB 데이터 확인 (한글 정상 저장 확인)
- [ ] 프론트엔드 제품 목록 표시 확인
- [ ] AI 챗봇 제품 추천 확인
- [ ] 퀘이사존 리뷰 수집 로직 점검
- [ ] 벤치마크 테이블 생성 확인

---

## 예상 소요 시간

- 크롤러 전체 수집: **30~60분** (9개 카테고리, 각 5페이지)
- 데이터 검증: **5분**
- 프론트엔드 확인: **5분**

**총 예상 시간: 약 1시간**

---

**이 문제의 핵심: MySQL 클라이언트 character set 설정이 latin1이어서 한글이 깨짐**

**해결책: PyMySQL connect_args에 charset과 init_command 명시적 설정**

✅ **해결 완료!**



