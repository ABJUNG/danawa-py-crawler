package com.danawa.webservice.service;

import com.danawa.webservice.domain.Part;
import com.danawa.webservice.domain.PartSpec;
import com.danawa.webservice.dto.PartResponseDto;
import com.danawa.webservice.repository.PartRepository;
import com.danawa.webservice.repository.PartSpecRepository;
import jakarta.persistence.EntityManager;
import jakarta.persistence.PersistenceContext;
import jakarta.persistence.criteria.Predicate;
import jakarta.persistence.criteria.JoinType; // --- 1. (추가) JoinType import ---
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.json.JSONObject;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageImpl;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.domain.Specification;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.util.MultiValueMap;

import java.util.*;
import java.util.Collections;
import java.util.stream.Collectors;

@Slf4j
@Service
@Transactional(readOnly = true)
@RequiredArgsConstructor
public class PartService {

    private final PartRepository partRepository;
    private final PartSpecRepository partSpecRepository;
    
    @PersistenceContext
    private final EntityManager em;

    // (필터 순서 정의 - 기존과 동일)
    private static final Map<String, List<String>> FILTERABLE_COLUMNS = Map.of(
            "CPU", List.of("manufacturer", "socket", "cores", "threads", "cpu_series", "codename", "integrated_graphics"),
            "쿨러", List.of("manufacturer", "product_type", "cooling_method", "air_cooling_form", "fan_size", "radiator_length"),
            "메인보드", List.of("manufacturer", "socket", "chipset", "form_factor", "memory_spec"),
            "RAM", List.of("manufacturer", "product_class", "capacity", "clock_speed", "ram_timing"),
            "그래픽카드", List.of("manufacturer", "nvidia_chipset", "amd_chipset", "gpu_memory_capacity", "gpu_length"),
            "SSD", List.of("manufacturer", "form_factor", "ssd_interface", "capacity", "sequential_read"),
            "HDD", List.of("manufacturer", "disk_capacity", "rotation_speed", "buffer_capacity"),
            "케이스", List.of("manufacturer", "case_size", "supported_board", "cpu_cooler_height_limit", "vga_length"),
            "파워", List.of("manufacturer", "rated_output", "eighty_plus_cert", "cable_connection")
    );

    /**
     * [수정됨] JSON 스펙을 파싱하여 동적 필터 목록을 생성합니다.
     */
    public Map<String, Set<String>> getAvailableFiltersForCategory(String category) {
        Map<String, Set<String>> availableFilters = new HashMap<>();
        List<String> columns = FILTERABLE_COLUMNS.get(category);
        if (columns == null) {
            return availableFilters;
        }

        // 1. 해당 카테고리의 모든 PartSpec을 조회 (Part 엔티티와 함께 Fetch Join)
        List<PartSpec> specsForCategory = partSpecRepository.findAllWithPartByCategory(category);

        if (specsForCategory.isEmpty()) {
            return availableFilters; // 스펙 정보가 없으면 빈 맵 반환
        }

        // 2. 각 스펙(JSON)을 파싱하여 필터 목록을 동적으로 생성
        for (String columnKey : columns) {
            Set<String> values = new HashSet<>();
            for (PartSpec partSpec : specsForCategory) {
                try {
                    if (partSpec.getSpecs() != null) {
                        JSONObject specsJson = new JSONObject(partSpec.getSpecs());

                        // 3. JSON에서 키(columnKey)로 값을 찾음
                        if (specsJson.has(columnKey) && specsJson.get(columnKey) != null) {
                            String value = specsJson.getString(columnKey);
                            if (value != null && !value.isBlank()) {
                                values.add(value);
                            }
                        }
                    }
                } catch (Exception e) {
                    // JSON 파싱 오류 등 무시
                }
            }
            if (!values.isEmpty()) {
                // 4. 맵의 키는 App.js가 사용하는 키 (columnKey)
                availableFilters.put(columnKey, values);
            }
        }
        
        return availableFilters;
    }

