import re
import asyncio
from playwright.async_api import async_playwright, Playwright
from bs4 import BeautifulSoup
from sqlalchemy import create_engine, text
import json
import time
from playwright_stealth import stealth_sync
from urllib.parse import quote_plus, quote, quote as url_quote
import requests
import statistics
import sys
import pymysql
import os


# --- 1. 기본 설정 ---
# 이 부분의 값을 변경하여 크롤러 동작을 제어할 수 있습니다.

# 크롤링할 페이지 수 (예: 2로 설정하면 각 카테고리별로 2페이지까지 수집)
CRAWL_PAGES = 2

# 브라우저 창을 띄울지 여부 (True: 숨김, False: 보임 - 디버깅 및 안정성에 유리)
HEADLESS_MODE = True

# 각 동작 사이의 지연 시간 (ms). 봇 탐지를 피하고 안정성을 높임 (50~100 추천)
SLOW_MOTION = 20

# ===== [속도 최적화 설정] =====
# 동시 처리할 상품 개수 (기본: 2, 권장 범위: 1~5)
# - 벤치마크/리뷰 수집 시 2개 권장 (안정성 우선)
# - 기본 정보만 수집 시 3~5개 가능
# - 값이 클수록 빠르지만 DB 연결/락 타임아웃 발생 가능
# - 환경 변수 MAX_CONCURRENT_ITEMS로 오버라이드 가능
MAX_CONCURRENT_ITEMS = int(os.getenv('MAX_CONCURRENT_ITEMS', '2'))

# 페이지 로딩 최대 대기 시간 (ms, 기본: 30000 = 30초)
# - 빠른 크롤링을 원하면 15000~20000으로 줄이기
PAGE_LOAD_TIMEOUT = int(os.getenv('PAGE_LOAD_TIMEOUT', '30000'))

# 개별 요소 대기 시간 (ms, 기본: 5000 = 5초)
# - 빠른 크롤링을 원하면 2000~3000으로 줄이기
ELEMENT_TIMEOUT = int(os.getenv('ELEMENT_TIMEOUT', '5000'))

# --- 2. DB 설정 (로컬 모드) ---
# 환경 변수에서 읽거나, 기본값 사용 (docker-compose.yml 참고)
DB_HOST = os.environ.get("DB_HOST", "localhost")
DB_PORT = int(os.environ.get("DB_PORT", "3307"))
DB_USER = os.environ.get("DB_USER", "root")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "1234")
DB_NAME = os.environ.get("DB_NAME", "danawa")

# --- 3. 크롤링 카테고리 ---
CATEGORIES = {
         'CPU': 'cpu', 
         '쿨러': 'cooler&attribute=687-4015-OR%2C687-4017-OR',
         '메인보드': 'mainboard',
         'RAM': 'RAM',
         '그래픽카드': 'vga',
         'SSD': 'ssd',
         'HDD': 'hdd', 
         '케이스': 'pc case',
         '파워': 'power'
}

# --- 5. SQLAlchemy 엔진 생성 (로컬 MySQL) ---
try:
    # [검증] DB 설정 확인
    if not all([DB_HOST, DB_USER, DB_PASSWORD, DB_NAME]):
        raise ValueError("DB_HOST, DB_USER, DB_PASSWORD, DB_NAME을 설정해야 합니다.")

    # MySQL 연결 문자열 생성 (UTF-8 설정 강화)
    db_url = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}?charset=utf8mb4"
    
    # SQLAlchemy 엔진 생성
    engine = create_engine(
        db_url,
        pool_pre_ping=True,     # 연결 상태 확인 (중요: 끊긴 연결 감지)
        pool_recycle=1800,      # 30분마다 연결 재생성 (MySQL wait_timeout보다 짧게)
        pool_size=15,           # 연결 풀 크기 증가 (동시 처리 개수보다 크게)
        max_overflow=30,        # 추가 연결 허용 증가
        pool_timeout=60,        # 연결 풀 타임아웃 증가 (60초)
        echo=False,             # SQL 로그 출력 여부
        connect_args={
            'charset': 'utf8mb4',
            'init_command': "SET NAMES utf8mb4 COLLATE utf8mb4_unicode_ci",
            'connect_timeout': 30,     # 연결 타임아웃 증가 (30초)
            'read_timeout': 120,       # 읽기 타임아웃 증가 (120초)
            'write_timeout': 120,      # 쓰기 타임아웃 증가 (120초)
            'autocommit': False,       # 명시적 트랜잭션 사용
        }
    )

    with engine.connect() as conn:
        print(f"로컬 MySQL DB 연결 성공 ({DB_HOST}:{DB_PORT}/{DB_NAME})")
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
        
        # (이하 테이블 생성/수정 로직은 동일)
        # ... (180행까지의 기존 try...except...pass 구문들) ...
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
        
        # === 호환성 규칙 테이블 생성 ===
        print("\n=== AI 견적 추천 시스템 테이블 초기화 ===")
        create_compatibility_rules_sql = text("""
        CREATE TABLE IF NOT EXISTS compatibility_rules (
            id BIGINT AUTO_INCREMENT PRIMARY KEY,
            rule_type VARCHAR(50) NOT NULL COMMENT 'cpu_socket, ram_type, power_wattage 등',
            source_value VARCHAR(100) COMMENT '예: AM5, DDR5',
            target_value VARCHAR(100) COMMENT '호환되는 값',
            is_compatible BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            KEY idx_rule_type (rule_type),
            KEY idx_source_value (source_value)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """)
        conn.execute(create_compatibility_rules_sql)
        print("  -> compatibility_rules 테이블 생성/확인 완료")
        
        # === 사용자 견적 구성 테이블 생성 ===
        create_build_configurations_sql = text("""
        CREATE TABLE IF NOT EXISTS build_configurations (
            id BIGINT AUTO_INCREMENT PRIMARY KEY,
            session_id VARCHAR(100) UNIQUE,
            user_budget INT COMMENT '사용자 예산',
            user_purpose VARCHAR(50) COMMENT '게이밍, 사무용, 영상편집 등',
            selected_parts JSON COMMENT '선택된 부품 ID 목록',
            ai_recommendation TEXT COMMENT 'AI 추천 내용',
            compatibility_check JSON COMMENT '호환성 검사 결과',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            KEY idx_session_id (session_id),
            KEY idx_user_purpose (user_purpose)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """)
        conn.execute(create_build_configurations_sql)
        print("  -> build_configurations 테이블 생성/확인 완료")
        
        # === 용도별 부품 가중치 테이블 생성 ===
        create_usage_weights_sql = text("""
        CREATE TABLE IF NOT EXISTS usage_weights (
            id BIGINT AUTO_INCREMENT PRIMARY KEY,
            usage_type VARCHAR(50) NOT NULL COMMENT '게이밍, 영상편집, 사무용 등',
            category VARCHAR(50) NOT NULL COMMENT 'CPU, 그래픽카드 등',
            weight_percentage INT COMMENT '예산 배분 비율 (%)',
            priority INT COMMENT '중요도 순위 (1=최우선)',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE KEY uq_usage_category (usage_type, category)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """)
        conn.execute(create_usage_weights_sql)
        print("  -> usage_weights 테이블 생성/확인 완료")
        
except Exception as e:
    print(f"DB 연결 실패: {e}")
    # (디버깅을 위해 오류 상세 출력)
    import traceback
    traceback.print_exc()
    exit()

def initialize_compatibility_rules(engine):
    """대표적인 호환성 규칙 데이터 삽입"""
    with engine.connect() as conn:
        with conn.begin():
            # 기존 규칙 확인
            check_sql = text("SELECT COUNT(*) FROM compatibility_rules")
            count = conn.execute(check_sql).scalar()
            
            if count > 0:
                print(f"  -> 호환성 규칙 {count}개 이미 존재, 건너뜀")
                return
            
            print("  -> 호환성 규칙 데이터 초기화 중...")
            
            # CPU 소켓 호환성 규칙
            socket_rules = [
                # AMD 소켓
                ('cpu_socket', 'AM5', 'AM5', True),
                ('cpu_socket', 'AM4', 'AM4', True),
                # Intel 소켓
                ('cpu_socket', 'LGA1700', 'LGA1700', True),
                ('cpu_socket', 'LGA1851', 'LGA1851', True),
                ('cpu_socket', 'LGA1200', 'LGA1200', True),
            ]
            
            # RAM 타입 호환성
            ram_rules = [
                ('ram_type', 'DDR5', 'DDR5', True),
                ('ram_type', 'DDR4', 'DDR4', True),
                ('ram_type', 'DDR5', 'DDR4', False),  # 호환 안됨
                ('ram_type', 'DDR4', 'DDR5', False),  # 호환 안됨
            ]
            
            # 메인보드 폼팩터와 케이스 호환성
            formfactor_rules = [
                ('board_case', 'ATX', 'Full Tower', True),
                ('board_case', 'ATX', 'Mid Tower', True),
                ('board_case', 'M-ATX', 'Mid Tower', True),
                ('board_case', 'M-ATX', 'Mini Tower', True),
                ('board_case', 'ITX', 'Mini Tower', True),
            ]
            
            all_rules = socket_rules + ram_rules + formfactor_rules
            
            insert_sql = text("""
                INSERT INTO compatibility_rules (rule_type, source_value, target_value, is_compatible)
                VALUES (:rule_type, :source_value, :target_value, :is_compatible)
            """)
            
            for rule in all_rules:
                conn.execute(insert_sql, {
                    'rule_type': rule[0],
                    'source_value': rule[1],
                    'target_value': rule[2],
                    'is_compatible': rule[3]
                })
            
            print(f"  -> 호환성 규칙 {len(all_rules)}개 삽입 완료")


def initialize_usage_weights(engine):
    """용도별 부품 가중치 초기 데이터 삽입"""
    with engine.connect() as conn:
        with conn.begin():
            # 기존 가중치 확인
            check_sql = text("SELECT COUNT(*) FROM usage_weights")
            count = conn.execute(check_sql).scalar()
            
            if count > 0:
                print(f"  -> 용도별 가중치 {count}개 이미 존재, 건너뜀")
                return
            
            print("  -> 용도별 가중치 데이터 초기화 중...")
            
            # 가중치 데이터: (용도, 카테고리, 예산비율%, 우선순위)
            weights = [
                # 게이밍 PC
                ('게이밍', 'CPU', 20, 2),
                ('게이밍', '그래픽카드', 40, 1),  # 최우선
                ('게이밍', 'RAM', 10, 4),
                ('게이밍', 'SSD', 8, 5),
                ('게이밍', '메인보드', 12, 3),
                ('게이밍', '파워', 7, 6),
                ('게이밍', '케이스', 3, 7),
                
                # 영상편집 PC
                ('영상편집', 'CPU', 35, 1),  # 최우선
                ('영상편집', '그래픽카드', 25, 2),
                ('영상편집', 'RAM', 20, 3),
                ('영상편집', 'SSD', 10, 4),
                ('영상편집', '메인보드', 7, 5),
                ('영상편집', '파워', 2, 6),
                ('영상편집', '케이스', 1, 7),
                
                # 사무용 PC
                ('사무용', 'CPU', 30, 1),
                ('사무용', '그래픽카드', 10, 5),
                ('사무용', 'RAM', 20, 2),
                ('사무용', 'SSD', 20, 3),
                ('사무용', '메인보드', 15, 4),
                ('사무용', '파워', 3, 6),
                ('사무용', '케이스', 2, 7),
                
                # 코딩/개발 PC
                ('코딩', 'CPU', 30, 1),
                ('코딩', '그래픽카드', 15, 4),
                ('코딩', 'RAM', 25, 2),
                ('코딩', 'SSD', 18, 3),
                ('코딩', '메인보드', 10, 5),
                ('코딩', '파워', 1, 6),
                ('코딩', '케이스', 1, 7),
            ]
            
            insert_sql = text("""
                INSERT INTO usage_weights (usage_type, category, weight_percentage, priority)
                VALUES (:usage_type, :category, :weight_percentage, :priority)
            """)
            
            for weight in weights:
                conn.execute(insert_sql, {
                    'usage_type': weight[0],
                    'category': weight[1],
                    'weight_percentage': weight[2],
                    'priority': weight[3]
                })
            
            print(f"  -> 용도별 가중치 {len(weights)}개 삽입 완료")


def parse_cpu_specs(name, spec_string):
    """[수정] P+E코어, 클럭, 캐시, 벤치마크 등 상세 스펙을 지원하는 CPU 파서"""
    specs = {}
    
    # 1. 기본 텍스트 준비
    full_text = name + " / " + spec_string
    spec_parts = [part.strip() for part in spec_string.split('/')]

    # 2. 제조사 확정 (기존 로직)
    if '인텔' in full_text or '코어i' in full_text or '울트라' in full_text:
        specs['manufacturer'] = '인텔'
    elif 'AMD' in full_text or '라이젠' in full_text:
        specs['manufacturer'] = 'AMD'

    # 3. 루프를 돌며 "Key: Value" 및 단순 키워드 스펙 파싱
    for part in spec_parts:
        # "스펙명: 값" 형식에서 '값' 부분만 추출 (없으면 원본)
        value = part.split(':', 1)[-1].strip()

        if '메모리 규격:' in part:
            specs['memory_spec'] = value
        elif '기본 클럭:' in part:
            specs['base_clock'] = value
        elif '최대 클럭:' in part:
            specs['max_clock'] = value
        elif 'L2 캐시:' in part:
            specs['l2_cache'] = value
        elif 'L3 캐시:' in part:
            specs['l3_cache'] = value
        elif 'PBP-MTP:' in part: # 인텔 전력
            specs['power_consumption'] = value
        elif 'TDP:' in part: # AMD 전력
            specs['power_consumption'] = value
        elif '기술 지원:' in part:
            specs['tech_support'] = value
        elif '쿨러:' in part:
            specs['cooler_included'] = value
        elif '시네벤치R23(싱글):' in part:
            specs['cinebench_r23_single'] = value
        elif '시네벤치R23(멀티):' in part:
            specs['cinebench_r23_multi'] = value
        elif '출시가:' in part:
            specs['launch_price'] = value
        elif 'nm' in part and 'process_node' not in specs: # 예: TSMC 3nm
            specs['process_node'] = part
        elif 'PCIe' in part and 'pcie_version' not in specs: # 예: PCIe5.0, 4.0
            specs['pcie_version'] = part
        elif 'MHz' in part and 'memory_clock_default' not in specs: # 예: 6400MHz
            specs['memory_clock_default'] = part
        elif '그래픽' in part and '내장그래픽' not in part and 'graphics_model' not in specs: # 예: 인텔 그래픽스(Xe LPG)
            specs['graphics_model'] = part

    # 4. 정규 표현식으로 복잡/중복 스펙 보완 (기존 로직 + 개선)
    
    # 코어 (기존 로직)
    if 'cores' not in specs:
        core_match = re.search(r'([PE\d\+]+코어)', full_text)
        if core_match:
            specs['cores'] = core_match.group(1)

    # 스레드 (기존 로직)
    if 'threads' not in specs:
        thread_match = re.search(r'([\d\+]+)\s*스레드', full_text)
        if thread_match:
            specs['threads'] = thread_match.group(1).replace(' ', '') + '스레드'

    # 소켓 (개선된 로직: 괄호 안의 소켓도 인식)
    # 예: 인텔(소켓1851), AMD(소켓AM5), 소켓1700
    if 'socket' not in specs:
        socket_match = re.search(r'(소켓[\w\d\+]+)', full_text) # \w+ for AM5
        if socket_match:
            specs['socket'] = socket_match.group(1)
    
    # 코드네임 (기존 로직)
    if 'codename' not in specs:
        codename_match = re.search(r'\(([^)]*(?:레이크|릿지|리프레시|라파엘|버미어|피카소|세잔|시마다 픽|피닉스|Zen\d+)[^)]*)\)', full_text)
        if codename_match:
            specs['codename'] = codename_match.group(1)
    
    # CPU 시리즈 (기존 로직)
    if 'cpu_series' not in specs:
        # '세대' 또는 '(Zen5)' 같은 코드네임도 시리즈로 간주
        series_match = re.search(r'(\d+세대|\(Zen\d+\))', full_text)
        if series_match:
            specs['cpu_series'] = series_match.group(1)
        elif 'codename' in specs: # 코드네임을 시리즈로 활용
            specs['cpu_series'] = specs['codename']

    # CPU 종류 (기존 로직)
    if 'cpu_class' not in specs:
        class_match = re.search(r'(코어\s?(?:울트라|i)\d+|라이젠\s?\d)', name, re.I)
        if class_match:
            specs['cpu_class'] = class_match.group(1).replace(' ', '')

    # 내장그래픽 (기존 로직 + 보완)
    if 'integrated_graphics' not in specs:
        if '내장그래픽' in full_text:
            if '미탑재' in full_text:
                specs['integrated_graphics'] = '미탑재'
            elif '탑재' in full_text:
                specs['integrated_graphics'] = '탑재'
        elif 'graphics_model' in specs: # 그래픽 모델이 있으면 '탑재'로 간주
             specs['integrated_graphics'] = '탑재'
            
    return specs

