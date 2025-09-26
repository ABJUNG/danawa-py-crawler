package com.danawa.webservice.controller;

import com.danawa.webservice.domain.Part;
import com.danawa.webservice.service.PartService;
import lombok.RequiredArgsConstructor;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.http.ResponseEntity;
import org.springframework.util.MultiValueMap;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.util.Map;
import java.util.Set; // 반환 타입 Set으로 변경

@RestController
@RequiredArgsConstructor
public class PartController {

    private final PartService partService;

    /**
     * 상품 목록을 필터링, 페이징, 정렬하여 반환하는 API 입니다.
     * 이 부분은 이미 동적으로 잘 구현되어 있으므로 수정할 필요가 없습니다.
     */
    @GetMapping("/api/parts")
    public Page<Part> getParts(@RequestParam MultiValueMap<String, String> allParams, Pageable pageable) {
        return partService.findByFilters(allParams, pageable);
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
}