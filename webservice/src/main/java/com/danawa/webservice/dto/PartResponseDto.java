package com.danawa.webservice.dto; // 1. dto 패키지

import com.danawa.webservice.domain.Part;
import com.danawa.webservice.domain.CommunityReview;
import lombok.Getter;

@Getter
public class PartResponseDto {
    // --- Tier 1: 'parts' 테이블의 공통 정보 ---
    private Long id;
    private String name;
    private String category;
    private Integer price;
    private String link;
    private String imgSrc;
    private String manufacturer;
    private String warrantyInfo;
    private Integer reviewCount; // 다나와 리뷰 수
    private Float starRating;  // 다나와 별점

    // --- Tier 2: 'part_spec' 테이블의 세부 스펙 (JSON 문자열) ---
    private String specs;

    // --- Tier 3: 'community_reviews' 테이블의 AI 요약 ---
    private String aiSummary; // AI가 요약한 퀘이사존 리뷰

    /**
     * Entity(Part)를 DTO(PartResponseDto)로 변환하는 생성자
     * Part 엔티티를 받아서 프론트엔드가 필요한 모든 데이터를 조합합니다.
     */
    public PartResponseDto(Part entity) {
        // 1. Part 엔티티의 기본 정보 복사
        this.id = entity.getId();
        this.name = entity.getName();
        this.category = entity.getCategory();
        this.price = entity.getPrice();
        this.link = entity.getLink();
        this.imgSrc = entity.getImgSrc();
        this.manufacturer = entity.getManufacturer();
        this.warrantyInfo = entity.getWarrantyInfo();
        this.reviewCount = entity.getReviewCount();
        this.starRating = entity.getStarRating();

        // 2. PartSpec에서 'specs' (JSON) 정보 가져오기
        // (N+1 문제가 발생할 수 있지만, 우선 작동하도록 구현)
        if (entity.getPartSpec() != null) {
            this.specs = entity.getPartSpec().getSpecs();
        }

        // 3. CommunityReviews 리스트에서 'aiSummary' 가져오기
        // (N+1 문제가 발생할 수 있지만, 우선 작동하도록 구현)
        if (entity.getCommunityReviews() != null && !entity.getCommunityReviews().isEmpty()) {
            // 여러 리뷰 중 요약(aiSummary)이 있는 첫 번째 리뷰를 찾아서 DTO에 담습니다.
            this.aiSummary = entity.getCommunityReviews().stream()
                    .map(CommunityReview::getAiSummary) // CommunityReview 객체에서 aiSummary 문자열만 추출
                    .filter(summary -> summary != null && !summary.isBlank()) // NULL이나 빈 요약은 제외
                    .findFirst() // 가장 첫 번째 요약본을
                    .orElse(null); // 없으면 NULL
        }
    }
}