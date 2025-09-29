import re
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
from sqlalchemy import create_engine, text
from playwright_stealth import stealth_sync

# --- 1. 기본 설정 ---
# 이 부분의 값을 변경하여 크롤러 동작을 제어할 수 있습니다.

# 크롤링할 페이지 수 (예: 2로 설정하면 각 카테고리별로 2페이지까지 수집)
CRAWL_PAGES = 2 

# 브라우저 창을 띄울지 여부 (True: 숨김, False: 보임 - 디버깅 및 안정성에 유리)
HEADLESS_MODE = False

# 각 동작 사이의 지연 시간 (ms). 봇 탐지를 피하고 안정성을 높임 (50~100 추천)
SLOW_MOTION = 50

# --- 2. DB 설정 ---
DB_USER = 'root'
DB_PASSWORD = '1234'  # 실제 비밀번호로 수정
DB_HOST = 'localhost'
DB_PORT = '3306'
DB_NAME = 'danawa'

# --- 3. 크롤링 카테고리 ---
CATEGORIES = {
    'CPU': 'cpu', '쿨러': 'cooler', '메인보드': 'mainboard', 'RAM': 'RAM',
    '그래픽카드': 'vga', 'SSD': 'ssd', 'HDD': 'hdd', '케이스': 'pc case', '파워': 'power'
}

# --- 4. DB 테이블의 모든 스펙 컬럼 목록 ---
# DB에 데이터를 저장할 때 사용할 마스터 키 리스트
ALL_SPEC_KEYS = [
    "manufacturer", "codename", "cpu_series", "cpu_class", "socket", "cores", "threads", "integrated_graphics",
    "product_type", "cooling_method", "air_cooling_form", "cooler_height", "radiator_length", "fan_size", "fan_connector",
    "chipset", "form_factor", "memory_spec", "memory_slots", "vga_connection", "m2_slots", "wireless_lan",
    "device_type", "capacity", "ram_count", "clock_speed", "ram_timing", "heatsink_presence", "product_class",
    "nvidia_chipset", "amd_chipset", "intel_chipset", "gpu_interface", "gpu_memory_capacity", "output_ports", 
    "recommended_psu", "fan_count", "gpu_length", "ssd_interface", "memory_type", "ram_mounted", 
    "sequential_read", "sequential_write", "hdd_series", "disk_capacity", "rotation_speed", "buffer_capacity", "hdd_warranty",
    "case_size", "supported_board", "side_panel", "psu_length", "vga_length", "cpu_cooler_height_limit",
    "rated_output", "eighty_plus_cert", "eta_cert", "cable_connection", "pcie_16pin"
]

# --- 5. SQLAlchemy 엔진 생성 ---
try:
    engine = create_engine(f'mysql+mysqlconnector://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}')
    with engine.connect() as conn:
        print("DB 연결 성공")
except Exception as e:
    print(f"DB 연결 실패: {e}")
    exit()

# --- 6. 각 카테고리별 파싱 함수들 ---

COOLER_PRODUCT_TYPES = [
    'CPU 쿨러', '써멀컴파운드', '시스템 쿨러', 'M.2 SSD 쿨러', 'RAM 쿨러',
    'VGA 쿨러', 'HDD 쿨러', '팬컨트롤러', '써멀패드', '써멀퍼티',
    '조명기기', '방열판', 'VGA 지지대', '가이드', '팬 부속품', '수랭 부속품', '튜닝 용품'
]

