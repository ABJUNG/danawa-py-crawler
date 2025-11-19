package com.danawa.webservice.config;

import com.danawa.webservice.domain.PcFaq;
import com.danawa.webservice.repository.PcFaqRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.boot.CommandLineRunner;
import org.springframework.stereotype.Component;

import java.util.Arrays;
import java.util.List;

/**
 * FAQ 데이터 자동 초기화
 * 애플리케이션 시작 시 FAQ 데이터가 없으면 자동으로 생성합니다.
 */
@Slf4j
@Component
@RequiredArgsConstructor
public class FaqInitializer implements CommandLineRunner {

    private final PcFaqRepository pcFaqRepository;

    @Override
    public void run(String... args) {
        // FAQ 데이터가 이미 있으면 건너뛰기
        if (pcFaqRepository.count() > 0) {
            log.info("FAQ 데이터가 이미 존재합니다. ({}개)", pcFaqRepository.count());
            return;
        }

        log.info("FAQ 데이터 초기화 시작...");

        List<PcFaq> faqs = Arrays.asList(
            // CPU 관련
            createFaq(
                "CPU를 선택할 때 코어 수와 클럭 속도 중 뭐가 더 중요한가요?",
                "용도에 따라 다릅니다!\n\n• **게임**: 클럭 속도가 더 중요 (6코어 이상 권장)\n• **영상편집/렌더링**: 코어 수가 더 중요 (8코어 이상 권장)\n• **사무/웹서핑**: 4코어면 충분\n\n최근 게임들은 멀티코어를 활용하므로 코어와 클럭 둘 다 중요합니다!",
                "CPU",
                "cpu,코어,클럭,선택"
            ),
            createFaq(
                "인텔과 AMD 중 어떤 걸 선택해야 하나요?",
                "용도와 예산에 따라 선택하세요!\n\n• **인텔**: 게임 최적화 우수, 안정성 높음\n• **AMD**: 가성비 우수, 멀티태스킹 강함\n\n**2024년 추천**:\n• 게임 중심 → Intel 13~14세대 또는 AMD 7000번대\n• 작업 중심 → AMD Ryzen 9 시리즈\n• 가성비 → AMD Ryzen 5/7 시리즈",
                "CPU",
                "cpu,인텔,amd,비교"
            ),
            createFaq(
                "CPU 쿨러는 정품 쿨러로 충분한가요?",
                "CPU에 따라 다릅니다!\n\n✅ **정품 쿨러로 충분**:\n• 저전력 CPU (65W 이하)\n• 오버클럭 안 하는 경우\n\n❌ **별도 쿨러 필요**:\n• 고성능 CPU (95W 이상)\n• 오버클럭 하는 경우\n• 소음에 민감한 경우\n\n**추천**: 3만원대 타워형 쿨러면 충분히 조용하고 효율적입니다!",
                "CPU",
                "cpu,쿨러,정품"
            ),
            // RAM 관련
            createFaq(
                "RAM은 몇 GB가 필요한가요?",
                "용도별 권장 용량입니다:\n\n• **8GB**: ❌ 2024년 기준 부족\n• **16GB**: ✅ 게임, 일반 작업 충분\n• **32GB**: ✅✅ 게임+방송, 영상편집 권장 (가장 인기!)\n• **64GB**: 전문 작업 (3D, 렌더링)\n\n게임을 즐긴다면 32GB를 강력 추천합니다!",
                "RAM",
                "ram,gb,용량,필요"
            ),
            createFaq(
                "DDR4와 DDR5 중 어떤 걸 선택해야 하나요?",
                "예산과 메인보드에 따라 다릅니다!\n\n• **DDR4**: 가성비 우수, 안정적 (2024년에도 충분히 좋음)\n• **DDR5**: 최신 기술, 향후 확장성 (가격이 높음)\n\n**추천**:\n• 예산이 넉넉하면 → DDR5\n• 가성비 중시 → DDR4 (여전히 훌륭함)\n• 게임용 → DDR4 3600MHz면 충분",
                "RAM",
                "ram,ddr4,ddr5,비교"
            ),
            createFaq(
                "RAM은 2개(듀얼채널)가 1개보다 좋나요?",
                "네, 2개가 훨씬 좋습니다!\n\n**듀얼채널의 장점**:\n• 메모리 대역폭 2배 증가\n• 게임 성능 5~15% 향상\n• 멀티태스킹 성능 향상\n\n**권장 구성**:\n• 16GB → 8GB × 2개\n• 32GB → 16GB × 2개\n• 64GB → 32GB × 2개\n\n**주의**: 같은 용량, 같은 속도로 구성하세요!",
                "RAM",
                "ram,듀얼채널,2개,1개"
            ),
            // 그래픽카드 관련
            createFaq(
                "그래픽카드 VRAM은 몇 GB가 적당한가요?",
                "게임 해상도와 설정에 따라 다릅니다!\n\n• **4GB**: 1080p 낮음 설정 (2024년 기준 부족)\n• **6GB**: 1080p 중간 설정\n• **8GB**: 1080p 고화질, 1440p 중간 설정 (가장 인기!)\n• **12GB**: 1440p 고화질, 4K 중간 설정\n• **16GB+**: 4K 고화질, 레이 트레이싱\n\n**2024년 추천**: 최소 8GB, 이상적으론 12GB 이상!",
                "그래픽카드",
                "vram,gb,그래픽카드,gpu"
            ),
            createFaq(
                "중고 그래픽카드 사도 되나요?",
                "중고 그래픽카드는 주의해서 구매하면 괜찮습니다!\n\n✅ **구매해도 되는 경우**:\n• 신뢰할 수 있는 판매자\n• 정상 작동 확인 가능\n• 가격이 합리적인 경우\n\n❌ **피해야 하는 경우**:\n• 채굴용 의심 (과도하게 저렴)\n• 개인 간 거래 (AS 불가)\n• 오래된 세대 (3년 이상)\n\n**추천**: 중고나라, 당근마켓보다는 PC방 중고나 공식 리퍼 제품을 추천합니다!",
                "그래픽카드",
                "중고,그래픽카드,gpu"
            ),
            // 저장장치 관련
            createFaq(
                "SSD와 HDD 중 어떤 걸 선택해야 하나요?",
                "용도에 따라 다릅니다!\n\n**SSD (권장)**:\n• 빠른 부팅 속도 (10초 이내)\n• 빠른 게임 로딩\n• 조용함, 내구성\n• 가격이 높음\n\n**HDD**:\n• 저렴한 가격 (용량 대비)\n• 대용량 저장 (4TB 이상)\n• 느린 속도\n\n**추천 구성**: SSD 1TB (OS+게임) + HDD 2TB (저장용)",
                "저장장치",
                "ssd,hdd,선택,비교"
            ),
            createFaq(
                "NVMe SSD와 SATA SSD 차이는?",
                "속도 차이가 큽니다!\n\n**NVMe SSD**:\n• 읽기 속도: 3000~7000 MB/s\n• 쓰기 속도: 2000~5000 MB/s\n• M.2 슬롯 사용\n• 가격이 높음\n\n**SATA SSD**:\n• 읽기 속도: 500~550 MB/s\n• 쓰기 속도: 400~500 MB/s\n• SATA 케이블 사용\n• 가격이 저렴\n\n**추천**: OS용은 NVMe, 저장용은 SATA도 충분!",
                "저장장치",
                "nvme,sata,ssd,차이"
            ),
            // 파워 관련
            createFaq(
                "파워 용량은 어떻게 계산하나요?",
                "부품별 전력 소비량을 합산하세요!\n\n**대략적인 전력 소비**:\n• CPU: 65W~250W\n• 그래픽카드: 150W~450W\n• 메인보드: 30W~50W\n• RAM: 5W~10W\n• SSD/HDD: 5W~10W\n• 쿨러: 10W~30W\n\n**계산 예시**:\n• CPU 150W + GPU 300W + 기타 100W = 550W\n• 여유분 30% 추가 → 550W × 1.3 = 715W\n• **추천**: 750W 파워\n\n**온라인 계산기**: bequiet! 파워 계산기 추천!",
                "파워",
                "파워,용량,계산,와트"
            ),
            createFaq(
                "80 PLUS 인증이 뭔가요?",
                "파워 효율 인증 등급입니다!\n\n**등급별 효율**:\n• 80 PLUS: 80% (기본)\n• Bronze: 82~85%\n• Silver: 85~88%\n• Gold: 87~90% (가장 인기!)\n• Platinum: 90~92%\n• Titanium: 94~96%\n\n**추천**: Gold 등급이 가성비 최고! Bronze도 충분히 좋습니다.\n\n**주의**: 80 PLUS 인증만으로는 품질을 보장하지 않습니다. 브랜드도 중요해요!",
                "파워",
                "80 plus,인증,효율"
            ),
            // 케이스 관련
            createFaq(
                "케이스 크기는 어떻게 선택하나요?",
                "메인보드 크기에 맞춰 선택하세요!\n\n**케이스 크기**:\n• **미니타워**: ITX, mATX (작고 깔끔)\n• **미들타워**: ATX, mATX (가장 인기!)\n• **풀타워**: E-ATX, ATX (대형, 확장성)\n\n**선택 기준**:\n• 메인보드 크기 확인\n• 그래픽카드 길이 확인\n• CPU 쿨러 높이 확인\n• 케이스 내부 공간 확인\n\n**추천**: 미들타워가 가장 범용적이고 가성비 좋습니다!",
                "케이스",
                "케이스,크기,선택"
            ),
            // 호환성 관련
            createFaq(
                "CPU와 메인보드 소켓이 맞아야 하나요?",
                "네, 반드시 맞아야 합니다!\n\n**주요 소켓**:\n• **인텔**: LGA1700 (12~14세대), LGA1200 (10~11세대)\n• **AMD**: AM5 (7000번대), AM4 (5000번대 이하)\n\n**호환성 확인 방법**:\n• CPU 제조사 사이트에서 소켓 확인\n• 메인보드 제조사 사이트에서 지원 CPU 목록 확인\n• 다나와에서 호환성 체크 기능 사용\n\n**주의**: 소켓이 안 맞으면 절대 장착 불가능합니다!",
                "호환성",
                "소켓,메인보드,cpu,호환성"
            ),
            // 예산 관련
            createFaq(
                "100만원으로 PC 조립 가능한가요?",
                "네, 가능합니다!\n\n**100만원 구성 예시**:\n• CPU: AMD Ryzen 5 7500F (20만원)\n• 메인보드: B650M (15만원)\n• RAM: DDR5 16GB (8만원)\n• 그래픽카드: RTX 4060 (35만원)\n• SSD: 500GB NVMe (5만원)\n• 파워: 600W 80+ Bronze (7만원)\n• 케이스: 미들타워 (5만원)\n• 쿨러: 기본 쿨러 (포함)\n\n**총합**: 약 95만원\n\n**팁**: 중고 그래픽카드 사용 시 더 좋은 성능 가능!",
                "예산",
                "100만원,예산,가능"
            ),
            createFaq(
                "예산별 추천 구성은?",
                "예산에 따른 추천 구성입니다!\n\n**50만원**: 사무용, 간단한 게임\n• CPU: Ryzen 5 5600G (내장 그래픽)\n• RAM: 16GB DDR4\n• SSD: 500GB\n\n**100만원**: 게임용 기본\n• CPU: Ryzen 5 7500F\n• GPU: RTX 4060\n• RAM: 16GB DDR5\n\n**150만원**: 게임용 중급\n• CPU: Ryzen 7 7700\n• GPU: RTX 4070\n• RAM: 32GB DDR5\n\n**200만원+**: 게임용 고급\n• CPU: Ryzen 7 7800X3D\n• GPU: RTX 4080\n• RAM: 32GB DDR5",
                "예산",
                "예산,추천,구성"
            ),
            // 조립 관련
            createFaq(
                "PC 조립 순서가 어떻게 되나요?",
                "초보자도 따라할 수 있는 조립 순서입니다!\n\n**1단계**: 메인보드에 CPU 장착\n**2단계**: CPU 쿨러 장착\n**3단계**: RAM 장착 (2개면 2,4번 슬롯)\n**4단계**: M.2 SSD 장착\n**5단계**: 메인보드를 케이스에 고정\n**6단계**: 파워 서플라이 장착 및 케이블 연결\n**7단계**: 그래픽카드 장착 (마지막)\n**8단계**: 케이블 정리 및 첫 부팅\n\n💡 **팁**: 유튜브 조립 영상을 보면서 천천히 하면 누구나 할 수 있어요!",
                "조립",
                "조립,순서,방법,초보"
            ),
            createFaq(
                "기존 PC 업그레이드 시 뭘 먼저 바꿔야 하나요?",
                "용도에 따라 다릅니다!\n\n**게임 성능 향상**:\n1순위: 그래픽카드\n2순위: CPU\n3순위: RAM (16GB 미만인 경우)\n\n**전체적인 속도 향상**:\n1순위: SSD (HDD 사용 중인 경우)\n2순위: RAM (8GB 미만인 경우)\n3순위: CPU\n\n**주의사항**:\n• 메인보드 소켓 확인 (CPU 교체 시)\n• 파워 용량 확인 (그래픽카드 교체 시)\n• 케이스 크기 확인 (큰 부품 교체 시)\n\n**추천**: SSD가 가장 체감이 큽니다!",
                "업그레이드",
                "업그레이드,순서,교체"
            )
        );

        pcFaqRepository.saveAll(faqs);
        log.info("FAQ 데이터 초기화 완료! ({}개)", faqs.size());
    }

    private PcFaq createFaq(String question, String answer, String category, String keywords) {
        return PcFaq.builder()
                .question(question)
                .answer(answer)
                .category(category)
                .keywords(keywords)
                .viewCount(0)
                .helpfulCount(0)
                .build();
    }
}

