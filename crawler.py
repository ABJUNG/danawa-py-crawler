import re
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
from sqlalchemy import create_engine, text
import json
import time
from playwright_stealth import stealth_sync
from urllib.parse import quote_plus, quote
import requests
import statistics

from google.cloud.sql.connector import Connector


# --- 1. 기본 설정 ---
# 이 부분의 값을 변경하여 크롤러 동작을 제어할 수 있습니다.

# 크롤링할 페이지 수 (예: 2로 설정하면 각 카테고리별로 2페이지까지 수집)
CRAWL_PAGES = 2

# 브라우저 창을 띄울지 여부 (True: 숨김, False: 보임 - 디버깅 및 안정성에 유리)
HEADLESS_MODE = True

# 각 동작 사이의 지연 시간 (ms). 봇 탐지를 피하고 안정성을 높임 (50~100 추천)
SLOW_MOTION = 50

# --- 2. DB 설정 ---
DB_USER = 'root'
DB_PASSWORD = 'fullstack'  # 실제 비밀번호로 수정
DB_NAME = 'danawa'

# [신규] Cloud SQL 인스턴스 연결 이름 (1단계에서 확인한 값)
INSTANCE_CONNECTION_NAME = 'pcbuildproject-478007:asia-northeast3:danawa-db-instance'

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

# --- 5. SQLAlchemy 엔진 생성 ---

import os
from google.cloud.sql.connector import Connector, IPTypes

# Cloud Run에서 설정할 환경 변수들
DB_USER = os.environ.get("DB_USER") # 예: "root"
DB_PASSWORD = os.environ.get("DB_PASS") # 예: "1234"
DB_NAME = os.environ.get("DB_NAME") # 예: "danawa"
INSTANCE_CONNECTION_NAME = os.environ.get("INSTANCE_CONNECTION_NAME") # 예: "my-project:region:my-instance"


try:
    connector = Connector()

    # Cloud SQL 연결을 위한 헬퍼 함수
    def getconn():
        # IP 유형을 PRIVATE으로 설정 (VPC 사용 시) 또는 PUBLIC
        conn = connector.connect(
            INSTANCE_CONNECTION_NAME,
            "pymysql",  # 👈 (수정) "mysql+mysqlconnector" -> "pymysql"
            user=DB_USER,
            password=DB_PASSWORD,
            db=DB_NAME,
            ip_type=IPTypes.PRIVATE 
        )
        return conn

    # SQLAlchemy 엔진 생성 (연결 풀 사용)
    engine = create_engine(
        "mysql+pymysql://",  # 👈 (수정) "mysql+mysqlconnector://" -> "mysql+pymysql://"
        creator=getconn,
    )

    with engine.connect() as conn:
        print("Cloud SQL DB 연결 성공")
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
    # (디버깅을 위해 오류 상세 출력)
    import traceback
    traceback.print_exc()
    exit()

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
        elif re.search(r'^[A-Z]\d{3}[A-Z]*$', part): 
            specs['chipset'] = part
        elif 'ATX' in part or 'ITX' in part: 
            specs['form_factor'] = part
        elif 'DDR' in part: 
            specs['memory_spec'] = part
        elif 'VGA 연결' in part or 'PCIe' in part and 'vga_connection' not in specs: 
            specs['vga_connection'] = part
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

    # --- 2. 정규식을 이용한 상세 스펙 추출 (전체 텍스트 기반) ---
    
    # 전원부
    if (m := re.search(r'전원부:\s*([\d\+\s]+페이즈)', full_text)):
        specs['power_phases'] = m.group(1)
        
    # 메모리
    if (m := re.search(r'(\d+)MHz\s*\((PC\d-[\d]+)\)', full_text)):
        specs['memory_clock'] = m.group(1) + 'MHz'
    if (m := re.search(r'메모리 용량:\s*(최대 [\d,]+GB)', full_text)):
        specs['memory_capacity_max'] = m.group(1)
    if 'XMP' in full_text: specs['memory_profile_xmp'] = 'Y'
    if 'EXPO' in full_text: specs['memory_profile_expo'] = 'Y'

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

