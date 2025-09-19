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

def scrape_category(page, category_name, query):
    """지정된 카테고리의 상품 정보를 여러 페이지에 걸쳐 스크랩하는 함수"""
    print(f"\n--- '{category_name}' 카테고리 스크래핑 시작 ---")
    
    # ▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼
    # [수정된 부분] 1페이지부터 5페이지까지 순회합니다. (한 페이지당 약 40개 * 5 = 약 200개)
    for page_num in range(1, 6):
        url = f'https://search.danawa.com/dsearch.php?query={query}&page={page_num}'
        print(f"--- '{category_name}' 카테고리, {page_num}페이지 스크래핑 ---")
        
        try:
            page.goto(url)
            page.wait_for_selector('ul.product_list', timeout=10000) # 타임아웃을 10초로 줄임

            last_height = page.evaluate("document.body.scrollHeight")
            while True:
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                page.wait_for_timeout(1500)
                new_height = page.evaluate("document.body.scrollHeight")
                if new_height == last_height:
                    break
                last_height = new_height

            html = page.content()
            soup = BeautifulSoup(html, 'html.parser')
            product_list = soup.select('li.prod_item[id^="productItem"]')

            # 만약 현재 페이지에 상품이 없다면, 해당 카테고리 수집을 중단하고 다음으로 넘어감
            if not product_list:
                print("--- 현재 페이지에 상품이 없어 다음 카테고리로 넘어갑니다. ---")
                break

            for item in product_list:
                try:
                    name = item.select_one('p.prod_name > a').text.strip()
                    price_str = item.select_one('p.price_sect > a > strong').text.strip()
                    price = int(price_str.replace(',', ''))
                    link = item.select_one('p.prod_name > a')['href']
                    img_src = "https:" + item.select_one('div.thumb_image img')['src']

                    with engine.connect() as conn:
                        sql = text("""
                            INSERT INTO parts (name, category, price, link, img_src)
                            VALUES (:name, :category, :price, :link, :img_src)
                            ON DUPLICATE KEY UPDATE
                                name = VALUES(name), category = VALUES(category), price = VALUES(price), img_src = VALUES(img_src);
                        """)
                        conn.execute(sql, {
                            "name": name, "category": category_name, "price": price, "link": link, "img_src": img_src
                        })
                        conn.commit()

                except (AttributeError, ValueError, TypeError):
                    continue
        
        except Exception as e:
            print(f"--- {page_num}페이지 처리 중 오류 발생: {e} ---")
            continue
    # ▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲

# ... (run_crawler와 if __name__ == "__main__": 부분은 기존과 동일) ...
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