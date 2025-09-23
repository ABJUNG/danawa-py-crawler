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

import java.util.HashMap;
import java.util.Map;

@RestController
@RequiredArgsConstructor
public class PartController {

    private final PartService partService;

    @GetMapping("/api/parts")
    public Page<Part> getParts(@RequestParam MultiValueMap<String, String> allParams, Pageable pageable) {
        return partService.findByFilters(allParams, pageable);
    }

    @GetMapping("/api/filters")
    public ResponseEntity<Map<String, Object>> getFiltersByCategory(@RequestParam String category) {
        Map<String, Object> filters = new HashMap<>();

        filters.put("manufacturers", partService.getManufacturersByCategory(category));

        switch (category) {
            case "CPU":
                filters.put("socketTypes", partService.getSocketTypes(category));
                filters.put("coreTypes", partService.getCoreTypes(category));
                break;
            case "메인보드":
                filters.put("socketTypes", partService.getSocketTypes(category));
                break;
            case "RAM":
                filters.put("ramCapacities", partService.getRamCapacities(category));
                break;
            case "그래픽카드":
                filters.put("chipsets", partService.getChipsetManufacturers(category));
                break;
        }
        return ResponseEntity.ok(filters);
    }
}