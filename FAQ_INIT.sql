-- PC FAQ 테이블 생성 (이미 존재하면 건너뜀)
CREATE TABLE IF NOT EXISTS pc_faq (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    question VARCHAR(500) NOT NULL,
    answer TEXT NOT NULL,
    category VARCHAR(50),
    keywords VARCHAR(255),
    view_count INT DEFAULT 0,
    helpful_count INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_category (category),
    INDEX idx_keywords (keywords)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 기존 데이터 삭제 (재실행 시)
TRUNCATE TABLE pc_faq;

-- FAQ 데이터 삽입 (상위 20개 핵심 질문)

-- CPU 관련
INSERT INTO pc_faq (question, answer, category, keywords) VALUES
('CPU를 선택할 때 코어 수와 클럭 속도 중 뭐가 더 중요한가요?', 
'용도에 따라 다릅니다!\n\n• **게임**: 클럭 속도가 더 중요 (6코어 이상 권장)\n• **영상편집/렌더링**: 코어 수가 더 중요 (8코어 이상 권장)\n• **사무/웹서핑**: 4코어면 충분\n\n최근 게임들은 멀티코어를 활용하므로 코어와 클럭 둘 다 중요합니다!', 
'CPU', 'cpu,코어,클럭,선택'),

('인텔과 AMD 중 어떤 걸 선택해야 하나요?', 
'용도와 예산에 따라 선택하세요!\n\n• **인텔**: 게임 최적화 우수, 안정성 높음\n• **AMD**: 가성비 우수, 멀티태스킹 강함\n\n**2024년 추천**:\n• 게임 중심 → Intel 13~14세대 또는 AMD 7000번대\n• 작업 중심 → AMD Ryzen 9 시리즈\n• 가성비 → AMD Ryzen 5/7 시리즈', 
'CPU', 'cpu,인텔,amd,비교'),

('CPU 쿨러는 정품 쿨러로 충분한가요?', 
'CPU에 따라 다릅니다!\n\n✅ **정품 쿨러로 충분**:\n• 저전력 CPU (65W 이하)\n• 오버클럭 안 하는 경우\n\n❌ **별도 쿨러 필요**:\n• 고성능 CPU (95W 이상)\n• 오버클럭 하는 경우\n• 소음에 민감한 경우\n\n**추천**: 3만원대 타워형 쿨러면 충분히 조용하고 효율적입니다!', 
'CPU', 'cpu,쿨러,정품');

-- RAM 관련
INSERT INTO pc_faq (question, answer, category, keywords) VALUES
('RAM은 몇 GB가 필요한가요?', 
'용도별 권장 용량입니다:\n\n• **8GB**: ❌ 2024년 기준 부족\n• **16GB**: ✅ 게임, 일반 작업 충분\n• **32GB**: ✅✅ 게임+방송, 영상편집 권장 (가장 인기!)\n• **64GB**: 전문 작업 (3D, 렌더링)\n\n게임을 즐긴다면 32GB를 강력 추천합니다!', 
'RAM', 'ram,gb,용량,필요'),

('DDR4와 DDR5 중 어떤 걸 선택해야 하나요?', 
'**DDR5 권장합니다!** (신규 조립 기준)\n\n• **DDR4**: 가성비 우수, 구형 플랫폼\n• **DDR5**: 성능 우수, 최신 플랫폼\n\n**DDR5 지원**:\n• Intel 12세대 이상\n• AMD 7000번대 이상\n\n가격 차이가 많이 줄었으므로 신규 조립은 DDR5 추천!', 
'RAM', 'ram,ddr4,ddr5,비교'),

('RAM은 2개(듀얼채널)가 1개보다 좋나요?', 
'✅✅ **매우 중요합니다!**\n\n• **듀얼채널 (8GB x2 = 16GB)**: 성능 최대 50% 향상\n• **싱글채널 (16GB x1)**: ❌ 비추천\n\n**이유**: 메모리 대역폭이 2배가 되어 CPU와 GPU 성능이 모두 향상됩니다.\n\n**결론**: 항상 2개 이상 구매하세요! (예: 16GB x2 = 32GB)', 
'RAM', 'ram,듀얼채널,개수');

-- 그래픽카드 관련
INSERT INTO pc_faq (question, answer, category, keywords) VALUES
('그래픽카드 VRAM은 몇 GB가 적당한가요?', 
'해상도에 따라 다릅니다!\n\n• **1080p 게임**: 6~8GB (RTX 4060, 4060 Ti)\n• **1440p 게임**: 8~12GB (RTX 4070)\n• **4K 게임/영상작업**: 12GB 이상 (RTX 4070 Ti, 4080)\n\n최근 게임들은 VRAM을 많이 사용하므로 여유 있게 선택하세요!', 
'그래픽카드', 'vram,gb,그래픽카드'),

('중고 그래픽카드 사도 되나요?', 
'신중하게 결정하세요!\n\n❌ **채굴용 중고**: 비추천 (24시간 가동으로 수명 짧음)\n⚠️ **게임용 중고**: 신중하게\n  • 보증 기간 확인\n  • 판매자 신뢰도 확인\n  • 벤치마크 테스트 요청\n✅ **새 제품**: 추천 (AS 보증, 안정성)\n\n**결론**: 가격 차이가 크지 않다면 새 제품 구매 권장!', 
'그래픽카드', '중고,그래픽카드');

-- 저장장치 관련
INSERT INTO pc_faq (question, answer, category, keywords) VALUES
('SSD와 HDD 중 어떤 걸 선택해야 하나요?', 
'**둘 다 사용하세요!**\n\n• **SSD**: 빠름, 조용함, 내구성 우수\n  → ✅ OS 설치 필수!\n• **HDD**: 저렴, 대용량\n  → 데이터 저장용\n\n**권장 구성**:\n• SSD 500GB (OS/프로그램)\n• HDD 2TB (사진, 영상, 문서)\n\n최소한 OS는 꼭 SSD에 설치하세요!', 
'저장장치', 'ssd,hdd,비교,선택'),

('NVMe SSD와 SATA SSD 차이는?', 
'속도 차이가 있습니다!\n\n• **NVMe**: 읽기 5000MB/s 이상, M.2 슬롯\n• **SATA**: 읽기 550MB/s, 2.5인치\n\n**체감 차이**:\n• 일반 사용/게임: 크지 않음\n• 대용량 파일 작업: 확실한 차이\n\n**추천**: 가격 비슷하면 NVMe 선택! (요즘은 가격 차이 거의 없음)', 
'저장장치', 'nvme,sata,ssd,차이');

-- 파워 관련
INSERT INTO pc_faq (question, answer, category, keywords) VALUES
('파워 용량은 어떻게 계산하나요?', 
'**간단 계산법**:\n```\n총 소비 전력 = CPU TDP + GPU TDP + 100W (기타)\n파워 용량 = 총 소비 전력 × 1.5배\n```\n\n**예시**:\n• RTX 4060 (115W) + i5-14600K (125W) + 100W = 340W\n• 권장 파워: 500~650W\n\n**RTX 4070 이상**: 750W 이상\n**RTX 4080 이상**: 850W 이상\n\n여유 있게 선택하세요!', 
'파워', '파워,용량,계산'),

('80 PLUS 인증이 뭔가요?', 
'전력 효율 등급입니다!\n\n• **Bronze**: 효율 80% 이상 (저렴)\n• **Gold**: 효율 87% 이상 ✅ (권장)\n• **Platinum**: 효율 90% 이상 (고급)\n• **Titanium**: 효율 92% 이상 (프리미엄)\n\n**추천**: Gold 이상!\n• 전기료 절약\n• 발열 적음\n• 소음 적음\n\n장기적으로 봤을 때 Gold가 가성비 최고!', 
'파워', '파워,80plus,인증');

-- 케이스 관련
INSERT INTO pc_faq (question, answer, category, keywords) VALUES
('케이스 크기는 어떻게 선택하나요?', 
'메인보드 크기에 맞춰 선택하세요!\n\n• **미니타워**: 작음, ITX/M-ATX 지원\n• **미들타워**: ✅✅ 가장 일반적, ATX 지원 (강력 추천!)\n• **풀타워**: 큼, E-ATX 지원\n\n**대부분의 사용자**: 미들타워면 충분!\n• 확장성 우수\n• 쿨링 좋음\n• 조립 편함', 
'케이스', '케이스,크기,선택');

-- 호환성 관련
INSERT INTO pc_faq (question, answer, category, keywords) VALUES
('CPU와 메인보드 소켓이 맞아야 하나요?', 
'✅ **매우 중요합니다!**\n\n소켓이 다르면 장착 불가!\n\n**Intel**:\n• LGA1700: 12~14세대\n• LGA1200: 10~11세대\n\n**AMD**:\n• AM5: 7000번대\n• AM4: 5000번대 이하\n\n**구매 전 필수 확인**:\n1. CPU 소켓\n2. 메인보드 소켓\n3. 둘이 일치하는지\n\n다나와에서 "호환" 태그 확인하세요!', 
'호환성', '소켓,호환성,메인보드,cpu');

-- 예산 관련
INSERT INTO pc_faq (question, answer, category, keywords) VALUES
('100만원으로 PC 조립 가능한가요?', 
'✅ **가능합니다!**\n\n**권장 구성 (약 106만원)**:\n• CPU: AMD Ryzen 5 7600 (25만원)\n• 메인보드: B650 (15만원)\n• RAM: DDR5 16GB (8만원)\n• GPU: RTX 4060 (40만원)\n• SSD: 500GB NVMe (6만원)\n• 파워: 650W Bronze (6만원)\n• 케이스: (6만원)\n\n**성능**: 1080p 고옵션 게임 가능!\n\n**팁**: 쿨러/HDD는 나중에 추가 가능', 
'예산', '예산,100만원,가능'),

('예산별 추천 구성은?', 
'**용도별 권장 예산**:\n\n• **80~100만원**: 사무용, 웹서핑\n• **120만원**: 1080p 게임 (중옵)\n• **150만원**: 1080p 게임 (고옵 144fps)\n• **200만원**: ✅✅ 1440p 게임 (고옵) - 가장 인기!\n• **250만원**: 1440p 게임 (울트라)\n• **300만원 이상**: 4K 게임, 전문 작업\n\n**추천**: 200만원대가 가성비와 성능의 최적점!', 
'예산', '예산,추천,구성');

-- 조립 관련
INSERT INTO pc_faq (question, answer, category, keywords) VALUES
('PC 조립 순서가 어떻게 되나요?', 
'**조립 순서**:\n\n1. 메인보드에 CPU 장착\n2. CPU 쿨러 장착\n3. RAM 장착 (2번, 4번 슬롯 우선)\n4. M.2 SSD 장착 (메인보드에)\n5. 메인보드를 케이스에 장착\n6. 파워 장착 및 케이블 연결\n7. 그래픽카드 장착\n8. SATA SSD/HDD 장착\n9. 케이블 정리\n10. 부팅 테스트\n\n**초보자 팁**: 유튜브 "PC 조립" 영상 보면서 따라하세요!', 
'조립', '조립,순서,방법');

-- 업그레이드 관련
INSERT INTO pc_faq (question, answer, category, keywords) VALUES
('기존 PC 업그레이드 시 뭘 먼저 바꿔야 하나요?', 
'**업그레이드 우선순위**:\n\n1. **SSD 추가/교체** ✅✅\n   • 체감 성능 향상 최대!\n   • 가격 저렴 (10만원 내외)\n\n2. **RAM 증설** ✅\n   • 8GB → 16GB 또는 16GB → 32GB\n   • 즉시 효과 체감\n\n3. **그래픽카드 업그레이드**\n   • 게임 성능 향상\n   • 가격 부담 큼\n\n4. **CPU/메인보드**\n   • 마지막 고려\n   • 가장 비쌈\n\n**결론**: SSD부터 시작하세요!', 
'업그레이드', '업그레이드,우선순위');

-- 데이터 삽입 완료 메시지
SELECT COUNT(*) as '삽입된 FAQ 개수' FROM pc_faq;

