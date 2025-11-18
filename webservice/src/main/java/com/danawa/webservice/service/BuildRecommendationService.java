package com.danawa.webservice.service;

import com.danawa.webservice.domain.Part;
import com.danawa.webservice.dto.BuildRecommendationDto;
import com.danawa.webservice.dto.BuildRequestDto;
import com.danawa.webservice.dto.CompatibilityResult;
import com.danawa.webservice.dto.PartResponseDto;
import com.danawa.webservice.repository.PartRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.json.JSONObject;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Sort;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.*;
import java.util.stream.Collectors;
import java.util.Arrays;

@Slf4j
@Service
@Transactional(readOnly = true)
@RequiredArgsConstructor
public class BuildRecommendationService {
    
    private final PartRepository partRepository;
    private final CompatibilityService compatibilityService;
    private final JdbcTemplate jdbcTemplate;
    private final ChatService chatService; // Gemini API 호출을 위해 추가
    
    /**
     * 사용자 요구사항에 맞는 PC 견적을 추천합니다.
     */
    public BuildRecommendationDto recommendBuild(BuildRequestDto request) {
        log.info("견적 추천 요청 - 예산: {}, 용도: {}", request.getBudget(), request.getPurpose());
        
        // 1. 용도별 예산 배분 가져오기
        Map<String, Integer> budgetAllocation = getBudgetAllocation(
            request.getPurpose(), 
            request.getBudget(),
            request.getPreferences()
        );
        
        // 2. 각 카테고리별 최적 부품 후보 선택
        Map<String, Part> selectedParts = new HashMap<>();
        
        for (Map.Entry<String, Integer> entry : budgetAllocation.entrySet()) {
            String category = entry.getKey();
            int categoryBudget = entry.getValue();
            
            // 쿨러는 공랭 쿨러 우선 선택
            if ("쿨러".equals(category)) {
                Part bestPart = findBestCooler(categoryBudget, request.getPreferences());
                if (bestPart != null) {
                    selectedParts.put(category, bestPart);
                }
            } else {
                Part bestPart = findBestPartInBudget(category, categoryBudget, request.getPreferences());
                if (bestPart != null) {
                    selectedParts.put(category, bestPart);
                }
            }
        }
        
        // 쿨러가 빠진 경우 강제 추가 (공랭 쿨러)
        if (!selectedParts.containsKey("쿨러")) {
            log.warn("쿨러가 선택되지 않았습니다. 기본 공랭 쿨러를 추가합니다.");
            int coolerBudget = (int)(request.getBudget() * 0.03);
            Part defaultCooler = findBestCooler(coolerBudget, request.getPreferences());
            if (defaultCooler != null) {
                selectedParts.put("쿨러", defaultCooler);
            }
        }
        
        // 3. 호환성 검사
        List<Long> partIds = selectedParts.values().stream()
            .map(Part::getId)
            .collect(Collectors.toList());
        
        CompatibilityResult compatibilityCheck = compatibilityService.checkCompatibility(partIds);
        
        // 4. 호환성 문제가 있으면 대체 부품 찾기
        if (!compatibilityCheck.isCompatible()) {
            log.warn("호환성 문제 발생, 대체 부품 검색 중...");
            selectedParts = resolveCompatibilityIssues(selectedParts, budgetAllocation, request);
            
            // 재검사
            partIds = selectedParts.values().stream()
                .map(Part::getId)
                .collect(Collectors.toList());
            compatibilityCheck = compatibilityService.checkCompatibility(partIds);
        }
        
        // 5. 결과 DTO 생성
        Map<String, PartResponseDto> recommendedParts = new HashMap<>();
        int totalPrice = 0;
        
        for (Map.Entry<String, Part> entry : selectedParts.entrySet()) {
            Part part = entry.getValue();
            recommendedParts.put(entry.getKey(), PartResponseDto.fromEntity(part));
            totalPrice += part.getPrice();
        }
        
        // 6. 업그레이드 옵션 생성
        List<BuildRecommendationDto.UpgradeOption> upgradeOptions = 
            generateUpgradeOptions(selectedParts, request.getBudget(), totalPrice);
        
        // 7. AI 설명 생성 (프롬프트 기반)
        String explanation = generateAIExplanation(selectedParts, request, totalPrice, compatibilityCheck);
        
        return BuildRecommendationDto.builder()
            .recommendedParts(recommendedParts)
            .totalPrice(totalPrice)
            .explanation(explanation)
            .upgradeOptions(upgradeOptions)
            .compatibilityCheck(compatibilityCheck)
            .build();
    }
    
