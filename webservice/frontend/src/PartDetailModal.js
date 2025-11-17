import React, { useState, useEffect } from 'react';
import './PartDetailModal.css'; // (다음 단계에서 이 CSS 파일을 만듭니다)

/**
 * 스펙 JSON을 파싱하여 상세 목록을 만드는 헬퍼 함수
 * @param {string} specsJson - part.specs (JSON 문자열)
 * @param {object} filterLabels - App.js의 FILTER_LABELS 객체
 */

const parseSpecs = (specsJson, filterLabels) => {
    if (!specsJson) {
        return []; // 스펙 정보가 없음
    }
    try {
        const parsed = JSON.parse(specsJson);
        // JSON 객체를 [key, value] 배열로 변환
        return Object.entries(parsed)
            .map(([key, value]) => {
                // filterLabels에서 예쁜 이름(예: 'cpu_series' -> 'CPU 시리즈')을 찾음
                const label = filterLabels[key] || key; 
                return { key: label, value: value };
            })
            .filter(item => item.value); // 값이 없는 항목은 제외
    } catch (e) {
        console.error("Failed to parse specs JSON in Modal:", e, specsJson);
        return [];
    }
};

function PartDetailModal({ part, onClose, filterLabels }) {
    // part.specs (JSON 문자열)를 상세 스펙 목록(배열)으로 변환
    const detailedSpecs = parseSpecs(part.specs, filterLabels);
    // --- 👇 [신규] 벤치마크 데이터가 있는지 확인 ---
    const hasBenchmarks = part.benchmarks && part.benchmarks.length > 0;

    return (
        <div className="modal-backdrop" onClick={onClose}>
            <div className="modal-content" onClick={(e) => e.stopPropagation()}>
                <button className="modal-close-btn" onClick={onClose}>×</button>
                
                <div className="modal-body">
                    <div className="modal-image-container">
                        <img 
                            src={part.imgSrc || 'https://img.danawa.com/new/noData/img/noImg_160.gif'} 
                            alt={part.name} 
                            className="modal-image" 
                        />
                    </div>
                    
                    <div className="modal-info-container">
                        <h2 className="modal-title">{part.name}</h2>
                        <h3 className="modal-price">{part.price.toLocaleString()}원</h3>
                        
                        {/* 1. 상세 스펙 섹션 */}
                        <div className="modal-section">
                            <h4>상세 스펙</h4>
                            <ul className="spec-list">
                                {detailedSpecs.length > 0 ? (
                                    detailedSpecs.map(spec => (
                                        <li key={spec.key} className="spec-item">
                                            <strong>{spec.key}:</strong> {spec.value}
                                        </li>
                                    ))
                                ) : (
                                    <li>상세 스펙 정보가 없습니다.</li>
                                )}
                            </ul>
                        </div>

                                {/* --- 👇 [신규] 벤치마크 섹션 추가 --- */}
                                {/* 벤치마크 데이터가 있을 때만 이 섹션을 보여줍니다. */}
                                {hasBenchmarks && (
                                    <div className="modal-section">
                                        <h4>벤치마크 정보</h4>
                                        <ul className="spec-list"> {/* 상세 스펙과 동일한 CSS 재사용 */}
                                            {part.benchmarks.map((bench, index) => (
                                                <li key={index} className="spec-item">
                                                    <strong>
                                                        {/* 예: Cinebench R23 (Multi) */}
                                                        {bench.testName} {bench.testVersion} 
                                                        {bench.scenario ? ` (${bench.scenario})` : ''}
                                                    </strong> 
                                                    <span>
                                                        {/* 예: 14500 pts */}
                                                        {bench.value.toLocaleString()} {bench.unit}
                                                    </span>
                                                </li>
                                            ))}
                                        </ul>
                                    </div>
                                )}

                        {/* 2. 퀘이사존 AI 요약 섹션 */}
                        <div className="modal-section">
                            <h4>퀘이사존 AI 요약</h4>
                            {part.aiSummary ? (
                                <p className="ai-summary">{part.aiSummary}</p>
                            ) : (
                                <p className="ai-summary-loading">AI 요약 정보가 아직 없습니다. (요약 스크립트 실행 필요)</p>
                            )}
                        </div>

                        {/* 3. 다나와 링크 버튼 */}
                        <a 
                            href={part.link} 
                            target="_blank" 
                            rel="noopener noreferrer" 
                            className="danawa-link-btn"
                        >
                            다나와에서 가격 비교하기
                        </a>
                    </div>
                </div>
            </div>
        </div>
    );
}

export default PartDetailModal;