package com.danawa.webservice.service;

import com.danawa.webservice.domain.Part;
import com.danawa.webservice.domain.PcFaq;
import com.danawa.webservice.repository.PartRepository;
import com.danawa.webservice.repository.PcFaqRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Sort;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.client.RestTemplate;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import com.danawa.webservice.domain.PartSpec;
import org.json.JSONObject;
import org.json.JSONArray;

import java.util.List;
import java.util.stream.Collectors;

@Service
@Transactional(readOnly = true)
@RequiredArgsConstructor
public class ChatService {

    private final PartRepository partRepository; // DB 접근 위해 PartRepository 주입
    private final PcFaqRepository pcFaqRepository; // FAQ Repository 주입

    @Value("${gemini.api.key}") // application.properties에서 API 키 가져오기
    private String apiKey;

    public String getAiResponse(String userQuery) {
        // 0. FAQ 먼저 검색 (빠른 응답)
        String faqAnswer = searchFAQ(userQuery);
        if (faqAnswer != null) {
            return faqAnswer;
        }
        
        // 1. 설명 질문인지 확인 (예: "CPU가 뭐야?", "그래픽카드 설명해줘")
        if (isExplanationQuery(userQuery)) {
            String category = extractCategory(userQuery);
            if (category != null) {
                // 카테고리가 있으면 Gemini에게 직접 설명 요청
                String explanationPrompt = String.format(
                    """
                    너는 PC 부품 전문가 '다오나(DAONA)'야. 사용자가 %s에 대해 물어보고 있어.
                    
                    사용자 질문: "%s"
                    
                    친절하고 이해하기 쉽게 %s가 무엇인지, 어떤 역할을 하는지, 왜 중요한지 설명해줘.
                    - 전문 용어는 쉽게 풀어서 설명
                    - 예시를 들어서 설명
                    - 이모지를 적절히 사용
                    - 3~5줄 정도로 간결하게
                    
                    시작: "안녕하세요! 다오나입니다. 🤖"
                    마무리: "더 궁금한 점이 있으시면 언제든 물어보세요! 💬"
                    """,
                    category, userQuery, category
                );
                
                String explanation = callGeminiApi(explanationPrompt);
                if (explanation != null && !explanation.isEmpty()) {
                    return explanation;
                }
            }
            // Gemini 실패 시 기본 설명 반환
            return generateBasicExplanation(userQuery);
        }
        
        // 2. 사용자 쿼리 분석 (간단 버전: 카테고리만 추출 시도)
        String category = extractCategory(userQuery); // 예: "CPU", "그래픽카드" 등
        if (category == null) {
            return "안녕하세요! 다오나입니다. 😊\n\n어떤 PC 부품에 대해 알고 싶으신가요?\n\n🔹 **추천받고 싶은 부품을 말씀해주세요:**\n• \"게임용 그래픽카드 추천해줘\"\n• \"저렴한 CPU 알려줘\"\n• \"고성능 SSD 뭐가 좋아?\"\n• \"100만원 예산으로 RAM 추천\"\n\n🔹 **이런 부품들을 추천해드릴 수 있어요:**\nCPU, 그래픽카드, RAM, SSD, 메인보드, 파워, 케이스, 쿨러\n\n편하게 물어보세요! 💬";
        }

        // 2. DB에서 관련 데이터 검색 
        // - 가격대별 다양한 제품 조회 (저가, 중가, 고가)
        // - 리뷰 요약이 있는 제품 우선
        List<Part> allParts = partRepository.findAll(
                (root, query, cb) -> cb.equal(root.get("category"), category),
                PageRequest.of(0, 50, Sort.by(Sort.Direction.ASC, "price"))
        ).getContent();

        if (allParts.isEmpty()) {
            return "죄송합니다. 😢 현재 " + category + " 카테고리의 부품 정보가 데이터베이스에 없습니다.\n크롤러를 실행하여 데이터를 수집해주세요.";
        }

        // 가격대별 제품 선택 (저가, 중가, 고가)
        List<Part> relevantParts = selectDiverseParts(allParts, 10);

        // 3. 참고 자료(Context) 문자열 만들기
        StringBuilder contextBuilder = new StringBuilder();
        for (int i = 0; i < relevantParts.size(); i++) {
            Part part = relevantParts.get(i);
            contextBuilder.append(String.format("[제품 %d]\n", i + 1));
            contextBuilder.append(String.format("- 제품명: %s\n", part.getName()));
            contextBuilder.append(String.format("- 가격: %,d원\n", part.getPrice()));
            contextBuilder.append(String.format("- 브랜드: %s\n", part.getManufacturer() != null ? part.getManufacturer() : "정보없음"));
            contextBuilder.append(String.format("- 스펙: %s\n", buildSpecString(part)));
            
            // 리뷰가 있으면 추가 (communityReviews 리스트에서)
            if (part.getCommunityReviews() != null && !part.getCommunityReviews().isEmpty()) {
                var review = part.getCommunityReviews().get(0);
                String reviewText = review.getAiSummary() != null && !review.getAiSummary().isEmpty() 
                    ? review.getAiSummary() 
                    : review.getRawText();
                if (reviewText != null && !reviewText.isEmpty()) {
                    contextBuilder.append(String.format("- 사용자 리뷰: %s\n", 
                        reviewText.length() > 200 ? 
                        reviewText.substring(0, 200) + "..." : 
                        reviewText));
                }
            }
            contextBuilder.append("\n");
        }

        // 4. 프롬프트 구성 (더 구체적이고 실용적인 프롬프트)
        String prompt = String.format(
                """
                # 페르소나
                너는 PC 부품 전문가 '다오나(DAONA)'야. 사용자의 질문에 대해 아래 '참고 자료'의 실제 제품 정보만을 바탕으로 최적의 부품을 추천해야 해.
    
                # 지시사항
                1. **정확성 최우선**: 반드시 '참고 자료' 안의 정보만 사용해서 답변해. 없는 내용은 절대 지어내지 마.
                
                2. **추천 형식** (사용자의 질문에 가장 적합한 부품 1~3개 추천):
                   
                   📌 **추천 1: [제품명]** (가격: [가격]원)
                   - **왜 추천?**: [가성비, 성능, 적합성 등]
                   - **주요 스펙**: [핵심 스펙 요약]
                   - **사용자 리뷰**: [리뷰 요약 내용 - 있는 경우만]
                   
                   📌 **추천 2: ...** (중가 옵션)
                   📌 **추천 3: ...** (고가 옵션)
                
                3. **가격대별 비교**: 저가(~가성비), 중가(~밸런스), 고가(~최고성능) 옵션을 골고루 추천해줘.
                
                4. **실용적 조언**: 각 제품의 장단점과 어떤 사용자에게 적합한지 명확하게 설명해줘.
                   - 예산 제약이 있는 경우 → 가성비 제품
                   - 게임/작업 성능이 중요한 경우 → 중~고가 제품
                
                5. **답변 형식**:
                   - 시작: "안녕하세요! 다오나입니다 🤖"
                   - 마무리: "더 궁금한 점이 있으시면 언제든 물어보세요! 💬"
                
                6. **친절하고 이해하기 쉽게**: 전문 용어는 간단히 설명하고, 이모지를 적절히 사용해줘.
    
                ---
                ## 참고 자료 (%s 카테고리, 총 %d개 제품) ##
                %s
                ---
    
                # 사용자 질문
                %s
                
                # 추가 지침
                - 질문에 예산이 명시되어 있다면, 그 예산 범위 내에서 최적의 제품을 추천해줘.
                - "추천해줘", "알려줘" 같은 질문이면 가격대별로 2~3개 추천.
                - "어떤 게 좋아?" 같은 질문이면 사용 목적을 물어보고 맞춤 추천.
                - 특정 브랜드/모델을 언급하면 그 제품과 유사한 옵션 비교.
                """, category, relevantParts.size(), contextBuilder.toString(), userQuery
        );

        // 5. Gemini API 호출
        String aiResponse = callGeminiApi(prompt);
        
        // API 호출 실패 시 간단한 키워드 기반 응답 생성
        if (aiResponse == null || aiResponse.isEmpty()) {
            return generateSimpleResponse(category, relevantParts, userQuery);
        }

        return aiResponse;
    }

