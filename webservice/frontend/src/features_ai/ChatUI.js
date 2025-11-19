import React, { useState, useEffect, useRef } from 'react';

function ChatUI({ onComplete }) {
    const [conversations, setConversations] = useState([]);
    const [currentStep, setCurrentStep] = useState(0);
    const [answers, setAnswers] = useState({});
    const chatEndRef = useRef(null);
    const hasAddedRef = useRef(false);

    const questions = [
        {
            id: 'skillLevel',
            question: '컴퓨터 견적을 얼마나 잘 알고 계신가요? 편하게 말씀해 주세요.',
            options: [
                { text: '잘 모르겠어요', value: 'beginner' },
                { text: '기본은 알아요', value: 'intermediate' },
                { text: '잘 알아요', value: 'advanced' },
            ],
        },
        {
            id: 'specAwareness',
            question:
                '좋아요. 혹시 지금 사용 중인 PC의 사양을 직접 확인해본 적이 있으신가요? 이건 나중에 업그레이드 가능 여부를 판단하는 데 중요해요. 정확히 몰라도 괜찮으니, 가장 가까운 답을 골라주세요.',
            options: [
                { text: '확인해본 적 없어요', value: 'never_checked' },
                { text: '대략 어떤 부품인지 알아요', value: 'roughly_know' },
                { text: '정확히 확인할 수 있어요', value: 'exactly_know' },
            ],
        },
        {
            id: 'estimatePurpose',
            question:
                '이번 견적은 완전히 새로 맞추시려는 건가요, 아니면 기존 부품을 일부 유지하면서 업그레이드하시려는 건가요?',
            options: [
                { text: '완전 새로 맞추려고 해요', value: 'new_build' },
                { text: '기존 PC 업그레이드하려고 해요', value: 'upgrade' },
            ],
        },
    ];

    // ✅ 수정된 부분
    useEffect(() => {
        if (!hasAddedRef.current && conversations.length === 0) {
            addAIMessage(questions[0]);
            hasAddedRef.current = true; // 이후 재실행 방지
        }
    }, []);

    // 자동 스크롤 기능 - 모든 AI 메시지를 중앙으로
    useEffect(() => {
        if (conversations.length > 0) {
            // 약간의 딜레이 후 스크롤 (DOM 렌더링 완료 대기)
            setTimeout(() => {
                const messageElements = document.querySelectorAll('.chat-message.ai');
                const lastAiMessage = messageElements[messageElements.length - 1];
                if (lastAiMessage) {
                    lastAiMessage.scrollIntoView({ behavior: 'smooth', block: 'center' });
                }
            }, 100);
        }
    }, [conversations]);

    const addAIMessage = (question) => {
        const newMessage = {
            id: Date.now(),
            speaker: 'ai',
            text: question.question,
            options: question.options,
            questionId: question.id,
        };
        setConversations((prev) => [...prev, newMessage]);
    };

    const addUserMessage = (text) => {
        const newMessage = {
            id: Date.now(),
            speaker: 'user',
            text: text,
        };
        setConversations((prev) => [...prev, newMessage]);
    };

    const handleOptionClick = (questionId, option) => {
        // Add user's answer to conversation
        addUserMessage(option.text);

        // Save answer
        const newAnswers = { ...answers, [questionId]: option.value };
        setAnswers(newAnswers);

        // Move to next question or complete
        const nextStep = currentStep + 1;
        if (nextStep < questions.length) {
            setTimeout(() => {
                addAIMessage(questions[nextStep]);
                setCurrentStep(nextStep);
            }, 1000);
        } else {
            // Complete chat phase
            setTimeout(() => {
                onComplete(newAnswers);
            }, 1000);
        }
    };

    return (
        <div className="chat-container">
            {conversations.map((conv) => (
                <div key={conv.id} className={`chat-message ${conv.speaker}`}>
                    {/* AI Message */}
                    {conv.speaker === 'ai' && (
                        <>
                            <div
                                className="chat-avatar ai"
                                style={{
                                    overflow: 'hidden',
                                    position: 'relative',
                                }}
                            >
                                <img
                                    src="https://page.gensparksite.com/v1/base64_upload/0b9ad9992753a55a5d410471d7f3e0f8"
                                    alt="다오나"
                                    style={{
                                        position: 'absolute',
                                        top: '50%',
                                        left: '50%',
                                        width: '140%',
                                        height: '140%',
                                        objectFit: 'cover',
                                        transform: 'translate(-50%, -50%)',
                                    }}
                                />
                            </div>
                            <div className="chat-bubble ai">
                                <div className="chat-text">{conv.text}</div>
                                {conv.options && (
                                    <div className="options-container">
                                        {conv.options.map((option, idx) => (
                                            <button
                                                key={idx}
                                                className="option-button"
                                                onClick={() => handleOptionClick(conv.questionId, option)}
                                            >
                                                {option.text}
                                            </button>
                                        ))}
                                    </div>
                                )}
                            </div>
                        </>
                    )}

                    {/* User Message */}
                    {conv.speaker === 'user' && (
                        <>
                            <div className="chat-bubble user">
                                <div className="chat-text">{conv.text}</div>
                            </div>
                            <div className="chat-avatar user">👤</div>
                        </>
                    )}
                </div>
            ))}
            <div ref={chatEndRef} />
        </div>
    );
}

export default ChatUI;
