import React, { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import './App.css';

const CATEGORIES = ['CPU', '쿨러', '메인보드', 'RAM', '그래픽카드', 'SSD', 'HDD', '파워', '케이스'];
const ITEMS_PER_PAGE = 20;

function App() {
  // --- State Variables ---
  const [parts, setParts] = useState([]);
  const [selectedCategory, setSelectedCategory] = useState('CPU');
  const [manufacturers, setManufacturers] = useState([]);
  const [selectedManufacturer, setSelectedManufacturer] = useState('');
  const [searchTerm, setSearchTerm] = useState('');
  const [history, setHistory] = useState([]);
  const [isHistoryVisible, setIsHistoryVisible] = useState(false);
  const [currentPage, setCurrentPage] = useState(0);
  const [totalPages, setTotalPages] = useState(0);
  const [sortOption, setSortOption] = useState('createdAt,desc'); // 정렬 옵션 state 추가

  // --- API 호출 함수 ---
  const fetchParts = useCallback(async (category, manufacturer, keyword, page, sort) => {
    try {
      const params = new URLSearchParams({
        category: category,
        page: page,
        size: ITEMS_PER_PAGE,
        sort: sort, // API 요청에 sort 파라미터 추가
      });

      let url = '/api/parts';
      if (keyword) {
        url = '/api/parts/search';
        params.append('keyword', keyword);
      } else if (manufacturer) {
        params.append('manufacturer', manufacturer);
      }
      
      const response = await axios.get(`${url}?${params.toString()}`);
      
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
    }
  }, [history]); // useCallback의 의존성 배열에 history 추가

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
        const manuRes = await axios.get(`/api/manufacturers?category=${selectedCategory}`);
        setManufacturers(manuRes.data);
      } catch (error) {
        console.error("제조사 목록을 불러오는 중 오류가 발생했습니다.", error);
        setManufacturers([]);
      }
      setCurrentPage(0);
      setSelectedManufacturer('');
      setSearchTerm('');
      // 카테고리 변경 시 현재 정렬 옵션을 유지하며 데이터 요청
      fetchParts(selectedCategory, '', '', 0, sortOption); 
    };
    loadCategoryData();
  }, [selectedCategory, fetchParts]);


  // --- Event Handlers ---

  const handleCategoryClick = (category) => {
    setSelectedCategory(category);
  };

  const handleManufacturerChange = (manufacturer) => {
    setSelectedManufacturer(manufacturer);
    setCurrentPage(0);
    fetchParts(selectedCategory, manufacturer, '', 0, sortOption);
  };

  const handleSearch = () => {
    setCurrentPage(0);
    fetchParts(selectedCategory, selectedManufacturer, searchTerm, 0, sortOption);
  };
  
  const handleHistoryClick = (keyword) => {
    setSearchTerm(keyword);
    setCurrentPage(0);
    fetchParts(selectedCategory, selectedManufacturer, keyword, 0, sortOption);
  };

  const handleDeleteHistory = (itemToDelete) => {
    setHistory(history.filter(item => item !== itemToDelete));
  };
  
  const handlePageChange = (pageNumber) => {
    setCurrentPage(pageNumber);
    fetchParts(selectedCategory, selectedManufacturer, searchTerm, pageNumber, sortOption);
  };
  
  const handleSortChange = (sortValue) => {
    setSortOption(sortValue);
    setCurrentPage(0);
    fetchParts(selectedCategory, selectedManufacturer, searchTerm, 0, sortValue);
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
      
      <div className="controls-container">
        <div className="filter-container">
          <select
            className="filter-select"
            value={selectedManufacturer}
            onChange={(e) => handleManufacturerChange(e.target.value)}
          >
            <option value="">-- 제조사 전체 --</option>
            {manufacturers.map(manu => (
              <option key={manu} value={manu}>{manu}</option>
            ))}
          </select>
        </div>
        
        <div className="sort-container">
          <select 
            className="sort-select"
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

      <div className="parts-list">
        {parts.map(part => (
          <a key={part.id} href={part.link} target="_blank" rel="noopener noreferrer" className="part-card">
            <img src={part.imgSrc} alt={part.name} className="part-image" />
            <div className="part-info">
              <h2 className="part-name">{part.name}</h2>
              <p className="part-price">{part.price.toLocaleString()}원</p>
            </div>
          </a>
        ))}
      </div>
      
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