def parse_cpu_specs(name, spec_string):
    specs = {}
    if '인텔' in name: specs['manufacturer'] = '인텔'
    elif 'AMD' in name: specs['manufacturer'] = 'AMD'
    name_parts = name.replace('(', ' ').replace(')', ' ').split()
    for part in name_parts:
        if '세대' in part and 'cpu_series' not in specs: specs['cpu_series'] = part
        if part in ['랩터레이크', '엘더레이크', '버미어', '라파엘', '시더밀', '코멧레이크', '마티스', '애로우레이크']: specs['codename'] = part
    spec_parts = [part.strip() for part in spec_string.split('/')]
    for part in spec_parts:
        if '소켓' in part: specs['socket'] = part
        elif '코어' in part: specs['cores'] = part
        elif '스레드' in part: specs['threads'] = part
        elif '내장그래픽' in part: specs['integrated_graphics'] = "탑재" if '탑재' in part else "미탑재"
        elif '코드네임' in part: specs['codename'] = part.replace('코드네임:', '').strip()
        elif 'CPU 시리즈' in part: specs['cpu_series'] = part.replace('CPU 시리즈:', '').strip()
        elif 'CPU 종류' in part: specs['cpu_class'] = part.replace('CPU 종류:', '').strip()
    return specs

def parse_cooler_specs(name, spec_string):
    specs = {}
    if name: specs['manufacturer'] = name.split()[0]
    for p_type in COOLER_PRODUCT_TYPES:
        if p_type.replace(' ', '') in name.replace(' ', ''):
            specs['product_type'] = p_type
            break
    if 'product_type' not in specs and 'CPU 쿨러' in spec_string: specs['product_type'] = 'CPU 쿨러'
    spec_parts = [part.strip() for part in spec_string.split('/')]
    for part in spec_parts:
        if '공랭' in part: specs['cooling_method'] = '공랭'
        elif '수랭' in part: specs['cooling_method'] = '수랭'
        if '타워형' in part: specs['air_cooling_form'] = '타워형'
        elif '플라워형' in part: specs['air_cooling_form'] = '플라워형'
        if '라디에이터' in part:
            match = re.search(r'(\d+열)', part)
            if match: specs['radiator_length'] = match.group(1)
        if '높이' in part:
            match = re.search(r'(\d+(\.\d+)?)mm', part)
            if match: specs['cooler_height'] = match.group(1)
        if '팬 크기' in part:
            match = re.search(r'(\d+(\.\d+)?)mm', part)
            if match: specs['fan_size'] = match.group(1) + "mm"
        if '팬 커넥터' in part: specs['fan_connector'] = part
    return specs

def parse_motherboard_specs(name, spec_string):
    specs = {}
    if name: specs['manufacturer'] = name.split()[0]
    spec_parts = [part.strip() for part in spec_string.split('/')]
    for part in spec_parts:
        if 'CPU 소켓' in part: specs['socket'] = part.replace('CPU 소켓:', '').strip()
        if '칩셋' in part and '세부' not in part: specs['chipset'] = part
        if '폼팩터' in part: specs['form_factor'] = part
        if 'DDR' in part: specs['memory_spec'] = part
        if '메모리 슬롯' in part: specs['memory_slots'] = part
        if 'VGA 연결' in part: specs['vga_connection'] = part
        if 'M.2' in part: specs['m2_slots'] = part
        if '무선랜' in part: specs['wireless_lan'] = part
    return specs

def parse_ram_specs(name, spec_string):
    specs = {}
    if name: specs['manufacturer'] = name.split()[0]
    spec_parts = [part.strip() for part in spec_string.split('/')]
    for part in spec_parts:
        if '데스크탑용' in part: specs['device_type'] = '데스크탑용'
        elif '노트북용' in part: specs['device_type'] = '노트북용'
        if 'DDR' in part: specs['product_class'] = part
        if 'GB' in part or 'TB' in part: specs['capacity'] = part
        if '램개수' in part: specs['ram_count'] = part
        if '동작클럭' in part: specs['clock_speed'] = part
        if '램타이밍' in part: specs['ram_timing'] = part
        if '방열판' in part: specs['heatsink_presence'] = part
    return specs

def parse_vga_specs(name, spec_string):
    specs = {}
    if name: specs['manufacturer'] = name.split()[0]
    spec_parts = [part.strip() for part in spec_string.split('/')]
    for part in spec_parts:
        if 'RTX' in part or 'GTX' in part or 'GT' in part: specs['nvidia_chipset'] = part
        elif 'RX' in part or 'Radeon' in part: specs['amd_chipset'] = part
        elif 'Arc' in part: specs['intel_chipset'] = part
        if 'PCIe' in part: specs['gpu_interface'] = part
        if 'GDDR' in part and 'GB' in part: specs['gpu_memory_capacity'] = part
        if '출력 단자' in part: specs['output_ports'] = part
        if '권장 파워' in part: specs['recommended_psu'] = part
        if '팬 개수' in part: specs['fan_count'] = part
        if '가로(길이)' in part: specs['gpu_length'] = part
    return specs