    // FAQ 검색 (우선순위 높음 - 즉시 답변 가능)
    private String searchFAQ(String userQuery) {
        try {
            String lowerQuery = userQuery.toLowerCase();
            
            // FAQ 키워드 검색
            List<String> keywords = extractKeywords(lowerQuery);
            
            for (String keyword : keywords) {
                List<PcFaq> faqs = pcFaqRepository.findByQuestionContainingOrKeywordsContaining(keyword);
                
                if (!faqs.isEmpty()) {
                    // 가장 적합한 FAQ 선택 (첫 번째)
                    PcFaq bestMatch = faqs.get(0);
                    
                    // 조회수 증가 (비동기로 처리하면 더 좋음)
                    try {
                        bestMatch.incrementViewCount();
                        pcFaqRepository.save(bestMatch);
                    } catch (Exception e) {
                        // 조회수 업데이트 실패해도 답변은 반환
                    }
                    
                    // FAQ 답변 반환
                    return String.format("📌 **자주 묻는 질문**\n\n**Q: %s**\n\n%s\n\n💡 이 답변이 도움이 되었나요?\n더 궁금한 점이 있으시면 언제든 물어보세요!", 
                        bestMatch.getQuestion(), bestMatch.getAnswer());
                }
            }
        } catch (Exception e) {
            System.err.println("FAQ 검색 중 오류: " + e.getMessage());
        }
        
        return null; // FAQ에서 답변을 찾지 못함
    }
    
