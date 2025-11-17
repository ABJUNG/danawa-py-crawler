import React, { useState, useEffect, useRef } from 'react';

function AiChatbot() {
    const [isOpen, setIsOpen] = useState(false);
    const [messages, setMessages] = useState([
        {
            id: 1,
            sender: 'ai',
            text: '안녕하세요! 다오나입니다. 🎧\nPC 견적에 대해 궁금한 점이 있으시면 언제든 물어보세요!',
        },
    ]);
    const [inputText, setInputText] = useState('');
    const messagesEndRef = useRef(null);

    // 자동 스크롤
    useEffect(() => {
        if (messagesEndRef.current) {
            messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
        }
    }, [messages]);

    // AI 자동 응답 (백엔드 Gemini API 연동)
    const getAIResponse = async (userMessage) => {
        try {
            // 백엔드 API URL 설정 (환경 변수 또는 기본값 사용)
            const apiUrl = process.env.REACT_APP_API_URL || 'http://localhost:8080';
            
            const response = await fetch(`${apiUrl}/api/chat`, {
                method: 'POST',
                headers: { 
                    'Content-Type': 'text/plain; charset=UTF-8',
                },
                body: userMessage
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const aiResponse = await response.text();
            return aiResponse;

        } catch (error) {
            console.error('AI 응답 오류:', error);
            
            // 폴백: 샘플 키워드 기반 응답
            return getFallbackResponse(userMessage);
        }
    };

    // 폴백 응답 (API 실패 시)
    const getFallbackResponse = (userMessage) => {
        const lowerMessage = userMessage.toLowerCase();

        // 키워드 기반 자동 응답
        if (lowerMessage.includes('cpu') || lowerMessage.includes('프로세서')) {
            return 'CPU는 컴퓨터의 두뇌 역할을 합니다.\n\n게임용으로는 **AMD Ryzen 7 7800X3D**나 **Intel i7-14700K**를 추천드려요. 작업용이라면 **AMD Ryzen 9 7950X**가 좋습니다.\n\n어떤 용도로 사용하실 건가요?';
        }

        if (lowerMessage.includes('gpu') || lowerMessage.includes('그래픽')) {
            return 'GPU는 그래픽 처리를 담당합니다.\n\n**RTX 4060**: 1080p 게임 (40만원대)\n**RTX 4070**: 1440p 게임 (70만원대)\n**RTX 4080**: 4K 게임 (140만원대)\n\n해상도와 예산에 따라 선택하시면 됩니다!';
        }

        if (lowerMessage.includes('램') || lowerMessage.includes('ram') || lowerMessage.includes('메모리')) {
            return 'RAM은 작업 공간입니다.\n\n**16GB**: 게임 및 일반 작업\n**32GB**: 영상편집, 멀티태스킹\n**64GB**: 전문 작업 (3D, 렌더링)\n\n게임이라면 32GB를 추천드립니다!';
        }

        if (lowerMessage.includes('예산') || lowerMessage.includes('가격')) {
            return '예산별 추천 구성입니다:\n\n**100만원대**: 사무/웹서핑\n**150만원대**: 1080p 게임 가능\n**200만원대**: 1440p 게임 + 작업\n**300만원 이상**: 4K 게임 + 전문 작업\n\n원하시는 예산대가 있으신가요?';
        }

        if (lowerMessage.includes('파워') || lowerMessage.includes('psu')) {
            return 'PSU(파워)는 안정적인 전력 공급을 담당합니다.\n\n**650W**: RTX 4060 급\n**750W**: RTX 4070 급\n**850W+**: RTX 4080 이상\n\n80+ Gold 이상 인증 제품을 권장합니다!';
        }

        if (lowerMessage.includes('케이스') || lowerMessage.includes('case')) {
            return '케이스는 쿨링과 확장성을 고려해야 합니다.\n\n**미니타워**: 작고 가벼움\n**미들타워**: 가장 일반적 (추천)\n**풀타워**: 확장성 최고\n\n쿨링이 중요하다면 메쉬 패널을 추천드려요!';
        }

        if (lowerMessage.includes('감사') || lowerMessage.includes('고마')) {
            return '천만에요! 😊\n더 궁금한 점이 있으시면 언제든 물어보세요.\n\n좋은 PC 구성하시길 바랍니다!';
        }

        // 기본 응답
        return '죄송해요, 그 부분은 잘 모르겠어요. 😅\n\n다음과 같은 질문을 해보세요:\n• CPU 추천해줘\n• GPU 어떤 거 살까?\n• RAM은 몇 GB 필요해?\n• 예산별 추천 알려줘\n• PSU 용량은?\n• 케이스 뭐가 좋아?';
    };

    const handleSendMessage = async () => {
        if (!inputText.trim()) return;

        // 사용자 메시지 추가
        const userMessage = {
            id: Date.now(),
            sender: 'user',
            text: inputText,
        };
        setMessages((prev) => [...prev, userMessage]);

        // 입력창 초기화
        const currentInput = inputText;
        setInputText('');

        // "입력 중..." 표시
        const typingMessage = {
            id: Date.now() + 0.5,
            sender: 'ai',
            text: '답변을 생성하고 있습니다... ⏳',
        };
        setMessages((prev) => [...prev, typingMessage]);

        // AI 응답 받기
        try {
            const aiResponseText = await getAIResponse(currentInput);
            
            // "입력 중..." 메시지 제거 후 실제 응답 추가
            setMessages((prev) => {
                const withoutTyping = prev.filter(msg => msg.id !== typingMessage.id);
                return [...withoutTyping, {
                    id: Date.now() + 1,
                    sender: 'ai',
                    text: aiResponseText,
                }];
            });
        } catch (error) {
            // 오류 시 "입력 중..." 메시지 제거
            setMessages((prev) => prev.filter(msg => msg.id !== typingMessage.id));
        }
    };

    const handleKeyPress = (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSendMessage();
        }
    };

    return (
        <>
            {/* 플로팅 버튼 (말풍선) */}
            <div
                onClick={() => setIsOpen(!isOpen)}
                style={{
                    position: 'fixed',
                    bottom: '2rem',
                    right: '2rem',
                    width: '80px',
                    height: '80px',
                    borderRadius: '50%',
                    background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    boxShadow: '0 8px 24px rgba(102, 126, 234, 0.4)',
                    border: '4px solid white',
                    cursor: 'pointer',
                    zIndex: 9998,
                    transition: 'all 0.3s',
                    fontSize: '3rem',
                }}
                onMouseEnter={(e) => {
                    e.currentTarget.style.transform = 'scale(1.1) translateY(-5px)';
                    e.currentTarget.style.boxShadow = '0 12px 32px rgba(102, 126, 234, 0.5)';
                }}
                onMouseLeave={(e) => {
                    e.currentTarget.style.transform = 'scale(1) translateY(0)';
                    e.currentTarget.style.boxShadow = '0 8px 24px rgba(102, 126, 234, 0.4)';
                }}
            >
                {isOpen ? (
                    <span
                        style={{
                            fontSize: '2.5rem',
                            fontWeight: 'bold',
                            color: 'white',
                            lineHeight: '1',
                        }}
                    >
                        ✕
                    </span>
                ) : (
                    <span style={{ lineHeight: '1' }}>💬</span>
                )}
            </div>

            {/* 채팅창 */}
            {isOpen && (
                <div
                    className="chatbot-window"
                    style={{
                        position: 'fixed',
                        bottom: '6rem',
                        right: '2rem',
                        width: '380px',
                        height: '550px',
                        background: 'white',
                        borderRadius: '16px',
                        boxShadow: '0 12px 48px rgba(0,0,0,0.15)',
                        display: 'flex',
                        flexDirection: 'column',
                        zIndex: 9999,
                        animation: 'slideUp 0.3s ease-out',
                    }}
                >
                    {/* 헤더 */}
                    <div
                        style={{
                            padding: '1.5rem',
                            background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                            borderRadius: '16px 16px 0 0',
                            color: 'white',
                        }}
                    >
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.8rem' }}>
                            <div
                                style={{
                                    width: '50px',
                                    height: '50px',
                                    borderRadius: '50%',
                                    overflow: 'hidden',
                                    border: '3px solid rgba(255,255,255,0.3)',
                                    boxShadow: '0 2px 8px rgba(0,0,0,0.2)',
                                }}
                            >
                                <img
                                    src="https://page.gensparksite.com/v1/base64_upload/0b9ad9992753a55a5d410471d7f3e0f8"
                                    alt="다오나"
                                    style={{
                                        width: '140%',
                                        height: '140%',
                                        objectFit: 'cover',
                                        transform: 'translate(-14%, -14%)',
                                    }}
                                />
                            </div>
                            <div>
                                <div style={{ fontWeight: '700', fontSize: '1.1rem' }}>다오나</div>
                                <div style={{ fontSize: '0.85rem', opacity: 0.9 }}>AI 견적 도우미</div>
                            </div>
                        </div>
                    </div>

                    {/* 메시지 영역 */}
                    <div
                        style={{
                            flex: 1,
                            overflowY: 'auto',
                            padding: '1.5rem',
                            background: '#f8fafc',
                        }}
                    >
                        {messages.map((msg) => (
                            <div
                                key={msg.id}
                                style={{
                                    display: 'flex',
                                    justifyContent: msg.sender === 'ai' ? 'flex-start' : 'flex-end',
                                    marginBottom: '1rem',
                                }}
                            >
                                <div
                                    style={{
                                        maxWidth: '75%',
                                        padding: '0.9rem 1.1rem',
                                        borderRadius: msg.sender === 'ai' ? '4px 16px 16px 16px' : '16px 4px 16px 16px',
                                        background:
                                            msg.sender === 'ai'
                                                ? 'white'
                                                : 'linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%)',
                                        color: msg.sender === 'ai' ? '#1e293b' : 'white',
                                        fontSize: '0.95rem',
                                        lineHeight: '1.5',
                                        whiteSpace: 'pre-wrap',
                                        boxShadow:
                                            msg.sender === 'ai'
                                                ? '0 2px 8px rgba(0,0,0,0.08)'
                                                : '0 4px 12px rgba(99, 102, 241, 0.3)',
                                        border: msg.sender === 'ai' ? '1px solid #e2e8f0' : 'none',
                                    }}
                                >
                                    {msg.text}
                                </div>
                            </div>
                        ))}
                        <div ref={messagesEndRef} />
                    </div>

                    {/* 입력 영역 */}
                    <div
                        style={{
                            padding: '1rem',
                            borderTop: '1px solid #e2e8f0',
                            background: 'white',
                            borderRadius: '0 0 16px 16px',
                        }}
                    >
                        <div style={{ display: 'flex', gap: '0.5rem' }}>
                            <input
                                type="text"
                                value={inputText}
                                onChange={(e) => setInputText(e.target.value)}
                                onKeyPress={handleKeyPress}
                                placeholder="궁금한 점을 물어보세요..."
                                style={{
                                    flex: 1,
                                    padding: '0.9rem',
                                    border: '2px solid #e2e8f0',
                                    borderRadius: '10px',
                                    fontSize: '0.95rem',
                                    outline: 'none',
                                    transition: 'border-color 0.2s',
                                }}
                                onFocus={(e) => (e.target.style.borderColor = '#6366f1')}
                                onBlur={(e) => (e.target.style.borderColor = '#e2e8f0')}
                            />
                            <button
                                onClick={handleSendMessage}
                                style={{
                                    padding: '0.9rem 1.2rem',
                                    background: 'linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%)',
                                    border: 'none',
                                    borderRadius: '10px',
                                    color: 'white',
                                    fontSize: '1.2rem',
                                    cursor: 'pointer',
                                    transition: 'all 0.2s',
                                    display: 'flex',
                                    alignItems: 'center',
                                    justifyContent: 'center',
                                }}
                                onMouseEnter={(e) => {
                                    e.currentTarget.style.transform = 'scale(1.05)';
                                }}
                                onMouseLeave={(e) => {
                                    e.currentTarget.style.transform = 'scale(1)';
                                }}
                            >
                                ➤
                            </button>
                        </div>
                        <div
                            style={{
                                fontSize: '0.75rem',
                                color: '#94a3b8',
                                marginTop: '0.5rem',
                                textAlign: 'center',
                            }}
                        >
                            💡 CPU, GPU, RAM, 예산 등에 대해 물어보세요
                        </div>
                    </div>
                </div>
            )}
        </>
    );
}

export default AiChatbot;
