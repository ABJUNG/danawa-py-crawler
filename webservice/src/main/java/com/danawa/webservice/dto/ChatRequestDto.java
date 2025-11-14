package com.danawa.webservice.dto;

import lombok.AllArgsConstructor;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
public class ChatRequestDto {
    
    private String sessionId;   // 대화 세션 ID (컨텍스트 유지용)
    private String message;     // 사용자 메시지
    private String context;     // 대화 컨텍스트 (선택사항)
}

