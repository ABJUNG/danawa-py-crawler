    import React from 'react';
    import './ComparisonModal.css';

    const ComparisonModal = ({ products, onClose, filterLabels, filterOrderMap }) => {
    if (!products || products.length === 0) {
        return null;
    }

    // 비교할 상품들의 카테고리를 확인 (모두 동일 카테고리)
    const category = products[0].category;
    // 해당 카테고리에 맞는 스펙 키 목록을 App.js로부터 받아옴
    const specKeys = filterOrderMap[category] || [];

    return (
        <div className="modal-overlay" onClick={onClose}>
        <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <button className="modal-close-btn" onClick={onClose}>×</button>
            <h2>상품 비교 - {category}</h2>

            <div className="comparison-table-container">
            <table className="comparison-table">
                <thead>
                <tr>
                    <th className="sticky-header">항목</th>
                    {products.map(product => (
                    <th key={product.id}>
                        <img 
                        src={product.imgSrc || 'https://img.danawa.com/new/noData/img/noImg_160.gif'} 
                        alt={product.name} 
                        className="product-compare-image"
                        />
                        <a href={product.link} target="_blank" rel="noopener noreferrer">
                        {product.name}
                        </a>
                    </th>
                    ))}
                </tr>
                </thead>
                <tbody>
                {/* 가격 및 리뷰 정보 */}
                <tr className="main-info">
                    <td>가격</td>
                    {products.map(product => (
                    <td key={product.id} className="price">{product.price.toLocaleString()}원</td>
                    ))}
                </tr>
                <tr className="main-info">
                    <td>의견/평점</td>
                    {products.map(product => (
                    <td key={product.id}>
                        의견 {product.reviewCount?.toLocaleString() || 0} | 
                        ⭐ {product.starRating || 'N/A'} ({product.ratingReviewCount?.toLocaleString() || 0})
                    </td>
                    ))}
                </tr>

                {/* [수정] 동적으로 해당 카테고리의 상세 스펙만 표시 */}
                {specKeys.map(key => {
                    // 제조사는 이름에 포함되므로 중복 표시 방지
                    if (key === 'manufacturer') return null;

                    // 적어도 한 개의 상품이라도 해당 스펙 값이 있는 경우에만 행을 표시
                    const hasValue = products.some(p => p[key]);
                    if (!hasValue) return null;

                    return (
                        <tr key={key}>
                        <td>{filterLabels[key] || key}</td>
                        {products.map(product => (
                            <td key={product.id}>
                            {product[key] ? String(product[key]).toLocaleString() : '-'}
                            </td>
                        ))}
                        </tr>
                    );
                })}
                </tbody>
            </table>
            </div>
        </div>
        </div>
    );
    };

    export default ComparisonModal;

