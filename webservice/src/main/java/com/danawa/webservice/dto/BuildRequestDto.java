package com.danawa.webservice.dto;

import lombok.AllArgsConstructor;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

import java.util.Map;

@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
public class BuildRequestDto {
    
    private int budget;                    // 예산 (원)
    private String purpose;                // 용도 (게이밍, 영상편집, 사무용 등)
    private Map<String, String> preferences; // 추가 요구사항 (브랜드 선호, RGB 여부 등)
}