    // 설명 질문인지 확인 (예: "CPU가 뭐야?", "그래픽카드 설명해줘")
    private boolean isExplanationQuery(String query) {
        String lowerQuery = query.toLowerCase();
        
        // 설명 요청 패턴
        String[] explanationPatterns = {
            "뭐야", "뭐니", "뭐인가", "무엇", "무엇인가",
            "설명", "알려줘", "알려주세요", "가르쳐줘",
            "이해", "의미", "역할", "기능", "용도",
            "뭔가", "뭔지", "뭔데", "뭐하는", "뭐하는거"
        };
        
        for (String pattern : explanationPatterns) {
            if (lowerQuery.contains(pattern)) {
                return true;
            }
        }
        
        return false;
    }
    
    // 기본 설명 생성 (Gemini 실패 시)
    private String generateBasicExplanation(String userQuery) {
        String category = extractCategory(userQuery);
        
        if (category == null) {
            return "안녕하세요! 다오나입니다. 😊\n\n질문을 더 구체적으로 해주시면 도와드릴 수 있어요!\n\n예시:\n• \"CPU가 뭐야?\"\n• \"그래픽카드 설명해줘\"\n• \"RAM의 역할은?\"\n\n편하게 물어보세요! 💬";
        }
        
        // 카테고리별 기본 설명
        switch (category) {
            case "CPU":
                return "안녕하세요! 다오나입니다. 🤖\n\n**CPU (Central Processing Unit)**는 컴퓨터의 두뇌 역할을 하는 핵심 부품입니다! 🧠\n\n**주요 역할**:\n• 모든 프로그램 실행\n• 계산 및 데이터 처리\n• 시스템 전체 성능 결정\n\n**중요한 스펙**:\n• 코어 수: 동시 작업 처리 능력\n• 클럭 속도: 작업 처리 속도\n\n게임, 영상편집, 사무용 등 용도에 따라 적합한 CPU가 달라요! 💻\n\n더 궁금한 점이 있으시면 언제든 물어보세요! 💬";
            case "그래픽카드":
            case "GPU":
                return "안녕하세요! 다오나입니다. 🤖\n\n**그래픽카드 (GPU)**는 화면에 이미지를 그려주는 부품입니다! 🎮\n\n**주요 역할**:\n• 게임 그래픽 렌더링\n• 영상 편집/렌더링 가속\n• 3D 작업 처리\n\n**중요한 스펙**:\n• VRAM: 그래픽 메모리 용량\n• 코어 클럭: 처리 속도\n\n게임을 즐기거나 영상 작업을 한다면 필수 부품이에요! 🎨\n\n더 궁금한 점이 있으시면 언제든 물어보세요! 💬";
            case "RAM":
                return "안녕하세요! 다오나입니다. 🤖\n\n**RAM (Random Access Memory)**는 컴퓨터가 작업하는 동안 데이터를 임시 저장하는 메모리입니다! 💾\n\n**주요 역할**:\n• 프로그램 실행 속도 향상\n• 멀티태스킹 지원\n• 게임/작업 성능 결정\n\n**중요한 스펙**:\n• 용량: 16GB, 32GB 등\n• 속도: DDR4, DDR5 등\n\n용량이 많을수록 더 많은 프로그램을 동시에 실행할 수 있어요! ⚡\n\n더 궁금한 점이 있으시면 언제든 물어보세요! 💬";
            case "SSD":
                return "안녕하세요! 다오나입니다. 🤖\n\n**SSD (Solid State Drive)**는 빠른 속도로 데이터를 저장하는 저장장치입니다! 💿\n\n**주요 역할**:\n• 운영체제 및 프로그램 저장\n• 빠른 부팅 속도\n• 파일 읽기/쓰기 속도 향상\n\n**장점**:\n• HDD보다 10배 이상 빠름\n• 조용하고 내구성 우수\n• 전력 소비 적음\n\nOS는 반드시 SSD에 설치하는 것을 추천해요! 🚀\n\n더 궁금한 점이 있으시면 언제든 물어보세요! 💬";
            case "메인보드":
                return "안녕하세요! 다오나입니다. 🤖\n\n**메인보드**는 모든 부품을 연결하는 컴퓨터의 기반이 되는 부품입니다! 🔌\n\n**주요 역할**:\n• CPU, RAM, GPU 등 모든 부품 연결\n• 부품 간 통신 관리\n• 전원 공급 및 데이터 전송\n\n**중요한 스펙**:\n• 소켓: CPU 호환성\n• 메모리 타입: DDR4/DDR5\n• 폼팩터: 크기 (ATX, mATX 등)\n\nCPU와 메인보드의 소켓이 일치해야 해요! ⚙️\n\n더 궁금한 점이 있으시면 언제든 물어보세요! 💬";
            case "파워":
            case "PSU":
                return "안녕하세요! 다오나입니다. 🤖\n\n**파워 서플라이**는 컴퓨터에 전기를 공급하는 부품입니다! ⚡\n\n**주요 역할**:\n• 모든 부품에 안정적인 전원 공급\n• 전압 변환 및 안정화\n• 과전압/과전류 보호\n\n**중요한 스펙**:\n• 용량: 와트(W) 단위\n• 효율: 80 PLUS 인증 등급\n\n부품들의 전력 소비량을 합산해서 적절한 용량을 선택해야 해요! 🔋\n\n더 궁금한 점이 있으시면 언제든 물어보세요! 💬";
            case "케이스":
                return "안녕하세요! 다오나입니다. 🤖\n\n**케이스**는 모든 부품을 담는 PC의 외관입니다! 📦\n\n**주요 역할**:\n• 부품 보호\n• 쿨링 (공기 순환)\n• 외관 및 디자인\n\n**중요한 스펙**:\n• 크기: 미니타워, 미들타워, 풀타워\n• 메인보드 호환성\n• 그래픽카드 길이 지원\n\n메인보드 크기에 맞는 케이스를 선택해야 해요! 🏠\n\n더 궁금한 점이 있으시면 언제든 물어보세요! 💬";
            case "쿨러":
                return "안녕하세요! 다오나입니다. 🤖\n\n**CPU 쿨러**는 CPU의 열을 식혀주는 부품입니다! ❄️\n\n**주요 역할**:\n• CPU 온도 관리\n• 성능 저하 방지\n• 수명 연장\n\n**종류**:\n• 공랭 쿨러: 팬으로 공기 순환\n• 수랭 쿨러: 물로 냉각\n\n고성능 CPU나 오버클럭 시에는 좋은 쿨러가 필수예요! 🌡️\n\n더 궁금한 점이 있으시면 언제든 물어보세요! 💬";
            default:
                return String.format("안녕하세요! 다오나입니다. 🤖\n\n%s에 대해 궁금하시는군요!\n\n더 자세한 설명이나 제품 추천이 필요하시면 구체적으로 물어보세요!\n\n예시:\n• \"%s 추천해줘\"\n• \"%s 어떤 게 좋아?\"\n\n더 궁금한 점이 있으시면 언제든 물어보세요! 💬", category, category, category);
        }
    }
    
