package com.danawa.webservice.domain;

import jakarta.persistence.*;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Getter;
import lombok.NoArgsConstructor;

@Entity
@Table(name = "compatibility_rules")
@Getter
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class CompatibilityRule extends BaseTimeEntity {
    
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;
    
    @Column(nullable = false, length = 50)
    private String ruleType;
    
    @Column(length = 100)
    private String sourceValue;
    
    @Column(length = 100)
    private String targetValue;
    
    @Column(nullable = false)
    private Boolean isCompatible;
}