    /**
     * 용도별 예산 배분 가져오기
     */
    private Map<String, Integer> getBudgetAllocation(String purpose, int totalBudget, Map<String, Object> preferences) {
        String sql = """
            SELECT category, weight_percentage
            FROM usage_weights
            WHERE usage_type = ?
            ORDER BY priority ASC
        """;
        
        List<Map<String, Object>> weights = jdbcTemplate.queryForList(sql, purpose);
        
        Map<String, Integer> allocation = new HashMap<>();
        
        if (weights.isEmpty()) {
            // 기본 배분 (용도 정보 없을 때) - 쿨러와 HDD 추가
            allocation.put("CPU", (int)(totalBudget * 0.22));
            allocation.put("쿨러", (int)(totalBudget * 0.03)); // 쿨러 필수 추가 (공랭 기준 3%)
            allocation.put("그래픽카드", (int)(totalBudget * 0.26));
            allocation.put("RAM", (int)(totalBudget * 0.12));
            allocation.put("SSD", (int)(totalBudget * 0.09));
            allocation.put("HDD", (int)(totalBudget * 0.06)); // HDD 추가 (선택적)
            allocation.put("메인보드", (int)(totalBudget * 0.14));
            allocation.put("파워", (int)(totalBudget * 0.05));
            allocation.put("케이스", (int)(totalBudget * 0.03));
        } else {
            for (Map<String, Object> row : weights) {
                String category = (String) row.get("category");
                int percentage = (Integer) row.get("weight_percentage");
                allocation.put(category, (int)(totalBudget * percentage / 100.0));
            }
        }
        
        // component_ratios가 제공된 경우 0% 부품 제외 처리
        if (preferences != null && preferences.containsKey("component_ratios")) {
            try {
                @SuppressWarnings("unchecked")
                Map<String, Object> componentRatios = (Map<String, Object>) preferences.get("component_ratios");
                
                // 카테고리 매핑
                Map<String, String> categoryMapping = new HashMap<>();
                categoryMapping.put("cpu", "CPU");
                categoryMapping.put("gpu", "그래픽카드");
                categoryMapping.put("mainboard", "메인보드");
                categoryMapping.put("ram", "RAM");
                categoryMapping.put("storage", "SSD"); // storage는 SSD로 매핑
                categoryMapping.put("psu", "파워");
                categoryMapping.put("case", "케이스");
                categoryMapping.put("cooler", "쿨러");
                
                // 0% 부품 제외
                for (Map.Entry<String, Object> entry : componentRatios.entrySet()) {
                    String key = entry.getKey();
                    Object ratioObj = entry.getValue();
                    
                    if (ratioObj instanceof Number) {
                        int ratio = ((Number) ratioObj).intValue();
                        String dbCategory = categoryMapping.get(key);
                        
                        if (ratio == 0 && dbCategory != null) {
                            // 0%인 카테고리는 제외
                            allocation.remove(dbCategory);
                            log.info("0% 설정으로 {} 카테고리 제외", dbCategory);
                        }
                    }
                }
            } catch (Exception e) {
                log.warn("component_ratios 처리 중 오류 발생: {}", e.getMessage());
            }
        }
        
        return allocation;
    }
    
    /**
     * 공랭 쿨러 우선 선택 (자동 추천 시)
     */
    private Part findBestCooler(int budget, Map<String, Object> preferences) {
        // 추천 스타일에 따른 가격 범위
        String recommendStyle = getStringValue(preferences, "recommend_style", "balanced");
        double minMultiplier = 0.7;
        double maxMultiplier = 1.3;
        
        if ("value".equals(recommendStyle)) {
            minMultiplier = 0.5;
            maxMultiplier = 0.9;
        } else if ("highend".equals(recommendStyle)) {
            minMultiplier = 0.9;
            maxMultiplier = 1.5;
        }
        
        int minPrice = (int)(budget * minMultiplier);
        int maxPrice = (int)(budget * maxMultiplier);
        
        // 쿨러 검색 (공랭 쿨러 우선)
        List<Part> candidates = partRepository.findAll(
            (root, query, cb) -> cb.and(
                cb.equal(root.get("category"), "쿨러"),
                cb.between(root.get("price"), minPrice, maxPrice)
            ),
            PageRequest.of(0, 20, Sort.by(
                Sort.Order.desc("starRating"),
                Sort.Order.asc("price")
            ))
        ).getContent();
        
        // 공랭 쿨러 필터링 (스펙에서 "공랭" 또는 "타워형" 포함)
        List<Part> airCoolers = candidates.stream()
            .filter(p -> {
                try {
                    if (p.getPartSpec() != null && p.getPartSpec().getSpecs() != null) {
                        JSONObject specsJson = new JSONObject(p.getPartSpec().getSpecs());
                        String productClass = specsJson.optString("product_class", "");
                        // 공랭, 타워형, 사이드플로우 등의 키워드 포함 시 공랭으로 판단
                        return productClass.contains("공랭") || 
                               productClass.contains("타워형") || 
                               productClass.contains("사이드플로우") ||
                               !productClass.contains("수랭"); // 수랭이 아니면 공랭으로 간주
                    }
                } catch (Exception e) {
                    log.debug("쿨러 스펙 파싱 실패: {}", e.getMessage());
                }
                return true; // 스펙 정보가 없으면 공랭으로 간주
            })
            .collect(Collectors.toList());
        
        // 공랭 쿨러가 있으면 우선 선택
        if (!airCoolers.isEmpty()) {
            return airCoolers.get(0);
        }
        
        // 공랭 쿨러가 없으면 일반 쿨러 중 선택
        return candidates.isEmpty() ? null : candidates.get(0);
    }
    