    // (기존 getHeightRanges 함수는 JSON으로 대체되었으므로 삭제 또는 주석 처리)


    /**
     * [수정됨] Part 엔티티가 아닌 DTO를 반환합니다.
     * JSON 스펙 필터링 지원 추가
     */
    public Page<PartResponseDto> findByFilters(MultiValueMap<String, String> filters, Pageable pageable) {
        String category = filters.getFirst("category");
        System.out.println("=== findByFilters 호출 ===");
        System.out.println("카테고리: " + category);
        
        Specification<Part> spec = createSpecification(filters);
        Page<Part> partPage = partRepository.findAll(spec, pageable);
        
        System.out.println("조회된 상품 수 (totalElements): " + partPage.getTotalElements());
        System.out.println("조회된 상품 목록 크기 (content.size): " + partPage.getContent().size());
        System.out.println("총 페이지 수: " + partPage.getTotalPages());
        
        // JSON 필터가 있는지 확인
        Set<String> excludedKeys = Set.of("category", "keyword", "manufacturer", "page", "size", "sort");
        boolean hasJsonFilters = filters.entrySet().stream()
            .anyMatch(entry -> !excludedKeys.contains(entry.getKey()) && 
                             entry.getValue() != null && 
                             !entry.getValue().isEmpty() && 
                             !entry.getValue().get(0).isEmpty());
        
        Page<Part> filteredPage;
        if (hasJsonFilters) {
            // JSON 필터링이 필요한 경우, 전체 데이터를 조회하여 필터링 후 페이징 적용
            // 성능을 위해 큰 사이즈로 조회 (최대 10000개)
            Pageable largePageable = org.springframework.data.domain.PageRequest.of(0, 10000, pageable.getSort());
            Page<Part> allPartsPage = partRepository.findAll(spec, largePageable);
            
            // 전체 데이터 필터링
            List<Part> allFilteredParts = allPartsPage.getContent().stream()
                .filter(part -> matchesJsonFilters(part, filters))
                .collect(Collectors.toList());
            
            System.out.println("전체 JSON 필터링 후 상품 수: " + allFilteredParts.size());
            
            // 필터링된 결과에 페이징 적용
            int start = (int) pageable.getOffset();
            int end = Math.min((start + pageable.getPageSize()), allFilteredParts.size());
            List<Part> pagedFilteredParts = start < allFilteredParts.size() 
                ? allFilteredParts.subList(start, end)
                : Collections.emptyList();
            
            filteredPage = new PageImpl<>(
                pagedFilteredParts,
                pageable,
                allFilteredParts.size()
            );
        } else {
            // JSON 필터가 없으면 필터링 없이 그대로 반환
            filteredPage = partPage;
        }
        
        // Page<Part>를 Page<PartResponseDto>로 변환하여 반환
        return filteredPage.map(PartResponseDto::new);
    }
    