def scrape_3dmark_generic(page, gpu_name, conn, part_id, test_name: str, url: str):
    """3DMark 필터를 사용하여 GPU Graphics Score의 Average Score를 수집."""
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
            page.goto(search_url_with_params, wait_until='load', timeout=90000)
            page.wait_for_timeout(10000)  # AJAX 로딩 대기
        else:
            # GPU ID를 찾지 못한 경우 기존 방식 사용
            main_url = "https://www.3dmark.com/search"
            page.goto(main_url, wait_until='load', timeout=45000)
            page.wait_for_timeout(8000)
            
            # 고급 검색 모드로 전환
            try:
                # URL 해시로 고급 검색 모드 활성화
                page.evaluate(f"window.location.hash = '#advanced?test={quote(test_code)}&scoreType=graphicsScore'")
                page.wait_for_timeout(3000)
            except:
                pass
            
            # Benchmark 필터 선택 (#resultTypeId)
            try:
                result_type_select = page.locator('#resultTypeId')
                result_type_select.wait_for(state='visible', timeout=10000)
                result_type_select.select_option(value=test_code)
                page.wait_for_timeout(2000)
                print(f"        -> (디버그) Benchmark 필터 설정: {test_code}")
            except Exception as e:
                print(f"        -> (정보) Benchmark 필터 설정 실패: {type(e).__name__}")
            
            # Score 필터에서 Graphics Score 선택 (#scoreType)
            try:
                page.wait_for_timeout(2000)  # scoreType이 동적으로 채워지므로 대기
                score_type_select = page.locator('#scoreType')
                score_type_select.wait_for(state='visible', timeout=10000)
                score_type_select.select_option(value='graphicsScore')
                page.wait_for_timeout(2000)
                print(f"        -> (디버그) Score 필터 설정: graphicsScore")
            except Exception as e:
                print(f"        -> (정보) Score 필터 설정 실패: {type(e).__name__}")
            
            # GPU 필터에서 GPU 모델 검색 및 선택 (#gpuName)
            try:
                gpu_name_input = page.locator('#gpuName')
                gpu_name_input.wait_for(state='visible', timeout=10000)
                gpu_name_input.fill(token)
                page.wait_for_timeout(3000)  # 자동완성 대기
                
                # 자동완성 리스트에서 GPU 선택 (.gpuid-list li.list-item)
                gpu_list_items = page.locator('.gpuid-list li.list-item')
                if gpu_list_items.count() > 0:
                    for i in range(min(gpu_list_items.count(), 10)):
                        item = gpu_list_items.nth(i)
                        item_text = item.text_content()
                        if token.upper() in item_text.upper():
                            item.click()
                            page.wait_for_timeout(3000)
                            print(f"        -> (디버그) GPU 선택: {item_text[:50]}")
                            break
            except Exception as e:
                print(f"        -> (정보) GPU 필터 설정 실패: {type(e).__name__}")
            
            # 필터 변경 시 자동으로 검색이 실행되므로 결과 대기
            page.wait_for_timeout(5000)
        
        # Average Score 추출 (#medianScore) - 여러 번 시도
        avg_score = None
        for attempt in range(3):  # 최대 3번 시도
            try:
                # medianScore 요소가 나타날 때까지 대기
                median_score_element = page.locator('#medianScore')
                median_score_element.wait_for(state='visible', timeout=10000)
                
                median_text = median_score_element.text_content().strip()
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
                page.wait_for_timeout(3000)  # 재시도 전 대기
        
        if avg_score:
            # Average Score 저장
            _insert_bench(conn, part_id, "GPU", common_label, "3dmark", test_name, "GPU", avg_score, "pts", url, metric_name="Graphics Score")
            print(f"        -> 3DMark {test_name} Graphics Score Average: {int(avg_score)} [{common_label}]")
            return
        
        # 대체 방법: HTML에서 직접 추출
        html = page.content()
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
            warranty_info=VALUES(warranty_info),
            img_src=VALUES(img_src)
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
            if 'query=' in query: # 쿨러처럼 복잡한 쿼리 문자열인 경우
                url = f'https://search.danawa.com/dsearch.php?{query}&page={page_num}'
            else: # CPU처럼 단순 키워드인 경우
                url = f'https://search.danawa.com/dsearch.php?query={query}&page={page_num}'

            print(f"--- '{category_name}' 카테고리, {page_num}페이지 목록 수집 ---")
            
            try:
                page.goto(url, wait_until='load', timeout=20000)
                page.wait_for_selector('ul.product_list', timeout=10000)

                # [수정] 스크롤 로직 강화 (횟수 5, 대기 1초)
                print("     -> 스크롤 다운 (5회)...")
                for _ in range(5):
                    page.mouse.wheel(0, 1500)
                    page.wait_for_timeout(1000) # 👈 스크롤 후 대기 시간 증가
                
                # [수정] networkidle 대기 시간 증가
                try:
                    page.wait_for_load_state('networkidle', timeout=10000)
                except Exception as e:
                    print(f"     -> (경고) networkidle 대기 시간 초과 (무시하고 진행): {type(e).__name__}")

                # --- [핵심 수정] ---
                # BeautifulSoup(page.content()) 대신 Playwright Locator 사용
                
                # 1. 모든 상품 아이템의 'locator'를 가져옵니다.
                product_items_loc = page.locator('li.prod_item[id^="productItem"]')
                
                # 2. 최소 1개의 아이템이 로드될 때까지 기다립니다.
                try:
                    product_items_loc.first.wait_for(timeout=10000)
                except Exception:
                    print("     -> (경고) 상품 아이템(li.prod_item)을 기다렸지만 로드되지 않았습니다.")
                    
                item_count = product_items_loc.count()
                if item_count == 0:
                    print("--- 현재 페이지에 상품이 없어 다음 카테고리로 넘어갑니다. ---")
                    break
                
                print(f"     -> {item_count}개 상품 아이템(locator) 감지. 파싱 시작...")

                # 3. BeautifulSoup 루프 대신 locator 루프 사용
                for i in range(item_count):
                    item_loc = product_items_loc.nth(i)
                    
                    # 4. Locator를 사용하여 각 요소를 추출 (이 과정에서 Playwright가 자동으로 대기함)
                    try:
                        name_tag_loc = item_loc.locator('p.prod_name > a')
                        
                        # [수정] 🔽 'a > strong' 대신 'a' 자체를 찾고, 그 안의 첫 번째 strong을 찾도록 변경
                        price_tag_loc = item_loc.locator('p.price_sect > a').first.locator('strong').first
                        
                        # [수정] 🔽 'img' 대신 '옵션마크' 이미지를 제외하는 클래스 선택자 사용
                        # 'img.lazyload' (지연 로딩 이미지) 또는 '옵션마크'가 아닌 첫번째 img
                        img_tag_loc = item_loc.locator('div.thumb_image img.lazyload, div.thumb_image img:not([alt*="옵션마크"])').first
                        
                        name = name_tag_loc.inner_text(timeout=5000)
                        link = name_tag_loc.get_attribute('href', timeout=5000)
                        
                        # [수정] 🔽 .first를 이미 위에서 사용했으므로 여기서는 제거
                        price_text = price_tag_loc.inner_text(timeout=5000)
                        if '가격비교예정' in price_text or not price_text:
                            print(f"  - (정보) {name} (가격 정보 없음, 건너뜀)")
                            continue
                            
                        price = int(price_text.strip().replace(',', ''))
                        
                        # [수정] 🔽 .first를 이미 위에서 사용했으므로 여기서는 제거
                        img_src = img_tag_loc.get_attribute('data-src', timeout=2000) or \
                                    img_tag_loc.get_attribute('data-original-src', timeout=2000) or \
                                    img_tag_loc.get_attribute('src', timeout=2000)

                        if img_src and not img_src.startswith('https:'):
                            img_src = 'https:' + img_src
                        
                        # noimg가 저장되는 것을 방지
                        if 'noImg' in (img_src or ''):
                            print(f"  - (경고) {name} (이미지 로드 실패, noImg 건너뜀)")
                            continue

                    except Exception as e:
                        print(f"  - (오류) 상품 기본 정보(이름/가격/이미지) 추출 실패: {e}")
                        continue

                    # --- [수정] Locator를 사용하여 리뷰/별점 추출 ---
                    review_count = 0
                    star_rating = 0.0
                    meta_items_loc = item_loc.locator('.prod_sub_meta .meta_item')
                    meta_count = meta_items_loc.count()
                    for j in range(meta_count):
                        meta_text = ""
                        try:
                            meta_text = meta_items_loc.nth(j).inner_text(timeout=1000)
                        except Exception:
                            continue
                            
                        if '상품의견' in meta_text:
                            count_tag_loc = meta_items_loc.nth(j).locator('.dd strong')
                            if count_tag_loc.count() > 0:
                                count_text = count_tag_loc.inner_text(timeout=1000)
                                if (match := re.search(r'[\d,]+', count_text)):
                                    review_count = int(match.group().replace(',', ''))
                        
                        elif '상품리뷰' in meta_text:
                            score_tag_loc = meta_items_loc.nth(j).locator('.text__score')
                            if score_tag_loc.count() > 0:
                                try: star_rating = float(score_tag_loc.inner_text(timeout=1000).strip())
                                except (ValueError, TypeError): star_rating = 0.0

                    # --- [수정] Locator를 사용하여 스펙 문자열 추출 ---
                    spec_string = ""
                    try:
                        # '전체 스펙'을 우선 시도
                        spec_tag_loc = item_loc.locator('div.spec-box--full .spec_list')
                        spec_string = spec_tag_loc.inner_text(timeout=2000)
                    except Exception:
                        try:
                            # '전체 스펙'이 없으면 '요약 스펙'이라도 가져옴
                            spec_tag_loc_fallback = item_loc.locator('div.spec_list').first
                            spec_string = spec_tag_loc_fallback.inner_text(timeout=1000)
                        except Exception:
                            print(f"  - (경고) {name} (스펙 정보 없음)")
                    
                    spec_string = spec_string.strip()
                    # --- [수정] 완료 ---
                    
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
                    print(f"\n   [처리 시작] {name}") # 한 줄 띄우고 시작
                    
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
                                print(f"         -> 벤치마크 수집 시도...")
                                # (1) Cinebench R23 (render4you.com)
                                scrape_cinebench_r23(page, name, conn, part_id, category_name)
                                time.sleep(2)
                                # (2) Geekbench v6 (browser.geekbench.com)
                                scrape_geekbench_v6(page, name, conn, part_id)
                                time.sleep(2)
                                # (3) Blender Median Score (opendata.blender.org)
                                scrape_blender_median(page, name, conn, part_id)
                                time.sleep(2)
                                
                                print(f"         -> 벤치마크 수집 완료.")

                            # --- 👇 [신규] GPU 벤치마크 수집 (Blender GPU) ---
                            if collect_benchmarks and category_name == '그래픽카드':
                                print(f"         -> GPU 벤치마크 수집 시도...")
                                # 동일 모델(GPU 공통 라벨)에 대한 벤치가 이미 존재하면 스킵
                                common_label, token = _normalize_gpu_model(name)
                                skip_gpu = False
                                try:
                                    exists_any = conn.execute(text(
                                        "SELECT EXISTS(SELECT 1 FROM benchmark_results WHERE part_type='GPU' AND cpu_model=:m)"
                                    ), {"m": common_label}).scalar()
                                    if exists_any == 1:
                                        print(f"         -> (건너뜀) {common_label} 벤치마크가 이미 존재합니다.")
                                        skip_gpu = True
                                except:
                                    pass
                                if skip_gpu:
                                    # 벤치마크만 건너뛰고, 나머지 저장/커밋은 계속 진행
                                    pass
                                else: # 👈 [수정] skip_gpu가 False일 때만 벤치마크 수집
                                    # (1) Blender GPU Median (opendata.blender.org)
                                    scrape_blender_gpu(page, common_label, conn, part_id)
                                    time.sleep(2)
                                    # (2) 3DMark Fire Strike / Time Spy / Port Royal (랭킹/리더보드 페이지)
                                    # 주의: 실제 랭킹 URL은 제품/테스트별로 다를 수 있어, 기본 엔트리 포인트로 접근 후 텍스트 기반 파싱을 수행
                                    scrape_3dmark_generic(page, common_label, conn, part_id, 'Fire Strike', 'https://www.3dmark.com/search#advanced/fs')
                                    page.goto("about:blank")
                                    time.sleep(2)
                                    scrape_3dmark_generic(page, common_label, conn, part_id, 'Time Spy', 'https://www.3dmark.com/search#advanced/spy')
                                    page.goto("about:blank")
                                    time.sleep(2)
                                    scrape_3dmark_generic(page, common_label, conn, part_id, 'Port Royal', 'https://www.3dmark.com/search#advanced/pr')
                                    time.sleep(2)

                            # 2. DB에 저장 (기존)
                            specs_json = json.dumps(detailed_specs, ensure_ascii=False)
                            
                            specs_params = {
                                "part_id": part_id,
                                "specs": specs_json
                            }
                            conn.execute(sql_specs, specs_params) # part_spec 테이블에 저장
                            
                            # --- 👇 [핵심 수정] part_spec.id를 parts.part_spec_id에 연결 ---
                            # 1. 방금 저장/수정된 part_spec의 id를 part_id를 이용해 다시 조회
                            #    (MySQL은 ON DUPLICATE KEY UPDATE에서 ID를 반환하지 않으므로, 별도 조회가 필요)
                            get_spec_id_sql = text("SELECT id FROM part_spec WHERE part_id = :part_id")
                            spec_id_result = conn.execute(get_spec_id_sql, {"part_id": part_id})
                            spec_id = spec_id_result.scalar_one_or_none()
                            
                            # 2. 조회된 spec_id를 parts 테이블에 업데이트
                            if spec_id:
                                update_parts_sql = text("""
                                    UPDATE parts
                                    SET part_spec_id = :spec_id
                                    WHERE id = :part_id
                                """)
                                conn.execute(update_parts_sql, {"spec_id": spec_id, "part_id": part_id})
                                print(f"         -> parts 테이블 연결 완료 (part_id: {part_id} -> spec_id: {spec_id})") # 로그 추가
                            else:
                                print(f"      [경고] part_id {part_id}에 해당하는 spec_id를 찾지 못해 parts.part_spec_id를 업데이트할 수 없습니다.")
                            # --- [수정 완료] ---


                        # --- (수정) 3단계: 퀘이사존 리뷰 수집 (선택적) ---
                        if collect_reviews and part_id: # part_id를 성공적으로 가져왔다면
                            # 퀘이사존 리뷰가 DB에 이미 저장되어 있는지 확인
                            review_exists_result = conn.execute(sql_check_review, {"part_id": part_id})
                            review_exists = review_exists_result.scalar() == 1 # (True 또는 False)

                            if not review_exists:
                                print(f"         -> 퀘이사존 리뷰 없음, 수집 시도...") # 4칸 -> 6칸
                                # (신규) category_name과 detailed_specs를 인자로 추가 전달
                                scrape_quasarzone_reviews(page, conn, sql_review, part_id, name, category_name, detailed_specs)
                            # else:
                                # (선택적) 이미 리뷰가 있다면 건너뛰었다고 로그 표시
                                # print(f"     -> (건너뜀) 이미 퀘이사존 리뷰가 수집된 상품입니다.")

                        trans.commit() # 트랜잭션 완료
                        # --- 👇 [수정 3] "완료" 로그 수정 및 들여쓰기 추가 ---
                        print(f"     [처리 완료] {name} (댓글: {review_count}) 저장 성공.")
                        
                    except Exception as e:
                        trans.rollback() # 오류 발생 시 롤백

                        # --- 👇 [수정 4] "오류" 로그 수정 및 들여쓰기 추가 ---
                        print(f"     [처리 오류] {name} 저장 중 오류 발생: {e}") 

                    # # --- 👇 [필수] 상품 1개만 테스트하기 위해 break 추가 ---
                    #     print("\n--- [테스트] 상품 1개 처리 완료, 크롤러를 중단합니다. ---")
                    #     break
                    #     # --- 👆 [필수] ---

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