    /**
     * 예산 내 최적 부품 찾기 (개선된 버전)
     */
    private Part findBestPartInBudget(String category, int budget, Map<String, Object> preferences) {
        // 예산 여유도 가져오기 (0-20%, 기본값 10%)
        int budgetFlexibilityPercent = 10;
        if (preferences != null && preferences.containsKey("budget_flexibility")) {
            Object flexObj = preferences.get("budget_flexibility");
            if (flexObj instanceof Number) {
                budgetFlexibilityPercent = ((Number) flexObj).intValue();
            }
        }
        double budgetFlexibility = budgetFlexibilityPercent / 100.0; // 0.0 ~ 0.2
        
        // AI 유연성에 따른 가격 범위 조정
        String aiFlexibility = getStringValue(preferences, "ai_flexibility", "strict");
        double flexibilityMultiplier = "flexible".equals(aiFlexibility) ? 1.3 : 1.2; // 유연 모드는 30%까지 허용
        
        // 추천 스타일에 따른 가격 범위 조정
        String recommendStyle = getStringValue(preferences, "recommend_style", "balanced");
        double minMultiplier = 0.8 - budgetFlexibility; // 예산 여유도를 최소값에도 적용
        double maxMultiplier = flexibilityMultiplier + budgetFlexibility; // 예산 여유도를 최대값에도 적용
        
        if ("value".equals(recommendStyle)) {
            // 가성비: 예산의 (60%-여유도) ~ (90%+여유도) 범위에서 검색
            minMultiplier = 0.6 - budgetFlexibility;
            maxMultiplier = 0.9 + budgetFlexibility;
        } else if ("highend".equals(recommendStyle)) {
            // 최고사양: 예산의 (90%-여유도) ~ (120%+여유도) 범위에서 검색
            minMultiplier = 0.9 - budgetFlexibility;
            maxMultiplier = flexibilityMultiplier + budgetFlexibility;
        }
        
        // 최소값이 음수가 되지 않도록 보정
        minMultiplier = Math.max(0.3, minMultiplier);
        
        int minPrice = (int)(budget * minMultiplier);
        int maxPrice = (int)(budget * maxMultiplier);
        
        // 정렬 기준 설정 (추천 스타일에 따라)
        Sort sort;
        if ("value".equals(recommendStyle)) {
            // 가성비: 가격 낮은 순 + 별점 높은 순
            sort = Sort.by(
                Sort.Order.asc("price"),
                Sort.Order.desc("starRating")
            );
        } else if ("highend".equals(recommendStyle)) {
            // 최고사양: 가격 높은 순 + 별점 높은 순
            sort = Sort.by(
                Sort.Order.desc("price"),
                Sort.Order.desc("starRating")
            );
        } else {
            // 균형형: 별점 높은 순
            sort = Sort.by(Sort.Direction.DESC, "starRating");
        }
        
        // 카테고리, 가격 범위로 검색
        List<Part> candidates = partRepository.findAll(
            (root, query, cb) -> cb.and(
                cb.equal(root.get("category"), category),
                cb.between(root.get("price"), minPrice, maxPrice)
            ),
            PageRequest.of(0, 10, sort)
        ).getContent();
        
        if (candidates.isEmpty()) {
            // 범위 확대
            candidates = partRepository.findAll(
                (root, query, cb) -> cb.and(
                    cb.equal(root.get("category"), category),
                    cb.le(root.get("price"), maxPrice)
                ),
                PageRequest.of(0, 5, sort)
            ).getContent();
        }
        
        // RAM 카테고리인 경우 노트북용 제외
        if ("RAM".equals(category)) {
            candidates = candidates.stream()
                .filter(p -> !isNotebookRam(p))
                .collect(Collectors.toList());
            
            // 노트북용만 남은 경우 원본 반환 (데스크탑용이 없을 수 있음)
            if (candidates.isEmpty()) {
                log.warn("데스크탑용 RAM을 찾을 수 없습니다. 노트북용 제외 필터를 해제합니다.");
                candidates = partRepository.findAll(
                    (root, query, cb) -> cb.and(
                        cb.equal(root.get("category"), category),
                        cb.le(root.get("price"), maxPrice)
                    ),
                    PageRequest.of(0, 5, sort)
                ).getContent();
            }
        }
        
        // 추가 필터링 (선택사항)
        candidates = applyAdvancedFilters(candidates, category, preferences);
        
        // 브랜드 선호도 적용
        if (preferences != null && preferences.containsKey("preferred_brand")) {
            String preferredBrand = getStringValue(preferences, "preferred_brand", null);
            if (preferredBrand != null) {
                Optional<Part> preferredPart = candidates.stream()
                    .filter(p -> p.getManufacturer() != null && 
                                 p.getManufacturer().equalsIgnoreCase(preferredBrand))
                    .findFirst();
                
                if (preferredPart.isPresent()) {
                    return preferredPart.get();
                }
            }
        }
        
        // 기본: 리스트 첫 번째 부품 선택 (이미 정렬됨)
        return candidates.isEmpty() ? null : candidates.get(0);
    }
    