    /**
     * JSON 스펙 필터링 검사
     */
    private boolean matchesJsonFilters(Part part, MultiValueMap<String, String> filters) {
        // category, keyword, manufacturer, page, size, sort는 이미 처리되었거나 페이징/정렬용이므로 제외
        // manufacturer는 SQL에서 직접 필터링되므로 JSON 필터링에서 제외
        Set<String> excludedKeys = Set.of("category", "keyword", "manufacturer", "page", "size", "sort");
        
        // 필터링할 실제 필터 키가 있는지 확인
        boolean hasJsonFilters = false;
        for (Map.Entry<String, List<String>> entry : filters.entrySet()) {
            String key = entry.getKey();
            List<String> values = entry.getValue();
            
            if (!excludedKeys.contains(key) && 
                values != null && !values.isEmpty() && !values.get(0).isEmpty()) {
                hasJsonFilters = true;
                break;
            }
        }
        
        // JSON 필터가 없으면 모든 상품 통과
        if (!hasJsonFilters) {
            return true;
        }
        
        // PartSpec이 없으면 필터링에서 제외하지 않고 통과 (필터가 없을 때와 동일하게 처리)
        if (part.getPartSpec() == null || part.getPartSpec().getSpecs() == null) {
            log.warn("Part ID {} has no PartSpec, skipping JSON filter check", part.getId());
            return true; // PartSpec이 없어도 통과 (데이터가 없을 수 있으므로)
        }
        
        for (Map.Entry<String, List<String>> entry : filters.entrySet()) {
            String key = entry.getKey();
            List<String> values = entry.getValue();
            
            if (excludedKeys.contains(key) || 
                values == null || values.isEmpty() || values.get(0).isEmpty()) {
                continue;
            }
            
            // JSON 스펙 필터링
            try {
                JSONObject specsJson = new JSONObject(part.getPartSpec().getSpecs());
                
                // JSON에서 해당 키의 값 확인
                if (specsJson.has(key)) {
                    Object jsonValue = specsJson.get(key);
                    String jsonValueStr = jsonValue != null ? jsonValue.toString() : "";
                    
                    // 필터 값과 일치하는지 확인 (대소문자 무시)
                    boolean matches = values.stream()
                        .anyMatch(filterValue -> jsonValueStr.equalsIgnoreCase(filterValue) ||
                                jsonValueStr.contains(filterValue) ||
                                filterValue.contains(jsonValueStr));
                    
                    if (!matches) {
                        return false; // 하나라도 일치하지 않으면 제외
                    }
                } else {
                    // JSON에 해당 키가 없으면 필터링에서 제외하지 않고 통과
                    // (스펙 정보가 없을 수 있으므로 엄격하게 필터링하지 않음)
                    log.debug("Part ID {} JSON does not have key '{}', allowing through", part.getId(), key);
                    continue;
                }
            } catch (Exception e) {
                // JSON 파싱 실패 시 로그만 남기고 통과 (데이터 문제일 수 있으므로)
                log.warn("Failed to parse JSON for Part ID {}: {}", part.getId(), e.getMessage());
                continue;
            }
        }
        
        return true;
    }

    /**
     * [수정됨] Part 엔티티가 아닌 DTO를 반환합니다.
     */
    public List<PartResponseDto> findByIds(List<Long> ids) {
        List<Part> parts = partRepository.findAllById(ids);
        
        // List<Part>를 List<PartResponseDto>로 변환하여 반환
        // (N+1 문제 경고)
        return parts.stream()
                    .map(PartResponseDto::new) // 람다를 메서드 레퍼런스로 변경
                    .collect(Collectors.toList());
    }

