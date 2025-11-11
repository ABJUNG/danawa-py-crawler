import React, { useState, useEffect, useCallback, useRef } from 'react';
import axios from 'axios';
import './App.css';
import ComparisonModal from './ComparisonModal'; // ComparisonModal import
import PartDetailModal from './PartDetailModal'; // 👈 1. 이 줄을 추가

const CATEGORIES = ['CPU', '쿨러', '메인보드', 'RAM', '그래픽카드', 'SSD', 'HDD', '파워', '케이스'];
const ITEMS_PER_PAGE = 21;

// 백엔드 API 기본 URL 설정 (Docker 환경에서는 backend:8080, 로컬에서는 localhost:8080)
const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8080';

// (FILTER_LABELS, FILTER_ORDER_MAP, generateSpecString 함수는 기존과 동일)
const FILTER_LABELS = {
  manufacturer: '제조사',
  codename: '코드네임',
  cpu_series: 'CPU 시리즈',
  cpu_class: 'CPU 종류',
  socket: '소켓 구분',
  cores: '코어 수',
  threads: '스레드 수',
  integrated_graphics: '내장그래픽',
  
  // --- 쿨러 스펙 ---
  product_type: '제품 분류',
  cooling_method: '냉각 방식',
  air_cooling_form: '공랭 형태',
  cooler_height: '쿨러 높이',
  radiator_length: '라디에이터',
  fan_size: '팬 크기',
  fan_count: '팬 개수',
  fan_connector: '팬 커넥터',
  max_fan_speed: '최대 팬속도',
  max_airflow: '최대 풍량',
  static_pressure: '최대 풍압(정압)',
  max_fan_noise: '최대 팬소음',
  tdp: 'TDP',
  warranty_period: 'A/S 기간',
  intel_socket: '인텔 소켓',
  amd_socket: 'AMD 소켓',
  width: '가로',
  depth: '세로',
  height: '높이',
  weight: '무게',
  fan_thickness: '팬 두께',
  fan_bearing: '베어링',
  pwm_support: 'PWM 지원',
  led_type: 'LED 타입',
  operating_voltage: '작동 전압',
  daisy_chain: '데이지 체인',
  zero_fan: '제로팬(0-dB)',

  // --- RAM ---
  device_type: '사용 장치',
  product_class: '제품 분류',
  capacity: '메모리 용량',
  ram_count: '램 개수',
  clock_speed: '동작 클럭',
  ram_timing: '램 타이밍',
  heatsink_presence: '방열판',

  // --- 메인보드 ---
  chipset: '세부 칩셋',
  form_factor: '폼팩터',
  memory_spec: '메모리 종류',
  memory_slots: '메모리 슬롯',
  vga_connection: 'VGA 연결',
  m2_slots: 'M.2',
  wireless_lan: '무선랜',

  // --- 그래픽카드 ---
  nvidia_chipset: 'NVIDIA 칩셋',
  amd_chipset: 'AMD 칩셋',
  intel_chipset: '인텔 칩셋',
  gpu_interface: '인터페이스',
  gpu_memory_capacity: '메모리 용량',
  output_ports: '출력 단자',
  recommended_psu: '권장 파워',
  // fan_count: '팬 개수', (쿨러와 중복)
  gpu_length: '가로(길이)',

  // --- SSD ---
  // form_factor: '폼팩터', (메인보드와 중복)
  ssd_interface: '인터페이스',
  memory_type: '메모리 타입',
  ram_mounted: 'RAM 탑재',
  sequential_read: '순차읽기',
  sequential_write: '순차쓰기',

  // --- HDD ---
  hdd_series: '시리즈 구분',
  disk_capacity: '디스크 용량',
  rotation_speed: '회전수',
  buffer_capacity: '버퍼 용량',
  hdd_warranty: 'A/S 정보',

  // --- 케이스 ---
  case_size: '케이스 크기',
  supported_board: '지원보드 규격',
  side_panel: '측면',
  psu_length: '파워 장착 길이',
  vga_length: 'VGA 길이',
  cpu_cooler_height_limit: 'CPU쿨러 높이',

  // --- 파워 ---
  rated_output: '정격출력',
  eighty_plus_cert: '80PLUS인증',
  eta_cert: 'ETA인증',
  cable_connection: '케이블연결',
  pcie_16pin: 'PCIe 16핀',
};

