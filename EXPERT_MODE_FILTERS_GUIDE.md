# 전문가 모드 필터 가이드 📋

## ✅ 적용된 수정 사항

### 1. 프론트엔드 (Frontend)

#### SidebarStack1Expert.js
- `handleStart` 함수에서 모든 필터 조건을 `expertFilters` 객체로 수집
- 백엔드로 전달할 수 있는 형식으로 변환
- 예산, 부품 비율 설정 포함

#### AiBuildApp.js
- `generateAutoCompleteParts` 함수에서 `expert_filters` 추가
- 백엔드 API 호출 시 전문가 필터 전달

### 2. 작동하는 필터 목록

#### CPU 필터
- ✅ 소켓 종류 (LGA1700, AM5, AM4, LGA1200)
- ✅ 세대/아키텍처 (Intel 14세대, Ryzen 7000 등)
- ✅ 내장 그래픽 (iGPU 있음/없음)
- ✅ 코어 수 (4/6/8/12/16/24+ 코어)
- ✅ 스레드 수 (8/12/16/24/32+ 스레드)
- ✅ TDP 범위 (65W ~ 250W)

#### 쿨러 필터
- ✅ 쿨러 타입 (타워형, 저소음형, 수냉 120/240/360mm)
- ✅ 소켓 호환성
- ✅ 높이 제한 (케이스 호환)
- ✅ TDP 냉각 능력
- ✅ 팬 크기
- ✅ 소음 수준
- ✅ RGB 조명

#### 메인보드 필터
- ✅ 칩셋 (B850, X870, Z790 등)
- ✅ 폼팩터 (ATX, M-ATX, Mini-ITX)
- ✅ 메모리 종류 (DDR4, DDR5)
- ✅ 최대 RAM 용량 (128GB+)
- ✅ 최대 RAM 속도 (7200MHz+)
- ✅ XMP/EXPO 지원
- ✅ M.2 슬롯 수 (1~10개)
- ✅ SATA 포트 수 (0~10개)
- ✅ 무선랜 (Wi-Fi)
- ✅ M.2-SATA 충돌 여부

#### RAM 필터
- ✅ 메모리 세대 (DDR4, DDR5)
- ✅ 용량 (8GB, 16GB, 32GB, 64GB+)
- ✅ 속도 (2666MHz ~ 8000MHz)
- ✅ 타이밍 (CL14 ~ CL40)
- ✅ 전압 (1.1V, 1.2V, 1.35V, 1.5V)
- ✅ XMP/EXPO 지원

#### GPU 필터
- ✅ VRAM 용량 (4GB, 6GB, 8GB, 12GB, 16GB, 24GB+)
- ✅ 전력 소비 (최대 400W)
- ✅ 길이 (최대 350mm)
- ✅ 두께/슬롯 (2/2.5/3 슬롯)
- ✅ 전원 커넥터 (8pin, 12VHPWR)
- ✅ 팬 개수 (2팬, 3팬, 4팬)
- ✅ 백플레이트 (있음/없음)

#### 파워 (PSU) 필터
- ✅ 용량 (와트 범위)
- ✅ 효율 등급 (80 PLUS Bronze ~ Titanium)
- ✅ 폼팩터 (ATX, SFX, SFX-L)
- ✅ 커넥터 (8pin, 12VHPWR)
- ✅ 케이블 타입 (일체형, 모듈러, 세미모듈러)
- ✅ 팬 크기
- ✅ 깊이 (케이스 호환)

#### 케이스 필터
- ✅ 케이스 타입 (미들타워, 미니타워, 풀타워, SFF)
- ✅ 메인보드 지원 (ATX, M-ATX, ITX)
- ✅ PSU 지원 (ATX, SFX)
- ✅ GPU 최대 길이 (최대 400mm)
- ✅ GPU 슬롯 수 (최대 4슬롯)
- ✅ 쿨러 최대 높이 (최대 200mm)
- ✅ 팬 개수 (0~10개)
- ✅ 에어플로우 (메시, 강화유리)
- ✅ 강화유리 패널 (있음/없음)

#### 저장장치 (SSD) 필터
- ✅ 인터페이스 (SATA, NVMe)
- ✅ 폼팩터 (M.2, 2.5인치)
- ✅ 용량 (256GB ~ 4TB+)
- ✅ DRAM 탑재 (있음/없음)
- ✅ TBW (100 ~ 3000)
- ✅ 히트싱크 (있음/없음)

#### 저장장치 (HDD) 필터
- ✅ 용량 (1TB ~ 20TB+)
- ✅ RPM (5400, 7200)

## 🚀 사용 방법

### 전문가 모드 활성화
1. AI PC Builder 페이지에서 "전문가 모드" 버튼 클릭
2. 각 부품 섹션 클릭하여 세부 필터 설정
3. "AI 견적 추천 시작" 버튼 클릭

