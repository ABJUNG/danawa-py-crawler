import re
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
from sqlalchemy import create_engine, text
import json
import time
from playwright_stealth import stealth_sync
from urllib.parse import quote_plus
import requests


# --- 1. 기본 설정 ---
# 이 부분의 값을 변경하여 크롤러 동작을 제어할 수 있습니다.

# 크롤링할 페이지 수 (예: 2로 설정하면 각 카테고리별로 2페이지까지 수집)
CRAWL_PAGES = 1 

# 브라우저 창을 띄울지 여부 (True: 숨김, False: 보임 - 디버깅 및 안정성에 유리)
HEADLESS_MODE = True

# 각 동작 사이의 지연 시간 (ms). 봇 탐지를 피하고 안정성을 높임 (50~100 추천)
SLOW_MOTION = 50

# --- 2. DB 설정 ---
DB_USER = 'root'
DB_PASSWORD = '1234'  # 실제 비밀번호로 수정
DB_HOST = 'db'
DB_PORT = '3306'
DB_NAME = 'danawa'

# --- 3. 크롤링 카테고리 ---
CATEGORIES = {
    'CPU': 'cpu', 
    # '쿨러': 'cooler', '메인보드': 'mainboard', 'RAM': 'RAM',
    # '그래픽카드': 'vga', 'SSD': 'ssd', 'HDD': 'hdd', '케이스': 'pc case', '파워': 'power'
}

# --- 5. SQLAlchemy 엔진 생성 ---
try:
    engine = create_engine(f'mysql+mysqlconnector://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}')
    with engine.connect() as conn:
        print("DB 연결 성공")
        # 벤치마크 결과 테이블이 없으면 생성
        create_bench_sql = text("""
        CREATE TABLE IF NOT EXISTS benchmark_results (
            id BIGINT AUTO_INCREMENT PRIMARY KEY,
            part_id BIGINT NOT NULL,
            part_type VARCHAR(16) NULL COMMENT 'CPU 또는 GPU',
            cpu_model VARCHAR(64) NULL COMMENT 'CPU 모델명 (예: 7500F, 7800X3D)',
            source VARCHAR(64) NOT NULL,
            test_name VARCHAR(128) NOT NULL,
            test_version VARCHAR(32) NOT NULL DEFAULT '',
            scenario VARCHAR(256) NOT NULL DEFAULT '',
            metric_name VARCHAR(64) NOT NULL,
            value DOUBLE NOT NULL,
            unit VARCHAR(32) NULL,
            review_url VARCHAR(512) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            -- utf8mb4 인덱스 길이 제한(3072 bytes)을 피하기 위해 prefix index 적용
            UNIQUE KEY uq_part_test (
                part_id,
                test_name(64),
                test_version(16),
                scenario(128),
                metric_name(32),
                review_url(191)
            ),
            KEY idx_part (part_id),
            KEY idx_part_type (part_type),
            KEY idx_cpu_model (cpu_model)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """)
        conn.execute(create_bench_sql)
        
        # 기존 테이블에 컬럼 추가 (이미 존재하는 경우 무시)
        try:
            alter_sql1 = text("ALTER TABLE benchmark_results ADD COLUMN part_type VARCHAR(16) NULL COMMENT 'CPU 또는 GPU' AFTER part_id")
            conn.execute(alter_sql1)
        except:
            pass
        
        try:
            alter_sql2 = text("ALTER TABLE benchmark_results ADD COLUMN cpu_model VARCHAR(64) NULL COMMENT 'CPU 모델명 (예: 7500F, 7800X3D)' AFTER part_type")
            conn.execute(alter_sql2)
        except:
            pass
        
        try:
            alter_sql3 = text("ALTER TABLE benchmark_results ADD KEY idx_part_type (part_type)")
            conn.execute(alter_sql3)
        except:
            pass
        
        try:
            alter_sql4 = text("ALTER TABLE benchmark_results ADD KEY idx_cpu_model (cpu_model)")
            conn.execute(alter_sql4)
        except:
            pass
        
        # community_reviews 테이블에 part_type, cpu_model 컬럼 추가
        try:
            alter_review1 = text("ALTER TABLE community_reviews ADD COLUMN part_type VARCHAR(16) NULL COMMENT 'CPU 또는 GPU' AFTER part_id")
            conn.execute(alter_review1)
        except:
            pass
        
        try:
            alter_review2 = text("ALTER TABLE community_reviews ADD COLUMN cpu_model VARCHAR(64) NULL COMMENT 'CPU 모델명 (예: 7500F, 7800X3D)' AFTER part_type")
            conn.execute(alter_review2)
        except:
            pass
        
        try:
            alter_review3 = text("ALTER TABLE community_reviews ADD KEY idx_review_part_type (part_type)")
            conn.execute(alter_review3)
        except:
            pass
        
        try:
            alter_review4 = text("ALTER TABLE community_reviews ADD KEY idx_review_cpu_model (cpu_model)")
            conn.execute(alter_review4)
        except:
            pass
except Exception as e:
    print(f"DB 연결 실패: {e}")
    exit()

def parse_cpu_specs(name, spec_string):
    """[최종 완성] P+E코어, 복합 스레드 등 모든 최신 CPU 스펙을 완벽하게 지원하는 파서"""
    specs = {}
    # 이름과 스펙 문자열을 하나로 합쳐 검색 효율성 극대화
    full_text = name + " / " + spec_string

    # 1. 제조사 확정
    if '인텔' in full_text or '코어i' in full_text or '울트라' in full_text:
        specs['manufacturer'] = '인텔'
    elif 'AMD' in full_text or '라이젠' in full_text:
        specs['manufacturer'] = 'AMD'

    # 2. 정규 표현식으로 각 스펙을 정확하게 추출
    
    # 코어 (P+E 코어 형식 포함, 예: P8+E12코어, 8코어)
    core_match = re.search(r'([PE\d\+]+코어)', full_text)
    if core_match:
        specs['cores'] = core_match.group(1)

    # 스레드 (복합 스레드 형식 포함, 예: 12+8스레드, 20스레드)
    # --- 여기가 핵심 수정 부분입니다! ---
    thread_match = re.search(r'([\d\+]+)\s*스레드', full_text)
    if thread_match:
        specs['threads'] = thread_match.group(1).replace(' ', '') + '스레드'

    # 소켓 (괄호 안 형식 포함, 예: 인텔(소켓1700))
    socket_match = re.search(r'소켓([^\s\)]+)', full_text)
    if socket_match:
        specs['socket'] = '소켓' + socket_match.group(1)

    # 코드네임 (괄호 안 형식 우선 추출, 예: (애로우레이크))
    codename_match = re.search(r'\(([^)]+(?:레이크|릿지|리프레시|라파엘|버미어|라파엘|피카소|세잔|시마다 픽|피닉스|Zen\d+))\)', full_text)
    if codename_match:
        specs['codename'] = codename_match.group(1)
        
    # CPU 시리즈 (예: 14세대, 6세대)
    series_match = re.search(r'(\d+세대)', full_text)
    if series_match:
        specs['cpu_series'] = series_match.group(1)

    # CPU 종류 (상품명에서 추출)
    class_match = re.search(r'(코어\s?(?:울트라|i)\d+|라이젠\s?\d)', name, re.I)
    if class_match:
        specs['cpu_class'] = class_match.group(1).replace(' ', '')

    # 내장그래픽
    if '내장그래픽' in full_text:
        if '미탑재' in full_text:
            specs['integrated_graphics'] = '미탑재'
        elif '탑재' in full_text:
            specs['integrated_graphics'] = '탑재'
            
    return specs

def parse_cooler_specs(name, spec_string):
    """쿨러 파싱 로직 개선"""
    specs = {}
    if name: specs['manufacturer'] = name.split()[0]
    
    spec_parts = [part.strip() for part in spec_string.split('/')]
    for part in spec_parts:
        if 'CPU' in part and '쿨러' in part: specs['product_type'] = 'CPU 쿨러'
        elif '공랭' in part: specs['cooling_method'] = '공랭'
        elif '수랭' in part: specs['cooling_method'] = '수랭'
        elif '타워형' in part: specs['air_cooling_form'] = '타워형'
        elif '플라워형' in part: specs['air_cooling_form'] = '플라워형'
        elif '라디에이터' in part and '열' in part: specs['radiator_length'] = part
        elif '쿨러 높이' in part: specs['cooler_height'] = part
        elif '팬 크기' in part: specs['fan_size'] = part
        elif '팬 커넥터' in part: specs['fan_connector'] = part
            
    return specs

