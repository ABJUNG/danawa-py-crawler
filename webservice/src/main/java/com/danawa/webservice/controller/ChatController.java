package com.danawa.webservice.controller;

import com.danawa.webservice.dto.ChatRequestDto;
import com.danawa.webservice.dto.ChatResponseDto;
import com.danawa.webservice.service.ChatService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.Arrays;
import java.util.List;

@Slf4j
@RestController
@RequestMapping("/api/chat")
@RequiredArgsConstructor
@CrossOrigin(origins = "*")
public class ChatController {
    
    private final ChatService chatService;
    
    /**
     * 대화형 AI 챗봇 메시지 처리
     * POST /api/chat/message
     */
    @PostMapping("/message")
    public ResponseEntity<ChatResponseDto> sendMessage(@RequestBody ChatRequestDto request) {
        log.info("챗봇 메시지 수신 - 세션: {}, 메시지: {}", 
                 request.getSessionId(), request.getMessage());
        
        try {
            // ChatService를 통해 AI 응답 생성
            String aiResponse = chatService.getAiResponse(request.getMessage());
            
            // 응답 메시지 분석하여 제안 버튼 생성
            List<String> suggestions = generateSuggestions(request.getMessage(), aiResponse);
            
            ChatResponseDto response = ChatResponseDto.builder()
                .message(aiResponse)
                .suggestions(suggestions)
                .nextAction(determineNextAction(request.getMessage()))
                .build();
            
            return ResponseEntity.ok(response);
        } catch (Exception e) {
            log.error("챗봇 메시지 처리 중 오류 발생", e);
            
            ChatResponseDto errorResponse = ChatResponseDto.builder()
                .message("죄송합니다. 일시적인 오류가 발생했습니다. 다시 시도해주세요.")
                .suggestions(Arrays.asList("다시 시도", "처음부터"))
                .build();
            
            return ResponseEntity.ok(errorResponse);
        }
    }
    
    /**
     * 사용자 메시지와 AI 응답을 기반으로 제안 버튼 생성
     */
    private List<String> generateSuggestions(String userMessage, String aiResponse) {
        // 간단한 규칙 기반 제안
        if (userMessage.contains("예산") || userMessage.contains("얼마")) {
            return Arrays.asList("100만원", "150만원", "200만원");
        }
        
        if (userMessage.contains("용도") || userMessage.contains("뭐")) {
            return Arrays.asList("게이밍", "영상편집", "사무용", "코딩");
        }
        
        if (aiResponse.contains("추천")) {
            return Arrays.asList("견적 보기", "다른 옵션", "처음부터");
        }
        
        return Arrays.asList("계속하기", "처음부터");
    }
    
    /**
     * 다음 액션 결정
     */
    private String determineNextAction(String userMessage) {
        if (userMessage.contains("추천") || userMessage.contains("견적")) {
            return "show_build";
        }
        
        if (userMessage.contains("CPU") || userMessage.contains("프로세서")) {
            return "select_cpu";
        }
        
        return "continue_chat";
    }
}


