import re
from playwright.sync_api import sync_playwright, TimeoutError
from bs4 import BeautifulSoup
from sqlalchemy import create_engine, text
from playwright_stealth import stealth_sync

# --- DB 설정 ---
DB_USER = 'root'
DB_PASSWORD = '1234'  # 실제 비밀번호로 수정
DB_HOST = 'localhost'
DB_PORT = '3306'
DB_NAME = 'danawa'
# -----------------

# --- 크롤링 설정 ---
CATEGORIES = {
    'CPU': 'cpu',
    '쿨러': 'cooler',
    '메인보드': 'mainboard',
    'RAM': 'RAM',
    '그래픽카드': 'vga',
    'SSD': 'ssd',
    'HDD': 'hdd',
    '케이스': 'pc case',
}

# --- SQLAlchemy 엔진 생성 ---
try:
    engine = create_engine(f'mysql+mysqlconnector://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}')
    with engine.connect() as conn:
        print("✅ DB 연결 성공")
except Exception as e:
    print(f"❗ DB 연결 실패: {e}")
    exit()

# [신설] '쿨러' 카테고리의 '제품 종류' 목록
COOLER_PRODUCT_TYPES = [
    'CPU 쿨러', '써멀컴파운드', '시스템 쿨러', 'M.2 SSD 쿨러', 'RAM 쿨러',
    'VGA 쿨러', 'HDD 쿨러', '팬컨트롤러', '써멀패드', '써멀퍼티',
    '조명기기', '방열판', 'VGA 지지대', '가이드', '팬 부속품', '수랭 부속품', '튜닝 용품'
]

def parse_cpu_specs(name, spec_string):
    """[수정] 상품 이름과 스펙 문자열 모두에서 정보를 교차 추출하도록 로직 강화"""
    specs = {}
    
    # 1. 이름에서 기본 정보 추출 (더 정확할 수 있음)
    if '인텔' in name: specs['manufacturer'] = '인텔'
    elif 'AMD' in name: specs['manufacturer'] = 'AMD'

    name_parts = name.replace('(', ' ').replace(')', ' ').split()
    for part in name_parts:
        if '세대' in part and 'cpu_series' not in specs:
            specs['cpu_series'] = part
        if part in ['랩터레이크', '엘더레이크', '버미어', '라파엘', '시더밀', '코멧레이크', '마티스', '애로우레이크']:
            specs['codename'] = part
    
    # 2. 상세 스펙 문자열에서 정보 보충 및 덮어쓰기
    spec_parts = [part.strip() for part in spec_string.split('/')]
    for part in spec_parts:
        if '소켓' in part:
            specs['socket'] = part
        elif '코어' in part:
            specs['cores'] = part
        elif '스레드' in part:
            specs['threads'] = part
        elif '내장그래픽' in part:
            specs['integrated_graphics'] = "탑재" if '탑재' in part else "미탑재"
        elif '코드네임' in part:
            specs['codename'] = part.replace('코드네임:', '').strip()
        elif 'CPU 시리즈' in part:
            specs['cpu_series'] = part.replace('CPU 시리즈:', '').strip()
        elif 'CPU 종류' in part:
            specs['cpu_class'] = part.replace('CPU 종류:', '').strip()
            
    return specs