    // 키워드 추출 (FAQ 검색용)
    private List<String> extractKeywords(String query) {
        List<String> keywords = new java.util.ArrayList<>();
        
        // 일반적인 질문 키워드
        String[] commonQuestions = {
            "코어", "클럭", "인텔", "amd", "쿨러", "정품",
            "vram", "중고", "rtx", "gtx",
            "ram", "gb", "ddr4", "ddr5", "듀얼채널",
            "ssd", "hdd", "nvme", "sata",
            "파워", "용량", "계산", "80 plus", "정격",
            "케이스", "크기", "호환",
            "소켓", "메인보드", "호환성",
            "수냉", "공랭",
            "예산", "만원", "가능",
            "조립", "순서", "바이오스",
            "업그레이드", "몇 년"
        };
        
        for (String keyword : commonQuestions) {
            if (query.contains(keyword)) {
                keywords.add(keyword);
            }
        }
        
        return keywords;
    }
    
    // 간단한 키워드 기반 응답 생성 (API 실패 시 폴백)
    private String generateSimpleResponse(String category, List<Part> parts, String userQuery) {
        if (parts.isEmpty()) {
            return String.format("죄송합니다. 😢\n현재 %s 카테고리의 제품 정보가 없습니다.\n크롤러를 실행하여 데이터를 수집해주세요.", category);
        }
        
        String lowerQuery = userQuery.toLowerCase();
        
        // 사용자 질문에서 키워드 추출
        boolean wantsAMD = lowerQuery.contains("amd") || lowerQuery.contains("라이젠") || lowerQuery.contains("라데온");
        boolean wantsIntel = lowerQuery.contains("인텔") || lowerQuery.contains("intel") || lowerQuery.contains("코어");
        boolean wantsNvidia = lowerQuery.contains("nvidia") || lowerQuery.contains("지포스") || lowerQuery.contains("rtx") || lowerQuery.contains("gtx");
        boolean wantsHighEnd = lowerQuery.contains("고성능") || lowerQuery.contains("하이엔드") || lowerQuery.contains("최고") || lowerQuery.contains("상급");
        boolean wantsBudget = lowerQuery.contains("저렴") || lowerQuery.contains("가성비") || lowerQuery.contains("싼") || lowerQuery.contains("저가");
        boolean wantsDesktop = lowerQuery.contains("데스크탑") || lowerQuery.contains("데스크톱") || lowerQuery.contains("desktop");
        boolean wantsNotebook = lowerQuery.contains("노트북") || lowerQuery.contains("랩탑") || lowerQuery.contains("notebook") || lowerQuery.contains("laptop");
        
        // 제조사 필터링
        List<Part> filtered = new java.util.ArrayList<>(parts);
        if (wantsAMD) {
            filtered = filtered.stream()
                .filter(p -> p.getName().toLowerCase().contains("amd") || 
                            p.getName().toLowerCase().contains("라이젠") ||
                            p.getName().toLowerCase().contains("라데온"))
                .collect(Collectors.toList());
        } else if (wantsIntel) {
            filtered = filtered.stream()
                .filter(p -> p.getName().toLowerCase().contains("인텔") || 
                            p.getName().toLowerCase().contains("intel") ||
                            p.getName().toLowerCase().contains("코어"))
                .collect(Collectors.toList());
        } else if (wantsNvidia) {
            filtered = filtered.stream()
                .filter(p -> p.getName().toLowerCase().contains("nvidia") || 
                            p.getName().toLowerCase().contains("지포스") ||
                            p.getName().toLowerCase().contains("rtx") ||
                            p.getName().toLowerCase().contains("gtx"))
                .collect(Collectors.toList());
        }
        
        // RAM 카테고리인 경우 데스크탑/노트북 필터링
        if ("RAM".equals(category)) {
            if (wantsDesktop) {
                // 데스크탑용만: 노트북용 제외
                filtered = filtered.stream()
                    .filter(p -> {
                        String nameLower = p.getName().toLowerCase();
                        return !nameLower.contains("노트북") && 
                               !nameLower.contains("notebook") && 
                               !nameLower.contains("랩탑") &&
                               !nameLower.contains("laptop") &&
                               !nameLower.contains("so-dimm");
                    })
                    .collect(Collectors.toList());
            } else if (wantsNotebook) {
                // 노트북용만
                filtered = filtered.stream()
                    .filter(p -> {
                        String nameLower = p.getName().toLowerCase();
                        return nameLower.contains("노트북") || 
                               nameLower.contains("notebook") || 
                               nameLower.contains("랩탑") ||
                               nameLower.contains("laptop") ||
                               nameLower.contains("so-dimm");
                    })
                    .collect(Collectors.toList());
            } else {
                // 기본적으로 데스크탑용만 보여주기 (노트북용 제외)
                filtered = filtered.stream()
                    .filter(p -> {
                        String nameLower = p.getName().toLowerCase();
                        return !nameLower.contains("노트북") && 
                               !nameLower.contains("notebook") && 
                               !nameLower.contains("랩탑") &&
                               !nameLower.contains("laptop") &&
                               !nameLower.contains("so-dimm");
                    })
                    .collect(Collectors.toList());
            }
        }
        
        // 필터링 후 결과가 없으면 원본 사용
        if (filtered.isEmpty()) {
            filtered = new java.util.ArrayList<>(parts);
        }
        
        StringBuilder response = new StringBuilder();
        response.append("안녕하세요! 다오나입니다. 🤖\n\n");
        
        // 제조사 특정 요청에 대한 응답
        if (wantsAMD) {
            response.append(String.format("**AMD %s 추천드립니다!**\n\n", category));
        } else if (wantsIntel) {
            response.append(String.format("**인텔 %s 추천드립니다!**\n\n", category));
        } else if (wantsNvidia) {
            response.append(String.format("**NVIDIA %s 추천드립니다!**\n\n", category));
        } else {
            response.append(String.format("**%s 추천드립니다!**\n\n", category));
        }
        
        // 가격대별 또는 요청별 추천
        if (wantsHighEnd) {
            // 고성능만 추천 (상위 30%)
            int startIdx = (int)(filtered.size() * 0.7);
            List<Part> highEndParts = filtered.subList(Math.max(0, startIdx), filtered.size());
            
            response.append("🚀 **고성능 옵션**\n");
            int count = 0;
            for (Part part : highEndParts) {
                if (count >= 5) break;
                response.append(String.format("• %s\n  가격: %,d원\n", part.getName(), part.getPrice()));
                count++;
            }
            response.append("\n");
            
        } else if (wantsBudget) {
            // 가성비만 추천 (하위 30%)
            int endIdx = (int)(filtered.size() * 0.3);
            List<Part> budgetParts = filtered.subList(0, Math.min(endIdx, filtered.size()));
            
            response.append("💰 **가성비 옵션**\n");
            int count = 0;
            for (Part part : budgetParts) {
                if (count >= 5) break;
                response.append(String.format("• %s\n  가격: %,d원\n", part.getName(), part.getPrice()));
                count++;
            }
            response.append("\n");
            
        } else {
            // 일반 추천: 가격대별 다양하게
            List<Part> selected = selectDiverseParts(filtered, 6);
            
            // 저가 (30%)
            int lowCount = Math.min(2, selected.size());
            if (lowCount > 0) {
                response.append("💰 **가성비 옵션**\n");
                for (int i = 0; i < lowCount; i++) {
                    Part part = selected.get(i);
                    response.append(String.format("• %s\n  가격: %,d원\n", part.getName(), part.getPrice()));
                }
                response.append("\n");
            }
            
            // 중가 (30-70%)
            int midStart = lowCount;
            int midCount = Math.min(2, selected.size() - midStart);
            if (midCount > 0) {
                response.append("⚖️ **밸런스 옵션**\n");
                for (int i = midStart; i < midStart + midCount; i++) {
                    Part part = selected.get(i);
                    response.append(String.format("• %s\n  가격: %,d원\n", part.getName(), part.getPrice()));
                }
                response.append("\n");
            }
            
            // 고가 (70%+)
            int highStart = midStart + midCount;
            int highCount = Math.min(2, selected.size() - highStart);
            if (highCount > 0) {
                response.append("🚀 **고성능 옵션**\n");
                for (int i = highStart; i < highStart + highCount; i++) {
                    Part part = selected.get(i);
                    response.append(String.format("• %s\n  가격: %,d원\n", part.getName(), part.getPrice()));
                }
                response.append("\n");
            }
        }
        
        response.append("더 궁금한 점이 있으시면 언제든 물어보세요! 💬");
        
        return response.toString();
    }
    