def parse_ssd_specs(name, spec_string):
    specs = {}
    if name: specs['manufacturer'] = name.split()[0]
    spec_parts = [part.strip() for part in spec_string.split('/')]
    for part in spec_parts:
        if '폼팩터' in spec_string and ('M.2' in part or '2.5인치' in part): specs['form_factor'] = part
        if '인터페이스' in spec_string and ('PCIe' in part or 'SATA' in part): specs['ssd_interface'] = part
        if '용량' in spec_string and ('TB' in part or 'GB' in part): specs['capacity'] = part
        if '메모리 타입' in spec_string and ('TLC' in part or 'QLC' in part or 'MLC' in part): specs['memory_type'] = part
        if 'RAM 탑재' in part: specs['ram_mounted'] = part
        if '순차읽기' in part: specs['sequential_read'] = part
        if '순차쓰기' in part: specs['sequential_write'] = part
    return specs

def parse_hdd_specs(name, spec_string):
    specs = {}
    if name: specs['manufacturer'] = name.split()[0]
    name_parts = name.replace('(', ' ').replace(')', ' ').split()
    for part in name_parts:
        if part in ['BarraCuda', 'IronWolf', 'WD', 'Toshiba']: specs['hdd_series'] = part
    spec_parts = [part.strip() for part in spec_string.split('/')]
    for part in spec_parts:
        if '용량' in spec_string and ('TB' in part or 'GB' in part): specs['disk_capacity'] = part
        if 'RPM' in part: specs['rotation_speed'] = part
        if '버퍼' in part: specs['buffer_capacity'] = part
        if 'A/S' in part: specs['hdd_warranty'] = part
    return specs

def parse_case_specs(name, spec_string):
    specs = {}
    if name: specs['manufacturer'] = name.split()[0]
    spec_parts = [part.strip() for part in spec_string.split('/')]
    for part in spec_parts:
        if 'PC케이스' in part: specs['product_type'] = part
        if '타워' in part: specs['case_size'] = part
        if '지원보드 규격' in spec_string and ('ATX' in part or 'M-ATX' in part or 'ITX' in part): specs['supported_board'] = part
        if '측면' in part: specs['side_panel'] = part
        if '파워 장착' in part: specs['psu_length'] = part
        if '그래픽카드 장착' in part: specs['vga_length'] = part
        if 'CPU 쿨러 장착' in part: specs['cpu_cooler_height_limit'] = part
    return specs

def parse_power_specs(name, spec_string):
    specs = {}
    if name: specs['manufacturer'] = name.split()[0]
    spec_parts = [part.strip() for part in spec_string.split('/')]
    for part in spec_parts:
        if '파워' in part and ('ATX' in part or 'SFX' in part): specs['product_type'] = part
        if '정격출력' in part: specs['rated_output'] = part
        if '80PLUS' in part: specs['eighty_plus_cert'] = part
        if 'ETA인증' in part: specs['eta_cert'] = part
        if '케이블연결' in part: specs['cable_connection'] = part
        if 'PCIe 16핀' in part: specs['pcie_16pin'] = part
    return specs