    /**
     * [수정됨] JSON 스펙 필터링 로직이 비활성화되었습니다.
     * (현재 'category'와 'keyword' 필터만 작동합니다.)
     */
    private Specification<Part> createSpecification(MultiValueMap<String, String> filters) {
        return (root, query, cb) -> {
            Predicate predicate = cb.conjunction();
            
            // 디버깅: 필터 키 확인
            log.debug("createSpecification - 필터 키들: {}", filters.keySet());
            
            // (1단계에서 삭제한 스펙 필드 필터링 로직은 비활성화 상태 유지)
            // List<String> allFilterKeys = new ArrayList<>();
            // FILTERABLE_COLUMNS.values().forEach(allFilterKeys::addAll);

            for (Map.Entry<String, List<String>> entry : filters.entrySet()) {
                String key = entry.getKey();
                List<String> values = entry.getValue();
                
                log.debug("createSpecification - 처리 중인 키: {}, 값: {}", key, values);
                
                if (values == null || values.isEmpty() || values.get(0).isEmpty()) {
                    log.debug("createSpecification - 키 '{}'의 값이 비어있어 건너뜀", key);
                    continue;
                }

                if (key.equals("category")) {
                    // category 필터 적용
                    log.debug("createSpecification - category 필터 적용: {}", values);
                    predicate = cb.and(predicate, root.get("category").in(values));
                } else if (key.equals("keyword")) {
                    // keyword 필터 적용
                    log.debug("createSpecification - keyword 필터 적용: {}", values.get(0));
                    predicate = cb.and(predicate, cb.like(root.get("name"), "%" + values.get(0) + "%"));
                } else if (key.equals("manufacturer")) {
                    // manufacturer 필터 적용 (일반 컬럼이므로 SQL에서 직접 필터링)
                    log.debug("createSpecification - manufacturer 필터 적용: {}", values);
                    predicate = cb.and(predicate, root.get("manufacturer").in(values));
                } else {
                    // 기타 필터는 무시 (JSON 필터링은 나중에 matchesJsonFilters에서 처리)
                    log.debug("createSpecification - 키 '{}'는 SQL 필터링에서 무시됨 (JSON 필터링으로 처리)", key);
                }
                
                // (1단계에서 주석 처리한 JSON 스펙 필터링 로직)
                // TODO: 'key'가 'cores', 'socket' 등 스펙 필드일 경우, 
                // PartSpec 테이블의 'specs' JSON 컬럼을 검색하는 로직 (Native Query 또는 H2 JSON 함수) 추가 필요
                /*
                else if (key.equals("coolerHeight")) { ... } 
                else if (allFilterKeys.contains(key)) { ... }
                */
            }

            // --- 2. (추가) 상세 스펙을 함께 조회하도록 Fetch Join 추가 ---
            // N+1 문제를 방지하고 DTO가 PartSpec에 접근할 수 있도록 Eager Fetching을 강제합니다.
            // (주의: count 쿼리에서는 fetch join을 하면 안 되므로, 실제 쿼리일 때만 적용)
            if (query.getResultType() != Long.class && query.getResultType() != long.class) {
                root.fetch("partSpec", JoinType.LEFT);
            }
            // --- 2. (추가 완료) ---

            log.debug("createSpecification - 최종 predicate 생성 완료");
            return predicate;
        };
    }

    /**
     * 특정 카테고리의 고유한 모델명 목록을 반환합니다.
     * 예: GPU 카테고리의 경우 "RTX 4060", "RTX 4070" 등
     */
    public Set<String> getUniqueModelsForCategory(String category) {
        List<PartSpec> specs = partSpecRepository.findAllWithPartByCategory(category);
        Set<String> models = new HashSet<>();
        
        for (PartSpec spec : specs) {
            try {
                if (spec.getSpecs() != null) {
                    JSONObject specsJson = new JSONObject(spec.getSpecs());
                    
                    // 카테고리별로 모델명을 추출하는 키가 다를 수 있음
                    String modelKey = switch (category) {
                        case "CPU" -> "codename";
                        case "그래픽카드" -> "nvidia_chipset"; // 또는 amd_chipset
                        case "메인보드" -> "chipset";
                        case "RAM" -> "product_class";
                        default -> "model"; // 기본값
                    };
                    
                    if (specsJson.has(modelKey)) {
                        String model = specsJson.getString(modelKey);
                        if (model != null && !model.isBlank()) {
                            models.add(model);
                        }
                    }
                    
                    // GPU의 경우 AMD 칩셋도 확인
                    if (category.equals("그래픽카드") && specsJson.has("amd_chipset")) {
                        String amdModel = specsJson.getString("amd_chipset");
                        if (amdModel != null && !amdModel.isBlank()) {
                            models.add(amdModel);
                        }
                    }
                }
            } catch (Exception e) {
                // JSON 파싱 오류 무시
            }
        }
        
        return models;
    }

