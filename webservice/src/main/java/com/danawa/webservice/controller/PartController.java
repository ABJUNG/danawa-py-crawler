package com.danawa.webservice.controller;

// import com.danawa.webservice.domain.Part; // 👈 이제 Part 대신 PartResponseDto를 사용
import com.danawa.webservice.service.PartService;
import lombok.RequiredArgsConstructor;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.http.ResponseEntity;
import org.springframework.util.MultiValueMap;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import com.danawa.webservice.service.ChatService; 
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import com.danawa.webservice.dto.PartResponseDto; // 👈 DTO import

import java.util.List;
import java.util.Map;
import java.util.Set;

@RestController
@RequiredArgsConstructor
public class PartController {

    private final PartService partService;
    private final ChatService chatService;

    /**
     * [수정됨] 상품 목록을 DTO로 변환하여 반환합니다.
     */
    @GetMapping("/api/parts")
    // 1. 반환 타입을 Page<Part>에서 ResponseEntity<Page<PartResponseDto>>로 변경
    public ResponseEntity<Page<PartResponseDto>> getParts(@RequestParam MultiValueMap<String, String> allParams, Pageable pageable) {
        // PartService가 Page<PartResponseDto>를 반환하도록 5.2 단계에서 수정했습니다.
        Page<PartResponseDto> partPage = partService.findByFilters(allParams, pageable);
        return ResponseEntity.ok(partPage);
    }

    /**
     * [수정됨] ID 목록으로 여러 부품을 조회하는 API (DTO로 반환)
     */
    @GetMapping("/api/parts/compare")
    // 2. 반환 타입이 ResponseEntity<List<PartResponseDto>>로 이미 맞습니다.
    public ResponseEntity<List<PartResponseDto>> getPartsByIds(@RequestParam("ids") List<Long> ids) { // @RequestParam에 "ids" 명시
        // 3. PartService가 List<PartResponseDto>를 반환하도록 수정합니다.
        List<PartResponseDto> partsDto = partService.findByIds(ids);
        return ResponseEntity.ok(partsDto); // DTO 리스트를 반환
    }

    /**
     * 필터 옵션을 동적으로 생성하여 반환하는 API 입니다.
     */
    @GetMapping("/api/filters")
    public ResponseEntity<Map<String, Set<String>>> getFiltersByCategory(@RequestParam String category) {
        Map<String, Set<String>> filters = partService.getAvailableFiltersForCategory(category);
        return ResponseEntity.ok(filters);
    }

    /**
     * AI 채팅 응답 API
     */
    @PostMapping("/api/chat")
    public ResponseEntity<String> getAiChatResponse(@RequestBody String userQuery) {
        String aiResponse = chatService.getAiResponse(userQuery);
        return ResponseEntity.ok(aiResponse);
    }
}