package com.danawa.webservice.domain;

import jakarta.persistence.*;
import lombok.AccessLevel;
import lombok.Getter;
import lombok.NoArgsConstructor;

@Table(name = "benchmark_results") // 크롤러가 사용하는 테이블 이름과 일치
@Getter
@NoArgsConstructor(access = AccessLevel.PROTECTED)
@Entity
public class BenchmarkResult extends BaseTimeEntity {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    // Part 엔티티와 N:1 (다대일) 관계
    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "part_id") // DB의 part_id FK
    private Part part;

    @Column(nullable = false, length = 64)
    private String source; // 출처 (예: "퀘이사존")

    @Column(nullable = false, length = 128)
    private String testName; // 테스트명 (예: "Cinebench")

    @Column(length = 32)
    private String testVersion; // 버전 (예: "R23")

    @Column(length = 256)
    private String scenario; // 시나리오 (예: "Multi", "Single")

    @Column(nullable = false, length = 64)
    private String metricName; // 측정 항목 (예: "Score")

    @Column(nullable = false)
    private Double value; // 점수

    @Column(length = 32)
    private String unit; // 단위 (예: "pts")

    @Column(length = 512)
    private String reviewUrl; // 출처 URL
    
    // 빌더는 필요 시 추가
}