    /**
     * 특정 카테고리의 고유한 브랜드(제조사) 목록을 반환합니다.
     */
    public Set<String> getUniqueBrandsForCategory(String category) {
        List<PartSpec> specs = partSpecRepository.findAllWithPartByCategory(category);
        Set<String> brands = new HashSet<>();
        
        for (PartSpec spec : specs) {
            try {
                if (spec.getSpecs() != null) {
                    JSONObject specsJson = new JSONObject(spec.getSpecs());
                    
                    if (specsJson.has("manufacturer")) {
                        String brand = specsJson.getString("manufacturer");
                        if (brand != null && !brand.isBlank()) {
                            brands.add(brand);
                        }
                    }
                }
            } catch (Exception e) {
                // JSON 파싱 오류 무시
            }
        }
        
        return brands;
    }

    /**
     * 특정 카테고리의 가격 범위를 반환합니다.
     * min: 최소 가격, max: 최대 가격, avg: 평균 가격
     */
    public Map<String, Integer> getPriceRangeForCategory(String category) {
        List<Part> parts = partRepository.findAllByCategory(category);
        
        if (parts.isEmpty()) {
            return Map.of("min", 0, "max", 0, "avg", 0);
        }
        
        int min = parts.stream()
                .mapToInt(Part::getPrice)
                .min()
                .orElse(0);
        
        int max = parts.stream()
                .mapToInt(Part::getPrice)
                .max()
                .orElse(0);
        
        int avg = (int) parts.stream()
                .mapToInt(Part::getPrice)
                .average()
                .orElse(0);
        
        return Map.of("min", min, "max", max, "avg", avg);
    }
    
    /**
     * AI 추천 점수가 포함된 부품 목록을 반환합니다.
     * 사용 목적과 예산에 맞춰 AI 점수를 계산합니다.
     */
    public Page<PartResponseDto> findByFiltersWithAIScore(
            MultiValueMap<String, String> filters, 
            String purpose, 
            Integer budget, 
            Pageable pageable) {
        // 기본 필터링
        Specification<Part> spec = createSpecification(filters);
        Page<Part> partPage = partRepository.findAll(spec, pageable);
        
        // 카테고리 추출
        String category = filters.getFirst("category");
        
        // AI 점수 계산 및 DTO 변환
        return partPage.map(part -> {
            PartResponseDto dto = new PartResponseDto(part);
            // AI 점수 계산
            double aiScore = calculateAIScore(part, category, purpose, budget);
            dto.setAiScore(aiScore);
            return dto;
        });
    }
    
    /**
     * AI 추천 점수 계산
     * 사용 목적, 예산, 벤치마크, 리뷰 등을 종합적으로 고려합니다.
     */
    private double calculateAIScore(Part part, String category, String purpose, Integer budget) {
        double score = 50.0; // 기본 점수
        
        // 1. 별점 (최대 20점)
        if (part.getStarRating() != null) {
            score += part.getStarRating() * 4.0;
        }
        
        // 2. 리뷰 수 (최대 10점)
        if (part.getReviewCount() != null) {
            score += Math.min(part.getReviewCount() / 20.0, 10.0);
        }
        
        // 3. 가격 대비 가성비 (최대 15점)
        if (budget != null && budget > 0 && category != null) {
            Map<String, Integer> priceRange = getPriceRangeForCategory(category);
            int avgPrice = priceRange.get("avg");
            int minPrice = priceRange.get("min");
            int maxPrice = priceRange.get("max");
            
            if (avgPrice > 0) {
                // 사용 목적에 따른 가격 점수 계산
                double priceScore = calculatePriceScore(
                    part.getPrice(), 
                    avgPrice, 
                    minPrice, 
                    maxPrice, 
                    purpose, 
                    budget
                );
                score += priceScore;
            }
        }
        
        // 4. 사용 목적에 따른 가중치 (최대 10점)
        score += calculatePurposeScore(part, category, purpose);
        
        // 5. 벤치마크 존재 여부 (5점)
        if (part.getBenchmarkResults() != null && !part.getBenchmarkResults().isEmpty()) {
            score += 5.0;
        }
        
        // 6. 리뷰 요약 존재 여부 (5점)
        if (part.getCommunityReviews() != null && 
            part.getCommunityReviews().stream()
                .anyMatch(r -> r.getAiSummary() != null && !r.getAiSummary().isEmpty())) {
            score += 5.0;
        }
        
        return Math.min(Math.round(score), 100.0);
    }
    