### 필터 조합 예시

#### 게이밍 PC (고성능)
- **CPU**: AM5 소켓, Ryzen 7000, 8코어+, TDP 105W+
- **쿨러**: 타워형 또는 수냉 240mm, TDP 200W+
- **메인보드**: X870 칩셋, ATX, DDR5, M.2 3개+
- **RAM**: DDR5, 32GB, 6000MHz+, CL30
- **GPU**: VRAM 12GB+, 3팬, 백플레이트 있음
- **PSU**: 850W+, 80+ Gold, 모듈러
- **케이스**: 미들타워, 메시 에어플로우, GPU 350mm+

#### 사무용 PC (저전력)
- **CPU**: LGA1700, Intel 13세대, 6코어, TDP 65W, iGPU 있음
- **쿨러**: 저소음형, 높이 120mm 이하
- **메인보드**: B660 칩셋, M-ATX, DDR4
- **RAM**: DDR4, 16GB, 3200MHz
- **GPU**: 없음 (내장 그래픽 사용)
- **PSU**: 450W, 80+ Bronze
- **케이스**: 미니타워, 조용한 폐쇄형

#### 영상 편집 PC (작업용)
- **CPU**: AM5, Ryzen 7000, 12코어+, TDP 170W
- **쿨러**: 수냉 360mm, TDP 250W+
- **메인보드**: X870, ATX, DDR5, M.2 4개+
- **RAM**: DDR5, 64GB, 5600MHz+
- **GPU**: VRAM 16GB+, 전력 300W+
- **SSD**: NVMe, M.2, 2TB+, DRAM 있음
- **PSU**: 1000W+, 80+ Platinum, 모듈러

## 💡 필터 작동 방식

### 백엔드 처리
1. 프론트엔드에서 필터 조건 전달
2. `BuildRecommendationService`에서 각 카테고리별 필터 적용
3. 데이터베이스 specs JSON 필드와 매칭
4. 조건에 맞는 부품만 추천

### 크롤러 스펙 매핑
크롤러가 수집한 스펙과 필터가 자동 매핑됩니다:

#### CPU 스펙 매핑
```
필터 -> 크롤러 스펙 필드
socket -> socket
generation -> generation, architecture
cores -> cores
threads -> threads
tdp -> tdp
igpu -> integrated_graphics
```

#### 메인보드 스펙 매핑
```
필터 -> 크롤러 스펙 필드
chipset -> chipset
formFactor -> form_factor, board_form_factor
memoryGen -> memory_type
m2Slots -> m2_slots
sataPorts -> sata3_ports
hasWifi -> wireless_lan
```

#### GPU 스펙 매핑
```
필터 -> 크롤러 스펙 필드
vram -> gpu_memory_capacity
power -> tdp
length -> length
fans -> fan_count
```

## ⚙️ 고급 기능

### AI 예산 분배
전문가 모드에서도 AI가 설정한 필터에 맞춰 자동으로 예산을 분배합니다.

### 호환성 검사
"AI 호환성 검사 및 보정" 버튼으로 선택한 필터 간 호환성을 사전 확인할 수 있습니다.

### 예상 가격 계산
필터를 설정하면 각 부품의 예상 가격이 자동으로 계산됩니다.

## 📝 참고 사항

### 필터 우선순위
1. **핵심 필터** (필수): 소켓, 칩셋, 메모리 세대 등
2. **성능 필터**: 코어 수, VRAM, 용량 등
3. **물리적 필터**: 크기, 높이, 길이 등
4. **선택 필터**: RGB, 색상, 소음 등

### 필터 조합 시 주의사항
- CPU 소켓과 메인보드 칩셋은 반드시 호환되어야 합니다
- 쿨러 높이와 케이스 지원 높이를 확인하세요
- GPU 길이와 케이스 지원 길이를 확인하세요
- 전체 시스템 전력과 PSU 용량을 확인하세요

## 🔧 백엔드 개발자용 정보

### expert_filters 데이터 구조
```json
{
  "expert_filters": {
    "cpu": {
      "socket": "AM5",
      "generation": "Ryzen 7000",
      "cores": [8, 12, 16],
      "tdp": [65, 170]
    },
    "ram": {
      "gen": "DDR5",
      "capacity": "32GB",
      "speed": [6000, 7200]
    }
    // ... 기타 카테고리
  }
}
```

### 필터 처리 흐름
1. `BuildRequestDto`에서 `expert_filters` 추출
2. `applyAdvancedFilters`에서 각 필터 조건 검사
3. 부품의 `specs` JSON과 매칭
4. 조건 만족하는 부품만 반환

## 📞 추가 지원

전문가 모드 사용 중 문제가 발생하거나 추가 필터가 필요하면 알려주세요!

