package com.danawa.webservice.domain;

import jakarta.persistence.*;
import lombok.AccessLevel;
import lombok.Builder;
import lombok.Getter;
import lombok.NoArgsConstructor;
import jakarta.persistence.Table;

@Table(name = "community_reviews")
@Getter
@NoArgsConstructor(access = AccessLevel.PROTECTED)
@Entity
public class CommunityReview extends BaseTimeEntity { // 1.1에서 만든 BaseTimeEntity 상속

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    // Part 엔티티와 N:1 (다대일) 관계
    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "part_id") // DB에는 part_id 라는 FK 컬럼이 생성됨
    private Part part;

    @Column(nullable = false)
    private String source; // 출처 (예: "퀘이사존")

    @Column(nullable = false, unique = true, length = 512)
    private String reviewUrl; // 원본 글 URL (중복 수집 방지)

    @Column(columnDefinition = "TEXT")
    private String rawText; // 크롤링한 원본 텍스트

    @Column(columnDefinition = "TEXT")
    private String aiSummary; // AI가 요약한 텍스트 (초기엔 NULL)

    private Float reviewScore; // 리뷰 점수 (있다면)

    @Builder
    public CommunityReview(Part part, String source, String reviewUrl, String rawText, Float reviewScore) {
        this.part = part;
        this.source = source;
        this.reviewUrl = reviewUrl;
        this.rawText = rawText;
        this.reviewScore = reviewScore;
    }

    // AI 요약본을 업데이트하기 위한 메서드
    public void updateAiSummary(String aiSummary) {
        this.aiSummary = aiSummary;
    }
}