def parse_motherboard_specs(name, spec_string):
    """메인보드 파싱 로직 개선"""
    specs = {}
    if name: specs['manufacturer'] = name.split()[0]

    spec_parts = [part.strip() for part in spec_string.split('/')]
    for part in spec_parts:
        part_no_keyword = part.replace('CPU 소켓:','').strip()
        if '소켓' in part: specs['socket'] = part_no_keyword
        # 칩셋 (예: B760, X670) 패턴
        elif re.search(r'^[A-Z]\d{3}[A-Z]*$', part): specs['chipset'] = part
        # 폼팩터
        elif 'ATX' in part or 'ITX' in part: specs['form_factor'] = part
        # 메모리 종류
        elif 'DDR' in part: specs['memory_spec'] = part
        elif '메모리 슬롯' in part: specs['memory_slots'] = part
        elif 'VGA 연결' in part or 'PCIe' in part: specs['vga_connection'] = part
        elif 'M.2' in part: specs['m2_slots'] = part
        elif '무선랜' in part or 'Wi-Fi' in part: specs['wireless_lan'] = part
            
    return specs

def parse_ram_specs(name, spec_string):
    """RAM 파싱 로직 개선"""
    specs = {}
    if name: specs['manufacturer'] = name.split()[0]
    spec_parts = [part.strip() for part in spec_string.split('/')]
    for part in spec_parts:
        if '데스크탑용' in part or '노트북용' in part: specs['device_type'] = part
        elif re.match(r'^DDR\d+$', part): specs['product_class'] = part
        elif re.search(r'^\d+GB$|^\d+TB$', part): specs['capacity'] = part
        elif re.search(r'^\d+개$', part): specs['ram_count'] = part
        elif 'MHz' in part: specs['clock_speed'] = part
        elif 'CL' in part: specs['ram_timing'] = part
        elif '방열판' in part: specs['heatsink_presence'] = part

    return specs

def parse_vga_specs(name, spec_string):
    """그래픽카드 파싱 로직 개선"""
    specs = {}
    if name: specs['manufacturer'] = name.split()[0]
    spec_parts = [part.strip() for part in spec_string.split('/')]
    for part in spec_parts:
        if 'RTX' in part or 'GTX' in part: specs['nvidia_chipset'] = part
        elif 'RX' in part: specs['amd_chipset'] = part
        elif 'Arc' in part: specs['intel_chipset'] = part
        elif 'PCIe' in part: specs['gpu_interface'] = part
        elif 'GDDR' in part: specs['gpu_memory_capacity'] = part
        elif '출력 단자' in part: specs['output_ports'] = part
        elif '권장 파워' in part: specs['recommended_psu'] = part
        elif '팬 개수' in part: specs['fan_count'] = part
        elif '가로(길이)' in part: specs['gpu_length'] = part

    return specs

def parse_ssd_specs(name, spec_string):
    """SSD 파싱 로직 개선"""
    specs = {}
    if name: specs['manufacturer'] = name.split()[0]
    spec_parts = [part.strip() for part in spec_string.split('/')]
    for part in spec_parts:
        if 'M.2' in part or '2.5인치' in part: specs['form_factor'] = part
        elif 'PCIe' in part or 'SATA' in part: specs['ssd_interface'] = part
        elif ('TB' in part or 'GB' in part) and 'capacity' not in specs: specs['capacity'] = part
        elif 'TLC' in part or 'QLC' in part or 'MLC' in part: specs['memory_type'] = part
        elif 'RAM 탑재' in part: specs['ram_mounted'] = part
        elif '순차읽기' in part: specs['sequential_read'] = part
        elif '순차쓰기' in part: specs['sequential_write'] = part
            
    return specs

def parse_hdd_specs(name, spec_string):
    """HDD 파싱 로직 개선"""
    specs = {}
    if name: specs['manufacturer'] = name.split()[0]
    spec_parts = [part.strip() for part in spec_string.split('/')]
    for part in spec_parts:
        if any(s in part for s in ['BarraCuda', 'IronWolf', 'WD', 'P300']): specs['hdd_series'] = part
        elif ('TB' in part or 'GB' in part): specs['disk_capacity'] = part
        elif 'RPM' in part: specs['rotation_speed'] = part
        elif '버퍼' in part: specs['buffer_capacity'] = part
        elif 'A/S' in part: specs['hdd_warranty'] = part
            
    return specs

def parse_case_specs(name, spec_string):
    """케이스 파싱 로직 개선"""
    specs = {}
    if name: specs['manufacturer'] = name.split()[0]
    spec_parts = [part.strip() for part in spec_string.split('/')]
    for part in spec_parts:
        if 'PC케이스' in part: specs['product_type'] = part
        elif '타워' in part: specs['case_size'] = part
        elif 'ATX' in part or 'ITX' in part: specs['supported_board'] = part
        elif '강화유리' in part or '메쉬' in part: specs['side_panel'] = part
        elif '파워 장착' in part: specs['psu_length'] = part
        elif 'VGA 장착' in part or '그래픽카드 장착' in part: specs['vga_length'] = part
        elif '쿨러 장착' in part or 'CPU 쿨러 장착' in part: specs['cpu_cooler_height_limit'] = part
            
    return specs

def parse_power_specs(name, spec_string):
    """파워 파싱 로직 개선"""
    specs = {}
    if name: specs['manufacturer'] = name.split()[0]
    spec_parts = [part.strip() for part in spec_string.split('/')]
    for part in spec_parts:
        if '파워' in part: specs['product_type'] = part
        elif '정격출력' in part or ('W' in part and 'rated_output' not in specs): specs['rated_output'] = part
        elif '80PLUS' in part: specs['eighty_plus_cert'] = part
        elif 'ETA' in part: specs['eta_cert'] = part
        elif '케이블연결' in part: specs['cable_connection'] = part
        elif '16핀' in part: specs['pcie_16pin'] = part
            
    return specs

PARSER_MAP = {
    'CPU': parse_cpu_specs,
    '쿨러': parse_cooler_specs,
    '메인보드': parse_motherboard_specs,
    'RAM': parse_ram_specs,
    '그래픽카드': parse_vga_specs,
    'SSD': parse_ssd_specs,
    'HDD': parse_hdd_specs,
    '케이스': parse_case_specs,
    '파워': parse_power_specs,
}

def scrape_cinebench_r23(page, keyword):
    """ (신규) render4you.com에서 Cinebench R23 '멀티코어' 점수만 스크랩합니다. """
    print(f"        -> (1/4) Cinebench R23 검색 (키워드: {keyword})")
    try:
        url = "https://www.render4you.com/cinebench-benchmark-database"
        page.goto(url, wait_until='domcontentloaded', timeout=15000)
        
        try:
            page.wait_for_selector('table#benchmark-table', timeout=10000)
        except Exception:
            print("        -> (경고) Cinebench R23 테이블을 시간 초과로 찾지 못했습니다.")
            return None
        
        # Playwright가 로드한 페이지의 HTML을 BeautifulSoup으로 파싱
        html = page.content()
        soup = BeautifulSoup(html, 'lxml')

        # 'benchmark-table' ID를 가진 테이블을 찾습니다.
        table = soup.find('table', {'id': 'benchmark-table'})
        if not table:
            print("        -> (경고) Cinebench R23 테이블을 찾지 못했습니다.")
            return None

        rows = table.find('tbody').find_all('tr')
        keyword_lower = keyword.lower()

        for row in rows:
            cols = row.find_all('td')
            # 0: CPU 이름, 1: 멀티코어 점수, 2: 싱글코어 점수
            if len(cols) < 2: 
                continue

            cpu_name = cols[0].text.strip().lower()
            
            # 키워드(예: 14700K)가 CPU 이름(예: intel core i7-14700k)에 포함되는지 확인
            if keyword_lower in cpu_name:
                try:
                    # Multi-Core 점수(cols[1])만 추출
                    multi_score_text = cols[1].text.strip().replace(',', '')
                    multi_score = int(multi_score_text)
                    
                    print(f"        -> (성공) Cinebench R23 (Multi) 점수 찾음: {multi_score}")
                    return multi_score # 점수(int)만 반환
                except ValueError:
                    # 점수 란에 "N/A" 등이 적힌 경우 무시
                    continue 

        print(f"        -> (정보) Cinebench R23 DB에서 '{keyword}'를 찾지 못했습니다.")
        return None # 못 찾으면 None 반환
    except Exception as e:
        print(f"        -> (경고) Cinebench 스크래핑 실패: {e}")
        return None

