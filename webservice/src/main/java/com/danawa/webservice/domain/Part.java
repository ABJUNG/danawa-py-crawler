package com.danawa.webservice.domain;

import jakarta.persistence.*;
import lombok.Getter;
import lombok.NoArgsConstructor;
import org.hibernate.annotations.UpdateTimestamp;

import java.time.LocalDateTime;

@Getter
@NoArgsConstructor
@Entity
@Table(name = "parts")
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

    @Column(name = "img_src", length = 512)
    private String imgSrc;

    // ▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼
    // [추가된 부분] DB에 추가했던 컬럼들을 Entity에도 추가합니다.
    @Column(name = "socket")
    private String socket;

    @Column(name = "core_type")
    private String coreType;

    @Column(name = "ram_capacity")
    private String ramCapacity;

    @Column(name = "chipset")
    private String chipset;
    // ▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲

    @Column(name = "created_at", updatable = false)
    private LocalDateTime createdAt;

    @Column(name = "updated_at")
    @UpdateTimestamp
    private LocalDateTime updatedAt;
}