    // 가격대별 다양한 제품 선택 (저가, 중가, 고가 골고루)
    private List<Part> selectDiverseParts(List<Part> allParts, int maxCount) {
        if (allParts.size() <= maxCount) {
            return allParts;
        }

        List<Part> selected = new java.util.ArrayList<>();
        int size = allParts.size();
        
        // 저가 (하위 30%)
        int lowEnd = (int) (size * 0.3);
        for (int i = 0; i < Math.min(lowEnd, maxCount / 3); i++) {
            selected.add(allParts.get(i));
        }
        
        // 중가 (중간 40%)
        int midStart = (int) (size * 0.3);
        int midEnd = (int) (size * 0.7);
        for (int i = midStart; i < midEnd && selected.size() < (maxCount * 2 / 3); i++) {
            selected.add(allParts.get(i));
        }
        
        // 고가 (상위 30%)
        int highStart = (int) (size * 0.7);
        for (int i = highStart; i < size && selected.size() < maxCount; i++) {
            selected.add(allParts.get(i));
        }
        
        // 리뷰가 있는 제품 우선 정렬 (communityReviews 리스트 기준)
        selected.sort((p1, p2) -> {
            boolean p1HasReview = p1.getCommunityReviews() != null && !p1.getCommunityReviews().isEmpty();
            boolean p2HasReview = p2.getCommunityReviews() != null && !p2.getCommunityReviews().isEmpty();
            if (p1HasReview && !p2HasReview) return -1;
            if (!p1HasReview && p2HasReview) return 1;
            return 0;
        });
        
        return selected;
    }

