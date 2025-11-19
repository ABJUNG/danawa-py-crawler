import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { formatPartName } from '../utils/partNameFormatter';

// 백엔드 API 기본 URL
const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8080';

function SidebarStack3({ onProductConfirm, onBack, isActive, currentCategory, currentModel, userAnswers, aiPreferences }) {
    const [sortBy, setSortBy] = useState('recommended');
    const [selectedBrand, setSelectedBrand] = useState(null);
    const [searchQuery, setSearchQuery] = useState('');
    const [products, setProducts] = useState([]);
    const [brands, setBrands] = useState([]);
    const [isLoading, setIsLoading] = useState(false);

    // 카테고리 ID를 DB 카테고리명으로 변환
    const getCategoryName = (categoryId) => {
        const categoryMap = {
            'cpu': 'CPU',
            'cooler': '쿨러',
            'motherboard': '메인보드',
            'ram': 'RAM',
            'gpu': '그래픽카드',
            'ssd': 'SSD',
            'hdd': 'HDD',
            'psu': '파워',
            'case': '케이스'
        };
        return categoryMap[categoryId] || categoryId;
    };

    // 카테고리가 변경되면 제품 데이터 로드 (currentModel은 선택사항)
    useEffect(() => {
        if (currentCategory && isActive) {
            loadProducts();
        }
    }, [currentCategory, isActive]);

    /**
     * DB에서 제품 데이터 가져오기 (AI 점수 포함)
     * currentModel이 있으면 해당 모델명으로 필터링, 없으면 카테고리 전체 제품 가져오기
     */
    const loadProducts = async () => {
        setIsLoading(true);
        try {
            const dbCategory = getCategoryName(currentCategory);
            
            // 사용자 예산 및 용도 추출
            const budget = aiPreferences?.currentBudget || parseInt(userAnswers?.budget || '1500000');
            let purpose = '게이밍'; // 기본값
            if (aiPreferences?.usagePurposes && aiPreferences.usagePurposes.length > 0) {
                purpose = aiPreferences.usagePurposes[0];
            } else if (userAnswers?.purpose) {
                purpose = userAnswers.purpose;
            }
            
            // API 파라미터 구성
            const params = {
                category: dbCategory,
                page: 0,
                size: 100, // 최대 100개로 증가 (더 많은 제품 표시)
                sort: 'starRating,desc', // 별점 높은 순
                purpose: purpose, // 사용 목적 추가
                budget: budget // 예산 추가
            };
            
            // currentModel이 있으면 키워드 검색으로 필터링
            if (currentModel) {
                params.keyword = currentModel;
            }
            
            // 백엔드 AI 추천 API 호출
            const response = await axios.get(`${API_BASE_URL}/api/parts/ai-recommended`, { params });

            const data = response.data.content || [];
            
            // 제품 데이터 가공
            const formattedProducts = data.map(part => {
                // specs 파싱 - 타입 체크 후 조건부 파싱
                let specs = {};
                if (part.specs) {
                    try {
                        if (typeof part.specs === 'string') {
                            // 문자열인 경우에만 JSON.parse 시도
                            specs = JSON.parse(part.specs);
                        } else if (typeof part.specs === 'object') {
                            // 이미 객체인 경우 그대로 사용
                            specs = part.specs;
                        }
                    } catch (e) {
                        // JSON 파싱 실패 시 빈 객체 사용
                        console.warn('Specs 파싱 실패:', part.id, e);
                        specs = {};
                    }
                }
                
                return {
                    id: part.id,
                    name: part.name,
                    price: part.price,
                    brand: part.manufacturer || '제조사 미상',
                    tags: generateTags(part),
                    aiScore: part.aiScore || 50, // 백엔드에서 계산한 AI 점수 사용
                    stock: '재고풍부', // DB에 재고 정보가 없으므로 기본값
                    shipping: part.price >= 30000 ? '무료배송' : '유료배송',
                    reviewCount: part.reviewCount || 0,
                    starRating: part.starRating || 0,
                    image: part.imgSrc || 'https://via.placeholder.com/150x100/6366f1/ffffff?text=No+Image',
                    aiSummary: part.aiSummary, // 리뷰 요약
                    benchmarks: part.benchmarks || [], // 벤치마크 데이터
                    specs: specs
                };
            });

            setProducts(formattedProducts);

            // 브랜드 목록 추출
            const uniqueBrands = [...new Set(formattedProducts.map(p => p.brand))];
            setBrands(uniqueBrands);

        } catch (error) {
            console.error('제품 로드 실패:', error);
            alert('제품 데이터를 불러오는 데 실패했습니다.');
        } finally {
            setIsLoading(false);
        }
    };

    /**
     * 부품 태그 생성
     */
    const generateTags = (part) => {
        const tags = [];
        
        // RAM/SSD/HDD 카테고리에 대한 용량 정보 추가
        const categoryName = getCategoryName(currentCategory);
        if (categoryName === 'RAM' || categoryName === 'SSD' || categoryName === 'HDD') {
            try {
                // specs 파싱 - 타입 체크 후 조건부 파싱
                let specs = {};
                if (part.specs) {
                    if (typeof part.specs === 'string') {
                        specs = JSON.parse(part.specs);
                    } else if (typeof part.specs === 'object') {
                        specs = part.specs;
                    }
                }
                
                if (categoryName === 'RAM') {
                    // RAM: 용량 + 개수
                    if (specs.capacity) tags.push(specs.capacity);
                    if (specs.ram_count) tags.push(specs.ram_count);
                } else if (categoryName === 'SSD') {
                    // SSD: 저장 용량
                    if (specs.storage_capacity) tags.push(specs.storage_capacity);
                } else if (categoryName === 'HDD') {
                    // HDD: 디스크 용량
                    if (specs.disk_capacity) tags.push(specs.disk_capacity);
                }
            } catch (e) {
                // 스펙 파싱 실패 시 제품명에서 용량 추출 시도
                const name = part.name || '';
                
                // GB/TB 패턴 추출
                const capacityMatch = name.match(/(\d+(?:\.\d+)?)\s*(TB|GB)/i);
                if (capacityMatch) {
                    tags.push(capacityMatch[0]);
                }
                
                // RAM 개수 추출 (예: 2개, x2)
                if (categoryName === 'RAM') {
                    const countMatch = name.match(/(\d+개|\d+\s*x\s*\d+)/i);
                    if (countMatch) {
                        tags.push(countMatch[0]);
                    }
                }
            }
        }
        
        // 가격 태그
        if (part.price < 100000) tags.push('저렴함');
        else if (part.price > 500000) tags.push('고급형');
        
        // 별점 태그
        if (part.starRating >= 4.5) tags.push('최고평점');
        else if (part.starRating >= 4.0) tags.push('고평점');
        
        // 리뷰 태그
        if (part.reviewCount > 100) tags.push('인기상품');
        
        // AI 요약 태그
        if (part.aiSummary) tags.push('리뷰분석');
        
        // 벤치마크 태그
        if (part.benchmarks && part.benchmarks.length > 0) tags.push('벤치마크');
        
        return tags;
    };

    /**
     * AI 점수 계산 (백엔드에서 계산하므로 사용하지 않지만, 폴백용으로 유지)
     */
    const calculateAIScore = (part) => {
        // 백엔드에서 계산한 AI 점수가 있으면 사용
        if (part.aiScore !== undefined && part.aiScore !== null) {
            return part.aiScore;
        }
        
        // 폴백: 간단한 로컬 계산
        let score = 50; // 기본 점수
        
        // 별점 (최대 30점)
        score += (part.starRating || 0) * 6;
        
        // 리뷰 수 (최대 15점)
        const reviewScore = Math.min(part.reviewCount / 10, 15);
        score += reviewScore;
        
        // AI 요약 존재 (5점)
        if (part.aiSummary) score += 5;
        
        // 벤치마크 존재 (5점)
        if (part.benchmarks && part.benchmarks.length > 0) score += 5;
        
        return Math.min(Math.round(score), 100);
    };

    // 필터링 및 정렬
    const getFilteredAndSortedProducts = () => {
        let filtered = [...products];

        // 브랜드 필터링
        if (selectedBrand) {
            filtered = filtered.filter(p => p.brand === selectedBrand);
        }

        // 검색어 필터링
        if (searchQuery) {
            const query = searchQuery.toLowerCase();
            filtered = filtered.filter(p => 
                p.name.toLowerCase().includes(query) || 
                p.brand.toLowerCase().includes(query)
            );
        }

        // 정렬
        switch (sortBy) {
            case 'price':
                filtered.sort((a, b) => a.price - b.price);
                break;
            case 'reviews':
                filtered.sort((a, b) => b.reviewCount - a.reviewCount);
                break;
            case 'recommended':
            default:
                filtered.sort((a, b) => b.aiScore - a.aiScore);
                break;
        }

        return filtered;
    };

    const filteredProducts = getFilteredAndSortedProducts();

    const getCategoryDisplayName = (categoryId) => {
        const names = {
            cpu: 'CPU',
            gpu: '그래픽카드',
            ram: 'RAM',
            ssd: 'SSD',
            hdd: 'HDD',
            case: '케이스',
            psu: '파워',
            cooler: '쿨러',
            motherboard: '메인보드',
        };
        return names[categoryId] || categoryId.toUpperCase();
    };

    return (
        <div className={`sidebar-stack sidebar-stack-3 ${isActive ? 'slide-in' : ''}`}>
            <div className="sidebar-header">
                <button className="btn-back" onClick={onBack}>← 뒤로</button>
                <div className="sidebar-title">
                    제품 선택 - {getCategoryDisplayName(currentCategory)}
                    {currentModel && ` (${currentModel})`}
                </div>
            </div>

            <div className="sidebar-content">
                {/* 검색 & 필터 */}
                <div style={{ marginBottom: '1rem' }}>
                    <input
                        type="text"
                        placeholder="제품명 또는 브랜드로 검색..."
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                        style={{
                            width: '100%',
                            padding: '0.7rem',
                            borderRadius: '8px',
                            border: '1px solid #e2e8f0',
                            fontSize: '0.95rem',
                            marginBottom: '0.8rem'
                        }}
                    />

                    {/* 브랜드 필터 */}
                    {brands.length > 0 && (
                        <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap', marginBottom: '0.8rem' }}>
                            <button
                                onClick={() => setSelectedBrand(null)}
                                style={{
                                    padding: '0.5rem 0.9rem',
                                    borderRadius: '20px',
                                    border: '1px solid',
                                    borderColor: selectedBrand === null ? '#667eea' : '#cbd5e1',
                                    background: selectedBrand === null ? '#667eea' : 'white',
                                    color: selectedBrand === null ? 'white' : '#64748b',
                                    fontSize: '0.85rem',
                                    cursor: 'pointer',
                                    fontWeight: '500'
                                }}
                            >
                                전체
                            </button>
                            {brands.map(brand => (
                                <button
                                    key={brand}
                                    onClick={() => setSelectedBrand(brand)}
                                    style={{
                                        padding: '0.5rem 0.9rem',
                                        borderRadius: '20px',
                                        border: '1px solid',
                                        borderColor: selectedBrand === brand ? '#667eea' : '#cbd5e1',
                                        background: selectedBrand === brand ? '#667eea' : 'white',
                                        color: selectedBrand === brand ? 'white' : '#64748b',
                                        fontSize: '0.85rem',
                                        cursor: 'pointer',
                                        fontWeight: '500'
                                    }}
                                >
                                    {brand}
                                </button>
                            ))}
                        </div>
                    )}

                    {/* 정렬 옵션 */}
                    <select
                        value={sortBy}
                        onChange={(e) => setSortBy(e.target.value)}
                        style={{
                            width: '100%',
                            padding: '0.7rem',
                            borderRadius: '8px',
                            border: '1px solid #e2e8f0',
                            fontSize: '0.9rem',
                            background: 'white'
                        }}
                    >
                        <option value="recommended">AI 추천 순</option>
                        <option value="price">가격 낮은 순</option>
                        <option value="reviews">리뷰 많은 순</option>
                    </select>
                </div>

                {/* 로딩 상태 */}
                {isLoading && (
                    <div style={{ textAlign: 'center', padding: '2rem', color: '#64748b' }}>
                        <div style={{ fontSize: '2rem', marginBottom: '1rem' }}>⏳</div>
                        <div>제품 목록을 불러오는 중...</div>
                    </div>
                )}

                {/* 제품 목록 */}
                {!isLoading && filteredProducts.length === 0 && (
                    <div style={{ textAlign: 'center', padding: '2rem', color: '#64748b' }}>
                        <div style={{ fontSize: '2rem', marginBottom: '1rem' }}>🔍</div>
                        <div>검색 결과가 없습니다.</div>
                    </div>
                )}

                {/* 제품 카드 */}
                {!isLoading && filteredProducts.map((product) => (
                    <div
                        key={product.id}
                        style={{
                            border: '1px solid #e2e8f0',
                            borderRadius: '10px',
                            padding: '1rem',
                            marginBottom: '0.8rem',
                            background: 'white',
                            boxShadow: '0 1px 3px rgba(0,0,0,0.1)',
                            cursor: 'pointer',
                            transition: 'all 0.2s'
                        }}
                        onMouseEnter={(e) => {
                            e.currentTarget.style.transform = 'translateY(-2px)';
                            e.currentTarget.style.boxShadow = '0 4px 12px rgba(102, 126, 234, 0.2)';
                        }}
                        onMouseLeave={(e) => {
                            e.currentTarget.style.transform = 'translateY(0)';
                            e.currentTarget.style.boxShadow = '0 1px 3px rgba(0,0,0,0.1)';
                        }}
                        onClick={() => onProductConfirm(currentCategory, product.name, product)}
                    >
                        <div style={{ display: 'flex', gap: '1rem' }}>
                            {/* 제품 이미지 */}
                            <img
                                src={product.image}
                                alt={product.name}
                                style={{
                                    width: '100px',
                                    height: '100px',
                                    objectFit: 'cover',
                                    borderRadius: '6px',
                                    border: '1px solid #e2e8f0'
                                }}
                            />

                            {/* 제품 정보 */}
                            <div style={{ flex: 1 }}>
                                {/* AI 점수 */}
                                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '0.5rem' }}>
                                    <div style={{
                                        display: 'inline-block',
                                        background: `linear-gradient(135deg, ${product.aiScore >= 90 ? '#10b981, #34d399' : product.aiScore >= 75 ? '#667eea, #764ba2' : '#f59e0b, #f97316'})`,
                                        color: 'white',
                                        padding: '0.3rem 0.7rem',
                                        borderRadius: '20px',
                                        fontSize: '0.75rem',
                                        fontWeight: '600'
                                    }}>
                                        ✨ AI 점수 {product.aiScore}
                                    </div>
                                    <div style={{ color: '#94a3b8', fontSize: '0.8rem' }}>{product.stock}</div>
                                </div>

                                {/* 제품명 */}
                                <div style={{ 
                                    fontWeight: '600', 
                                    fontSize: '0.95rem', 
                                    marginBottom: '0.4rem', 
                                    color: '#1e293b',
                                    overflow: 'hidden',
                                    textOverflow: 'ellipsis',
                                    display: '-webkit-box',
                                    WebkitLineClamp: 3,
                                    WebkitBoxOrient: 'vertical',
                                    lineHeight: '1.4em',
                                    minHeight: '4.2em'
                                }}>
                                    {product.name}
                                </div>

                                {/* 브랜드 & 태그 */}
                                <div style={{ display: 'flex', gap: '0.4rem', flexWrap: 'wrap', marginBottom: '0.5rem' }}>
                                    <span style={{
                                        fontSize: '0.75rem',
                                        padding: '0.2rem 0.6rem',
                                        borderRadius: '4px',
                                        background: '#f1f5f9',
                                        color: '#475569',
                                        fontWeight: '500'
                                    }}>
                                        {product.brand}
                                    </span>
                                    {product.tags.slice(0, 3).map((tag, idx) => (
                                        <span
                                            key={idx}
                                            style={{
                                                fontSize: '0.7rem',
                                                padding: '0.2rem 0.5rem',
                                                borderRadius: '4px',
                                                background: '#dbeafe',
                                                color: '#1e40af'
                                            }}
                                        >
                                            {tag}
                                        </span>
                                    ))}
                                    {/* RAM/SSD/HDD 용량 표시 */}
                                    {(() => {
                                        const categoryName = getCategoryName(currentCategory);
                                        if (['RAM', 'SSD', 'HDD'].includes(categoryName)) {
                                            const formatted = formatPartName(product.name, categoryName);
                                            if (formatted.capacity || formatted.package) {
                                                return (
                                                    <span style={{
                                                        fontSize: '0.75rem',
                                                        padding: '0.2rem 0.6rem',
                                                        borderRadius: '4px',
                                                        background: '#dcfce7',
                                                        color: '#166534',
                                                        fontWeight: '600'
                                                    }}>
                                                        {formatted.capacity || formatted.package}
                                                    </span>
                                                );
                                            }
                                        }
                                        return null;
                                    })()}
                                </div>

                                {/* 가격 & 리뷰 */}
                                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                    <div style={{ fontSize: '1.1rem', fontWeight: '700', color: '#667eea' }}>
                                        {product.price.toLocaleString()}원
                                    </div>
                                    <div style={{ fontSize: '0.85rem', color: '#64748b' }}>
                                        ⭐ {product.starRating.toFixed(1)} ({product.reviewCount})
                                    </div>
                                </div>

                                {/* AI 리뷰 요약 (있는 경우) */}
                                {product.aiSummary && (
                                    <div style={{
                                        marginTop: '0.6rem',
                                        padding: '0.6rem',
                                        background: '#f8fafc',
                                        borderRadius: '6px',
                                        fontSize: '0.8rem',
                                        color: '#475569',
                                        lineHeight: '1.5'
                                    }}>
                                        <strong>AI 리뷰:</strong> {product.aiSummary.substring(0, 80)}...
                                    </div>
                                )}

                                {/* 벤치마크 (있는 경우) */}
                                {product.benchmarks && product.benchmarks.length > 0 && (
                                    <div style={{
                                        marginTop: '0.6rem',
                                        display: 'flex',
                                        gap: '0.5rem',
                                        flexWrap: 'wrap'
                                    }}>
                                        {product.benchmarks.slice(0, 3).map((bench, idx) => (
                                            <span key={idx} style={{
                                                fontSize: '0.75rem',
                                                padding: '0.2rem 0.5rem',
                                                borderRadius: '4px',
                                                background: '#fef3c7',
                                                color: '#92400e'
                                            }}>
                                                {bench.testName}: {bench.value}
                                            </span>
                                        ))}
                                    </div>
                                )}
                            </div>
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
}

export default SidebarStack3;
