package com.danawa.webservice.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

import java.util.List;

@Getter
@Setter
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class ChatResponseDto {
    
    private String message;              // AI 응답 메시지
    private List<String> suggestions;    // 제안 버튼 (선택지)
    private String nextAction;           // 다음 액션 (예: "show_build", "select_cpu")
}



