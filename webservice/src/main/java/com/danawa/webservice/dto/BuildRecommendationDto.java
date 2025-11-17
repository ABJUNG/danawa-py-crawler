package com.danawa.webservice.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

import java.util.List;
import java.util.Map;

@Getter
@Setter
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class BuildRecommendationDto {
    
    private Map<String, PartResponseDto> recommendedParts;  // 카테고리별 추천 부품
    private int totalPrice;                                  // 총 견적 금액
    private String explanation;                              // AI 설명
    private List<UpgradeOption> upgradeOptions;              // 업그레이드 옵션
    private CompatibilityResult compatibilityCheck;          // 호환성 검사 결과
    
    @Getter
    @Setter
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class UpgradeOption {
        private String category;        // 업그레이드할 부품 카테고리
        private PartResponseDto part;   // 업그레이드 부품
        private int additionalCost;     // 추가 비용
        private String benefit;         // 업그레이드 효과
    }
}