def parse_cooler_specs(name, spec_string):
    """[대규모 수정] 쿨러 스펙 파싱 로직을 매우 정교하게 개선"""
    specs = {}
    
    # 1. 제조사 추출 (상품명의 첫 단어)
    if name:
        specs['manufacturer'] = name.split()[0]

    # 2. 제품 종류 추출 (정의된 목록과 비교)
    for p_type in COOLER_PRODUCT_TYPES:
        if p_type.replace(' ', '') in name.replace(' ', ''): # 공백 제거 후 비교
            specs['product_type'] = p_type
            break
    if 'product_type' not in specs and 'CPU 쿨러' in spec_string:
        specs['product_type'] = 'CPU 쿨러' # 이름에 없으면 스펙에서 한번 더 확인

    # 3. 상세 스펙 문자열 파싱
    spec_parts = [part.strip() for part in spec_string.split('/')]
    for part in spec_parts:
        # 냉각 방식
        if '공랭' in part: specs['cooling_method'] = '공랭'
        elif '수랭' in part: specs['cooling_method'] = '수랭'
        # 공랭 형태
        if '타워형' in part: specs['air_cooling_form'] = '타워형'
        elif '플라워형' in part: specs['air_cooling_form'] = '플라워형'
        # 라디에이터 (숫자+열 형태 추출)
        if '라디에이터' in part:
            match = re.search(r'(\d+열)', part)
            if match:
                specs['radiator_length'] = match.group(1)
        # 높이 (숫자만 추출)
        if '높이' in part:
            match = re.search(r'(\d+(\.\d+)?)mm', part)
            if match:
                specs['cooler_height'] = match.group(1) # "158.5"와 같이 숫자만 저장
        # 팬 크기 (숫자만 추출)
        if '팬 크기' in part:
            match = re.search(r'(\d+(\.\d+)?)mm', part)
            if match:
                specs['fan_size'] = match.group(1) + "mm" # "120mm"와 같이 단위 포함 저장
        # 팬 커넥터
        if '팬 커넥터' in part:
            specs['fan_connector'] = part
            
    return specs

# [신설] 메인보드 스펙 파싱 함수
def parse_motherboard_specs(name, spec_string):
    """[수정] 폼팩터, 메모리 종류 파싱 로직 추가"""
    specs = {}
    if name: specs['manufacturer'] = name.split()[0]

    spec_parts = [part.strip() for part in spec_string.split('/')]
    for part in spec_parts:
        if 'CPU 소켓' in part: specs['socket'] = part.replace('CPU 소켓:', '').strip()
        if '칩셋' in part and '세부' not in part: specs['chipset'] = part
        if '폼팩터' in part: specs['form_factor'] = part # [추가]
        if 'DDR' in part: specs['memory_spec'] = part # [추가]
        if '메모리 슬롯' in part: specs['memory_slots'] = part
        if 'VGA 연결' in part: specs['vga_connection'] = part
        if 'M.2' in part: specs['m2_slots'] = part
        if '무선랜' in part: specs['wireless_lan'] = part
            
    return specs

# [신설] RAM 스펙 파싱 함수
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
        if '방열판' in part:
            specs['heatsink_presence'] = part

    return specs

# [신설] 그래픽카드 스펙 파싱 함수
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

# [신설] SSD 스펙 파싱 함수
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

# [신설] HDD 스펙 파싱 함수
def parse_hdd_specs(name, spec_string):
    specs = {}
    if name: specs['manufacturer'] = name.split()[0]

    # 시리즈 정보는 이름에 포함된 경우가 많음 (예: BarraCuda, WD Blue)
    name_parts = name.replace('(', ' ').replace(')', ' ').split()
    for part in name_parts:
        if part in ['BarraCuda', 'IronWolf', 'WD', 'Toshiba']: # 대표적인 시리즈/브랜드
            specs['hdd_series'] = part

    spec_parts = [part.strip() for part in spec_string.split('/')]
    for part in spec_parts:
        if '용량' in spec_string and ('TB' in part or 'GB' in part): specs['disk_capacity'] = part
        if 'RPM' in part: specs['rotation_speed'] = part
        if '버퍼' in part: specs['buffer_capacity'] = part
        if 'A/S' in part: specs['hdd_warranty'] = part
            
    return specs

# [신설] 케이스 스펙 파싱 함수
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