def parse_cooler_specs(name, spec_string):
    """쿨러 파싱 로직 개선 (CPU 쿨러 / 시스템 쿨러 / 상세스펙 최종본)"""
    specs = {}
    if name: specs['manufacturer'] = name.split()[0]
    
    spec_parts = [part.strip() for part in spec_string.split('/')]
    full_text = name + " / " + spec_string

    # 1. product_type을 명시적으로 탐색 (기존 로직)
    if 'CPU 쿨러' in spec_parts:
        specs['product_type'] = 'CPU 쿨러'
    elif any(s in spec_parts for s in ['시스템 쿨러', '시스템 팬']):
        specs['product_type'] = '시스템 쿨러'
    else:
        # spec_parts에 명시적 타입이 없는 경우, 이름(name)이나 전체 텍스트에서 추론
        if 'CPU 쿨러' in full_text:
            specs['product_type'] = 'CPU 쿨러'
        elif '시스템 쿨러' in full_text or '시스템 팬' in full_text:
            if '시스템 팬 커넥터' not in full_text:
                 specs['product_type'] = '시스템 쿨러'
        else:
            # 최후의 수단: 스펙 내용으로 추론 (CPU 쿨러 스펙이 보이면 CPU 쿨러로)
            if any(s in spec_string for s in ['공랭', '수랭', '타워형', '쿨러 높이', '라디에이터']):
                 specs['product_type'] = 'CPU 쿨러'
            elif ' fan' in name.lower() or ' 팬' in name:
                specs['product_type'] = '시스템 쿨러'
            else:
                specs['product_type'] = '기타 쿨러' # M.2 쿨러 등

    # 2. 루프를 돌며 세부 스펙을 파싱합니다.
    for part in spec_parts:
        # "스펙명: 값" 형식에서 '값' 부분만 추출 (없으면 원본)
        value = part.split(':', 1)[-1].strip()

        # --- [A] 공통 스펙 (CPU 쿨러 & 시스템 쿨러) ---
        if '팬 크기:' in part:
            fan_size_match = re.search(r'(\d+mm)', part) 
            if fan_size_match: specs['fan_size'] = fan_size_match.group(1) # "120mm"
        
        elif '팬 커넥터' in part or ('핀' in part and not value.startswith('12V') and '16핀' not in part): # "4핀", "3핀"
            specs['fan_connector'] = value 
        
        elif 'RPM' in part:
            specs['max_fan_speed'] = value # "1550 RPM" or "3000 RPM"
        elif 'CFM' in part:
            specs['max_airflow'] = value # "66.17 CFM" or "77 CFM"
        elif 'mmH2O' in part:
            specs['static_pressure'] = value # "1.53mmH₂O" or "6.9mmH₂O"
        elif 'dBA' in part:
            specs['max_fan_noise'] = value # "25.6dBA"
        
        elif 'A/S기간' in part or 'A/S 기간' in part:
            specs['warranty_period'] = value # "6년" or "3년"
        
        elif '무게:' in part:
            specs['weight'] = value # "185g" or "850g"

        elif re.search(r'^\d+T$', part): # "25T"
            specs['fan_thickness'] = part 

        elif '베어링:' in part:
            specs['fan_bearing'] = value # "FDB(유체)" or "S-FDB(유체)"

        elif 'PWM 지원' in part:
            specs['pwm_support'] = 'Y'
            
        elif 'LED' in part: 
            specs['led_type'] = value # "non-LED"
            
        # --- [B] 시스템 쿨러 전용 스펙 ---
        if specs.get('product_type') == '시스템 쿨러':
            if '작동전압:' in part:
                specs['operating_voltage'] = value # "팬 12V"
            
            elif '데이지체인' in part:
                specs['daisy_chain'] = 'Y'
            
            elif '제로팬' in part or '0-dB' in part:
                specs['zero_fan'] = 'Y'
            
            elif re.search(r'^\d+개$', part): # "3개", "5개"
                specs['fan_count'] = part

        # --- [C] CPU 쿨러 전용 스펙 ---
        if specs.get('product_type') == 'CPU 쿨러':
            if '공랭' in part: specs['cooling_method'] = '공랭'
            elif '수랭' in part: specs['cooling_method'] = '수랭'
            
            # 공랭 폼팩터
            elif '듀얼타워형' in part: specs['air_cooling_form'] = '듀얼타워형'
            elif '싱글타워형' in part: specs['air_cooling_form'] = '싱글타워형'
            elif '슬림형' in part: specs['air_cooling_form'] = '슬림형'
            elif '일반형' in part: specs['air_cooling_form'] = '일반형'
            elif '서버용' in part: specs['air_cooling_form'] = '서버용'
            
            # 라디에이터
            elif ('라디에이터' in part or '열' in part):
                radiator_match = re.search(r'(1열|2열|3열|4열)', part)
                if radiator_match: specs['radiator_length'] = radiator_match.group(1)
            
            # TDP
            elif 'TDP' in part and ('W' in part or 'w' in part):
                specs['tdp'] = value # "260W"
            
            # Sockets
            elif '인텔 소켓:' in part:
                specs['intel_socket'] = value
            elif 'AMD 소켓:' in part:
                specs['amd_socket'] = value

            # Dimensions
            elif '가로:' in part:
                specs['width'] = value
            elif '세로:' in part:
                specs['depth'] = value
            elif '높이:' in part and '쿨러 높이' not in part: 
                specs['height'] = value
            elif '쿨러 높이:' in part:
                specs['cooler_height'] = value # "155mm"
                
            # Fan Count (CPU specific)
            elif re.search(r'팬 개수: \d+개', part):
                specs['fan_count'] = value # "2개"

    # 3. 후처리 (기존 로직)
    if specs.get('product_type') == '시스템 쿨러' and 'fan_count' not in specs:
        count_match = re.search(r'(\d)(?:IN1|PACK)', name, re.I)
        if count_match:
            specs['fan_count'] = f"{count_match.group(1)}개"
            
    if specs.get('cooling_method') != '수랭' and 'radiator_length' in specs:
        del specs['radiator_length']
            
    return specs

def parse_motherboard_specs(name, spec_string):
    """메인보드 파싱 로직 개선 (사용자 요청 스펙 모두 반영)"""
    specs = {}
    if name: specs['manufacturer'] = name.split()[0]

    # '/'로 나뉜 기본 스펙 리스트
    spec_parts = [part.strip() for part in spec_string.split('/')]
    
    # 원본 스펙 문자열 (복잡한 파싱용)
    full_text = " / ".join(spec_parts)

    # --- 1. 기본 스펙 (루프 파싱) ---
    for part in spec_parts:
        part_no_keyword = part.replace('CPU 소켓:','').strip()
        
        if '소켓' in part and 'CPU 소켓' in part: 
            specs['socket'] = part_no_keyword
            specs['cpu_socket'] = part_no_keyword  # 호환성을 위해 cpu_socket에도 저장
        elif re.search(r'^[A-Z]\d{3}[A-Z]*$', part): 
            specs['chipset'] = part
        elif 'ATX' in part or 'ITX' in part: 
            specs['form_factor'] = part
            specs['board_form_factor'] = part  # 호환성을 위해 board_form_factor에도 저장
        elif 'DDR' in part: 
            specs['memory_spec'] = part
            # DDR4, DDR5 등 메모리 타입 추출하여 memory_type에도 저장
            if 'DDR5' in part:
                specs['memory_type'] = 'DDR5'
            elif 'DDR4' in part:
                specs['memory_type'] = 'DDR4'
            elif 'DDR3' in part:
                specs['memory_type'] = 'DDR3'
        elif 'VGA 연결' in part or 'PCIe' in part and 'vga_connection' not in specs: 
            specs['vga_connection'] = part
            # VGA 인터페이스 정보도 별도로 저장 (호환성 체크용)
            if 'VGA 연결' in part:
                specs['vga_interface'] = part
        elif '메모리 슬롯' in part: 
            specs['memory_slots'] = part
        elif 'M.2:' in part: 
            specs['m2_slots'] = part.split(':')[-1].strip()
        elif 'SATA3:' in part:
            specs['sata3_ports'] = part.split(':')[-1].strip()
        elif 'ch(' in part or '.1ch' in part:
            specs['audio_channels'] = part
        elif '무선랜' in part or 'Wi-Fi' in part: 
            specs['wireless_lan'] = 'Y' # 존재 여부
        elif '블루투스' in part:
            specs['bluetooth'] = 'Y' # 존재 여부
        elif 'MHz' in part and 'memory_clock' not in specs:
            # 메모리 클럭 추출 (예: "8000MHz", "6000MHz(PC5-48000)")
            specs['memory_clock'] = part

    # --- 2. 정규식을 이용한 상세 스펙 추출 (전체 텍스트 기반) ---
    
    # 전원부
    if (m := re.search(r'전원부:\s*([\d\+\s]+페이즈)', full_text)):
        specs['power_phases'] = m.group(1)
        specs['power_phase'] = m.group(1)  # 호환성을 위해 power_phase에도 저장
        
    # 메모리
    if (m := re.search(r'(\d+)MHz\s*\((PC\d-[\d]+)\)', full_text)):
        specs['memory_clock'] = m.group(1) + 'MHz'
    elif 'memory_clock' in specs and 'MHz' not in specs['memory_clock']:
        # 이미 memory_clock이 설정되었지만 MHz가 없는 경우 (예: "8000")
        pass  # 유지
    if (m := re.search(r'메모리 용량:\s*(최대 [\d,]+GB)', full_text)):
        specs['memory_capacity_max'] = m.group(1)
        specs['max_memory_capacity'] = m.group(1)  # 호환성을 위해 max_memory_capacity에도 저장
    if 'XMP' in full_text: 
        specs['memory_profile_xmp'] = 'Y'
        specs['xmp'] = 'Y'
    if 'EXPO' in full_text: 
        specs['memory_profile_expo'] = 'Y'
        specs['expo'] = 'Y'

    # 확장슬롯
    if (m := re.search(r'PCIe버전:\s*([\w\d\.,\s]+)', full_text)):
        specs['pcie_versions'] = m.group(1).strip().rstrip(',')
    if (m := re.search(r'PCIex16:\s*(\d+개)', full_text)):
        specs['pciex16_slots'] = m.group(1)
    if (m := re.search(r'PCIex1:\s*([\d+]+개)', full_text)):
        specs['pciex1_slots'] = m.group(1)

    # 저장장치
    if (m := re.search(r'M.2 연결:\s*([\w\d\.,\s]+)', full_text)):
        specs['m2_interface'] = m.group(1).strip().rstrip(',')

    # 후면단자 (항목별 존재 여부 및 개수)
    if (m := re.search(r'후면단자:\s*([^\/]+(?:\s*\/[^\/]+)*)', full_text)):
        rear_io_text = m.group(1)
        if 'HDMI' in rear_io_text: specs['rear_io_hdmi'] = 'Y'
        if 'DP' in rear_io_text: specs['rear_io_dp'] = 'Y'
        if 'USB 3' in rear_io_text: specs['rear_io_usb3'] = 'Y'
        if 'USB 2.0' in rear_io_text: specs['rear_io_usb2'] = 'Y'
        if 'RJ-45' in rear_io_text: specs['rear_io_rj45'] = 'Y'
        if '오디오잭' in rear_io_text: specs['rear_io_audio'] = 'Y'
        if 'PS/2' in rear_io_text: specs['rear_io_ps2'] = 'Y'
        if 'BIOS플래시백' in rear_io_text: specs['rear_io_bios_flashback'] = 'Y'
            
    if (m := re.search(r'USB A타입:\s*(\d+개)', full_text)):
        specs['rear_io_usb_a'] = m.group(1)
    if (m := re.search(r'USB C타입:\s*(\d+개)', full_text)):
        specs['rear_io_usb_c'] = m.group(1)

    # 랜/오디오
    if (m := re.search(r'유선랜 칩셋:\s*([\w\s]+)', full_text)):
        specs['lan_chipset'] = m.group(1).strip()
    if (m := re.search(r'([\d\.]+)Gbps', full_text)):
        specs['lan_speed'] = m.group(1) + 'Gbps'
    if (m := re.search(r'RJ-45:\s*(\d+개)', full_text)):
        specs['rj45_ports'] = m.group(1)
    if (m := re.search(r'오디오 칩셋:\s*([\w\s]+)', full_text)):
        specs['audio_chipset'] = m.group(1).strip()

    # 내부 I/O
    if 'USB3.0 헤더' in full_text: specs['internal_io_usb3'] = 'Y'
    if 'USB2.0 헤더' in full_text: specs['internal_io_usb2'] = 'Y'
    if 'USB3.0 Type C 헤더' in full_text: specs['internal_io_usb_c'] = 'Y'
    if 'RGB 12V 4핀 헤더' in full_text: specs['internal_io_rgb_12v'] = 'Y'
    if 'ARGB 5V 3핀 헤더' in full_text: specs['internal_io_argb_5v'] = 'Y'
    if (m := re.search(r'시스템팬 4핀:\s*(\d+개)', full_text)):
        specs['internal_io_sys_fan'] = m.group(1)
    if 'TPM 헤더' in full_text: specs['internal_io_tpm'] = 'Y'
    if '프론트오디오AAFP 헤더' in full_text: specs['internal_io_audio'] = 'Y'

    # 특징
    if '전원부 방열판' in full_text: specs['feature_vr_heatsink'] = 'Y'
    if 'M.2 히트싱크' in full_text: specs['feature_m2_heatsink'] = 'Y'
    if 'UEFI' in full_text: specs['feature_uefi'] = 'Y'
    if (m := re.search(r'(\d{2}년 \d{1,2}월부로.*)', full_text)):
        specs['product_note'] = m.group(1)

    # --- 3. 소켓 및 메모리 타입 추론 (정보가 없는 경우 칩셋이나 제품명에서 추론) ---
    chipset = specs.get('chipset', '')
    product_name_upper = name.upper() if name else ''
    
    # 3-1. 소켓 추론
    if 'socket' not in specs or not specs['socket']:
        # AMD 소켓 추론 (칩셋 기반)
        if chipset:
            if any(chip in chipset for chip in ['B850', 'X870', 'A620', 'B650', 'X670']):
                specs['socket'] = 'AM5'
                specs['cpu_socket'] = 'AM5'
            elif any(chip in chipset for chip in ['B550', 'X570', 'A520']):
                specs['socket'] = 'AM4'
                specs['cpu_socket'] = 'AM4'
            # Intel 소켓 추론 (칩셋 기반)
            elif any(chip in chipset for chip in ['Z890', 'B860', 'H810']):
                specs['socket'] = 'LGA1851'
                specs['cpu_socket'] = 'LGA1851'
            elif any(chip in chipset for chip in ['Z790', 'B760', 'H770', 'B660']):
                specs['socket'] = 'LGA1700'
                specs['cpu_socket'] = 'LGA1700'
            elif any(chip in chipset for chip in ['Z690', 'H670']):
                specs['socket'] = 'LGA1700'
                specs['cpu_socket'] = 'LGA1700'
        
        # 칩셋에서 찾지 못한 경우 제품명에서 추론
        if ('socket' not in specs or not specs['socket']) and product_name_upper:
            # AMD 제품명 기반 추론
            if any(chip in product_name_upper for chip in ['B850', 'X870', 'B650', 'X670', 'A620']):
                specs['socket'] = 'AM5'
                specs['cpu_socket'] = 'AM5'
            elif any(chip in product_name_upper for chip in ['B550', 'X570', 'A520']):
                specs['socket'] = 'AM4'
                specs['cpu_socket'] = 'AM4'
            # Intel 제품명 기반 추론
            elif any(chip in product_name_upper for chip in ['Z890', 'B860', 'H810']):
                specs['socket'] = 'LGA1851'
                specs['cpu_socket'] = 'LGA1851'
            elif any(chip in product_name_upper for chip in ['Z790', 'B760', 'H770']):
                specs['socket'] = 'LGA1700'
                specs['cpu_socket'] = 'LGA1700'
            elif any(chip in product_name_upper for chip in ['Z690', 'B660', 'H670']):
                specs['socket'] = 'LGA1700'
                specs['cpu_socket'] = 'LGA1700'
    
    # 3-2. 메모리 타입 추론 (메모리 타입 정보가 없는 경우)
    if 'memory_type' not in specs or not specs['memory_type']:
        # 칩셋 기반 메모리 타입 추론 (최신 칩셋들은 DDR5 전용)
        if chipset:
            # AM5 칩셋은 DDR5 전용
            if any(chip in chipset for chip in ['B850', 'X870', 'B650', 'X670', 'A620']):
                specs['memory_type'] = 'DDR5'
            # AM4 칩셋은 DDR4 전용
            elif any(chip in chipset for chip in ['B550', 'X570', 'A520', 'B450', 'X470']):
                specs['memory_type'] = 'DDR4'
            # 최신 Intel 칩셋 (13세대 이후)는 주로 DDR5 (일부 DDR4 지원)
            elif any(chip in chipset for chip in ['Z890', 'B860', 'H810']):
                specs['memory_type'] = 'DDR5'
            # 12-13세대 Intel 칩셋은 DDR4/DDR5 혼용 (정확한 판단 어려움)
            # Z790, B760 등은 제품에 따라 DDR4 또는 DDR5 지원
            # 이 경우 memory_clock으로 추론 시도
            elif any(chip in chipset for chip in ['Z790', 'B760', 'H770']):
                memory_clock_str = str(specs.get('memory_clock', ''))
                if memory_clock_str:
                    clock_num = int(''.join(filter(str.isdigit, memory_clock_str))) if any(c.isdigit() for c in memory_clock_str) else 0
                    # DDR5는 일반적으로 4800MHz 이상
                    if clock_num >= 4800:
                        specs['memory_type'] = 'DDR5'
                    # DDR4는 일반적으로 2133~3200MHz
                    elif 2000 <= clock_num < 4800:
                        specs['memory_type'] = 'DDR4'
        
        # 칩셋에서 찾지 못한 경우 제품명에서 추론
        if ('memory_type' not in specs or not specs['memory_type']) and product_name_upper:
            # AM5 제품명은 DDR5 전용
            if any(chip in product_name_upper for chip in ['B850', 'X870', 'B650', 'X670', 'A620']):
                specs['memory_type'] = 'DDR5'
            # AM4 제품명은 DDR4 전용
            elif any(chip in product_name_upper for chip in ['B550', 'X570', 'A520', 'B450']):
                specs['memory_type'] = 'DDR4'
            # Intel 최신 칩셋
            elif any(chip in product_name_upper for chip in ['Z890', 'B860', 'H810']):
                specs['memory_type'] = 'DDR5'

    return specs