def _scrape_geekbench_page(page, url, keyword):
    """ (신규) Geekbench 헬퍼 함수. 특정 URL에서 keyword의 점수를 1개 찾습니다. """
    try:
        page.goto(url, wait_until='domcontentloaded', timeout=15000)
        
        try:
            page.wait_for_selector('table.list tbody tr', timeout=10000)
        except Exception:
            print(f"        -> (경고) Geekbench 테이블을 시간 초과로 찾지 못했습니다. ({url})")
            return None

        # 테이블의 모든 행(tr)을 가져옵니다.
        rows = page.locator('table.list tbody tr')
        
        for i in range(rows.count()):
            row = rows.nth(i)
            try:
                cpu_name_element = row.locator('.name-col')
                if not cpu_name_element:
                    continue
                
                cpu_name = cpu_name_element.inner_text().strip().lower()
                
                # 키워드(예: 14700K)가 CPU 이름(예: intel core i7-14700k)에 포함되는지 확인
                if keyword.lower() in cpu_name:
                    score_text = row.locator('.score-col').inner_text().strip().replace(',', '')
                    score = int(score_text)
                    return score # 일치하는 첫 번째 점수 반환
                    
            except Exception:
                continue # 한 행 파싱 실패 시 무시

        return None # 테이블 전체에서 못 찾음
    except Exception as e:
        print(f"        -> (경고) Geekbench 페이지({url}) 스크래핑 실패: {e}")
        return None

def scrape_geekbench_6(page, keyword):
    """ (신규) geekbench.com에서 Multi/Single 점수를 모두 스크랩합니다. """
    print(f"        -> (2/4) Geekbench 6 검색 (키워드: {keyword})")
    
    multi_url = "https://browser.geekbench.com/v6/cpu/multicore"
    single_url = "https://browser.geekbench.com/v6/cpu/singlecore"
    
    multi_score = None
    single_score = None

    # 1. 멀티코어 점수 가져오기
    print(f"        -> (2/4) 멀티코어 점수 검색 중...")
    multi_score = _scrape_geekbench_page(page, multi_url, keyword)

    # 2. 싱글코어 점수 가져오기
    print(f"        -> (2/4) 싱글코어 점수 검색 중...")
    single_score = _scrape_geekbench_page(page, single_url, keyword)

    if multi_score and single_score:
        print(f"        -> (성공) Geekbench 점수 찾음: Multi {multi_score}, Single {single_score}")
        return {"multi": multi_score, "single": single_score}
    else:
        if not multi_score:
            print(f"        -> (정보) Geekbench '멀티코어' DB에서 '{keyword}'를 찾지 못했습니다.")
        if not single_score:
            print(f"        -> (정보) Geekbench '싱글코어' DB에서 '{keyword}'를 찾지 못했습니다.")
        return None

def scrape_blender(page, keyword):
    """ (신규) opendata.blender.org에서 'Median Score'를 스크랩합니다. """
    print(f"        -> (3/4) Blender 검색 (키워드: {keyword})")
    try:
        url = "https://opendata.blender.org/benchmarks/query/?compute_type=CPU"
        page.goto(url, wait_until='domcontentloaded', timeout=15000)
        
        search_box_selector = 'input[type="search"]'
        try:
            page.wait_for_selector(search_box_selector, timeout=10000)
        except Exception:
             print(f"        -> (경고) Blender 검색창을 시간 초과로 찾지 못했습니다.")
             return None
        
        search_box = page.locator(search_box_selector)

        # 2. 검색창에 키워드를 입력합니다.
        search_box.fill(keyword)
        
        # 3. JavaScript가 테이블을 필터링할 때까지 1초 대기합니다.
        page.wait_for_timeout(1000)

        # 4. 필터링된 테이블의 '첫 번째' 행(tr)을 찾습니다.
        first_row = page.locator('table tbody tr').first
        
        if not first_row.is_visible(timeout=2000):
            print(f"        -> (정보) Blender DB에서 '{keyword}'를 찾지 못했습니다.")
            return None
        
        # 5. 첫 번째 행(tr)의 두 번째(nth(1)) 'Score' 열(td)에서 점수를 추출합니다.
        score_element = first_row.locator('td').nth(1)
        score_text = score_element.inner_text().strip().replace(',', '')
        
        # Blender 점수는 소수점을 포함하므로 float으로 변환
        score = float(score_text)
        
        print(f"        -> (성공) Blender 점수 찾음: {score}")
        return score

    except Exception as e:
        print(f"        -> (경고) Blender 스크래핑 실패: {e}")
        return None

def extract_benchmark_scores(raw_text):
    """
    리뷰 본문 텍스트에서 대표적인 벤치마크 점수(정수)를 단순 정규식으로 추출합니다.
    - Cinebench R23/R24: Multi/Single
    - CPU Profile: Max/1T/2T/4T/8T/16T
    값이 다수일 경우 상위 몇 개만 반환합니다.
    """
    results = []

    # 공통 숫자 파서
    def to_int(num_str):
        try:
            return int(num_str.replace(',', '').strip())
        except Exception:
            return None

    text = raw_text

    # Cinebench R23/R24
    for m in re.finditer(r"Cinebench\s*R(2[34])\s*(Multi|멀티|Single|싱글)?[^\n\r]*?([\d,]{3,})", text, re.I):
        version = m.group(1)
        scenario = m.group(2) or ''
        value = to_int(m.group(3))
        if value:
            results.append({
                "test_name": "Cinebench",
                "test_version": f"R{version}",
                "scenario": ("Multi" if scenario and scenario.lower().startswith('m') else ("Single" if scenario and scenario.lower().startswith('s') else "")),
                "metric_name": "Score",
                "value": value,
                "unit": "pts"
            })

    # CPU Profile
    for scenario_label in ["Max", "1T", "2T", "4T", "8T", "16T"]:
        pattern = rf"CPU\s*Profile[^\n\r]*{scenario_label}[^\n\r]*([\d,]{3,})"
        for m in re.finditer(pattern, text, re.I):
            value = to_int(m.group(1))
            if value:
                results.append({
                    "test_name": "CPU Profile",
                    "test_version": "",
                    "scenario": scenario_label,
                    "metric_name": "Score",
                    "value": value,
                    "unit": "pts"
                })

    # 너무 많은 결과면 상위 10개만 반환
    return results[:10]

