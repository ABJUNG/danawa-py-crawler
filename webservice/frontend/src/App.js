import React, { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import './App.css';
import ComparisonModal from './ComparisonModal'; // ComparisonModal import

const CATEGORIES = ['CPU', '쿨러', '메인보드', 'RAM', '그래픽카드', 'SSD', 'HDD', '파워', '케이스'];
const ITEMS_PER_PAGE = 20;

// (FILTER_LABELS, FILTER_ORDER_MAP, generateSpecString 함수는 기존과 동일)
const FILTER_LABELS = {
  manufacturer: '제조사',
  codename: '코드네임',
  cpuSeries: 'CPU 시리즈',
  cpuClass: 'CPU 종류',
  socket: '소켓 구분',
  cores: '코어 수',
  threads: '스레드 수',
  integratedGraphics: '내장그래픽 탑재 여부',
  productType: '제품 분류',
  coolingMethod: '냉각 방식',
  airCoolingForm: '공랭 형태',
  coolerHeight: '쿨러 높이',
  radiatorLength: '라디에이터',
  fanSize: '팬 크기',
  fanConnector: '팬 커넥터',
  deviceType: '사용 장치',
  productClass: '제품 분류',
  capacity: '메모리 용량',
  ramCount: '램 개수',
  clockSpeed: '동작 클럭(대역폭)',
  ramTiming: '램 타이밍',
  heatsinkPresence: '히트싱크',
  chipset: '세부 칩셋',
  formFactor: '폼팩터',
  memorySpec: '메모리 종류',
  memorySlots: '메모리 슬롯',
  vgaConnection: 'VGA 연결',
  m2Slots: 'M.2',
  wirelessLan: '무선랜 종류',
  nvidiaChipset: 'NVIDIA 칩셋',
  amdChipset: 'AMD 칩셋',
  intelChipset: '인텔 칩셋',
  gpuInterface: '인터페이스',
  gpuMemoryCapacity: '메모리 용량',
  outputPorts: '출력 단자',
  recommendedPsu: '권장 파워용량',
  fanCount: '팬 개수',
  gpuLength: '가로(길이)',
  ssdInterface: '인터페이스',
  memoryType: '메모리 타입',
  ramMounted: 'RAM 탑재',
  sequentialRead: '순차읽기',
  sequentialWrite: '순차쓰기',
  hddSeries: '시리즈 구분',
  diskCapacity: '디스크 용량',
  rotationSpeed: '회전수',
  bufferCapacity: '버퍼 용량',
  hddWarranty: 'A/S 정보',
  caseSize: '케이스 크기',
  supportedBoard: '지원보드 규격',
  sidePanel: '측면 개폐 방식',
  psuLength: '파워 장착 길이',
  vgaLength: 'VGA 길이',
  cpuCoolerHeightLimit: 'CPU쿨러 높이',
  ratedOutput: '정격출력',
  eightyPlusCert: '80PLUS인증',
  etaCert: 'ETA인증',
  cableConnection: '케이블연결',
  pcie16pin: 'PCIe 16핀(12+4)',
};

const FILTER_ORDER_MAP = {
  CPU: ['manufacturer', 'codename', 'cpuSeries', 'cpuClass', 'socket', 'cores', 'threads', 'integratedGraphics'],
  쿨러: ['manufacturer', 'productType', 'coolingMethod', 'airCoolingForm', 'coolerHeight', 'radiatorLength', 'fanSize', 'fanConnector'],
  메인보드: ['manufacturer', 'socket', 'chipset', 'formFactor', 'memorySpec', 'memorySlots', 'vgaConnection', 'm2Slots', 'wirelessLan'],
  RAM: ['manufacturer', 'deviceType', 'productClass', 'capacity', 'ramCount', 'clockSpeed', 'ramTiming', 'heatsinkPresence'],
  그래픽카드: ['manufacturer', 'nvidiaChipset', 'amdChipset', 'intelChipset', 'gpuInterface', 'gpuMemoryCapacity', 'outputPorts', 'recommendedPsu', 'fanCount', 'gpuLength'],
  SSD: ['manufacturer', 'formFactor', 'ssdInterface', 'capacity', 'memoryType', 'ramMounted', 'sequentialRead', 'sequentialWrite'],
  HDD: ['manufacturer', 'hddSeries', 'diskCapacity', 'rotationSpeed', 'bufferCapacity', 'hddWarranty'],
  케이스: ['manufacturer', 'productType', 'caseSize', 'supportedBoard', 'sidePanel', 'psuLength', 'vgaLength', 'cpuCoolerHeightLimit'],
  파워: ['manufacturer', 'productType', 'ratedOutput', 'eightyPlusCert', 'etaCert', 'cableConnection', 'pcie16pin']
};

const generateSpecString = (part) => {
  let specs = [];
  switch (part.category) {
    case 'CPU': specs = [part.manufacturer, part.socket, part.cores, part.threads, part.cpuSeries, part.codename]; break;
    case '쿨러': specs = [part.manufacturer, part.coolingMethod, part.airCoolingForm, part.fanSize, part.radiatorLength]; break;
    case '메인보드': specs = [part.manufacturer, part.socket, part.chipset, part.formFactor, part.memorySpec]; break;
    case 'RAM': specs = [part.manufacturer, part.productClass, part.capacity, part.clockSpeed, part.ramTiming]; break;
    case '그래픽카드': specs = [part.manufacturer, (part.nvidiaChipset || part.amdChipset || part.intelChipset), part.gpuMemoryCapacity, part.gpuLength]; break;
    case 'SSD': specs = [part.manufacturer, part.formFactor, part.ssdInterface, part.capacity, part.sequentialRead]; break;
    case 'HDD': specs = [part.manufacturer, part.diskCapacity, part.rotationSpeed, part.bufferCapacity]; break;
    case '케이스': specs = [part.manufacturer, part.caseSize, part.supportedBoard, part.cpuCoolerHeightLimit, part.vgaLength]; break;
    case '파워': specs = [part.manufacturer, part.ratedOutput, part.eightyPlusCert, part.cableConnection]; break;
    default: return '';
  }
  return specs.filter(Boolean).join(' / ');
};


function App() {
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
  const [comparisonList, setComparisonList] = useState([]);
  const [isModalOpen, setIsModalOpen] = useState(false);
  
  // --- [추가] 1. 다크/라이트 모드 상태 관리 ---
  const [theme, setTheme] = useState('light');

  // --- [추가] 2. 테마 변경 함수 ---
  const toggleTheme = () => {
    const newTheme = theme === 'light' ? 'dark' : 'light';
    setTheme(newTheme);
    localStorage.setItem('theme', newTheme); // 사용자의 테마 선택을 저장
  };

  // --- [추가] 3. 컴포넌트 첫 로딩 시, 저장된 테마나 시스템 설정 확인 ---
  useEffect(() => {
    const savedTheme = localStorage.getItem('theme');
    const prefersDark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
    if (savedTheme) {
      setTheme(savedTheme);
    } else if (prefersDark) {
      setTheme('dark');
    }
  }, []);

   // --- [추가] 아코디언 UI를 위한 상태 ---
  // 처음에는 첫 번째 필터가 열려있도록 'manufacturer'로 초기화
  const [openFilter, setOpenFilter] = useState('manufacturer'); 

  // --- [추가] 아코디언 토글 핸들러 ---
  const handleFilterToggle = (filterKey) => {
    // 이미 열려있는 필터를 다시 클릭하면 닫고, 다른 필터를 클릭하면 새로 연다.
    setOpenFilter(prevOpenFilter => prevOpenFilter === filterKey ? null : filterKey);
  };


  const handleAddToCompare = (e, partToAdd) => {
    e.preventDefault();
    e.stopPropagation();

    setComparisonList(prevList => {
      if (prevList.find(p => p.id === partToAdd.id)) {
        return prevList.filter(p => p.id !== partToAdd.id);
      }
      if (prevList.length > 0 && prevList[0].category !== partToAdd.category) {
        alert('같은 카테고리의 상품만 비교할 수 있습니다.');
        return prevList;
      }
      if (prevList.length < 3) {
        return [...prevList, partToAdd];
      }
      alert('최대 3개의 상품만 비교할 수 있습니다.');
      return prevList;
    });
  };

  // (이하 데이터 로딩 및 필터링 관련 함수들은 기존과 동일)
  const handleRemoveFromCompare = (partId) => {
    setComparisonList(prevList => prevList.filter(p => p.id !== partId));
  };

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

      if (keyword && !history.includes(keyword)) {
        const newHistory = [keyword, ...history];
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
      setIsLoading(true);
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
    };

    loadCategoryData().then(() => {
        fetchParts(selectedCategory, {}, '', 0, sortOption);
    });
  }, [selectedCategory, sortOption, fetchParts]);

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
    fetchParts(selectedCategory, newFilters, searchTerm, 0, sortOption);
  };

  const handleSearch = (e) => {
    e.preventDefault();
    setCurrentPage(0);
    fetchParts(selectedCategory, selectedFilters, searchTerm, 0, sortOption);
  };
  
  const handleHistoryClick = (keyword) => {
    setSearchTerm(keyword);
    setCurrentPage(0);
    fetchParts(selectedCategory, selectedFilters, keyword, 0, sortOption);
  };

  const handleDeleteHistory = (e, itemToDelete) => {
    e.stopPropagation();
    setHistory(history.filter(item => item !== itemToDelete));
  };
  
  const handlePageChange = (pageNumber) => {
    setCurrentPage(pageNumber);
    fetchParts(selectedCategory, selectedFilters, searchTerm, pageNumber, sortOption);
  };
  
  const handleSortChange = (sortValue) => {
    setSortOption(sortValue);
  };

  const renderFilters = () => {
    const filterOrder = FILTER_ORDER_MAP[selectedCategory] || Object.keys(availableFilters);

    return filterOrder.map(filterKey => {
      const values = availableFilters[filterKey];
      if (!values || values.length === 0) { return null; }
      
      const label = FILTER_LABELS[filterKey] || filterKey;
      const isOpen = openFilter === filterKey; // 현재 필터가 열려있는지 확인

      if (['fanSize', 'capacity', 'gpuMemoryCapacity', 'diskCapacity'].includes(filterKey)) {
        values.sort((a, b) => {
            const numA = parseInt(a.replace(/[^0-9]/g, ''), 10);
            const numB = parseInt(b.replace(/[^0-9]/g, ''), 10);
            return numB - numA;
        });
      } else {
        values.sort();
      }

      return (
        // 클릭 이벤트와 active 클래스 추가
        <div key={filterKey} className={`filter-group ${isOpen ? 'active' : ''}`}>
          <strong className="filter-title" onClick={() => handleFilterToggle(filterKey)}>
            {label}
            {/* 열림/닫힘 아이콘 추가 */}
            <span className="toggle-icon">{isOpen ? '▲' : '▼'}</span>
          </strong>
          {/* filter-options를 항상 렌더링하되, CSS로 표시 여부 제어 */}
          <div className="filter-options radio-group">
            {values.map(value => (
              <label key={value} className="radio-label">
                <input
                  type="checkbox"
                  checked={(selectedFilters[filterKey] || []).includes(value)}
                  onChange={() => handleFilterChange(filterKey, value)}
                />
                <span className="radio-text">{value}</span>
              </label>
            ))}
          </div>
        </div>
      );
    });
  };

  return (
    // --- [수정] 4. 최상위 div에 theme 클래스 적용 ---
    <div className={`app-wrapper ${theme}`}>
      <div className="app-container">
        <header>
          <h1>💻 다 나올까? 💻</h1>
          <p className="app-subtitle">웹 크롤링을 이용한 PC 부품 가격 비교 앱</p>
          {/* --- [추가] 5. 테마 변경 버튼 --- */}
          <button className="theme-toggle-btn" onClick={toggleTheme}>
            {theme === 'light' ? '🌙' : '☀️'}
          </button>
        </header>

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
        
        {/* --- [수정] 좌/우 2단 레이아웃 적용 --- */}
        <div className="main-content">
          <aside className="filters-sidebar">
            <div className="controls-container">
              <h2 className="controls-title">상세 검색</h2>
              <div className="controls-container-grid">
                <div className="search-sort-wrapper">
                  <form className="search-container" onSubmit={handleSearch}>
                    <strong className="filter-title">상품명 검색</strong>
                    <div className="search-bar">
                      <input type="text" placeholder={`${selectedCategory} 내에서 검색...`} value={searchTerm} onChange={(e) => setSearchTerm(e.target.value)} onFocus={() => setIsHistoryVisible(true)} onBlur={() => setTimeout(() => setIsHistoryVisible(false), 200)} />
                      <button type="submit">검색</button>
                    </div>
                    {isHistoryVisible && history.length > 0 && (
                      <div className="history-container">
                        <ul className="history-list">
                          {history.map((item, index) => (
                            <li key={index} className="history-item" onMouseDown={() => handleHistoryClick(item)}>
                              <span className="history-term">{item}</span>
                              <button className="delete-btn" onMouseDown={(e) => handleDeleteHistory(e, item)}>X</button>
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </form>
                  <div className="sort-container">
                    <strong className="filter-title">정렬</strong>
                    <select className="filter-select" value={sortOption} onChange={(e) => handleSortChange(e.target.value)}>
                      <option value="reviewCount,desc">인기상품순</option>
                      <option value="createdAt,desc">신상품순</option>
                      <option value="price,asc">낮은가격순</option>
                      <option value="price,desc">높은가격순</option>
                    </select>
                  </div>
                </div>
                {renderFilters()}
              </div>
            </div>
          </aside>

          <main className="products-area">
            {isLoading ? (
              <div className="spinner-container"><div className="spinner"></div></div>
            ) : (
              <>
                <div className="parts-list">
                  {parts.length > 0 ? parts.map(part => {
                    const specString = generateSpecString(part);
                    return (
                      <a key={part.id} href={part.link} target="_blank" rel="noopener noreferrer" className="card-link">
                        <div className="part-card">
                          <img src={part.imgSrc || 'https://img.danawa.com/new/noData/img/noImg_160.gif'} alt={part.name} className="part-image" />
                          <div className="part-info">
                            <h2 className="part-name">{part.name}</h2>
                            {specString && <p className="part-specs">{specString}</p>}
                            <p className="part-price">{part.price.toLocaleString()}원</p>
                            <div className="part-reviews">
                              <span>의견 {part.reviewCount?.toLocaleString() || 0}</span>
                              <span className="review-divider">|</span>
                              <span>⭐ {part.starRating || 'N/A'} ({part.ratingReviewCount?.toLocaleString() || 0})</span>
                            </div>
                          </div>
                          <div className="part-card-footer">
                            <button onClick={(e) => handleAddToCompare(e, part)} disabled={comparisonList.length >= 3 && !comparisonList.find(p => p.id === part.id)} className={comparisonList.find(p => p.id === part.id) ? 'btn-compare active' : 'btn-compare'}>
                              {comparisonList.find(p => p.id === part.id) ? '✔ 비교 중' : '✚ 비교 담기'}
                            </button>
                          </div>
                        </div>
                      </a>
                    );
                  }) : <div className="no-results">검색 결과가 없습니다.</div>}
                </div>
                
                <div className="pagination-container">
                  {totalPages > 1 && Array.from({ length: totalPages }, (_, i) => i).map(pageNumber => (
                    <button key={pageNumber} onClick={() => handlePageChange(pageNumber)} className={`page-btn ${currentPage === pageNumber ? 'active' : ''}`}>
                      {pageNumber + 1}
                    </button>
                  ))}
                </div>
              </>
            )}
          </main>
        </div>
      </div>

      {comparisonList.length > 0 && (
        <div className="comparison-tray">
          <div className="comparison-tray-items">
            {comparisonList.map(part => (
              <div key={part.id} className="comparison-item">
                <span>{part.name.substring(0, 15)}...</span>
                <button onClick={() => handleRemoveFromCompare(part.id)}>×</button>
              </div>
            ))}
          </div>
          <button className="btn-show-compare" onClick={() => setIsModalOpen(true)} disabled={comparisonList.length < 2}>
            비교하기 ({comparisonList.length}/3)
          </button>
        </div>
      )}

      {isModalOpen && (
        <ComparisonModal products={comparisonList} onClose={() => setIsModalOpen(false)} filterLabels={FILTER_LABELS} filterOrderMap={FILTER_ORDER_MAP}/>
      )}
    </div>
  );
}

export default App;