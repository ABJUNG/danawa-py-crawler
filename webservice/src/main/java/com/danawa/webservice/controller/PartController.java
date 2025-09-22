package com.danawa.webservice.controller;

import com.danawa.webservice.domain.Part;
import com.danawa.webservice.repository.PartRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

@RestController
@RequiredArgsConstructor
public class PartController {

    private final PartRepository partRepository;

    // [수정된 부분] 반환 타입을 Page<Part>로 변경
    @GetMapping("/api/parts")
    public Page<Part> getParts(
            @RequestParam String category,
            @RequestParam(required = false) String manufacturer,
            Pageable pageable
    ) {
        if (manufacturer != null && !manufacturer.isEmpty()) {
            // [수정된 부분] pageable 인자 전달
            return partRepository.findByCategoryAndNameStartsWith(category, manufacturer, pageable);
        }
        // [수정된 부분] pageable 인자 전달
        return partRepository.findByCategory(category, pageable);
    }

    // [수정된 부분] 새로 만든 최적화된 메소드 호출
    @GetMapping("/api/manufacturers")
    public List<String> getManufacturersByCategory(@RequestParam String category) {
        return partRepository.findDistinctManufacturersByCategory(category);
    }

    // [수정된 부분] 반환 타입을 Page<Part>로 변경하고, pageable 인자 전달
    @GetMapping("/api/parts/search")
    public Page<Part> searchParts(
            @RequestParam String category,
            @RequestParam String keyword,
            Pageable pageable
    ) {
        return partRepository.findByCategoryAndNameContainingIgnoreCase(category, keyword, pageable);
    }
}