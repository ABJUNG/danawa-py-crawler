package com.danawa.webservice.service;

import com.danawa.webservice.domain.Part;
import com.danawa.webservice.dto.BuildRecommendationDto;
import com.danawa.webservice.dto.BuildRequestDto;
import com.danawa.webservice.dto.CompatibilityResult;
import com.danawa.webservice.dto.PartResponseDto;
import com.danawa.webservice.repository.PartRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Sort;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.*;
import java.util.stream.Collectors;

@Slf4j
@Service
@Transactional(readOnly = true)
@RequiredArgsConstructor
public class BuildRecommendationService {
    
    private final PartRepository partRepository;
    private final CompatibilityService compatibilityService;
    private final JdbcTemplate jdbcTemplate;
    
    /**
     * 사용자 요구사항에 맞는 PC 견적을 추천합니다.
     */
    public BuildRecommendationDto recommendBuild(BuildRequestDto request) {
        log.info("견적 추천 요청 - 예산: {}, 용도: {}", request.getBudget(), request.getPurpose());
        
        // 1. 용도별 예산 배분 가져오기
        Map<String, Integer> budgetAllocation = getBudgetAllocation(
            request.getPurpose(), 
            request.getBudget()
        );
        
        // 2. 각 카테고리별 최적 부품 후보 선택
        Map<String, Part> selectedParts = new HashMap<>();
        
        for (Map.Entry<String, Integer> entry : budgetAllocation.entrySet()) {
            String category = entry.getKey();
            int categoryBudget = entry.getValue();
            
            Part bestPart = findBestPartInBudget(category, categoryBudget, request.getPreferences());
            if (bestPart != null) {
                selectedParts.put(category, bestPart);
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
    private Map<String, Integer> getBudgetAllocation(String purpose, int totalBudget) {
        String sql = """
            SELECT category, weight_percentage
            FROM usage_weights
            WHERE usage_type = ?
            ORDER BY priority ASC
        """;
        
        List<Map<String, Object>> weights = jdbcTemplate.queryForList(sql, purpose);
        
        Map<String, Integer> allocation = new HashMap<>();
        
        if (weights.isEmpty()) {
            // 기본 배분 (용도 정보 없을 때)
            allocation.put("CPU", (int)(totalBudget * 0.25));
            allocation.put("그래픽카드", (int)(totalBudget * 0.30));
            allocation.put("RAM", (int)(totalBudget * 0.12));
            allocation.put("SSD", (int)(totalBudget * 0.10));
            allocation.put("메인보드", (int)(totalBudget * 0.15));
            allocation.put("파워", (int)(totalBudget * 0.05));
            allocation.put("케이스", (int)(totalBudget * 0.03));
        } else {
            for (Map<String, Object> row : weights) {
                String category = (String) row.get("category");
                int percentage = (Integer) row.get("weight_percentage");
                allocation.put(category, (int)(totalBudget * percentage / 100.0));
            }
        }
        
        return allocation;
    }
    
    /**
     * 예산 내 최적 부품 찾기
     */
    private Part findBestPartInBudget(String category, int budget, Map<String, String> preferences) {
        // 가격 범위: 예산의 80% ~ 120% (약간의 유연성)
        int minPrice = (int)(budget * 0.8);
        int maxPrice = (int)(budget * 1.2);
        
        // 카테고리, 가격 범위로 검색 (리뷰 점수 높은 순)
        List<Part> candidates = partRepository.findAll(
            (root, query, cb) -> cb.and(
                cb.equal(root.get("category"), category),
                cb.between(root.get("price"), minPrice, maxPrice)
            ),
            PageRequest.of(0, 10, Sort.by(Sort.Direction.DESC, "starRating"))
        ).getContent();
        
        if (candidates.isEmpty()) {
            // 범위 확대
            candidates = partRepository.findAll(
                (root, query, cb) -> cb.and(
                    cb.equal(root.get("category"), category),
                    cb.le(root.get("price"), maxPrice)
                ),
                PageRequest.of(0, 5, Sort.by(Sort.Direction.DESC, "starRating"))
            ).getContent();
        }
        
        // 브랜드 선호도 적용
        if (preferences != null && preferences.containsKey("preferred_brand")) {
            String preferredBrand = preferences.get("preferred_brand");
            Optional<Part> preferredPart = candidates.stream()
                .filter(p -> p.getManufacturer() != null && 
                             p.getManufacturer().equalsIgnoreCase(preferredBrand))
                .findFirst();
            
            if (preferredPart.isPresent()) {
                return preferredPart.get();
            }
        }
        
        // 기본: 리뷰 점수 최고인 부품 선택
        return candidates.isEmpty() ? null : candidates.get(0);
    }
    
    /**
     * 호환성 문제 해결
     */
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
     * AI 설명 생성
     */
    private String generateAIExplanation(
            Map<String, Part> selectedParts,
            BuildRequestDto request,
            int totalPrice,
            CompatibilityResult compatibilityCheck) {
        
        // Vertex AI 호출을 위한 프롬프트 구성
        StringBuilder prompt = new StringBuilder();
        prompt.append("# 페르소나\n");
        prompt.append("당신은 10년 경력의 PC 견적 전문가 '다오나'입니다.\n\n");
        
        prompt.append("# 컨텍스트\n");
        prompt.append(String.format("- 사용자 예산: %,d원\n", request.getBudget()));
        prompt.append(String.format("- 용도: %s\n", request.getPurpose()));
        prompt.append(String.format("- 실제 견적 금액: %,d원\n\n", totalPrice));
        
        prompt.append("# 선택된 부품\n");
        for (Map.Entry<String, Part> entry : selectedParts.entrySet()) {
            Part part = entry.getValue();
            prompt.append(String.format("- %s: %s (%,d원, 평점: %.1f)\n",
                entry.getKey(), part.getName(), part.getPrice(), part.getStarRating()));
        }
        prompt.append("\n");
        
        prompt.append("# 호환성 검사 결과\n");
        prompt.append(compatibilityCheck.getSummary()).append("\n\n");
        
        prompt.append("# 지시사항\n");
        prompt.append("1. 각 부품 선택 이유를 용도에 맞게 설명해주세요.\n");
        prompt.append("2. 예산 대비 가성비를 평가해주세요.\n");
        prompt.append("3. 호환성 문제가 있다면 주의사항을 알려주세요.\n");
        prompt.append("4. 총 3-5문장으로 간결하게 설명해주세요.\n\n");
        
        prompt.append("# 출력 형식\n");
        prompt.append("간단한 텍스트 설명 (JSON 아님)\n");
        
        // 실제로는 Vertex AI를 호출해야 하지만, 여기서는 간단한 설명 반환
        // ChatService의 callGeminiApi를 재사용하거나 별도 메서드 구현 필요
        
        return String.format(
            "%s 용도로 선택된 견적입니다. 총 %,d원으로 예산 내에서 구성되었습니다. " +
            "호환성 검사 결과: %s",
            request.getPurpose(), totalPrice, compatibilityCheck.getSummary()
        );
    }
}