def scrape_category(page, category_name, query):
    # [수정] 모든 부품의 컬럼을 포함하도록 SQL 확장
    sql = text("""
        INSERT INTO parts (
            name, category, price, link, img_src, manufacturer, review_count,
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
            case_size, supported_board, side_panel, psu_length, vga_length, cpu_cooler_height_limit
        ) VALUES (
            :name, :category, :price, :link, :img_src, :manufacturer, :review_count,
            -- CPU
            :codename, :cpu_series, :cpu_class, :socket, :cores, :threads, :integrated_graphics,
            -- 쿨러
            :product_type, :cooling_method, :air_cooling_form, :cooler_height, :radiator_length, :fan_size, :fan_connector,
            -- 메인보드
            :chipset, :form_factor, :memory_spec, :memory_slots, :vga_connection, :m2_slots, :wireless_lan,
            -- RAM
            :device_type, :capacity, :ram_count, :clock_speed, :ram_timing, :heatsink_presence, :product_class,
            -- 그래픽카드
            :nvidia_chipset, :amd_chipset, :intel_chipset, :gpu_interface, :gpu_memory_capacity, :output_ports, :recommended_psu, :fan_count, :gpu_length,
            -- SSD
            :ssd_interface, :memory_type, :ram_mounted, :sequential_read, :sequential_write,
            -- HDD
            :hdd_series, :disk_capacity, :rotation_speed, :buffer_capacity, :hdd_warranty,
            -- 케이스
            :case_size, :supported_board, :side_panel, :psu_length, :vga_length, :cpu_cooler_height_limit
        )
        ON DUPLICATE KEY UPDATE
            price=VALUES(price), 
            review_count=VALUES(review_count), 
            manufacturer=VALUES(manufacturer),
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
            case_size=VALUES(case_size), supported_board=VALUES(supported_board), side_panel=VALUES(side_panel), psu_length=VALUES(psu_length), vga_length=VALUES(vga_length), cpu_cooler_height_limit=VALUES(cpu_cooler_height_limit);
    """)
    
    with engine.connect() as conn:
        for page_num in range(1, 2):
            url = f'https://search.danawa.com/dsearch.php?query={query}&page={page_num}'
            print(f"--- '{category_name}' 카테고리, {page_num}페이지 목록 수집 ---")
            
            try:
                page.goto(url, wait_until='load', timeout=15000)
                page.wait_for_selector('ul.product_list', timeout=10000)
                
                list_html = page.content()
                list_soup = BeautifulSoup(list_html, 'html.parser')
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
                    img_src = "https:" + img_tag.get('data-original-src', img_tag['src'])

                    try:
                        price_str = price_tag.text.strip()
                        price = int(price_str.replace(',', ''))
                    except ValueError:
                        print(f"  - 가격 정보가 유효하지 않아 건너뜁니다: {name} (값: '{price_str}')")
                        continue

                    review_count = 0
                    review_tag = item.select_one('a.count_cmt')
                    if review_tag:
                        count_text = review_tag.text.strip()
                        match = re.search(r'\d+', count_text)
                        if match:
                            review_count = int(match.group())
                    
                    spec_tag = item.select_one('div.spec_list')
                    spec_string = spec_tag.text.strip() if spec_tag else ""
                    
                    detailed_specs = {}
                    if category_name == 'CPU':
                        detailed_specs = parse_cpu_specs(name, spec_string)
                    elif category_name == '쿨러':
                        detailed_specs = parse_cooler_specs(name, spec_string)
                    elif category_name == '메인보드':
                        detailed_specs = parse_motherboard_specs(name, spec_string)
                    elif category_name == 'RAM':
                        detailed_specs = parse_ram_specs(name, spec_string)
                    elif category_name == '그래픽카드':
                        detailed_specs = parse_vga_specs(name, spec_string)
                    elif category_name == 'SSD':
                        detailed_specs = parse_ssd_specs(name, spec_string)
                    elif category_name == 'HDD':
                        detailed_specs = parse_hdd_specs(name, spec_string)
                    elif category_name == '케이스':
                        detailed_specs = parse_case_specs(name, spec_string)

                    params = {
                        # 공통
                        "name": name, "category": category_name, "price": price, 
                        "link": link, "img_src": img_src, "review_count": review_count,
                        "manufacturer": detailed_specs.get('manufacturer'),
                        # CPU
                        "codename": detailed_specs.get('codename'), "cpu_series": detailed_specs.get('cpu_series'),
                        "cpu_class": detailed_specs.get('cpu_class'), "socket": detailed_specs.get('socket'),
                        "cores": detailed_specs.get('cores'), "threads": detailed_specs.get('threads'),
                        "integrated_graphics": detailed_specs.get('integrated_graphics'),
                        # 쿨러
                        "product_type": detailed_specs.get('product_type'),
                        "cooling_method": detailed_specs.get('cooling_method'),
                        "air_cooling_form": detailed_specs.get('air_cooling_form'),
                        "cooler_height": detailed_specs.get('cooler_height'),
                        "radiator_length": detailed_specs.get('radiator_length'),
                        "fan_size": detailed_specs.get('fan_size'),
                        "fan_connector": detailed_specs.get('fan_connector'),
                        # 메인보드
                        "chipset": detailed_specs.get('chipset'), 
                        "form_factor": detailed_specs.get('form_factor'),
                        "memory_spec": detailed_specs.get('memory_spec'), 
                        "memory_slots": detailed_specs.get('memory_slots'),
                        "vga_connection": detailed_specs.get('vga_connection'), 
                        "m2_slots": detailed_specs.get('m2_slots'),
                        "wireless_lan": detailed_specs.get('wireless_lan'),
                        # RAM
                        "device_type": detailed_specs.get('device_type'),
                        "product_class": detailed_specs.get('product_class'),
                        "capacity": detailed_specs.get('capacity'),
                        "ram_count": detailed_specs.get('ram_count'),
                        "clock_speed": detailed_specs.get('clock_speed'),
                        "ram_timing": detailed_specs.get('ram_timing'),
                        "heatsink_presence": detailed_specs.get('heatsink_presence'),
                        # 그래픽카드
                        "nvidia_chipset": detailed_specs.get('nvidia_chipset'),
                        "amd_chipset": detailed_specs.get('amd_chipset'),
                        "intel_chipset": detailed_specs.get('intel_chipset'),
                        "gpu_interface": detailed_specs.get('gpu_interface'),
                        "gpu_memory_capacity": detailed_specs.get('gpu_memory_capacity'),
                        "output_ports": detailed_specs.get('output_ports'),
                        "recommended_psu": detailed_specs.get('recommended_psu'),
                        "fan_count": detailed_specs.get('fan_count'),
                        "gpu_length": detailed_specs.get('gpu_length'),
                        # SSD
                        "ssd_interface": detailed_specs.get('ssd_interface'),
                        "memory_type": detailed_specs.get('memory_type'),
                        "ram_mounted": detailed_specs.get('ram_mounted'),
                        "sequential_read": detailed_specs.get('sequential_read'),
                        "sequential_write": detailed_specs.get('sequential_write'),
                        # HDD
                        "hdd_series": detailed_specs.get('hdd_series'),
                        "disk_capacity": detailed_specs.get('disk_capacity'),
                        "rotation_speed": detailed_specs.get('rotation_speed'),
                        "buffer_capacity": detailed_specs.get('buffer_capacity'),
                        "hdd_warranty": detailed_specs.get('hdd_warranty'),
                        # 케이스
                        "case_size": detailed_specs.get('case_size'),
                        "supported_board": detailed_specs.get('supported_board'),
                        "side_panel": detailed_specs.get('side_panel'),
                        "psu_length": detailed_specs.get('psu_length'),
                        "vga_length": detailed_specs.get('vga_length'),
                        "cpu_cooler_height_limit": detailed_specs.get('cpu_cooler_height_limit'),
                        # 다른 카테고리와 공용인 필드
                        "form_factor": detailed_specs.get('form_factor'),
                        "capacity": detailed_specs.get('capacity'),
                    }
                    
                    conn.execute(sql, params)
                    print(f"  ✅ {name} (댓글: {review_count})")
                
                conn.commit()

            except Exception as e:
                print(f"--- {page_num}페이지 처리 중 오류 발생: {e}. 다음 페이지로 넘어갑니다. ---")
                conn.rollback() 
                continue

def run_crawler():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        stealth_sync(page)
        
        page.set_extra_http_headers({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"})

        for category_name, query in CATEGORIES.items():
            scrape_category(page, category_name, query)
            
        browser.close()
        print("\n🎉🎉🎉 모든 카테고리 데이터 수집을 완료했습니다. 🎉🎉🎉")

if __name__ == "__main__":
    run_crawler()