# --- (신규) CPU 벤치마크 수집 함수들 ---
def scrape_cinebench_r23(page, cpu_name, conn, part_id, category_name='CPU'):
    """
    render4you.com에서 Cinebench R23 점수 수집 (Multi/Single)
    테이블 구조: thead에 Manufactur, Modell, R20, R23, 2024
    tbody tr에 td 순서: 제조사, 모델명, R20, R23, 2024
    """
    try:
        # CPU 모델명 추출 (7500F, 7800X3D 등)
        cpu_model_match = re.search(r'(\d{3,5}\w*(?:F|K|X|G|3D)*|\d{3}[K])', cpu_name, re.I)
        cpu_model = cpu_model_match.group(1) if cpu_model_match else None
        
        # 중복 체크: 이미 데이터가 있으면 수집하지 않음
        check_sql = text("""
            SELECT EXISTS (
                SELECT 1 FROM benchmark_results 
                WHERE part_id = :part_id 
                AND test_name = 'Cinebench' 
                AND test_version = 'R23'
                AND scenario = 'Multi'
            )
        """)
        exists_result = conn.execute(check_sql, {"part_id": part_id})
        if exists_result.scalar() == 1:
            print(f"        -> (건너뜀) Cinebench R23 데이터가 이미 존재합니다.")
            return
        # CPU 모델명 정규화 (7500F -> 7500, 7800X3D -> 7800)
        # 더 정확한 매칭을 위해 전체 모델명도 시도
        model_match = re.search(r'(\d{3,5}\w*(?:F|K|X|G|3D)*)', cpu_name, re.I)
        if not model_match:
            return
        
        search_term_full = model_match.group(1)  # 전체 (예: 7500F)
        search_term_num = re.search(r'(\d{3,5})', cpu_name, re.I)
        search_term_num = search_term_num.group(1) if search_term_num else search_term_full[:4]
        
        url = "https://www.render4you.com/cinebench-benchmark-database"
        print(f"      -> Cinebench R23 검색: {url} (필터: {search_term_full})")
        
        page.goto(url, wait_until='networkidle', timeout=15000)
        page.wait_for_timeout(3000)  # 페이지 로딩 대기 증가
        
        # 검색 입력 필드 찾기 및 입력 (여러 시도)
        search_attempted = False
        for selector in [
            'input[type="search"]',
            '.dataTables_filter input',
            'input[placeholder*="Search"]',
            'input[placeholder*="search"]',
            'input.dataTables_filter',
            'input[aria-controls*="t"]'
        ]:
            try:
                search_input = page.locator(selector)
                if search_input.count() > 0:
                    search_input.first.fill(search_term_num)
                    page.wait_for_timeout(3000)  # 필터링 대기 시간 증가
                    search_attempted = True
                    break
            except:
                continue
        
        if not search_attempted:
            print(f"        -> (정보) 검색 필드를 찾지 못해 전체 테이블 스캔")
        
        # 페이지 재로드 후 HTML 가져오기
        page.wait_for_timeout(2000)
        html = page.content()
        soup = BeautifulSoup(html, 'lxml')
        
        # 테이블 찾기 (여러 선택자 시도)
        table = None
        for selector in ['table#t2844', 'table.ce-table-datatables', 'table.dataTable', 'table.ce-table', 'table tbody']:
            table = soup.select_one(selector)
            if table:
                break
        
        if not table:
            # 모든 테이블 찾기
            all_tables = soup.select('table')
            if all_tables:
                table = all_tables[0]  # 첫 번째 테이블 사용
                print(f"        -> (정보) 테이블 ID로 찾지 못해 첫 번째 테이블 사용")
        
        if not table:
            print(f"        -> (정보) Cinebench 테이블을 찾지 못했습니다.")
            return
        
        rows = table.select('tbody tr')
        if not rows or len(rows) == 0:
            # tbody가 없으면 직접 tr 찾기
            rows = table.select('tr')
            # thead 제외
            rows = [r for r in rows if r.select_one('th') is None]
        
        if not rows:
            print(f"        -> (정보) 테이블 행을 찾지 못했습니다.")
            return
        
        print(f"        -> (디버그) 테이블 행 {len(rows)}개 발견")
        
        sql_bench = text("""
            INSERT INTO benchmark_results (
                part_id, part_type, cpu_model, source, test_name, test_version, scenario,
                metric_name, value, unit, review_url
            ) VALUES (
                :part_id, :part_type, :cpu_model, :source, :test_name, :test_version, :scenario,
                :metric_name, :value, :unit, :review_url
            )
            ON DUPLICATE KEY UPDATE
                value = VALUES(value),
                created_at = CURRENT_TIMESTAMP
        """)
        
        found = False
        # 전체 테이블 스캔 (검색 필터 실패 시 대비) - 모든 행 확인
        print(f"        -> (디버그) 총 {len(rows)}개 행 중 스캔 시작...")
        for idx, row in enumerate(rows):  # 전체 행 확인
            cells = row.select('td')
            if len(cells) < 2:
                continue
            
            # 모델명 셀 찾기 (두 번째 셀)
            model_text = cells[1].get_text(strip=True) if len(cells) >= 2 else ''
            if not model_text:
                model_text = row.get_text(strip=True)
            
            # 검색어 매칭 (더 유연하게)
            # "AMD  Ryzen 5 7500F" 형식에서 "7500F" 또는 "7500" 찾기
            model_lower = model_text.lower()
            
            # 숫자 부분 추출해서 비교
            model_num = re.search(r'\d{3,5}', model_text)
            model_num = model_num.group() if model_num else ''
            
            matches = (
                search_term_full.lower() in model_lower or
                search_term_num.lower() in model_lower or
                model_num == search_term_num or
                ('ryzen' in model_lower and search_term_num in model_text) or
                ('ryzen 5' in model_lower and search_term_num in model_text)
            )
            
            if not matches:
                # 전체 CPU 이름의 주요 단어로 확인
                cpu_keywords = [w for w in cpu_name.split() if len(w) >= 3 and w.lower() not in ['amd', 'intel', '라이젠', '세대', '라파엘']]
                if not any(kw.lower() in model_lower for kw in cpu_keywords):
                    continue
            
            # 디버그: 매칭된 행 출력
            print(f"        -> (디버그) 행 {idx+1} 매칭 성공: {model_text[:60]}")
            
            # R23 점수 찾기 (네 번째 셀, 인덱스 3)
            r23_score = None
            if len(cells) >= 4:
                r23_text = cells[3].get_text(strip=True)
                try:
                    r23_score = int(r23_text.replace(',', '').strip())
                except:
                    pass
                # 디버그
                if idx < 5:
                    print(f"        -> (디버그) R23 텍스트: {r23_text}, 파싱: {r23_score}")
            
            # R23 점수를 찾지 못했으면 전체 행에서 숫자 패턴 찾기
            if not r23_score or r23_score == 0:
                row_text = row.get_text()
                # 큰 숫자 패턴 찾기 (R23은 보통 4자리 이상)
                numbers = re.findall(r'([\d,]{4,})', row_text)
                if numbers:
                    try:
                        # 가장 큰 숫자가 R23 Multi일 가능성 (1000 이상)
                        nums = [int(n.replace(',', '')) for n in numbers if int(n.replace(',', '')) > 1000]
                        if nums:
                            r23_score = max(nums)
                            if idx < 5:
                                print(f"        -> (디버그) 행 텍스트에서 R23 점수 추출: {r23_score}")
                    except:
                        pass
            
            if r23_score and r23_score > 0:
                conn.execute(sql_bench, {
                    "part_id": part_id,
                    "part_type": category_name,
                    "cpu_model": cpu_model,
                    "source": "render4you",
                    "test_name": "Cinebench",
                    "test_version": "R23",
                    "scenario": "Multi",
                    "metric_name": "Score",
                    "value": r23_score,
                    "unit": "pts",
                    "review_url": url
                })
                found = True
                print(f"        -> Cinebench R23 Multi: {r23_score}")
                break
        
        if not found:
            print(f"        -> (정보) Cinebench R23 점수를 찾지 못했습니다. (검색어: {search_term_full})")
    except Exception as e:
        print(f"        -> (경고) Cinebench R23 수집 중 오류: {type(e).__name__} - {str(e)[:100]}")

