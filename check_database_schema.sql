-- 데이터베이스 스키마 및 제약조건 확인 스크립트
-- 이 스크립트는 데이터가 안전하게 보존되는지 확인합니다.

-- 1. parts 테이블 구조 확인
SHOW CREATE TABLE parts;

-- 2. parts 테이블의 UNIQUE 제약조건 확인
SELECT 
    CONSTRAINT_NAME,
    COLUMN_NAME,
    CONSTRAINT_TYPE
FROM 
    INFORMATION_SCHEMA.TABLE_CONSTRAINTS tc
    JOIN INFORMATION_SCHEMA.KEY_COLUMN_USAGE kcu 
        ON tc.CONSTRAINT_NAME = kcu.CONSTRAINT_NAME
WHERE 
    tc.TABLE_SCHEMA = 'danawa'
    AND tc.TABLE_NAME = 'parts'
    AND tc.CONSTRAINT_TYPE = 'UNIQUE';

-- 3. part_spec 테이블의 UNIQUE 제약조건 확인
SELECT 
    CONSTRAINT_NAME,
    COLUMN_NAME,
    CONSTRAINT_TYPE
FROM 
    INFORMATION_SCHEMA.TABLE_CONSTRAINTS tc
    JOIN INFORMATION_SCHEMA.KEY_COLUMN_USAGE kcu 
        ON tc.CONSTRAINT_NAME = kcu.CONSTRAINT_NAME
WHERE 
    tc.TABLE_SCHEMA = 'danawa'
    AND tc.TABLE_NAME = 'part_spec'
    AND tc.CONSTRAINT_TYPE = 'UNIQUE';

-- 4. 현재 데이터 개수 확인
SELECT 
    category,
    COUNT(*) as count,
    MIN(created_at) as oldest_record,
    MAX(updated_at) as latest_update
FROM parts
GROUP BY category
ORDER BY category;

-- 5. 최근 업데이트된 상품 확인 (가격 변동 등)
SELECT 
    category,
    COUNT(*) as updated_count
FROM parts
WHERE updated_at > DATE_SUB(NOW(), INTERVAL 7 DAY)
GROUP BY category
ORDER BY category;

-- 6. 중복 link 확인 (있으면 안됨)
SELECT 
    link,
    COUNT(*) as duplicate_count
FROM parts
GROUP BY link
HAVING COUNT(*) > 1
LIMIT 10;

-- 7. parts와 part_spec 연결 상태 확인
SELECT 
    p.category,
    COUNT(p.id) as total_parts,
    COUNT(ps.id) as parts_with_specs,
    COUNT(p.id) - COUNT(ps.id) as parts_without_specs
FROM parts p
LEFT JOIN part_spec ps ON p.part_spec_id = ps.id
GROUP BY p.category
ORDER BY p.category;

