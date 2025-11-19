-- CPU 데이터 확인 스크립트

-- 1. CPU 카테고리 상품 개수 확인
SELECT COUNT(*) as cpu_count FROM parts WHERE category = 'CPU';

-- 2. CPU 상품 목록 확인 (최대 10개)
SELECT id, name, category, price, manufacturer, created_at 
FROM parts 
WHERE category = 'CPU' 
ORDER BY created_at DESC 
LIMIT 10;

-- 3. PartSpec이 있는 CPU 상품 개수 확인
SELECT COUNT(*) as cpu_with_specs
FROM parts p
LEFT JOIN part_spec ps ON p.part_spec_id = ps.id
WHERE p.category = 'CPU' AND ps.id IS NOT NULL;

-- 4. PartSpec이 없는 CPU 상품 개수 확인
SELECT COUNT(*) as cpu_without_specs
FROM parts p
LEFT JOIN part_spec ps ON p.part_spec_id = ps.id
WHERE p.category = 'CPU' AND ps.id IS NULL;

-- 5. 모든 카테고리별 상품 개수 확인
SELECT category, COUNT(*) as count 
FROM parts 
GROUP BY category 
ORDER BY category;

