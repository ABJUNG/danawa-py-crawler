package com.danawa.webservice.domain;

import jakarta.persistence.*;
import lombok.AccessLevel;
import lombok.Builder;
import lombok.Getter;
import lombok.NoArgsConstructor;

import com.fasterxml.jackson.core.type.TypeReference; // 👈 1. import 추가
import com.fasterxml.jackson.databind.ObjectMapper; // 👈 2. import 추가
import java.util.Map; // 👈 3. import 추가
import java.util.HashMap; // 👈 4. import 추가

@Getter
@NoArgsConstructor(access = AccessLevel.PROTECTED)
@Entity
public class PartSpec extends BaseTimeEntity { // 1.1에서 만든 BaseTimeEntity 상속

    @Id 
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    // Part 엔티티와 1:1 관계
    @OneToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "part_id") // DB에는 part_id 라는 FK 컬럼이 생성됨
    private Part part;

    // 모든 세부 스펙이 JSON 문자열 형태로 이 컬럼에 저장됨
    @Column(columnDefinition = "JSON")
    private String specs;

    @Builder
    public PartSpec(Part part, String specs) {
        this.part = part;
        this.specs = specs;
    }
    public Map<String, String> getSpecsAsMap() {
        if (this.specs == null || this.specs.isBlank()) {
            return new HashMap<>(); // 비어있으면 빈 맵 반환
        }
        try {
            ObjectMapper objectMapper = new ObjectMapper();
            return objectMapper.readValue(this.specs, new TypeReference<Map<String, String>>() {});
        } catch (Exception e) {
            e.printStackTrace();
            return new HashMap<>(); // 파싱 실패 시 빈 맵 반환
        }
    }
}