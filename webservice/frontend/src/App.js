import React, { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import './App.css';

const CATEGORIES = ['CPU', '쿨러', '메인보드', 'RAM', '그래픽카드', 'SSD', 'HDD', '파워', '케이스'];
const ITEMS_PER_PAGE = 20;

const FILTER_LABELS = {
  // 공통
  manufacturer: '제조사',
  // CPU
  codename: '코드네임',
  cpuSeries: 'CPU 시리즈',
  cpuClass: 'CPU 종류',
  socket: '소켓 구분',
  cores: '코어 수',
  threads: '스레드 수',
  integrated_graphics: '내장그래픽 탑재 여부',
  //쿨러
  productType: '제품 종류',
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
  // [추가] 그래픽카드
  nvidiaChipset: 'NVIDIA 칩셋',
  amdChipset: 'AMD 칩셋',
  intelChipset: '인텔 칩셋',
  gpuInterface: '인터페이스',
  gpuMemoryCapacity: '메모리 용량',
  outputPorts: '출력 단자',
  recommendedPsu: '권장 파워용량',
  fanCount: '팬 개수',
  gpuLength: '가로(길이)',
  // [추가] SSD
  formFactor: '폼팩터',
  ssdInterface: '인터페이스',
  capacity: '용량',
  memoryType: '메모리 타입',
  ramMounted: 'RAM 탑재',
  sequentialRead: '순차읽기',
  sequentialWrite: '순차쓰기',
  // [추가] HDD
  hddSeries: '시리즈 구분',
  diskCapacity: '디스크 용량',
  rotationSpeed: '회전수',
  bufferCapacity: '버퍼 용량',
  hddWarranty: 'A/S 정보',
  // [추가] 케이스
  caseSize: '케이스 크기',
  supportedBoard: '지원보드 규격',
  sidePanel: '측면 개폐 방식',
  psuLength: '파워 장착 길이',
  vgaLength: 'VGA 길이',
  cpuCoolerHeightLimit: 'CPU쿨러 높이',
};

// [신설] 필터를 표시할 순서를 정의하는 배열
const CPU_FILTER_ORDER = [
    'manufacturer',
    'codename',
    'cpuSeries',
    'cpuClass',
    'socket',
    'cores',
    'threads',
    'integrated_graphics'
];
// [신설] 쿨러 필터 표시 순서 정의
const COOLER_FILTER_ORDER = [
    'manufacturer',
    'productType',
    'coolingMethod',
    'airCoolingForm',
    'coolerHeight',
    'radiatorLength',
    'fanSize',
    'fanConnector'
];

// [신설] 메인보드 필터 표시 순서 정의
const MOTHERBOARD_FILTER_ORDER = [
    'manufacturer',
    'socket',
    'chipset',
    'formFactor',
    'memorySpec',
    'memorySlots',
    'vgaConnection',
    'm2Slots',
    'wirelessLan'
];

// [신설] RAM 필터 표시 순서 정의
const RAM_FILTER_ORDER = [
    'manufacturer',
    'deviceType',
    'productClass',
    'capacity',
    'ramCount',
    'clockSpeed',
    'ramTiming',
    'heatsinkPresence'
];

// [신설] 그래픽카드 필터 표시 순서 정의
const VGA_FILTER_ORDER = [
    'manufacturer',
    'nvidiaChipset',
    'amdChipset',
    'intelChipset',
    'gpuInterface',
    'gpuMemoryCapacity',
    'outputPorts',
    'recommendedPsu',
    'fanCount',
    'gpuLength'
];

const SSD_FILTER_ORDER = [
    'manufacturer',
    'formFactor',
    'ssdInterface',
    'capacity',
    'memoryType',
    'ramMounted',
    'sequentialRead',
    'sequentialWrite'
];

// [신설] HDD 필터 표시 순서 정의
const HDD_FILTER_ORDER = [
    'manufacturer',
    'hddSeries',
    'diskCapacity',
    'rotationSpeed',
    'bufferCapacity',
    'hddWarranty'
];

// [신설] 케이스 필터 표시 순서 정의
const CASE_FILTER_ORDER = [
    'manufacturer',
    'productType',
    'caseSize',
    'supportedBoard',
    'sidePanel',
    'psuLength',
    'vgaLength',
    'cpuCoolerHeightLimit'
];

// 다른 카테고리의 필터 순서도 필요하다면 여기에 추가할 수 있습니다.
// const RAM_FILTER_ORDER = ['manufacturer', 'capacity', 'memory_spec'];


function App() {
  // --- State 및 API 호출 함수는 기존과 동일 ---
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
      // fetchParts가 useEffect의 의존성 배열에 있으면 무한 루프가 발생할 수 있어 분리 호출
    };
    loadCategoryData().then(() => {
        fetchParts(selectedCategory, {}, '', 0, sortOption);
    });
  }, [selectedCategory, sortOption]);

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

  // --- [수정] renderFilters 함수 ---
  // 정의된 순서(FILTER_ORDER)에 따라 필터를 렌더링하도록 변경
  const renderFilters = () => {
        let filterOrder = [];
        if (selectedCategory === 'CPU') {
            filterOrder = CPU_FILTER_ORDER;
        } else if (selectedCategory === '쿨러') {
            filterOrder = COOLER_FILTER_ORDER;
        } else if (selectedCategory === '메인보드') {
            filterOrder = MOTHERBOARD_FILTER_ORDER;
        } else if (selectedCategory === 'RAM') {
            filterOrder = RAM_FILTER_ORDER;
        } else if (selectedCategory === '그래픽카드') {
            filterOrder = VGA_FILTER_ORDER;
        } else if (selectedCategory === 'SSD') {
            filterOrder = SSD_FILTER_ORDER;
        } else if (selectedCategory === 'HDD') {
            filterOrder = HDD_FILTER_ORDER;
        } else if (selectedCategory === '케이스') {
            filterOrder = CASE_FILTER_ORDER;
        }

    // 다른 카테고리 순서 추가
    // else if (selectedCategory === 'RAM') {
    //     filterOrder = RAM_FILTER_ORDER;
    // }

    return filterOrder.map(filterKey => {
      const values = availableFilters[filterKey];
      
      // API 응답에 해당 필터가 없거나 값이 없으면 렌더링하지 않음
      if (!values || values.length === 0) {
        return null;
      }
      
      const label = FILTER_LABELS[filterKey] || filterKey;

      if (filterKey === 'fanSize') {
                values.sort((a, b) => {
                    const numA = parseInt(a, 10);
                    const numB = parseInt(b, 10);
                    return numB - numA;
                });
            } else {
                values.sort(); // 나머지 필드는 가나다순 정렬
            }

            return (
                <div key={filterKey} className="filter-group">
                  <strong className="filter-title">{label}</strong>
                  <div className="filter-options">
                    {/* [수정] 정렬된 values를 사용하도록 변경 */}
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

        {/* [수정] 정렬 옵션 순서 변경 */}
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

      {/* --- 이하 JSX 렌더링 부분은 기존과 동일 --- */}
      <form className="search-container" onSubmit={handleSearch}>
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

      {isLoading ? (
        <div className="spinner-container"><div className="spinner"></div></div>
      ) : (
        <>
          <div className="parts-list">
            {parts.length > 0 ? parts.map(part => (
              <a key={part.id} href={part.link} target="_blank" rel="noopener noreferrer" className="card-link">
                <div className="part-card">
                  <img src={part.imgSrc} alt={part.name} className="part-image" />
                  <div className="part-info">
                    <h2 className="part-name">{part.name}</h2>
                    <p className="part-price">{part.price.toLocaleString()}원</p>
                  </div>
                </div>
              </a>
            )) : <p className="no-results">검색 결과가 없습니다.</p>}
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