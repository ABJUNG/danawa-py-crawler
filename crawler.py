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
    'RAM': 'RAM',
    # '메인보드': 'mainboard', # 새로운 파싱 함수 추가 필요
}

# --- SQLAlchemy 엔진 생성 ---
try:
    engine = create_engine(f'mysql+mysqlconnector://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}')
    with engine.connect() as conn:
        print("✅ DB 연결 성공")
except Exception as e:
    print(f"❗ DB 연결 실패: {e}")
    exit()


def parse_cpu_specs(spec_string):
    """[신설] CPU 스펙 문자열을 파싱하여 딕셔너리로 반환하는 함수"""
    specs = {}
    spec_parts = [part.strip() for part in spec_string.split('/')]

    for part in spec_parts:
        if '소켓' in part:
            # ex: "인텔(소켓1851)" -> "소켓1851"
            socket_info = re.search(r'소켓\d+', part)
            if socket_info:
                specs['socket'] = socket_info.group()
        elif '코어' in part:
            specs['cores'] = part
        elif '스레드' in part:
            specs['threads'] = part
        elif '클럭' in part:
            if '최대' in part:
                specs['clock_speed'] = part # 최대 클럭을 우선 저장
            elif '기본' in part and 'clock_speed' not in specs:
                specs['clock_speed'] = part # 최대 클럭이 없으면 기본 클럭 저장
        elif 'L3 캐시' in part:
            specs['l3_cache'] = part
        elif 'L2 캐시' in part:
            specs['l2_cache'] = part
        elif '내장그래픽' in part:
            specs['integrated_graphics'] = "있음" if '탑재' in part else "없음"
    return specs


def scrape_category(page, category_name, query):
    """[수정] 목록 페이지만 스크래핑하도록 재구성된 함수"""
    print(f"\n--- '{category_name}' 카테고리 스크래핑 시작 ---")
    
    sql = text("""
        INSERT INTO parts (
            name, category, price, link, img_src, 
            socket, cores, threads, clock_speed, l2_cache, l3_cache, integrated_graphics
        ) VALUES (
            :name, :category, :price, :link, :img_src, 
            :socket, :cores, :threads, :clock_speed, :l2_cache, :l3_cache, :integrated_graphics
        )
        ON DUPLICATE KEY UPDATE
            price=VALUES(price), img_src=VALUES(img_src), socket=VALUES(socket), cores=VALUES(cores),
            threads=VALUES(threads), clock_speed=VALUES(clock_speed), l2_cache=VALUES(l2_cache), 
            l3_cache=VALUES(l3_cache), integrated_graphics=VALUES(integrated_graphics);
    """)

    with engine.connect() as conn:
        for page_num in range(1, 6): # 5페이지까지 수집
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
                    # ... (이전과 동일한 파싱 로직) ...
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
                    
                    spec_tag = item.select_one('div.spec_list')
                    spec_string = spec_tag.text.strip() if spec_tag else ""
                    
                    detailed_specs = {}
                    if category_name == 'CPU':
                        detailed_specs = parse_cpu_specs(spec_string)

                    params = {
                        "name": name, "category": category_name, "price": price, 
                        "link": link, "img_src": img_src,
                        "socket": detailed_specs.get('socket'),
                        "cores": detailed_specs.get('cores'),
                        "threads": detailed_specs.get('threads'),
                        "clock_speed": detailed_specs.get('clock_speed'),
                        "l2_cache": detailed_specs.get('l2_cache'),
                        "l3_cache": detailed_specs.get('l3_cache'),
                        "integrated_graphics": detailed_specs.get('integrated_graphics')
                    }
                    
                    conn.execute(sql, params)
                    print(f"  ✅ {name}")
                
                conn.commit()

            except Exception as e:
                # [수정] 자세한 오류 메시지 확인을 위해 e를 직접 출력
                print(f"--- {page_num}페이지 처리 중 오류 발생: {e}. 다음 페이지로 넘어갑니다. ---")
                conn.rollback() # 오류 발생 시 현재 트랜잭션 롤백
                continue

def run_crawler():
    """전체 크롤링 프로세스를 실행하는 메인 함수"""
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