def parse_ram_specs(name, spec_string):
    """RAM 파싱 로직 개선 (사용자 요청 스펙 모두 반영)"""
    specs = {}
    if name: specs['manufacturer'] = name.split()[0]
    
    spec_parts = [part.strip() for part in spec_string.split('/')]
    full_text = " / ".join(spec_parts) # LED 시스템 등 '/'로 분리 안되는 스펙 검사용

    for part in spec_parts:
        # --- 1. 기본 스펙 ---
        if '데스크탑용' in part or '노트북용' in part: 
            specs['device_type'] = part
        elif re.match(r'^DDR\d+$', part): 
            specs['product_class'] = part
        elif re.search(r'^\d+GB$|^\d+TB$', part) and 'capacity' not in specs: 
            specs['capacity'] = part
        
        # --- 2. 상세 스펙 (사용자 요청 기준) ---
        
        # 클럭
        elif (m := re.search(r'(\d+MHz)\s*\((PC\d-[\d]+)\)', part)):
            specs['clock_speed'] = m.group(1)
            specs['pc_clock_speed'] = m.group(2)
        elif 'MHz' in part and 'clock_speed' not in specs:
            specs['clock_speed'] = part
        
        # 램타이밍
        elif '램타이밍:' in part:
            specs['ram_timing'] = part.split(':')[-1].strip()
        
        # 전압
        elif (m := re.search(r'([\d\.]+)V$', part)):
            specs['voltage'] = m.group(1) + 'V'
            
        # 램개수
        elif '램개수:' in part:
            specs['ram_count'] = part.split(':')[-1].strip()
        
        # LED
        elif 'LED 라이트' in part:
            specs['led_light'] = 'Y'
        elif 'LED색상:' in part:
            specs['led_color'] = part.split(':')[-1].strip()

        # 프로파일
        elif 'XMP' in part: # XMP3.0, XMP 등
            specs['memory_profile_xmp'] = 'Y'
        elif 'EXPO' in part:
            specs['memory_profile_expo'] = 'Y'
        
        # 기타
        elif '온다이ECC' in part:
            specs['on_die_ecc'] = 'Y'
        
        # 방열판
        elif '히트싱크:' in part:
            specs['heatsink_presence'] = part.split(':')[-1].strip()
        elif '방열판 색상:' in part:
            specs['heatsink_color'] = part.split(':')[-1].strip()
        elif '방열판' in part and 'heatsink_presence' not in specs: # '방열판'만 있는 경우
            specs['heatsink_presence'] = 'Y'
            
        # 높이
        elif '높이:' in part:
            specs['height'] = part.split(':')[-1].strip()
            
        # 모듈제조사
        elif '모듈제조사:' in part:
            specs['module_manufacturer'] = part.split(':')[-1].strip()

    # --- 3. 전체 텍스트 기반 스펙 (LED 시스템) ---
    if (m := re.search(r'LED 시스템:\s*([^\/]+)', full_text)):
        specs['led_system'] = m.group(1).strip()

    return specs

def parse_vga_specs(name, spec_string):
    """그래픽카드 파싱 로직 개선 (사용자 요청 스펙 모두 반영)"""
    specs = {}
    if name: specs['manufacturer'] = name.split()[0]
    
    spec_parts = [part.strip() for part in spec_string.split('/')]
    full_text = " / ".join(spec_parts) # '/'로 분리 안되는 스펙 검사용

    # --- 1. 기본 스펙 (루프 파싱) ---
    for part in spec_parts:
        if 'RTX' in part or 'GTX' in part: 
            specs['nvidia_chipset'] = part
        elif 'RX' in part: 
            specs['amd_chipset'] = part
        elif 'Arc' in part: 
            specs['intel_chipset'] = part
        elif 'PCIe' in part and 'gpu_interface' not in specs: 
            specs['gpu_interface'] = part
        elif 'GDDR' in part and 'gpu_memory_type' not in specs:
            specs['gpu_memory_type'] = part # 예: GDDR7
        elif 'GB' in part and 'TB' not in part and 'gpu_memory_capacity' not in specs:
             # '용량'이 다른 스펙(예: HDD)과 겹칠 수 있으므로 GPU 파서 내에서만 사용
            specs['gpu_memory_capacity'] = part # 예: 12GB
        elif '팬 개수' in part or ('팬' in part and len(part) < 4):
            specs['fan_count'] = part # 3팬, 2팬 등
        
    # --- 2. 정규식을 이용한 상세 스펙 추출 (전체 텍스트 기반) ---
    
    # 전력 및 크기
    if (m := re.search(r'정격파워\s*([\w\d\s]+이상)', full_text)):
        specs['recommended_psu'] = m.group(1)
    if (m := re.search(r'전원 포트:\s*([^\/]+)', full_text)):
        specs['power_connector'] = m.group(1).strip()
    if (m := re.search(r'가로\(길이\):\s*([\d\.]+mm)', full_text)):
        specs['gpu_length'] = m.group(1)
    if (m := re.search(r'두께:\s*([\d\.]+mm)', full_text)):
        specs['gpu_thickness'] = m.group(1)
    if (m := re.search(r'사용전력:\s*([\w\d\s]+)', full_text)):
        specs['power_consumption'] = m.group(1).strip()

    # 클럭 및 프로세서
    if (m := re.search(r'베이스클럭:\s*(\d+MHz)', full_text)):
        specs['base_clock'] = m.group(1)
    if (m := re.search(r'부스트클럭:\s*(\d+MHz)', full_text)):
        specs['boost_clock'] = m.group(1)
    if (m := re.search(r'OC클럭:\s*(\d+MHz)', full_text)):
        specs['oc_clock'] = m.group(1)
    if (m := re.search(r'스트림 프로세서:\s*([\d,]+)개', full_text)):
        specs['stream_processors'] = m.group(1) + '개'

    # 출력 및 지원
    if (m := re.search(r'출력단자:\s*([^\/]+)', full_text)):
        specs['output_ports'] = m.group(1).strip()
    if '8K' in full_text: specs['support_8k'] = 'Y'
    if 'HDR' in full_text: specs['support_hdr'] = 'Y'
    if 'HDCP 2.3' in full_text: specs['support_hdcp'] = '2.3'
    if (m := re.search(r'A/S\s*([\d년]+)', full_text)):
        specs['warranty_period'] = m.group(1)

    # 특징
    if '제로팬' in full_text or '0-dB' in full_text:
        specs['zero_fan'] = 'Y'
    if '백플레이트' in full_text:
        specs['has_backplate'] = 'Y'
    if 'DrMOS' in full_text:
        specs['feature_drmos'] = 'Y'
    if 'LED 라이트' in full_text:
        specs['led_light'] = 'Y'
    if (m := re.search(r'MYSTIC LIGHT', full_text)): # LED 시스템은 예시가 하나라 하드코딩
        specs['led_system'] = m.group(0)
    if (m := re.search(r'구성품:\s*([^\/]+)', full_text)):
        specs['accessories'] = m.group(1).strip()

    return specs

def parse_ssd_specs(name, spec_string):
    """SSD 파싱 로직 개선 (사용자 요청 스펙 모두 반영)"""
    specs = {}
    if name: specs['manufacturer'] = name.split()[0]
    
    spec_parts = [part.strip() for part in spec_string.split('/')]
    full_text = " / ".join(spec_parts) # '/'로 분리 안되는 스펙 검사용

    # --- 1. 기본 스펙 (루프 파싱) ---
    for part in spec_parts:
        if 'M.2' in part or '2.5인치' in part or 'SATA' in part and 'form_factor' not in specs: 
            specs['form_factor'] = part
        elif 'PCIe' in part or 'SATA' in part and 'ssd_interface' not in specs: 
            specs['ssd_interface'] = part
        elif ('TLC' in part or 'QLC' in part or 'MLC' in part) and 'memory_type' not in specs: 
            specs['memory_type'] = part
        elif 'DRAM 탑재' in part or 'DRAM 미탑재' in part: 
            specs['ram_mounted'] = part
        elif 'DDR' in part and 'GB' in part:
            specs['ram_spec'] = part
        elif '컨트롤러:' in part:
            specs['controller'] = part.split(':')[-1].strip()
        
        # 성능
        elif '순차읽기:' in part:
            specs['sequential_read'] = part.split(':')[-1].strip()
        elif '순차쓰기:' in part:
            specs['sequential_write'] = part.split(':')[-1].strip()
        elif '읽기IOPS:' in part:
            specs['read_iops'] = part.split(':')[-1].strip()
        elif '쓰기IOPS:' in part:
            specs['write_iops'] = part.split(':')[-1].strip()

        # 지원기능
        elif 'TRIM' in part: specs['support_trim'] = 'Y'
        elif 'GC' in part: specs['support_gc'] = 'Y'
        elif 'SLC캐싱' in part: specs['support_slc_caching'] = 'Y'
        elif 'S.M.A.R.T' in part: specs['support_smart'] = 'Y'
        elif 'DEVSLP' in part: specs['support_devslp'] = 'Y'
        elif 'AES 암호화' in part: specs['support_aes'] = 'Y'
        elif '전용 S/W' in part: specs['support_sw'] = 'Y'
        
        # 환경특성
        elif 'MTBF:' in part:
            specs['mtbf'] = part.split(':')[-1].strip()
        elif 'TBW:' in part:
            specs['tbw'] = part.split(':')[-1].strip()
        elif 'PS5 호환' in part:
            specs['ps5_compatible'] = 'Y'
        elif 'A/S기간:' in part:
            specs['warranty_period'] = part.split(':')[-1].strip()
        elif '방열판' in part and 'heatsink_presence' not in specs:
            specs['heatsink_presence'] = part # 방열판 미포함, 방열판 포함 등
        elif '두께:' in part:
            specs['ssd_thickness'] = part.split(':')[-1].strip()
        elif (m := re.search(r'(\d+g)$', part)):
            specs['ssd_weight'] = m.group(1)
    
    # --- 2. 루프로 잡기 힘든 스펙 (A/S 기간 등) ---
    if 'warranty_period' not in specs:
         if (m := re.search(r'A/S\s*([\w\d년\s,]+)', full_text)):
            specs['warranty_period'] = m.group(1).strip()
    if 'capacity' not in specs: # 'TB'/'GB'가 TBW와 겹칠 수 있으므로 마지막에 체크
        for part in spec_parts:
            # 'TB' 또는 'GB'를 포함하지만 'TBW'나 'DDR'(DRAM스펙)은 아닌 경우
            if ('TB' in part or 'GB' in part) and 'TBW' not in part and 'DDR' not in part and 'capacity' not in specs:
                specs['capacity'] = part
                break

    return specs

def parse_hdd_specs(name, spec_string):
    """HDD 파싱 로직 개선 (사용자 요청 스펙 모두 반영)"""
    specs = {}
    if name: specs['manufacturer'] = name.split()[0]
    
    spec_parts = [part.strip() for part in spec_string.split('/')]
    full_text = " / ".join(spec_parts) # '/'로 분리 안되는 스펙 검사용

    for part in spec_parts:
        if 'HDD (' in part: # HDD (NAS용)
            specs['product_class'] = part
        elif 'cm' in part or '인치' in part: # 8.9cm(3.5인치)
            specs['form_factor'] = part
        elif ('TB' in part or 'GB' in part) and 'disk_capacity' not in specs: 
            specs['disk_capacity'] = part
        elif 'SATA' in part: # SATA3 (6Gb/s)
            specs['hdd_interface'] = part
        elif 'RPM' in part: # 7,200RPM
            specs['rotation_speed'] = part
        elif '메모리' in part or '버퍼' in part: # 메모리 512MB
            specs['buffer_capacity'] = part
        elif 'MB/s' in part: # 275MB/s
            specs['transfer_rate'] = part
        elif '기록방식:' in part:
            specs['recording_method'] = part.split(':')[-1].strip()
        elif '두께:' in part:
            specs['hdd_thickness'] = part.split(':')[-1].strip()
        elif '헬륨충전' in part:
            specs['helium_filled'] = 'Y'
        elif 'RV센서' in part:
            specs['rv_sensor'] = 'Y'
        elif '사용보증:' in part:
            specs['mtbf'] = part.split(':')[-1].strip()
        elif '소음' in part and 'dB' in part: # 소음(유휴/탐색): 28/32dB
            specs['noise_level'] = part.split(':')[-1].strip()
        elif 'A/S 정보:' in part:
            specs['hdd_warranty'] = part.split(':')[-1].strip()
    
    # A/S 정보가 루프에서 안 잡혔을 경우
    if 'hdd_warranty' not in specs:
         if (m := re.search(r'A/S 정보:\s*([^\/]+)', full_text)):
            specs['hdd_warranty'] = m.group(1).strip()

    return specs

def parse_case_specs(name, spec_string):
    """케이스 파싱 로직 개선 (사용자 요청 스펙 모두 반영)"""
    specs = {}
    if name: specs['manufacturer'] = name.split()[0]
    
    spec_parts = [part.strip() for part in spec_string.split('/')]
    full_text = " / ".join(spec_parts) # '/'로 분리 안되는 스펙 검사용

    # --- 1. 기본 스펙 (루프 파싱) ---
    for part in spec_parts:
        if '케이스' in part and '(' not in part and 'product_class' not in specs: # 'PC케이스' or 'M-ATX 케이스'
            specs['product_class'] = part
        elif '지원보드규격:' in part:
            specs['supported_board'] = part.split(':')[-1].strip()
        elif 'VGA' in part and ('mm' in part or '길이' in part) and 'vga_length' not in specs:
            specs['vga_length'] = part.split(':')[-1].strip()
        elif 'CPU' in part and ('mm' in part or '높이' in part) and 'cpu_cooler_height_limit' not in specs:
            specs['cpu_cooler_height_limit'] = part.split(':')[-1].strip()
        elif '타워' in part: # 미니타워, 빅타워 등
            specs['case_size'] = part
        elif '파워미포함' in part or '파워포함' in part:
            specs['psu_included'] = part
        elif '측면:' in part: # 측면 패널 타입: (Fallback)
            specs['panel_side'] = part.split(':')[-1].strip()
        elif '파워 장착 길이:' in part:
            specs['psu_length'] = part.split(':')[-1].strip()
        elif '파워 위치:' in part:
            specs['psu_location'] = part.split(':')[-1].strip()
        elif 'LED 색상:' in part:
            specs['led_color'] = part.split(':')[-1].strip()

    # --- 2. 정규식을 이용한 상세 스펙 추출 (전체 텍스트 기반) ---
    
    # 패널
    if (m := re.search(r'전면 패널 타입:\s*([^\/]+)', full_text)):
        specs['panel_front'] = m.group(1).strip()
    if (m := re.search(r'측면 패널 타입:\s*([^\/]+)', full_text)):
        specs['panel_side'] = m.group(1).strip() # 루프 파싱 덮어쓰기 (더 정확)

    # 쿨러/튜닝
    if (m := re.search(r'쿨링팬:\s*(총[\d]+개)', full_text)):
        specs['cooling_fan_total'] = m.group(1)
    if (m := re.search(r'LED팬:\s*([\d]+개)', full_text)):
        specs['cooling_fan_led'] = m.group(1)
    if (m := re.search(r'후면:\s*([^\/]+)', full_text)):
        specs['cooling_fan_rear'] = m.group(1).strip()

    # 크기
    if (m := re.search(r'너비\(W\):\s*([\d\.]+mm)', full_text)):
        specs['case_width'] = m.group(1)
    if (m := re.search(r'깊이\(D\):\s*([\d\.]+mm)', full_text)):
        specs['case_depth'] = m.group(1)
    if (m := re.search(r'높이\(H\):\s*([\d\.]+mm)', full_text)):
        specs['case_height'] = m.group(1)

    return specs

