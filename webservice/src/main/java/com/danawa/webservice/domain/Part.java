package com.danawa.webservice.domain;

import jakarta.persistence.*;
import lombok.Getter;
import lombok.NoArgsConstructor;
import org.hibernate.annotations.UpdateTimestamp;

import java.time.LocalDateTime;

@Getter
@NoArgsConstructor
@Entity
@Table(name = "parts") // 실제 DB 테이블 이름이 'parts'임을 명시
public class Part {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(length = 255, nullable = false)
    private String name;

    @Column(length = 50, nullable = false)
    private String category;

    @Column(nullable = false)
    private int price;


    @Column(length = 512, nullable = false, unique = true)
    private String link;

    @Column(name = "img_src", length = 512) // DB 컬럼명과 필드명이 다를 경우 명시
    private String imgSrc;

    @Column(name = "created_at", updatable = false)
    private LocalDateTime createdAt;

    @Column(name = "updated_at")
    @UpdateTimestamp // 데이터가 업데이트될 때마다 자동으로 현재 시간 저장
    private LocalDateTime updatedAt;
}