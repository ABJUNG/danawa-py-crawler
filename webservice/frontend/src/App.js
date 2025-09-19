import React, { useState, useEffect } from 'react';
import axios from 'axios';
import './App.css';

const CATEGORIES = ['CPU', '쿨러', '메인보드', 'RAM', '그래픽카드', 'SSD', 'HDD', '파워', '케이스'];

function App() {
  // --- State Variables ---
  const [parts, setParts] = useState([]);
  const [selectedCategory, setSelectedCategory] = useState('CPU');
  const [manufacturers, setManufacturers] = useState([]);
  const [selectedManufacturer, setSelectedManufacturer] = useState('');
  const [searchTerm, setSearchTerm] = useState('');
  const [history, setHistory] = useState([]);
  const [isHistoryVisible, setIsHistoryVisible] = useState(false);

  // --- useEffect Hooks ---

  // 앱 로딩 시 로컬 스토리지에서 히스토리 불러오기
  useEffect(() => {
    const savedHistory = localStorage.getItem('searchHistory');
    if (savedHistory) {
      setHistory(JSON.parse(savedHistory));
    }
  }, []);

  // 히스토리 변경 시 로컬 스토리지에 저장하기
  useEffect(() => {
    localStorage.setItem('searchHistory', JSON.stringify(history));
  }, [history]);

  // 선택된 카테고리가 바뀔 때마다 데이터(부품, 제조사) 새로 불러오기
  useEffect(() => {
    const fetchData = async () => {
      try {
        const partsRes = await axios.get(`/api/parts?category=${selectedCategory}`);
        setParts(partsRes.data);

        const manuRes = await axios.get(`/api/manufacturers?category=${selectedCategory}`);
        setManufacturers(manuRes.data);
      } catch (error) {
        console.error("데이터를 불러오는 중 오류가 발생했습니다.", error);
      }
    };

    fetchData();
    setSelectedManufacturer(''); // 카테고리 변경 시 제조사 선택 초기화
    setSearchTerm(''); // 카테고리 변경 시 검색어 초기화
  }, [selectedCategory]);

  // --- Event Handlers ---

  // 카테고리 버튼 클릭
  const handleCategoryClick = (category) => {
    setSelectedCategory(category);
  };

  // 제조사 선택
  const handleManufacturerChange = async (manufacturer) => {
    setSelectedManufacturer(manufacturer);
    // 제조사 필터링 API 호출
    const res = await axios.get(`/api/parts?category=${selectedCategory}&manufacturer=${manufacturer}`);
    setParts(res.data);
  };

  // 검색 버튼 클릭
  const handleSearch = async () => {
    try {
      // 검색 API 호출
      const res = await axios.get(`/api/parts/search?category=${selectedCategory}&keyword=${searchTerm}`);
      setParts(res.data);
      // 히스토리 추가
      if (searchTerm) {
        const newHistory = [searchTerm, ...history.filter(item => item !== searchTerm)];
        setHistory(newHistory.slice(0, 10));
      }
    } catch (error) {
      console.error("검색 중 오류가 발생했습니다.", error);
    }
  };

  // 히스토리 클릭
  const handleHistoryClick = (keyword) => {
    setSearchTerm(keyword);
    // 히스토리 키워드로 검색 실행
    handleSearch();
  };

  // 히스토리 삭제
  const handleDeleteHistory = (itemToDelete) => {
    setHistory(history.filter(item => item !== itemToDelete));
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
                  <span className="history-term" onClick={() => handleHistoryClick(item)}>
                    {item}
                  </span>
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
    </div>
  );
}

export default App;