def extract_capacity_from_option(option_text, category_name):
    """
    가격 옵션 텍스트에서 용량 정보 추출
    
    Args:
        option_text: 가격 옵션 텍스트 (예: "4TB 629,940원", "32GB(16Gx2) 807,970원", "1위 2TB 329,390원")
        category_name: 카테고리 이름 ('RAM', 'SSD', 'HDD')
    
    Returns:
        용량 문자열 (예: "4TB", "32GB (16GB x2)", "2TB") 또는 None
    """
    if not option_text:
        return None
    
    # RAM의 경우: "32GB(16Gx2)", "48GB(24Gx2)", "16GB x2", "32GB (16GB x2)", "J 패키지" 등
    if category_name == 'RAM':
        # 패턴 1: "32GB(16Gx2)" 또는 "48GB(24Gx2)" - 괄호 안에 축약형
        pattern1 = re.search(r'(\d+GB)\((\d+)Gx(\d+)\)', option_text, re.IGNORECASE)
        if pattern1:
            total_capacity = pattern1.group(1)  # 예: "32GB"
            single_capacity_num = int(pattern1.group(2))  # 예: 16
            count = int(pattern1.group(3))  # 예: 2
            single_capacity = f"{single_capacity_num}GB"
            return f"{total_capacity} ({single_capacity} x{count})"
        
        # 패턴 2: "32GB(16GBx2)" - 괄호 안에 GB 포함
        pattern2 = re.search(r'(\d+GB)\((\d+GB)x(\d+)\)', option_text, re.IGNORECASE)
        if pattern2:
            total_capacity = pattern2.group(1)  # 예: "32GB"
            single_capacity = pattern2.group(2)  # 예: "16GB"
            count = int(pattern2.group(3))  # 예: 2
            return f"{total_capacity} ({single_capacity} x{count})"
        
        # 패턴 3: "16GB x2" 또는 "16GB x 2" - 공백 포함
        pattern3 = re.search(r'(\d+GB)\s*x\s*(\d+)', option_text, re.IGNORECASE)
        if pattern3:
            single_capacity = pattern3.group(1)  # 예: "16GB"
            count = int(pattern3.group(2))  # 예: 2
            # 총 용량 계산
            single_capacity_num = int(single_capacity.replace('GB', ''))
            total_capacity_num = single_capacity_num * count
            return f"{total_capacity_num}GB ({single_capacity} x{count})"
        
        # 패턴 4: "32GB (16GB x2)" - 괄호와 공백 포함
        pattern4 = re.search(r'(\d+GB)\s*\((\d+GB)\s*x\s*(\d+)\)', option_text, re.IGNORECASE)
        if pattern4:
            total_capacity = pattern4.group(1)  # 예: "32GB"
            single_capacity = pattern4.group(2)  # 예: "16GB"
            count = int(pattern4.group(3))  # 예: 2
            return f"{total_capacity} ({single_capacity} x{count})"
        
        # 패턴 5: "J 패키지" 또는 "K 패키지" 등 - 패키지 정보만 있는 경우
        # 이 경우 용량 정보는 상품명에서 추출해야 하므로, 패키지 정보만 반환
        package_match = re.search(r'([JK])\s*패키지', option_text, re.IGNORECASE)
        if package_match:
            # J 패키지 = 2개, K 패키지 = 4개 (일반적인 규칙)
            package_type = package_match.group(1).upper()
            package_count = 2 if package_type == 'J' else 4 if package_type == 'K' else 2
            # 용량 정보가 함께 있는지 확인
            capacity_match = re.search(r'(\d+GB)', option_text, re.IGNORECASE)
            if capacity_match:
                total_capacity = capacity_match.group(1)
                # 단일 용량 추정 (총 용량 / 패키지 개수)
                total_capacity_num = int(total_capacity.replace('GB', ''))
                single_capacity_num = total_capacity_num // package_count
                single_capacity = f"{single_capacity_num}GB"
                return f"{total_capacity} ({single_capacity} x{package_count})"
            else:
                # 용량 정보가 없으면 패키지 정보만 반환
                return f"{package_type} 패키지"
        
        # 패턴 6: 단순 용량 패턴 (예: "32GB") - 패키지 정보 없음
        capacity_match = re.search(r'(\d+GB)', option_text, re.IGNORECASE)
        if capacity_match:
            return capacity_match.group(1)
    
    # SSD, HDD의 경우: "4TB", "2TB", "1TB", "512GB" 등
    # 또는 "8TB 135원/1GB 1,079,080원" 같은 형식
    elif category_name in ['SSD', 'HDD']:
        # TB 우선 검색 (숫자 + TB 패턴, 앞뒤 공백이나 다른 문자 허용)
        tb_match = re.search(r'(\d+(?:\.\d+)?)\s*TB', option_text, re.IGNORECASE)
        if tb_match:
            return f"{tb_match.group(1)}TB"
        
        # GB 검색 (숫자 + GB 패턴)
        gb_match = re.search(r'(\d+(?:\.\d+)?)\s*GB', option_text, re.IGNORECASE)
        if gb_match:
            return f"{gb_match.group(1)}GB"
    
    return None

def parse_power_specs(name, spec_string):
    """파워 파싱 로직 개선 (사용자 요청 스펙 모두 반영)"""
    specs = {}
    if name: specs['manufacturer'] = name.split()[0]
    
    spec_parts = [part.strip() for part in spec_string.split('/')]
    full_text = " / ".join(spec_parts) # '/'로 분리 안되는 스펙 검사용

    for part in spec_parts:
        if '파워' in part and 'ATX' in part and 'product_class' not in specs: 
            specs['product_class'] = part # ATX 파워
        elif 'W' in part and 'rated_output' not in specs: 
            specs['rated_output'] = part # 850W
        elif '80 PLUS' in part: 
            specs['eighty_plus_cert'] = part # 80 PLUS 브론즈
        elif '케이블연결:' in part:
            specs['cable_connection'] = part.split(':')[-1].strip()
        elif 'ETA인증:' in part:
            specs['eta_cert'] = part.split(':')[-1].strip()
        elif 'LAMBDA인증:' in part:
            specs['lambda_cert'] = part.split(':')[-1].strip()
        elif '+12V' in part and '레일' in part:
            specs['plus_12v_rail'] = part # +12V 싱글레일
        elif '+12V 가용률:' in part:
            specs['plus_12v_availability'] = part.split(':')[-1].strip()
        elif 'PFC' in part: # 액티브PFC
            specs['pfc_circuit'] = part
        elif 'PF(역률):' in part:
            specs['pf_rate'] = part.split(':')[-1].strip()
        elif 'mm 팬' in part: # 120mm 팬
            specs['fan_size'] = part
        elif '깊이:' in part:
            specs['psu_depth'] = part.split(':')[-1].strip()
        elif '무상' in part or 'A/S' in part and 'warranty_period' not in specs:
            specs['warranty_period'] = part # 무상 7년
            
        # 커넥터
        elif '메인전원:' in part:
            specs['main_connector'] = part.split(':')[-1].strip()
        elif '보조전원:' in part:
            specs['aux_connector'] = part.split(':')[-1].strip()
        elif 'PCIe 16핀' in part:
            specs['pcie_16pin'] = part.split(':')[-1].strip()
        elif 'PCIe 8핀' in part:
            specs['pcie_8pin'] = part.split(':')[-1].strip()
        elif 'SATA:' in part:
            specs['sata_connectors'] = part.split(':')[-1].strip()
        elif 'IDE 4핀:' in part:
            specs['ide_4pin_connectors'] = part.split(':')[-1].strip()
            
        # 부가기능
        elif '대기전력 1W 미만' in part:
            specs['feature_standby_power'] = 'Y'
        elif '플랫케이블' in part:
            specs['feature_flat_cable'] = 'Y'
            
    # 변경사항 (전체 텍스트에서 검색)
    if (m := re.search(r'(\d{2}년 \d{1,2}월.*)', full_text)):
        specs['product_note'] = m.group(1)

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
async def scrape_cinebench_r23(browser, cpu_name, conn, part_id, category_name='CPU'):
    """
    render4you.com에서 Cinebench R23 점수 수집 (Multi/Single)
    테이블 구조: thead에 Manufactur, Modell, R20, R23, 2024
    tbody tr에 td 순서: 제조사, 모델명, R20, R23, 2024
    """

    new_page = None # 새 페이지 객체 초기화

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
        
        # 새 탭(페이지) 생성
        new_page = await browser.new_page(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
        )
        # 타임아웃 증가 (15초 -> 45초)
        try:
            await new_page.goto(url, wait_until='networkidle', timeout=45000)
        except Exception as e:
            print(f"        -> (경고) networkidle 실패, load로 재시도: {type(e).__name__}")
            await new_page.goto(url, wait_until='load', timeout=30000)
        await new_page.wait_for_timeout(3000)  # 페이지 로딩 대기 증가
        
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
                search_input = new_page.locator(selector)
                if await search_input.count() > 0:
                    await search_input.first.fill(search_term_num)
                    await new_page.wait_for_timeout(3000)  # 필터링 대기 시간 증가
                    search_attempted = True
                    break
            except:
                continue
        
        if not search_attempted:
            print(f"        -> (정보) 검색 필드를 찾지 못해 전체 테이블 스캔")
        
        # 페이지 재로드 후 HTML 가져오기
        await new_page.wait_for_timeout(2000) # page. -> new_page.
        html = await new_page.content() # page. -> new_page.
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
    finally:
    # 작업 완료 후 새 탭 닫기
        if new_page:
            await new_page.close()

async def scrape_geekbench_v6(browser, cpu_name, conn, part_id):
    """
    browser.geekbench.com에서 Geekbench v6 싱글코어/멀티코어 점수 수집
    /search?q= 형식 사용, Windows 최신 결과 우선
    """
    new_page = None # 새 페이지 객체 초기화
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
        
        # 새 탭(페이지) 생성
        new_page = await browser.new_page(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
        )
        # 타임아웃 증가 (15초 -> 45초)
        try:
            await new_page.goto(search_url, wait_until='networkidle', timeout=45000)
        except Exception as e:
            print(f"        -> (경고) networkidle 실패, load로 재시도: {type(e).__name__}")
            await new_page.goto(search_url, wait_until='load', timeout=30000)
        await new_page.wait_for_timeout(3000)
        
        html = await new_page.content() # page. -> new_page.
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
    finally:
        # 작업 완료 후 새 탭 닫기
        if new_page:
            await new_page.close()

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

def scrape_blender_gpu(page, gpu_name, conn, part_id):
    """
    opendata.blender.org에서 GPU Median Score 수집
    DataTables API 사용: /benchmarks/query/?group_by=device_name&blender_version=4.5.0
    정확한 GPU 모델명 매칭 (예: RTX 5060과 RTX 5060 Ti 구분)
    """
    try:
        if not gpu_name:
            return
        # 공통 라벨/토큰 추출
        common_label, search_token = _normalize_gpu_model(gpu_name)

        # 중복 체크: 이미 데이터가 있으면 수집하지 않음
        check_sql = text("""
            SELECT EXISTS (
                SELECT 1 FROM benchmark_results 
                WHERE part_type = 'GPU'
                AND cpu_model = :model 
                AND source = 'blender_opendata'
                AND test_name = 'Blender' 
                AND test_version = '4.5.0'
                AND scenario = 'Median GPU'
            )
        """)
        exists_result = conn.execute(check_sql, {"model": common_label})
        if exists_result.scalar() == 1:
            print(f"        -> (건너뜀) Blender GPU Median 데이터가 이미 존재합니다.")
            return

        # 사용자 제공 URL 형식 사용
        url = "https://opendata.blender.org/benchmarks/query/"
        params = {
            "group_by": "device_name",
            "blender_version": "4.5.0",
            "response_type": "datatables"
        }
        print(f"      -> Blender GPU Median 검색: {url}")

        response = requests.get(url, params=params, timeout=20)
        if response.status_code != 200:
            print(f"        -> (경고) GPU API 응답 오류: {response.status_code}")
            return

        try:
            data = response.json()
        except:
            print(f"        -> (경고) GPU JSON 파싱 실패")
            return

        if not isinstance(data, dict) or 'rows' not in data:
            print(f"        -> (경고) GPU 잘못된 응답 구조")
            return

        columns = data.get('columns', [])
        median_idx = None
        device_idx = None
        for i, col in enumerate(columns):
            display_name = col.get('display_name', '') if isinstance(col, dict) else str(col)
            if 'Median Score' in display_name or 'median' in display_name.lower():
                median_idx = i
            if 'Device Name' in display_name or 'device_name' in display_name.lower():
                device_idx = i

        if median_idx is None:
            print(f"        -> (경고) GPU Median Score 컬럼을 찾지 못했습니다.")
            return

        rows = data.get('rows', [])
        found = None
        found_device = ''
        
        # 정확한 모델명 매칭을 위한 패턴 생성
        # 예: "RTX 5060" -> "5060"이 포함되지만 "5060 Ti"는 제외
        # 예: "RTX 5060 Ti" -> "5060 Ti"가 포함되어야 함
        
        # 매칭 패턴: common_label의 정확한 형태로 매칭
        # "RTX 5060"을 찾을 때는 "5060"이 포함되지만 "5060 Ti"는 제외
        # "RTX 5060 Ti"를 찾을 때는 "5060 Ti"가 포함되어야 함
        def matches_gpu_model(device_name: str, label: str, token: str) -> bool:
            """GPU 모델명이 정확히 매칭되는지 확인 (5060과 5060 Ti 구분)"""
            if not token:
                return False
                
            dev_upper = device_name.upper()
            label_upper = label.upper()
            
            # common_label이 "RTX 5060 Ti"인 경우
            if 'TI' in label_upper or 'SUPER' in label_upper:
                # 정확히 "5060 Ti" 또는 "5060TI" 형태가 포함되어야 함
                if (f"{token} TI" in dev_upper) or (f"{token}TI" in dev_upper):
                    return True
                # 또는 common_label 전체가 포함되어야 함
                if label_upper.replace(' ', '') in dev_upper.replace(' ', ''):
                    return True
                return False
            else:
                # common_label이 "RTX 5060"인 경우 (Ti 없음)
                # "5060"이 포함되어야 하지만 "5060 Ti"는 제외
                if token in dev_upper:
                    # "5060 Ti"가 포함되어 있으면 제외
                    if (f"{token} TI" in dev_upper) or (f"{token}TI" in dev_upper):
                        return False
                    # "5060"만 포함되어 있으면 매칭
                    return True
                # 또는 common_label 전체가 포함되어야 함
                if label_upper.replace(' ', '') in dev_upper.replace(' ', ''):
                    # "5060 Ti"가 포함되어 있으면 제외
                    if 'TI' in dev_upper and token in dev_upper:
                        # "5060" 다음에 "TI"가 오는지 확인
                        pattern = re.compile(rf"{re.escape(token)}\s*TI", re.IGNORECASE)
                        if pattern.search(dev_upper):
                            return False
                    return True
                return False
        
        for row in rows:
            if not isinstance(row, list):
                continue
            dev = ''
            if device_idx is not None and device_idx < len(row):
                dev = str(row[device_idx])
                if '<a' in dev:
                    dev = re.sub(r'<[^>]+>', '', dev)
                dev = dev.strip()

            # 정확한 모델명 매칭
            if matches_gpu_model(dev, common_label, search_token):
                if median_idx < len(row):
                    try:
                        val = float(row[median_idx])
                        if val > 0:
                            found = val
                            found_device = dev
                            print(f"        -> (디버그) 매칭된 디바이스: {dev}")
                            break
                    except:
                        pass

        if not found:
            print(f"        -> (정보) Blender GPU Median 점수를 찾지 못했습니다. (검색어: {common_label})")
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

        conn.execute(sql_bench, {
            "part_id": part_id,
            "part_type": "GPU",
            "cpu_model": common_label,  # 공통 컬럼 재사용 (모델명 저장)
            "source": "blender_opendata",
            "test_name": "Blender",
            "test_version": "4.5.0",
            "scenario": "Median GPU",
            "metric_name": "Score",
            "value": found,
            "unit": "pts",
            "review_url": f"{url}?{'&'.join([f'{k}={v}' for k, v in params.items()])}"
        })
        print(f"        -> Blender GPU Median: {found} ({found_device})")
    except Exception as e:
        print(f"        -> (경고) Blender GPU Median 수집 중 오류: {type(e).__name__} - {str(e)[:100]}")

def _trimmed_median(scores: list[float], trim_ratio: float = 0.1) -> float:
    """윈저라이즈/트리밍 기반 중앙값. 점수 리스트에서 상/하위 trim_ratio 비율을 잘라낸 후 중앙값 계산."""
    if not scores:
        return 0.0
    scores_sorted = sorted(scores)
    n = len(scores_sorted)
    k = int(n * trim_ratio)
    trimmed = scores_sorted[k:n - k] if n > 2 * k and k > 0 else scores_sorted
    try:
        return float(statistics.median(trimmed))
    except:
        return float(trimmed[len(trimmed)//2]) if trimmed else 0.0

def _parse_scores_for_gpu(html: str, gpu_name: str) -> list[float]:
    """3DMark 페이지 HTML에서 GPU 이름이 포함된 행/블록의 Graphics Score만 추출."""
    soup = BeautifulSoup(html, 'lxml')
    # GPU 식별: 이름의 숫자 토큰 기반
    token_match = re.search(r"(\d{3,5})", gpu_name)
    token = token_match.group(1) if token_match else None
    if not token:
        return []
    
    scores = []
    token_upper = token.upper()
    
    # 방법 1: 테이블 구조에서 Graphics Score 컬럼 찾기
    # 더 넓은 범위의 선택자 사용
    rows = soup.select('table tbody tr, table tr, .result-row, .benchmark-row, [class*="result"], [class*="benchmark"], [class*="score"], tr[class*="row"], div[class*="row"]')
    
    for row in rows:
        row_text = row.get_text(" ", strip=True)
        
        # GPU 모델 토큰이 포함되어 있는지 확인 (대소문자 무시)
        if token_upper not in row_text.upper():
            continue
        
        # 방법 1-1: "Graphics Score" 또는 "GPU Score" 텍스트와 함께 있는 숫자 찾기
        graphics_score_patterns = [
            r"Graphics\s+Score[:\s]*[=]?\s*(\d{4,6})",
            r"GPU\s+Score[:\s]*[=]?\s*(\d{4,6})",
            r"Graphics[:\s]*[=]?\s*(\d{4,6})",
            r"Graphics\s*:\s*(\d{4,6})",
            r"GPU\s*:\s*(\d{4,6})",
        ]
        
        for pattern in graphics_score_patterns:
            match = re.search(pattern, row_text, re.IGNORECASE)
            if match:
                try:
                    val = int(match.group(1))
                    if 1000 <= val <= 200000:  # 유효한 점수 범위
                        scores.append(float(val))
                        break  # 하나 찾으면 다음 행으로
                except:
                    pass
        
        # 방법 1-2: 테이블 셀에서 숫자 찾기 (Graphics 관련 헤더가 있는 컬럼)
        cells = row.select('td, th, [class*="cell"], [class*="column"]')
        if len(cells) >= 2:  # 최소 2개 컬럼이 있어야 함
            # 첫 번째 셀에 GPU 모델명이 있고, 다른 셀에 점수가 있을 수 있음
            for i, cell in enumerate(cells):
                cell_text = cell.get_text(" ", strip=True)
                # GPU 모델명이 포함된 셀 다음의 셀들에서 점수 찾기
                if token_upper in cell_text.upper() and i < len(cells) - 1:
                    # 다음 셀들에서 점수 찾기
                    for j in range(i + 1, min(i + 5, len(cells))):  # 최대 4개 셀 확인
                        score_cell = cells[j].get_text(" ", strip=True)
                        # 4-6자리 숫자만 추출
                        num_match = re.search(r'\b(\d{4,6})\b', score_cell)
                        if num_match:
                            try:
                                val = int(num_match.group(1))
                                if 1000 <= val <= 200000:
                                    scores.append(float(val))
                                    break
                            except:
                                pass
    
    # 방법 2: 전체 텍스트에서 "Graphics Score" 레이블 근처의 숫자 찾기
    if len(scores) < 3:
        text = soup.get_text(" ")
        # "Graphics Score" 또는 "GPU Score" 다음에 오는 숫자 찾기
        graphics_patterns = [
            r"Graphics\s+Score[:\s]*[=]?\s*(\d{4,6})",
            r"GPU\s+Score[:\s]*[=]?\s*(\d{4,6})",
            r"Graphics[:\s]*[=]?\s*(\d{4,6})",
        ]
        
        for pattern in graphics_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                # 매칭된 위치 근처(앞뒤 300자)에 GPU 토큰이 있는지 확인
                start = max(0, match.start() - 300)
                end = min(len(text), match.end() + 300)
                context = text[start:end]
                if token_upper in context.upper():
                    try:
                        val = int(match.group(1))
                        if 1000 <= val <= 200000:
                            scores.append(float(val))
                    except:
                        pass
    
    # 방법 3: GPU 모델명 근처의 모든 4-6자리 숫자를 후보로 추출 (더 관대한 방법)
    if len(scores) < 3:
        text = soup.get_text(" ")
        # GPU 토큰 주변(앞뒤 500자)에서 모든 4-6자리 숫자 찾기
        token_positions = []
        for match in re.finditer(re.escape(token), text, re.IGNORECASE):
            token_positions.append(match.start())
        
        for pos in token_positions:
            start = max(0, pos - 500)
            end = min(len(text), pos + 500)
            context = text[start:end]
            # 컨텍스트에서 4-6자리 숫자 찾기
            nums = re.findall(r'\b(\d{4,6})\b', context)
            for num_str in nums:
                try:
                    val = int(num_str)
                    if 1000 <= val <= 200000:
                        scores.append(float(val))
                except:
                    pass
    
    # 중복 제거 및 정렬
    scores = sorted(list(set(scores)))
    
    # 너무 많은 값이면 상위 100개만 사용
    if len(scores) > 100:
        scores = scores[:100]
    
    return scores

def _insert_bench(conn, part_id, part_type, model_name, source, test_name, scenario, value, unit, url, metric_name="Score"):
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
        "part_type": part_type,
        "cpu_model": model_name,
        "source": source,
        "test_name": test_name,
        "test_version": "",
        "scenario": scenario,
        "metric_name": metric_name,
        "value": value,
        "unit": unit,
        "review_url": url
    })