def scrape_geekbench_v6(page, cpu_name, conn, part_id):
    """
    browser.geekbench.com에서 Geekbench v6 싱글코어/멀티코어 점수 수집
    /search?q= 형식 사용, Windows 최신 결과 우선
    """
    try:
        from datetime import datetime
        
        # CPU 모델명 정규화 (7800X3D -> 7800X3D 또는 7500F -> 7500F)
        model_match = re.search(r'(\d{3,5}\w*(?:F|K|X|G|3D)*|\d{3}[K])', cpu_name, re.I)
        if not model_match:
            return
        
        search_term = model_match.group(1)
        search_num = re.search(r'\d{3,5}', search_term)
        search_num = search_num.group() if search_num else search_term
        
        # CPU 모델명 추출
        cpu_model = search_term
        
        # 중복 체크: 이미 데이터가 있으면 수집하지 않음
        check_sql = text("""
            SELECT EXISTS (
                SELECT 1 FROM benchmark_results 
                WHERE part_id = :part_id 
                AND test_name = 'Geekbench' 
                AND test_version = 'v6'
            )
        """)
        exists_result = conn.execute(check_sql, {"part_id": part_id})
        if exists_result.scalar() == 1:
            print(f"        -> (건너뜀) Geekbench v6 데이터가 이미 존재합니다.")
            return
        
        sql_bench = text("""
            INSERT INTO benchmark_results (
                part_id, part_type, cpu_model, source, test_name, test_version, scenario,
                metric_name, value, unit, review_url
            ) VALUES (
                :part_id, :part_type, :cpu_model, :source, :test_name, :test_version, :scenario,
                :metric_name, :value, :unit, :review_url
            )
            ON DUPLICATE KEY UPDATE
                value = VALUES(value),
                created_at = CURRENT_TIMESTAMP
        """)
        
        # 통합 검색 페이지 사용 (/search?q=)
        search_url = f"https://browser.geekbench.com/search?q={quote_plus(search_term)}"
        print(f"      -> Geekbench v6 검색: {search_url}")
        
        page.goto(search_url, wait_until='networkidle', timeout=15000)
        page.wait_for_timeout(3000)
        
        html = page.content()
        soup = BeautifulSoup(html, 'lxml')
        
        # 검색 결과 항목 찾기 (.list-col-inner)
        list_items = soup.select('.list-col-inner')
        print(f"        -> (디버그) Geekbench 검색 결과 {len(list_items)}개 발견")
        
        # 매칭된 결과 수집 (날짜와 플랫폼 정보 포함)
        matched_results = []
        
        for idx, item in enumerate(list_items[:100]):  # 최대 100개 확인
            model_elem = item.select_one('.list-col-model')
            if not model_elem:
                continue
            
            model_text = model_elem.get_text(strip=True)
            model_lower = model_text.lower()
            
            # CPU 이름 매칭 확인
            matches = (
                search_term.lower() in model_lower or
                search_num.lower() in model_lower or
                ('ryzen' in model_lower and search_num in model_text) or
                ('ryzen 5' in model_lower and search_num in model_text)
            )
            
            if not matches:
                # 전체 CPU 이름에서도 확인
                cpu_words = [w for w in cpu_name.split() if len(w) > 2 and w.lower() not in ['amd', 'intel', '라이젠', '세대', '라파엘']]
                if not any(word.lower() in model_lower for word in cpu_words):
                    continue
            
            # 날짜 추출 (Uploaded)
            date_text = ''
            date_elem = item.select_one('.list-col-text')
            if date_elem:
                date_text = date_elem.get_text(strip=True)
                # "Nov 03, 2025" 형식 파싱
                date_match = re.search(r'(\w+ \d{1,2}, \d{4})', date_text)
                if date_match:
                    date_text = date_match.group(1)
            
            # 플랫폼 추출 (Platform)
            platform = ''
            platform_elems = item.select('.list-col-text')
            if len(platform_elems) >= 2:
                platform = platform_elems[1].get_text(strip=True)
            
            # 점수 추출
            score_elems = item.select('.list-col-text-score')
            single_score = None
            multi_score = None
            
            if len(score_elems) >= 1:
                try:
                    single_score = int(score_elems[0].get_text(strip=True))
                except:
                    pass
            
            if len(score_elems) >= 2:
                try:
                    multi_score = int(score_elems[1].get_text(strip=True))
                except:
                    pass
            
            if single_score and single_score > 0:
                # 날짜 파싱 (정렬용)
                date_obj = None
                try:
                    if date_text:
                        date_obj = datetime.strptime(date_text, "%b %d, %Y")
                except:
                    pass
                
                matched_results.append({
                    'model': model_text,
                    'date': date_obj,
                    'date_text': date_text,
                    'platform': platform.lower(),
                    'single': single_score,
                    'multi': multi_score,
                    'idx': idx
                })
                
                if idx < 5:
                    print(f"        -> (디버그) 매칭 항목 {idx+1}: {model_text[:50]} | {platform} | {date_text} | Single: {single_score}, Multi: {multi_score}")
        
        if not matched_results:
            print(f"        -> (정보) Geekbench v6 점수를 찾지 못했습니다. (검색어: {search_term})")
            return
        
        # 정렬: Windows 우선, 그 다음 최신 날짜 우선
        def sort_key(result):
            platform_score = 0 if 'windows' in result['platform'] else 1
            date_score = result['date'] if result['date'] else datetime(1900, 1, 1)
            return (platform_score, -date_score.timestamp())  # 음수로 최신 날짜 우선
        
        matched_results.sort(key=sort_key)
        
        # 최상위 결과 선택 (Windows 최신 우선)
        best_result = matched_results[0]
        print(f"        -> (정보) 선택된 결과: {best_result['model'][:50]} | {best_result['platform']} | {best_result['date_text']}")
        
        # Single-core 점수 저장
        if best_result['single']:
            conn.execute(sql_bench, {
                "part_id": part_id,
                "part_type": "CPU",
                "cpu_model": cpu_model,
                "source": "geekbench",
                "test_name": "Geekbench",
                "test_version": "v6",
                "scenario": "Single-core",
                "metric_name": "Score",
                "value": best_result['single'],
                "unit": "pts",
                "review_url": search_url
            })
            print(f"        -> Geekbench v6 Single-core: {best_result['single']}")
        
        # Multi-core 점수 저장
        if best_result['multi']:
            conn.execute(sql_bench, {
                "part_id": part_id,
                "part_type": "CPU",
                "cpu_model": cpu_model,
                "source": "geekbench",
                "test_name": "Geekbench",
                "test_version": "v6",
                "scenario": "Multi-core",
                "metric_name": "Score",
                "value": best_result['multi'],
                "unit": "pts",
                "review_url": search_url
            })
            print(f"        -> Geekbench v6 Multi-core: {best_result['multi']}")
            
    except Exception as e:
        print(f"        -> (경고) Geekbench v6 수집 중 오류: {type(e).__name__} - {str(e)[:100]}")

def scrape_blender_median(page, cpu_name, conn, part_id):
    """
    opendata.blender.org에서 Blender Median Score 수집
    DataTables API 사용: /benchmarks/query/?compute_type=CPU&response_type=datatables
    """
    try:
        # CPU 모델명 정규화
        model_match = re.search(r'(\d{3,5}\w*(?:F|K|X|G|3D)*|\d{3}[K])', cpu_name, re.I)
        if not model_match:
            return
        
        search_term = model_match.group(1)
        cpu_model = search_term
        
        # 중복 체크: 이미 데이터가 있으면 수집하지 않음
        check_sql = text("""
            SELECT EXISTS (
                SELECT 1 FROM benchmark_results 
                WHERE part_id = :part_id 
                AND test_name = 'Blender' 
                AND test_version = '4.5.0'
                AND scenario = 'Median'
            )
        """)
        exists_result = conn.execute(check_sql, {"part_id": part_id})
        if exists_result.scalar() == 1:
            print(f"        -> (건너뜀) Blender Median Score 데이터가 이미 존재합니다.")
            return
        # Blender Open Data API 호출 (DataTables 형식)
        url = "https://opendata.blender.org/benchmarks/query/"
        params = {
            "compute_type": "CPU",
            "group_by": "device_name",
            "blender_version": "4.5.0",
            "response_type": "datatables"
        }
        
        print(f"      -> Blender Median Score 검색: {url}")
        
        # DataTables API 호출
        response = requests.get(url, params=params, timeout=15)
        if response.status_code != 200:
            print(f"        -> (경고) API 응답 오류: {response.status_code}")
            return
        
        try:
            data = response.json()
        except:
            print(f"        -> (경고) JSON 파싱 실패")
            return
        
        # DataTables 응답 구조: {columns: [...], rows: [[...], [...]]}
        if not isinstance(data, dict) or 'rows' not in data:
            print(f"        -> (경고) 잘못된 응답 구조")
            return
        
        # columns에서 'Median Score' 컬럼 인덱스 찾기
        columns = data.get('columns', [])
        median_score_idx = None
        device_name_idx = None
        
        for i, col in enumerate(columns):
            display_name = col.get('display_name', '') if isinstance(col, dict) else str(col)
            if 'Median Score' in display_name or 'median' in display_name.lower():
                median_score_idx = i
            if 'Device Name' in display_name or 'device_name' in display_name.lower():
                device_name_idx = i
        
        if median_score_idx is None:
            print(f"        -> (경고) Median Score 컬럼을 찾지 못했습니다.")
            return
        
        # rows에서 CPU 이름 매칭하여 점수 찾기
        rows = data.get('rows', [])
        median_score = None
        
        for row in rows:
            if not isinstance(row, list) or len(row) <= max(median_score_idx, device_name_idx if device_name_idx else 0):
                continue
            
            device_name = ''
            if device_name_idx is not None and device_name_idx < len(row):
                device_name = str(row[device_name_idx])
                # HTML 태그 제거
                if '<a' in device_name:
                    device_name = re.sub(r'<[^>]+>', '', device_name)
                device_name = device_name.strip()
            
            # 검색어 매칭
            if (search_term.lower() in device_name.lower() or 
                any(word in device_name.lower() for word in cpu_name.split() if len(word) > 3)):
                if median_score_idx < len(row):
                    score_val = row[median_score_idx]
                    if score_val and score_val != 0:
                        try:
                            median_score = float(score_val)
                            break
                        except:
                            pass
        
        if median_score:
            sql_bench = text("""
                INSERT INTO benchmark_results (
                    part_id, part_type, cpu_model, source, test_name, test_version, scenario,
                    metric_name, value, unit, review_url
                ) VALUES (
                    :part_id, :part_type, :cpu_model, :source, :test_name, :test_version, :scenario,
                    :metric_name, :value, :unit, :review_url
                )
                ON DUPLICATE KEY UPDATE
                    value = VALUES(value),
                    created_at = CURRENT_TIMESTAMP
            """)
            conn.execute(sql_bench, {
                "part_id": part_id,
                "part_type": "CPU",
                "cpu_model": cpu_model,
                "source": "blender_opendata",
                "test_name": "Blender",
                "test_version": "4.5.0",
                "scenario": "Median",
                "metric_name": "Score",
                "value": median_score,
                "unit": "pts",
                "review_url": f"{url}?{'&'.join([f'{k}={v}' for k, v in params.items()])}"
            })
            print(f"        -> Blender Median Score: {median_score}")
        else:
            print(f"        -> (정보) Blender Median Score를 찾지 못했습니다.")
    except Exception as e:
        print(f"        -> (경고) Blender Median Score 수집 중 오류: {type(e).__name__} - {str(e)[:100]}")

