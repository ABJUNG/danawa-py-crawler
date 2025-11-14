package com.danawa.webservice.controller;

import com.danawa.webservice.service.PartService;
import lombok.RequiredArgsConstructor;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.http.ResponseEntity;
import org.springframework.util.MultiValueMap;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import com.danawa.webservice.service.ChatService; // ChatService import 추가
import org.springframework.web.bind.annotation.PostMapping; // POST 요청 위해 추가
import org.springframework.web.bind.annotation.RequestBody; // 요청 본문 받기 위해 추가
import com.danawa.webservice.dto.PartResponseDto;

import java.util.List;
import java.util.Map;
import java.util.Set; // 반환 타입 Set으로 변경

@RestController
@RequiredArgsConstructor
public class PartController {

    private final PartService partService;
    private final ChatService chatService; // ChatService 주입 추가

    /**
     * 상품 목록을 필터링, 페이징, 정렬하여 반환하는 API 입니다.
     * 이 부분은 이미 동적으로 잘 구현되어 있으므로 수정할 필요가 없습니다.
     */
    @GetMapping("/api/parts")
    public Page<PartResponseDto> getParts(@RequestParam MultiValueMap<String, String> allParams, Pageable pageable) {
        return partService.findByFilters(allParams, pageable);
    }

    // [신설] ID 목록으로 여러 부품을 조회하는 API
    @GetMapping("/api/parts/compare")
    public ResponseEntity<List<PartResponseDto>> getPartsByIds(@RequestParam List<Long> ids) {
        List<PartResponseDto> parts = partService.findByIds(ids);
        return ResponseEntity.ok(parts);
    }

    /**
     * [수정] 선택된 카테고리에 해당하는 모든 필터 옵션을 동적으로 생성하여 반환하는 API 입니다.
     * 기존의 하드코딩된 switch 문을 제거하고, 서비스 레이어에 모든 로직을 위임합니다.
     */
    @GetMapping("/api/filters")
    public ResponseEntity<Map<String, Set<String>>> getFiltersByCategory(@RequestParam String category) {
        // PartService에 새로 만들 getAvailableFiltersForCategory 메서드를 호출합니다.
        // 이 메서드는 해당 카테고리의 모든 필터와 값들을 Map 형태로 반환할 것입니다.
        Map<String, Set<String>> filters = partService.getAvailableFiltersForCategory(category);
        return ResponseEntity.ok(filters);
    }

    @PostMapping("/api/chat")
    public ResponseEntity<String> getAiChatResponse(@RequestBody String userQuery) {
        String aiResponse = chatService.getAiResponse(userQuery);
        return ResponseEntity.ok(aiResponse);
    }
    
    /**
     * [신규] AI 견적 추천을 요청하는 엔드포인트
     * @param userQuery 사용자의 텍스트 입력 (예: "게이밍 PC 맞춰줘")
     * @return AI가 생성한 견적 (JSON 문자열)
     */
    @GetMapping("/api/v1/chat/recommend")
    public ResponseEntity<String> getAiRecommendation(@RequestParam String userQuery) {
        try {
            String recommendationJson = chatService.getAiRecommendation(userQuery);
            // AI가 JSON 형식을 반환하므로, Content-Type을 application/json으로 설정
            return ResponseEntity.ok()
                    .header("Content-Type", "application/json; charset=UTF-8")
                    .body(recommendationJson);
        } catch (IOException e) {
            e.printStackTrace();
            return ResponseEntity.internalServerError().body("AI 견적 생성에 실패했습니다.");
}