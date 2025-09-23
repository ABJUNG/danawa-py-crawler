import React, { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import './App.css';

const CATEGORIES = ['CPU', '쿨러', '메인보드', 'RAM', '그래픽카드', 'SSD', 'HDD', '파워', '케이스'];
const ITEMS_PER_PAGE = 20;

function App() {
  // --- State Variables ---
  const [parts, setParts] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [selectedCategory, setSelectedCategory] = useState('CPU');
  
  const [availableFilters, setAvailableFilters] = useState({});
  const [selectedFilters, setSelectedFilters] = useState({});
  
  const [searchTerm, setSearchTerm] = useState('');
  const [history, setHistory] = useState([]);
  const [isHistoryVisible, setIsHistoryVisible] = useState(false);
  const [currentPage, setCurrentPage] = useState(0);
  const [totalPages, setTotalPages] = useState(0);
  const [sortOption, setSortOption] = useState('createdAt,desc');

  // --- API 호출 함수 ---
  const fetchParts = useCallback(async (category, filters, keyword, page, sort) => {
    setIsLoading(true);
    try {
      const params = new URLSearchParams();
      params.append('category', category);
      params.append('page', page);
      params.append('size', ITEMS_PER_PAGE);
      params.append('sort', sort);

      for (const key in filters) {
        if (filters[key] && filters[key].length > 0) {
            filters[key].forEach(value => {
                params.append(key, value);
            });
        }
      }
      
      if (keyword) {
        params.append('keyword', keyword);
      }
      
      const response = await axios.get(`/api/parts?${params.toString()}`);
      
      setParts(response.data.content);
      setTotalPages(response.data.totalPages);

      if (keyword) {
        const newHistory = [keyword, ...history.filter(item => item !== keyword)];
        setHistory(newHistory.slice(0, 10));
      }
    } catch (error) {
      console.error("데이터를 불러오는 중 오류가 발생했습니다.", error);
      setParts([]);
      setTotalPages(0);
    } finally {
      setIsLoading(false);
    }
  }, [history]);

  // --- useEffect Hooks ---
  useEffect(() => {
    const savedHistory = localStorage.getItem('searchHistory');
    if (savedHistory) {
      setHistory(JSON.parse(savedHistory));
    }
  }, []);

  useEffect(() => {
    localStorage.setItem('searchHistory', JSON.stringify(history));
  }, [history]);

  useEffect(() => {
    const loadCategoryData = async () => {
      try {
        const filtersRes = await axios.get(`/api/filters?category=${selectedCategory}`);
        setAvailableFilters(filtersRes.data);
      } catch (error) {
        console.error("필터 목록을 불러오는 중 오류가 발생했습니다.", error);
        setAvailableFilters({});
      }
      
      setSelectedFilters({});
      setCurrentPage(0);
      setSearchTerm('');
      fetchParts(selectedCategory, {}, '', 0, sortOption);
    };
    loadCategoryData();
  }, [selectedCategory, sortOption, fetchParts]);

  // --- Event Handlers ---
  const handleCategoryClick = (category) => { setSelectedCategory(category); };

  const handleFilterChange = (filterType, value) => {
    const newFilters = { ...selectedFilters };
    const currentValues = newFilters[filterType] || [];

    if (currentValues.includes(value)) {
      newFilters[filterType] = currentValues.filter(item => item !== value);
    } else {
      newFilters[filterType] = [...currentValues, value];
    }
    
    if (newFilters[filterType].length === 0) {
      delete newFilters[filterType];
    }

    setSelectedFilters(newFilters);
    setCurrentPage(0);
    fetchParts(selectedCategory, newFilters, '', 0, sortOption);
  };

  const handleSearch = () => {
    setCurrentPage(0);
    fetchParts(selectedCategory, selectedFilters, searchTerm, 0, sortOption);
  };
  
  const handleHistoryClick = (keyword) => {
    setSearchTerm(keyword);
    setCurrentPage(0);
    fetchParts(selectedCategory, selectedFilters, keyword, 0, sortOption);
  };

  const handleDeleteHistory = (itemToDelete) => { setHistory(history.filter(item => item !== itemToDelete)); };
  
  const handlePageChange = (pageNumber) => {
    setCurrentPage(pageNumber);
    fetchParts(selectedCategory, selectedFilters, searchTerm, pageNumber, sortOption);
  };
  
  const handleSortChange = (sortValue) => {
    setSortOption(sortValue);
    setCurrentPage(0);
    fetchParts(selectedCategory, selectedFilters, searchTerm, 0, sortValue);
  };

  const renderFilters = () => {
    const filterMap = {
      manufacturers: '제조사', socketTypes: '소켓 타입', coreTypes: '코어 종류',
      ramCapacities: 'RAM 용량', chipsets: '칩셋 제조사',
    };

    return Object.keys(filterMap).map(filterKey => {
      if (availableFilters[filterKey] && availableFilters[filterKey].length > 0) {
        return (
          <div key={filterKey} className="filter-group">
            <strong className="filter-title">{filterMap[filterKey]}</strong>
            <div className="filter-options">
              {availableFilters[filterKey].sort().map(value => (
                <label key={value} className="filter-label">
                  <input
                    type="checkbox"
                    checked={(selectedFilters[filterKey] || []).includes(value)}
                    onChange={() => handleFilterChange(filterKey, value)}
                  /> {value}
                </label>
              ))}
            </div>
          </div>
        );
      }
      return null;
    });
  };

  // --- JSX Rendering ---
  return (
    <div className="app-container">
      <h1>🖥️ PC 부품 가격 정보 (다나와)</h1>

      <nav className="category-nav">
        {CATEGORIES.map(category => (
          <button
            key={category}
            className={`category-btn ${selectedCategory === category ? 'active' : ''}`}
            onClick={() => handleCategoryClick(category)}
          >
            {category}
          </button>
        ))}
      </nav>
      
      <div className="controls-container-grid">
        {renderFilters()}

        <div className="sort-container">
          <strong className="filter-title">정렬</strong>
          <select 
            className="filter-select"
            value={sortOption}
            onChange={(e) => handleSortChange(e.target.value)}
          >
            <option value="createdAt,desc">신상품순</option>
            <option value="price,asc">낮은가격순</option>
            <option value="price,desc">높은가격순</option>
          </select>
        </div>
      </div>

      <div className="search-container">
        <div className="search-bar">
          <input
            type="text"
            placeholder={`${selectedCategory} 내에서 검색...`}
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
            onFocus={() => setIsHistoryVisible(true)}
            onBlur={() => setTimeout(() => setIsHistoryVisible(false), 150)}
          />
          <button onClick={handleSearch}>검색</button>
        </div>
        
        {isHistoryVisible && history.length > 0 && (
          <div className="history-container">
            <ul className="history-list">
              {history.map((item, index) => (
                <li key={index} className="history-item">
                  <span className="history-term" onClick={() => handleHistoryClick(item)}>{item}</span>
                  <button className="delete-btn" onClick={() => handleDeleteHistory(item)}>X</button>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>

      {isLoading ? (
        <div className="spinner-container"><div className="spinner"></div></div>
      ) : (
        <div className="parts-list">
          {parts.map(part => (
            <a key={part.id} href={part.link} target="_blank" rel="noopener noreferrer" className="card-link">
              <div className="part-card">
                <img src={part.imgSrc} alt={part.name} className="part-image" />
                <div className="part-info">
                  <h2 className="part-name">{part.name}</h2>
                  <p className="part-price">{part.price.toLocaleString()}원</p>
                </div>
              </div>
            </a>
          ))}
        </div>
      )}
      
      <div className="pagination-container">
        {totalPages > 0 && Array.from({ length: totalPages }, (_, i) => i).map(pageNumber => (
          <button
            key={pageNumber}
            onClick={() => handlePageChange(pageNumber)}
            className={`page-btn ${currentPage === pageNumber ? 'active' : ''}`}
          >
            {pageNumber + 1}
          </button>
        ))}
      </div>
    </div>
  );
}

export default App;