def scrape_3dmark_timespy(page, cpu_name, conn, part_id):
    """
    topcpu.net에서 3DMark Time Spy CPU 점수 수집
    """
    try:
        # CPU 모델명 정규화
        model_match = re.search(r'(\d{4,5}\w*(?:F|K|X|G|3D)*|\d{3}[K])', cpu_name, re.I)
        if not model_match:
            return
        
        search_term = model_match.group(1)
        url = f"https://www.topcpu.net/ko/gpu-r/3dmark-time-spy"
        
        print(f"      -> 3DMark Time Spy 검색: {url}")
        
        page.goto(url, wait_until='networkidle', timeout=15000)
        page.wait_for_timeout(1000)
        
        # 검색어 입력 및 검색 버튼 클릭 시도
        try:
            search_input = page.locator('input[type="search"], input[placeholder*="검색"], input[name*="search"]')
            if search_input.count() > 0:
                search_input.first.fill(search_term)
                page.wait_for_timeout(500)
                search_btn = page.locator('button[type="submit"], button:has-text("검색")')
                if search_btn.count() > 0:
                    search_btn.first.click()
                    page.wait_for_timeout(2000)
        except:
            pass
        
        html = page.content()
        soup = BeautifulSoup(html, 'lxml')
        
        # 테이블/리스트에서 CPU 이름 매칭하여 점수 찾기
        rows = soup.select('table tbody tr, .cpu-item, .benchmark-item')
        sql_bench = text("""
            INSERT INTO benchmark_results (
                part_id, source, test_name, test_version, scenario,
                metric_name, value, unit, review_url
            ) VALUES (
                :part_id, :source, :test_name, :test_version, :scenario,
                :metric_name, :value, :unit, :review_url
            )
            ON DUPLICATE KEY UPDATE
                value = VALUES(value),
                created_at = CURRENT_TIMESTAMP
        """)
        
        found = False
        for row in rows[:5]:  # 최대 5개 확인
            row_text = row.get_text()
            if search_term.lower() not in row_text.lower():
                continue
            
            # 점수 추출 (숫자 패턴)
            score_match = re.search(r'(\d{4,5})', row_text)
            if score_match:
                score = int(score_match.group(1))
                conn.execute(sql_bench, {
                    "part_id": part_id,
                    "source": "topcpu",
                    "test_name": "3DMark Time Spy",
                    "test_version": "",
                    "scenario": "CPU",
                    "metric_name": "Score",
                    "value": score,
                    "unit": "pts",
                    "review_url": url
                })
                found = True
                print(f"        -> 3DMark Time Spy CPU: {score}")
                break
        
        if not found:
            print(f"        -> (정보) 3DMark Time Spy 점수를 찾지 못했습니다.")
    except Exception as e:
        print(f"        -> (경고) 3DMark Time Spy 수집 중 오류: {type(e).__name__} - {str(e)[:100]}")

