import React, { useState, useEffect } from 'react';
import axios from 'axios';
import './ai-build.css';
import AiIntro from './AiIntro';
import ChatUI from './ChatUI';
import SidebarStack1 from './SidebarStack1';
import SidebarStack2 from './SidebarStack2';
import SidebarStack3 from './SidebarStack3';
import SidebarStack4 from './SidebarStack4';
import AiChatbot from './AiChatbot';

// 백엔드 API 기본 URL
const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8080';

function AiBuildApp() {
    const [phase, setPhase] = useState('intro'); // 'intro', 'chat', 'sidebar'
    const [userAnswers, setUserAnswers] = useState({});
    const [estimateMode, setEstimateMode] = useState(null); // 'auto' or 'guided'
    const [activeStack, setActiveStack] = useState(1);
    const [isLoadingAI, setIsLoadingAI] = useState(false); // AI 추천 로딩 상태

    // Stack 2와 Stack 3 간 공유 상태
    const [selectedParts, setSelectedParts] = useState({}); // {cpu: {model: 'i5-13400F', product: '...', confirmed: true}}
    const [currentCategory, setCurrentCategory] = useState(null); // 현재 선택 중인 카테고리
    const [currentModel, setCurrentModel] = useState(null); // 현재 선택 중인 모델
    const [partCategories, setPartCategories] = useState([]); // DB에서 가져온 카테고리
    const [aiPreferences, setAiPreferences] = useState({}); // SidebarStack1에서 전달받은 AI 설정
    const [aiExplanation, setAiExplanation] = useState(''); // AI 설명
    const [compatibilityResult, setCompatibilityResult] = useState(null); // 호환성 검사 결과

    // 카테고리 목록 로드
    useEffect(() => {
        loadCategories();
    }, []);

    /**
     * DB에서 사용 가능한 카테고리 목록 가져오기
     */
    const loadCategories = async () => {
        try {
            // 모든 카테고리 가져오기 (메인보드 추가)
            const categories = [
                { id: 'cpu', name: 'CPU', dbCategory: 'CPU' },
                { id: 'cooler', name: '쿨러', dbCategory: '쿨러' },
                { id: 'motherboard', name: '메인보드', dbCategory: '메인보드' },
                { id: 'ram', name: 'RAM', dbCategory: 'RAM' },
                { id: 'gpu', name: '그래픽카드', dbCategory: '그래픽카드' },
                { id: 'ssd', name: 'SSD', dbCategory: 'SSD' },
                { id: 'hdd', name: 'HDD', dbCategory: 'HDD' },
                { id: 'psu', name: '파워', dbCategory: '파워' },
                { id: 'case', name: '케이스', dbCategory: '케이스' },
            ];
            setPartCategories(categories);
        } catch (error) {
            console.error('카테고리 로드 실패:', error);
            // 오류 발생 시 기본 카테고리 사용
            setPartCategories([
                { id: 'cpu', name: 'CPU', dbCategory: 'CPU' },
                { id: 'gpu', name: '그래픽카드', dbCategory: '그래픽카드' },
                { id: 'ram', name: 'RAM', dbCategory: 'RAM' },
                { id: 'ssd', name: 'SSD', dbCategory: 'SSD' },
                { id: 'psu', name: '파워', dbCategory: '파워' },
                { id: 'case', name: '케이스', dbCategory: '케이스' },
            ]);
        }
    };

    /**
     * AI 자동 완성: 백엔드 API 호출하여 추천 받기
     */
    const generateAutoCompleteParts = async (preferences = {}) => {
        setIsLoadingAI(true);
        try {
            // 사용자 답변 및 AI 설정에서 예산과 용도 추출
            const budget = preferences.currentBudget || parseInt(userAnswers.budget || '1500000');
            
            // 사용 목적 우선순위: 1) preferences.usagePurposes 2) userAnswers.purpose
            let purpose = '게이밍'; // 기본값
            if (preferences.usagePurposes && preferences.usagePurposes.length > 0) {
                purpose = preferences.usagePurposes[0]; // 첫 번째 용도 사용
            } else if (userAnswers.purpose) {
                purpose = userAnswers.purpose;
            }

            // 백엔드로 전달할 preferences 구성
            const requestPreferences = {
                // 추천 스타일
                recommend_style: preferences.recommendStyle || 'balanced', // value/balanced/highend
                
                // AI 유연성
                ai_flexibility: preferences.aiFlexibility || 'strict', // strict/flexible
                
                // 예산 여유도
                budget_flexibility: preferences.budgetFlexibility || 10, // 0-20%
                
                // 부품별 비율 (백엔드가 참고용으로 사용)
                component_ratios: preferences.componentRatios || {},
                
                // 성능 설정 (선택사항)
                workload_intensity: preferences.workloadIntensity,
                multitasking_level: preferences.multitaskingLevel,
                graphics_target: preferences.graphicsTarget,
                
                // 케이스 및 환경 (선택사항)
                case_size: preferences.caseSize,
                panel_type: preferences.panelType,
                
                // 전력 및 소음 (선택사항)
                power_saving: preferences.powerSaving,
                noise_criteria: preferences.noiseCriteria,
                
                // 디자인 (선택사항)
                rgb_lighting: preferences.rgbLighting,
                color_theme: preferences.colorTheme,
                material: preferences.material,
                
                // 업그레이드 및 내구성 (선택사항)
                upgrade_plan: preferences.upgradePlan,
                as_criteria: preferences.asCriteria,
                lifecycle: preferences.lifecycle
            };

            console.log('AI 추천 요청:', { budget, purpose, preferences: requestPreferences });

            const response = await axios.post(`${API_BASE_URL}/api/builds/recommend`, {
                budget: budget,
                purpose: purpose,
                preferences: requestPreferences
            });

            const recommendation = response.data;
            
            // AI 설명과 호환성 결과 저장
            if (recommendation.explanation) {
                setAiExplanation(recommendation.explanation);
            }
            if (recommendation.compatibilityCheck) {
                setCompatibilityResult(recommendation.compatibilityCheck);
            }
            
            // 백엔드 응답을 selectedParts 형태로 변환
            const parts = {};
            for (const [category, part] of Object.entries(recommendation.recommendedParts || {})) {
                const categoryId = getCategoryId(category);
                if (categoryId) {
                    parts[categoryId] = {
                        model: part.name,
                        product: part,
                        confirmed: true
                    };
                }
            }

            setIsLoadingAI(false);
            return parts;
        } catch (error) {
            console.error('AI 추천 실패:', error);
            setIsLoadingAI(false);
            
            // 상세한 에러 메시지 표시
            let errorMessage = 'AI 추천 중 오류가 발생했습니다.';
            if (error.response) {
                // 서버 응답이 있는 경우
                if (error.response.data && error.response.data.error) {
                    errorMessage = error.response.data.error;
                } else if (error.response.status === 405) {
                    errorMessage = '서버에서 요청을 처리할 수 없습니다. (405 Method Not Allowed)';
                } else if (error.response.status === 403) {
                    errorMessage = '접근이 거부되었습니다. CORS 설정을 확인해주세요.';
                } else {
                    errorMessage = `서버 오류 (${error.response.status}): ${error.response.statusText}`;
                }
            } else if (error.request) {
                // 요청은 보냈지만 응답을 받지 못한 경우
                errorMessage = '서버에 연결할 수 없습니다. 백엔드가 실행 중인지 확인해주세요.';
            } else {
                // 요청 설정 중 오류
                errorMessage = `요청 설정 오류: ${error.message}`;
            }
            
            alert(errorMessage);
            return {};
        }
    };

    /**
     * DB 카테고리명을 ID로 변환
     */
    const getCategoryId = (dbCategory) => {
        const categoryMap = {
            'CPU': 'cpu',
            '쿨러': 'cooler',
            '메인보드': 'motherboard',
            'RAM': 'ram',
            '그래픽카드': 'gpu',
            'SSD': 'ssd',
            'HDD': 'hdd',
            '파워': 'psu',
            '케이스': 'case'
        };
        return categoryMap[dbCategory];
    };

    const handlePhaseChange = (newPhase, data = {}) => {
        setPhase(newPhase);
        if (data.answers) {
            setUserAnswers((prev) => ({ ...prev, ...data.answers }));
        }
        if (data.mode) {
            setEstimateMode(data.mode);
        }
        if (data.stack) {
            setActiveStack(data.stack);
        }
    };

    // Stack 2에서 모델 선택 시 호출 (확정된 부품도 재선택 가능)
    const handleModelSelect = (categoryId, model) => {
        setCurrentCategory(categoryId);
        setCurrentModel(model);
        setActiveStack(3); // Stack 3로 이동
    };

    // 확정된 부품 수정 시작
    const handlePartEdit = (categoryId) => {
        // confirmed 상태를 해제하여 드롭다운으로 다른 모델 선택 가능하게
        const newSelectedParts = { ...selectedParts };
        delete newSelectedParts[categoryId]; // 해당 부품 선택 해제
        setSelectedParts(newSelectedParts);

        // Stack2에서 해당 카테고리 드롭다운 열기 위해 상태만 변경
        // Stack3로 이동하지 않음
    };

    // Stack 3에서 제품 확정 시 호출
    const handleProductConfirm = (categoryId, model, product) => {
        const newSelectedParts = {
            ...selectedParts,
            [categoryId]: {
                model: model,
                product: product,
                confirmed: true,
            },
        };
        setSelectedParts(newSelectedParts);

        setCurrentCategory(null);
        setCurrentModel(null);

        // 모든 부품이 확정되었는지 확인
        const allConfirmed = partCategories.every((cat) => newSelectedParts[cat.id]?.confirmed);

        if (allConfirmed) {
            // 모든 부품 확정되면 Stack 4로 자동 이동
            setTimeout(() => {
                setActiveStack(4);
            }, 500);
        } else {
            // AI 자동완성 모드면 Stack4로, 가이드 모드면 Stack2로
            if (estimateMode === 'auto') {
                setActiveStack(4);
            } else {
                setActiveStack(2);
            }
        }
    };

    return (
        <div className="app">
            {/* Fixed Navigation Bar */}
            <nav className="navbar">
                <div className="nav-brand">Danaolga & Daona: AI PC Builder</div>
            </nav>

            {/* AI Chatbot (플로팅 버튼) */}
            {phase === 'sidebar' && <AiChatbot />}

            {/* Phase 1: Intro Screen */}
            {phase === 'intro' && <AiIntro onNext={() => handlePhaseChange('chat')} />}

            {/* Phase 1: Chat UI (4-step dialogue) */}
            {phase === 'chat' && <ChatUI onComplete={(answers) => handlePhaseChange('sidebar', { answers })} />}

            {/* Phase 2: Sidebar Stacks */}
            {phase === 'sidebar' && (
                <div className="sidebar-layout">
                    <SidebarStack1
                        onNext={async (mode, preferences) => {
                            setEstimateMode(mode);
                            setAiPreferences(preferences); // AI 설정 저장
                            
                            if (mode === 'auto') {
                                // AI 자동완성: 백엔드에서 추천 받기
                                const aiParts = await generateAutoCompleteParts(preferences);
                                
                                // API 호출이 성공했는지 확인 (부품이 있는지 확인)
                                if (aiParts && Object.keys(aiParts).length > 0) {
                                    setSelectedParts(aiParts);
                                    // Stack2와 Stack4만 표시 (Stack3는 건너뜀)
                                    setTimeout(() => setActiveStack(2), 100);
                                    setTimeout(() => setActiveStack(4), 400);
                                } else {
                                    // API 호출 실패 - 가이드 모드로 전환하거나 에러 표시
                                    alert('AI 추천을 받을 수 없습니다. 가이드 모드로 전환합니다.');
                                    setEstimateMode('guided');
                                    setActiveStack(2);
                                }
                            } else {
                                // 가이드 모드: Stack 2로 이동
                                setActiveStack(2);
                            }
                        }}
                        isActive={activeStack >= 1}
                        isLoadingAI={isLoadingAI}
                    />

                    {estimateMode && activeStack >= 2 && (
                        <SidebarStack2
                            onModelSelect={handleModelSelect}
                            onPartEdit={handlePartEdit}
                            onBack={() => setActiveStack(1)}
                            isActive={activeStack >= 2}
                            selectedParts={selectedParts}
                            partCategories={partCategories}
                            currentCategory={currentCategory}
                        />
                    )}

                    {estimateMode && activeStack >= 3 && currentCategory && (
                        <SidebarStack3
                            onProductConfirm={handleProductConfirm}
                            onBack={() => {
                                setActiveStack(estimateMode === 'auto' ? 4 : 2);
                                setCurrentCategory(null);
                                setCurrentModel(null);
                            }}
                            isActive={activeStack >= 3}
                            currentCategory={currentCategory}
                            currentModel={currentModel}
                            userAnswers={userAnswers}
                            aiPreferences={aiPreferences}
                        />
                    )}

                    {estimateMode && activeStack >= 4 && (
                        <SidebarStack4
                            userAnswers={userAnswers}
                            estimateMode={estimateMode}
                            selectedParts={selectedParts}
                            aiExplanation={aiExplanation}
                            compatibilityResult={compatibilityResult}
                            onBack={() => setActiveStack(estimateMode === 'auto' ? 1 : 2)}
                            isActive={activeStack >= 4}
                        />
                    )}
                </div>
            )}
        </div>
    );
}

export default AiBuildApp;
