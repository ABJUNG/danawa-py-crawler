package com.danawa.webservice.service;

import com.danawa.webservice.domain.Part;
import com.danawa.webservice.repository.PartRepository;
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

    @Value("${gemini.api.key}") // application.properties에서 API 키 가져오기
    private String apiKey;

    public String getAiResponse(String userQuery) {
        // 1. 사용자 쿼리 분석 (간단 버전: 카테고리만 추출 시도)
        String category = extractCategory(userQuery); // 예: "CPU", "그래픽카드" 등
        if (category == null) {
            return "어떤 종류의 부품을 찾으시는지 명확하지 않아요. 😅\n\n예시:\n- \"게임용 그래픽카드 추천해줘\"\n- \"저렴한 CPU 찾아줘\"\n- \"고성능 SSD 알려줘\"";
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

        return aiResponse;
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

    // 사용자 쿼리에서 카테고리 추출 (개선된 버전)
    private String extractCategory(String query) {
        String lowerQuery = query.toLowerCase();
        
        // CPU
        if (lowerQuery.contains("cpu") || lowerQuery.contains("프로세서") || 
            lowerQuery.contains("인텔") || lowerQuery.contains("amd") ||
            lowerQuery.contains("라이젠") || lowerQuery.contains("코어")) {
            return "CPU";
        }
        
        // 그래픽카드
        if (lowerQuery.contains("그래픽") || lowerQuery.contains("vga") || 
            lowerQuery.contains("gpu") || lowerQuery.contains("지포스") ||
            lowerQuery.contains("rtx") || lowerQuery.contains("gtx") ||
            lowerQuery.contains("라데온")) {
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
        
        // SSD
        if (lowerQuery.contains("ssd") || lowerQuery.contains("저장장치")) {
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
                System.err.println("Gemini API 키가 설정되지 않았습니다.");
                return "컴박사입니다! 🤖 (AI 서비스 연결 실패 - API 키 없음)";
            }

            // Gemini REST API 엔드포인트
            String apiUrl = String.format(
                "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key=%s",
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
            
            // 폴백: 테스트용 응답
            System.out.println("--- [폴백 모드] 전달된 프롬프트 ---");
            System.out.println(prompt);
            System.out.println("--------------------");
            return "컴박사입니다! 🤖 (AI 응답 테스트 모드 - API 호출 실패)";
            
        } catch (Exception e) {
            System.err.println("Gemini API 호출 중 예상치 못한 오류: " + e.getMessage());
            e.printStackTrace();
            return "AI 응답 생성 중 오류가 발생했습니다.";
        }
    }
    
    /**
     * 견적 설명 생성을 위한 Gemini API 호출 (BuildRecommendationService에서 사용)
     */
    public String generateBuildExplanation(String prompt) {
        return callGeminiApi(prompt);
    }
}