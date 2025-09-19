package com.danawa.webservice.controller;

import com.danawa.webservice.domain.Part;
import com.danawa.webservice.repository.PartRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;
import java.util.stream.Collectors;

@RestController
@RequiredArgsConstructor
public class PartController {

    private final PartRepository partRepository;

    // [수정된 부분 1]
    // 이제 /api/parts?category=CPU 와 같은 요청을 처리합니다.
    // 카테고리 파라미터가 없으면 모든 부품을 반환합니다.
    // [수정된 부분] manufacturer 파라미터를 추가로 받아 필터링
    @GetMapping("/api/parts")
    public List<Part> getParts(
            @RequestParam String category,
            @RequestParam(required = false) String manufacturer
    ) {
        if (manufacturer != null && !manufacturer.isEmpty()) {
            return partRepository.findByCategoryAndNameStartsWith(category, manufacturer);
        }
        return partRepository.findByCategory(category);
    }

    // [새로 추가된 부분]
    // 지정된 카테고리의 모든 제조사 목록을 중복 없이 반환합니다.
    @GetMapping("/api/manufacturers")
    public List<String> getManufacturersByCategory(@RequestParam String category) {
        List<Part> parts = partRepository.findByCategory(category);
        return parts.stream()
                .map(part -> part.getName().split(" ")[0]) // 이름의 첫 단어를 제조사로 간주
                .distinct() // 중복 제거
                .sorted()   // 가나다순 정렬
                .collect(Collectors.toList());
    }

    // [수정된 부분 2]
    // 이제 /api/parts/search?category=CPU&keyword=i5 와 같은 요청을 처리합니다.
    @GetMapping("/api/parts/search")
    public List<Part> searchParts(
            @RequestParam(required = false) String category,
            @RequestParam String keyword
    ) {
        if (category != null && !category.isEmpty()) {
            return partRepository.findByCategoryAndNameContainingIgnoreCase(category, keyword);
        }
        return partRepository.findByNameContainingIgnoreCase(keyword);
    }
}