package com.danawa.webservice.controller;

import com.danawa.webservice.dto.BuildRecommendationDto;
import com.danawa.webservice.dto.BuildRequestDto;
import com.danawa.webservice.dto.CompatibilityResult;
import com.danawa.webservice.service.BuildRecommendationService;
import com.danawa.webservice.service.CompatibilityService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

@Slf4j
@RestController
@RequestMapping("/api/builds")
@RequiredArgsConstructor
@CrossOrigin(origins = "*", maxAge = 3600)  // CORS 설정
public class BuildController {
    
    private final BuildRecommendationService buildRecommendationService;
    private final CompatibilityService compatibilityService;
    
    /**
     * AI 기반 PC 견적 추천
     * POST /api/builds/recommend
     */
    @PostMapping("/recommend")
    @CrossOrigin(origins = "*")
    public ResponseEntity<?> recommend(@RequestBody BuildRequestDto request) {
        log.info("견적 추천 요청 수신 - 예산: {}, 용도: {}", request.getBudget(), request.getPurpose());
        log.info("Preferences: {}", request.getPreferences());
        
        // 요청 검증
        if (request.getBudget() <= 0) {
            return ResponseEntity.badRequest()
                    .body(Map.of("error", "예산은 0보다 커야 합니다."));
        }
        if (request.getPurpose() == null || request.getPurpose().isEmpty()) {
            return ResponseEntity.badRequest()
                    .body(Map.of("error", "용도를 지정해주세요."));
        }
        
        try {
            BuildRecommendationDto recommendation = buildRecommendationService.recommendBuild(request);
            log.info("견적 추천 완료 - 총 가격: {}, 부품 수: {}", recommendation.getTotalPrice(), 
                    recommendation.getRecommendedParts() != null ? recommendation.getRecommendedParts().size() : 0);
            return ResponseEntity.ok(recommendation);
        } catch (Exception e) {
            log.error("견적 추천 중 오류 발생", e);
            e.printStackTrace();
            return ResponseEntity.status(500)
                    .body(Map.of("error", "견적 추천 중 오류가 발생했습니다: " + e.getMessage()));
        }
    }
    
    /**
     * OPTIONS 요청 처리 (CORS preflight)
     */
    @RequestMapping(value = "/recommend", method = RequestMethod.OPTIONS)
    @CrossOrigin(origins = "*")
    public ResponseEntity<?> recommendOptions() {
        return ResponseEntity.ok().build();
    }
    
    /**
     * 부품 호환성 검사
     * POST /api/builds/check-compatibility
     * Request Body: [partId1, partId2, ...]
     */
    @PostMapping("/check-compatibility")
    public ResponseEntity<CompatibilityResult> checkCompatibility(@RequestBody List<Long> partIds) {
        log.info("호환성 검사 요청 - 부품 개수: {}", partIds.size());
        
        try {
            CompatibilityResult result = compatibilityService.checkCompatibility(partIds);
            return ResponseEntity.ok(result);
        } catch (Exception e) {
            log.error("호환성 검사 중 오류 발생", e);
            return ResponseEntity.internalServerError().build();
        }
    }
    
    /**
     * 견적 저장 (향후 구현)
     * POST /api/builds/save
     */
    @PostMapping("/save")
    public ResponseEntity<String> saveBuild(@RequestBody BuildRecommendationDto config) {
        log.info("견적 저장 요청");
        
        // TODO: build_configurations 테이블에 저장
        return ResponseEntity.ok("견적이 저장되었습니다. (구현 예정)");
    }
}








