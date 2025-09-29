import React, { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import './App.css';

const CATEGORIES = ['CPU', '쿨러', '메인보드', 'RAM', '그래픽카드', 'SSD', 'HDD', '파워', '케이스'];
const ITEMS_PER_PAGE = 20;

// [수정] 중복 키를 정리한 최종 FILTER_LABELS
const FILTER_LABELS = {
  manufacturer: '제조사',
  // CPU
  codename: '코드네임',
  cpuSeries: 'CPU 시리즈',
  cpuClass: 'CPU 종류',
  socket: '소켓 구분',
  cores: '코어 수',
  threads: '스레드 수',
  integratedGraphics: '내장그래픽 탑재 여부',
  // 쿨러
  productType: '제품 분류',
  coolingMethod: '냉각 방식',
  airCoolingForm: '공랭 형태',
  coolerHeight: '쿨러 높이',
  radiatorLength: '라디에이터',
  fanSize: '팬 크기',
  fanConnector: '팬 커넥터',
  // RAM
  deviceType: '사용 장치',
  productClass: '제품 분류',
  capacity: '메모리 용량',
  ramCount: '램 개수',
  clockSpeed: '동작 클럭(대역폭)',
  ramTiming: '램 타이밍',
  heatsinkPresence: '히트싱크',
  // 메인보드
  chipset: '세부 칩셋',
  formFactor: '폼팩터',
  memorySpec: '메모리 종류',
  memorySlots: '메모리 슬롯',
  vgaConnection: 'VGA 연결',
  m2Slots: 'M.2',
  wirelessLan: '무선랜 종류',
  // 그래픽카드
  nvidiaChipset: 'NVIDIA 칩셋',
  amdChipset: 'AMD 칩셋',
  intelChipset: '인텔 칩셋',
  gpuInterface: '인터페이스',
  gpuMemoryCapacity: '메모리 용량',
  outputPorts: '출력 단자',
  recommendedPsu: '권장 파워용량',
  fanCount: '팬 개수',
  gpuLength: '가로(길이)',
  // SSD
  ssdInterface: '인터페이스',
  memoryType: '메모리 타입',
  ramMounted: 'RAM 탑재',
  sequentialRead: '순차읽기',
  sequentialWrite: '순차쓰기',
  // HDD
  hddSeries: '시리즈 구분',
  diskCapacity: '디스크 용량',
  rotationSpeed: '회전수',
  bufferCapacity: '버퍼 용량',
  hddWarranty: 'A/S 정보',
  // 케이스
  caseSize: '케이스 크기',
  supportedBoard: '지원보드 규격',
  sidePanel: '측면 개폐 방식',
  psuLength: '파워 장착 길이',
  vgaLength: 'VGA 길이',
  cpuCoolerHeightLimit: 'CPU쿨러 높이',
  // 파워
  ratedOutput: '정격출력',
  eightyPlusCert: '80PLUS인증',
  etaCert: 'ETA인증',
  cableConnection: '케이블연결',
  pcie16pin: 'PCIe 16핀(12+4)',
};

// [수정] 모든 카테고리 필터 순서를 하나의 객체로 통합
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

// [수정] App 컴포넌트 바깥으로 헬퍼 함수 분리
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
      
      if (!values || values.length === 0) {
        return null;
      }
      
      const label = FILTER_LABELS[filterKey] || filterKey;

      // 숫자 기반 정렬이 필요한 필터들을 위한 로직
      if (['fanSize', 'capacity', 'gpuMemoryCapacity'].includes(filterKey)) {
        values.sort((a, b) => {
            const numA = parseInt(a, 10);
            const numB = parseInt(b, 10);
            return numB - numA;
        });
      } else {
        values.sort();
      }

      return (
        <div key={filterKey} className="filter-group">
          <strong className="filter-title">{label}</strong>
          <div className="filter-options">
            {values.map(value => (
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
    });
  };

  return (
    <div className="app-container">
      <header>
        <h1>💻 다 나올까? 💻</h1>
        <p className="app-subtitle">웹 크롤링을 이용한 PC 부품 가격 비교 앱</p>
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
      
      <div className="controls-container">
        <h2 className="controls-title">상세 검색</h2>
        <div className="controls-container-grid">
          {renderFilters()}

          <form className="search-container" onSubmit={handleSearch}>
            <strong className="filter-title">상품명 검색</strong>
            <div className="search-bar">
              <input
                type="text"
                placeholder={`${selectedCategory} 내에서 검색...`}
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                onFocus={() => setIsHistoryVisible(true)}
                onBlur={() => setTimeout(() => setIsHistoryVisible(false), 200)}
              />
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
            <select 
              className="filter-select"
              value={sortOption}
              onChange={(e) => handleSortChange(e.target.value)}
            >
              <option value="reviewCount,desc">인기상품순</option>
              <option value="createdAt,desc">신상품순</option>
              <option value="price,asc">낮은가격순</option>
              <option value="price,desc">높은가격순</option>
            </select>
          </div>
        </div>
      </div>

      {isLoading ? (
        <div className="spinner-container"><div className="spinner"></div></div>
      ) : (
        <>
          <div className="parts-list">
            {parts.map(part => {
              const specString = generateSpecString(part);
              return (
                <a key={part.id} href={part.link} target="_blank" rel="noopener noreferrer" className="card-link">
                  <div className="part-card">
                    <img 
                      src={part.imgSrc || 'https://img.danawa.com/new/noData/img/noImg_160.gif'} 
                      alt={part.name} 
                      className="part-image" 
                    />
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
                  </div>
                </a>
              );
            })}
          </div>
          
          <div className="pagination-container">
            {totalPages > 1 && Array.from({ length: totalPages }, (_, i) => i).map(pageNumber => (
              <button
                key={pageNumber}
                onClick={() => handlePageChange(pageNumber)}
                className={`page-btn ${currentPage === pageNumber ? 'active' : ''}`}
              >
                {pageNumber + 1}
              </button>
            ))}
          </div>
        </>
      )}
    </div>
  );
}

export default App;