def scrape_category(page, category_name, query, collect_reviews=False, collect_benchmarks=False):
    """
    카테고리별 크롤링 함수
    
    Args:
        page: Playwright 페이지 객체
        category_name: 카테고리 이름 (예: 'CPU')
        query: 검색 쿼리
        collect_reviews: 퀘이사존 리뷰 수집 여부
        collect_benchmarks: 벤치마크 정보 수집 여부
    """
    # --- 1. (신규) parts 테이블 INSERT SQL ---
    # ON DUPLICATE KEY UPDATE: 이미 수집된 상품(link 기준)이면 가격, 리뷰 수 등만 업데이트합니다.
    sql_parts = text("""
        INSERT INTO parts (
            name, category, price, link, img_src, manufacturer, 
            review_count, star_rating, warranty_info
        ) VALUES (
            :name, :category, :price, :link, :img_src, :manufacturer,
            :review_count, :star_rating, :warranty_info
        )
        ON DUPLICATE KEY UPDATE
            price=VALUES(price), review_count=VALUES(review_count), 
            star_rating=VALUES(star_rating), manufacturer=VALUES(manufacturer), 
            warranty_info=VALUES(warranty_info)
    """)
    
    # --- 2. (신규) part_specs 테이블 INSERT SQL ---
    # ON DUPLICATE KEY UPDATE: 이미 스펙이 있으면 새 스펙으로 덮어씁니다.
    sql_specs = text("""
        INSERT INTO part_spec (part_id, specs)
        VALUES (:part_id, :specs)
        ON DUPLICATE KEY UPDATE
            specs=VALUES(specs)
    """)

    # --- 3. (신규) community_reviews 테이블 INSERT SQL ---
    # ON DUPLICATE KEY UPDATE: review_url이 이미 존재하면 무시(아무것도 안 함)
    sql_review = text("""
        INSERT INTO community_reviews (
            part_id, part_type, cpu_model, source, review_url, raw_text
        ) VALUES (
            :part_id, :part_type, :cpu_model, :source, :review_url, :raw_text
        )
        ON DUPLICATE KEY UPDATE
            part_id = part_id 
    """)
    # --- 4. (신규) 퀘이사존 리뷰 존재 여부 확인 SQL ---
    sql_check_review = text("SELECT EXISTS (SELECT 1 FROM community_reviews WHERE part_id = :part_id)")

    with engine.connect() as conn:
        for page_num in range(1, CRAWL_PAGES + 1): # CRAWL_PAGES 변수 사용하도록 수정
            url = f'https://search.danawa.com/dsearch.php?query={query}&page={page_num}'
            print(f"--- '{category_name}' 카테고리, {page_num}페이지 목록 수집 ---")
            
            try:
                page.goto(url, wait_until='load', timeout=20000)
                page.wait_for_selector('ul.product_list', timeout=10000)

                # 페이지 스크롤 다운 (기존 로직 유지)
                for _ in range(3):
                    page.mouse.wheel(0, 1500)
                    page.wait_for_timeout(500)
                page.wait_for_load_state('networkidle', timeout=5000)
                
                list_html = page.content()
                list_soup = BeautifulSoup(list_html, 'lxml')
                product_items = list_soup.select('li.prod_item[id^="productItem"]')

                if not product_items:
                    print("--- 현재 페이지에 상품이 없어 다음 카테고리로 넘어갑니다. ---")
                    break
                
                for item in product_items:
                    name_tag = item.select_one('p.prod_name > a')
                    price_tag = item.select_one('p.price_sect > a > strong')
                    img_tag = item.select_one('div.thumb_image img')

                    if not all([name_tag, price_tag, img_tag]):
                        continue

                    name = name_tag.text.strip()
                    link = name_tag['href']
                    
                    img_src = img_tag.get('data-original-src') or img_tag.get('src', '')
                    if img_src and not img_src.startswith('https:'):
                        img_src = 'https:' + img_src

                    try:
                        price = int(price_tag.text.strip().replace(',', ''))
                    except ValueError:
                        print(f"  - 가격 정보가 유효하지 않아 건너뜁니다: {name} (값: {price_tag.text.strip()})")
                        continue
                    
                    # 리뷰, 별점 수집 (기존 로직 유지)
                    review_count = 0
                    star_rating = 0.0
                    rating_review_count = 0 # (참고: 이 값은 현재 DB에 저장되지 않음)

                    meta_items = item.select('.prod_sub_meta .meta_item')
                    for meta in meta_items:
                        if '상품의견' in meta.text:
                            count_tag = meta.select_one('.dd strong')
                            if count_tag and (match := re.search(r'[\d,]+', count_tag.text)):
                                review_count = int(match.group().replace(',', ''))
                        
                        elif '상품리뷰' in meta.text:
                            score_tag = meta.select_one('.text__score')
                            if score_tag:
                                try: star_rating = float(score_tag.text.strip())
                                except (ValueError, TypeError): star_rating = 0.0
                    
                    spec_tag = item.select_one('div.spec_list')
                    spec_string = spec_tag.text.strip() if spec_tag else ""
                    
                    # --- 3. (수정) 파서 호출 및 보증 기간(warrantyInfo) 추출 ---
                    parser_func = PARSER_MAP.get(category_name)
                    detailed_specs = parser_func(name, spec_string) if parser_func else {}
                    
                    # 스펙 문자열에서 '보증' 정보 추출 (AI 판단 근거)
                    warranty_info = None
                    warranty_match = re.search(r'(?:A/S|보증)\s*([\w\d년개월\s]+)', spec_string)
                    if warranty_match:
                        warranty_info = warranty_match.group(1).strip()
                    
                    # 제조사 정보는 detailed_specs에서 가져오거나 이름에서 추출
                    manufacturer = detailed_specs.get("manufacturer")
                    if not manufacturer and name:
                        manufacturer = name.split()[0]

                    # --- 👇 [수정 1] "시작" 로그 추가 ---
                    print(f"\n  [처리 시작] {name}") # 한 줄 띄우고 시작
                    
                    # --- 4. (신규) 1단계: `parts` 테이블에 공통 정보 저장 ---
                    parts_params = {
                        "name": name, "category": category_name, "price": price, "link": link,
                        "img_src": img_src, "manufacturer": manufacturer, 
                        "review_count": review_count, "star_rating": star_rating,
                        "warranty_info": warranty_info
                    }
                    
                    # 트랜잭션 시작 (중요)
                    trans = conn.begin()
                    try:
                        # parts 테이블에 삽입
                        result = conn.execute(sql_parts, parts_params)

                        
                        
                        # 방금 INSERT된 part_id 또는 이미 존재하는 part_id 가져오기
                        part_id = None
                        if result.lastrowid: # 새 데이터가 INSERT 된 경우
                            part_id = result.lastrowid
                        else: # ON DUPLICATE KEY UPDATE가 발생한 경우 (link 기준)
                            find_id_sql = text("SELECT id FROM parts WHERE link = :link")
                            part_id_result = conn.execute(find_id_sql, {"link": link})
                            part_id = part_id_result.scalar_one_or_none()

                        if part_id:
                            # --- 5. (신규) 2단계: `part_specs` 테이블에 세부 스펙 저장 ---
                            
                            # 1. 다나와에서 기본 스펙 파싱 (기존)
                            detailed_specs = parser_func(name, spec_string) if parser_func else {}

                            # --- 👇 [신규] 3대 벤치마크 수집 (Cinebench, Geekbench, Blender) ---
                            if collect_benchmarks and category_name == 'CPU':
                                print(f"      -> 벤치마크 수집 시도...")
                                # (1) Cinebench R23 (render4you.com)
                                scrape_cinebench_r23(page, name, conn, part_id, category_name)
                                time.sleep(2)
                                # (2) Geekbench v6 (browser.geekbench.com)
                                scrape_geekbench_v6(page, name, conn, part_id)
                                time.sleep(2)
                                # (3) Blender Median Score (opendata.blender.org)
                                scrape_blender_median(page, name, conn, part_id)
                                time.sleep(2)
                                
                                print(f"      -> 벤치마크 수집 완료.")

                            # 2. DB에 저장 (기존)
                            specs_json = json.dumps(detailed_specs, ensure_ascii=False)
                            
                            specs_params = {
                                "part_id": part_id,
                                "specs": specs_json
                            }
                            conn.execute(sql_specs, specs_params) # part_spec 테이블에 저장


                        # --- (수정) 3단계: 퀘이사존 리뷰 수집 (선택적) ---
                        if collect_reviews and part_id: # part_id를 성공적으로 가져왔다면
                            # 퀘이사존 리뷰가 DB에 이미 저장되어 있는지 확인
                            review_exists_result = conn.execute(sql_check_review, {"part_id": part_id})
                            review_exists = review_exists_result.scalar() == 1 # (True 또는 False)

                            if not review_exists:
                                print(f"      -> 퀘이사존 리뷰 없음, 수집 시도...") # 4칸 -> 6칸
                                # (신규) category_name과 detailed_specs를 인자로 추가 전달
                                scrape_quasarzone_reviews(page, conn, sql_review, part_id, name, category_name, detailed_specs)
                            # else:
                                # (선택적) 이미 리뷰가 있다면 건너뛰었다고 로그 표시
                                # print(f"    -> (건너뜀) 이미 퀘이사존 리뷰가 수집된 상품입니다.")

                        trans.commit() # 트랜잭션 완료
                        # --- 👇 [수정 3] "완료" 로그 수정 및 들여쓰기 추가 ---
                        print(f"    [처리 완료] {name} (댓글: {review_count}) 저장 성공.")
                        
                    except Exception as e:
                        trans.rollback() # 오류 발생 시 롤백

                        # --- 👇 [수정 4] "오류" 로그 수정 및 들여쓰기 추가 ---
                        print(f"    [처리 오류] {name} 저장 중 오류 발생: {e}") 

                    # --- 👇 [필수] 상품 1개만 테스트하기 위해 break 추가 ---
                        print("\n--- [테스트] 상품 1개 처리 완료, 크롤러를 중단합니다. ---")
                        break
                        # --- 👆 [필수] ---

            except Exception as e:
                print(f"--- {page_num}페이지 처리 중 오류 발생: {e}. 다음 페이지로 넘어갑니다. ---")
                continue

# --- run_crawler 함수 수정 (CRAWL_PAGES 변수 전달) ---
# 기존 run_crawler 함수를 찾아서 scrape_category 호출 부분을 수정합니다.


def get_user_choice():
    """
    사용자로부터 크롤링 옵션을 Y/N 형식으로 입력받습니다.
    """
    print("\n" + "="*60)
    print("크롤링 옵션 선택")
    print("="*60)
    print("1. 다나와 부품 정보 및 가격/스펙 수집 (필수)")
    print("   -> 항상 수집됩니다.")
    
    while True:
        choice = input("\n2. 퀘이사존 리뷰 기사 수집? (Y/N): ").strip().upper()
        if choice in ['Y', 'N']:
            collect_reviews = (choice == 'Y')
            break
        print("   -> Y 또는 N을 입력해주세요.")
    
    while True:
        choice = input("3. 벤치마크 정보 수집? (Y/N): ").strip().upper()
        if choice in ['Y', 'N']:
            collect_benchmarks = (choice == 'Y')
            break
        print("   -> Y 또는 N을 입력해주세요.")
    
    print("\n" + "="*60)
    print("선택된 옵션:")
    print(f"  - 다나와 부품 정보: 필수 (항상 수집)")
    print(f"  - 퀘이사존 리뷰: {'수집함' if collect_reviews else '건너뜀'}")
    print(f"  - 벤치마크 정보: {'수집함' if collect_benchmarks else '건너뜀'}")
    print("="*60 + "\n")
    
    return collect_reviews, collect_benchmarks