const FILTER_ORDER_MAP = {
  CPU: ['manufacturer', 'codename', 'cpu_series', 'cpu_class', 'socket', 'cores', 'threads', 'integrated_graphics'],
  쿨러: [
    'product_type', 'manufacturer', 'cooling_method', 
    'air_cooling_form', 'radiator_length', 
    'tdp', 'warranty_period', 
    // 호환/크기
    'intel_socket', 'amd_socket', 
    'width', 'depth', 'height', 'cooler_height', 'weight',
    // 팬 스펙
    'fan_size', 'fan_count', 'fan_thickness', 'fan_connector', 'fan_bearing', 
    'max_fan_speed', 'max_airflow', 'static_pressure', 'max_fan_noise', 
    'pwm_support', 'led_type',
    // 시스템팬 전용
    'operating_voltage', 'daisy_chain', 'zero_fan'
  ],
  메인보드: ['manufacturer', 'socket', 'chipset', 'form_factor', 'memory_spec', 'memory_slots', 'vga_connection', 'm2_slots', 'wireless_lan'],
  RAM: ['manufacturer', 'device_type', 'product_class', 'capacity', 'ram_count', 'clock_speed', 'ram_timing', 'heatsink_presence'],
  그래픽카드: ['manufacturer', 'nvidia_chipset', 'amd_chipset', 'intel_chipset', 'gpu_interface', 'gpu_memory_capacity', 'output_ports', 'recommended_psu', 'fan_count', 'gpu_length'],
  SSD: ['manufacturer', 'form_factor', 'ssd_interface', 'capacity', 'memory_type', 'ram_mounted', 'sequential_read', 'sequential_write'],
  HDD: ['manufacturer', 'hdd_series', 'disk_capacity', 'rotation_speed', 'buffer_capacity', 'hdd_warranty'],
  케이스: ['manufacturer', 'product_type', 'case_size', 'supported_board', 'side_panel', 'psu_length', 'vga_length', 'cpu_cooler_height_limit'],
  파워: ['manufacturer', 'product_type', 'rated_output', 'eighty_plus_cert', 'eta_cert', 'cable_connection', 'pcie_16pin']
};

/**
 * [신규] 상품 카드에 표시할 핵심 스펙을 추출하는 헬퍼 함수
 * part.specs JSON을 파싱하여 카테고리별 주요 스펙을 반환합니다.
 */