    // 사용자 쿼리에서 카테고리 추출 (개선된 버전 - 맥락 기반 추론)
    private String extractCategory(String query) {
        String lowerQuery = query.toLowerCase();
        
        // CPU (더 많은 키워드와 맥락 추가)
        if (lowerQuery.contains("cpu") || lowerQuery.contains("프로세서") || 
            lowerQuery.contains("인텔") || lowerQuery.contains("amd") ||
            lowerQuery.contains("라이젠") || lowerQuery.contains("코어") ||
            lowerQuery.matches(".*\\d{4,5}[xkf].*") || // 7800X3D, 14700K 같은 패턴
            lowerQuery.contains("i5") || lowerQuery.contains("i7") || lowerQuery.contains("i9")) {
            return "CPU";
        }
        
        // 그래픽카드 (더 많은 키워드)
        if (lowerQuery.contains("그래픽") || lowerQuery.contains("vga") || 
            lowerQuery.contains("gpu") || lowerQuery.contains("지포스") ||
            lowerQuery.contains("rtx") || lowerQuery.contains("gtx") ||
            lowerQuery.contains("라데온") || lowerQuery.contains("게임") || 
            lowerQuery.contains("게이밍") || lowerQuery.contains("영상")) {
            return "그래픽카드";
        }
        
        // 메모리
        if (lowerQuery.contains("ram") || lowerQuery.contains("메모리") ||
            lowerQuery.contains("ddr")) {
            return "RAM";
        }
        
        // 메인보드
        if (lowerQuery.contains("메인보드") || lowerQuery.contains("마더보드") ||
            lowerQuery.contains("보드")) {
            return "메인보드";
        }
        
        // SSD (더 많은 키워드)
        if (lowerQuery.contains("ssd") || lowerQuery.contains("저장장치") ||
            lowerQuery.contains("하드") || lowerQuery.contains("nvme") ||
            lowerQuery.contains("m.2") || lowerQuery.contains("저장")) {
            return "SSD";
        }
        
        // 파워
        if (lowerQuery.contains("파워") || lowerQuery.contains("psu") ||
            lowerQuery.contains("전원")) {
            return "파워";
        }
        
        // 케이스
        if (lowerQuery.contains("케이스") || lowerQuery.contains("pc케이스")) {
            return "케이스";
        }
        
        // 쿨러
        if (lowerQuery.contains("쿨러") || lowerQuery.contains("cpu쿨러")) {
            return "쿨러";
        }
        
        // 맥락 기반 추론: 가격/예산만 언급된 경우 → CPU 기본 추천
        if ((lowerQuery.contains("저렴") || lowerQuery.contains("가성비") || 
             lowerQuery.contains("예산") || lowerQuery.contains("만원") ||
             lowerQuery.contains("추천") || lowerQuery.contains("좋아")) &&
            !lowerQuery.contains("견적")) {
            
            // "추천"이 포함되어 있으면 CPU 기본 추천
            if (lowerQuery.contains("추천") || lowerQuery.contains("좋아")) {
                return "CPU";
            }
        }
        
        return null;
    }