def _normalize_gpu_model(raw_name: str) -> tuple[str, str]:
    """브랜드/유통사 제거하고 공통 GPU 모델로 정규화. 반환: (common_label, numeric_token)
    예) "GALAX GeForce RTX 5060 DUAL" -> ("RTX 5060", "5060")
    예) "AMD Radeon RX 7800 XT" -> ("RX 7800 XT", "7800")
    """
    name = (raw_name or '').upper()
    # NVIDIA
    m = re.search(r"(RTX|GTX)\s*(\d{3,4,5})\s*(TI|SUPER|XT)?", name)
    if m:
        series, num, suffix = m.group(1), m.group(2), m.group(3) or ''
        series_label = f"{series} {num}{(' ' + suffix) if suffix else ''}".strip()
        return series_label.title(), num
    # AMD
    m = re.search(r"(RX)\s*(\d{3,4,5})\s*(XT|XTX)?", name)
    if m:
        series, num, suffix = m.group(1), m.group(2), m.group(3) or ''
        series_label = f"{series} {num}{(' ' + suffix) if suffix else ''}".strip()
        return series_label, num
    # Fallback: 숫자 토큰만
    token = re.search(r"(\d{3,5})", name)
    t = token.group(1) if token else name.split()[0:2]
    common = f"GPU {t}" if isinstance(t, str) else ' '.join(t)
    return common, (t if isinstance(t, str) else '')

async def scrape_3dmark_generic(browser, gpu_name, conn, part_id, test_name: str, url: str):
    """3DMark 필터를 사용하여 GPU Graphics Score의 Average Score를 수집."""
    new_page = None # 새 페이지 객체 초기화
    try:
        common_label, token = _normalize_gpu_model(gpu_name)
        if not token:
            print(f"        -> (정보) 3DMark {test_name} GPU 모델명을 추출할 수 없습니다.")
            return
        
        print(f"      -> 3DMark {test_name} 검색: {url}")
        
        # 테스트 이름을 3DMark 테스트 코드로 변환
        test_code_mapping = {
            'Fire Strike': 'fs P',
            'Time Spy': 'spy P',
            'Port Royal': 'pr P'
        }
        test_code = test_code_mapping.get(test_name)
        if not test_code:
            print(f"        -> (정보) 3DMark {test_name} 테스트 코드를 찾을 수 없습니다.")
            return
        
        # 먼저 GPU ID를 찾기 위해 API 호출
        gpu_id = None
        try:
            # GPU 이름으로 검색하여 GPU ID 찾기
            search_url = f"https://www.3dmark.com/proxycon/ajax/search/gpuname?term={token}"
            response = requests.get(search_url, timeout=10)
            if response.status_code == 200:
                gpu_data = response.json()
                if isinstance(gpu_data, list) and len(gpu_data) > 0:
                    # common_label이 포함된 GPU 찾기
                    for gpu in gpu_data[:10]:  # 최대 10개 확인
                        gpu_label = gpu.get('label', '')
                        if token.upper() in gpu_label.upper():
                            gpu_id = gpu.get('id')
                            if gpu_id:
                                print(f"        -> (디버그) GPU ID 발견: {gpu_id} ({gpu_label[:50]})")
                                break
        except Exception as e:
            print(f"        -> (정보) GPU ID 검색 실패: {type(e).__name__}")
        
        # 새 탭(페이지) 생성
        new_page = await browser.new_page(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
        )

        # URL 파라미터 직접 구성
        if gpu_id:
            # URL 해시 파라미터 구성
            test_param = quote(test_code)
            search_url_with_params = (
                f"https://www.3dmark.com/search#advanced?"
                f"test={test_param}&"
                f"cpuId=undefined&"
                f"gpuId={gpu_id}&"
                f"gpuCount=&"
                f"gpuType=ALL&"
                f"deviceType=&"
                f"storageModel=ALL&"
                f"modelId=&"
                f"showRamDisks=false&"
                f"memoryChannels=&"
                f"country=&"
                f"scoreType=graphicsScore&"
                f"hofMode=false&"
                f"showInvalidResults=false&"
                f"freeParams=&"
                f"minGpuCoreClock=&"
                f"maxGpuCoreClock=&"
                f"minGpuMemClock=&"
                f"maxGpuMemClock=&"
                f"minCpuClock=&"
                f"maxCpuClock="
            )
            
            # URL로 직접 이동
            await new_page.goto(search_url_with_params, wait_until='load', timeout=90000) # page. -> new_page.
            await new_page.wait_for_timeout(10000)  # AJAX 로딩 대기 # page. -> new_page.
        else:
            # GPU ID를 찾지 못한 경우 기존 방식 사용
            main_url = "https://www.3dmark.com/search"
            await new_page.goto(main_url, wait_until='load', timeout=45000) # page. -> new_page.
            await new_page.wait_for_timeout(8000) # page. -> new_page.
            
            # [수정] 이하 모든 page. 로직을 new_page. 로 변경
            try:
                await new_page.evaluate(f"window.location.hash = '#advanced?test={quote(test_code)}&scoreType=graphicsScore'")
                await new_page.wait_for_timeout(3000)
            except:
                pass
            
            try:
                result_type_select = new_page.locator('#resultTypeId')
                await result_type_select.wait_for(state='visible', timeout=10000)
                await result_type_select.select_option(value=test_code)
                await new_page.wait_for_timeout(2000)
                print(f"        -> (디버그) Benchmark 필터 설정: {test_code}")
            except Exception as e:
                print(f"        -> (정보) Benchmark 필터 설정 실패: {type(e).__name__}")
            
            # Score 필터에서 Graphics Score 선택 (#scoreType)
            try:
                await new_page.wait_for_timeout(2000)  # scoreType이 동적으로 채워지므로 대기
                score_type_select = new_page.locator('#scoreType')
                await score_type_select.wait_for(state='visible', timeout=10000)
                await score_type_select.select_option(value='graphicsScore')
                await new_page.wait_for_timeout(2000)
                print(f"        -> (디버그) Score 필터 설정: graphicsScore")
            except Exception as e:
                print(f"        -> (정보) Score 필터 설정 실패: {type(e).__name__}")
            
            # GPU 필터에서 GPU 모델 검색 및 선택 (#gpuName)
            try:
                gpu_name_input = new_page.locator('#gpuName')
                await gpu_name_input.wait_for(state='visible', timeout=10000)
                await gpu_name_input.fill(token)
                await new_page.wait_for_timeout(3000)  # 자동완성 대기
                
                # 자동완성 리스트에서 GPU 선택 (.gpuid-list li.list-item)
                gpu_list_items = new_page.locator('.gpuid-list li.list-item')
                if await gpu_list_items.count() > 0:
                    for i in range(min(await gpu_list_items.count(), 10)):
                        item = gpu_list_items.nth(i)
                        item_text = await item.text_content()
                        if token.upper() in item_text.upper():
                            await item.click()
                            await new_page.wait_for_timeout(3000)
                            print(f"        -> (디버그) GPU 선택: {item_text[:50]}")
                            break
            except Exception as e:
                print(f"        -> (정보) GPU 필터 설정 실패: {type(e).__name__}")
            
            # 필터 변경 시 자동으로 검색이 실행되므로 결과 대기
            await new_page.wait_for_timeout(5000)
        
        # Average Score 추출 (#medianScore) - 여러 번 시도
        avg_score = None
        for attempt in range(3):  # 최대 3번 시도
            try:
                median_score_element = new_page.locator('#medianScore') # page. -> new_page.
                await median_score_element.wait_for(state='visible', timeout=10000)
                
                median_text = (await median_score_element.text_content()).strip()
                if median_text and median_text != 'N/A' and median_text != '':
                    try:
                        avg_score = float(median_text.replace(',', ''))
                        # GPU 모델명(토큰)과 같은 값이면 제외
                        if avg_score != float(token) and 1000 <= avg_score <= 200000:
                            print(f"        -> (디버그) Average Score 발견: {int(avg_score)}")
                            break
                    except ValueError:
                        pass
            except:
                await new_page.wait_for_timeout(3000)  # 재시도 전 대기
        
        if avg_score:
            # Average Score 저장
            _insert_bench(conn, part_id, "GPU", common_label, "3dmark", test_name, "GPU", avg_score, "pts", url, metric_name="Graphics Score")
            print(f"        -> 3DMark {test_name} Graphics Score Average: {int(avg_score)} [{common_label}]")
            return
        
        # 대체 방법: HTML에서 직접 추출
        html = await new_page.content()
        soup = BeautifulSoup(html, 'lxml')
        
        # #medianScore 요소 찾기
        median_score_elem = soup.select_one('#medianScore')
        if median_score_elem:
            median_text = median_score_elem.get_text(strip=True)
            if median_text and median_text != 'N/A' and median_text != '':
                try:
                    avg_score = float(median_text.replace(',', ''))
                    if avg_score != float(token) and 1000 <= avg_score <= 200000:
                        _insert_bench(conn, part_id, "GPU", common_label, "3dmark", test_name, "GPU", avg_score, "pts", url, metric_name="Graphics Score")
                        print(f"        -> 3DMark {test_name} Graphics Score Average: {int(avg_score)} [{common_label}]")
                        return
                except ValueError:
                    pass
        
        # 텍스트 패턴으로 찾기
        text = soup.get_text(" ")
        avg_score_patterns = [
            r"Average\s+score[:\s]+(\d{4,6})",
            r"Average\s+Score[:\s]+(\d{4,6})",
        ]
        
        for pattern in avg_score_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    val = int(match.group(1))
                    if val != int(token) and 1000 <= val <= 200000:
                        avg_score = float(val)
                        _insert_bench(conn, part_id, "GPU", common_label, "3dmark", test_name, "GPU", avg_score, "pts", url, metric_name="Graphics Score")
                        print(f"        -> 3DMark {test_name} Graphics Score Average: {int(avg_score)} [{common_label}]")
                        return
                except:
                    pass
        
        print(f"        -> (정보) 3DMark {test_name} Average Score를 찾지 못했습니다.")
    except Exception as e:
        print(f"        -> (경고) 3DMark {test_name} 수집 중 오류: {type(e).__name__} - {str(e)[:100]}")
    finally:
        # 작업 완료 후 새 탭 닫기
        if new_page:
            await new_page.close()

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

# (crawler.py 파일의 1238행부터 시작)