const getSummarySpecs = (part) => {
    if (!part.specs || typeof part.specs !== 'object') {
        // DTO에서 specs가 아예 없거나 ({}가 아닌) null, undefined인 경우
        return [];
    }
    try {
        const parsed = part.specs; // DTO가 이미 JSON 객체로 보내주므로 JSON.parse 불필요
        const summary = [];
        
        // 카테고리별로 카드에 보여줄 우선순위 스펙 키
        // FILTER_ORDER_MAP을 재사용하여 순서대로 가져옴
        const keys = FILTER_ORDER_MAP[part.category] || [];
        
        for (const key of keys) {
            // nvidia_chipset 또는 amd_chipset/intel_chipset 둘 중 하나만 처리
            if (key === 'nvidia_chipset') {
                 if (parsed['nvidia_chipset']) {
                    summary.push({ key: FILTER_LABELS[key], value: parsed[key] });
                 } else if (parsed['amd_chipset']) {
                    summary.push({ key: FILTER_LABELS['amd_chipset'], value: parsed['amd_chipset'] });
                 } else if (parsed['intel_chipset']) {
                    summary.push({ key: FILTER_LABELS['intel_chipset'], value: parsed['intel_chipset'] });
                 }
                 continue; // 중복 방지
            }
            // 이미 위에서 처리했으므로 건너뛰기
            if (key === 'amd_chipset' || key === 'intel_chipset') continue;
            
            // 그 외 스펙들은 순서대로 추가
            if (parsed[key]) {
                const label = FILTER_LABELS[key] || key; 
                summary.push({ key: label, value: parsed[key] });
            }
            
            // --- 👇 [수정] 최대 3개에서 8개로 변경 ---
            if (summary.length >= 8) {
                break;
            }
        }
        return summary;

    } catch (e) {
        console.error("Failed to parse summary specs:", e, part.specs);
        return [];
    }
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
  const [sortOption, setSortOption] = useState('reviewCount,desc');
  const [comparisonList, setComparisonList] = useState([]);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isDetailModalOpen, setIsDetailModalOpen] = useState(false);
  const [selectedPart, setSelectedPart] = useState(null);
  
  // --- [추가] 아코디언 UI를 위한 상태 관리 ---
  const [openFilter, setOpenFilter] = useState('manufacturer'); 

  // --- [추가] 아코디언 토글 핸들러 ---
  const handleFilterToggle = (filterKey) => {
    setOpenFilter(prevOpenFilter => prevOpenFilter === filterKey ? null : filterKey);
  };



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

  const handleOpenDetailModal = (part) => {
    setSelectedPart(part);
    setIsDetailModalOpen(true);
  };

  const handleCloseDetailModal = () => {
    setIsDetailModalOpen(false);
    setSelectedPart(null); // 선택된 부품 정보 초기화
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
      
      const response = await axios.get(`${API_BASE_URL}/api/parts?${params.toString()}`);
      
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
        const filtersRes = await axios.get(`${API_BASE_URL}/api/filters?category=${selectedCategory}`);
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
 
  // --- [추가] 이전 페이지로 이동하는 함수 ---
  const handlePrevPage = () => {
    if (currentPage > 0) {
      handlePageChange(currentPage - 1);
    }
  };

  // --- [추가] 다음 페이지로 이동하는 함수 ---
  const handleNextPage = () => {
    if (currentPage < totalPages - 1) {
      handlePageChange(currentPage + 1);
    }
  };
  
  const handleSortChange = (sortValue) => {
    setSortOption(sortValue);
  };

  // --- [추가] 선택된 필터 태그를 클릭하여 제거하는 함수 ---
  const handleRemoveFilter = (filterKey, valueToRemove) => {
    const newFilters = { ...selectedFilters };

    // 현재 필터의 값 배열에서 제거할 값을 제외한 새 배열을 생성
    const newValues = newFilters[filterKey].filter(value => value !== valueToRemove);

    if (newValues.length > 0) {
      // 새 배열에 값이 남아있으면 업데이트
      newFilters[filterKey] = newValues;
    } else {
      // 새 배열이 비어있으면 해당 필터 키 자체를 삭제
      delete newFilters[filterKey];
    }

    setSelectedFilters(newFilters);
    setCurrentPage(0);
    fetchParts(selectedCategory, newFilters, searchTerm, 0, sortOption);
  };

  // --- [추가] 모든 필터를 초기화하는 함수 ---
  const handleResetFilters = () => {
    setSelectedFilters({});
    setCurrentPage(0);
    fetchParts(selectedCategory, {}, searchTerm, 0, sortOption);
  };

  // --- [추가] 선택된 필터 태그들을 렌더링하는 함수 ---
  const renderSelectedFilters = () => {
    // 선택된 필터가 없으면 아무것도 렌더링하지 않음
    if (Object.keys(selectedFilters).length === 0) {
      return null;
    }

    return (
      <div className="selected-filters-container">
        {Object.entries(selectedFilters).flatMap(([key, values]) =>
          values.map(value => (
            <div key={`${key}-${value}`} className="filter-tag">
              <span>{FILTER_LABELS[key]}: {value}</span>
              <button onClick={() => handleRemoveFilter(key, value)}>🅧</button>
            </div>
          ))
        )}
        <button className="reset-filters-btn" onClick={handleResetFilters}>
          전체 초기화
        </button>
      </div>
    );
  };

  // --- [추가] 스켈레톤 UI 컴포넌트 ---
  const SkeletonCard = () => {
  return (
    <div className="skeleton-card">
      <div className="skeleton-image"></div>
      <div className="skeleton-info">
        <div className="skeleton-text long"></div>
        <div className="skeleton-text short"></div>
        <div className="skeleton-text medium"></div>
      </div>
    </div>
  );
};
  // --- [수정] 아코디언 UI를 적용할 renderFilters 함수 ---
  const renderFilters = () => {
    const filterOrder = FILTER_ORDER_MAP[selectedCategory] || Object.keys(availableFilters);

    return filterOrder.map(filterKey => {
      const values = availableFilters[filterKey];
      if (!values || values.length === 0) { return null; }
      
      const label = FILTER_LABELS[filterKey] || filterKey;
      const isOpen = openFilter === filterKey;

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
        <div key={filterKey} className={`filter-group ${isOpen ? 'active' : ''}`}>
          {/* 제목을 클릭하면 펼쳐지도록 onClick 이벤트 추가 */}
          <strong className="filter-title" onClick={() => handleFilterToggle(filterKey)}>
            {label}
            <span className="toggle-icon">{isOpen ? '▲' : '▼'}</span>
          </strong>
          {/* 알약 버튼 그룹 */}
          <div className="radio-group">
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
            {renderSelectedFilters()}

            {isLoading ? (
              <div className="parts-list">
                {/* ITEMS_PER_PAGE 개수만큼 스켈레톤 카드 렌더링 */}
                {Array.from({ length: ITEMS_PER_PAGE }).map((_, index) => (
                  <SkeletonCard key={index} />
                ))}
              </div>
            ) : (
              <>
                <div className="parts-list">
                      {parts.length > 0 ? parts.map(part => {
                          // --- 👇 [수정] getSummarySpecs 함수 호출 ---
                          const summarySpecs = getSummarySpecs(part); 
                          return (
                              <div key={part.id} className="card-link" onClick={() => handleOpenDetailModal(part)}> 
                                  <div className="part-card">
                                      <img src={part.imgSrc || 'https://img.danawa.com/new/noData/img/noImg_160.gif'} alt={part.name} className="part-image" />
                                      <div className="part-info">
                                          <h2 className="part-name">{part.name}</h2>
                                          
                                          {/* --- 👇 [수정] 상세 스펙 요약 리스트 (ul/li 사용) --- */}
                                          <ul className="part-summary-specs">
                                              {summarySpecs.length > 0 ? (
                                                  summarySpecs.map(spec => (
                                                      <li key={spec.key}>
                                                          <strong>{spec.key}:</strong> {spec.value}
                                                      </li>
                                                  ))
                                              ) : (
                                                  <li className="no-spec">주요 스펙 정보 없음</li>
                                              )}
                                          </ul>
                                          {/* --- [수정 완료] --- */}
                                          
                                          <p className="part-price">{part.price.toLocaleString()}원</p>
                                          <div className="part-reviews">
                                {/* 👈 한글화 확인 */}
                                <span>의견 {part.reviewCount?.toLocaleString() || 0}</span>
                                <span className="review-divider">|</span>
                                <span>⭐ {part.starRating || 'N/A'} ({part.ratingReviewCount?.toLocaleString() || 0})</span>
                              </div>
                            </div>
                            <div className="part-card-footer">
                              <button onClick={(e) => handleAddToCompare(e, part)} disabled={comparisonList.length >= 3 && !comparisonList.find(p => p.id === part.id)} className={comparisonList.find(p => p.id === part.id) ? 'btn-compare active' : 'btn-compare'}>
                                {/* 👈 한글화 확인 */}
                                {comparisonList.find(p => p.id === part.id) ? '✔ 비교 중' : '✚ 비교 담기'}
                              </button>
                            </div>
                          </div>
                        </div>
                      );
                    }) : <div className="no-results">검색 결과가 없습니다.</div>}
                </div>
                
                <div className="pagination-container">
                <button 
                  onClick={handlePrevPage} 
                  disabled={currentPage === 0}
                  className="page-btn arrow-btn"
                >
                  &lt;
                </button>
                
                {totalPages > 1 && Array.from({ length: totalPages }, (_, i) => i).map(pageNumber => (
                  <button
                    key={pageNumber}
                    onClick={() => handlePageChange(pageNumber)}
                    className={`page-btn ${currentPage === pageNumber ? 'active' : ''}`}
                  >
                    {pageNumber + 1}
                  </button>
                  ))}
                  <button 
                  onClick={handleNextPage} 
                  disabled={currentPage === totalPages - 1}
                  className="page-btn arrow-btn"
                >
                  &gt;
                </button>
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
      {isDetailModalOpen && selectedPart && (
          <PartDetailModal 
              part={selectedPart} 
              onClose={handleCloseDetailModal}
              filterLabels={FILTER_LABELS} /* 👈 스펙 라벨링을 위해 전달 */
          />
      )}
    </div>
  );
}

export default App;