    /**
     * 고급 필터 적용 (RGB, 소음, 전력, 케이스 크기, 패널, 색상, 재질, AS 기준 등)
     */
    private List<Part> applyAdvancedFilters(List<Part> candidates, String category, Map<String, Object> preferences) {
        if (candidates.isEmpty()) return candidates;
        
        List<Part> filtered = new ArrayList<>(candidates);
        
        // 1. 케이스 크기 필터링 및 외장 하드 케이스 제외 (케이스 카테고리)
        if ("케이스".equals(category)) {
            // 외장 하드 케이스 제외
            filtered = filtered.stream()
                .filter(p -> !isExternalCase(p))
                .collect(Collectors.toList());
                
            String caseSize = getStringValue(preferences, "case_size", null);
            if (caseSize != null && !caseSize.isEmpty()) {
                List<Part> sizeFiltered = filtered.stream()
                    .filter(p -> matchesCaseSize(p, caseSize))
                    .collect(Collectors.toList());
                
                // 필터링 후 결과가 있으면 적용
                if (!sizeFiltered.isEmpty()) {
                    filtered = sizeFiltered;
                }
            }
        }
        
        // 2. 패널 형태 필터링 (케이스 카테고리)
        if ("케이스".equals(category)) {
            String panelType = getStringValue(preferences, "panel_type", null);
            if (panelType != null && !panelType.isEmpty()) {
                List<Part> panelFiltered = filtered.stream()
                    .filter(p -> matchesPanelType(p, panelType))
                    .collect(Collectors.toList());
                
                if (!panelFiltered.isEmpty()) {
                    filtered = panelFiltered;
                }
            }
        }
        
        // 3. 색상 테마 필터링 (케이스, 쿨러, RAM 등)
        if (Arrays.asList("케이스", "쿨러", "RAM").contains(category)) {
            Object colorThemeObj = preferences != null ? preferences.get("color_theme") : null;
            if (colorThemeObj != null) {
                // 배열 또는 문자열 처리
                List<String> colorThemes = new ArrayList<>();
                if (colorThemeObj instanceof List) {
                    @SuppressWarnings("unchecked")
                    List<Object> colorList = (List<Object>) colorThemeObj;
                    for (Object color : colorList) {
                        if (color != null) {
                            colorThemes.add(color.toString());
                        }
                    }
                } else if (colorThemeObj instanceof String) {
                    colorThemes.add((String) colorThemeObj);
                }
                
                if (!colorThemes.isEmpty()) {
                    // 색상 테마는 우선순위 정렬로 처리 (필터링하지 않음)
                    filtered.sort((p1, p2) -> {
                        boolean p1Matches = matchesAnyColorTheme(p1, colorThemes);
                        boolean p2Matches = matchesAnyColorTheme(p2, colorThemes);
                        if (p1Matches && !p2Matches) return -1;
                        if (!p1Matches && p2Matches) return 1;
                        return 0;
                    });
                }
            }
        }
        
        // 4. 재질 필터링 (케이스 카테고리)
        if ("케이스".equals(category)) {
            String material = getStringValue(preferences, "material", null);
            if (material != null && !material.isEmpty()) {
                List<Part> materialFiltered = filtered.stream()
                    .filter(p -> matchesMaterial(p, material))
                    .collect(Collectors.toList());
                
                if (!materialFiltered.isEmpty()) {
                    filtered = materialFiltered;
                }
            }
        }
        
        // 5. AS 기준 필터링 (모든 카테고리)
        String asCriteria = getStringValue(preferences, "as_criteria", null);
        if ("domestic".equals(asCriteria)) {
            // 국내 AS 우선 정렬
            filtered.sort((p1, p2) -> {
                boolean p1Domestic = hasDomesticAS(p1);
                boolean p2Domestic = hasDomesticAS(p2);
                if (p1Domestic && !p2Domestic) return -1;
                if (!p1Domestic && p2Domestic) return 1;
                return 0;
            });
        }
        
        // 6. 사용 수명 목표에 따른 내구성 고려
        String lifecycle = getStringValue(preferences, "lifecycle", null);
        if (lifecycle != null && !lifecycle.isEmpty()) {
            // 장기 사용 목표인 경우 내구성 높은 제품 우선
            if (lifecycle.contains("5년") || lifecycle.contains("7년") || lifecycle.contains("10년")) {
                filtered.sort((p1, p2) -> {
                    int durability1 = getDurabilityScore(p1);
                    int durability2 = getDurabilityScore(p2);
                    return Integer.compare(durability2, durability1); // 높은 내구성 우선
                });
            }
        }
        
        // 7. 업그레이드 계획에 따른 추천 로직
        String upgradePlan = getStringValue(preferences, "upgrade_plan", null);
        if ("true".equals(upgradePlan)) {
            // 업그레이드 계획이 있으면 확장성 좋은 제품 우선
            if ("메인보드".equals(category)) {
                filtered.sort((p1, p2) -> {
                    int expandability1 = getExpandabilityScore(p1);
                    int expandability2 = getExpandabilityScore(p2);
                    return Integer.compare(expandability2, expandability1);
                });
            }
        }
        
        // 8. RGB 조명 선호
        if ("true".equals(getStringValue(preferences, "rgb_lighting", "false"))) {
            // RGB가 있는 제품 우선 정렬 (스펙에서 확인)
            filtered.sort((p1, p2) -> {
                boolean p1HasRgb = hasRgbLighting(p1);
                boolean p2HasRgb = hasRgbLighting(p2);
                if (p1HasRgb && !p2HasRgb) return -1;
                if (!p1HasRgb && p2HasRgb) return 1;
                return 0;
            });
        }
        
        // 9. 전력 절약 모드
        if ("true".equals(getStringValue(preferences, "power_saving", "false"))) {
            // 저전력 부품 우선
            if ("CPU".equals(category)) {
                filtered.sort((p1, p2) -> {
                    int tdp1 = extractTdpFromSpecs(p1);
                    int tdp2 = extractTdpFromSpecs(p2);
                    return Integer.compare(tdp1, tdp2); // 낮은 TDP 우선
                });
            }
        }
        
        // 10. 소음 기준
        String noiseCriteria = getStringValue(preferences, "noise_criteria", null);
        if ("silent".equals(noiseCriteria) && ("쿨러".equals(category) || "파워".equals(category))) {
            // 저소음 제품 우선 정렬
            filtered.sort((p1, p2) -> {
                boolean p1Silent = isLowNoise(p1);
                boolean p2Silent = isLowNoise(p2);
                if (p1Silent && !p2Silent) return -1;
                if (!p1Silent && p2Silent) return 1;
                return 0;
            });
        }
        
        return filtered;
    }
    
    /**
     * RGB 조명 여부 확인
     */
    private boolean hasRgbLighting(Part part) {
        if (part.getPartSpec() == null || part.getPartSpec().getSpecs() == null) {
            return false;
        }
        try {
            JSONObject specs = new JSONObject(part.getPartSpec().getSpecs());
            String ledSystem = specs.optString("led_system", "").toLowerCase();
            String ledLight = specs.optString("led_light", "").toLowerCase();
            return ledSystem.contains("rgb") || ledLight.contains("rgb") || 
                   specs.optString("product_class", "").toLowerCase().contains("rgb");
        } catch (Exception e) {
            return false;
        }
    }
    
    /**
     * TDP 추출
     */
    private int extractTdpFromSpecs(Part part) {
        if (part.getPartSpec() == null || part.getPartSpec().getSpecs() == null) {
            return 999; // 정보 없으면 높은 값 반환
        }
        try {
            JSONObject specs = new JSONObject(part.getPartSpec().getSpecs());
            String tdp = specs.optString("tdp", specs.optString("thermal_design_power", ""));
            return Integer.parseInt(tdp.replaceAll("[^0-9]", ""));
        } catch (Exception e) {
            return 999;
        }
    }
    
