package com.danawa.webservice.service;

import com.danawa.webservice.domain.Part;
import com.danawa.webservice.repository.PartRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.beans.factory.annotation.Value; // API 키 주입 위해 추가
import org.springframework.data.domain.PageRequest; // DB 조회 위해 추가
import org.springframework.data.domain.Sort; // DB 조회 위해 추가
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import com.danawa.webservice.domain.PartSpec;
import org.json.JSONObject;

import java.util.List;
import java.util.stream.Collectors;

// Google AI SDK 관련 import (예시 - 실제 SDK에 맞게 수정 필요)
// import com.google.cloud.vertexai.VertexAI;
// import com.google.cloud.vertexai.api.GenerateContentResponse;
// import com.google.cloud.vertexai.generativeai.GenerativeModel;
// import com.google.cloud.vertexai.generativeai.ResponseHandler;

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
            return "어떤 종류의 부품을 찾으시는지 명확하지 않아요. (예: CPU 추천해줘)";
        }

        // 2. DB에서 관련 데이터 검색 (예: 해당 카테고리 가격 낮은 순 5개)
        List<Part> relevantParts = partRepository.findAll(
                (root, query, cb) -> cb.equal(root.get("category"), category), // 카테고리 필터
                PageRequest.of(0, 5, Sort.by(Sort.Direction.ASC, "price")) // 0페이지, 5개, 가격 오름차순
        ).getContent();

        if (relevantParts.isEmpty()) {
            return category + " 카테고리의 부품 정보를 찾을 수 없어요.";
        }

        // 3. 참고 자료(Context) 문자열 만들기
        String context = relevantParts.stream()
                .map(part -> String.format("제품명: %s, 가격: %d원, 스펙: %s",
                        part.getName(), part.getPrice(), buildSpecString(part))) // buildSpecString은 부품 스펙 요약 함수 (아래 예시)
                .collect(Collectors.joining("\n"));

        // 4. 프롬프트 구성
        String prompt = String.format(
                """
                # 페르소나
                너는 PC 부품 전문가 '컴박사'야. 사용자의 질문에 대해 아래 '참고 자료'만을 바탕으로 답변해야 해.
    
                # 지시사항
                1. 반드시 '참고 자료' 안의 정보만 사용해서 답변해. 없는 내용은 말하지 마.
                2. 사용자의 질문에 가장 적합한 부품을 추천하고, 그 이유를 가격과 스펙을 근거로 설명해줘.
                3. 답변은 "컴박사입니다! 🤖" 로 시작해줘.
    
                ---
                ## 참고 자료 ##
                %s
                ---
    
                # 사용자 질문
                %s
                """, context, userQuery
        );

        // 5. Gemini API 호출 (실제 SDK 사용법에 맞게 수정 필요)
        String aiResponse = callGeminiApi(prompt); // 아래 callGeminiApi 함수 예시 참고

        return aiResponse;
    }

    // 사용자 쿼리에서 카테고리 추출 (간단 예시)
    private String extractCategory(String query) {
        if (query.contains("CPU")) return "CPU";
        if (query.contains("그래픽카드") || query.contains("VGA")) return "그래픽카드";
        // ... 다른 카테고리 추가 ...
        return null;
    }

    // 부품 스펙 요약 문자열 만들기 (간단 예시)
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
                return String.format("%s / %s / %s",
                        specs.optString("cores", ""), // optString은 키가 없어도 오류 대신 빈 문자열 반환
                        specs.optString("threads", ""),
                        specs.optString("socket", ""));
            }
            if ("그래픽카드".equals(part.getCategory())) {
                String chipset = specs.optString("nvidia_chipset", specs.optString("amd_chipset"));
                return String.format("%s / %s",
                        chipset,
                        specs.optString("gpu_memory_capacity", ""));
            }
            if ("RAM".equals(part.getCategory())) {
                return String.format("%s / %s / %s",
                        specs.optString("capacity", ""),
                        specs.optString("clock_speed", ""),
                        specs.optString("product_class", ""));
            }
            // ... (필요한 다른 카테고리들도 위와 같은 방식으로 추가) ...

        } catch (Exception e) {
            // JSON 파싱 중 오류 발생 시
            return "스펙 처리 중 오류";
        }
        
        return "상세 스펙 확인 필요";
    }

    // Gemini API 호출 함수 (실제 SDK 사용 예시 - 세부 내용은 SDK 문서 참조)
    private String callGeminiApi(String prompt) {
        // try (VertexAI vertexAi = new VertexAI("YOUR_PROJECT_ID", "YOUR_LOCATION")) { // 프로젝트 ID, 위치 설정
        //     GenerativeModel model = new GenerativeModel("gemini-1.5-flash-001", vertexAi); // 사용할 모델 지정
        //     GenerateContentResponse response = model.generateContent(prompt);
        //     return ResponseHandler.getText(response);
        // } catch (IOException e) {
        //     e.printStackTrace();
        //     return "AI 응답 생성 중 오류가 발생했습니다.";
        // }

        // --- 임시 테스트용 응답 ---
        System.out.println("--- 전달된 프롬프트 ---");
        System.out.println(prompt);
        System.out.println("--------------------");
        return "컴박사입니다! 🤖 (AI 응답 테스트) 사용자 질문: " + prompt.substring(prompt.lastIndexOf("# 사용자 질문") + 10).trim();
        // --- 임시 테스트용 응답 끝 ---
    }
}