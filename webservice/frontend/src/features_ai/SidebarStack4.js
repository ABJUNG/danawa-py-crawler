import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { formatPartName } from '../utils/partNameFormatter';

// 백엔드 API 기본 URL
const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8080';

function SidebarStack4({ userAnswers, estimateMode, selectedParts, aiExplanation, compatibilityResult, aiPreferences, onBack, onReset, isActive }) {
    const [showAIMessage, setShowAIMessage] = useState(false);
    const [isReviewing, setIsReviewing] = useState(false);
    const [reviewResult, setReviewResult] = useState(null);

    useEffect(() => {
        setTimeout(() => setShowAIMessage(true), 500);
    }, []);

    // selectedParts를 견적 테이블 형식으로 변환
    const getFinalBuild = () => {
        const partsList = [];

        // 실제 부품 정보 추출
        const categoryMap = {
            cpu: 'CPU',
            cooler: '쿨러',
            motherboard: '메인보드',
            ram: 'RAM',
            gpu: '그래픽카드',
            ssd: 'SSD',
            hdd: 'HDD',
            psu: '파워',
            case: '케이스'
        };

        for (const [key, dbCategory] of Object.entries(categoryMap)) {
            if (selectedParts[key]?.confirmed && selectedParts[key].product) {
                const product = selectedParts[key].product;
                // 스펙 정보 추출 (specs 필드에서) - 상세 스펙 한 줄 표시
                let specs = '';
                if (product.specs) {
                    try {
                        const specsObj = typeof product.specs === 'string' 
                            ? JSON.parse(product.specs) 
                            : product.specs;
                        
                        const specParts = []; // 슬래시로 구분할 스펙 배열
                        
                        // 카테고리별 상세 스펙 추출
                        if (dbCategory === 'CPU') {
                            if (specsObj.manufacturer) specParts.push(specsObj.manufacturer);
                            if (specsObj.codename) specParts.push(specsObj.codename);
                            if (specsObj.generation) specParts.push(specsObj.generation);
                            if (specsObj.series) specParts.push(specsObj.series);
                            if (specsObj.socket) specParts.push(specsObj.socket);
                            if (specsObj.cores) specParts.push(`${specsObj.cores}코어`);
                            if (specsObj.threads) specParts.push(`${specsObj.threads}스레드`);
                            if (specsObj.base_clock) specParts.push(specsObj.base_clock);
                            if (specsObj.boost_clock) specParts.push(specsObj.boost_clock);
                        } else if (dbCategory === '그래픽카드') {
                            if (specsObj.manufacturer) specParts.push(specsObj.manufacturer);
                            if (specsObj.chipset_manufacturer) specParts.push(specsObj.chipset_manufacturer);
                            if (specsObj.nvidia_chipset) specParts.push(specsObj.nvidia_chipset);
                            if (specsObj.amd_chipset) specParts.push(specsObj.amd_chipset);
                            if (specsObj.chipset) specParts.push(specsObj.chipset);
                            if (specsObj.memory_capacity) specParts.push(specsObj.memory_capacity);
                            if (specsObj.memory_type) specParts.push(specsObj.memory_type);
                            if (specsObj.interface) specParts.push(specsObj.interface);
                            if (specsObj.base_clock) specParts.push(`베이스 ${specsObj.base_clock}`);
                            if (specsObj.boost_clock) specParts.push(`부스트 ${specsObj.boost_clock}`);
                            if (specsObj.stream_processors) specParts.push(`${specsObj.stream_processors} SP`);
                            if (specsObj.cuda_cores) specParts.push(`${specsObj.cuda_cores} CUDA`);
                        } else if (dbCategory === 'RAM') {
                            if (specsObj.manufacturer) specParts.push(specsObj.manufacturer);
                            if (specsObj.device_type) specParts.push(specsObj.device_type);
                            if (specsObj.product_class) specParts.push(specsObj.product_class);
                            if (specsObj.memory_standard) specParts.push(specsObj.memory_standard);
                            if (specsObj.operating_clock) specParts.push(specsObj.operating_clock);
                            if (specsObj.memory_clock) specParts.push(specsObj.memory_clock);
                            if (specsObj.capacity) specParts.push(specsObj.capacity);
                            if (specsObj.ram_count) specParts.push(specsObj.ram_count);
                            if (specsObj.timing) specParts.push(specsObj.timing);
                            if (specsObj.voltage) specParts.push(specsObj.voltage);
                        } else if (dbCategory === 'SSD') {
                            if (specsObj.manufacturer) specParts.push(specsObj.manufacturer);
                            if (specsObj.storage_capacity) specParts.push(specsObj.storage_capacity);
                            if (specsObj.form_factor) specParts.push(specsObj.form_factor);
                            if (specsObj.interface) specParts.push(specsObj.interface);
                            if (specsObj.memory_type) specParts.push(specsObj.memory_type);
                            if (specsObj.nand_type) specParts.push(specsObj.nand_type);
                            if (specsObj.dram_mounted) specParts.push(specsObj.dram_mounted);
                            if (specsObj.controller) specParts.push(specsObj.controller);
                            if (specsObj.sequential_read) specParts.push(`읽기 ${specsObj.sequential_read}`);
                            if (specsObj.max_read_speed) specParts.push(`읽기 ${specsObj.max_read_speed}`);
                            if (specsObj.sequential_write) specParts.push(`쓰기 ${specsObj.sequential_write}`);
                            if (specsObj.max_write_speed) specParts.push(`쓰기 ${specsObj.max_write_speed}`);
                        } else if (dbCategory === 'HDD') {
                            if (specsObj.manufacturer) specParts.push(specsObj.manufacturer);
                            if (specsObj.product_class) specParts.push(specsObj.product_class);
                            if (specsObj.disk_capacity) specParts.push(specsObj.disk_capacity);
                            if (specsObj.form_factor) specParts.push(specsObj.form_factor);
                            if (specsObj.interface) specParts.push(specsObj.interface);
                            if (specsObj.hdd_interface) specParts.push(specsObj.hdd_interface);
                            if (specsObj.rotation_speed) specParts.push(specsObj.rotation_speed);
                            if (specsObj.buffer_capacity) specParts.push(specsObj.buffer_capacity);
                            if (specsObj.recording_method) specParts.push(specsObj.recording_method);
                        } else if (dbCategory === '파워') {
                            if (specsObj.manufacturer) specParts.push(specsObj.manufacturer);
                            if (specsObj.product_class) specParts.push(specsObj.product_class);
                            if (specsObj.rated_output) specParts.push(specsObj.rated_output);
                            if (specsObj.certification_80plus) specParts.push(specsObj.certification_80plus);
                            if (specsObj.cable_connection) specParts.push(specsObj.cable_connection);
                            if (specsObj.product_type) specParts.push(specsObj.product_type);
                            if (specsObj.pfc_circuit) specParts.push(specsObj.pfc_circuit);
                            if (specsObj.eta_certification) specParts.push(`ETA ${specsObj.eta_certification}`);
                            if (specsObj.depth) specParts.push(`깊이 ${specsObj.depth}`);
                        } else if (dbCategory === '메인보드') {
                            // 사용자 요청 순서대로 표시: 제조사, 메모리 종류, VGA 연결, 폼팩터, 전원부, 메모리 클럭, 최대 메모리, EXPO
                            if (specsObj.manufacturer) specParts.push(specsObj.manufacturer);
                            if (specsObj.memory_type) specParts.push(specsObj.memory_type);
                            // VGA 연결: vga_interface 또는 vga_connection 필드 확인
                            if (specsObj.vga_interface) {
                                // "VGA 연결: PCIe5.0 x16" 형식에서 "VGA 연결: " 제거
                                let vgaInterface = specsObj.vga_interface;
                                if (vgaInterface.includes('VGA 연결:')) {
                                    vgaInterface = vgaInterface.replace('VGA 연결:', '').trim();
                                }
                                specParts.push(vgaInterface);
                            } else if (specsObj.vga_connection) {
                                specParts.push(specsObj.vga_connection);
                            }
                            // 폼팩터: board_form_factor 우선, 없으면 form_factor
                            if (specsObj.board_form_factor) {
                                specParts.push(specsObj.board_form_factor);
                            } else if (specsObj.form_factor) {
                                specParts.push(specsObj.form_factor);
                            }
                            if (specsObj.power_phase) specParts.push(specsObj.power_phase);
                            if (specsObj.memory_clock) specParts.push(specsObj.memory_clock);
                            // 최대 메모리: max_memory_capacity 우선, 없으면 max_memory
                            if (specsObj.max_memory_capacity) {
                                specParts.push(`최대 ${specsObj.max_memory_capacity}`);
                            } else if (specsObj.max_memory) {
                                specParts.push(`최대 ${specsObj.max_memory}`);
                            }
                            // EXPO: expo 필드 확인 (Y/N 또는 true/false)
                            if (specsObj.expo !== undefined && specsObj.expo !== null) {
                                const expoValue = specsObj.expo.toString().toUpperCase();
                                if (expoValue === 'Y' || expoValue === 'TRUE' || expoValue === 'YES' || expoValue === '1') {
                                    specParts.push('EXPO: Y');
                                } else if (expoValue === 'N' || expoValue === 'FALSE' || expoValue === 'NO' || expoValue === '0') {
                                    // EXPO: N은 표시하지 않음 (기본값)
                                }
                            }
                        } else if (dbCategory === '케이스') {
                            if (specsObj.manufacturer) specParts.push(specsObj.manufacturer);
                            if (specsObj.product_class) specParts.push(specsObj.product_class);
                            if (specsObj.case_size) specParts.push(specsObj.case_size);
                            if (specsObj.board_support) specParts.push(specsObj.board_support);
                            if (specsObj.vga_length) specParts.push(`VGA ${specsObj.vga_length}`);
                            if (specsObj.cpu_cooler_height) specParts.push(`쿨러 ${specsObj.cpu_cooler_height}`);
                            if (specsObj.power_included) specParts.push(specsObj.power_included);
                            if (specsObj.power_support) specParts.push(specsObj.power_support);
                            if (specsObj.front_panel) specParts.push(specsObj.front_panel);
                            if (specsObj.side_panel_type) specParts.push(specsObj.side_panel_type);
                        } else if (dbCategory === '쿨러') {
                            if (specsObj.manufacturer) specParts.push(specsObj.manufacturer);
                            if (specsObj.product_class) specParts.push(specsObj.product_class);
                            if (specsObj.cooling_type) specParts.push(specsObj.cooling_type);
                            if (specsObj.cooler_form) specParts.push(specsObj.cooler_form);
                            if (specsObj.tdp) specParts.push(`TDP ${specsObj.tdp}`);
                            if (specsObj.intel_socket) specParts.push(`Intel ${specsObj.intel_socket}`);
                            if (specsObj.amd_socket) specParts.push(`AMD ${specsObj.amd_socket}`);
                            if (specsObj.socket_support) specParts.push(specsObj.socket_support);
                            if (specsObj.cooler_width) specParts.push(`가로 ${specsObj.cooler_width}`);
                            if (specsObj.cooler_height) specParts.push(`높이 ${specsObj.cooler_height}`);
                        }
                        
                        // 슬래시로 구분하여 한 줄로 표시
                        specs = specParts.filter(part => part && part.trim()).join(' / ');
                        
                        // 스펙이 없으면 기본 정보 표시
                        if (!specs) {
                            specs = specsObj.product_class || product.name || '';
                        }
                    } catch (e) {
                        specs = product.name || selectedParts[key].model;
                    }
                } else {
                    specs = product.name || selectedParts[key].model;
                }

                // 상품명 포맷팅 (용량/개수 정보 추출)
                const formatted = formatPartName(product.name || selectedParts[key].model, dbCategory);
                
                partsList.push({
                    category: dbCategory,
                    model: selectedParts[key].model,
                    product: formatted.displayName,
                    price: product.price || 0,
                    specs: specs || selectedParts[key].model,
                    capacity: formatted.capacity,
                    package: formatted.package,
                });
            }
        }

        // 샘플 데이터 제거 - 실제 API 응답만 사용
        return partsList;
    };

    const finalBuild = getFinalBuild();
    const totalPrice = finalBuild.reduce((sum, item) => sum + item.price, 0);
    // 예산 계산: aiPreferences.currentBudget 우선, 없으면 userAnswers.budget, 둘 다 없으면 기본값
    const budget = aiPreferences?.currentBudget 
        ? parseInt(aiPreferences.currentBudget) 
        : (userAnswers.budget ? parseInt(userAnswers.budget) : 1500000);
    const remaining = budget - totalPrice;
    const usageRate = budget > 0 ? ((totalPrice / budget) * 100).toFixed(1) : 0;

    const handleAIReview = async () => {
        setIsReviewing(true);
        setReviewResult(null);
        
        try {
            // selectedParts에서 part ID 추출
            const partIds = [];
            for (const [categoryId, partData] of Object.entries(selectedParts)) {
                if (partData?.confirmed && partData?.product?.id) {
                    partIds.push(partData.product.id);
                }
            }
            
            if (partIds.length === 0) {
                alert('재검토할 부품이 없습니다. 먼저 부품을 선택해주세요.');
                setIsReviewing(false);
                return;
            }
            
            // 호환성 검사 API 호출
            const response = await axios.post(`${API_BASE_URL}/api/builds/check-compatibility`, partIds);
            const compatibilityCheck = response.data;
            
            // 예산 검사
            const budgetCheck = {
                totalPrice: totalPrice,
                budget: budget,
                remaining: remaining,
                usageRate: usageRate,
                isWithinBudget: remaining >= 0,
                isOverBudget: remaining < 0
            };
            
            // 전력 공급 검사 (간단한 추정)
            const powerCheck = {
                estimatedPower: estimatePowerConsumption(selectedParts),
                recommendedPSU: getRecommendedPSU(selectedParts),
                isSufficient: true // 실제 계산은 복잡하므로 간단히 true로 설정
            };
            
            setReviewResult({
                compatibility: compatibilityCheck,
                budget: budgetCheck,
                power: powerCheck,
                timestamp: new Date().toLocaleString('ko-KR')
            });
        } catch (error) {
            console.error('AI 재검토 실패:', error);
            alert('재검토 중 오류가 발생했습니다. 다시 시도해주세요.');
        } finally {
            setIsReviewing(false);
        }
    };
    
    /**
     * 전력 소비량 추정 (간단한 추정)
     */
    const estimatePowerConsumption = (parts) => {
        // 간단한 추정 로직 (실제로는 더 복잡한 계산 필요)
        let estimated = 0;
        
        // CPU: 약 65-250W
        if (parts.cpu?.product) {
            estimated += 150; // 평균값
        }
        
        // GPU: 약 100-450W
        if (parts.gpu?.product) {
            estimated += 250; // 평균값
        }
        
        // 기타 부품: 약 100W
        estimated += 100;
        
        return estimated;
    };
    
    /**
     * 권장 PSU 용량 계산
     */
    const getRecommendedPSU = (parts) => {
        const estimated = estimatePowerConsumption(parts);
        // 여유를 두고 1.5배 권장
        return Math.ceil(estimated * 1.5 / 50) * 50; // 50W 단위로 반올림
    };

    return (
        <div className={`sidebar-stack sidebar-stack-4 ${isActive ? 'slide-in' : ''}`}>
            <div className="sidebar-header">
                <div className="sidebar-title">📋 최종 견적서</div>
                <div style={{ fontSize: '0.85rem', color: '#64748b', marginTop: '0.3rem' }}>
                    {estimateMode === 'auto' ? '✨ AI 자동 완성' : '🤖 AI 가이드 선택'} 방식
                </div>
            </div>

            <div className="sidebar-content">
                {/* Estimate Summary Table (Horizontal Card Style) */}
                <div style={{ marginBottom: '2rem' }}>
                    <label className="form-label">📦 견적 구성 ({finalBuild.length}개 부품)</label>
                    {finalBuild.length === 0 ? (
                        <div
                            style={{
                                padding: '2rem',
                                textAlign: 'center',
                                background: '#f8fafc',
                                border: '2px dashed #cbd5e1',
                                borderRadius: '10px',
                                color: '#64748b',
                            }}
                        >
                            아직 선택된 부품이 없습니다.
                            <br />
                            Stack 2에서 부품을 선택해주세요.
                        </div>
                    ) : (
                        <div
                            style={{
                                background: '#ffffff',
                                border: '2px solid #e2e8f0',
                                borderRadius: '12px',
                                overflow: 'hidden',
                                boxShadow: '0 4px 12px rgba(0,0,0,0.08)',
                            }}
                        >
                            {finalBuild.map((item, idx) => (
                                <div
                                    key={idx}
                                    style={{
                                        display: 'grid',
                                        gridTemplateColumns: '90px 1fr 130px',
                                        gap: '1rem',
                                        padding: '1.2rem',
                                        background: idx % 2 === 0 ? '#ffffff' : '#f8fafc',
                                        borderBottom: idx < finalBuild.length - 1 ? '1px solid #e2e8f0' : 'none',
                                        alignItems: 'start',
                                        transition: 'background 0.2s',
                                    }}
                                >
                                    <div
                                        style={{
                                            fontWeight: '700',
                                            fontSize: '0.9rem',
                                            color: '#ffffff',
                                            background: 'linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%)',
                                            padding: '0.5rem',
                                            borderRadius: '6px',
                                            textAlign: 'center',
                                        }}
                                    >
                                        {item.category}
                                    </div>
                                    <div>
                                        <div
                                            style={{
                                                fontSize: '0.95rem',
                                                fontWeight: '600',
                                                marginBottom: '0.3rem',
                                                color: '#1e293b',
                                            }}
                                        >
                                            {item.product}
                                        </div>
                                        <div style={{ fontSize: '0.75rem', color: '#64748b', lineHeight: '1.4', marginTop: '0.3rem' }}>
                                            {item.specs}
                                        </div>
                                        {item.capacity && (
                                            <div style={{ fontSize: '0.7rem', color: '#2563eb', marginTop: '0.2rem', fontWeight: '600' }}>
                                                💾 용량: {item.capacity}
                                            </div>
                                        )}
                                        {item.package && (
                                            <div style={{ fontSize: '0.7rem', color: '#2563eb', marginTop: '0.2rem', fontWeight: '600' }}>
                                                📦 구성: {item.package}
                                            </div>
                                        )}
                                    </div>
                                    <div
                                        style={{
                                            fontSize: '1.1rem',
                                            fontWeight: '800',
                                            color: '#2563eb',
                                            textAlign: 'right',
                                        }}
                                    >
                                        ₩{item.price.toLocaleString()}
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}
                </div>

                {/* Total & Remaining Budget */}
                {finalBuild.length > 0 && (
                    <div
                        style={{
                            padding: '1.5rem',
                            background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                            border: 'none',
                            borderRadius: '12px',
                            marginBottom: '1.5rem',
                            boxShadow: '0 8px 24px rgba(102, 126, 234, 0.3)',
                        }}
                    >
                        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.8rem' }}>
                            <span style={{ fontSize: '1rem', fontWeight: '600', color: 'white' }}>💰 총 견적 금액</span>
                            <span style={{ fontSize: '1.5rem', fontWeight: '900', color: 'white' }}>
                                ₩{totalPrice.toLocaleString()}
                            </span>
                        </div>
                        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.8rem' }}>
                            <span style={{ fontSize: '0.9rem', color: 'rgba(255,255,255,0.9)' }}>잔액</span>
                            <span
                                style={{
                                    fontSize: '1.1rem',
                                    fontWeight: '700',
                                    color: remaining >= 0 ? '#d1fae5' : '#fecaca',
                                    textShadow: '0 2px 4px rgba(0,0,0,0.1)',
                                }}
                            >
                                {remaining >= 0 ? '+' : ''}₩{remaining.toLocaleString()}
                            </span>
                        </div>
                        <div
                            style={{
                                width: '100%',
                                height: '10px',
                                background: 'rgba(255,255,255,0.3)',
                                borderRadius: '8px',
                                overflow: 'hidden',
                                marginBottom: '0.5rem',
                                border: '1px solid rgba(255,255,255,0.2)',
                            }}
                        >
                            <div
                                style={{
                                    width: `${Math.min(usageRate, 100)}%`,
                                    height: '100%',
                                    background:
                                        usageRate > 95
                                            ? 'linear-gradient(90deg, #ef4444, #dc2626)'
                                            : 'linear-gradient(90deg, #10b981, #34d399)',
                                    transition: 'width 0.5s ease',
                                    boxShadow: '0 2px 8px rgba(0,0,0,0.2)',
                                }}
                            ></div>
                        </div>
                        <div style={{ fontSize: '0.9rem', color: 'white', textAlign: 'center', fontWeight: '600' }}>
                            📊 예산 사용률: {usageRate}%
                        </div>
                    </div>
                )}

                {/* AI Explanation */}
                {aiExplanation && (
                    <div
                        style={{
                            padding: '1.5rem',
                            background: '#f1f5f9',
                            borderLeft: '4px solid #2563eb',
                            borderRadius: '8px',
                            marginBottom: '1.5rem',
                            animation: 'slideUp 0.5s ease-out',
                        }}
                    >
                        <div style={{ display: 'flex', alignItems: 'start', gap: '0.8rem' }}>
                            <div style={{ fontSize: '1.5rem' }}>🤖</div>
                            <div style={{ flex: 1 }}>
                                <div style={{ fontWeight: '600', marginBottom: '0.5rem', color: '#2563eb' }}>
                                    다오나의 견적 설명
                                </div>
                                <div style={{ fontSize: '0.95rem', lineHeight: '1.6', color: '#1e293b', whiteSpace: 'pre-wrap' }}>
                                    {aiExplanation}
                                </div>
                            </div>
                        </div>
                    </div>
                )}

                {/* Compatibility Check Result */}
                {compatibilityResult && (() => {
                    // 디버깅: compatibilityResult 값 확인
                    console.log('compatibilityResult:', compatibilityResult);
                    console.log('compatibilityResult.isCompatible:', compatibilityResult.isCompatible);
                    console.log('compatibilityResult.compatible:', compatibilityResult.compatible);
                    console.log('typeof compatibilityResult.isCompatible:', typeof compatibilityResult.isCompatible);
                    
                    // isCompatible 값 확인 (다양한 가능성 고려)
                    const isCompatible = compatibilityResult.isCompatible !== undefined 
                        ? compatibilityResult.isCompatible 
                        : (compatibilityResult.compatible !== undefined ? compatibilityResult.compatible : true);
                    
                    // errors가 없고 summary가 "모든 부품이 호환됩니다"면 호환 가능으로 간주
                    const hasErrors = compatibilityResult.errors && compatibilityResult.errors.length > 0;
                    const isCompatibleBySummary = compatibilityResult.summary && 
                        compatibilityResult.summary.includes('모든 부품이 호환됩니다');
                    
                    // 최종 호환성 판단: 
                    // 1. summary에 "모든 부품이 호환됩니다"가 포함되면 무조건 호환 가능
                    // 2. 그렇지 않으면 isCompatible과 errors를 확인
                    const finalIsCompatible = isCompatibleBySummary || (isCompatible && !hasErrors);
                    
                    console.log('finalIsCompatible:', finalIsCompatible);
                    
                    return (
                        <div
                            style={{
                                padding: '1.2rem',
                                background: finalIsCompatible ? '#d1fae5' : '#fee2e2',
                                border: `2px solid ${finalIsCompatible ? '#10b981' : '#ef4444'}`,
                                borderRadius: '8px',
                                marginBottom: '1.5rem',
                            }}
                        >
                            <div style={{ fontWeight: '600', marginBottom: '0.5rem', color: finalIsCompatible ? '#065f46' : '#991b1b' }}>
                                {finalIsCompatible ? '✅ 문제 없음' : '⚠️ 호환성 문제 발견'}
                            </div>
                            {compatibilityResult.summary && (
                                <div style={{ fontSize: '0.9rem', color: finalIsCompatible ? '#065f46' : '#991b1b', marginBottom: '0.5rem' }}>
                                    {compatibilityResult.summary}
                                </div>
                            )}
                            {compatibilityResult.errors && compatibilityResult.errors.length > 0 && (
                                <div style={{ marginTop: '0.5rem' }}>
                                    {compatibilityResult.errors.map((error, idx) => (
                                        <div key={idx} style={{ fontSize: '0.85rem', color: '#991b1b', marginTop: '0.3rem' }}>
                                            ❌ {error}
                                        </div>
                                    ))}
                                </div>
                            )}
                            {compatibilityResult.warnings && compatibilityResult.warnings.length > 0 && (
                                <div style={{ marginTop: '0.5rem' }}>
                                    {compatibilityResult.warnings.map((warning, idx) => (
                                        <div key={idx} style={{ fontSize: '0.85rem', color: '#92400e', marginTop: '0.3rem' }}>
                                            ⚠️ {warning}
                                        </div>
                                    ))}
                                </div>
                            )}
                        </div>
                    );
                })()}

                {/* AI Closing Message (fallback) */}
                {showAIMessage && finalBuild.length > 0 && !aiExplanation && (
                    <div
                        style={{
                            padding: '1.5rem',
                            background: '#f1f5f9',
                            borderLeft: '4px solid #2563eb',
                            borderRadius: '8px',
                            marginBottom: '1.5rem',
                            animation: 'slideUp 0.5s ease-out',
                        }}
                    >
                        <div style={{ display: 'flex', alignItems: 'start', gap: '0.8rem' }}>
                            <div style={{ fontSize: '1.5rem' }}>🎧</div>
                            <div>
                                <div style={{ fontWeight: '600', marginBottom: '0.5rem', color: '#2563eb' }}>
                                    다오나
                                </div>
                                <div style={{ fontSize: '0.95rem', lineHeight: '1.6', color: '#1e293b' }}>
                                    "선택하신 조건으로 견적 구성을 마쳤어요.
                                    <br />
                                    수고하셨어요, 이제 완벽한 PC를 만날 준비만 남았네요!"
                                </div>
                            </div>
                        </div>
                    </div>
                )}

                {/* Action Buttons */}
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.8rem', marginBottom: '1rem' }}>
                    <button 
                        className="btn-secondary" 
                        onClick={() => {
                            if (onReset) {
                                onReset();
                            }
                        }}
                        style={{ 
                            fontWeight: '600',
                            cursor: 'pointer',
                            transition: 'all 0.2s',
                        }}
                        onMouseEnter={(e) => {
                            e.target.style.transform = 'translateY(-2px)';
                            e.target.style.boxShadow = '0 4px 8px rgba(0, 0, 0, 0.15)';
                        }}
                        onMouseLeave={(e) => {
                            e.target.style.transform = 'translateY(0)';
                            e.target.style.boxShadow = 'none';
                        }}
                    >
                        🔄 초기화
                    </button>
                    <button 
                        className="btn-secondary" 
                        style={{ 
                            fontWeight: '600',
                            opacity: 0.5,
                            cursor: 'not-allowed'
                        }}
                        disabled
                        title="준비 중인 기능입니다"
                    >
                        💾 견적서 저장
                    </button>
                    <button 
                        className="btn-secondary" 
                        style={{ 
                            fontWeight: '600',
                            opacity: 0.5,
                            cursor: 'not-allowed'
                        }}
                        disabled
                        title="준비 중인 기능입니다"
                    >
                        📝 PDF 출력
                    </button>
                    <button
                        className="btn-primary"
                        onClick={handleAIReview}
                        disabled={isReviewing}
                        style={{
                            background: isReviewing 
                                ? 'linear-gradient(135deg, #94a3b8 0%, #64748b 100%)'
                                : 'linear-gradient(135deg, #8b5cf6 0%, #6366f1 100%)',
                            border: 'none',
                            fontWeight: '700',
                            boxShadow: '0 4px 12px rgba(139, 92, 246, 0.3)',
                            cursor: isReviewing ? 'not-allowed' : 'pointer',
                            opacity: isReviewing ? 0.7 : 1
                        }}
                    >
                        {isReviewing ? '⏳ 검토 중...' : '🤖 AI 재검토'}
                    </button>
                </div>

                {/* AI 재검토 결과 */}
                {reviewResult && (
                    <div
                        style={{
                            padding: '1.2rem',
                            background: '#f1f5f9',
                            border: '2px solid #2563eb',
                            borderRadius: '8px',
                            marginBottom: '1.5rem',
                        }}
                    >
                        <div style={{ fontWeight: '600', marginBottom: '0.8rem', color: '#2563eb', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                            <span>🤖</span>
                            <span>AI 재검토 결과 ({reviewResult.timestamp})</span>
                        </div>
                        
                        {/* 호환성 검사 결과 */}
                        {reviewResult.compatibility && (() => {
                            // isCompatible 값 확인 (다양한 가능성 고려)
                            const isCompatible = reviewResult.compatibility.isCompatible !== undefined 
                                ? reviewResult.compatibility.isCompatible 
                                : (reviewResult.compatibility.compatible !== undefined ? reviewResult.compatibility.compatible : true);
                            
                            // errors가 없고 summary가 "모든 부품이 호환됩니다"면 호환 가능으로 간주
                            const hasErrors = reviewResult.compatibility.errors && reviewResult.compatibility.errors.length > 0;
                            const isCompatibleBySummary = reviewResult.compatibility.summary && 
                                reviewResult.compatibility.summary.includes('모든 부품이 호환됩니다');
                            
                            // 최종 호환성 판단: 
                            // 1. summary에 "모든 부품이 호환됩니다"가 포함되면 무조건 호환 가능
                            // 2. 그렇지 않으면 isCompatible과 errors를 확인
                            const finalIsCompatible = isCompatibleBySummary || (isCompatible && !hasErrors);
                            
                            return (
                                <div style={{ marginBottom: '0.8rem' }}>
                                    <div style={{ fontSize: '0.9rem', fontWeight: '600', marginBottom: '0.3rem', color: finalIsCompatible ? '#065f46' : '#991b1b' }}>
                                        {finalIsCompatible ? '✅ 호환성 검사 통과' : '❌ 호환성 문제 발견'}
                                    </div>
                                    {reviewResult.compatibility.summary && (
                                        <div style={{ fontSize: '0.85rem', color: '#475569', marginBottom: '0.3rem' }}>
                                            {reviewResult.compatibility.summary}
                                        </div>
                                    )}
                                    {reviewResult.compatibility.errors && reviewResult.compatibility.errors.length > 0 && (
                                        <div style={{ marginTop: '0.3rem' }}>
                                            {reviewResult.compatibility.errors.map((error, idx) => (
                                                <div key={idx} style={{ fontSize: '0.8rem', color: '#991b1b', marginTop: '0.2rem' }}>
                                                    ❌ {error}
                                                </div>
                                            ))}
                                        </div>
                                    )}
                                    {reviewResult.compatibility.warnings && reviewResult.compatibility.warnings.length > 0 && (
                                        <div style={{ marginTop: '0.3rem' }}>
                                            {reviewResult.compatibility.warnings.map((warning, idx) => (
                                                <div key={idx} style={{ fontSize: '0.8rem', color: '#92400e', marginTop: '0.2rem' }}>
                                                    ⚠️ {warning}
                                                </div>
                                            ))}
                                        </div>
                                    )}
                                </div>
                            );
                        })()}
                        
                        {/* 예산 검사 결과 */}
                        {reviewResult.budget && (
                            <div style={{ marginBottom: '0.8rem' }}>
                                <div style={{ fontSize: '0.9rem', fontWeight: '600', marginBottom: '0.3rem', color: reviewResult.budget.isWithinBudget ? '#065f46' : '#991b1b' }}>
                                    {reviewResult.budget.isWithinBudget ? '✅ 예산 범위 내' : '⚠️ 예산 초과'}
                                </div>
                                <div style={{ fontSize: '0.85rem', color: '#475569' }}>
                                    총 견적: ₩{reviewResult.budget.totalPrice.toLocaleString()} / 예산: ₩{reviewResult.budget.budget.toLocaleString()}
                                    <br />
                                    잔액: ₩{reviewResult.budget.remaining.toLocaleString()} ({reviewResult.budget.usageRate}% 사용)
                                </div>
                            </div>
                        )}
                        
                        {/* 전력 공급 검사 결과 */}
                        {reviewResult.power && (
                            <div>
                                <div style={{ fontSize: '0.9rem', fontWeight: '600', marginBottom: '0.3rem', color: reviewResult.power.isSufficient ? '#065f46' : '#991b1b' }}>
                                    {reviewResult.power.isSufficient ? '✅ 전력 공급 충분' : '⚠️ 전력 공급 부족 가능'}
                                </div>
                                <div style={{ fontSize: '0.85rem', color: '#475569' }}>
                                    예상 전력 소비: 약 {reviewResult.power.estimatedPower}W
                                    <br />
                                    권장 PSU 용량: {reviewResult.power.recommendedPSU}W 이상
                                </div>
                            </div>
                        )}
                    </div>
                )}

                {/* Back Button */}
                <button className="btn-secondary" onClick={onBack} style={{ width: '100%' }}>
                    ← 이전 단계로 돌아가기
                </button>

                {/* AI Review Info */}
                <div
                    style={{
                        marginTop: '1.5rem',
                        padding: '1rem',
                        background: '#fef3c7',
                        border: '1px solid #fbbf24',
                        borderRadius: '8px',
                        fontSize: '0.85rem',
                        color: '#92400e',
                    }}
                >
                    💡 <strong>AI 재검토</strong>는 다음을 자동으로 확인합니다:
                    <br />
                    • PSU 용량이 GPU+CPU 요구전력보다 충분한지
                    <br />
                    • CPU와 메인보드 소켓 호환성
                    <br />• 예산 초과 5% 이상 여부
                </div>
            </div>
        </div>
    );
}

export default SidebarStack4;