def scrape_category(page, category_name, query):
    sql = text("""
        INSERT INTO parts (
            name, category, price, link, img_src, manufacturer, review_count, star_rating, rating_review_count,
            -- CPU
            codename, cpu_series, cpu_class, socket, cores, threads, integrated_graphics,
            -- 쿨러
            product_type, cooling_method, air_cooling_form, cooler_height, radiator_length, fan_size, fan_connector,
            -- 메인보드
            chipset, form_factor, memory_spec, memory_slots, vga_connection, m2_slots, wireless_lan,
            -- RAM
            device_type, capacity, ram_count, clock_speed, ram_timing, heatsink_presence, product_class,
            -- 그래픽카드
            nvidia_chipset, amd_chipset, intel_chipset, gpu_interface, gpu_memory_capacity, output_ports, recommended_psu, fan_count, gpu_length,
            -- SSD
            ssd_interface, memory_type, ram_mounted, sequential_read, sequential_write,
            -- HDD
            hdd_series, disk_capacity, rotation_speed, buffer_capacity, hdd_warranty,
            -- 케이스
            case_size, supported_board, side_panel, psu_length, vga_length, cpu_cooler_height_limit,
            -- 파워
            rated_output, eighty_plus_cert, eta_cert, cable_connection, pcie_16pin
        ) VALUES (
            :name, :category, :price, :link, :img_src, :manufacturer, :review_count, :star_rating, :rating_review_count,
            :codename, :cpu_series, :cpu_class, :socket, :cores, :threads, :integrated_graphics,
            :product_type, :cooling_method, :air_cooling_form, :cooler_height, :radiator_length, :fan_size, :fan_connector,
            :chipset, :form_factor, :memory_spec, :memory_slots, :vga_connection, :m2_slots, :wireless_lan,
            :device_type, :capacity, :ram_count, :clock_speed, :ram_timing, :heatsink_presence, :product_class,
            :nvidia_chipset, :amd_chipset, :intel_chipset, :gpu_interface, :gpu_memory_capacity, :output_ports, :recommended_psu, :fan_count, :gpu_length,
            :ssd_interface, :memory_type, :ram_mounted, :sequential_read, :sequential_write,
            :hdd_series, :disk_capacity, :rotation_speed, :buffer_capacity, :hdd_warranty,
            :case_size, :supported_board, :side_panel, :psu_length, :vga_length, :cpu_cooler_height_limit,
            :rated_output, :eighty_plus_cert, :eta_cert, :cable_connection, :pcie_16pin
        )
        ON DUPLICATE KEY UPDATE
            price=VALUES(price), review_count=VALUES(review_count), star_rating=VALUES(star_rating), rating_review_count=VALUES(rating_review_count), manufacturer=VALUES(manufacturer),
            -- CPU
            codename=VALUES(codename), cpu_series=VALUES(cpu_series), cpu_class=VALUES(cpu_class), socket=VALUES(socket), cores=VALUES(cores), threads=VALUES(threads), integrated_graphics=VALUES(integrated_graphics),
            -- 쿨러
            product_type=VALUES(product_type), cooling_method=VALUES(cooling_method), air_cooling_form=VALUES(air_cooling_form), cooler_height=VALUES(cooler_height), radiator_length=VALUES(radiator_length), fan_size=VALUES(fan_size), fan_connector=VALUES(fan_connector),
            -- 메인보드
            chipset=VALUES(chipset), form_factor=VALUES(form_factor), memory_spec=VALUES(memory_spec), memory_slots=VALUES(memory_slots), vga_connection=VALUES(vga_connection), m2_slots=VALUES(m2_slots), wireless_lan=VALUES(wireless_lan),
            -- RAM
            device_type=VALUES(device_type), capacity=VALUES(capacity), ram_count=VALUES(ram_count), clock_speed=VALUES(clock_speed), ram_timing=VALUES(ram_timing), heatsink_presence=VALUES(heatsink_presence), product_class=VALUES(product_class),
            -- 그래픽카드
            nvidia_chipset=VALUES(nvidia_chipset), amd_chipset=VALUES(amd_chipset), intel_chipset=VALUES(intel_chipset), gpu_interface=VALUES(gpu_interface), gpu_memory_capacity=VALUES(gpu_memory_capacity), output_ports=VALUES(output_ports), recommended_psu=VALUES(recommended_psu), fan_count=VALUES(fan_count), gpu_length=VALUES(gpu_length),
            -- SSD
            ssd_interface=VALUES(ssd_interface), memory_type=VALUES(memory_type), ram_mounted=VALUES(ram_mounted), sequential_read=VALUES(sequential_read), sequential_write=VALUES(sequential_write),
            -- HDD
            hdd_series=VALUES(hdd_series), disk_capacity=VALUES(disk_capacity), rotation_speed=VALUES(rotation_speed), buffer_capacity=VALUES(buffer_capacity), hdd_warranty=VALUES(hdd_warranty),
            -- 케이스
            case_size=VALUES(case_size), supported_board=VALUES(supported_board), side_panel=VALUES(side_panel), psu_length=VALUES(psu_length), vga_length=VALUES(vga_length), cpu_cooler_height_limit=VALUES(cpu_cooler_height_limit),
            -- 파워
            rated_output=VALUES(rated_output), eighty_plus_cert=VALUES(eighty_plus_cert), eta_cert=VALUES(eta_cert), cable_connection=VALUES(cable_connection), pcie_16pin=VALUES(pcie_16pin);
    """)
    
    with engine.connect() as conn:
        for page_num in range(1, CRAWL_PAGES + 1):
            url = f'https://search.danawa.com/dsearch.php?query={query}&page={page_num}'
            print(f"--- '{category_name}' 카테고리, {page_num}페이지 목록 수집 ---")
            
            try:
                page.goto(url, wait_until='load', timeout=20000)
                page.wait_for_selector('ul.product_list', timeout=10000)

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
                    
                     # [핵심 수정] 리뷰, 별점, 리뷰 수 수집 로직 전면 개편
                    review_count = 0
                    star_rating = 0.0
                    rating_review_count = 0

                    # prod_sub_info 영역에서 모든 meta_item을 찾음
                    meta_items = item.select('.prod_sub_meta .meta_item')
                    for meta in meta_items:
                        # '상품의견' 텍스트가 있는지 확인
                        if '상품의견' in meta.text:
                            count_tag = meta.select_one('.dd strong')
                            if count_tag and (match := re.search(r'[\d,]+', count_tag.text)):
                                review_count = int(match.group().replace(',', ''))
                        
                        # '상품리뷰' 텍스트가 있는지 확인
                        elif '상품리뷰' in meta.text:
                            score_tag = meta.select_one('.text__score')
                            if score_tag:
                                try: star_rating = float(score_tag.text.strip())
                                except (ValueError, TypeError): star_rating = 0.0
                            
                            review_num_tag = meta.select_one('.text__number')
                            if review_num_tag:
                                try: rating_review_count = int(review_num_tag.text.strip().replace(',', ''))
                                except (ValueError, TypeError): rating_review_count = 0
                    
                    spec_tag = item.select_one('div.spec_list')
                    spec_string = spec_tag.text.strip() if spec_tag else ""
                    
                    parser_func_name = f"parse_{query.replace(' ', '_')}_specs"
                    parser_func = globals().get(parser_func_name)
                    detailed_specs = parser_func(name, spec_string) if parser_func else {}

                    base_params = {
                        "name": name, "category": category_name, "price": price, "link": link, 
                        "img_src": img_src, "review_count": review_count,
                        "star_rating": star_rating, "rating_review_count": rating_review_count
                    }
                    
                    final_params = {key: None for key in ALL_SPEC_KEYS}
                    final_params.update(base_params)
                    final_params.update(detailed_specs)
                    
                    conn.execute(sql, final_params)
                    print(f"  ✅ {name} (댓글: {review_count})")
                
                conn.commit()

            except Exception as e:
                print(f"--- {page_num}페이지 처리 중 오류 발생: {e}. 다음 페이지로 넘어갑니다. ---")
                conn.rollback() 
                continue

def run_crawler():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=HEADLESS_MODE, slow_mo=SLOW_MOTION) 
        page = browser.new_page()
        stealth_sync(page)
        
        page.set_extra_http_headers({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"})

        for category_name, query in CATEGORIES.items():
            scrape_category(page, category_name, query)
            
        browser.close()
        print("\n모든 카테고리 데이터 수집을 완료했습니다.")

if __name__ == "__main__":
    run_crawler()