async def scrape_category(browser, page, engine, category_name, query, collect_reviews, collect_benchmarks, sql_parts, sql_specs, sql_review, sql_check_review):
    """
    카테고리별 크롤링 함수
    
    Args:
        browser: Playwright 브라우저 객체
        page: Playwright 페이지 객체
        engine: SQLAlchemy 엔진 객체
        category_name: 카테고리 이름 (예: 'CPU')
        query: 검색 쿼리
        collect_reviews: 퀘이사존 리뷰 수집 여부
        collect_benchmarks: 벤치마크 정보 수집 여부
        sql_parts: parts 테이블 INSERT SQL
        sql_specs: part_spec 테이블 INSERT SQL
        sql_review: community_reviews 테이블 INSERT SQL
        sql_check_review: 리뷰 존재 여부 확인 SQL
    """

    # --- [신규 함수: 아이템 처리 로직을 분리 및 비동기화] ---
    async def process_item_async(browser, page, engine, category_name, item_loc, collect_benchmarks, collect_reviews, sql_parts, sql_specs, sql_review, sql_check_review):
        """개별 상품의 정보 추출, DB 저장, 벤치마크/리뷰 수집을 비동기적으로 처리합니다."""
        # DB 트랜잭션은 아이템별로 독립적으로 관리됩니다.
        # 각 아이템은 독립적인 DB 연결을 사용합니다.

        # 4. Locator를 사용하여 각 요소를 추출 (이 과정에서 Playwright가 자동으로 대기함)
        try:
            name_tag_loc = item_loc.locator('p.prod_name > a')
            img_tag_loc = item_loc.locator('div.thumb_image img.lazyload, div.thumb_image img:not([alt*="옵션마크"])').first
            
            name = await name_tag_loc.inner_text(timeout=5000)
            link = await name_tag_loc.get_attribute('href', timeout=5000)
            
            # ✅ 용량별 가격 수집 (RAM, SSD, HDD의 경우)
            price_options = []
            if category_name in ['RAM', 'SSD', 'HDD']:
                # 가격 섹션에서 모든 가격 옵션 가져오기
                price_sect_loc = item_loc.locator('p.price_sect')
                price_link_count = await price_sect_loc.locator('a').count()
                
                for i in range(price_link_count):
                    try:
                        price_link = price_sect_loc.locator('a').nth(i)
                        
                        # 각 가격 링크의 부모 p.price_sect 요소 찾기 (strict mode violation 방지)
                        # JavaScript를 사용하여 부모 요소 찾기
                        try:
                            parent_price_sect = await price_link.evaluate('''(element) => {
                                let parent = element.parentElement;
                                while (parent && (parent.tagName !== 'P' || !parent.classList.contains('price_sect'))) {
                                    parent = parent.parentElement;
                                    if (!parent) break;
                                }
                                return parent;
                            }''')
                        except:
                            parent_price_sect = None
                        
                        # 가격 텍스트 추출 (strong 태그 우선)
                        price_text = None
                        try:
                            price_strong = price_link.locator('strong').first
                            price_text = await price_strong.inner_text(timeout=2000)
                        except:
                            pass
                        
                        if not price_text:
                            # strong 태그가 없으면 전체 텍스트에서 가격 추출
                            option_text = await price_link.inner_text(timeout=2000)
                            price_match = re.search(r'([\d,]+)\s*원', option_text)
                            if price_match:
                                price_text = price_match.group(1)
                        
                        if not price_text:
                            continue
                        
                        # 가격 파싱
                        try:
                            price = int(price_text.strip().replace(',', ''))
                        except ValueError:
                            continue
                        
                        # 가격 링크의 href에서 pcode 추출
                        price_link_href = await price_link.get_attribute('href', timeout=1000) or ''
                        pcode_match = re.search(r'pcode=(\d+)', price_link_href)
                        current_pcode = pcode_match.group(1) if pcode_match else None
                        
                        # 용량 정보 추출 - 여러 방법 시도
                        capacity = None
                        debug_info = []  # 디버깅용 정보 수집
                        
                        # 방법 0: hidden input 필드에서 용량 정보 추출 (최우선)
                        if current_pcode:
                            try:
                                # 상품 아이템 내의 hidden input 필드 찾기 (wishListBundleVal_로 시작하는 id)
                                hidden_input_loc = item_loc.locator('input[id^="wishListBundleVal_"]').first
                                hidden_value = await hidden_input_loc.get_attribute('value', timeout=1000)
                                debug_info.append(f"hidden_input_value: '{hidden_value}'")
                                
                                if hidden_value:
                                    # 형식: "4TB^69869606**2TB^69869573**1TB^69869543//삼성전자 990 EVO Plus M.2 NVMe//69869543"
                                    # 또는: "32GB(16Gx2)^12345**16GB x2^67890//..."
                                    # 각 용량^pcode 쌍을 파싱
                                    # 먼저 "//"로 분리하여 용량 매핑 부분만 추출
                                    parts = hidden_value.split('//')
                                    if parts:
                                        capacity_mapping = parts[0]  # "4TB^69869606**2TB^69869573**1TB^69869543"
                                        # "**"로 분리하여 각 용량^pcode 쌍 확인
                                        capacity_pairs = capacity_mapping.split('**')
                                        for pair in capacity_pairs:
                                            if '^' in pair:
                                                cap, pcode = pair.split('^', 1)
                                                if pcode == current_pcode:
                                                    # 용량 추출 (예: "4TB", "32GB(16Gx2)")
                                                    cap_raw = cap.strip()
                                                    # extract_capacity_from_option으로 정규화 (RAM의 경우 패키지 정보 포함)
                                                    capacity_normalized = extract_capacity_from_option(cap_raw, category_name)
                                                    capacity = capacity_normalized if capacity_normalized else cap_raw
                                                    debug_info.append(f"hidden_input에서 용량 발견: {cap_raw} -> {capacity} (pcode: {pcode})")
                                                    break
                            except Exception as e:
                                debug_info.append(f"방법0(hidden_input)실패: {e}")
                        
                        # capacity가 설정되었으면 다른 방법들은 건너뛰기
                        if not capacity:
                            # 방법 1: 링크의 전체 텍스트에서 추출 (strong 제외한 텍스트)
                            try:
                                # 링크 내부의 모든 텍스트 노드 확인 (strong 제외)
                                all_text = await price_link.evaluate('''(element) => {
                                    let text = '';
                                    for (let node of element.childNodes) {
                                        if (node.nodeType === 3) { // Text node
                                            text += node.textContent.trim() + ' ';
                                        } else if (node.tagName && node.tagName !== 'STRONG') {
                                            const nodeText = node.textContent ? node.textContent.trim() : '';
                                            if (nodeText) text += nodeText + ' ';
                                        }
                                    }
                                    return text.trim();
                                }''')
                                debug_info.append(f"링크내부텍스트(strong제외): '{all_text}'")
                                if all_text:
                                    capacity = extract_capacity_from_option(all_text, category_name)
                            except Exception as e:
                                debug_info.append(f"방법1실패: {e}")
                        
                        # 방법 2: 링크의 전체 inner_text에서 추출
                        if not capacity:
                            try:
                                option_text = await price_link.inner_text(timeout=1000)
                                debug_info.append(f"전체inner_text: '{option_text}'")
                                # 가격 부분 제거하고 용량만 추출
                                option_without_price = re.sub(r'[\d,]+원', '', option_text).strip()
                                if option_without_price:
                                    capacity = extract_capacity_from_option(option_without_price, category_name)
                            except Exception as e:
                                debug_info.append(f"방법2실패: {e}")
                        
                        # 방법 3: 링크의 title 속성 확인
                        if not capacity:
                            try:
                                link_title = await price_link.get_attribute('title', timeout=1000)
                                debug_info.append(f"title속성: '{link_title}'")
                                if link_title:
                                    capacity = extract_capacity_from_option(link_title, category_name)
                            except Exception as e:
                                debug_info.append(f"방법3실패: {e}")
                        
                        # 방법 4: 링크 앞의 텍스트 노드 확인 (형제 요소)
                        if not capacity:
                            try:
                                # 부모 요소에서 링크 앞의 텍스트 확인
                                parent_text = await price_link.evaluate('''(element) => {
                                    const parent = element.parentElement;
                                    if (!parent) return '';
                                    let text = '';
                                    for (let node of parent.childNodes) {
                                        if (node === element) break;
                                        if (node.nodeType === 3) {
                                            text += node.textContent.trim() + ' ';
                                        } else if (node.textContent) {
                                            text += node.textContent.trim() + ' ';
                                        }
                                    }
                                    return text.trim();
                                }''')
                                debug_info.append(f"부모요소앞텍스트: '{parent_text}'")
                                if parent_text:
                                    capacity = extract_capacity_from_option(parent_text, category_name)
                            except Exception as e:
                                debug_info.append(f"방법4실패: {e}")
                        
                        # 방법 4-2: 부모 요소의 전체 텍스트 확인 (가격 섹션 전체)
                        if not capacity:
                            try:
                                # 각 가격 링크의 부모 p.price_sect 요소에서 텍스트 추출
                                if parent_price_sect:
                                    parent_full_text = await price_link.evaluate('''(element) => {
                                        let parent = element.parentElement;
                                        while (parent && (parent.tagName !== 'P' || !parent.classList.contains('price_sect'))) {
                                            parent = parent.parentElement;
                                            if (!parent) break;
                                        }
                                        return parent ? (parent.textContent || parent.innerText || '') : '';
                                    }''')
                                else:
                                    parent_full_text = ''
                                debug_info.append(f"가격섹션전체텍스트: '{parent_full_text[:200]}'")
                                
                                # 가격 텍스트 정규화 (쉼표 제거)
                                price_normalized = price_text.replace(',', '')
                                
                                # 방법 4-2-1: 가격 앞의 텍스트에서 용량 추출
                                if price_text in parent_full_text:
                                    price_index = parent_full_text.find(price_text)
                                    if price_index > 0:
                                        before_price = parent_full_text[:price_index].strip()
                                        capacity = extract_capacity_from_option(before_price, category_name)
                                
                                # 방법 4-2-2: 정규화된 가격으로 검색 (쉼표 없는 버전)
                                if not capacity and price_normalized in parent_full_text:
                                    price_index = parent_full_text.find(price_normalized)
                                    if price_index > 0:
                                        before_price = parent_full_text[:price_index].strip()
                                        capacity = extract_capacity_from_option(before_price, category_name)
                                
                                # 방법 4-2-3: "/" 또는 줄바꿈으로 분리된 각 세그먼트에서 해당 가격 찾기
                                if not capacity:
                                    # 세그먼트 분리 (/, \n, 공백 여러 개 등)
                                    segments = re.split(r'[/\n]+|\s{2,}', parent_full_text)
                                    for segment in segments:
                                        segment = segment.strip()
                                        # 세그먼트에 현재 가격이 포함되어 있는지 확인
                                        if price_text in segment or price_normalized in segment:
                                            # 세그먼트에서 용량 추출
                                            capacity = extract_capacity_from_option(segment, category_name)
                                            if capacity:
                                                break
                                
                                # 방법 4-2-4: 가격 섹션 전체에서 용량 패턴 직접 검색 (예: "8TB 135원/1GB 1,079,080원")
                                if not capacity:
                                    capacity = extract_capacity_from_option(parent_full_text, category_name)
                            except Exception as e:
                                debug_info.append(f"방법4-2실패: {e}")
                        
                        # 방법 4-3: 링크의 이전 형제 요소 확인
                        if not capacity:
                            try:
                                prev_sibling_text = await price_link.evaluate('''(element) => {
                                    let prev = element.previousElementSibling;
                                    while (prev) {
                                        if (prev.textContent && prev.textContent.trim()) {
                                            return prev.textContent.trim();
                                        }
                                        prev = prev.previousElementSibling;
                                    }
                                    return '';
                                }''')
                                debug_info.append(f"이전형제요소: '{prev_sibling_text}'")
                                if prev_sibling_text:
                                    capacity = extract_capacity_from_option(prev_sibling_text, category_name)
                            except Exception as e:
                                debug_info.append(f"방법4-3실패: {e}")
                        
                        # 방법 5: 링크의 data 속성 확인
                        if not capacity:
                            try:
                                data_capacity = await price_link.get_attribute('data-capacity', timeout=500)
                                if not data_capacity:
                                    data_capacity = await price_link.get_attribute('data-option', timeout=500)
                                debug_info.append(f"data속성: '{data_capacity}'")
                                if data_capacity:
                                    capacity = extract_capacity_from_option(data_capacity, category_name)
                            except:
                                pass
                        
                        # 방법 6: 링크의 전체 HTML 구조 확인 (span, em 등 모든 요소)
                        if not capacity:
                            try:
                                full_html = await price_link.evaluate('''(element) => {
                                    return element.outerHTML;
                                }''')
                                debug_info.append(f"전체HTML: '{full_html[:300]}'")
                                # HTML에서 용량 패턴 찾기
                                if full_html:
                                    capacity = extract_capacity_from_option(full_html, category_name)
                            except Exception as e:
                                debug_info.append(f"방법6실패: {e}")
                        
                        # 방법 7: 가격 섹션의 전체 HTML 구조 확인 (모든 형제 요소 포함)
                        if not capacity:
                            try:
                                price_sect_html = await price_link.evaluate('''(element) => {
                                    let parent = element.parentElement;
                                    while (parent && (parent.tagName !== 'P' || !parent.classList.contains('price_sect'))) {
                                        parent = parent.parentElement;
                                        if (!parent) break;
                                    }
                                    return parent ? (parent.innerHTML || parent.outerHTML || '') : '';
                                }''')
                                debug_info.append(f"가격섹션HTML: '{price_sect_html[:300]}'")
                                # HTML에서 용량 패턴 찾기
                                if price_sect_html:
                                    capacity = extract_capacity_from_option(price_sect_html, category_name)
                            except Exception as e:
                                debug_info.append(f"방법7실패: {e}")
                        
                        # 방법 8: 가격 링크의 다음 형제 요소 확인
                        if not capacity:
                            try:
                                next_sibling_text = await price_link.evaluate('''(element) => {
                                    let next = element.nextElementSibling;
                                    while (next) {
                                        if (next.textContent && next.textContent.trim()) {
                                            return next.textContent.trim();
                                        }
                                        next = next.nextElementSibling;
                                    }
                                    return '';
                                }''')
                                debug_info.append(f"다음형제요소: '{next_sibling_text}'")
                                if next_sibling_text:
                                    capacity = extract_capacity_from_option(next_sibling_text, category_name)
                            except Exception as e:
                                debug_info.append(f"방법8실패: {e}")
                        
                        if capacity:
                            price_options.append({
                                'capacity': capacity,
                                'price': price,
                                'option_text': f"{capacity} {price_text}원"
                            })
                            print(f"         -> 옵션 발견: {capacity} - {price:,}원")
                        else:
                            # 디버깅 정보 출력 (처음 몇 개만)
                            if len(price_options) < 5:  # 처음 5개만 상세 로그
                                print(f"         -> (디버그) 용량 추출 실패 - 가격: {price_text}원")
                                for info in debug_info:  # 모든 디버그 정보 출력
                                    print(f"            {info}")
                            else:
                                print(f"         -> (경고) 용량 정보 추출 실패: {price_text}원")
                    except Exception as e:
                        print(f"         -> (경고) 옵션 처리 실패: {e}")
                        continue
                
                # 용량별 가격이 없으면 첫 번째 가격만 사용
                # 단, 용량별 가격 옵션이 하나라도 있으면 용량 없는 기본 상품은 저장하지 않음
                if not price_options:
                    price_tag_loc = item_loc.locator('p.price_sect > a').first.locator('strong').first
                    price_text = await price_tag_loc.inner_text(timeout=5000)
                    if '가격비교예정' not in price_text and '단종' not in price_text and price_text:
                        try:
                            price = int(price_text.strip().replace(',', ''))
                            price_options.append({
                                'capacity': None,
                                'price': price,
                                'option_text': price_text
                            })
                        except ValueError:
                            pass
                else:
                    # 용량별 가격 옵션이 있는 경우, 용량이 없는 옵션은 제거
                    # (용량별 상품이 있는데 기본 상품도 저장하면 중복됨)
                    price_options = [opt for opt in price_options if opt['capacity'] is not None]
                    if not price_options:
                        # 모든 옵션에서 용량을 찾지 못한 경우에만 기본 상품 저장
                        price_tag_loc = item_loc.locator('p.price_sect > a').first.locator('strong').first
                        price_text = await price_tag_loc.inner_text(timeout=5000)
                        if '가격비교예정' not in price_text and '단종' not in price_text and price_text:
                            try:
                                price = int(price_text.strip().replace(',', ''))
                                price_options.append({
                                    'capacity': None,
                                    'price': price,
                                    'option_text': price_text
                                })
                            except ValueError:
                                pass
            else:
                # 다른 카테고리는 첫 번째 가격만 사용
                price_tag_loc = item_loc.locator('p.price_sect > a').first.locator('strong').first
                price_text = await price_tag_loc.inner_text(timeout=5000)
                if '가격비교예정' not in price_text and '단종' not in price_text and price_text:
                    try:
                        price = int(price_text.strip().replace(',', ''))
                        price_options.append({
                            'capacity': None,
                            'price': price,
                            'option_text': price_text
                        })
                    except ValueError:
                        pass
            
            # 가격 정보가 없으면 건너뛰기
            if not price_options:
                return
            
            img_src = await img_tag_loc.get_attribute('data-src', timeout=2000) or \
                        await img_tag_loc.get_attribute('data-original-src', timeout=2000) or \
                        await img_tag_loc.get_attribute('src', timeout=2000)

            if img_src and not img_src.startswith('https:'):
                img_src = 'https:' + img_src
            
            # noimg가 저장되는 것을 방지
            if 'noImg' in (img_src or ''):
                print(f"  - (경고) {name} (이미지 로드 실패, noImg 건너뜀)")
                return
        except Exception as e:
            print(f"  - (오류) 아이템 정보 추출 실패: {e}")
            return

        # 2. 리뷰/별점 추출
        review_count = 0
        star_rating = 0.0
        meta_items_loc = item_loc.locator('.prod_sub_meta .meta_item')
        meta_count = await meta_items_loc.count()
        for j in range(meta_count):
            meta_text = ""
            try:
                meta_text = await meta_items_loc.nth(j).inner_text(timeout=1000)
            except Exception:
                continue
                
            if '상품의견' in meta_text:
                count_tag_loc = meta_items_loc.nth(j).locator('.dd strong')
                if await count_tag_loc.count() > 0:
                    count_text = await count_tag_loc.inner_text(timeout=1000)
                    if (match := re.search(r'[\d,]+', count_text)):
                        review_count = int(match.group().replace(',', ''))
            
            elif '상품리뷰' in meta_text:
                score_tag_loc = meta_items_loc.nth(j).locator('.text__score')
                if await score_tag_loc.count() > 0:
                    try: star_rating = float((await score_tag_loc.inner_text(timeout=1000)).strip())
                    except (ValueError, TypeError): star_rating = 0.0

        # 3. 스펙 추출
        spec_string = ""
        try:
            # '전체 스펙'을 우선 시도
            spec_tag_loc = item_loc.locator('div.spec-box--full .spec_list')
            spec_string = await spec_tag_loc.inner_text(timeout=2000)
        except Exception:
            try:
                # '전체 스펙'이 없으면 '요약 스펙'이라도 가져옴
                spec_tag_loc_fallback = item_loc.locator('div.spec_list').first
                spec_string = await spec_tag_loc_fallback.inner_text(timeout=1000)
            except Exception:
                print(f"  - (경고) {name} (스펙 정보 없음)")
        
        spec_string = spec_string.strip()
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

        print(f"\n   [처리 시작] {name}") # 한 줄 띄우고 시작
        
        # --- 4. 용량별로 상품 저장 (RAM, SSD, HDD의 경우) ---
        # 각 용량별 가격 옵션을 별도 상품으로 저장
        for price_option in price_options:
            capacity = price_option['capacity']
            price = price_option['price']
            
            # 상품명에 용량 정보 추가 (용량이 있는 경우)
            product_name = name
            product_link = link
            if capacity:
                # 상품명에 용량 정보가 없으면 추가
                # RAM의 경우: "32GB (16GB x2)" 형태로 추가
                # SSD/HDD의 경우: "1TB", "2TB", "4TB" 형태로 추가
                if capacity not in product_name:
                    product_name = f"{name} ({capacity})"
                # link에 용량 정보 추가하여 unique하게 만들기 (URL 인코딩)
                encoded_capacity = url_quote(capacity, safe='')
                product_link = f"{link}#capacity={encoded_capacity}"
            
            # 용량 정보를 스펙에 추가
            detailed_specs_with_capacity = detailed_specs.copy()
            if capacity:
                if category_name == 'RAM':
                    # RAM의 경우 capacity에 패키지 정보 포함 (예: "32GB (16GB x2)")
                    detailed_specs_with_capacity['capacity'] = capacity
                    # 패키지 개수 추출
                    package_match = re.search(r'x(\d+)', capacity)
                    if package_match:
                        detailed_specs_with_capacity['ram_count'] = f"{package_match.group(1)}개"
                    # 총 용량 추출
                    total_capacity_match = re.search(r'^(\d+GB)', capacity)
                    if total_capacity_match:
                        detailed_specs_with_capacity['total_capacity'] = total_capacity_match.group(1)
                elif category_name in ['SSD', 'HDD']:
                    # SSD/HDD의 경우 storage_capacity에 용량 정보 저장 (예: "1TB", "2TB", "4TB")
                    detailed_specs_with_capacity['storage_capacity'] = capacity
            
            # --- 4. (신규) 1단계: `parts` 테이블에 공통 정보 저장 ---
            parts_params = {
                "name": product_name, "category": category_name, "price": price, "link": product_link,
                "img_src": img_src, "manufacturer": manufacturer, 
                "review_count": review_count, "star_rating": star_rating,
                "warranty_info": warranty_info
            }
            
            # 각 아이템은 독립적인 DB 연결 사용 (트랜잭션 충돌 방지)
            # 재시도 로직 추가 (DB Lock Timeout 대응)
            max_retries = 5  # 재시도 횟수 증가 (3 -> 5)
            retry_count = 0
            
            while retry_count < max_retries:
                try:
                    # 트랜잭션 격리 수준 설정 (READ COMMITTED로 변경하여 락 대기 시간 감소)
                    with engine.connect() as conn:
                        # 트랜잭션 격리 수준 설정 (선택사항, 필요시 주석 해제)
                        # conn.execute(text("SET SESSION TRANSACTION ISOLATION LEVEL READ COMMITTED"))
                        with conn.begin(): # SQLAlchemy Connection에서 트랜잭션 시작
                            # 기존 상품 확인 (가격 변동 체크) - link로 확인
                            find_existing_sql = text("SELECT id, price FROM parts WHERE link = :link")
                            existing_result = conn.execute(find_existing_sql, {"link": product_link})
                            existing = existing_result.fetchone()
                            
                            part_id = None
                            needs_update = False
                            
                            if existing:
                                # 기존 상품이 존재
                                part_id = existing[0]
                                old_price = existing[1]
                                
                                if old_price != price:
                                    # 가격 변동이 있는 경우만 업데이트
                                    print(f"     -> [{capacity or '기본'}] 가격 변동 감지: {old_price}원 -> {price}원 (업데이트)")
                                    needs_update = True
                                else:
                                    # 가격 변동 없음 - 벤치마크/리뷰만 확인
                                    print(f"     -> [{capacity or '기본'}] 가격 변동 없음 (건너뜀)")
                                    # 벤치마크/리뷰 수집은 계속 진행
                            else:
                                # 신규 상품
                                needs_update = True
                                print(f"     -> [{capacity or '기본'}] 신규 상품 발견: {product_name} ({price:,}원)")
                            
                            # 신규이거나 가격 변동이 있는 경우만 DB 업데이트
                            if needs_update:
                                result = conn.execute(sql_parts, parts_params)
                                if not part_id:  # 신규 상품인 경우
                                    if result.lastrowid:
                                        part_id = result.lastrowid
                                    else:
                                        find_id_sql = text("SELECT id FROM parts WHERE link = :link")
                                        part_id_result = conn.execute(find_id_sql, {"link": product_link})
                                        part_id = part_id_result.scalar_one_or_none()

                            # part_id가 확보된 경우에만 스펙 저장 (트랜잭션 블록 안에서 실행)
                            if part_id:
                                # 스펙 저장 (항상 업데이트 - 스펙이 변경될 수 있으므로)
                                specs_json = json.dumps(detailed_specs_with_capacity, ensure_ascii=False)
                                
                                # 기존 part_spec 확인
                                check_spec_sql = text("SELECT id FROM part_spec WHERE part_id = :part_id")
                                existing_spec = conn.execute(check_spec_sql, {"part_id": part_id}).fetchone()
                                
                                if existing_spec:
                                    # 기존 스펙이 있으면 UPDATE
                                    update_spec_sql = text("""
                                        UPDATE part_spec 
                                        SET specs = :specs, updated_at = CURRENT_TIMESTAMP
                                        WHERE part_id = :part_id
                                    """)
                                    conn.execute(update_spec_sql, {"part_id": part_id, "specs": specs_json})
                                    spec_id = existing_spec[0]
                                    print(f"         -> [{capacity or '기본'}] 스펙 업데이트 완료 (part_id: {part_id} -> spec_id: {spec_id})")
                                else:
                                    # 기존 스펙이 없으면 INSERT
                                    conn.execute(sql_specs, {"part_id": part_id, "specs": specs_json})
                                    
                                    # part_spec.id를 parts.part_spec_id에 연결
                                    get_spec_id_sql = text("SELECT id FROM part_spec WHERE part_id = :part_id")
                                    spec_id_result = conn.execute(get_spec_id_sql, {"part_id": part_id})
                                    spec_id = spec_id_result.scalar_one_or_none()
                                    
                                    if spec_id:
                                        print(f"         -> [{capacity or '기본'}] 스펙 저장 완료 (part_id: {part_id} -> spec_id: {spec_id})")
                                
                                # part_spec.id를 parts.part_spec_id에 연결 (항상 업데이트)
                                if spec_id:
                                    update_parts_sql = text("""
                                        UPDATE parts
                                        SET part_spec_id = :spec_id
                                        WHERE id = :part_id
                                    """)
                                    conn.execute(update_parts_sql, {"spec_id": spec_id, "part_id": part_id})
                                    if needs_update:
                                        print(f"         -> [{capacity or '기본'}] parts 테이블 연결 완료 (part_id: {part_id} -> spec_id: {spec_id})")

                    # 트랜잭션은 with 블록 종료 시 자동 커밋됨 (벤치마크/리뷰 수집 전에 커밋)
                    print(f"     [처리 완료] {product_name} (용량: {capacity or '기본'}, 가격: {price:,}원)")
                    
                    # === 벤치마크/리뷰 수집은 별도 트랜잭션으로 처리 (DB 락 방지) ===
                    if part_id:
                        # 벤치마크 수집 (CPU) - --benchmarks 플래그 선택 시에만 수집
                        if collect_benchmarks and category_name == 'CPU':
                            print(f"         -> [{capacity or '기본'}] CPU 벤치마크 수집 중... (--benchmarks 플래그 활성화)")
                            # 별도 커넥션 사용
                            with engine.connect() as bench_conn:
                                with bench_conn.begin():
                                    await scrape_cinebench_r23(browser, product_name, bench_conn, part_id, category_name)
                                    await asyncio.sleep(0.5)
                                    await scrape_geekbench_v6(browser, product_name, bench_conn, part_id)
                                    await asyncio.sleep(0.5)
                                    scrape_blender_median(None, product_name, bench_conn, part_id)
                                    await asyncio.sleep(0.5)
                        elif category_name == 'CPU':
                            print(f"         -> [{capacity or '기본'}] CPU 벤치마크 수집 건너뜀 (--benchmarks 플래그 미설정)")

                        # GPU 벤치마크 수집 - --benchmarks 플래그 선택 시에만 수집
                        if collect_benchmarks and category_name == '그래픽카드':
                            common_label, token = _normalize_gpu_model(product_name)
                            print(f"         -> [{capacity or '기본'}] GPU 벤치마크 수집 중... ({common_label}, --benchmarks 플래그 활성화)")
                            # 별도 커넥션 사용
                            with engine.connect() as bench_conn:
                                with bench_conn.begin():
                                    scrape_blender_gpu(page, common_label, bench_conn, part_id)
                                    await asyncio.sleep(2)
                                    await scrape_3dmark_generic(browser, common_label, bench_conn, part_id, 'Fire Strike', 'https://www.3dmark.com/search#advanced/fs')
                                    await asyncio.sleep(2)
                                    await scrape_3dmark_generic(browser, common_label, bench_conn, part_id, 'Time Spy', 'https://www.3dmark.com/search#advanced/spy')
                                    await asyncio.sleep(2)
                                    await scrape_3dmark_generic(browser, common_label, bench_conn, part_id, 'Port Royal', 'https://www.3dmark.com/search#advanced/pr')
                                    await asyncio.sleep(2)
                        elif category_name == '그래픽카드':
                            print(f"         -> [{capacity or '기본'}] GPU 벤치마크 수집 건너뜀 (--benchmarks 플래그 미설정)")

                        # 퀘이사존 리뷰 수집 - --reviews 플래그 선택 시에만 수집
                        if collect_reviews:
                            print(f"             -> [{capacity or '기본'}] 퀘이사존 리뷰 수집 중... (--reviews 플래그 활성화)")
                            # 별도 커넥션 사용
                            with engine.connect() as review_conn:
                                with review_conn.begin():
                                    await scrape_quasarzone_reviews(browser, review_conn, sql_review, part_id, product_name, category_name, detailed_specs_with_capacity)
                        else:
                            print(f"             -> [{capacity or '기본'}] 퀘이사존 리뷰 수집 건너뜀 (--reviews 플래그 미설정)")
                    
                    break  # 성공 시 재시도 루프 탈출
                    
                except Exception as e:
                    # DB 연결 및 타임아웃 오류 처리
                    error_msg = str(e).lower()
                    
                    # 재시도 가능한 오류 패턴
                    retryable_errors = [
                        "1205",                    # Lock wait timeout
                        "2013",                    # Lost connection to MySQL server
                        "2006",                    # MySQL server has gone away
                        "lock wait timeout",       # 락 타임아웃
                        "lost connection",         # 연결 끊김
                        "timeout",                 # 일반 타임아웃
                        "connection reset",        # 연결 리셋
                        "broken pipe",             # 파이프 끊김
                    ]
                    
                    is_retryable = any(pattern in error_msg for pattern in retryable_errors)
                    
                    if is_retryable:
                        retry_count += 1
                        if retry_count < max_retries:
                            # 지수 백오프: 2초, 4초, 8초, 16초, 32초 (최대 30초)
                            wait_time = min(2 ** retry_count, 30)
                            error_type = "연결 오류" if "connection" in error_msg or "2013" in error_msg or "2006" in error_msg else "DB 락 타임아웃"
                            print(f"     [{error_type}] {product_name} - {retry_count}/{max_retries}회 재시도 중... ({wait_time}초 대기)")
                            print(f"         상세: {str(e)[:100]}")
                            await asyncio.sleep(wait_time)
                            
                            # 연결 끊김 오류의 경우 연결 풀 정리 시도
                            if "connection" in error_msg or "2013" in error_msg or "2006" in error_msg:
                                try:
                                    engine.dispose()  # 연결 풀 재생성
                                    print(f"         -> 연결 풀 재생성 완료")
                                    await asyncio.sleep(2)  # 추가 대기
                                except:
                                    pass
                            
                            continue
                        else:
                            print(f"     [처리 오류] {product_name} 저장 중 오류 발생 (최대 재시도 횟수 {max_retries}회 초과)")
                            print(f"         상세: {e}")
                            print(f"     [권장 조치]")
                            print(f"       1. 동시 처리 개수 줄이기: MAX_CONCURRENT_ITEMS=3")
                            print(f"       2. MySQL wait_timeout 증가: SET GLOBAL wait_timeout=28800")
                            print(f"       3. MySQL max_connections 증가: SET GLOBAL max_connections=500")
                            break
                    else:
                        # 재시도 불가능한 오류는 즉시 중단
                        print(f"     [처리 오류] {product_name} 저장 중 오류 발생 (재시도 불가): {e}")
                        break

    for page_num in range(1, CRAWL_PAGES + 1): # CRAWL_PAGES 변수 사용하도록 수정
        if 'query=' in query: # 쿨러처럼 복잡한 쿼리 문자열인 경우
            url = f'https://search.danawa.com/dsearch.php?{query}&page={page_num}'
        else: # CPU처럼 단순 키워드인 경우
            url = f'https://search.danawa.com/dsearch.php?query={query}&page={page_num}'

        print(f"--- '{category_name}' 카테고리, {page_num}페이지 목록 수집 ---")
        
        try:
            await page.goto(url, wait_until='load', timeout=20000)
            await page.wait_for_selector('ul.product_list', timeout=10000)

            # [수정] 스크롤 로직 강화 (횟수 5, 대기 1초)
            print("     -> 스크롤 다운 (5회)...")
            for _ in range(5):
                await page.mouse.wheel(0, 1500)
                await page.wait_for_timeout(1000) # 👈 스크롤 후 대기 시간 증가
            
            # [수정] networkidle 대기 시간 증가
            try:
                await page.wait_for_load_state('networkidle', timeout=10000)
            except Exception as e:
                print(f"     -> (경고) networkidle 대기 시간 초과 (무시하고 진행): {type(e).__name__}")

            # --- [핵심 수정] ---
            # BeautifulSoup(page.content()) 대신 Playwright Locator 사용
            
            # 1. 모든 상품 아이템의 'locator'를 가져옵니다.
            product_items_loc = page.locator('li.prod_item[id^="productItem"]')
            
            # 2. 최소 1개의 아이템이 로드될 때까지 기다립니다.
            try:
                await product_items_loc.first.wait_for(timeout=10000)
            except Exception:
                print("     -> (경고) 상품 아이템(li.prod_item)을 기다렸지만 로드되지 않았습니다.")
                
            item_count = await product_items_loc.count()
            if item_count == 0:
                print("--- 현재 페이지에 상품이 없어 다음 카테고리로 넘어갑니다. ---")
                break
            
            print(f"     -> {item_count}개 상품 아이템(locator) 감지. 파싱 시작...")

            # 3. BeautifulSoup 루프 대신 locator 루프 사용 - 제한된 병렬 처리
            # ✅ Semaphore를 사용해 동시 실행 개수 제한 (DB 락 타임아웃 방지)
            semaphore = asyncio.Semaphore(MAX_CONCURRENT_ITEMS)
            
            async def limited_process(item_loc):
                async with semaphore:
                    return await process_item_async(browser, page, engine, category_name, item_loc, collect_benchmarks, collect_reviews, sql_parts, sql_specs, sql_review, sql_check_review)
            
            tasks = []
            for i in range(item_count):
                item_loc = product_items_loc.nth(i)
                tasks.append(limited_process(item_loc))
            
            # 제한된 병렬로 모든 아이템 처리
            await asyncio.gather(*tasks, return_exceptions=True) 

        except Exception as e:
            print(f"--- {page_num}페이지 처리 중 오류 발생: {e}. 다음 페이지로 넘어갑니다. ---")
            continue



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

    # 3. 파워 (시리즈명 추출 강화)
    if category_name == '파워':
        # 파워 제품명 패턴: "제조사 시리즈명 용량 인증등급 기타"
        # 예: "FSP VITA GD 750W 80PLUS골드 ATX 3.1"
        # 예: "CORSAIR RM1000e ETA플래티넘 ATX3.1 화이트"
        # 예: "마이크로닉스 Classic II 풀체인지 800W 80PLUS실버 ATX3.1"
        
        # 제조사 제거 (첫 단어)
        words = part_name.split()
        if len(words) > 1:
            remaining = " ".join(words[1:])
        else:
            remaining = part_name
        
        # 시리즈명 추출 전략: 숫자+문자 조합이나 특수 키워드 찾기
        # 패턴 1: 연속된 대문자+숫자 조합 (RM1000e, GX-1000, A750GL 등)
        series_match = re.search(r'([A-Z]{2,}[\w-]*\d+[\w]*)', remaining, re.I)
        if series_match:
            return series_match.group(1)
        
        # 패턴 2: 특정 시리즈명 (Classic, FOCUS, MegaMax 등)
        series_keywords = [
            'Classic', 'FOCUS', 'MegaMax', 'STARS', 'VITA', 'MEG', 
            'Compact', 'GSK', 'NEW', 'ETA', 'Ai', 'GEMINI'
        ]
        for keyword in series_keywords:
            if keyword in remaining:
                # 키워드 + 다음 단어까지 (예: "Classic II", "FOCUS V4", "NEW FOCUS")
                keyword_idx = remaining.find(keyword)
                after_keyword = remaining[keyword_idx:].split()
                
                # "NEW FOCUS" 같은 2단어 조합 처리
                if keyword == 'NEW' and len(after_keyword) >= 3:
                    return f"{after_keyword[0]} {after_keyword[1]} {after_keyword[2]}"
                elif len(after_keyword) >= 2:
                    return f"{after_keyword[0]} {after_keyword[1]}"
                return after_keyword[0]
        
        # 패턴 3: 일반 시리즈명 (앞 2~3 단어, W/인증등급 제외)
        clean = re.sub(r'\d{3,4}W', '', remaining)  # 용량 제거
        clean = re.sub(r'80PLUS\S*', '', clean)  # 인증등급 제거
        clean = re.sub(r'ATX[\d.]*', '', clean, re.I)  # ATX3.1 제거
        clean = re.sub(r'풀모듈러|세미모듈러|논모듈러', '', clean)  # 모듈러 타입 제거
        clean = ' '.join(clean.split())  # 중복 공백 제거
        
        words = clean.split()
        if len(words) >= 2:
            return f"{words[0]} {words[1]}"
        elif len(words) == 1:
            return words[0]
    
    # 4. 기타 부품 (이름에서 제조사 + 괄호 내용 제외)
    # 예: "MSI MAG A750GL 80PLUS골드..." -> "MAG A750GL"
    
    # 일반적인 불필요 단어 제거
    noise_words = ['파워', '서플라이', '케이스', '쿨러', 'RGB', '정품', '블랙', '화이트']
    
    search_query = part_name
    # 제조사 제거 (첫 단어)
    words = search_query.split()
    if len(words) > 1:
        search_query = " ".join(words[1:])
    
    # 괄호 내용 제거
    search_query = re.sub(r'\([^)]+\)', '', search_query).strip()
    # 용량(W) 제거
    search_query = re.sub(r'\d{3,4}W', '', search_query).strip()
    # 인증 등급 단어 제거 (80PLUS골드, 80PLUS브론즈 등은 유지하되 단독으로 나오면 제거)
    
    # 불필요 단어 제거
    for word in noise_words:
        search_query = search_query.replace(word, '')
    
    search_query = ' '.join(search_query.split())  # 중복 공백 제거
    
    # 너무 길면 앞 2~3 단어만 사용 (단, 제품 시리즈명을 보존)
    words = search_query.split()
    if len(words) > 3:
        # "STARS GEMINI 650W 80PLUS 브론즈" -> "STARS GEMINI" (앞 2단어만)
        search_query = " ".join(words[:2])
        
    return search_query.strip()

