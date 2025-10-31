import re
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
from sqlalchemy import create_engine, text
import json
import time
from playwright_stealth import stealth_sync
from urllib.parse import quote_plus


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
    'CPU': 'cpu', '쿨러': 'cooler', '메인보드': 'mainboard', 'RAM': 'RAM',
    '그래픽카드': 'vga', 'SSD': 'ssd', 'HDD': 'hdd', '케이스': 'pc case', '파워': 'power'
}

# --- 5. SQLAlchemy 엔진 생성 ---
try:
    engine = create_engine(f'mysql+mysqlconnector://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}')
    with engine.connect() as conn:
        print("DB 연결 성공")
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

def scrape_category(page, category_name, query):
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
            part_id, source, review_url, raw_text
        ) VALUES (
            :part_id, :source, :review_url, :raw_text
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
                            
                            # detailed_specs 딕셔너리를 JSON 문자열로 변환
                            # ensure_ascii=False: 한글이 깨지지 않도록 함
                            specs_json = json.dumps(detailed_specs, ensure_ascii=False)
                            
                            specs_params = {
                                "part_id": part_id,
                                "specs": specs_json
                            }
                            
                            # part_specs 테이블에 삽입/업데이트
                            conn.execute(sql_specs, specs_params)

                        # --- (수정) 3단계: 퀘이사존 리뷰 수집 ---
                        if part_id: # part_id를 성공적으로 가져왔다면
                            # 퀘이사존 리뷰가 DB에 이미 저장되어 있는지 확인
                            review_exists_result = conn.execute(sql_check_review, {"part_id": part_id})
                            review_exists = review_exists_result.scalar() == 1 # (True 또는 False)

                            if not review_exists:
                                print(f"    -> 퀘이사존 리뷰 없음, 수집 시도...")
                                # (신규) category_name과 detailed_specs를 인자로 추가 전달
                                scrape_quasarzone_reviews(page, conn, sql_review, part_id, name, category_name, detailed_specs)
                            # else:
                                # (선택적) 이미 리뷰가 있다면 건너뛰었다고 로그 표시
                                # print(f"    -> (건너뜀) 이미 퀘이사존 리뷰가 수집된 상품입니다.")

                        trans.commit() # 트랜잭션 완료
                        print(f"  ✅ {name} (댓글: {review_count})")
                        
                    except Exception as e:
                        trans.rollback() # 오류 발생 시 롤백
                        print(f"  ❌ {name} 저장 중 오류 발생: {e}")

            except Exception as e:
                print(f"--- {page_num}페이지 처리 중 오류 발생: {e}. 다음 페이지로 넘어갑니다. ---")
                continue

# --- run_crawler 함수 수정 (CRAWL_PAGES 변수 전달) ---
# 기존 run_crawler 함수를 찾아서 scrape_category 호출 부분을 수정합니다.


def run_crawler():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=HEADLESS_MODE, slow_mo=SLOW_MOTION) 
        page = browser.new_page()
        stealth_sync(page)
        page.set_extra_http_headers({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"})

        for category_name, query in CATEGORIES.items():
            # CRAWL_PAGES 변수를 사용하도록 scrape_category 함수를 수정했으므로
            # 이 부분은 변경할 필요 없이 그대로 둡니다.
            scrape_category(page, category_name, query)
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
    (봇 우회 강화) 메인 리뷰 페이지를 경유한 후,
    핵심 키워드로 퀘이사존 통합검색을 수행하고, 결과가 나올 때까지 대기한 후
    '리뷰/벤치마크' 게시판의 글을 수집하여 DB에 저장합니다.
    """
    try:
        search_keyword = get_search_keyword(part_name, category_name, detailed_specs)
        if not search_keyword:
            print(f"      -> (정보) '{part_name}'에 대한 핵심 키워드 추출 불가, 건너뜀.")
            return

        # --- (신규) 1. 봇 우회를 위해 메인 리뷰 페이지를 먼저 방문 (쿠키/세션 획득) ---
        try:
            print(f"      -> (봇 우회) 퀘이사존 메인 리뷰 페이지 방문 시도...")
            page.goto("https://quasarzone.com/bbs/qc_qsz", wait_until='networkidle', timeout=10000)
            page.wait_for_timeout(1000) # 1초 대기
        except Exception as e:
            print(f"      -> (경고) 메인 페이지 방문 실패 (무시하고 계속): {e}")
        # --- (신규 1. 끝) ---

        # 단일 검색 실행: 공식기사(칼럼/리뷰) 그룹 제목검색 1회만 수행
        q_url = (
            f"https://quasarzone.com/groupSearches?group_id=columns"
            f"&keyword={quote_plus(search_keyword)}&kind=subject"
        )
        print(f"      -> 퀘이사존 공식기사 검색 (키워드: {search_keyword}): {q_url}")
        try:
            page.goto(q_url, wait_until='networkidle', timeout=30000)
        except Exception as e:
            print(f"      -> (오류) 검색 페이지 로딩 실패: {e}")
            return

        # 가벼운 스크롤로 동적 로딩 유도
        page.mouse.wheel(0, 1200)
        page.wait_for_timeout(500)

        links_selector = (
            'a[href*="/bbs/qc_qsz/views/"], '
            'a[href*="/bbs/qc_bench/views/"]'
        )

        # 우선 locator로 첫 링크만 가져오기 시도
        first_link = None
        try:
            review_links = page.locator(links_selector)
            if review_links.count() > 0:
                href = review_links.nth(0).get_attribute('href')
                first_link = href
        except Exception:
            pass

        # 폴백: BeautifulSoup으로 첫 링크만 파싱
        if not first_link:
            html = page.content()
            soup = BeautifulSoup(html, 'lxml')
            a = soup.select_one('a[href*="/bbs/qc_qsz/views/"], a[href*="/bbs/qc_bench/views/"]')
            if a and a.get('href'):
                first_link = a.get('href')

        if not first_link:
            print(f"      -> (정보) 퀘이사존에서 '{search_keyword}' 관련 리뷰를 찾지 못했습니다.")
            return

        review_url = first_link
        if review_url and not review_url.startswith('https://'):
            review_url = f"https://quasarzone.com{review_url}"

        print(f"        -> [1/1] 리뷰 페이지 이동: {review_url}")
        page.goto(review_url, wait_until='load', timeout=15000)
        page.wait_for_timeout(800) # 봇 탐지 방지 대기

        content_element = page.locator('.view-content')
        if not content_element.is_visible(timeout=5000):
            print("        -> (오류) 리뷰 본문을 찾을 수 없습니다. (timeout)")
            return

        raw_text = content_element.inner_text()
        if len(raw_text) < 100:
            print("        -> (건너뜀) 리뷰 본문이 너무 짧습니다. (100자 미만)")
            return

        # DB에 저장 (1건)
        review_params = {
            "part_id": part_id,
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
    run_crawler()