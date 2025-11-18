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

        // 일반적인 질문 (더 자연스러운 대화)
        if (lowerMessage.includes('안녕') || lowerMessage.includes('하이') || lowerMessage.includes('헬로')) {
            return '안녕하세요! 😊\nPC 견적에 대해 궁금한 점이 있으시면 편하게 물어보세요!\n\n예를 들어:\n• "게임용 CPU 추천해줘"\n• "100만원 예산으로 뭐 살까?"\n• "고성능 SSD 알려줘"';
        }

        // CPU 관련
        if (lowerMessage.includes('cpu') || lowerMessage.includes('프로세서') || lowerMessage.includes('코어')) {
            return '💻 **CPU 추천드립니다!**\n\n게임용:\n• AMD Ryzen 7 7800X3D (약 50만원)\n• Intel i7-14700K (약 45만원)\n\n작업용:\n• AMD Ryzen 9 7950X (약 70만원)\n• Intel i9-14900K (약 75만원)\n\n가성비:\n• AMD Ryzen 5 7600 (약 25만원)\n• Intel i5-14400F (약 22만원)\n\n어떤 용도로 사용하실 건가요?';
        }

        // GPU 관련
        if (lowerMessage.includes('gpu') || lowerMessage.includes('그래픽') || lowerMessage.includes('게임') || lowerMessage.includes('게이밍')) {
            return '🎮 **그래픽카드 추천드립니다!**\n\n1080p 게임:\n• RTX 4060 (약 40만원)\n• RTX 4060 Ti (약 55만원)\n\n1440p 게임:\n• RTX 4070 (약 70만원)\n• RX 7800 XT (약 65만원)\n\n4K 게임:\n• RTX 4080 (약 140만원)\n• RTX 4090 (약 250만원)\n\n해상도와 예산을 알려주시면 더 정확히 추천해드릴게요!';
        }

        // RAM 관련
        if (lowerMessage.includes('램') || lowerMessage.includes('ram') || lowerMessage.includes('메모리')) {
            return '🧠 **RAM 용량 추천드립니다!**\n\n16GB:\n• 일반 게임, 웹서핑, 문서작업\n• 가격: 약 5~8만원\n\n32GB (추천!):\n• 게임 + 방송, 영상편집\n• 가격: 약 10~15만원\n\n64GB:\n• 전문 작업 (3D, 렌더링)\n• 가격: 약 20~30만원\n\n어떤 작업을 주로 하시나요?';
        }

        // SSD 관련
        if (lowerMessage.includes('ssd') || lowerMessage.includes('하드') || lowerMessage.includes('저장')) {
            return '💾 **SSD 추천드립니다!**\n\n가성비 (SATA):\n• 삼성 870 EVO 1TB (약 10만원)\n\n고성능 (NVMe):\n• 삼성 990 PRO 1TB (약 18만원)\n• WD Black SN850X 1TB (약 15만원)\n\n대용량:\n• 2TB 옵션 추천 (약 20~30만원)\n\n게임 설치가 많으면 2TB 이상 추천드려요!';
        }

        // 예산 관련
        if (lowerMessage.includes('예산') || lowerMessage.includes('만원') || lowerMessage.includes('저렴') || lowerMessage.includes('가성비')) {
            return '💰 **예산별 PC 구성 추천드립니다!**\n\n80~100만원:\n• 사무용, 웹서핑, 가벼운 작업\n\n150만원:\n• 1080p 게임 가능\n• CPU: Ryzen 5 / GPU: RTX 4060\n\n200만원 (추천!):\n• 1440p 게임 + 작업\n• CPU: Ryzen 7 / GPU: RTX 4070\n\n300만원 이상:\n• 4K 게임 + 전문 작업\n• CPU: Ryzen 9 / GPU: RTX 4080\n\n구체적인 예산을 말씀해주시면 상세 견적 알려드릴게요!';
        }

        // 파워 관련
        if (lowerMessage.includes('파워') || lowerMessage.includes('psu') || lowerMessage.includes('전원')) {
            return '⚡ **파워 용량 추천드립니다!**\n\n650W:\n• RTX 4060급 시스템\n• 80+ Bronze 이상 추천\n\n750W:\n• RTX 4070급 시스템\n• 80+ Gold 추천\n\n850W 이상:\n• RTX 4080 이상 시스템\n• 80+ Gold/Platinum 추천\n\n파워는 안정성이 중요해요! 정품 인증 제품을 선택하세요.';
        }

        // 케이스 관련
        if (lowerMessage.includes('케이스') || lowerMessage.includes('case') || lowerMessage.includes('본체')) {
            return '🏠 **케이스 추천드립니다!**\n\n미니타워 (작음):\n• 좁은 공간에 적합\n• 확장성 제한적\n\n미들타워 (추천!):\n• 가장 일반적\n• 쿨링과 확장성 균형\n\n풀타워 (큼):\n• 최고 확장성\n• 고급 수랭 쿨링 가능\n\n**쿨링 팁**: 메쉬 패널이 강화유리보다 통풍이 좋아요!';
        }

        // 감사 인사
        if (lowerMessage.includes('감사') || lowerMessage.includes('고마') || lowerMessage.includes('thanks')) {
            return '천만에요! 😊\n도움이 되셨다니 기쁩니다.\n\n더 궁금한 점이 있으시면 언제든 물어보세요!\n좋은 PC 구성하시길 바랍니다! 🎉';
        }

        // 인사
        if (lowerMessage.includes('잘가') || lowerMessage.includes('bye') || lowerMessage.includes('바이')) {
            return '안녕히 가세요! 👋\n좋은 PC 구성 하시길 바랍니다!\n\n다시 궁금한 점이 생기면 언제든 찾아주세요. 😊';
        }

        // 기본 응답 (더 자연스럽고 유용하게)
        return '음... 그 질문은 좀 어렵네요! 🤔\n\n제가 잘 도와드릴 수 있는 주제는:\n\n🔹 **부품 추천**\n• "게임용 GPU 추천해줘"\n• "가성비 CPU 알려줘"\n• "고성능 SSD 뭐가 좋아?"\n\n🔹 **예산별 구성**\n• "100만원으로 PC 맞출 수 있어?"\n• "200만원 예산 추천해줘"\n\n🔹 **부품 설명**\n• "RAM 용량은 얼마나 필요해?"\n• "파워는 몇 W가 좋아?"\n\n편하게 물어보세요! 😊';
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