# --- (수정) 퀘이사존 리뷰 크롤링 함수 (봇 우회 강화) ---
async def scrape_quasarzone_reviews(browser, conn, sql_review, part_id, part_name, category_name, detailed_specs):
    """
    (봇 우회 강화) ... (중략)
    """
    new_page = None # 새 페이지 객체 초기화
    try:
        search_keyword = get_search_keyword(part_name, category_name, detailed_specs)
        if not search_keyword:
            print(f"        -> (정보) '{part_name}'에 대한 핵심 키워드 추출 불가, 건너뜀.") # 6칸 -> 8칸
            return

        # 단일 검색 실행: 공식기사(칼럼/리뷰) 그룹 제목검색 1회만 수행
        q_url = (
            f"https://quasarzone.com/groupSearches?group_id=columns"
            f"&keyword={quote_plus(search_keyword)}&kind=subject"
        )

        print(f"         -> 퀘이사존 공식기사 검색 (키워드: {search_keyword}): {q_url}") # 6칸 -> 8칸
        try:
            # [수정] 새 탭(페이지) 생성
            new_page = await browser.new_page(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
            )
            
            # Cloud Run 환경 대응: 여러 wait_until 전략 시도
            try:
                await new_page.goto(q_url, wait_until='networkidle', timeout=30000)
            except Exception as e:
                print(f"         -> (경고) networkidle 실패, load로 재시도: {type(e).__name__}")
                await new_page.goto(q_url, wait_until='load', timeout=30000)
        except Exception as e:
            print(f"         -> (오류) 검색 페이지 로딩 실패: {e}") # 6칸 -> 8칸
            return

        # [수정] 이하 모든 page. 로직을 new_page. 로 변경
        await new_page.mouse.wheel(0, 1200)
        await new_page.wait_for_timeout(3000)  # 동적 콘텐츠 로딩 대기 (2초 -> 3초)

        # 쿠팡 광고 섹션을 제외하고 실제 검색 결과만 찾기
        # 퀘이사존 검색 결과는 일반적으로 특정 영역에 표시됨
        # 쿠팡 광고는 coupang 관련 클래스나 링크로 식별 가능
        
        # 먼저 검색 결과 영역을 찾습니다
        # 검색 결과 페이지의 메인 콘텐츠 영역에서만 링크를 찾습니다
        links_selector = 'a[href*="/bbs/"]'  # 모든 게시판 링크

        found_link = None
        try:
            # 1. 페이지에 있는 모든 게시판 링크를 가져옵니다.
            all_links_loc = new_page.locator(links_selector)
            links_count = await all_links_loc.count()
            print(f"         -> 검색 결과 페이지에서 {links_count}개의 게시판 링크 발견")
            
            # 디버깅: 링크가 없으면 페이지 상태 확인
            if links_count == 0:
                try:
                    page_text = await new_page.locator('body').inner_text()
                    if '검색 결과가 없습니다' in page_text or '결과가 없습니다' in page_text:
                        print(f"         -> (정보) 퀘이사존에 '{search_keyword}' 검색 결과가 없습니다.")
                    else:
                        print(f"         -> (경고) 페이지 로딩 문제 가능성 (게시판 링크를 찾을 수 없음)")
                        # 페이지 일부 내용 출력
                        preview = page_text[:200].replace('\n', ' ')
                        print(f"         -> (디버그) 페이지 미리보기: {preview}...")
                except Exception as debug_e:
                    print(f"         -> (디버그 오류) {debug_e}")
            
            # 키워드 정규화: 공백, 특수문자 제거하여 매칭률 높이기
            def normalize_text(text):
                """텍스트를 정규화 (공백, 특수문자 제거, 소문자 변환)"""
                text = text.lower()
                text = re.sub(r'[^\w가-힣]', '', text)  # 특수문자 및 공백 제거
                return text
            
            normalized_keyword = normalize_text(search_keyword)
            print(f"         -> 정규화된 검색 키워드: '{normalized_keyword}'")
            
            # 유효한 링크만 수집 (쿠팡 광고 제외)
            valid_links = []
            for i in range(links_count):
                link_loc = all_links_loc.nth(i)
                href = await link_loc.get_attribute('href')
                
                # 유효한 링크인지 확인 (퀘이사존 공식기사 게시물 링크만)
                # qc_qsz: 퀘이사존 리뷰, qc_bench: 벤치마크
                if not href:
                    continue
                    
                # 쿠팡 광고 제외
                if 'coupang' in href.lower() or 'coupa.ng' in href.lower():
                    continue
                    
                # 퀘이사존 공식 기사 게시판만 포함
                if '/bbs/qc_qsz' in href or '/bbs/qc_bench' in href:
                    try:
                        title = (await link_loc.inner_text() or "").strip()
                        if title:  # 제목이 있는 링크만
                            valid_links.append((href, title))
                    except:
                        pass
            
            print(f"         -> 유효한 퀘이사존 게시물 링크: {len(valid_links)}개")
            
            # 2. 유효한 링크를 순회하며 키워드 매칭 (필터링 제거, 첫 번째 매칭 즉시 선택)
            for href, title in valid_links:
                normalized_title = normalize_text(title)
                
                # 3. 링크의 텍스트(제목)에 키워드가 포함되어 있는지 확인
                if normalized_keyword in normalized_title:
                    print(f"         -> 매칭된 제목 발견: '{title[:60]}'")
                    found_link = href
                    break # 4. 일치하는 첫 번째 리뷰 링크를 찾으면 즉시 중단
            
        except Exception as e:
            print(f"      -> (경고) 링크 목록을 파싱하는 중 오류: {e}")
            import traceback
            traceback.print_exc()
            pass

        if not found_link: # 5. 일치하는 링크를 못 찾았다면
            print(f"      -> (정보) 퀘이사존에서 '{search_keyword}' 관련 리뷰를 찾지 못했습니다.")
            return

        review_url = found_link # 6. 일치하는 링크로 리뷰 수집 시작
        if review_url and not review_url.startswith('https://'):
                review_url = f"https://quasarzone.com{review_url}"

        print(f"         -> [1/1] 리뷰 페이지 이동: {review_url}")
        
        # [수정] Cloud Run 환경을 위한 페이지 로딩 개선
        try:
            await new_page.goto(review_url, wait_until='networkidle', timeout=45000)
        except Exception as e:
            print(f"         -> (경고) networkidle 대기 실패, load로 재시도: {type(e).__name__}")
            await new_page.goto(review_url, wait_until='load', timeout=30000)
        
        # 추가 대기: JavaScript 렌더링 시간 확보
        await new_page.wait_for_timeout(3000)
        
        # [수정] 여러 셀렉터 시도 (퀘이사존 페이지 구조 변경 대응)
        content_element = None
        selectors = [
            '.view-content',           # 기본 셀렉터
            '.article-content',        # 대체 셀렉터 1
            '.content-body',           # 대체 셀렉터 2
            'article .view-body',      # 대체 셀렉터 3
            '.board-read .content',    # 대체 셀렉터 4
            '.board-article-content',  # 대체 셀렉터 5
            '[class*="view-content"]', # 대체 셀렉터 6 (부분 일치)
            '[class*="article-content"]', # 대체 셀렉터 7 (부분 일치)
            'article',                 # 대체 셀렉터 8 (가장 넓은 범위)
        ]
        
        for selector in selectors:
            try:
                element = new_page.locator(selector)
                count = await element.count()
                if count > 0:
                    first = element.first
                    # is_visible 체크 시간 단축 (Cloud Run 대응)
                    try:
                        is_visible = await first.is_visible(timeout=3000)
                        if is_visible:
                            content_element = first
                            print(f"         -> (디버그) 본문 발견: {selector}")
                            break
                    except:
                        # timeout 시에도 요소가 있으면 시도
                        content_element = first
                        print(f"         -> (디버그) 본문 발견 (visibility timeout): {selector}")
                        break
            except Exception as e:
                continue
        
        if content_element is None:
            print("         -> (오류) 리뷰 본문을 찾을 수 없습니다. (모든 셀렉터 시도 실패)")
            # [디버깅] 상세 정보 출력
            try:
                # 페이지 제목 확인
                page_title = await new_page.title()
                print(f"         -> (디버그) 페이지 제목: {page_title}")
                
                # 페이지 URL 확인
                current_url = new_page.url
                print(f"         -> (디버그) 현재 URL: {current_url}")
                
                # 페이지 소스의 일부 확인 (body 태그 존재 여부)
                body_exists = await new_page.locator('body').count()
                print(f"         -> (디버그) body 태그 존재: {body_exists > 0}")
                
                # 주요 클래스 확인
                main_classes = await new_page.locator('[class*="content"], [class*="article"], [class*="view"]').count()
                print(f"         -> (디버그) content/article/view 관련 요소 수: {main_classes}")
                
                # 스크린샷 저장
                await new_page.screenshot(path=f"debug_screenshot_{part_id}.png", full_page=True)
                print(f"         -> (디버그) 스크린샷 저장: debug_screenshot_{part_id}.png")
                
                # HTML 일부 저장 (디버깅용)
                html_content = await new_page.content()
                with open(f"debug_html_{part_id}.html", "w", encoding="utf-8") as f:
                    f.write(html_content[:50000])  # 처음 50KB만 저장
                print(f"         -> (디버그) HTML 일부 저장: debug_html_{part_id}.html")
            except Exception as debug_e:
                print(f"         -> (디버그 오류) {debug_e}")
            return # [수정] finally가 실행되도록 return
                
        raw_text = await content_element.inner_text()
        if len(raw_text) < 100:
                print("         -> (건너뜀) 리뷰 본문이 너무 짧습니다. (100자 미만)")
                return # [수정] finally가 실행되도록 return

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
    finally:
        # [수정] 작업 완료 후 새 탭 닫기
        if new_page:
            await new_page.close()