    /**
     * 저소음 여부 확인
     */
    private boolean isLowNoise(Part part) {
        if (part.getPartSpec() == null || part.getPartSpec().getSpecs() == null) {
            return false;
        }
        try {
            JSONObject specs = new JSONObject(part.getPartSpec().getSpecs());
            String noise = specs.optString("max_fan_noise", "").toLowerCase();
            String productClass = specs.optString("product_class", "").toLowerCase();
            
            // 소음이 명시적으로 낮거나, "저소음" 키워드가 있는 경우
            if (noise.contains("저소음") || productClass.contains("저소음") || 
                noise.contains("무소음")) {
                return true;
            }
            
            // dBA 값이 25 이하면 저소음으로 간주
            try {
                String noiseValue = noise.replaceAll("[^0-9.]", "");
                if (!noiseValue.isEmpty()) {
                    double dba = Double.parseDouble(noiseValue);
                    return dba <= 25.0;
                }
            } catch (Exception ignored) {}
            
            return false;
        } catch (Exception e) {
            return false;
        }
    }
    
    /**
     * 케이스 크기 매칭 확인
     */
    private boolean matchesCaseSize(Part part, String caseSize) {
        if (part.getPartSpec() == null || part.getPartSpec().getSpecs() == null) {
            return false;
        }
        try {
            JSONObject specs = new JSONObject(part.getPartSpec().getSpecs());
            String caseSizeSpec = specs.optString("case_size", "").toLowerCase();
            String productClass = specs.optString("product_class", "").toLowerCase();
            String name = part.getName().toLowerCase();
            
            String sizeLower = caseSize.toLowerCase();
            
            // 매칭 로직
            if (sizeLower.contains("빅타워") || sizeLower.contains("full tower")) {
                return caseSizeSpec.contains("빅타워") || caseSizeSpec.contains("full") ||
                       productClass.contains("빅타워") || name.contains("빅타워");
            } else if (sizeLower.contains("미들타워") || sizeLower.contains("mid tower")) {
                return caseSizeSpec.contains("미들") || caseSizeSpec.contains("mid") ||
                       productClass.contains("미들") || name.contains("미들");
            } else if (sizeLower.contains("미니타워") || sizeLower.contains("mini tower")) {
                return caseSizeSpec.contains("미니") || caseSizeSpec.contains("mini") ||
                       productClass.contains("미니") || name.contains("미니");
            } else if (sizeLower.contains("sff") || sizeLower.contains("small form")) {
                return caseSizeSpec.contains("sff") || caseSizeSpec.contains("small") ||
                       productClass.contains("sff") || name.contains("sff");
            }
            
            return false;
        } catch (Exception e) {
            return false;
        }
    }
    
    /**
     * 패널 형태 매칭 확인
     */
    private boolean matchesPanelType(Part part, String panelType) {
        if (part.getPartSpec() == null || part.getPartSpec().getSpecs() == null) {
            return false;
        }
        try {
            JSONObject specs = new JSONObject(part.getPartSpec().getSpecs());
            String panelFront = specs.optString("panel_front", "").toLowerCase();
            String panelSide = specs.optString("panel_side", "").toLowerCase();
            String name = part.getName().toLowerCase();
            
            String panelLower = panelType.toLowerCase();
            
            if (panelLower.contains("강화유리") || panelLower.contains("tempered")) {
                return panelFront.contains("강화유리") || panelSide.contains("강화유리") ||
                       panelFront.contains("tempered") || panelSide.contains("tempered") ||
                       name.contains("강화유리") || name.contains("tempered");
            } else if (panelLower.contains("폐쇄") || panelLower.contains("closed")) {
                return panelFront.contains("폐쇄") || panelSide.contains("폐쇄") ||
                       name.contains("폐쇄");
            } else if (panelLower.contains("메시") || panelLower.contains("mesh")) {
                return panelFront.contains("메시") || panelFront.contains("mesh") ||
                       name.contains("메시") || name.contains("mesh");
            } else if (panelLower.contains("전면유리") || panelLower.contains("front glass")) {
                return panelFront.contains("유리") || panelFront.contains("glass") ||
                       name.contains("전면유리");
            }
            
            return false;
        } catch (Exception e) {
            return false;
        }
    }
    
    /**
     * 색상 테마 매칭 확인 (단일 색상)
     */
    private boolean matchesColorTheme(Part part, String colorTheme) {
        if (part == null || part.getName() == null) {
            return false;
        }
        try {
            String ledColor = "";
            if (part.getPartSpec() != null && part.getPartSpec().getSpecs() != null) {
                JSONObject specs = new JSONObject(part.getPartSpec().getSpecs());
                ledColor = specs.optString("led_color", "").toLowerCase();
            }
            String name = part.getName().toLowerCase();
            
            String colorLower = colorTheme.toLowerCase();
            
            if (colorLower.contains("블랙") || colorLower.contains("black")) {
                return name.contains("블랙") || name.contains("black") ||
                       ledColor.contains("블랙") || ledColor.contains("black");
            } else if (colorLower.contains("화이트") || colorLower.contains("white")) {
                return name.contains("화이트") || name.contains("white") ||
                       ledColor.contains("화이트") || ledColor.contains("white");
            } else if (colorLower.contains("실버") || colorLower.contains("silver")) {
                return name.contains("실버") || name.contains("silver") ||
                       ledColor.contains("실버") || ledColor.contains("silver");
            } else if (colorLower.contains("레드") || colorLower.contains("red")) {
                return name.contains("레드") || name.contains("red") ||
                       ledColor.contains("레드") || ledColor.contains("red");
            } else if (colorLower.contains("블루") || colorLower.contains("blue")) {
                return name.contains("블루") || name.contains("blue") ||
                       ledColor.contains("블루") || ledColor.contains("blue");
            }
            
            return false;
        } catch (Exception e) {
            return false;
        }
    }
    
    /**
     * 여러 색상 테마 중 하나라도 매칭되는지 확인
     */
    private boolean matchesAnyColorTheme(Part part, List<String> colorThemes) {
        for (String colorTheme : colorThemes) {
            if (matchesColorTheme(part, colorTheme)) {
                return true;
            }
        }
        return false;
    }
    
