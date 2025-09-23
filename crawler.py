import re
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
from sqlalchemy import create_engine, text

# --- DB 설정 (기존과 동일) ---
DB_USER = 'root'
DB_PASSWORD = '1234' # 실제 비밀번호로 수정
DB_HOST = 'localhost'
DB_PORT = '3306'
DB_NAME = 'danawa'
# --------------------------------

engine = create_engine(f'mysql+mysqlconnector://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}')

CATEGORIES = {
    'CPU': 'cpu',
    '쿨러': '쿨러',
    '메인보드': 'mainboard',
    'RAM': 'RAM',
    '그래픽카드': 'vga',
    'SSD': 'ssd',
    'HDD': 'hdd',
    '파워': 'power',
    '케이스': 'pc case'
}

def parse_specs(name, category):
    specs = {'socket': None, 'core_type': None, 'ram_capacity': None, 'chipset': None}
    
    if category == 'CPU' or category == '메인보드':
        match = re.search(r'\((LGA[0-9]+|AM[45])\)', name)
        if match: specs['socket'] = match.group(1)

    if category == 'CPU':
        if '코어i9' in name or '라이젠 9' in name: specs['core_type'] = 'i9/라이젠9'
        elif '코어i7' in name or '라이젠 7' in name: specs['core_type'] = 'i7/라이젠7'
        elif '코어i5' in name or '라이젠 5' in name: specs['core_type'] = 'i5/라이젠5'
        elif '코어i3' in name or '라이젠 3' in name: specs['core_type'] = 'i3/라이젠3'
    
    if category == 'RAM':
        match = re.search(r'(\d+GB)', name)
        if match: specs['ram_capacity'] = match.group(1)

    if category == '그래픽카드':
        if 'GeForce' in name: specs['chipset'] = 'NVIDIA'
        elif 'Radeon' in name: specs['chipset'] = 'AMD'
        
    return specs

def scrape_category(page, category_name, query):
    """지정된 카테고리의 상품 정보를 스크랩하는 함수 (네트워크 안정 상태 대기 적용)"""
    url = f'https://search.danawa.com/dsearch.php?query={query}'
    print(f"\n--- '{category_name}' 카테고리 스크래핑 시작 ---")
    
    try:
        page.goto(url)
        page.wait_for_selector('ul.product_list', timeout=30000)

        # ▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼
        # [수정된 부분] 더 안정적인 스크롤 및 대기 로직
        last_height = page.evaluate("document.body.scrollHeight")
        while True:
            # 페이지 맨 아래로 스크롤
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            
            # 네트워크 활동이 잠잠해질 때까지 최대 5초간 기다립니다.
            # 이것이 고정 시간 대기보다 훨씬 안정적입니다.
            page.wait_for_load_state('networkidle', timeout=5000)
            
            new_height = page.evaluate("document.body.scrollHeight")
            if new_height == last_height:
                break # 높이 변화가 없으면 모든 콘텐츠가 로드된 것이므로 반복 종료
            last_height = new_height
        # ▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲

        html = page.content()
        soup = BeautifulSoup(html, 'html.parser')
        product_list = soup.select('li.prod_item[id^="productItem"]')
        print(f"--- 최종 {len(product_list)}개의 '{category_name}' 상품 정보를 수집합니다. ---")

        for item in product_list:
            try:
                # ... (이하 DB 저장 로직은 기존과 동일) ...
                name = item.select_one('p.prod_name > a').text.strip()
                price_str = item.select_one('p.price_sect > a > strong').text.strip()
                price = int(price_str.replace(',', ''))
                link = item.select_one('p.prod_name > a')['href']
                img_src = "https:" + item.select_one('div.thumb_image img')['src']
                specs = parse_specs(name, category_name)

                with engine.connect() as conn:
                # SQL 쿼리에 새로운 컬럼들 추가
                    sql = text("""
                        INSERT INTO parts (name, category, price, link, img_src, socket, core_type, ram_capacity, chipset)
                        VALUES (:name, :category, :price, :link, :img_src, :socket, :core_type, :ram_capacity, :chipset)
                        ON DUPLICATE KEY UPDATE
                            name=VALUES(name), category=VALUES(category), price=VALUES(price), img_src=VALUES(img_src),
                            socket=VALUES(socket), core_type=VALUES(core_type), ram_capacity=VALUES(ram_capacity), chipset=VALUES(chipset);
                    """)
                    conn.execute(sql, {
                        "name": name, "category": category_name, "price": price, "link": link, "img_src": img_src,
                        "socket": specs['socket'], "core_type": specs['core_type'], 
                        "ram_capacity": specs['ram_capacity'], "chipset": specs['chipset']
                    })
                    conn.commit()

            except (AttributeError, ValueError, TypeError):
                continue
    
    except Exception as e:
        print(f"--- '{category_name}' 카테고리 처리 중 오류 발생: {e} ---")

def run_crawler():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        for category_name, query in CATEGORIES.items():
            scrape_category(page, category_name, query)

        browser.close()
        print("\n🎉🎉🎉 모든 카테고리 데이터 수집을 완료했습니다. 🎉🎉🎉")

if __name__ == "__main__":
    run_crawler()