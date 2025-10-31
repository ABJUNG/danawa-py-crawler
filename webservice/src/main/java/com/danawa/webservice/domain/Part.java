package com.danawa.webservice.domain;

import jakarta.persistence.*;
import lombok.AccessLevel;
import lombok.Builder;
import lombok.Getter;
import lombok.NoArgsConstructor;

import java.util.ArrayList;
import java.util.List;

@Getter
@NoArgsConstructor(access = AccessLevel.PROTECTED)
@Entity
@Table(name = "parts") // 테이블명 명시 (선택 사항이지만 권장)
// createdAt, updatedAt 때문에 BaseTimeEntity 상속
public class Part extends BaseTimeEntity { 

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false)
    private String name; // 상품명

    @Column(nullable = false, length = 50)
    private String category; // 카테고리

    @Column(nullable = false)
    private Integer price; // 가격

    @Column(length = 512, unique = true) // link는 중복되면 안 됨
    private String link; // 상품 링크

    @Column(length = 512)
    private String imgSrc; // 이미지 링크

    private String manufacturer; // 제조사

    // (신규) AI 판단 근거
    private String warrantyInfo; // 보증 기간 (예: "5년")

    // (기존) 다나와 리뷰/별점 (인기도)
    private Integer reviewCount;
    private Float starRating;

    // (신규) 1:1 관계 매핑
    @OneToOne(mappedBy = "part", cascade = CascadeType.ALL, fetch = FetchType.LAZY)
    private PartSpec partSpec;

    // (신규) 1:N 관계 매핑
    @OneToMany(mappedBy = "part", cascade = CascadeType.ALL, fetch = FetchType.LAZY)
    private List<CommunityReview> communityReviews = new ArrayList<>();

    // --- 여기부터 ---
    // codename, cpuSeries, cpuClass, socket, cores, threads, ... 등
    // ... 모든 세부 스펙 필드를 전부 삭제합니다 ...
    // ... pcie16pin 까지 전부 삭제 ---

    // --- 기존의 createdAt, updatedAt 필드 삭제 ---
    // (BaseTimeEntity 가 대신하므로)

    // 빌더 패턴도 공통 필드만 남기고 수정합니다.
    @Builder
    public Part(String name, String category, Integer price, String link, String imgSrc, 
                String manufacturer, String warrantyInfo, Integer reviewCount, Float starRating) {
        this.name = name;
        this.category = category;
        this.price = price;
        this.link = link;
        this.imgSrc = imgSrc;
        this.manufacturer = manufacturer;
        this.warrantyInfo = warrantyInfo;
        this.reviewCount = reviewCount;
        this.starRating = starRating;
    }

    // (신규) 연관관계 편의 메서드 (양방향 매핑 시 필요)
    public void setPartSpec(PartSpec partSpec) {
        this.partSpec = partSpec;
    }
}