    /**
     * 재질 매칭 확인
     */
    private boolean matchesMaterial(Part part, String material) {
        if (part == null || part.getName() == null) {
            return false;
        }
        try {
            String name = part.getName().toLowerCase();
            String materialLower = material.toLowerCase();
            
            if (materialLower.contains("철제") || materialLower.contains("스틸") || 
                materialLower.contains("steel")) {
                return name.contains("스틸") || name.contains("steel") ||
                       name.contains("철제") || name.contains("metal");
            } else if (materialLower.contains("알루미늄") || materialLower.contains("aluminum")) {
                return name.contains("알루미늄") || name.contains("aluminum") ||
                       name.contains("알미늄");
            } else if (materialLower.contains("플라스틱") || materialLower.contains("plastic")) {
                return name.contains("플라스틱") || name.contains("plastic");
            }
            
            return false;
        } catch (Exception e) {
            return false;
        }
    }
    
    /**
     * 노트북용 RAM 여부 확인
     */
    private boolean isNotebookRam(Part part) {
        if (part == null || part.getName() == null) {
            return false;
        }
        String name = part.getName().toLowerCase();
        
        // 제품명에서 노트북 키워드 확인
        if (name.contains("노트북") || name.contains("notebook") || name.contains("laptop")) {
            return true;
        }
        
        // 스펙에서도 확인
        try {
            if (part.getPartSpec() != null && part.getPartSpec().getSpecs() != null) {
                JSONObject specs = new JSONObject(part.getPartSpec().getSpecs());
                String deviceType = specs.optString("device_type", "").toLowerCase();
                String productClass = specs.optString("product_class", "").toLowerCase();
                
                if (deviceType.contains("노트북") || deviceType.contains("notebook") || 
                    deviceType.contains("laptop") || productClass.contains("노트북")) {
                    return true;
                }
            }
        } catch (Exception e) {
            // 스펙 파싱 실패 시 무시
        }
        
        return false;
    }
    
    /**
     * 외장 하드 케이스 여부 확인 (PC 케이스가 아닌 외장 하드 케이스 제외)
     */
    private boolean isExternalCase(Part part) {
        if (part == null || part.getName() == null) {
            return false;
        }
        String name = part.getName().toLowerCase();
        
        // 외장 하드, HDD 케이스, 외장케이스 키워드가 있으면 제외
        if (name.contains("외장") && (name.contains("하드") || name.contains("hdd"))) {
            return true;
        }
        if (name.contains("hdd") && name.contains("케이스") && !name.contains("pc")) {
            return true;
        }
        
        // 스펙에서도 확인
        try {
            if (part.getPartSpec() != null && part.getPartSpec().getSpecs() != null) {
                JSONObject specs = new JSONObject(part.getPartSpec().getSpecs());
                String productClass = specs.optString("product_class", "").toLowerCase();
                
                if (productClass.contains("외장") || productClass.contains("hdd케이스")) {
                    return true;
                }
            }
        } catch (Exception e) {
            // 스펙 파싱 실패 시 무시
        }
        
        return false;
    }
    
    /**
     * 국내 AS 여부 확인
     */
    private boolean hasDomesticAS(Part part) {
        if (part.getWarrantyInfo() == null) {
            return false;
        }
        String warranty = part.getWarrantyInfo().toLowerCase();
        String manufacturer = part.getManufacturer() != null ? 
            part.getManufacturer().toLowerCase() : "";
        
        // 국내 브랜드 확인
        if (manufacturer.contains("삼성") || manufacturer.contains("lg") ||
            manufacturer.contains("한화") || manufacturer.contains("하이닉스")) {
            return true;
        }
        
        // 보증 정보에서 국내 AS 키워드 확인
        return warranty.contains("국내") || warranty.contains("한국") ||
               warranty.contains("domestic") || warranty.contains("korea");
    }
    
    /**
     * 내구성 점수 계산 (별점, 리뷰 수, 보증 기간 등 기반)
     */
    private int getDurabilityScore(Part part) {
        int score = 0;
        
        // 별점 기반 (5점 만점)
        if (part.getStarRating() != null) {
            score += (int)(part.getStarRating() * 10);
        }
        
        // 리뷰 수 기반 (많을수록 신뢰도 높음)
        if (part.getReviewCount() != null && part.getReviewCount() > 0) {
            score += Math.min(part.getReviewCount() / 10, 20); // 최대 20점
        }
        
        // 보증 기간 기반
        if (part.getWarrantyInfo() != null) {
            String warranty = part.getWarrantyInfo().toLowerCase();
            if (warranty.contains("5년") || warranty.contains("5 year")) {
                score += 15;
            } else if (warranty.contains("3년") || warranty.contains("3 year")) {
                score += 10;
            } else if (warranty.contains("2년") || warranty.contains("2 year")) {
                score += 5;
            }
        }
        
        return score;
    }
    
    /**
     * 확장성 점수 계산 (메인보드의 경우)
     */
    private int getExpandabilityScore(Part part) {
        if (part.getPartSpec() == null || part.getPartSpec().getSpecs() == null) {
            return 0;
        }
        try {
            JSONObject specs = new JSONObject(part.getPartSpec().getSpecs());
            int score = 0;
            
            // PCIe 슬롯 수
            String pcieSlots = specs.optString("pcie_slots", "");
            if (pcieSlots.contains("3") || pcieSlots.contains("4")) {
                score += 10;
            }
            
            // RAM 슬롯 수
            String ramSlots = specs.optString("ram_slots", "");
            if (ramSlots.contains("4")) {
                score += 10;
            }
            
            // M.2 슬롯 수
            String m2Slots = specs.optString("m2_slots", "");
            if (m2Slots.contains("2") || m2Slots.contains("3")) {
                score += 10;
            }
            
            // SATA 포트 수
            String sataPorts = specs.optString("sata_ports", "");
            if (sataPorts.contains("6") || sataPorts.contains("8")) {
                score += 5;
            }
            
            return score;
        } catch (Exception e) {
            return 0;
        }
    }
    