# --- run_crawler 함수 수정 (CRAWL_PAGES 변수 전달) ---
# 기존 run_crawler 함수를 찾아서 scrape_category 호출 부분을 수정합니다.


async def run_crawler(collect_reviews=False, collect_benchmarks=False):
    """
    크롤러 실행 함수
    
    Args:
        collect_reviews: 퀘이사존 리뷰 수집 여부
        collect_benchmarks: 벤치마크 정보 수집 여부
    """
    # CATEGORIES 딕셔너리를 리스트로 변환
    category_list = list(CATEGORIES.items())

    # 브라우저를 몇 개 카테고리마다 재시작할지 설정합니다. (9개 카테고리 중 3개마다 재시작)
    RESTART_INTERVAL = 3

    # --- SQL 쿼리 정의 ---
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
            warranty_info=VALUES(warranty_info),
            img_src=VALUES(img_src)
    """)
    
    sql_specs = text("""
        INSERT INTO part_spec (part_id, specs)
        VALUES (:part_id, :specs)
        ON DUPLICATE KEY UPDATE
            specs=VALUES(specs)
    """)

    sql_review = text("""
        INSERT INTO community_reviews (
            part_id, part_type, cpu_model, source, review_url, raw_text
        ) VALUES (
            :part_id, :part_type, :cpu_model, :source, :review_url, :raw_text
        )
        ON DUPLICATE KEY UPDATE
            part_id = part_id 
    """)
    
    sql_check_review = text("SELECT EXISTS (SELECT 1 FROM community_reviews WHERE part_id = :part_id)")

    async with async_playwright() as p: # ✅ [수정] async_playwright 사용
        
        # 퀘이사존 세션 획득 로직은 그대로 둡니다.

        for i in range(0, len(category_list), RESTART_INTERVAL):
            # 1. 브라우저 시작 (Cloud Run 환경 최적화)
            browser = await p.chromium.launch(
                headless=HEADLESS_MODE, 
                slow_mo=SLOW_MOTION,
                args=[
                    '--no-sandbox',                    # Cloud Run 필수
                    '--disable-setuid-sandbox',        # Cloud Run 필수
                    '--disable-dev-shm-usage',         # 메모리 부족 방지
                    '--disable-gpu',                   # GPU 비활성화
                    '--disable-software-rasterizer',
                    '--disable-extensions',
                    '--disable-background-networking',
                    '--disable-background-timer-throttling',
                    '--disable-backgrounding-occluded-windows',
                    '--disable-renderer-backgrounding',
                    '--no-first-run',
                    '--no-default-browser-check',
                    '--window-size=1920,1080'          # 화면 크기 명시
                ]
            )
            # 메인 페이지 생성 및 봇 우회 (page는 다나와 목록 유지용)
            page = await browser.new_page() # await 추가
            
            # NOTE: stealth_sync는 동기 함수이므로, 여기서는 User-Agent 설정만 유지합니다.
            await page.set_extra_http_headers({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"})

            print(f"\n--- [재시작] 브라우저 세션 시작 (카테고리 {i+1}부터)")

            # 2. 퀘이사존 세션 획득 (매번 다시 로그인 페이지 방문)
            if collect_reviews:
                try:
                    print("--- (봇 우회) 퀘이사존 메인 리뷰 페이지 1회 방문 (세션 획득) ---")
                    await page.goto("https://quasarzone.com/bbs/qc_qsz", wait_until='load', timeout=30000) # await 추가
                    await page.wait_for_timeout(1000) # await 추가
                    print("--- 퀘이사존 세션 획득 완료 ---")
                except Exception as e:
                    print(f"--- (경고) 퀘이사존 메인 페이지 방문 실패 (무시하고 계속): {e}")

            # 3. 카테고리 묶음 처리 (순차 실행으로 변경)
            batch = category_list[i : i + RESTART_INTERVAL]
            
            for idx_in_batch, (category_name, query) in enumerate(batch, 1):
                global_idx = i + idx_in_batch
                print(f"\n--- [카테고리 {global_idx}/{len(category_list)}] '{category_name}' 처리 시작 ---")
                # 순차 실행
                await scrape_category(browser, page, engine, category_name, query, collect_reviews, collect_benchmarks, sql_parts, sql_specs, sql_review, sql_check_review)

            # 4. 브라우저 종료 (메모리 해제)
            await browser.close() # await 추가
            print("--- 브라우저 세션 종료 (메모리 해제) ---")

    print("\n모든 카테고리 데이터 수집을 완료했습니다.")


if __name__ == "__main__":
    # 1. 명령줄 인수(sys.argv)에서 선택지를 읽어옵니다.
    args = sys.argv
    
    # 2. 플래그 확인 (--reviews, --benchmarks)
    has_reviews_flag = "--reviews" in args
    has_benchmarks_flag = "--benchmarks" in args
    
    # 3. 플래그가 하나도 없으면 항상 대화형 메뉴 표시 (강제)
    if not has_reviews_flag and not has_benchmarks_flag:
        print("\n" + "="*60)
        print("🕷️  다나와 PC 부품 크롤러")
        print("="*60)
        print("\n수집할 데이터를 선택하세요:\n")
        print("  1️⃣  다나와 제품 정보만 (필수) ⚡ 빠름 (5-10분)")
        print("     → 제품 정보 + 상세 스펙")
        print()
        print("  2️⃣  다나와 + 퀘이사존 리뷰 🗨️ (15-25분)")
        print("     → 제품 정보 + 상세 스펙 + 퀘이사존 리뷰")
        print()
        print("  3️⃣  다나와 + 벤치마크 📊 (20-30분)")
        print("     → 제품 정보 + 상세 스펙 + CPU/GPU 벤치마크")
        print()
        print("  4️⃣  모두 수집 🚀 완전 수집 (30-45분)")
        print("     → 제품 정보 + 상세 스펙 + 리뷰 + 벤치마크")
        print()
        print("  0️⃣  취소")
        print()
        
        # stdin을 강제로 flush하고 입력 받기
        import sys
        sys.stdout.flush()
        sys.stderr.flush()
        
        try:
            choice = input("선택 (0-4): ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n\n❌ 입력이 취소되었습니다. 기본 수집(다나와만)을 시작합니다.")
            choice = "1"
        
        if choice == "0":
            print("\n❌ 크롤링이 취소되었습니다.")
            sys.exit(0)
        elif choice == "1":
            collect_reviews = False
            collect_benchmarks = False
            print("\n✅ 다나와 제품 정보만 수집합니다.")
        elif choice == "2":
            collect_reviews = True
            collect_benchmarks = False
            print("\n✅ 다나와 + 퀘이사존 리뷰를 수집합니다.")
        elif choice == "3":
            collect_reviews = False
            collect_benchmarks = True
            print("\n✅ 다나와 + 벤치마크를 수집합니다.")
        elif choice == "4":
            collect_reviews = True
            collect_benchmarks = True
            print("\n✅ 모든 데이터를 수집합니다. (시간이 오래 걸립니다)")
        else:
            print("\n❌ 잘못된 선택입니다. 기본 수집(다나와만)을 시작합니다.")
            collect_reviews = False
            collect_benchmarks = False
    else:
        # 플래그가 있으면 그대로 사용
        collect_reviews = has_reviews_flag
        collect_benchmarks = has_benchmarks_flag
        print("\n💡 플래그로 직접 실행 (대화형 메뉴 건너뜀)")

    print("\n" + "="*60)
    print("크롤러 실행 옵션:")
    print(f" - 다나와 제품 정보: ✅ 항상 수집")
    print(f" - 퀘이사존 리뷰 수집: {'✅ 수집함' if collect_reviews else '❌ 건너뜀'}")
    print(f" - 벤치마크 정보 수집: {'✅ 수집함' if collect_benchmarks else '❌ 건너뜀'}")
    print("="*60 + "\n")

    # 4. AI 견적 추천 시스템 데이터 초기화
    print("\n=== AI 견적 추천 시스템 데이터 초기화 ===")
    try:
        initialize_compatibility_rules(engine)
        initialize_usage_weights(engine)
        print("=== 초기화 완료 ===\n")
    except Exception as e:
        print(f"초기화 중 오류 발생: {e}")
        import traceback
        traceback.print_exc()

    # 5. 읽어온 옵션을 run_crawler 함수로 전달합니다.
    asyncio.run(run_crawler(collect_reviews=collect_reviews, collect_benchmarks=collect_benchmarks)) # ✅ [수정] asyncio.run으로 비동기 시작