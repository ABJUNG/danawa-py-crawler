package com.danawa.webservice.dto;

import lombok.*;

import java.util.ArrayList;
import java.util.List;

@Getter
@Setter
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class CompatibilityResult {
    
    @Builder.Default
    private boolean isCompatible = true;  // 호환 여부
    
    @Builder.Default
    private List<String> errors = new ArrayList<>();  // 치명적 호환성 오류
    
    @Builder.Default
    private List<String> warnings = new ArrayList<>();  // 경고 메시지
    
    private String summary;  // 요약 메시지
    
    /**
     * 오류 추가 (호환성 문제)
     */
    public void addError(String error) {
        if (errors == null) {
            errors = new ArrayList<>();
        }
        errors.add(error);
        this.isCompatible = false;  // 오류가 있으면 호환되지 않음
    }
    
    /**
     * 경고 추가
     */
    public void addWarning(String warning) {
        if (warnings == null) {
            warnings = new ArrayList<>();
        }
        warnings.add(warning);
    }
}

