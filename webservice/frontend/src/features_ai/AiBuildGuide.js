import React from 'react';
import './ai-build.css';

function AiBuildGuide() {
    return (
        <div className="build-guide-container">
            <div className="guide-header">
                <h1 className="guide-title">🤖 Danaolga & Daona: AI PC Builder</h1>
                <p className="guide-subtitle">AI 기반 PC 견적 추천 시스템 사용법</p>
            </div>

            <div className="guide-content">
                <section className="guide-section">
                    <div className="guide-section-header">
                        <span className="guide-icon">📋</span>
                        <h2>1단계: 견적 진행 방식 선택</h2>
                    </div>
                    <div className="guide-section-body">
                        <div className="guide-item">
                            <h3>🤖 AI 자동 완성</h3>
                            <p>AI가 사용자의 설정을 바탕으로 모든 부품을 자동으로 추천해드립니다.</p>
                            <ul>
                                <li>빠르고 간편한 견적 생성</li>
                                <li>AI가 최적의 조합을 제안</li>
                                <li>초보자에게 추천</li>
                            </ul>
                        </div>
                        <div className="guide-item">
                            <h3>📖 AI 가이드 선택</h3>
                            <p>AI의 가이드를 받으며 부품을 하나씩 직접 선택합니다.</p>
                            <ul>
                                <li>부품별 상세 정보 확인</li>
                                <li>원하는 부품 직접 선택</li>
                                <li>전문가에게 추천</li>
                            </ul>
                        </div>
                    </div>
                </section>

                <section className="guide-section">
                    <div className="guide-section-header">
                        <span className="guide-icon">🎯</span>
                        <h2>2단계: 추천 스타일 설정</h2>
                    </div>
                    <div className="guide-section-body">
                        <div className="guide-item">
                            <h3>💰 가성비 중심</h3>
                            <p>예산 대비 최고의 성능을 제공하는 부품을 추천합니다.</p>
                        </div>
                        <div className="guide-item">
                            <h3>⚖️ 균형형</h3>
                            <p>가격과 성능의 균형을 맞춘 부품을 추천합니다. (기본값)</p>
                        </div>
                        <div className="guide-item">
                            <h3>🚀 최고사양형</h3>
                            <p>예산 범위 내에서 최고 성능의 부품을 추천합니다.</p>
                        </div>
                    </div>
                </section>

                <section className="guide-section">
                    <div className="guide-section-header">
                        <span className="guide-icon">🔧</span>
                        <h2>3단계: AI 유연성 설정</h2>
                    </div>
                    <div className="guide-section-body">
                        <div className="guide-item">
                            <h3>🔒 조건 엄격 모드</h3>
                            <p>사용자가 선택한 조건을 엄격하게 지킵니다.</p>
                            <ul>
                                <li>선택한 브랜드/부품을 반드시 포함</li>
                                <li>예산을 절대 초과하지 않음</li>
                                <li>명확한 요구사항이 있을 때 추천</li>
                            </ul>
                        </div>
                        <div className="guide-item">
                            <h3>✨ 자유 추천 모드</h3>
                            <p>AI가 더 나은 대안을 자유롭게 제안합니다.</p>
                            <ul>
                                <li>더 좋은 옵션이 있으면 제안</li>
                                <li>예산을 약간 초과해도 성능 향상이 크면 추천</li>
                                <li>유연한 선택을 원할 때 추천</li>
                            </ul>
                        </div>
                    </div>
                </section>

                <section className="guide-section">
                    <div className="guide-section-header">
                        <span className="guide-icon">💻</span>
                        <h2>4단계: 사용 목적 선택</h2>
                    </div>
                    <div className="guide-section-body">
                        <div className="guide-grid">
                            <div className="guide-item-small">
                                <h3>📄 사무용</h3>
                                <p>문서 작업, 인터넷 검색 등 기본 업무용</p>
                            </div>
                            <div className="guide-item-small">
                                <h3>🎮 게이밍</h3>
                                <p>게임 플레이에 최적화된 구성</p>
                            </div>
                            <div className="guide-item-small">
                                <h3>🎨 디자인</h3>
                                <p>그래픽 디자인, CAD 작업용</p>
                            </div>
                            <div className="guide-item-small">
                                <h3>🎬 영상 편집</h3>
                                <p>영상 편집 및 렌더링 작업용</p>
                            </div>
                            <div className="guide-item-small">
                                <h3>💻 코딩·AI</h3>
                                <p>개발 및 AI 모델 학습용</p>
                            </div>
                        </div>
                        <p className="guide-note">💡 여러 목적을 선택하면 평균적인 구성으로 추천됩니다.</p>
                    </div>
                </section>

                <section className="guide-section">
                    <div className="guide-section-header">
                        <span className="guide-icon">💰</span>
                        <h2>5단계: 예산 범위 설정</h2>
                    </div>
                    <div className="guide-section-body">
                        <div className="guide-item">
                            <p>최소 예산과 최대 예산을 설정하세요.</p>
                            <ul>
                                <li>AI가 설정한 예산 범위 내에서 최적의 견적을 제안합니다</li>
                                <li>예산 여유도 설정으로 약간의 초과/하회를 허용할 수 있습니다</li>
                            </ul>
                        </div>
                    </div>
                </section>

                <section className="guide-section">
                    <div className="guide-section-header">
                        <span className="guide-icon">🚀</span>
                        <h2>시작하기</h2>
                    </div>
                    <div className="guide-section-body">
                        <div className="guide-start-box">
                            <p className="guide-start-text">
                                왼쪽 사이드바에서 설정을 완료한 후<br />
                                <strong>"AI 견적 추천 시작"</strong> 버튼을 클릭하세요!
                            </p>
                            <div className="guide-features">
                                <div className="guide-feature">
                                    <span className="guide-feature-icon">✅</span>
                                    <span>호환성 자동 검사</span>
                                </div>
                                <div className="guide-feature">
                                    <span className="guide-feature-icon">🤖</span>
                                    <span>AI 설명 제공</span>
                                </div>
                                <div className="guide-feature">
                                    <span className="guide-feature-icon">📊</span>
                                    <span>상세 스펙 표시</span>
                                </div>
                                <div className="guide-feature">
                                    <span className="guide-feature-icon">💬</span>
                                    <span>실시간 챗봇 지원</span>
                                </div>
                            </div>
                        </div>
                    </div>
                </section>

                <section className="guide-section">
                    <div className="guide-section-header">
                        <span className="guide-icon">💡</span>
                        <h2>팁</h2>
                    </div>
                    <div className="guide-section-body">
                        <div className="guide-tips">
                            <div className="guide-tip">
                                <strong>초보자라면?</strong>
                                <p>AI 자동 완성 + 균형형 + 조건 엄격 모드를 추천합니다.</p>
                            </div>
                            <div className="guide-tip">
                                <strong>전문가라면?</strong>
                                <p>AI 가이드 선택 + 자유 추천 모드로 세밀한 조정이 가능합니다.</p>
                            </div>
                            <div className="guide-tip">
                                <strong>예산이 타이트하다면?</strong>
                                <p>가성비 중심 + 조건 엄격 모드 + 예산 여유도 낮게 설정하세요.</p>
                            </div>
                        </div>
                    </div>
                </section>
            </div>
        </div>
    );
}

export default AiBuildGuide;