def run_crawler(collect_reviews=False, collect_benchmarks=False):
    """
    크롤러 실행 함수
    
    Args:
        collect_reviews: 퀘이사존 리뷰 수집 여부
        collect_benchmarks: 벤치마크 정보 수집 여부
    """
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=HEADLESS_MODE, slow_mo=SLOW_MOTION) 
        page = browser.new_page()
        stealth_sync(page)
        page.set_extra_http_headers({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"})

        # 퀘이사존 리뷰 수집이 활성화된 경우에만 세션 획득
        if collect_reviews:
            try:
                print("--- (봇 우회) 퀘이사존 메인 리뷰 페이지 1회 방문 (세션 획득) ---")
                page.goto("https://quasarzone.com/bbs/qc_qsz", wait_until='networkidle', timeout=20000)
                page.wait_for_timeout(1000) # 1초 대기
                print("--- 퀘이사존 세션 획득 완료 ---")
            except Exception as e:
                print(f"--- (경고) 퀘이사존 메인 페이지 방문 실패 (무시하고 계속): {e}")

        for category_name, query in CATEGORIES.items():
            scrape_category(page, category_name, query, collect_reviews, collect_benchmarks)
        browser.close()
        print("\n모든 카테고리 데이터 수집을 완료했습니다.")

# --- (신규) 퀘이사존 검색을 위한 핵심 키워드 추출 함수 ---
def get_search_keyword(part_name, category_name, detailed_specs):
    """
    상품명과 카테고리, 파싱된 스펙을 기반으로 퀘이사존 검색에 가장 적합한
    핵심 키워드(예: '7500F', 'RTX 4070', 'B650')를 추출합니다.
    """
    
    # 1. GPU/메인보드는 파싱된 칩셋 이름이 가장 정확함
    if category_name == '그래픽카드':
        keyword = detailed_specs.get('nvidia_chipset') or \
                  detailed_specs.get('amd_chipset') or \
                  detailed_specs.get('intel_chipset')
        if keyword:
            # "GeForce RTX 4070" -> "RTX 4070"
            return keyword.replace("GeForce", "").strip()

    if category_name == '메인보드':
        keyword = detailed_specs.get('chipset') # 예: B760, X670
        if keyword: return keyword

    # 2. CPU (Regex로 모델명 추출 시도)
    if category_name == 'CPU':
        # 예: 7500F, 14400F, 7800X3D, 265K (신형 모델)
        # (7800X3D, 14900KF, 7500F, 5600, 265K, 245K, 9600X 등)
        match = re.search(r'(\d{4,5}\w*(?:F|K|X|G|3D)*|\d{3}[K])', part_name, re.I)
        if match:
            return match.group(1)

    # 3. 기타 부품 (이름에서 제조사 + 괄호 내용 제외)
    # 예: "MSI MAG A750GL 80PLUS골드..." -> "MAG A750GL"
    search_query = " ".join(part_name.split()[1:]) # 기본 (제조사 제외)
    search_query = re.sub(r'\([^)]+\)', '', search_query).strip() # 괄호 내용 제거
    search_query = re.sub(r'(\d{3,4}W)', '', search_query).strip() # 파워 용량(W) 제거
    
    # 너무 길면 앞 2~3 단어만 사용
    if len(search_query.split()) > 3:
        search_query = " ".join(search_query.split()[:3])
        
    return search_query

# --- (수정) 퀘이사존 리뷰 크롤링 함수 (봇 우회 강화) ---
def scrape_quasarzone_reviews(page, conn, sql_review, part_id, part_name, category_name, detailed_specs):
    """
    (봇 우회 강화) ... (중략)
    """
    try:
        search_keyword = get_search_keyword(part_name, category_name, detailed_specs)
        if not search_keyword:
            print(f"        -> (정보) '{part_name}'에 대한 핵심 키워드 추출 불가, 건너뜀.") # 6칸 -> 8칸
            return

        # --- 👇 [수정] 이 'try...except' 블록 전체를 삭제하거나 주석 처리합니다. ---
        # try:
        #     print(f"      -> (봇 우회) 퀘이사존 메인 리뷰 페이지 방문 시도...")
        #     page.goto("https://quasarzone.com/bbs/qc_qsz", wait_until='networkidle', timeout=10000)
        #     page.wait_for_timeout(1000) # 1초 대기
        # except Exception as e:
        #     print(f"      -> (경고) 메인 페이지 방문 실패 (무시하고 계속): {e}")
        # --- [수정] 여기까지 ---

        # 단일 검색 실행: 공식기사(칼럼/리뷰) 그룹 제목검색 1회만 수행
        q_url = (
            f"https://quasarzone.com/groupSearches?group_id=columns"
            f"&keyword={quote_plus(search_keyword)}&kind=subject"
        )

        print(f"        -> 퀘이사존 공식기사 검색 (키워드: {search_keyword}): {q_url}") # 6칸 -> 8칸
        # (중복된 print문 한 줄 삭제)
        try:
            page.goto(q_url, wait_until='networkidle', timeout=30000)
        except Exception as e:
            print(f"        -> (오류) 검색 페이지 로딩 실패: {e}") # 6칸 -> 8칸
            return

        # 가벼운 스크롤로 동적 로딩 유도
        page.mouse.wheel(0, 1200)
        page.wait_for_timeout(500)

        links_selector = (
            'a[href*="/bbs/qc_qsz/views/"], '
            'a[href*="/bbs/qc_bench/views/"]'
        )

        links_selector = (
            'a[href*="/bbs/qc_qsz/views/"], '
            'a[href*="/bbs/qc_bench/views/"]'
        )

        found_link = None
        try:
            # 1. 페이지에 있는 모든 리뷰 링크를 가져옵니다.
            review_links = page.locator(links_selector).all() 
            
            # 2. 링크를 순회합니다.
            for link in review_links:
                title = (link.inner_text() or "").lower()
                keyword_lower = search_keyword.lower()
                
                # 3. 링크의 텍스트(제목)에 키워드가 포함되어 있는지 확인합니다.
                if keyword_lower in title:
                    href = link.get_attribute('href')
                    if href:
                        found_link = href
                        break # 4. 일치하는 첫 번째 링크를 찾으면 중단
            
        except Exception as e:
            print(f"      -> (경고) 링크 목록을 파싱하는 중 오류: {e}")
            pass

        if not found_link: # 5. 일치하는 링크를 못 찾았다면
            print(f"      -> (정보) 퀘이사존에서 '{search_keyword}' 관련 리뷰를 찾지 못했습니다.")
            return

        review_url = found_link # 6. 일치하는 링크로 리뷰 수집 시작
        if review_url and not review_url.startswith('https://'):
                review_url = f"https://quasarzone.com{review_url}"

        print(f"        -> [1/1] 리뷰 페이지 이동: {review_url}")
        page.goto(review_url, wait_until='domcontentloaded', timeout=15000)
        page.wait_for_timeout(800) # 봇 탐지 방지 대기

        content_element = page.locator('.view-content')
        if not content_element.is_visible(timeout=5000):
                print("        -> (오류) 리뷰 본문을 찾을 수 없습니다. (timeout)")
        return
            
        raw_text = content_element.inner_text()
        if len(raw_text) < 100:
                print("        -> (건너뜀) 리뷰 본문이 너무 짧습니다. (100자 미만)")
        return

        # CPU 모델명 추출 (7500F, 7800X3D 등)
        cpu_model = None
        if category_name == 'CPU':
            model_match = re.search(r'(\d{3,5}\w*(?:F|K|X|G|3D)*|\d{3}[K])', part_name, re.I)
            if model_match:
                cpu_model = model_match.group(1)
        
        # DB에 저장 (1건)
        review_params = {
                "part_id": part_id,
                "part_type": category_name,
                "cpu_model": cpu_model,
                "source": "퀘이사존",
                "review_url": review_url,
                "raw_text": raw_text
            }
        conn.execute(sql_review, review_params)
        print("      -> 퀘이사존 리뷰 1건 저장 완료.")
        
    except Exception as e:
        if "Target page, context or browser has been closed" in str(e):
            print("      -> (치명적 오류) 크롤러 페이지가 닫혔습니다. 중단합니다.")
            raise 
        
        print(f"      -> (경고) 퀘이사존 리뷰 수집 중 오류 발생 (무시함): {type(e).__name__} - {str(e)[:100]}...")
        pass

if __name__ == "__main__":
    # 사용자로부터 크롤링 옵션 입력받기
    collect_reviews, collect_benchmarks = get_user_choice()
    run_crawler(collect_reviews=collect_reviews, collect_benchmarks=collect_benchmarks)