    /**
     * 호환성 문제 해결
     */
    /**
     * Map에서 String 값을 안전하게 가져오는 헬퍼 메서드
     */
    private String getStringValue(Map<String, Object> map, String key, String defaultValue) {
        if (map == null || !map.containsKey(key)) {
            return defaultValue;
        }
        Object value = map.get(key);
        if (value == null) {
            return defaultValue;
        }
        return value.toString();
    }
    
    private Map<String, Part> resolveCompatibilityIssues(
            Map<String, Part> currentParts,
            Map<String, Integer> budgetAllocation,
            BuildRequestDto request) {
        
        // 간단한 전략: CPU-메인보드 소켓이 안 맞으면 메인보드 교체
        // 실제로는 더 복잡한 로직 필요
        
        Map<String, Part> resolvedParts = new HashMap<>(currentParts);
        
        // 예: 메인보드 재선택
        if (resolvedParts.containsKey("메인보드")) {
            int budget = budgetAllocation.getOrDefault("메인보드", 100000);
            Part alternativeBoard = findBestPartInBudget("메인보드", budget, request.getPreferences());
            if (alternativeBoard != null) {
                resolvedParts.put("메인보드", alternativeBoard);
            }
        }
        
        return resolvedParts;
    }
    
    /**
     * 업그레이드 옵션 생성
     */
    private List<BuildRecommendationDto.UpgradeOption> generateUpgradeOptions(
            Map<String, Part> selectedParts,
            int totalBudget,
            int currentTotalPrice) {
        
        List<BuildRecommendationDto.UpgradeOption> options = new ArrayList<>();
        int remainingBudget = totalBudget - currentTotalPrice;
        
        if (remainingBudget < 50000) {
            return options; // 여유 예산 부족
        }
        
        // CPU 업그레이드 옵션
        if (selectedParts.containsKey("CPU")) {
            Part currentCpu = selectedParts.get("CPU");
            List<Part> betterCpus = partRepository.findAll(
                (root, query, cb) -> cb.and(
                    cb.equal(root.get("category"), "CPU"),
                    cb.greaterThan(root.get("price"), currentCpu.getPrice()),
                    cb.le(root.get("price"), currentCpu.getPrice() + remainingBudget)
                ),
                PageRequest.of(0, 3, Sort.by(Sort.Direction.DESC, "starRating"))
            ).getContent();
            
            for (Part betterCpu : betterCpus) {
                options.add(BuildRecommendationDto.UpgradeOption.builder()
                    .category("CPU")
                    .part(PartResponseDto.fromEntity(betterCpu))
                    .additionalCost(betterCpu.getPrice() - currentCpu.getPrice())
                    .benefit("더 높은 성능과 멀티태스킹 능력")
                    .build());
            }
        }
        
        return options;
    }
    
