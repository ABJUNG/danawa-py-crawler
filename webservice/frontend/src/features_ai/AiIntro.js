import React, { useState, useEffect } from 'react';

function AiIntro({ onNext }) {
    const [fadeOut, setFadeOut] = useState(false);

    const handleClick = () => {
        setFadeOut(true);
        setTimeout(() => {
            onNext();
        }, 500);
    };

    return (
        <div className={`intro-container ${fadeOut ? 'fade-out' : ''}`} onClick={handleClick}>
            <div className="intro-message">
                <div
                    style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: '1rem',
                        marginBottom: '1.5rem',
                    }}
                >
                    <div
                        style={{
                            width: '80px',
                            height: '80px',
                            borderRadius: '50%',
                            overflow: 'hidden',
                            border: '4px solid rgba(37, 99, 235, 0.3)',
                            boxShadow: '0 4px 16px rgba(37, 99, 235, 0.2)',
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
                    <div
                        style={{
                            fontSize: '2.5rem',
                            fontWeight: '800',
                            color: '#2563eb',
                            letterSpacing: '-1px',
                        }}
                    >
                        다오나
                    </div>
                </div>
                <div className="intro-content">
                    안녕하세요, PC 견적 추천을 도와드리는 인공지능 다오나입니다.
                    <br />
                    컴퓨터가 어려워도 괜찮아요.
                    <br />몇 가지 질문만 답해주시면, 예산과 용도에 맞는 맞춤형 PC 견적을 추천해드릴게요.
                </div>
            </div>
        </div>
    );
}

export default AiIntro;