    // 부품 스펙 요약 문자열 만들기 (JSON 파싱 방식으로 수정)
    private String buildSpecString(Part part) {
        // 1. PartSpec 엔티티를 가져옵니다.
        PartSpec partSpec = part.getPartSpec();
        if (partSpec == null || partSpec.getSpecs() == null) {
            return "상세 스펙 정보 없음";
        }

        try {
            // 2. specs 컬럼의 JSON 문자열을 파싱합니다.
            JSONObject specs = new JSONObject(partSpec.getSpecs());

            // 3. 카테고리별로 JSON에서 스펙을 꺼내 씁니다.
            if ("CPU".equals(part.getCategory())) {
                return String.format("코어: %s / 쓰레드: %s / 소켓: %s / 클럭: %s",
                        specs.optString("cores", "정보없음"),
                        specs.optString("threads", "정보없음"),
                        specs.optString("socket", "정보없음"),
                        specs.optString("base_clock", "정보없음"));
            }
            
            if ("그래픽카드".equals(part.getCategory())) {
                String chipset = specs.optString("nvidia_chipset", specs.optString("amd_chipset", "정보없음"));
                return String.format("칩셋: %s / 메모리: %s / 부스트클럭: %s",
                        chipset,
                        specs.optString("gpu_memory_capacity", "정보없음"),
                        specs.optString("boost_clock", "정보없음"));
            }
            
            if ("RAM".equals(part.getCategory())) {
                return String.format("용량: %s / 속도: %s / 등급: %s / 타이밍: %s",
                        specs.optString("capacity", "정보없음"),
                        specs.optString("clock_speed", "정보없음"),
                        specs.optString("product_class", "정보없음"),
                        specs.optString("timing", "정보없음"));
            }
            
            if ("메인보드".equals(part.getCategory())) {
                return String.format("칩셋: %s / CPU소켓: %s / 폼팩터: %s / 메모리: %s",
                        specs.optString("chipset", "정보없음"),
                        specs.optString("cpu_socket", "정보없음"),
                        specs.optString("form_factor", "정보없음"),
                        specs.optString("memory_type", "정보없음"));
            }
            
            if ("SSD".equals(part.getCategory())) {
                return String.format("용량: %s / 인터페이스: %s / 폼팩터: %s / 읽기속도: %s",
                        specs.optString("capacity", "정보없음"),
                        specs.optString("interface", "정보없음"),
                        specs.optString("form_factor", "정보없음"),
                        specs.optString("read_speed", "정보없음"));
            }
            
            if ("파워".equals(part.getCategory())) {
                return String.format("정격출력: %s / 80PLUS: %s / 폼팩터: %s",
                        specs.optString("rated_power", "정보없음"),
                        specs.optString("plus_certification", "정보없음"),
                        specs.optString("form_factor", "정보없음"));
            }
            
            if ("케이스".equals(part.getCategory())) {
                return String.format("크기: %s / 지원파워: %s / GPU길이: %s",
                        specs.optString("case_size", "정보없음"),
                        specs.optString("power_included", "정보없음"),
                        specs.optString("gpu_support_length", "정보없음"));
            }
            
            if ("쿨러".equals(part.getCategory())) {
                return String.format("방식: %s / 소켓: %s / 높이: %s",
                        specs.optString("cooling_type", "정보없음"),
                        specs.optString("socket_support", "정보없음"),
                        specs.optString("height", "정보없음"));
            }

        } catch (Exception e) {
            // JSON 파싱 중 오류 발생 시
            return "스펙 처리 중 오류";
        }
        
        return "상세 스펙 확인 필요";
    }

