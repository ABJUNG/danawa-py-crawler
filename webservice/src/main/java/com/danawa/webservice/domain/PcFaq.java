package com.danawa.webservice.domain;

import jakarta.persistence.*;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Getter;
import lombok.NoArgsConstructor;
import org.hibernate.annotations.CreationTimestamp;

import java.time.LocalDateTime;

@Entity
@Table(name = "pc_faq")
@Getter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class PcFaq {
    
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;
    
    @Column(nullable = false, length = 500)
    private String question;
    
    @Column(nullable = false, columnDefinition = "TEXT")
    private String answer;
    
    @Column(length = 50)
    private String category;
    
    @Column(length = 255)
    private String keywords;
    
    @Column(name = "view_count")
    @Builder.Default
    private Integer viewCount = 0;
    
    @Column(name = "helpful_count")
    @Builder.Default
    private Integer helpfulCount = 0;
    
    @CreationTimestamp
    @Column(name = "created_at", updatable = false)
    private LocalDateTime createdAt;
    
    // 조회수 증가
    public void incrementViewCount() {
        this.viewCount++;
    }
    
    // 도움됨 카운트 증가
    public void incrementHelpfulCount() {
        this.helpfulCount++;
    }
}