    /**
     * 가격 점수 계산 (최대 15점)
     */
    private double calculatePriceScore(
            int price, 
            int avgPrice, 
            int minPrice, 
            int maxPrice, 
            String purpose, 
            int budget) {
        
        // 예산 대비 가격 비율
        double priceRatio = (double) price / budget;
        
        // 사용 목적에 따른 최적 가격 범위
        if ("게이밍".equals(purpose) || "영상편집".equals(purpose)) {
            // 게이밍이나 영상편집은 중상위권 가격대 선호
            if (priceRatio >= 0.7 && priceRatio <= 1.0) {
                return 15.0; // 예산의 70~100% 사용 시 최고 점수
            } else if (priceRatio >= 0.5 && priceRatio < 0.7) {
                return 10.0;
            } else if (priceRatio > 1.0 && priceRatio <= 1.2) {
                return 12.0; // 약간 초과는 허용
            }
        } else if ("사무용".equals(purpose) || "인터넷".equals(purpose)) {
            // 사무용이나 인터넷은 가성비 중시
            if (priceRatio >= 0.4 && priceRatio <= 0.7) {
                return 15.0; // 예산의 40~70% 사용 시 최고 점수
            } else if (priceRatio >= 0.3 && priceRatio < 0.4) {
                return 12.0;
            } else if (priceRatio > 0.7 && priceRatio <= 0.9) {
                return 10.0;
            }
        } else {
            // 기본: 예산의 60~90% 사용 시 최적
            if (priceRatio >= 0.6 && priceRatio <= 0.9) {
                return 15.0;
            } else if (priceRatio >= 0.4 && priceRatio < 0.6) {
                return 10.0;
            } else if (priceRatio > 0.9 && priceRatio <= 1.1) {
                return 12.0;
            }
        }
        
        // 평균 가격 대비 위치
        double avgRatio = (double) price / avgPrice;
        if (avgRatio >= 0.8 && avgRatio <= 1.2) {
            return 8.0; // 평균 근처
        } else if (avgRatio < 0.8) {
            return 10.0; // 평균보다 저렴
        }
        
        return 5.0; // 기본 점수
    }
    
    /**
     * 사용 목적에 따른 카테고리별 가중치 점수 (최대 10점)
     */
    private double calculatePurposeScore(Part part, String category, String purpose) {
        if (purpose == null || category == null) {
            return 5.0; // 기본 점수
        }
        
        // 사용 목적별 중요 카테고리
        Map<String, List<String>> purposeWeights = Map.of(
            "게이밍", List.of("그래픽카드", "CPU", "RAM", "SSD"),
            "영상편집", List.of("CPU", "RAM", "그래픽카드", "SSD"),
            "사무용", List.of("CPU", "RAM", "SSD"),
            "인터넷", List.of("CPU", "RAM"),
            "프로그래밍", List.of("CPU", "RAM", "SSD")
        );
        
        List<String> importantCategories = purposeWeights.getOrDefault(purpose, List.of());
        
        if (importantCategories.isEmpty()) {
            return 5.0;
        }
        
        // 카테고리 중요도에 따른 점수
        int priority = importantCategories.indexOf(category);
        if (priority == 0) {
            return 10.0; // 최우선 카테고리
        } else if (priority == 1) {
            return 8.0;
        } else if (priority == 2) {
            return 6.0;
        } else if (priority == 3) {
            return 4.0;
        }
        
        return 3.0; // 덜 중요한 카테고리
    }
}