    /**
     * AI 설명 생성 (Gemini API 사용)
     */
    private String generateAIExplanation(
            Map<String, Part> selectedParts,
            BuildRequestDto request,
            int totalPrice,
            CompatibilityResult compatibilityCheck) {
        
        // 벤치마크와 리뷰를 로드하기 위해 Part를 다시 조회 (MultipleBagFetchException 방지)
        Map<String, Part> partsWithData = new HashMap<>();
        for (Map.Entry<String, Part> entry : selectedParts.entrySet()) {
            Part part = entry.getValue();
            // 벤치마크와 리뷰를 별도 쿼리로 로드 (MultipleBagFetchException 방지)
            Part partWithBenchmarks = partRepository.findByIdWithBenchmarks(part.getId())
                .orElse(part);
            Part partWithReviews = partRepository.findByIdWithReviews(part.getId())
                .orElse(part);
            
            // 벤치마크와 리뷰를 하나의 Part 객체에 합치기
            // partWithReviews를 기본으로 사용하고, 벤치마크만 추가
            // 벤치마크 리스트는 이미 초기화되어 있으므로 clear() 후 addAll() 사용
            if (partWithBenchmarks.getBenchmarkResults() != null && 
                !partWithBenchmarks.getBenchmarkResults().isEmpty()) {
                partWithReviews.getBenchmarkResults().clear();
                partWithReviews.getBenchmarkResults().addAll(partWithBenchmarks.getBenchmarkResults());
            }
            
            partsWithData.put(entry.getKey(), partWithReviews);
        }
        
        // Gemini API 호출을 위한 프롬프트 구성
        StringBuilder prompt = new StringBuilder();
        prompt.append("# 페르소나\n");
        prompt.append("당신은 10년 경력의 PC 견적 전문가 '다오나'입니다.\n\n");
        
        prompt.append("# 컨텍스트\n");
        prompt.append(String.format("- 사용자 예산: %,d원\n", request.getBudget()));
        prompt.append(String.format("- 용도: %s\n", request.getPurpose()));
        prompt.append(String.format("- 실제 견적 금액: %,d원 (예산 대비 %.1f%%)\n\n", 
            totalPrice, (totalPrice * 100.0 / request.getBudget())));
        
        prompt.append("# 선택된 부품\n");
        for (Map.Entry<String, Part> entry : partsWithData.entrySet()) {
            Part part = entry.getValue();
            String specs = getPartKeySpecs(part);
            
            // 벤치마크 정보 수집
            StringBuilder benchmarkInfo = new StringBuilder();
            if (part.getBenchmarkResults() != null && !part.getBenchmarkResults().isEmpty()) {
                // 주요 벤치마크만 선택 (CPU: Cinebench, GPU: 3DMark 등)
                part.getBenchmarkResults().stream()
                    .filter(b -> {
                        String testName = b.getTestName().toLowerCase();
                        return testName.contains("cinebench") || testName.contains("geekbench") || 
                               testName.contains("3dmark") || testName.contains("blender");
                    })
                    .limit(3) // 최대 3개만
                    .forEach(b -> {
                        benchmarkInfo.append(String.format("%s %s: %.0f%s, ", 
                            b.getTestName(), 
                            b.getScenario() != null && !b.getScenario().isEmpty() ? b.getScenario() : "",
                            b.getValue(),
                            b.getUnit() != null ? b.getUnit() : ""));
                    });
            }
            
            // 리뷰 요약 정보 수집
            StringBuilder reviewInfo = new StringBuilder();
            if (part.getCommunityReviews() != null && !part.getCommunityReviews().isEmpty()) {
                part.getCommunityReviews().stream()
                    .filter(r -> r.getAiSummary() != null && !r.getAiSummary().isEmpty())
                    .limit(1) // 첫 번째 리뷰 요약만
                    .forEach(r -> {
                        String summary = r.getAiSummary();
                        // 요약이 너무 길면 자르기
                        if (summary.length() > 200) {
                            summary = summary.substring(0, 200) + "...";
                        }
                        reviewInfo.append(summary);
                    });
            }
            
            prompt.append(String.format("- %s: %s (%,d원, 평점: %.1f/5.0, %s)\n",
                entry.getKey(), part.getName(), part.getPrice(), 
                part.getStarRating() != null ? part.getStarRating() : 0.0,
                specs));
            
            // 벤치마크 정보 추가
            if (benchmarkInfo.length() > 0) {
                String benchStr = benchmarkInfo.toString().trim();
                if (benchStr.endsWith(",")) {
                    benchStr = benchStr.substring(0, benchStr.length() - 1);
                }
                prompt.append(String.format("  → 벤치마크: %s\n", benchStr));
            }
            
            // 리뷰 요약 추가
            if (reviewInfo.length() > 0) {
                prompt.append(String.format("  → 리뷰 요약: %s\n", reviewInfo.toString()));
            }
        }
        prompt.append("\n");
        
        prompt.append("# 호환성 검사 결과\n");
        prompt.append(compatibilityCheck.getSummary()).append("\n\n");
        
        prompt.append("# 지시사항\n");
        prompt.append("1. 각 부품 선택 이유를 용도에 맞게 설명해주세요. 벤치마크 수치와 리뷰 요약을 참고하여 구체적으로 설명해주세요.\n");
        prompt.append("2. 예산 대비 가성비를 평가해주세요. 벤치마크 성능 대비 가격을 고려하여 평가해주세요.\n");
        prompt.append("3. 호환성 문제가 있다면 주의사항을 알려주세요.\n");
        prompt.append("4. 이 견적의 성능 수준을 벤치마크 데이터를 바탕으로 간단히 평가해주세요.\n");
        prompt.append("5. 리뷰 요약에서 언급된 장점이나 단점이 있다면 자연스럽게 언급해주세요.\n");
        prompt.append("6. 총 5-8문장으로 친근하고 전문적으로 설명해주세요.\n\n");
        
        prompt.append("# 출력 형식\n");
        prompt.append("간단한 텍스트 설명 (JSON 없이 자연스러운 문장으로)\n");
        
        try {
            // Gemini API 호출 (ChatService의 메서드 재사용)
            String aiExplanation = chatService.generateBuildExplanation(prompt.toString());
            if (aiExplanation != null && !aiExplanation.isEmpty()) {
                return aiExplanation;
            }
        } catch (Exception e) {
            log.error("AI 설명 생성 실패", e);
        }
        
        // 폴백: 기본 설명 반환
        return String.format(
            "%s 용도로 최적화된 견적입니다. 총 %,d원으로 예산 내에서 구성되었습니다. " +
            "선택된 부품들은 모두 높은 평점과 리뷰를 받은 제품들입니다. " +
            "호환성 검사 결과: %s",
            request.getPurpose(), totalPrice, compatibilityCheck.getSummary()
        );
    }
    
    /**
     * 부품의 핵심 스펙 추출
     */
    private String getPartKeySpecs(Part part) {
        if (part.getPartSpec() == null || part.getPartSpec().getSpecs() == null) {
            return "스펙 정보 없음";
        }
        
        try {
            org.json.JSONObject specs = new org.json.JSONObject(part.getPartSpec().getSpecs());
            StringBuilder keySpecs = new StringBuilder();
            
            // 카테고리별 주요 스펙 추출
            switch (part.getCategory()) {
                case "CPU":
                    keySpecs.append(specs.optString("cores", "")).append("코어 ");
                    keySpecs.append(specs.optString("base_clock", "")).append(" ");
                    keySpecs.append(specs.optString("socket", ""));
                    break;
                case "그래픽카드":
                    keySpecs.append(specs.optString("chipset_maker", "")).append(" ");
                    keySpecs.append(specs.optString("memory_capacity", "")).append(" ");
                    keySpecs.append(specs.optString("memory_type", ""));
                    break;
                case "RAM":
                    keySpecs.append(specs.optString("memory_capacity", "")).append(" ");
                    keySpecs.append(specs.optString("memory_standard", ""));
                    break;
                case "SSD":
                case "HDD":
                    keySpecs.append(specs.optString("storage_capacity", "")).append(" ");
                    keySpecs.append(specs.optString("interface", ""));
                    break;
                case "파워":
                    keySpecs.append(specs.optString("rated_output", "")).append(" ");
                    keySpecs.append(specs.optString("certification_80plus", ""));
                    break;
                case "메인보드":
                    keySpecs.append(specs.optString("socket", "")).append(" ");
                    keySpecs.append(specs.optString("chipset", "")).append(" ");
                    keySpecs.append(specs.optString("board_form_factor", ""));
                    break;
                default:
                    keySpecs.append(specs.optString("product_class", ""));
            }
            
            String result = keySpecs.toString().trim();
            return result.isEmpty() ? "스펙 정보 없음" : result;
        } catch (Exception e) {
            return "스펙 정보 없음";
        }
    }
    
}