    // Gemini API 호출 함수 (REST API 방식)
    private String callGeminiApi(String prompt) {
        try {
            // API 키 확인
            if (apiKey == null || apiKey.isEmpty() || apiKey.equals("${GOOGLE_API_KEY}")) {
                System.err.println("Gemini API 키가 설정되지 않았습니다. 간단한 응답 모드로 전환합니다.");
                return null; // 폴백 응답 사용
            }

            // Gemini REST API 엔드포인트 (v1 사용, gemini-2.5-flash 모델)
            String apiUrl = String.format(
                "https://generativelanguage.googleapis.com/v1/models/gemini-2.5-flash:generateContent?key=%s",
                apiKey
            );

            // 요청 본문 생성 (JSON)
            JSONObject requestBody = new JSONObject();
            JSONArray contents = new JSONArray();
            JSONObject content = new JSONObject();
            JSONArray parts = new JSONArray();
            JSONObject part = new JSONObject();
            
            part.put("text", prompt);
            parts.put(part);
            content.put("parts", parts);
            contents.put(content);
            requestBody.put("contents", contents);

            // 생성 설정 추가 (옵션)
            JSONObject generationConfig = new JSONObject();
            generationConfig.put("temperature", 0.7);
            generationConfig.put("topK", 40);
            generationConfig.put("topP", 0.95);
            generationConfig.put("maxOutputTokens", 1024);
            requestBody.put("generationConfig", generationConfig);

            // HTTP 헤더 설정
            HttpHeaders headers = new HttpHeaders();
            headers.setContentType(MediaType.APPLICATION_JSON);

            // HTTP 요청 생성
            HttpEntity<String> entity = new HttpEntity<>(requestBody.toString(), headers);

            // RestTemplate을 사용하여 API 호출
            RestTemplate restTemplate = new RestTemplate();
            ResponseEntity<String> response = restTemplate.postForEntity(apiUrl, entity, String.class);

            // 응답 파싱
            JSONObject responseJson = new JSONObject(response.getBody());
            
            // candidates 배열 확인
            if (!responseJson.has("candidates") || responseJson.getJSONArray("candidates").length() == 0) {
                System.err.println("Gemini API 응답에 candidates가 없습니다.");
                System.err.println("응답 본문: " + response.getBody());
                throw new RuntimeException("Gemini API 응답에 candidates가 없습니다.");
            }
            
            // candidates[0].content.parts[0].text 경로로 응답 텍스트 추출
            JSONObject candidate = responseJson.getJSONArray("candidates").getJSONObject(0);
            
            // safetyRatings 확인 (차단된 경우)
            if (candidate.has("finishReason") && !candidate.getString("finishReason").equals("STOP")) {
                String finishReason = candidate.getString("finishReason");
                System.err.println("Gemini API 응답이 차단되었습니다. finishReason: " + finishReason);
                throw new RuntimeException("Gemini API 응답이 차단되었습니다: " + finishReason);
            }
            
            String aiResponse = candidate
                .getJSONObject("content")
                .getJSONArray("parts")
                .getJSONObject(0)
                .getString("text");

            return aiResponse;

        } catch (org.springframework.web.client.HttpClientErrorException e) {
            System.err.println("Gemini API HTTP 오류: " + e.getStatusCode() + " - " + e.getMessage());
            System.err.println("응답 본문: " + e.getResponseBodyAsString());
            e.printStackTrace();
            
            // 폴백: 간단한 키워드 기반 응답 반환 (프론트엔드 폴백이 처리하도록)
            return null;
            
        } catch (Exception e) {
            System.err.println("Gemini API 호출 중 예상치 못한 오류: " + e.getMessage());
            e.printStackTrace();
            return null;
        }
    }
    
    /**
     * 견적 설명 생성을 위한 Gemini API 호출 (BuildRecommendationService에서 사용)
     */
    public String generateBuildExplanation(String prompt) {
        return callGeminiApi(prompt);
    }
}