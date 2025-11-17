import React, { useState, useRef } from 'react';

// 전문가 모드 컴포넌트
function SidebarStack1Expert({
    onNext,
    currentBudget,
    setCurrentBudget,
    componentRatios,
    setComponentRatios,
    lockedComponents,
    toggleLock,
    handleRatioChange,
    setAIAutoRatio,
    totalRatio,
}) {
    // 세부 확장 상태
    const [expandedSections, setExpandedSections] = useState({});
    const [expandedDetails, setExpandedDetails] = useState({});

    // 예산 범위 상태 (최소/최대)
    const [budgetMin, setBudgetMin] = useState(1000000);
    const [budgetMax, setBudgetMax] = useState(5000000);

    // 호환성 검사 결과 모달 상태
    const [compatibilityModal, setCompatibilityModal] = useState({ show: false, results: null });

    // CPU 필터 (핵심: 라디오, 부가: 체크박스)
    const [cpuSocket, setCpuSocket] = useState('');
    const [cpuGeneration, setCpuGeneration] = useState('');
    const [cpuIgpu, setCpuIgpu] = useState('any');
    const [cpuCores, setCpuCores] = useState([]);
    const [cpuThreads, setCpuThreads] = useState([]);
    const [cpuTdp, setCpuTdp] = useState([65, 250]);

    // 쿨러 필터 (핵심: 라디오)
    const [coolerType, setCoolerType] = useState('');
    const [coolerSocket, setCoolerSocket] = useState([]);
    const [coolerHeight, setCoolerHeight] = useState(200);
    const [coolerTdp, setCoolerTdp] = useState([65, 250]); // 🆕 쿨러 TDP 냉각 능력
    const [coolerFanSize, setCoolerFanSize] = useState([]);
    const [coolerNoise, setCoolerNoise] = useState([0, 50]);
    const [coolerRgb, setCoolerRgb] = useState('any');

    // 메인보드 필터
    const [chipset, setChipset] = useState([]);
    const [formFactor, setFormFactor] = useState([]);
    const [memoryGen, setMemoryGen] = useState([]);
    const [ramMaxCapacity, setRamMaxCapacity] = useState(128); // 🆕 메인보드 최대 RAM 용량
    const [maxRamSpeed, setMaxRamSpeed] = useState(7200); // 🆕 메인보드 최대 RAM 속도
    const [xmpSupport, setXmpSupport] = useState('any'); // 🆕 XMP/EXPO 지원
    const [m2Slots, setM2Slots] = useState([1, 10]);
    const [sataPorts, setSataPorts] = useState([0, 10]);
    const [m2SataConflict, setM2SataConflict] = useState('any'); // 🆕 M.2 장착 시 SATA 충돌
    const [hasWifi, setHasWifi] = useState('any');

    // RAM 필터 (핵심: 라디오)
    const [ramGen, setRamGen] = useState('');
    const [ramCapacity, setRamCapacity] = useState('');
    const [ramSpeed, setRamSpeed] = useState([]);
    const [ramTiming, setRamTiming] = useState([]);
    const [ramVoltage, setRamVoltage] = useState([]);
    const [ramXmp, setRamXmp] = useState('any');

    // GPU 필터 (핵심: 라디오)
    const [gpuVram, setGpuVram] = useState('');
    const [gpuPower, setGpuPower] = useState(400);
    const [gpuLength, setGpuLength] = useState(350);
    const [gpuSlots, setGpuSlots] = useState(2.5); // 🆕 GPU 두께 (2/2.5/3 슬롯)
    const [gpuConnector, setGpuConnector] = useState(''); // 🆕 GPU 전원 커넥터 (8pin, 12VHPWR 등)
    const [gpuFans, setGpuFans] = useState([]);
    const [gpuBackplate, setGpuBackplate] = useState('any');

    // PSU 필터
    const [psuWattage, setPsuWattage] = useState([]);
    const [psuEfficiency, setPsuEfficiency] = useState([]);
    const [psuFormFactor, setPsuFormFactor] = useState(''); // 🆕 PSU 크기 (ATX/SFX/SFX-L)
    const [psuConnectors, setPsuConnectors] = useState([]); // 🆕 PSU 커넥터 (8pin, 12VHPWR 등)
    const [psuCableType, setPsuCableType] = useState([]);
    const [psuFanSize, setPsuFanSize] = useState([]);
    const [psuDepth, setPsuDepth] = useState([100, 200]);

    // 케이스 필터
    const [caseType, setCaseType] = useState([]);
    const [caseBoardSupport, setCaseBoardSupport] = useState([]);
    const [casePsuSupport, setCasePsuSupport] = useState([]); // 🆕 케이스가 지원하는 PSU 크기
    const [caseGpuLength, setCaseGpuLength] = useState(400);
    const [caseGpuSlots, setCaseGpuSlots] = useState(4); // 🆕 케이스 최대 GPU 슬롯 수
    const [caseCoolerHeight, setCaseCoolerHeight] = useState(200);
    const [caseFanCount, setCaseFanCount] = useState([0, 10]);
    const [caseAirflow, setCaseAirflow] = useState([]);
    const [caseGlass, setCaseGlass] = useState('any');

    // 저장장치 필터
    const [ssdInterface, setSsdInterface] = useState([]);
    const [ssdFormFactor, setSsdFormFactor] = useState([]);
    const [ssdCapacity, setSsdCapacity] = useState([]);
    const [ssdDram, setSsdDram] = useState('any');
    const [ssdTbw, setSsdTbw] = useState([100, 3000]);
    const [ssdHeatsink, setSsdHeatsink] = useState('any');
    const [hddCapacity, setHddCapacity] = useState([]);
    const [hddRpm, setHddRpm] = useState([]);

    // 환경 옵션
    const [caseEnvironment, setCaseEnvironment] = useState('balanced');
    const [rgbPreference, setRgbPreference] = useState('any');

    const toggleSection = (section) => {
        setExpandedSections((prev) => ({
            ...prev,
            [section]: !prev[section],
        }));
    };

    const toggleDetails = (section) => {
        setExpandedDetails((prev) => ({
            ...prev,
            [section]: !prev[section],
        }));
    };

    // AI가 필터 조건을 기반으로 예상 가격 계산 (더미 로직 - 추후 백엔드 연동)
    const calculateEstimatedPrices = () => {
        // 각 부품의 필터 조건을 기반으로 예상 가격 계산
        let estimated = {
            cpu: 0,
            cooler: 0,
            mainboard: 0,
            ram: 0,
            gpu: 0,
            psu: 0,
            case: 0,
            storage: 0,
            etc: 0,
        };

        // CPU 예상 가격
        if (cpuSocket || cpuGeneration) {
            let basePrice = 200000;
            if (cpuGeneration === 'Intel 14세대' || cpuGeneration === 'Ryzen 7000') basePrice = 450000;
            else if (cpuGeneration === 'Intel 13세대' || cpuGeneration === 'Ryzen 5000') basePrice = 300000;
            if (cpuCores.includes('12코어') || cpuCores.includes('16코어')) basePrice += 200000;
            if (cpuSocket === 'AM5' || cpuSocket === 'LGA1700') basePrice += 50000;
            estimated.cpu = basePrice;
        }

        // 쿨러 예상 가격
        if (coolerType) {
            if (coolerType === '수냉 360mm') estimated.cooler = 200000;
            else if (coolerType === '수냉 240mm') estimated.cooler = 150000;
            else if (coolerType === '수냉 120mm') estimated.cooler = 100000;
            else if (coolerType === '타워형') estimated.cooler = 50000;
            else if (coolerType === '저소음형') estimated.cooler = 40000;
        }

        // 메인보드 예상 가격
        if (chipset.length > 0 || formFactor.length > 0) {
            let basePrice = 150000;
            if (chipset.includes('Z790') || chipset.includes('X670E')) basePrice = 300000;
            if (memoryGen.includes('DDR5')) basePrice += 50000;
            estimated.mainboard = basePrice;
        }

        // RAM 예상 가격
        if (ramGen || ramCapacity) {
            let basePrice = 50000;
            if (ramCapacity === '128GB+') basePrice = 600000;
            else if (ramCapacity === '64GB') basePrice = 300000;
            else if (ramCapacity === '32GB') basePrice = 150000;
            else if (ramCapacity === '16GB') basePrice = 80000;
            else if (ramCapacity === '8GB') basePrice = 40000;
            if (ramGen === 'DDR5') basePrice += 50000;
            estimated.ram = basePrice;
        }

        // GPU 예상 가격
        if (gpuVram) {
            if (gpuVram === '24GB+') estimated.gpu = 2000000;
            else if (gpuVram === '16GB') estimated.gpu = 1200000;
            else if (gpuVram === '12GB') estimated.gpu = 800000;
            else if (gpuVram === '8GB') estimated.gpu = 500000;
            else if (gpuVram === '6GB') estimated.gpu = 350000;
            else if (gpuVram === '4GB') estimated.gpu = 250000;
        }

        // PSU 예상 가격
        if (psuWattage.length > 0 || psuEfficiency.length > 0) {
            let basePrice = 80000;
            if (psuWattage.includes('1000W') || psuWattage.includes('1200W+')) basePrice = 200000;
            if (psuEfficiency.includes('Platinum') || psuEfficiency.includes('Titanium')) basePrice += 50000;
            estimated.psu = basePrice;
        }

        // 케이스 예상 가격
        if (caseType.length > 0) {
            if (caseType.includes('풀타워')) estimated.case = 200000;
            else if (caseType.includes('미들타워')) estimated.case = 100000;
            else estimated.case = 80000;
        }

        // 저장장치 예상 가격
        if (ssdCapacity.length > 0) {
            if (ssdCapacity.includes('4TB+')) estimated.storage = 500000;
            else if (ssdCapacity.includes('2TB')) estimated.storage = 250000;
            else if (ssdCapacity.includes('1TB')) estimated.storage = 120000;
            else estimated.storage = 60000;
        }

        return estimated;
    };

    // AI 호환성 검사 함수
    const checkCompatibility = () => {
        const results = {
            success: [],
            warnings: [],
            errors: [],
            suggestions: [],
        };

        // 1. CPU 소켓 ↔ 쿨러 소켓 호환성
        if (cpuSocket && coolerSocket.length > 0) {
            if (coolerSocket.includes(cpuSocket)) {
                results.success.push(`CPU (${cpuSocket}) ↔ 쿨러 소켓 호환`);
            } else {
                results.errors.push(`CPU 소켓 (${cpuSocket})과 쿨러 소켓이 불일치합니다`);
                results.suggestions.push(`쿨러 소켓 호환에서 "${cpuSocket}"를 선택하세요`);
            }
        }

        // 2. 메인보드 ↔ RAM 세대 호환성
        if (memoryGen.length > 0 && ramGen) {
            if (memoryGen.includes(ramGen)) {
                results.success.push(`메인보드 ↔ RAM ${ramGen} 호환`);
            } else {
                results.errors.push(`메인보드가 ${ramGen}을 지원하지 않습니다`);
                results.suggestions.push(`메인보드 메모리 세대에서 "${ramGen}"를 선택하세요`);
            }
        }

        // 3. GPU 길이 ↔ 케이스 지원 길이
        if (gpuLength && caseGpuLength) {
            if (gpuLength <= caseGpuLength) {
                results.success.push(`GPU 길이 (${gpuLength}mm) ↔ 케이스 지원 (${caseGpuLength}mm)`);
            } else {
                results.errors.push(`GPU 최대 길이 ${gpuLength}mm가 케이스 지원 ${caseGpuLength}mm를 초과합니다`);
                results.suggestions.push(`케이스 GPU 최대 길이를 ${gpuLength}mm 이상으로 조정하세요`);
            }
        }

        // 4. 쿨러 높이 ↔ 케이스 높이 제한
        if (coolerHeight && caseCoolerHeight) {
            if (coolerHeight <= caseCoolerHeight) {
                results.success.push(`쿨러 높이 (${coolerHeight}mm) ↔ 케이스 지원 (${caseCoolerHeight}mm)`);
            } else {
                results.errors.push(`쿨러 높이 ${coolerHeight}mm가 케이스 지원 ${caseCoolerHeight}mm를 초과합니다`);
                results.suggestions.push(`케이스 쿨러 최대 높이를 ${coolerHeight}mm 이상으로 조정하세요`);
            }
        }

        // 5. PSU 용량 ↔ CPU+GPU 전력
        const estimatedPrices = calculateEstimatedPrices();
        if (cpuGeneration || gpuVram) {
            let estimatedPower = 0;

            // CPU 전력 추정
            if (cpuGeneration === 'Intel 14세대' || cpuGeneration === 'Ryzen 7000') {
                estimatedPower += 150;
            } else if (cpuGeneration) {
                estimatedPower += 100;
            }

            // GPU 전력 추정
            if (gpuVram === '24GB+') estimatedPower += 450;
            else if (gpuVram === '16GB') estimatedPower += 350;
            else if (gpuVram === '12GB') estimatedPower += 250;
            else if (gpuVram === '8GB') estimatedPower += 200;
            else if (gpuVram) estimatedPower += 150;

            const recommendedPSU = Math.ceil((estimatedPower * 1.5) / 100) * 100;

            if (psuWattage.length === 0) {
                results.warnings.push(
                    `전력 소비 예상: ${estimatedPower}W → 권장 PSU: ${recommendedPSU}W 이상 (현재 미설정)`
                );
                results.suggestions.push(`PSU 용량에서 ${recommendedPSU}W 이상을 선택하세요`);
            } else {
                const maxPsuWattage = Math.max(...psuWattage.map((w) => parseInt(w)));
                if (maxPsuWattage >= recommendedPSU) {
                    results.success.push(`PSU 용량 (${maxPsuWattage}W) 충분 (권장: ${recommendedPSU}W)`);
                } else {
                    results.warnings.push(
                        `PSU 용량 부족 가능: 예상 ${estimatedPower}W → 권장 ${recommendedPSU}W (선택: ${maxPsuWattage}W)`
                    );
                    results.suggestions.push(`더 높은 PSU 용량(${recommendedPSU}W+)을 선택하는 것을 권장합니다`);
                }
            }
        }

        // 6. 메인보드 포트 수 ↔ 저장장치 개수
        if (m2Slots[0] !== undefined || sataPorts[0] !== undefined) {
            let requiredM2 = 0;
            let requiredSata = 0;

            // M.2 SSD 개수 계산
            if (ssdInterface.includes('NVMe M.2 (Gen4)') || ssdInterface.includes('NVMe M.2 (Gen3)')) {
                requiredM2 = 1; // 최소 1개 필요
            }

            // SATA 장치 개수 계산
            if (ssdInterface.includes('SATA')) {
                requiredSata += 1;
            }
            if (hddCapacity.length > 0) {
                requiredSata += 1; // HDD는 SATA 사용
            }

            // M.2 슬롯 체크
            if (requiredM2 > 0) {
                const availableM2 = m2Slots[1] || 0;
                if (availableM2 >= requiredM2) {
                    results.success.push(`M.2 슬롯 충분 (필요: ${requiredM2}개, 메인보드: 최대 ${availableM2}개)`);
                } else if (availableM2 === 0) {
                    results.warnings.push(`NVMe M.2 SSD 선택 시 메인보드 M.2 슬롯이 필요합니다 (현재 미설정)`);
                    results.suggestions.push('메인보드 M.2 슬롯을 1개 이상으로 설정하세요');
                } else {
                    results.errors.push(`M.2 슬롯 부족 (필요: ${requiredM2}개, 메인보드: ${availableM2}개)`);
                    results.suggestions.push(`메인보드 M.2 슬롯을 ${requiredM2}개 이상으로 조정하세요`);
                }
            }

            // SATA 포트 체크
            if (requiredSata > 0) {
                const availableSata = sataPorts[1] || 0;
                if (availableSata >= requiredSata) {
                    results.success.push(`SATA 포트 충분 (필요: ${requiredSata}개, 메인보드: 최대 ${availableSata}개)`);
                } else if (availableSata === 0) {
                    results.warnings.push(`SATA SSD/HDD 선택 시 메인보드 SATA 포트가 필요합니다 (현재 미설정)`);
                    results.suggestions.push(`메인보드 SATA 포트를 ${requiredSata}개 이상으로 설정하세요`);
                } else {
                    results.errors.push(`SATA 포트 부족 (필요: ${requiredSata}개, 메인보드: ${availableSata}개)`);
                    results.suggestions.push(`메인보드 SATA 포트를 ${requiredSata}개 이상으로 조정하세요`);
                }
            }
        }

        // 7. 메인보드 폼팩터 ↔ 케이스 지원
        if (formFactor.length > 0 && caseBoardSupport.length > 0) {
            const hasCompatible = formFactor.some((form) => caseBoardSupport.includes(form));
            if (hasCompatible) {
                results.success.push('메인보드 폼팩터 ↔ 케이스 지원 호환');
            } else {
                results.errors.push(`메인보드 폼팩터 (${formFactor.join(', ')})를 케이스가 지원하지 않습니다`);
                results.suggestions.push(`케이스 메인보드 지원에서 ${formFactor[0]}를 선택하세요`);
            }
        }

        // 8. RAM 슬롯 개수 (일반적으로 2개 또는 4개)
        if (ramCapacity) {
            const capacity = parseInt(ramCapacity);
            if (capacity > 64) {
                results.warnings.push('128GB RAM은 4개 슬롯 메인보드가 필요할 수 있습니다');
                results.suggestions.push('메인보드가 충분한 RAM 슬롯을 제공하는지 확인하세요');
            }
        }

        // 9. 🆕 CPU TDP ↔ 쿨러 TDP (냉각 능력)
        if (cpuTdp[0] && coolerTdp[0]) {
            if (coolerTdp[0] >= cpuTdp[1]) {
                results.success.push(`쿨러 냉각 성능 충분 (CPU: ${cpuTdp[1]}W, 쿨러: ${coolerTdp[1]}W)`);
            } else {
                results.errors.push(`쿨러 냉각 성능 부족 (CPU: ${cpuTdp[1]}W, 쿨러: ${coolerTdp[1]}W)`);
                results.suggestions.push(`쿨러 TDP를 ${cpuTdp[1]}W 이상으로 조정하세요`);
            }
        }

        // 10. 🆕 CPU 세대 ↔ 메인보드 BIOS 지원
        if (cpuGeneration && chipset.length > 0) {
            let biosCompatible = false;
            if (cpuGeneration.includes('Intel 14세대') && (chipset.includes('Z790') || chipset.includes('B760'))) {
                biosCompatible = true;
            } else if (
                cpuGeneration.includes('Intel 13세대') &&
                (chipset.includes('Z790') ||
                    chipset.includes('Z690') ||
                    chipset.includes('B760') ||
                    chipset.includes('B660'))
            ) {
                biosCompatible = true;
            } else if (
                cpuGeneration.includes('Ryzen 7000') &&
                (chipset.includes('X670E') || chipset.includes('B650'))
            ) {
                biosCompatible = true;
            } else if (
                cpuGeneration.includes('Ryzen 5000') &&
                (chipset.includes('X570') || chipset.includes('B550') || chipset.includes('B450'))
            ) {
                biosCompatible = true;
                results.warnings.push('Ryzen 5000 시리즈는 B450 칩셋에서 BIOS 업데이트가 필요할 수 있습니다');
            }

            if (biosCompatible) {
                results.success.push(`CPU 세대 (${cpuGeneration}) ↔ 메인보드 칩셋 호환`);
            } else {
                results.errors.push(
                    `CPU 세대 (${cpuGeneration})와 메인보드 칩셋 (${chipset.join(', ')})이 불일치합니다`
                );
                results.suggestions.push('CPU 세대에 맞는 메인보드 칩셋을 선택하세요');
            }
        }

        // 11. 🆕 RAM 클럭 ↔ CPU/메인보드 지원 (XMP/EXPO)
        if (ramSpeed.length > 0 && maxRamSpeed) {
            const selectedMaxSpeed = Math.max(...ramSpeed.map((s) => parseInt(s)));
            if (selectedMaxSpeed <= maxRamSpeed) {
                results.success.push(`RAM 속도 (${selectedMaxSpeed}MHz) ↔ 메인보드 지원 (최대 ${maxRamSpeed}MHz)`);
            } else {
                results.warnings.push(`RAM 속도 ${selectedMaxSpeed}MHz가 메인보드 지원 ${maxRamSpeed}MHz를 초과합니다`);
                results.suggestions.push(
                    `메인보드가 ${selectedMaxSpeed}MHz RAM을 지원하는지 확인하거나, RAM 속도를 낮추세요`
                );
            }
        }

        if (ramXmp !== 'any' && xmpSupport !== 'any') {
            if (ramXmp === xmpSupport) {
                results.success.push(`XMP/EXPO 프로필 지원 호환`);
            } else {
                results.warnings.push(`RAM이 ${ramXmp}를 요구하지만, 메인보드는 ${xmpSupport}를 지원합니다`);
            }
        }

        // 12. 🆕 GPU 두께(슬롯) ↔ 케이스 지원
        if (gpuSlots && caseGpuSlots) {
            if (gpuSlots <= caseGpuSlots) {
                results.success.push(`GPU 두께 (${gpuSlots}슬롯) ↔ 케이스 지원 (${caseGpuSlots}슬롯)`);
            } else {
                results.errors.push(`GPU 두께 ${gpuSlots}슬롯이 케이스 지원 ${caseGpuSlots}슬롯을 초과합니다`);
                results.suggestions.push('더 넓은 슬롯 공간을 제공하는 케이스를 선택하세요');
            }
        }

        // 13. 🆕 파워 커넥터 ↔ GPU 요구사항
        if (gpuConnector && psuConnectors.length > 0) {
            if (psuConnectors.includes(gpuConnector)) {
                results.success.push(`GPU 전원 커넥터 (${gpuConnector}) ↔ PSU 지원`);
            } else {
                results.errors.push(`GPU가 ${gpuConnector} 커넥터를 요구하지만, PSU가 지원하지 않습니다`);
                results.suggestions.push(`PSU 커넥터에서 "${gpuConnector}"를 선택하세요`);
            }
        }

        // 14. 🆕 파워 크기(SFX/ATX) ↔ 케이스
        if (psuFormFactor && casePsuSupport.length > 0) {
            if (casePsuSupport.includes(psuFormFactor)) {
                results.success.push(`PSU 크기 (${psuFormFactor}) ↔ 케이스 지원`);
            } else {
                results.errors.push(
                    `PSU 크기 ${psuFormFactor}를 케이스가 지원하지 않습니다 (케이스 지원: ${casePsuSupport.join(', ')})`
                );
                results.suggestions.push(`케이스가 지원하는 PSU 크기 (${casePsuSupport[0]})로 변경하세요`);
            }
        }

        // 15. 🆕 RAM 최대 용량 ↔ 메인보드
        if (ramCapacity && ramMaxCapacity) {
            const selectedCapacity = parseInt(ramCapacity);
            if (selectedCapacity <= ramMaxCapacity) {
                results.success.push(`RAM 용량 (${ramCapacity}) ↔ 메인보드 지원 (최대 ${ramMaxCapacity}GB)`);
            } else {
                results.errors.push(`RAM 용량 ${ramCapacity}가 메인보드 최대 용량 ${ramMaxCapacity}GB를 초과합니다`);
                results.suggestions.push(`메인보드를 더 높은 RAM 용량을 지원하는 모델로 변경하세요`);
            }
        }

        // 16. 🆕 M.2 장착 ↔ SATA 포트 충돌 (PCIe 레인 공유)
        if (m2SataConflict === 'yes') {
            const requiredM2 =
                ssdInterface.includes('NVMe M.2 (Gen4)') || ssdInterface.includes('NVMe M.2 (Gen3)') ? 1 : 0;
            const requiredSata = (ssdInterface.includes('SATA') ? 1 : 0) + (hddCapacity.length > 0 ? 1 : 0);

            if (requiredM2 > 0 && requiredSata > 0) {
                results.warnings.push('M.2 SSD 장착 시 일부 SATA 포트가 비활성화될 수 있습니다');
                results.suggestions.push('메인보드 매뉴얼에서 M.2/SATA 포트 공유 여부를 확인하세요');
            }
        }

        // 17. 🆕 80+ 등급 안정성 권장
        if (psuEfficiency.length > 0) {
            const highEndGpu = gpuVram === '24GB+' || gpuVram === '16GB';
            const highEndCpu = cpuGeneration === 'Intel 14세대' || cpuGeneration === 'Ryzen 7000';

            if (highEndGpu || highEndCpu) {
                if (
                    psuEfficiency.includes('Platinum') ||
                    psuEfficiency.includes('Titanium') ||
                    psuEfficiency.includes('Gold')
                ) {
                    results.success.push('고성능 시스템에 적합한 PSU 등급 (Gold 이상)');
                } else {
                    results.warnings.push('고성능 GPU/CPU 사용 시 Gold 등급 이상 PSU를 권장합니다');
                    results.suggestions.push('PSU 80+ 등급을 Gold, Platinum, Titanium 중 하나로 선택하세요');
                }
            }
        }

        // 18. 미설정 핵심 필터 체크
        if (!cpuSocket && !cpuGeneration) {
            results.warnings.push('CPU 필터가 설정되지 않았습니다');
        }
        if (!gpuVram) {
            results.warnings.push('GPU VRAM이 설정되지 않았습니다');
        }
        if (!ramGen || !ramCapacity) {
            results.warnings.push('RAM 필터가 설정되지 않았습니다');
        }

        // 결과 표시
        showCompatibilityResults(results);
    };

    // 호환성 결과 모달 표시
    const showCompatibilityResults = (results) => {
        setCompatibilityModal({ show: true, results });
    };

    // 모달 닫기
    const closeCompatibilityModal = () => {
        setCompatibilityModal({ show: false, results: null });
    };

    const handleStart = () => {
        // 전문가 모드 설정 수집
        const expertSettings = {
            cpu: {
                socket: cpuSocket,
                generation: cpuGeneration,
                igpu: cpuIgpu,
                cores: cpuCores,
                threads: cpuThreads,
                tdp: cpuTdp,
            },
            cooler: {
                type: coolerType,
                socket: coolerSocket,
                height: coolerHeight,
                fanSize: coolerFanSize,
                noise: coolerNoise,
                rgb: coolerRgb,
            },
            mainboard: { chipset, formFactor, memoryGen, m2Slots, sataPorts, hasWifi },
            ram: {
                gen: ramGen,
                capacity: ramCapacity,
                speed: ramSpeed,
                timing: ramTiming,
                voltage: ramVoltage,
                xmp: ramXmp,
            },
            gpu: { vram: gpuVram, power: gpuPower, length: gpuLength, fans: gpuFans, backplate: gpuBackplate },
            psu: {
                wattage: psuWattage,
                efficiency: psuEfficiency,
                cableType: psuCableType,
                fanSize: psuFanSize,
                depth: psuDepth,
            },
            case: {
                type: caseType,
                boardSupport: caseBoardSupport,
                gpuLength: caseGpuLength,
                coolerHeight: caseCoolerHeight,
                fanCount: caseFanCount,
                airflow: caseAirflow,
                glass: caseGlass,
            },
            storage: {
                ssd: {
                    interface: ssdInterface,
                    formFactor: ssdFormFactor,
                    capacity: ssdCapacity,
                    dram: ssdDram,
                    tbw: ssdTbw,
                    heatsink: ssdHeatsink,
                },
                hdd: { capacity: hddCapacity, rpm: hddRpm },
            },
            environment: { caseEnvironment, rgbPreference },
            budget: currentBudget,
            componentRatios,
        };
        onNext(expertSettings);
    };

    return (
        <>
            {/* 안내 메시지 */}
            <div
                style={{
                    marginTop: '1rem',
                    padding: '1.5rem',
                    background: '#fef3c7',
                    borderRadius: '12px',
                    border: '2px solid #f59e0b',
                }}
            >
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1rem' }}>
                    <span style={{ fontSize: '1.5rem' }}>⚡</span>
                    <h3 style={{ margin: 0, fontSize: '1.1rem', fontWeight: '700', color: '#92400e' }}>전문가 모드</h3>
                </div>
                <p style={{ fontSize: '0.85rem', color: '#78350f', margin: 0 }}>
                    각 부품별 상세 필터를 설정할 수 있습니다. 필요한 부품을 클릭하여 세부 옵션을 확인하세요.
                </p>
            </div>

            {/* 🧠 CPU */}
            <div className="form-group" style={{ marginTop: '1.5rem' }}>
                <div
                    style={{
                        background: 'linear-gradient(135deg, #3b82f6, #2563eb)',
                        color: 'white',
                        padding: '0.8rem 1rem',
                        borderRadius: '8px',
                        marginBottom: '0.8rem',
                        cursor: 'pointer',
                    }}
                    onClick={() => toggleSection('cpu')}
                >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                            <span style={{ fontWeight: '600' }}>CPU (중앙처리장치)</span>
                        </div>
                        <span>{expandedSections.cpu ? '▲' : '▼'}</span>
                    </div>
                </div>
                {expandedSections.cpu && (
                    <div style={{ padding: '1rem', background: '#f8fafc', borderRadius: '8px' }}>
                        <div
                            style={{ fontSize: '0.75rem', color: '#64748b', marginBottom: '1rem', fontStyle: 'italic' }}
                        >
                            시스템 성능의 중심. 선택에 따라 전체 조합이 결정됨
                        </div>

                        {/* 핵심 필터 */}
                        <div style={{ marginBottom: '1rem', paddingBottom: '1rem', borderBottom: '1px solid #e2e8f0' }}>
                            <div
                                style={{
                                    fontSize: '0.8rem',
                                    fontWeight: '700',
                                    color: '#1e293b',
                                    marginBottom: '0.8rem',
                                }}
                            >
                                핵심 필터
                            </div>

                            {/* 소켓 종류 - 라디오 */}
                            <div style={{ marginBottom: '1rem' }}>
                                <label
                                    style={{
                                        fontSize: '0.8rem',
                                        fontWeight: '600',
                                        marginBottom: '0.5rem',
                                        display: 'block',
                                    }}
                                >
                                    소켓 종류 (핵심)
                                </label>
                                <div className="form-radio">
                                    <input
                                        type="radio"
                                        name="cpuSocket"
                                        value=""
                                        checked={cpuSocket === ''}
                                        onChange={(e) => setCpuSocket(e.target.value)}
                                    />
                                    <span style={{ fontSize: '0.8rem' }}>상관없음</span>
                                </div>
                                {['LGA1700', 'AM5', 'AM4', 'LGA1200'].map((socket) => (
                                    <div key={socket} className="form-radio">
                                        <input
                                            type="radio"
                                            name="cpuSocket"
                                            value={socket}
                                            checked={cpuSocket === socket}
                                            onChange={(e) => setCpuSocket(e.target.value)}
                                        />
                                        <span style={{ fontSize: '0.8rem' }}>{socket}</span>
                                    </div>
                                ))}
                            </div>

                            {/* 세대/아키텍처 - 라디오 */}
                            <div style={{ marginBottom: '1rem' }}>
                                <label
                                    style={{
                                        fontSize: '0.8rem',
                                        fontWeight: '600',
                                        marginBottom: '0.5rem',
                                        display: 'block',
                                    }}
                                >
                                    세대 / 아키텍처 (핵심)
                                </label>
                                <div className="form-radio">
                                    <input
                                        type="radio"
                                        name="cpuGeneration"
                                        value=""
                                        checked={cpuGeneration === ''}
                                        onChange={(e) => setCpuGeneration(e.target.value)}
                                    />
                                    <span style={{ fontSize: '0.8rem' }}>상관없음</span>
                                </div>
                                {['Intel 14세대', 'Intel 13세대', 'Ryzen 7000', 'Ryzen 5000'].map((gen) => (
                                    <div key={gen} className="form-radio">
                                        <input
                                            type="radio"
                                            name="cpuGeneration"
                                            value={gen}
                                            checked={cpuGeneration === gen}
                                            onChange={(e) => setCpuGeneration(e.target.value)}
                                        />
                                        <span style={{ fontSize: '0.8rem' }}>{gen}</span>
                                    </div>
                                ))}
                            </div>

                            {/* 내장 그래픽 */}
                            <div>
                                <label
                                    style={{
                                        fontSize: '0.8rem',
                                        fontWeight: '600',
                                        marginBottom: '0.5rem',
                                        display: 'block',
                                    }}
                                >
                                    내장 그래픽 (iGPU)
                                </label>
                                <div className="form-radio">
                                    <input
                                        type="radio"
                                        name="cpuIgpu"
                                        value="any"
                                        checked={cpuIgpu === 'any'}
                                        onChange={(e) => setCpuIgpu(e.target.value)}
                                    />
                                    <span style={{ fontSize: '0.8rem' }}>상관없음</span>
                                </div>
                                <div className="form-radio">
                                    <input
                                        type="radio"
                                        name="cpuIgpu"
                                        value="yes"
                                        checked={cpuIgpu === 'yes'}
                                        onChange={(e) => setCpuIgpu(e.target.value)}
                                    />
                                    <span style={{ fontSize: '0.8rem' }}>있음 (모니터 연결 가능)</span>
                                </div>
                                <div className="form-radio">
                                    <input
                                        type="radio"
                                        name="cpuIgpu"
                                        value="no"
                                        checked={cpuIgpu === 'no'}
                                        onChange={(e) => setCpuIgpu(e.target.value)}
                                    />
                                    <span style={{ fontSize: '0.8rem' }}>없음 (F 시리즈)</span>
                                </div>
                            </div>
                        </div>

                        {/* 자세히 ▼ */}
                        <div>
                            <button
                                onClick={() => toggleDetails('cpu')}
                                style={{
                                    width: '100%',
                                    padding: '0.6rem',
                                    background: expandedDetails.cpu ? '#e0e7ff' : '#f1f5f9',
                                    color: expandedDetails.cpu ? '#4338ca' : '#64748b',
                                    border: 'none',
                                    borderRadius: '6px',
                                    fontSize: '0.8rem',
                                    fontWeight: '600',
                                    cursor: 'pointer',
                                    transition: 'all 0.2s',
                                    marginBottom: '0.8rem',
                                }}
                            >
                                {expandedDetails.cpu ? '▲ 자세히 접기' : '▼ 자세히 펼치기'}
                            </button>

                            {expandedDetails.cpu && (
                                <div style={{ paddingTop: '0.5rem' }}>
                                    {/* 코어 수 */}
                                    <div style={{ marginBottom: '1rem' }}>
                                        <label
                                            style={{
                                                fontSize: '0.8rem',
                                                fontWeight: '600',
                                                marginBottom: '0.5rem',
                                                display: 'block',
                                            }}
                                        >
                                            코어 수
                                        </label>
                                        {['4코어', '6코어', '8코어', '12코어', '16코어', '24코어+'].map((core) => (
                                            <div key={core} className="form-checkbox">
                                                <input
                                                    type="checkbox"
                                                    checked={cpuCores.includes(core)}
                                                    onChange={(e) => {
                                                        if (e.target.checked) {
                                                            setCpuCores([...cpuCores, core]);
                                                        } else {
                                                            setCpuCores(cpuCores.filter((c) => c !== core));
                                                        }
                                                    }}
                                                />
                                                <span style={{ fontSize: '0.8rem' }}>{core}</span>
                                            </div>
                                        ))}
                                    </div>

                                    {/* 스레드 수 */}
                                    <div style={{ marginBottom: '1rem' }}>
                                        <label
                                            style={{
                                                fontSize: '0.8rem',
                                                fontWeight: '600',
                                                marginBottom: '0.5rem',
                                                display: 'block',
                                            }}
                                        >
                                            스레드 수
                                        </label>
                                        {['8스레드', '12스레드', '16스레드', '24스레드', '32스레드+'].map((thread) => (
                                            <div key={thread} className="form-checkbox">
                                                <input
                                                    type="checkbox"
                                                    checked={cpuThreads.includes(thread)}
                                                    onChange={(e) => {
                                                        if (e.target.checked) {
                                                            setCpuThreads([...cpuThreads, thread]);
                                                        } else {
                                                            setCpuThreads(cpuThreads.filter((t) => t !== thread));
                                                        }
                                                    }}
                                                />
                                                <span style={{ fontSize: '0.8rem' }}>{thread}</span>
                                            </div>
                                        ))}
                                    </div>

                                    {/* TDP */}
                                    <div>
                                        <label
                                            style={{
                                                fontSize: '0.8rem',
                                                fontWeight: '600',
                                                marginBottom: '0.5rem',
                                                display: 'block',
                                            }}
                                        >
                                            TDP (전력 소비): {cpuTdp[0]}W ~ {cpuTdp[1]}W
                                        </label>
                                        <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
                                            <span style={{ fontSize: '0.7rem', color: '#64748b' }}>65W</span>
                                            <input
                                                type="range"
                                                min="65"
                                                max="250"
                                                value={cpuTdp[1]}
                                                onChange={(e) => setCpuTdp([cpuTdp[0], parseInt(e.target.value)])}
                                                style={{ flex: 1 }}
                                            />
                                            <span style={{ fontSize: '0.7rem', color: '#64748b' }}>250W</span>
                                        </div>
                                    </div>
                                </div>
                            )}
                        </div>
                    </div>
                )}
            </div>

            {/* ❄️ CPU 쿨러 */}
            <div className="form-group" style={{ marginTop: '1.5rem' }}>
                <div
                    style={{
                        background: 'linear-gradient(135deg, #06b6d4, #0891b2)',
                        color: 'white',
                        padding: '0.8rem 1rem',
                        borderRadius: '8px',
                        marginBottom: '0.8rem',
                        cursor: 'pointer',
                    }}
                    onClick={() => toggleSection('cooler')}
                >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                            <span style={{ fontWeight: '600' }}>CPU 쿨러</span>
                        </div>
                        <span>{expandedSections.cooler ? '▲' : '▼'}</span>
                    </div>
                </div>
                {expandedSections.cooler && (
                    <div style={{ padding: '1rem', background: '#f8fafc', borderRadius: '8px' }}>
                        <div
                            style={{ fontSize: '0.75rem', color: '#64748b', marginBottom: '1rem', fontStyle: 'italic' }}
                        >
                            CPU 온도 관리. 케이스 높이와 호환성 확인 필수
                        </div>

                        {/* 핵심 필터 */}
                        <div style={{ marginBottom: '1rem', paddingBottom: '1rem', borderBottom: '1px solid #e2e8f0' }}>
                            <div
                                style={{
                                    fontSize: '0.8rem',
                                    fontWeight: '700',
                                    color: '#1e293b',
                                    marginBottom: '0.8rem',
                                }}
                            >
                                핵심 필터
                            </div>

                            {/* 쿨러 타입 - 라디오 */}
                            <div>
                                <label
                                    style={{
                                        fontSize: '0.8rem',
                                        fontWeight: '600',
                                        marginBottom: '0.5rem',
                                        display: 'block',
                                    }}
                                >
                                    쿨러 타입
                                </label>
                                <div className="form-radio">
                                    <input
                                        type="radio"
                                        name="coolerType"
                                        value=""
                                        checked={coolerType === ''}
                                        onChange={(e) => setCoolerType(e.target.value)}
                                    />
                                    <span style={{ fontSize: '0.8rem' }}>상관없음</span>
                                </div>
                                {['타워형', '저소음형', '수냉 120mm', '수냉 240mm', '수냉 360mm'].map((type) => (
                                    <div key={type} className="form-radio">
                                        <input
                                            type="radio"
                                            name="coolerType"
                                            value={type}
                                            checked={coolerType === type}
                                            onChange={(e) => setCoolerType(e.target.value)}
                                        />
                                        <span style={{ fontSize: '0.8rem' }}>{type}</span>
                                    </div>
                                ))}
                            </div>
                        </div>

                        {/* 자세히 ▼ */}
                        <div>
                            <button
                                onClick={() => toggleDetails('cooler')}
                                style={{
                                    width: '100%',
                                    padding: '0.6rem',
                                    background: expandedDetails.cooler ? '#e0e7ff' : '#f1f5f9',
                                    color: expandedDetails.cooler ? '#4338ca' : '#64748b',
                                    border: 'none',
                                    borderRadius: '6px',
                                    fontSize: '0.8rem',
                                    fontWeight: '600',
                                    cursor: 'pointer',
                                    transition: 'all 0.2s',
                                    marginBottom: '0.8rem',
                                }}
                            >
                                {expandedDetails.cooler ? '▲ 자세히 접기' : '▼ 자세히 펼치기'}
                            </button>

                            {expandedDetails.cooler && (
                                <div style={{ paddingTop: '0.5rem' }}>
                                    {/* 소켓 호환 */}
                                    <div style={{ marginBottom: '1rem' }}>
                                        <label
                                            style={{
                                                fontSize: '0.8rem',
                                                fontWeight: '600',
                                                marginBottom: '0.5rem',
                                                display: 'block',
                                            }}
                                        >
                                            소켓 호환
                                        </label>
                                        {['LGA1700', 'AM5', 'AM4', 'LGA1200'].map((socket) => (
                                            <div key={socket} className="form-checkbox">
                                                <input
                                                    type="checkbox"
                                                    checked={coolerSocket.includes(socket)}
                                                    onChange={(e) => {
                                                        if (e.target.checked) {
                                                            setCoolerSocket([...coolerSocket, socket]);
                                                        } else {
                                                            setCoolerSocket(coolerSocket.filter((s) => s !== socket));
                                                        }
                                                    }}
                                                />
                                                <span style={{ fontSize: '0.8rem' }}>{socket}</span>
                                            </div>
                                        ))}
                                    </div>

                                    {/* 최대 높이 */}
                                    <div style={{ marginBottom: '1rem' }}>
                                        <label
                                            style={{
                                                fontSize: '0.8rem',
                                                fontWeight: '600',
                                                marginBottom: '0.5rem',
                                                display: 'block',
                                            }}
                                        >
                                            쿨러 높이 제한: 최대 {coolerHeight}mm
                                        </label>
                                        <input
                                            type="range"
                                            min="50"
                                            max="200"
                                            step="5"
                                            value={coolerHeight}
                                            onChange={(e) => setCoolerHeight(parseInt(e.target.value))}
                                            style={{ width: '100%' }}
                                        />
                                    </div>

                                    {/* 🆕 쿨러 TDP (냉각 능력) */}
                                    <div style={{ marginBottom: '1rem' }}>
                                        <label
                                            style={{
                                                fontSize: '0.8rem',
                                                fontWeight: '600',
                                                marginBottom: '0.5rem',
                                                display: 'block',
                                            }}
                                        >
                                            쿨러 TDP (냉각 능력): {coolerTdp[0]}W ~ {coolerTdp[1]}W
                                        </label>
                                        <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
                                            <span style={{ fontSize: '0.7rem', color: '#64748b' }}>65W</span>
                                            <input
                                                type="range"
                                                min="65"
                                                max="250"
                                                value={coolerTdp[1]}
                                                onChange={(e) => setCoolerTdp([coolerTdp[0], parseInt(e.target.value)])}
                                                style={{ flex: 1 }}
                                            />
                                            <span style={{ fontSize: '0.7rem', color: '#64748b' }}>250W</span>
                                        </div>
                                    </div>

                                    {/* RGB 조명 */}
                                    <div>
                                        <label
                                            style={{
                                                fontSize: '0.8rem',
                                                fontWeight: '600',
                                                marginBottom: '0.5rem',
                                                display: 'block',
                                            }}
                                        >
                                            RGB 조명
                                        </label>
                                        <div className="form-radio">
                                            <input
                                                type="radio"
                                                name="coolerRgb"
                                                value="any"
                                                checked={coolerRgb === 'any'}
                                                onChange={(e) => setCoolerRgb(e.target.value)}
                                            />
                                            <span style={{ fontSize: '0.8rem' }}>상관없음</span>
                                        </div>
                                        <div className="form-radio">
                                            <input
                                                type="radio"
                                                name="coolerRgb"
                                                value="yes"
                                                checked={coolerRgb === 'yes'}
                                                onChange={(e) => setCoolerRgb(e.target.value)}
                                            />
                                            <span style={{ fontSize: '0.8rem' }}>RGB 필수</span>
                                        </div>
                                        <div className="form-radio">
                                            <input
                                                type="radio"
                                                name="coolerRgb"
                                                value="no"
                                                checked={coolerRgb === 'no'}
                                                onChange={(e) => setCoolerRgb(e.target.value)}
                                            />
                                            <span style={{ fontSize: '0.8rem' }}>RGB 불필요</span>
                                        </div>
                                    </div>
                                </div>
                            )}
                        </div>
                    </div>
                )}
            </div>

            {/* 🔲 메인보드 */}
            <div className="form-group" style={{ marginTop: '1.5rem' }}>
                <div
                    style={{
                        background: 'linear-gradient(135deg, #10b981, #059669)',
                        color: 'white',
                        padding: '0.8rem 1rem',
                        borderRadius: '8px',
                        marginBottom: '0.8rem',
                        cursor: 'pointer',
                    }}
                    onClick={() => toggleSection('mainboard')}
                >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                            <span style={{ fontWeight: '600' }}>메인보드 (마더보드)</span>
                        </div>
                        <span>{expandedSections.mainboard ? '▲' : '▼'}</span>
                    </div>
                </div>
                {expandedSections.mainboard && (
                    <div style={{ padding: '1rem', background: '#f8fafc', borderRadius: '8px' }}>
                        <div
                            style={{ fontSize: '0.75rem', color: '#64748b', marginBottom: '1rem', fontStyle: 'italic' }}
                        >
                            모든 부품의 연결 허브. CPU 소켓과 칩셋 호환 확인 필수
                        </div>

                        {/* 핵심 필터 */}
                        <div style={{ marginBottom: '1rem', paddingBottom: '1rem', borderBottom: '1px solid #e2e8f0' }}>
                            <div
                                style={{
                                    fontSize: '0.8rem',
                                    fontWeight: '700',
                                    color: '#1e293b',
                                    marginBottom: '0.8rem',
                                }}
                            >
                                핵심 필터
                            </div>

                            {/* 칩셋 */}
                            <div>
                                <label
                                    style={{
                                        fontSize: '0.8rem',
                                        fontWeight: '600',
                                        marginBottom: '0.5rem',
                                        display: 'block',
                                    }}
                                >
                                    칩셋
                                </label>
                                {['Z790', 'B760', 'H770', 'X670E', 'B650', 'A620'].map((chip) => (
                                    <div key={chip} className="form-checkbox">
                                        <input
                                            type="checkbox"
                                            checked={chipset.includes(chip)}
                                            onChange={(e) => {
                                                if (e.target.checked) {
                                                    setChipset([...chipset, chip]);
                                                } else {
                                                    setChipset(chipset.filter((c) => c !== chip));
                                                }
                                            }}
                                        />
                                        <span style={{ fontSize: '0.8rem' }}>{chip}</span>
                                    </div>
                                ))}
                            </div>
                        </div>

                        {/* 자세히 ▼ */}
                        <div>
                            <button
                                onClick={() => toggleDetails('mainboard')}
                                style={{
                                    width: '100%',
                                    padding: '0.6rem',
                                    background: expandedDetails.mainboard ? '#e0e7ff' : '#f1f5f9',
                                    color: expandedDetails.mainboard ? '#4338ca' : '#64748b',
                                    border: 'none',
                                    borderRadius: '6px',
                                    fontSize: '0.8rem',
                                    fontWeight: '600',
                                    cursor: 'pointer',
                                    transition: 'all 0.2s',
                                    marginBottom: '0.8rem',
                                }}
                            >
                                {expandedDetails.mainboard ? '▲ 자세히 접기' : '▼ 자세히 펼치기'}
                            </button>

                            {expandedDetails.mainboard && (
                                <div style={{ paddingTop: '0.5rem' }}>
                                    {/* 폼팩터 */}
                                    <div style={{ marginBottom: '1rem' }}>
                                        <label
                                            style={{
                                                fontSize: '0.8rem',
                                                fontWeight: '600',
                                                marginBottom: '0.5rem',
                                                display: 'block',
                                            }}
                                        >
                                            폼팩터 (크기)
                                        </label>
                                        {['E-ATX', 'ATX', 'M-ATX', 'Mini-ITX'].map((form) => (
                                            <div key={form} className="form-checkbox">
                                                <input
                                                    type="checkbox"
                                                    checked={formFactor.includes(form)}
                                                    onChange={(e) => {
                                                        if (e.target.checked) {
                                                            setFormFactor([...formFactor, form]);
                                                        } else {
                                                            setFormFactor(formFactor.filter((f) => f !== form));
                                                        }
                                                    }}
                                                />
                                                <span style={{ fontSize: '0.8rem' }}>{form}</span>
                                            </div>
                                        ))}
                                    </div>

                                    {/* 메모리 세대 */}
                                    <div style={{ marginBottom: '1rem' }}>
                                        <label
                                            style={{
                                                fontSize: '0.8rem',
                                                fontWeight: '600',
                                                marginBottom: '0.5rem',
                                                display: 'block',
                                            }}
                                        >
                                            메모리 세대 지원
                                        </label>
                                        {['DDR5', 'DDR4'].map((mem) => (
                                            <div key={mem} className="form-checkbox">
                                                <input
                                                    type="checkbox"
                                                    checked={memoryGen.includes(mem)}
                                                    onChange={(e) => {
                                                        if (e.target.checked) {
                                                            setMemoryGen([...memoryGen, mem]);
                                                        } else {
                                                            setMemoryGen(memoryGen.filter((m) => m !== mem));
                                                        }
                                                    }}
                                                />
                                                <span style={{ fontSize: '0.8rem' }}>{mem}</span>
                                            </div>
                                        ))}
                                    </div>

                                    {/* 🆕 RAM 최대 용량 */}
                                    <div style={{ marginBottom: '1rem' }}>
                                        <label
                                            style={{
                                                fontSize: '0.8rem',
                                                fontWeight: '600',
                                                marginBottom: '0.5rem',
                                                display: 'block',
                                            }}
                                        >
                                            RAM 최대 지원 용량: {ramMaxCapacity}GB
                                        </label>
                                        <input
                                            type="range"
                                            min="32"
                                            max="192"
                                            step="32"
                                            value={ramMaxCapacity}
                                            onChange={(e) => setRamMaxCapacity(parseInt(e.target.value))}
                                            style={{ width: '100%' }}
                                        />
                                    </div>

                                    {/* 🆕 RAM 최대 속도 */}
                                    <div style={{ marginBottom: '1rem' }}>
                                        <label
                                            style={{
                                                fontSize: '0.8rem',
                                                fontWeight: '600',
                                                marginBottom: '0.5rem',
                                                display: 'block',
                                            }}
                                        >
                                            RAM 최대 속도: {maxRamSpeed}MHz
                                        </label>
                                        <input
                                            type="range"
                                            min="3200"
                                            max="8000"
                                            step="400"
                                            value={maxRamSpeed}
                                            onChange={(e) => setMaxRamSpeed(parseInt(e.target.value))}
                                            style={{ width: '100%' }}
                                        />
                                    </div>

                                    {/* 🆕 XMP/EXPO 지원 */}
                                    <div style={{ marginBottom: '1rem' }}>
                                        <label
                                            style={{
                                                fontSize: '0.8rem',
                                                fontWeight: '600',
                                                marginBottom: '0.5rem',
                                                display: 'block',
                                            }}
                                        >
                                            XMP/EXPO 지원
                                        </label>
                                        <div className="form-radio">
                                            <input
                                                type="radio"
                                                name="xmpSupport"
                                                value="any"
                                                checked={xmpSupport === 'any'}
                                                onChange={(e) => setXmpSupport(e.target.value)}
                                            />
                                            <span style={{ fontSize: '0.8rem' }}>상관없음</span>
                                        </div>
                                        <div className="form-radio">
                                            <input
                                                type="radio"
                                                name="xmpSupport"
                                                value="XMP"
                                                checked={xmpSupport === 'XMP'}
                                                onChange={(e) => setXmpSupport(e.target.value)}
                                            />
                                            <span style={{ fontSize: '0.8rem' }}>XMP (Intel)</span>
                                        </div>
                                        <div className="form-radio">
                                            <input
                                                type="radio"
                                                name="xmpSupport"
                                                value="EXPO"
                                                checked={xmpSupport === 'EXPO'}
                                                onChange={(e) => setXmpSupport(e.target.value)}
                                            />
                                            <span style={{ fontSize: '0.8rem' }}>EXPO (AMD)</span>
                                        </div>
                                    </div>

                                    {/* M.2 슬롯 수 */}
                                    <div style={{ marginBottom: '1rem' }}>
                                        <label
                                            style={{
                                                fontSize: '0.8rem',
                                                fontWeight: '600',
                                                marginBottom: '0.5rem',
                                                display: 'block',
                                            }}
                                        >
                                            M.2 슬롯 수: {m2Slots[0]} ~ {m2Slots[1]}개
                                        </label>
                                        <input
                                            type="range"
                                            min="0"
                                            max="5"
                                            value={m2Slots[1]}
                                            onChange={(e) => setM2Slots([m2Slots[0], parseInt(e.target.value)])}
                                            style={{ width: '100%' }}
                                        />
                                    </div>

                                    {/* SATA 포트 수 */}
                                    <div style={{ marginBottom: '1rem' }}>
                                        <label
                                            style={{
                                                fontSize: '0.8rem',
                                                fontWeight: '600',
                                                marginBottom: '0.5rem',
                                                display: 'block',
                                            }}
                                        >
                                            SATA 포트 수: {sataPorts[0]} ~ {sataPorts[1]}개
                                        </label>
                                        <input
                                            type="range"
                                            min="0"
                                            max="8"
                                            value={sataPorts[1]}
                                            onChange={(e) => setSataPorts([sataPorts[0], parseInt(e.target.value)])}
                                            style={{ width: '100%' }}
                                        />
                                    </div>

                                    {/* 🆕 M.2 / SATA 포트 충돌 */}
                                    <div style={{ marginBottom: '1rem' }}>
                                        <label
                                            style={{
                                                fontSize: '0.8rem',
                                                fontWeight: '600',
                                                marginBottom: '0.5rem',
                                                display: 'block',
                                            }}
                                        >
                                            M.2 장착 시 SATA 포트 충돌
                                        </label>
                                        <div className="form-radio">
                                            <input
                                                type="radio"
                                                name="m2SataConflict"
                                                value="any"
                                                checked={m2SataConflict === 'any'}
                                                onChange={(e) => setM2SataConflict(e.target.value)}
                                            />
                                            <span style={{ fontSize: '0.8rem' }}>상관없음</span>
                                        </div>
                                        <div className="form-radio">
                                            <input
                                                type="radio"
                                                name="m2SataConflict"
                                                value="no"
                                                checked={m2SataConflict === 'no'}
                                                onChange={(e) => setM2SataConflict(e.target.value)}
                                            />
                                            <span style={{ fontSize: '0.8rem' }}>충돌 없음</span>
                                        </div>
                                        <div className="form-radio">
                                            <input
                                                type="radio"
                                                name="m2SataConflict"
                                                value="yes"
                                                checked={m2SataConflict === 'yes'}
                                                onChange={(e) => setM2SataConflict(e.target.value)}
                                            />
                                            <span style={{ fontSize: '0.8rem' }}>일부 포트 비활성화됨</span>
                                        </div>
                                    </div>

                                    {/* Wi-Fi */}
                                    <div>
                                        <label
                                            style={{
                                                fontSize: '0.8rem',
                                                fontWeight: '600',
                                                marginBottom: '0.5rem',
                                                display: 'block',
                                            }}
                                        >
                                            Wi-Fi 내장
                                        </label>
                                        <div className="form-radio">
                                            <input
                                                type="radio"
                                                name="hasWifi"
                                                value="any"
                                                checked={hasWifi === 'any'}
                                                onChange={(e) => setHasWifi(e.target.value)}
                                            />
                                            <span style={{ fontSize: '0.8rem' }}>상관없음</span>
                                        </div>
                                        <div className="form-radio">
                                            <input
                                                type="radio"
                                                name="hasWifi"
                                                value="yes"
                                                checked={hasWifi === 'yes'}
                                                onChange={(e) => setHasWifi(e.target.value)}
                                            />
                                            <span style={{ fontSize: '0.8rem' }}>Wi-Fi 필수</span>
                                        </div>
                                        <div className="form-radio">
                                            <input
                                                type="radio"
                                                name="hasWifi"
                                                value="no"
                                                checked={hasWifi === 'no'}
                                                onChange={(e) => setHasWifi(e.target.value)}
                                            />
                                            <span style={{ fontSize: '0.8rem' }}>유선만 사용</span>
                                        </div>
                                    </div>
                                </div>
                            )}
                        </div>
                    </div>
                )}
            </div>

            {/* 💾 RAM (메모리) */}
            <div className="form-group" style={{ marginTop: '1.5rem' }}>
                <div
                    style={{
                        background: 'linear-gradient(135deg, #f59e0b, #d97706)',
                        color: 'white',
                        padding: '0.8rem 1rem',
                        borderRadius: '8px',
                        marginBottom: '0.8rem',
                        cursor: 'pointer',
                    }}
                    onClick={() => toggleSection('ram')}
                >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                            <span style={{ fontWeight: '600' }}>RAM (메모리)</span>
                        </div>
                        <span>{expandedSections.ram ? '▲' : '▼'}</span>
                    </div>
                </div>
                {expandedSections.ram && (
                    <div style={{ padding: '1rem', background: '#f8fafc', borderRadius: '8px' }}>
                        <div
                            style={{ fontSize: '0.75rem', color: '#64748b', marginBottom: '1rem', fontStyle: 'italic' }}
                        >
                            멀티태스킹 성능에 직접 영향. 메인보드 지원 세대 확인
                        </div>

                        {/* 핵심 필터 */}
                        <div style={{ marginBottom: '1rem', paddingBottom: '1rem', borderBottom: '1px solid #e2e8f0' }}>
                            <div
                                style={{
                                    fontSize: '0.8rem',
                                    fontWeight: '700',
                                    color: '#1e293b',
                                    marginBottom: '0.8rem',
                                }}
                            >
                                핵심 필터
                            </div>

                            {/* RAM 세대 - 라디오 */}
                            <div style={{ marginBottom: '1rem' }}>
                                <label
                                    style={{
                                        fontSize: '0.8rem',
                                        fontWeight: '600',
                                        marginBottom: '0.5rem',
                                        display: 'block',
                                    }}
                                >
                                    RAM 세대
                                </label>
                                <div className="form-radio">
                                    <input
                                        type="radio"
                                        name="ramGen"
                                        value=""
                                        checked={ramGen === ''}
                                        onChange={(e) => setRamGen(e.target.value)}
                                    />
                                    <span style={{ fontSize: '0.8rem' }}>상관없음</span>
                                </div>
                                {['DDR5', 'DDR4'].map((gen) => (
                                    <div key={gen} className="form-radio">
                                        <input
                                            type="radio"
                                            name="ramGen"
                                            value={gen}
                                            checked={ramGen === gen}
                                            onChange={(e) => setRamGen(e.target.value)}
                                        />
                                        <span style={{ fontSize: '0.8rem' }}>{gen}</span>
                                    </div>
                                ))}
                            </div>

                            {/* 용량 - 라디오 */}
                            <div>
                                <label
                                    style={{
                                        fontSize: '0.8rem',
                                        fontWeight: '600',
                                        marginBottom: '0.5rem',
                                        display: 'block',
                                    }}
                                >
                                    용량
                                </label>
                                <div className="form-radio">
                                    <input
                                        type="radio"
                                        name="ramCapacity"
                                        value=""
                                        checked={ramCapacity === ''}
                                        onChange={(e) => setRamCapacity(e.target.value)}
                                    />
                                    <span style={{ fontSize: '0.8rem' }}>상관없음</span>
                                </div>
                                {['8GB', '16GB', '32GB', '64GB', '128GB+'].map((cap) => (
                                    <div key={cap} className="form-radio">
                                        <input
                                            type="radio"
                                            name="ramCapacity"
                                            value={cap}
                                            checked={ramCapacity === cap}
                                            onChange={(e) => setRamCapacity(e.target.value)}
                                        />
                                        <span style={{ fontSize: '0.8rem' }}>{cap}</span>
                                    </div>
                                ))}
                            </div>
                        </div>

                        {/* 자세히 ▼ */}
                        <div>
                            <button
                                onClick={() => toggleDetails('ram')}
                                style={{
                                    width: '100%',
                                    padding: '0.6rem',
                                    background: expandedDetails.ram ? '#e0e7ff' : '#f1f5f9',
                                    color: expandedDetails.ram ? '#4338ca' : '#64748b',
                                    border: 'none',
                                    borderRadius: '6px',
                                    fontSize: '0.8rem',
                                    fontWeight: '600',
                                    cursor: 'pointer',
                                    transition: 'all 0.2s',
                                    marginBottom: '0.8rem',
                                }}
                            >
                                {expandedDetails.ram ? '▲ 자세히 접기' : '▼ 자세히 펼치기'}
                            </button>

                            {expandedDetails.ram && (
                                <div style={{ paddingTop: '0.5rem' }}>
                                    {/* 속도 */}
                                    <div style={{ marginBottom: '1rem' }}>
                                        <label
                                            style={{
                                                fontSize: '0.8rem',
                                                fontWeight: '600',
                                                marginBottom: '0.5rem',
                                                display: 'block',
                                            }}
                                        >
                                            클럭 속도
                                        </label>
                                        {['3200MHz', '3600MHz', '4800MHz', '5600MHz', '6000MHz+'].map((speed) => (
                                            <div key={speed} className="form-checkbox">
                                                <input
                                                    type="checkbox"
                                                    checked={ramSpeed.includes(speed)}
                                                    onChange={(e) => {
                                                        if (e.target.checked) {
                                                            setRamSpeed([...ramSpeed, speed]);
                                                        } else {
                                                            setRamSpeed(ramSpeed.filter((s) => s !== speed));
                                                        }
                                                    }}
                                                />
                                                <span style={{ fontSize: '0.8rem' }}>{speed}</span>
                                            </div>
                                        ))}
                                    </div>

                                    {/* XMP/EXPO */}
                                    <div>
                                        <label
                                            style={{
                                                fontSize: '0.8rem',
                                                fontWeight: '600',
                                                marginBottom: '0.5rem',
                                                display: 'block',
                                            }}
                                        >
                                            XMP / EXPO 지원
                                        </label>
                                        <div className="form-radio">
                                            <input
                                                type="radio"
                                                name="ramXmp"
                                                value="any"
                                                checked={ramXmp === 'any'}
                                                onChange={(e) => setRamXmp(e.target.value)}
                                            />
                                            <span style={{ fontSize: '0.8rem' }}>상관없음</span>
                                        </div>
                                        <div className="form-radio">
                                            <input
                                                type="radio"
                                                name="ramXmp"
                                                value="yes"
                                                checked={ramXmp === 'yes'}
                                                onChange={(e) => setRamXmp(e.target.value)}
                                            />
                                            <span style={{ fontSize: '0.8rem' }}>오버클럭 지원 필수</span>
                                        </div>
                                    </div>
                                </div>
                            )}
                        </div>
                    </div>
                )}
            </div>

            {/* 🎮 GPU (그래픽카드) */}
            <div className="form-group" style={{ marginTop: '1.5rem' }}>
                <div
                    style={{
                        background: 'linear-gradient(135deg, #ef4444, #dc2626)',
                        color: 'white',
                        padding: '0.8rem 1rem',
                        borderRadius: '8px',
                        marginBottom: '0.8rem',
                        cursor: 'pointer',
                    }}
                    onClick={() => toggleSection('gpu')}
                >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                            <span style={{ fontWeight: '600' }}>GPU (그래픽카드)</span>
                        </div>
                        <span>{expandedSections.gpu ? '▲' : '▼'}</span>
                    </div>
                </div>
                {expandedSections.gpu && (
                    <div style={{ padding: '1rem', background: '#f8fafc', borderRadius: '8px' }}>
                        <div
                            style={{ fontSize: '0.75rem', color: '#64748b', marginBottom: '1rem', fontStyle: 'italic' }}
                        >
                            게임/렌더링 성능의 핵심. 케이스 길이와 파워 용량 확인 필수
                        </div>

                        {/* 핵심 필터 */}
                        <div style={{ marginBottom: '1rem', paddingBottom: '1rem', borderBottom: '1px solid #e2e8f0' }}>
                            <div
                                style={{
                                    fontSize: '0.8rem',
                                    fontWeight: '700',
                                    color: '#1e293b',
                                    marginBottom: '0.8rem',
                                }}
                            >
                                핵심 필터
                            </div>

                            {/* VRAM - 라디오 */}
                            <div>
                                <label
                                    style={{
                                        fontSize: '0.8rem',
                                        fontWeight: '600',
                                        marginBottom: '0.5rem',
                                        display: 'block',
                                    }}
                                >
                                    VRAM (비디오 메모리)
                                </label>
                                <div className="form-radio">
                                    <input
                                        type="radio"
                                        name="gpuVram"
                                        value=""
                                        checked={gpuVram === ''}
                                        onChange={(e) => setGpuVram(e.target.value)}
                                    />
                                    <span style={{ fontSize: '0.8rem' }}>상관없음</span>
                                </div>
                                {['4GB', '6GB', '8GB', '12GB', '16GB', '24GB+'].map((vram) => (
                                    <div key={vram} className="form-radio">
                                        <input
                                            type="radio"
                                            name="gpuVram"
                                            value={vram}
                                            checked={gpuVram === vram}
                                            onChange={(e) => setGpuVram(e.target.value)}
                                        />
                                        <span style={{ fontSize: '0.8rem' }}>{vram}</span>
                                    </div>
                                ))}
                            </div>
                        </div>

                        {/* 자세히 ▼ */}
                        <div>
                            <button
                                onClick={() => toggleDetails('gpu')}
                                style={{
                                    width: '100%',
                                    padding: '0.6rem',
                                    background: expandedDetails.gpu ? '#e0e7ff' : '#f1f5f9',
                                    color: expandedDetails.gpu ? '#4338ca' : '#64748b',
                                    border: 'none',
                                    borderRadius: '6px',
                                    fontSize: '0.8rem',
                                    fontWeight: '600',
                                    cursor: 'pointer',
                                    transition: 'all 0.2s',
                                    marginBottom: '0.8rem',
                                }}
                            >
                                {expandedDetails.gpu ? '▲ 자세히 접기' : '▼ 자세히 펼치기'}
                            </button>

                            {expandedDetails.gpu && (
                                <div style={{ paddingTop: '0.5rem' }}>
                                    {/* 최대 전력 */}
                                    <div style={{ marginBottom: '1rem' }}>
                                        <label
                                            style={{
                                                fontSize: '0.8rem',
                                                fontWeight: '600',
                                                marginBottom: '0.5rem',
                                                display: 'block',
                                            }}
                                        >
                                            최대 전력 소비: {gpuPower}W 이하
                                        </label>
                                        <input
                                            type="range"
                                            min="75"
                                            max="450"
                                            step="25"
                                            value={gpuPower}
                                            onChange={(e) => setGpuPower(parseInt(e.target.value))}
                                            style={{ width: '100%' }}
                                        />
                                    </div>

                                    {/* 최대 길이 */}
                                    <div style={{ marginBottom: '1rem' }}>
                                        <label
                                            style={{
                                                fontSize: '0.8rem',
                                                fontWeight: '600',
                                                marginBottom: '0.5rem',
                                                display: 'block',
                                            }}
                                        >
                                            최대 카드 길이: {gpuLength}mm 이하
                                        </label>
                                        <input
                                            type="range"
                                            min="150"
                                            max="400"
                                            step="10"
                                            value={gpuLength}
                                            onChange={(e) => setGpuLength(parseInt(e.target.value))}
                                            style={{ width: '100%' }}
                                        />
                                    </div>

                                    {/* 🆕 GPU 두께 (슬롯) */}
                                    <div style={{ marginBottom: '1rem' }}>
                                        <label
                                            style={{
                                                fontSize: '0.8rem',
                                                fontWeight: '600',
                                                marginBottom: '0.5rem',
                                                display: 'block',
                                            }}
                                        >
                                            GPU 두께: {gpuSlots}슬롯
                                        </label>
                                        <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
                                            <span style={{ fontSize: '0.7rem', color: '#64748b' }}>2슬롯</span>
                                            <input
                                                type="range"
                                                min="2"
                                                max="4"
                                                step="0.5"
                                                value={gpuSlots}
                                                onChange={(e) => setGpuSlots(parseFloat(e.target.value))}
                                                style={{ flex: 1 }}
                                            />
                                            <span style={{ fontSize: '0.7rem', color: '#64748b' }}>4슬롯</span>
                                        </div>
                                    </div>

                                    {/* 🆕 GPU 전원 커넥터 */}
                                    <div style={{ marginBottom: '1rem' }}>
                                        <label
                                            style={{
                                                fontSize: '0.8rem',
                                                fontWeight: '600',
                                                marginBottom: '0.5rem',
                                                display: 'block',
                                            }}
                                        >
                                            GPU 전원 커넥터
                                        </label>
                                        <div className="form-radio">
                                            <input
                                                type="radio"
                                                name="gpuConnector"
                                                value=""
                                                checked={gpuConnector === ''}
                                                onChange={(e) => setGpuConnector(e.target.value)}
                                            />
                                            <span style={{ fontSize: '0.8rem' }}>상관없음</span>
                                        </div>
                                        <div className="form-radio">
                                            <input
                                                type="radio"
                                                name="gpuConnector"
                                                value="8pin x1"
                                                checked={gpuConnector === '8pin x1'}
                                                onChange={(e) => setGpuConnector(e.target.value)}
                                            />
                                            <span style={{ fontSize: '0.8rem' }}>8pin x1</span>
                                        </div>
                                        <div className="form-radio">
                                            <input
                                                type="radio"
                                                name="gpuConnector"
                                                value="8pin x2"
                                                checked={gpuConnector === '8pin x2'}
                                                onChange={(e) => setGpuConnector(e.target.value)}
                                            />
                                            <span style={{ fontSize: '0.8rem' }}>8pin x2</span>
                                        </div>
                                        <div className="form-radio">
                                            <input
                                                type="radio"
                                                name="gpuConnector"
                                                value="8pin x3"
                                                checked={gpuConnector === '8pin x3'}
                                                onChange={(e) => setGpuConnector(e.target.value)}
                                            />
                                            <span style={{ fontSize: '0.8rem' }}>8pin x3</span>
                                        </div>
                                        <div className="form-radio">
                                            <input
                                                type="radio"
                                                name="gpuConnector"
                                                value="12VHPWR"
                                                checked={gpuConnector === '12VHPWR'}
                                                onChange={(e) => setGpuConnector(e.target.value)}
                                            />
                                            <span style={{ fontSize: '0.8rem' }}>12VHPWR (RTX 40)</span>
                                        </div>
                                    </div>

                                    {/* 백플레이트 */}
                                    <div>
                                        <label
                                            style={{
                                                fontSize: '0.8rem',
                                                fontWeight: '600',
                                                marginBottom: '0.5rem',
                                                display: 'block',
                                            }}
                                        >
                                            백플레이트 (금속 보강판)
                                        </label>
                                        <div className="form-radio">
                                            <input
                                                type="radio"
                                                name="gpuBackplate"
                                                value="any"
                                                checked={gpuBackplate === 'any'}
                                                onChange={(e) => setGpuBackplate(e.target.value)}
                                            />
                                            <span style={{ fontSize: '0.8rem' }}>상관없음</span>
                                        </div>
                                        <div className="form-radio">
                                            <input
                                                type="radio"
                                                name="gpuBackplate"
                                                value="yes"
                                                checked={gpuBackplate === 'yes'}
                                                onChange={(e) => setGpuBackplate(e.target.value)}
                                            />
                                            <span style={{ fontSize: '0.8rem' }}>백플레이트 필수</span>
                                        </div>
                                    </div>
                                </div>
                            )}
                        </div>
                    </div>
                )}
            </div>

            {/* ⚡ PSU (파워서플라이) */}
            <div className="form-group" style={{ marginTop: '1.5rem' }}>
                <div
                    style={{
                        background: 'linear-gradient(135deg, #8b5cf6, #7c3aed)',
                        color: 'white',
                        padding: '0.8rem 1rem',
                        borderRadius: '8px',
                        marginBottom: '0.8rem',
                        cursor: 'pointer',
                    }}
                    onClick={() => toggleSection('psu')}
                >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                            <span style={{ fontWeight: '600' }}>PSU (파워서플라이)</span>
                        </div>
                        <span>{expandedSections.psu ? '▲' : '▼'}</span>
                    </div>
                </div>
                {expandedSections.psu && (
                    <div style={{ padding: '1rem', background: '#f8fafc', borderRadius: '8px' }}>
                        <div
                            style={{ fontSize: '0.75rem', color: '#64748b', marginBottom: '1rem', fontStyle: 'italic' }}
                        >
                            안정적 전력 공급. CPU+GPU 소비 전력의 150% 권장
                        </div>

                        {/* 용량 */}
                        <div style={{ marginBottom: '1rem' }}>
                            <label
                                style={{
                                    fontSize: '0.8rem',
                                    fontWeight: '600',
                                    marginBottom: '0.5rem',
                                    display: 'block',
                                }}
                            >
                                용량 (Wattage)
                            </label>
                            {['550W', '650W', '750W', '850W', '1000W', '1200W+'].map((watt) => (
                                <div key={watt} className="form-checkbox">
                                    <input
                                        type="checkbox"
                                        checked={psuWattage.includes(watt)}
                                        onChange={(e) => {
                                            if (e.target.checked) {
                                                setPsuWattage([...psuWattage, watt]);
                                            } else {
                                                setPsuWattage(psuWattage.filter((w) => w !== watt));
                                            }
                                        }}
                                    />
                                    <span style={{ fontSize: '0.8rem' }}>{watt}</span>
                                </div>
                            ))}
                        </div>

                        {/* 효율 등급 */}
                        <div style={{ marginBottom: '1rem' }}>
                            <label
                                style={{
                                    fontSize: '0.8rem',
                                    fontWeight: '600',
                                    marginBottom: '0.5rem',
                                    display: 'block',
                                }}
                            >
                                80 PLUS 인증
                            </label>
                            {['White', 'Bronze', 'Silver', 'Gold', 'Platinum', 'Titanium'].map((eff) => (
                                <div key={eff} className="form-checkbox">
                                    <input
                                        type="checkbox"
                                        checked={psuEfficiency.includes(eff)}
                                        onChange={(e) => {
                                            if (e.target.checked) {
                                                setPsuEfficiency([...psuEfficiency, eff]);
                                            } else {
                                                setPsuEfficiency(psuEfficiency.filter((e) => e !== eff));
                                            }
                                        }}
                                    />
                                    <span style={{ fontSize: '0.8rem' }}>80+ {eff}</span>
                                </div>
                            ))}
                        </div>

                        {/* 🆕 PSU 폼팩터 (크기) */}
                        <div style={{ marginBottom: '1rem' }}>
                            <label
                                style={{
                                    fontSize: '0.8rem',
                                    fontWeight: '600',
                                    marginBottom: '0.5rem',
                                    display: 'block',
                                }}
                            >
                                PSU 크기
                            </label>
                            <div className="form-radio">
                                <input
                                    type="radio"
                                    name="psuFormFactor"
                                    value=""
                                    checked={psuFormFactor === ''}
                                    onChange={(e) => setPsuFormFactor(e.target.value)}
                                />
                                <span style={{ fontSize: '0.8rem' }}>상관없음</span>
                            </div>
                            <div className="form-radio">
                                <input
                                    type="radio"
                                    name="psuFormFactor"
                                    value="ATX"
                                    checked={psuFormFactor === 'ATX'}
                                    onChange={(e) => setPsuFormFactor(e.target.value)}
                                />
                                <span style={{ fontSize: '0.8rem' }}>ATX (표준)</span>
                            </div>
                            <div className="form-radio">
                                <input
                                    type="radio"
                                    name="psuFormFactor"
                                    value="SFX"
                                    checked={psuFormFactor === 'SFX'}
                                    onChange={(e) => setPsuFormFactor(e.target.value)}
                                />
                                <span style={{ fontSize: '0.8rem' }}>SFX (소형)</span>
                            </div>
                            <div className="form-radio">
                                <input
                                    type="radio"
                                    name="psuFormFactor"
                                    value="SFX-L"
                                    checked={psuFormFactor === 'SFX-L'}
                                    onChange={(e) => setPsuFormFactor(e.target.value)}
                                />
                                <span style={{ fontSize: '0.8rem' }}>SFX-L (중형)</span>
                            </div>
                        </div>

                        {/* 🆕 PSU 커넥터 지원 */}
                        <div style={{ marginBottom: '1rem' }}>
                            <label
                                style={{
                                    fontSize: '0.8rem',
                                    fontWeight: '600',
                                    marginBottom: '0.5rem',
                                    display: 'block',
                                }}
                            >
                                PSU 커넥터 지원
                            </label>
                            {['8pin x2', '8pin x3', '8pin x4', '12VHPWR'].map((conn) => (
                                <div key={conn} className="form-checkbox">
                                    <input
                                        type="checkbox"
                                        checked={psuConnectors.includes(conn)}
                                        onChange={(e) => {
                                            if (e.target.checked) {
                                                setPsuConnectors([...psuConnectors, conn]);
                                            } else {
                                                setPsuConnectors(psuConnectors.filter((c) => c !== conn));
                                            }
                                        }}
                                    />
                                    <span style={{ fontSize: '0.8rem' }}>{conn}</span>
                                </div>
                            ))}
                        </div>

                        {/* 케이블 타입 */}
                        <div>
                            <label
                                style={{
                                    fontSize: '0.8rem',
                                    fontWeight: '600',
                                    marginBottom: '0.5rem',
                                    display: 'block',
                                }}
                            >
                                케이블 타입
                            </label>
                            {['모듈러 (풀)', '세미 모듈러', '논모듈러'].map((cable) => (
                                <div key={cable} className="form-checkbox">
                                    <input
                                        type="checkbox"
                                        checked={psuCableType.includes(cable)}
                                        onChange={(e) => {
                                            if (e.target.checked) {
                                                setPsuCableType([...psuCableType, cable]);
                                            } else {
                                                setPsuCableType(psuCableType.filter((c) => c !== cable));
                                            }
                                        }}
                                    />
                                    <span style={{ fontSize: '0.8rem' }}>{cable}</span>
                                </div>
                            ))}
                        </div>
                    </div>
                )}
            </div>

            {/* 📦 케이스 */}
            <div className="form-group" style={{ marginTop: '1.5rem' }}>
                <div
                    style={{
                        background: 'linear-gradient(135deg, #64748b, #475569)',
                        color: 'white',
                        padding: '0.8rem 1rem',
                        borderRadius: '8px',
                        marginBottom: '0.8rem',
                        cursor: 'pointer',
                    }}
                    onClick={() => toggleSection('case')}
                >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                            <span style={{ fontWeight: '600' }}>케이스 (PC 외형)</span>
                        </div>
                        <span>{expandedSections.case ? '▲' : '▼'}</span>
                    </div>
                </div>
                {expandedSections.case && (
                    <div style={{ padding: '1rem', background: '#f8fafc', borderRadius: '8px' }}>
                        <div
                            style={{ fontSize: '0.75rem', color: '#64748b', marginBottom: '1rem', fontStyle: 'italic' }}
                        >
                            모든 부품을 담는 외형. 메인보드/GPU/쿨러 크기 호환 확인
                        </div>

                        {/* 케이스 타입 */}
                        <div style={{ marginBottom: '1rem' }}>
                            <label
                                style={{
                                    fontSize: '0.8rem',
                                    fontWeight: '600',
                                    marginBottom: '0.5rem',
                                    display: 'block',
                                }}
                            >
                                케이스 크기
                            </label>
                            {['풀타워', '미들타워', '미니타워', 'SFF (소형)'].map((type) => (
                                <div key={type} className="form-checkbox">
                                    <input
                                        type="checkbox"
                                        checked={caseType.includes(type)}
                                        onChange={(e) => {
                                            if (e.target.checked) {
                                                setCaseType([...caseType, type]);
                                            } else {
                                                setCaseType(caseType.filter((t) => t !== type));
                                            }
                                        }}
                                    />
                                    <span style={{ fontSize: '0.8rem' }}>{type}</span>
                                </div>
                            ))}
                        </div>

                        {/* 메인보드 호환 */}
                        <div style={{ marginBottom: '1rem' }}>
                            <label
                                style={{
                                    fontSize: '0.8rem',
                                    fontWeight: '600',
                                    marginBottom: '0.5rem',
                                    display: 'block',
                                }}
                            >
                                메인보드 지원
                            </label>
                            {['E-ATX', 'ATX', 'M-ATX', 'Mini-ITX'].map((board) => (
                                <div key={board} className="form-checkbox">
                                    <input
                                        type="checkbox"
                                        checked={caseBoardSupport.includes(board)}
                                        onChange={(e) => {
                                            if (e.target.checked) {
                                                setCaseBoardSupport([...caseBoardSupport, board]);
                                            } else {
                                                setCaseBoardSupport(caseBoardSupport.filter((b) => b !== board));
                                            }
                                        }}
                                    />
                                    <span style={{ fontSize: '0.8rem' }}>{board}</span>
                                </div>
                            ))}
                        </div>

                        {/* 🆕 PSU 지원 크기 */}
                        <div style={{ marginBottom: '1rem' }}>
                            <label
                                style={{
                                    fontSize: '0.8rem',
                                    fontWeight: '600',
                                    marginBottom: '0.5rem',
                                    display: 'block',
                                }}
                            >
                                PSU 크기 지원
                            </label>
                            {['ATX', 'SFX', 'SFX-L'].map((psu) => (
                                <div key={psu} className="form-checkbox">
                                    <input
                                        type="checkbox"
                                        checked={casePsuSupport.includes(psu)}
                                        onChange={(e) => {
                                            if (e.target.checked) {
                                                setCasePsuSupport([...casePsuSupport, psu]);
                                            } else {
                                                setCasePsuSupport(casePsuSupport.filter((p) => p !== psu));
                                            }
                                        }}
                                    />
                                    <span style={{ fontSize: '0.8rem' }}>{psu}</span>
                                </div>
                            ))}
                        </div>

                        {/* GPU 최대 길이 */}
                        <div style={{ marginBottom: '1rem' }}>
                            <label
                                style={{
                                    fontSize: '0.8rem',
                                    fontWeight: '600',
                                    marginBottom: '0.5rem',
                                    display: 'block',
                                }}
                            >
                                GPU 최대 길이: {caseGpuLength}mm
                            </label>
                            <input
                                type="range"
                                min="200"
                                max="450"
                                step="10"
                                value={caseGpuLength}
                                onChange={(e) => setCaseGpuLength(parseInt(e.target.value))}
                                style={{ width: '100%' }}
                            />
                        </div>

                        {/* 🆕 GPU 최대 슬롯 수 */}
                        <div style={{ marginBottom: '1rem' }}>
                            <label
                                style={{
                                    fontSize: '0.8rem',
                                    fontWeight: '600',
                                    marginBottom: '0.5rem',
                                    display: 'block',
                                }}
                            >
                                GPU 최대 슬롯 수: {caseGpuSlots}슬롯
                            </label>
                            <input
                                type="range"
                                min="2"
                                max="5"
                                step="0.5"
                                value={caseGpuSlots}
                                onChange={(e) => setCaseGpuSlots(parseFloat(e.target.value))}
                                style={{ width: '100%' }}
                            />
                        </div>

                        {/* 쿨러 최대 높이 */}
                        <div style={{ marginBottom: '1rem' }}>
                            <label
                                style={{
                                    fontSize: '0.8rem',
                                    fontWeight: '600',
                                    marginBottom: '0.5rem',
                                    display: 'block',
                                }}
                            >
                                쿨러 최대 높이: {caseCoolerHeight}mm
                            </label>
                            <input
                                type="range"
                                min="100"
                                max="200"
                                step="10"
                                value={caseCoolerHeight}
                                onChange={(e) => setCaseCoolerHeight(parseInt(e.target.value))}
                                style={{ width: '100%' }}
                            />
                        </div>

                        {/* 에어플로우 */}
                        <div style={{ marginBottom: '1rem' }}>
                            <label
                                style={{
                                    fontSize: '0.8rem',
                                    fontWeight: '600',
                                    marginBottom: '0.5rem',
                                    display: 'block',
                                }}
                            >
                                에어플로우 타입
                            </label>
                            {['메쉬 (통풍 최고)', '밀폐형 (조용함)', '하이브리드'].map((airflow) => (
                                <div key={airflow} className="form-checkbox">
                                    <input
                                        type="checkbox"
                                        checked={caseAirflow.includes(airflow)}
                                        onChange={(e) => {
                                            if (e.target.checked) {
                                                setCaseAirflow([...caseAirflow, airflow]);
                                            } else {
                                                setCaseAirflow(caseAirflow.filter((a) => a !== airflow));
                                            }
                                        }}
                                    />
                                    <span style={{ fontSize: '0.8rem' }}>{airflow}</span>
                                </div>
                            ))}
                        </div>

                        {/* 강화유리 */}
                        <div style={{ marginBottom: '1rem' }}>
                            <label
                                style={{
                                    fontSize: '0.8rem',
                                    fontWeight: '600',
                                    marginBottom: '0.5rem',
                                    display: 'block',
                                }}
                            >
                                강화유리 패널
                            </label>
                            <div className="form-radio">
                                <input
                                    type="radio"
                                    name="caseGlass"
                                    value="any"
                                    checked={caseGlass === 'any'}
                                    onChange={(e) => setCaseGlass(e.target.value)}
                                />
                                <span style={{ fontSize: '0.8rem' }}>상관없음</span>
                            </div>
                            <div className="form-radio">
                                <input
                                    type="radio"
                                    name="caseGlass"
                                    value="yes"
                                    checked={caseGlass === 'yes'}
                                    onChange={(e) => setCaseGlass(e.target.value)}
                                />
                                <span style={{ fontSize: '0.8rem' }}>강화유리 필수</span>
                            </div>
                            <div className="form-radio">
                                <input
                                    type="radio"
                                    name="caseGlass"
                                    value="no"
                                    checked={caseGlass === 'no'}
                                    onChange={(e) => setCaseGlass(e.target.value)}
                                />
                                <span style={{ fontSize: '0.8rem' }}>밀폐형 선호</span>
                            </div>
                        </div>

                        {/* 케이스 환경 */}
                        <div style={{ marginBottom: '1rem' }}>
                            <label
                                style={{
                                    fontSize: '0.8rem',
                                    fontWeight: '600',
                                    marginBottom: '0.5rem',
                                    display: 'block',
                                }}
                            >
                                케이스 환경
                            </label>
                            <div className="form-radio">
                                <input
                                    type="radio"
                                    name="caseEnvironment"
                                    value="balanced"
                                    checked={caseEnvironment === 'balanced'}
                                    onChange={(e) => setCaseEnvironment(e.target.value)}
                                />
                                <span style={{ fontSize: '0.8rem' }}>균형형 (표준)</span>
                            </div>
                            <div className="form-radio">
                                <input
                                    type="radio"
                                    name="caseEnvironment"
                                    value="silent"
                                    checked={caseEnvironment === 'silent'}
                                    onChange={(e) => setCaseEnvironment(e.target.value)}
                                />
                                <span style={{ fontSize: '0.8rem' }}>저소음 우선</span>
                            </div>
                            <div className="form-radio">
                                <input
                                    type="radio"
                                    name="caseEnvironment"
                                    value="cooling"
                                    checked={caseEnvironment === 'cooling'}
                                    onChange={(e) => setCaseEnvironment(e.target.value)}
                                />
                                <span style={{ fontSize: '0.8rem' }}>쿨링 우선</span>
                            </div>
                        </div>

                        {/* RGB 선호 */}
                        <div>
                            <label
                                style={{
                                    fontSize: '0.8rem',
                                    fontWeight: '600',
                                    marginBottom: '0.5rem',
                                    display: 'block',
                                }}
                            >
                                RGB 조명 선호도
                            </label>
                            <div className="form-radio">
                                <input
                                    type="radio"
                                    name="rgbPreference"
                                    value="any"
                                    checked={rgbPreference === 'any'}
                                    onChange={(e) => setRgbPreference(e.target.value)}
                                />
                                <span style={{ fontSize: '0.8rem' }}>상관없음</span>
                            </div>
                            <div className="form-radio">
                                <input
                                    type="radio"
                                    name="rgbPreference"
                                    value="yes"
                                    checked={rgbPreference === 'yes'}
                                    onChange={(e) => setRgbPreference(e.target.value)}
                                />
                                <span style={{ fontSize: '0.8rem' }}>RGB 화려하게</span>
                            </div>
                            <div className="form-radio">
                                <input
                                    type="radio"
                                    name="rgbPreference"
                                    value="no"
                                    checked={rgbPreference === 'no'}
                                    onChange={(e) => setRgbPreference(e.target.value)}
                                />
                                <span style={{ fontSize: '0.8rem' }}>RGB 최소화</span>
                            </div>
                        </div>
                    </div>
                )}
            </div>

            {/* 💿 저장장치 */}
            <div className="form-group" style={{ marginTop: '1.5rem' }}>
                <div
                    style={{
                        background: 'linear-gradient(135deg, #14b8a6, #0d9488)',
                        color: 'white',
                        padding: '0.8rem 1rem',
                        borderRadius: '8px',
                        marginBottom: '0.8rem',
                        cursor: 'pointer',
                    }}
                    onClick={() => toggleSection('storage')}
                >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                            <span style={{ fontWeight: '600' }}>저장장치 (SSD / HDD)</span>
                        </div>
                        <span>{expandedSections.storage ? '▲' : '▼'}</span>
                    </div>
                </div>
                {expandedSections.storage && (
                    <div style={{ padding: '1rem', background: '#f8fafc', borderRadius: '8px' }}>
                        <div
                            style={{ fontSize: '0.75rem', color: '#64748b', marginBottom: '1rem', fontStyle: 'italic' }}
                        >
                            OS 및 데이터 보관. SSD는 속도, HDD는 대용량에 유리
                        </div>

                        {/* SSD 인터페이스 */}
                        <div style={{ marginBottom: '1rem' }}>
                            <label
                                style={{
                                    fontSize: '0.8rem',
                                    fontWeight: '600',
                                    marginBottom: '0.5rem',
                                    display: 'block',
                                }}
                            >
                                SSD 인터페이스
                            </label>
                            {['NVMe M.2 (Gen4)', 'NVMe M.2 (Gen3)', 'SATA'].map((inter) => (
                                <div key={inter} className="form-checkbox">
                                    <input
                                        type="checkbox"
                                        checked={ssdInterface.includes(inter)}
                                        onChange={(e) => {
                                            if (e.target.checked) {
                                                setSsdInterface([...ssdInterface, inter]);
                                            } else {
                                                setSsdInterface(ssdInterface.filter((i) => i !== inter));
                                            }
                                        }}
                                    />
                                    <span style={{ fontSize: '0.8rem' }}>{inter}</span>
                                </div>
                            ))}
                        </div>

                        {/* SSD 용량 */}
                        <div style={{ marginBottom: '1rem' }}>
                            <label
                                style={{
                                    fontSize: '0.8rem',
                                    fontWeight: '600',
                                    marginBottom: '0.5rem',
                                    display: 'block',
                                }}
                            >
                                SSD 용량
                            </label>
                            {['256GB', '512GB', '1TB', '2TB', '4TB+'].map((cap) => (
                                <div key={cap} className="form-checkbox">
                                    <input
                                        type="checkbox"
                                        checked={ssdCapacity.includes(cap)}
                                        onChange={(e) => {
                                            if (e.target.checked) {
                                                setSsdCapacity([...ssdCapacity, cap]);
                                            } else {
                                                setSsdCapacity(ssdCapacity.filter((c) => c !== cap));
                                            }
                                        }}
                                    />
                                    <span style={{ fontSize: '0.8rem' }}>{cap}</span>
                                </div>
                            ))}
                        </div>

                        {/* DRAM 캐시 */}
                        <div>
                            <label
                                style={{
                                    fontSize: '0.8rem',
                                    fontWeight: '600',
                                    marginBottom: '0.5rem',
                                    display: 'block',
                                }}
                            >
                                DRAM 캐시 (내구성/성능)
                            </label>
                            <div className="form-radio">
                                <input
                                    type="radio"
                                    name="ssdDram"
                                    value="any"
                                    checked={ssdDram === 'any'}
                                    onChange={(e) => setSsdDram(e.target.value)}
                                />
                                <span style={{ fontSize: '0.8rem' }}>상관없음</span>
                            </div>
                            <div className="form-radio">
                                <input
                                    type="radio"
                                    name="ssdDram"
                                    value="yes"
                                    checked={ssdDram === 'yes'}
                                    onChange={(e) => setSsdDram(e.target.value)}
                                />
                                <span style={{ fontSize: '0.8rem' }}>DRAM 캐시 필수</span>
                            </div>
                        </div>
                    </div>
                )}
            </div>

            {/* 💰 예산 관리 (항상 열림) */}
            <div className="form-group" style={{ marginTop: '1.5rem' }}>
                <div
                    style={{
                        background: 'linear-gradient(135deg, #10b981, #059669)',
                        color: 'white',
                        padding: '0.8rem 1rem',
                        borderRadius: '8px',
                        marginBottom: '0.8rem',
                    }}
                >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                            <span style={{ fontWeight: '600' }}>예산 관리</span>
                        </div>
                    </div>
                </div>
                <div style={{ padding: '1rem', background: '#f8fafc', borderRadius: '8px' }}>
                    {/* 최소/최대 예산 입력 필드 */}
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '1rem' }}>
                        <div style={{ flex: 1, marginRight: '0.5rem' }}>
                            <label
                                style={{
                                    fontSize: '0.75rem',
                                    color: '#64748b',
                                    marginBottom: '0.3rem',
                                    display: 'block',
                                }}
                            >
                                최소 예산
                            </label>
                            <input
                                type="text"
                                value={`₩${budgetMin.toLocaleString()}`}
                                onChange={(e) => {
                                    const val = parseInt(e.target.value.replace(/[^0-9]/g, '')) || 500000;
                                    setBudgetMin(val);
                                    if (currentBudget < val) setCurrentBudget(val);
                                }}
                                style={{
                                    width: '100%',
                                    padding: '0.5rem',
                                    border: '1px solid #cbd5e1',
                                    borderRadius: '6px',
                                    fontSize: '0.9rem',
                                    fontWeight: '600',
                                }}
                            />
                        </div>
                        <div style={{ flex: 1, marginLeft: '0.5rem' }}>
                            <label
                                style={{
                                    fontSize: '0.75rem',
                                    color: '#64748b',
                                    marginBottom: '0.3rem',
                                    display: 'block',
                                }}
                            >
                                최대 예산
                            </label>
                            <input
                                type="text"
                                value={`₩${budgetMax.toLocaleString()}`}
                                onChange={(e) => {
                                    const val = parseInt(e.target.value.replace(/[^0-9]/g, '')) || 5000000;
                                    setBudgetMax(val);
                                    if (currentBudget > val) setCurrentBudget(val);
                                }}
                                style={{
                                    width: '100%',
                                    padding: '0.5rem',
                                    border: '1px solid #cbd5e1',
                                    borderRadius: '6px',
                                    fontSize: '0.9rem',
                                    fontWeight: '600',
                                }}
                            />
                        </div>
                    </div>

                    {/* 현재 예산 슬라이더 */}
                    <div style={{ marginBottom: '0.8rem' }}>
                        <div style={{ fontSize: '0.85rem', color: '#64748b', marginBottom: '0.3rem' }}>
                            현재 예산:{' '}
                            <span style={{ fontWeight: '700', color: '#2563eb' }}>
                                ₩{currentBudget.toLocaleString()}
                            </span>
                        </div>
                        <input
                            type="range"
                            min={budgetMin}
                            max={budgetMax}
                            step="50000"
                            value={currentBudget}
                            onChange={(e) => setCurrentBudget(parseInt(e.target.value))}
                            style={{ width: '100%' }}
                        />
                    </div>
                    <div style={{ fontSize: '0.7rem', color: '#94a3b8', marginTop: '0.5rem', fontStyle: 'italic' }}>
                        💡 예산을 직접 입력하세요 (예: 2,500,000)
                    </div>

                    {/* 총합/남은 예산 표시 */}
                    <div
                        style={{
                            marginBottom: '1.5rem',
                            padding: '1rem',
                            background: 'linear-gradient(135deg, #dbeafe, #bfdbfe)',
                            borderRadius: '8px',
                            border: '2px solid #3b82f6',
                        }}
                    >
                        {(() => {
                            const estimatedPrices = calculateEstimatedPrices();
                            const totalEstimated = Object.values(estimatedPrices).reduce(
                                (sum, price) => sum + price,
                                0
                            );
                            const remaining = currentBudget - totalEstimated;
                            const isOverBudget = remaining < 0;

                            return (
                                <>
                                    <div
                                        style={{
                                            display: 'flex',
                                            justifyContent: 'space-between',
                                            marginBottom: '0.5rem',
                                        }}
                                    >
                                        <span style={{ fontSize: '0.85rem', color: '#1e40af' }}>AI 예측 총합:</span>
                                        <span style={{ fontSize: '0.9rem', fontWeight: '700', color: '#1e40af' }}>
                                            ₩{totalEstimated.toLocaleString()}
                                        </span>
                                    </div>
                                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                                        <span style={{ fontSize: '0.85rem', color: '#1e40af' }}>남은 예산:</span>
                                        <span
                                            style={{
                                                fontSize: '0.9rem',
                                                fontWeight: '700',
                                                color: isOverBudget ? '#ef4444' : '#10b981',
                                            }}
                                        >
                                            {isOverBudget ? '-' : ''}₩{Math.abs(remaining).toLocaleString()}
                                            {isOverBudget && ' ⚠️ 초과'}
                                        </span>
                                    </div>
                                    {totalEstimated === 0 && (
                                        <div
                                            style={{
                                                marginTop: '0.5rem',
                                                fontSize: '0.75rem',
                                                color: '#64748b',
                                                textAlign: 'center',
                                                fontStyle: 'italic',
                                            }}
                                        >
                                            부품 필터를 설정하면 AI가 예상 가격을 계산합니다
                                        </div>
                                    )}
                                </>
                            );
                        })()}
                    </div>

                    {/* 부품별 예산 비중 그래프 */}
                    <div>
                        <div
                            style={{
                                display: 'flex',
                                justifyContent: 'space-between',
                                alignItems: 'center',
                                marginBottom: '0.8rem',
                            }}
                        >
                            <span style={{ fontSize: '0.85rem', fontWeight: '600', color: '#1e293b' }}>
                                부품별 예산 비중 (AI 예측)
                            </span>
                            <span style={{ fontSize: '0.7rem', color: '#64748b', fontStyle: 'italic' }}>
                                필터 조건 기반
                            </span>
                        </div>
                        {(() => {
                            const estimatedPrices = calculateEstimatedPrices();
                            const totalEstimated = Object.values(estimatedPrices).reduce(
                                (sum, price) => sum + price,
                                0
                            );

                            const labels = {
                                cpu: 'CPU',
                                gpu: 'GPU',
                                mainboard: '메인보드',
                                ram: 'RAM',
                                storage: '저장장치',
                                psu: '파워',
                                case: '케이스',
                                cooler: '쿨러',
                                etc: '기타',
                            };
                            const colors = {
                                cpu: '#3b82f6',
                                gpu: '#ef4444',
                                mainboard: '#10b981',
                                ram: '#f59e0b',
                                storage: '#14b8a6',
                                psu: '#8b5cf6',
                                case: '#64748b',
                                cooler: '#06b6d4',
                                etc: '#ec4899',
                            };

                            return Object.entries(estimatedPrices).map(([component, price]) => {
                                const percentage = totalEstimated > 0 ? ((price / totalEstimated) * 100).toFixed(1) : 0;
                                const hasFilter = price > 0;

                                return (
                                    <div
                                        key={component}
                                        style={{ marginBottom: '0.8rem', opacity: hasFilter ? 1 : 0.4 }}
                                    >
                                        <div
                                            style={{
                                                display: 'flex',
                                                justifyContent: 'space-between',
                                                alignItems: 'center',
                                                marginBottom: '0.3rem',
                                            }}
                                        >
                                            <div style={{ display: 'flex', alignItems: 'center', gap: '0.3rem' }}>
                                                <span style={{ fontSize: '0.75rem', fontWeight: '600' }}>
                                                    {labels[component]}
                                                </span>
                                                {!hasFilter && (
                                                    <span style={{ fontSize: '0.65rem', color: '#94a3b8' }}>
                                                        (미설정)
                                                    </span>
                                                )}
                                            </div>
                                            <span
                                                style={{ fontSize: '0.7rem', color: hasFilter ? '#64748b' : '#94a3b8' }}
                                            >
                                                {hasFilter ? `${percentage}% (₩${price.toLocaleString()})` : '-'}
                                            </span>
                                        </div>
                                        <div
                                            style={{
                                                width: '100%',
                                                height: '8px',
                                                background: '#e2e8f0',
                                                borderRadius: '4px',
                                                overflow: 'hidden',
                                            }}
                                        >
                                            <div
                                                style={{
                                                    width: `${percentage}%`,
                                                    height: '100%',
                                                    background: hasFilter ? colors[component] : '#cbd5e1',
                                                    transition: 'width 0.3s ease',
                                                }}
                                            ></div>
                                        </div>
                                    </div>
                                );
                            });
                        })()}
                    </div>
                </div>
            </div>

            {/* AI 호환성 검사 버튼 */}
            <div style={{ marginTop: '2rem' }}>
                <button
                    onClick={checkCompatibility}
                    style={{
                        width: '100%',
                        padding: '1rem',
                        background: 'linear-gradient(135deg, #6366f1, #8b5cf6)',
                        color: 'white',
                        border: 'none',
                        borderRadius: '10px',
                        fontSize: '0.95rem',
                        fontWeight: '600',
                        cursor: 'pointer',
                        transition: 'all 0.2s',
                        boxShadow: '0 4px 12px rgba(99, 102, 241, 0.3)',
                        marginBottom: '1rem',
                    }}
                    onMouseEnter={(e) => (e.target.style.transform = 'translateY(-2px)')}
                    onMouseLeave={(e) => (e.target.style.transform = 'translateY(0)')}
                >
                    🤖 AI 호환성 검사 및 보정
                </button>
            </div>

            {/* 실행 버튼 */}
            <button className="btn-primary" onClick={handleStart}>
                AI 견적 추천 시작
            </button>

            {/* 🆕 호환성 검사 결과 모달 */}
            {compatibilityModal.show && compatibilityModal.results && (
                <div
                    style={{
                        position: 'fixed',
                        top: 0,
                        left: 0,
                        right: 0,
                        bottom: 0,
                        background: 'rgba(0, 0, 0, 0.6)',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        zIndex: 9999,
                        padding: '1rem',
                    }}
                    onClick={closeCompatibilityModal}
                >
                    <div
                        style={{
                            background: 'white',
                            borderRadius: '16px',
                            maxWidth: '700px',
                            width: '100%',
                            maxHeight: '85vh',
                            overflow: 'hidden',
                            boxShadow: '0 20px 60px rgba(0, 0, 0, 0.3)',
                            display: 'flex',
                            flexDirection: 'column',
                        }}
                        onClick={(e) => e.stopPropagation()}
                    >
                        {/* 모달 헤더 */}
                        <div
                            style={{
                                background: 'linear-gradient(135deg, #6366f1, #8b5cf6)',
                                color: 'white',
                                padding: '1.5rem',
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'space-between',
                            }}
                        >
                            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                                <span style={{ fontSize: '1.5rem' }}>🤖</span>
                                <h3 style={{ margin: 0, fontSize: '1.2rem', fontWeight: '700' }}>
                                    AI 호환성 검사 결과
                                </h3>
                            </div>
                            <button
                                onClick={closeCompatibilityModal}
                                style={{
                                    background: 'rgba(255, 255, 255, 0.2)',
                                    border: 'none',
                                    color: 'white',
                                    width: '32px',
                                    height: '32px',
                                    borderRadius: '50%',
                                    cursor: 'pointer',
                                    fontSize: '1.2rem',
                                    display: 'flex',
                                    alignItems: 'center',
                                    justifyContent: 'center',
                                    transition: 'all 0.2s',
                                }}
                                onMouseEnter={(e) => (e.target.style.background = 'rgba(255, 255, 255, 0.3)')}
                                onMouseLeave={(e) => (e.target.style.background = 'rgba(255, 255, 255, 0.2)')}
                            >
                                ✕
                            </button>
                        </div>

                        {/* 모달 바디 */}
                        <div
                            style={{
                                padding: '1.5rem',
                                overflowY: 'auto',
                                flex: 1,
                            }}
                        >
                            {(() => {
                                const { success, warnings, errors, suggestions } = compatibilityModal.results;
                                const totalIssues = errors.length + warnings.length;

                                return (
                                    <>
                                        {/* 전체 요약 */}
                                        {totalIssues === 0 && success.length > 0 && (
                                            <div
                                                style={{
                                                    background: 'linear-gradient(135deg, #10b981, #059669)',
                                                    color: 'white',
                                                    padding: '1rem 1.25rem',
                                                    borderRadius: '12px',
                                                    marginBottom: '1.5rem',
                                                    display: 'flex',
                                                    alignItems: 'center',
                                                    gap: '0.75rem',
                                                    boxShadow: '0 4px 12px rgba(16, 185, 129, 0.3)',
                                                }}
                                            >
                                                <span style={{ fontSize: '2rem' }}>✅</span>
                                                <div>
                                                    <div
                                                        style={{
                                                            fontSize: '1.1rem',
                                                            fontWeight: '700',
                                                            marginBottom: '0.25rem',
                                                        }}
                                                    >
                                                        완벽합니다!
                                                    </div>
                                                    <div style={{ fontSize: '0.9rem', opacity: 0.95 }}>
                                                        모든 호환성 검사를 통과했습니다 ({success.length}/17)
                                                    </div>
                                                </div>
                                            </div>
                                        )}

                                        {/* ✅ 정상 */}
                                        {success.length > 0 && (
                                            <div style={{ marginBottom: '1.5rem' }}>
                                                <div
                                                    style={{
                                                        display: 'flex',
                                                        alignItems: 'center',
                                                        gap: '0.5rem',
                                                        marginBottom: '0.75rem',
                                                        paddingBottom: '0.5rem',
                                                        borderBottom: '2px solid #10b981',
                                                    }}
                                                >
                                                    <span style={{ fontSize: '1.25rem' }}>✅</span>
                                                    <h4
                                                        style={{
                                                            margin: 0,
                                                            fontSize: '1rem',
                                                            fontWeight: '700',
                                                            color: '#059669',
                                                        }}
                                                    >
                                                        정상 ({success.length})
                                                    </h4>
                                                </div>
                                                <div
                                                    style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}
                                                >
                                                    {success.map((item, idx) => (
                                                        <div
                                                            key={idx}
                                                            style={{
                                                                padding: '0.75rem',
                                                                background: '#f0fdf4',
                                                                borderLeft: '3px solid #10b981',
                                                                borderRadius: '6px',
                                                                fontSize: '0.85rem',
                                                                color: '#065f46',
                                                            }}
                                                        >
                                                            • {item}
                                                        </div>
                                                    ))}
                                                </div>
                                            </div>
                                        )}

                                        {/* ⚠️ 경고 */}
                                        {warnings.length > 0 && (
                                            <div style={{ marginBottom: '1.5rem' }}>
                                                <div
                                                    style={{
                                                        display: 'flex',
                                                        alignItems: 'center',
                                                        gap: '0.5rem',
                                                        marginBottom: '0.75rem',
                                                        paddingBottom: '0.5rem',
                                                        borderBottom: '2px solid #f59e0b',
                                                    }}
                                                >
                                                    <span style={{ fontSize: '1.25rem' }}>⚠️</span>
                                                    <h4
                                                        style={{
                                                            margin: 0,
                                                            fontSize: '1rem',
                                                            fontWeight: '700',
                                                            color: '#d97706',
                                                        }}
                                                    >
                                                        경고 ({warnings.length})
                                                    </h4>
                                                </div>
                                                <div
                                                    style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}
                                                >
                                                    {warnings.map((item, idx) => (
                                                        <div
                                                            key={idx}
                                                            style={{
                                                                padding: '0.75rem',
                                                                background: '#fffbeb',
                                                                borderLeft: '3px solid #f59e0b',
                                                                borderRadius: '6px',
                                                                fontSize: '0.85rem',
                                                                color: '#92400e',
                                                            }}
                                                        >
                                                            • {item}
                                                        </div>
                                                    ))}
                                                </div>
                                            </div>
                                        )}

                                        {/* ❌ 오류 */}
                                        {errors.length > 0 && (
                                            <div style={{ marginBottom: '1.5rem' }}>
                                                <div
                                                    style={{
                                                        display: 'flex',
                                                        alignItems: 'center',
                                                        gap: '0.5rem',
                                                        marginBottom: '0.75rem',
                                                        paddingBottom: '0.5rem',
                                                        borderBottom: '2px solid #ef4444',
                                                    }}
                                                >
                                                    <span style={{ fontSize: '1.25rem' }}>❌</span>
                                                    <h4
                                                        style={{
                                                            margin: 0,
                                                            fontSize: '1rem',
                                                            fontWeight: '700',
                                                            color: '#dc2626',
                                                        }}
                                                    >
                                                        오류 ({errors.length})
                                                    </h4>
                                                </div>
                                                <div
                                                    style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}
                                                >
                                                    {errors.map((item, idx) => (
                                                        <div
                                                            key={idx}
                                                            style={{
                                                                padding: '0.75rem',
                                                                background: '#fef2f2',
                                                                borderLeft: '3px solid #ef4444',
                                                                borderRadius: '6px',
                                                                fontSize: '0.85rem',
                                                                color: '#991b1b',
                                                            }}
                                                        >
                                                            • {item}
                                                        </div>
                                                    ))}
                                                </div>
                                            </div>
                                        )}

                                        {/* 💡 AI 제안 */}
                                        {suggestions.length > 0 && (
                                            <div style={{ marginBottom: '0.5rem' }}>
                                                <div
                                                    style={{
                                                        display: 'flex',
                                                        alignItems: 'center',
                                                        gap: '0.5rem',
                                                        marginBottom: '0.75rem',
                                                        paddingBottom: '0.5rem',
                                                        borderBottom: '2px solid #3b82f6',
                                                    }}
                                                >
                                                    <span style={{ fontSize: '1.25rem' }}>💡</span>
                                                    <h4
                                                        style={{
                                                            margin: 0,
                                                            fontSize: '1rem',
                                                            fontWeight: '700',
                                                            color: '#2563eb',
                                                        }}
                                                    >
                                                        AI 제안 ({suggestions.length})
                                                    </h4>
                                                </div>
                                                <div
                                                    style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}
                                                >
                                                    {suggestions.map((item, idx) => (
                                                        <div
                                                            key={idx}
                                                            style={{
                                                                padding: '0.75rem',
                                                                background: '#eff6ff',
                                                                borderLeft: '3px solid #3b82f6',
                                                                borderRadius: '6px',
                                                                fontSize: '0.85rem',
                                                                color: '#1e40af',
                                                            }}
                                                        >
                                                            • {item}
                                                        </div>
                                                    ))}
                                                </div>
                                            </div>
                                        )}
                                    </>
                                );
                            })()}
                        </div>

                        {/* 모달 푸터 */}
                        <div
                            style={{
                                padding: '1rem 1.5rem',
                                borderTop: '1px solid #e5e7eb',
                                display: 'flex',
                                justifyContent: 'flex-end',
                            }}
                        >
                            <button
                                onClick={closeCompatibilityModal}
                                style={{
                                    background: 'linear-gradient(135deg, #6366f1, #8b5cf6)',
                                    color: 'white',
                                    border: 'none',
                                    padding: '0.75rem 2rem',
                                    borderRadius: '8px',
                                    fontSize: '0.9rem',
                                    fontWeight: '600',
                                    cursor: 'pointer',
                                    transition: 'all 0.2s',
                                    boxShadow: '0 4px 12px rgba(99, 102, 241, 0.3)',
                                }}
                                onMouseEnter={(e) => (e.target.style.transform = 'translateY(-2px)')}
                                onMouseLeave={(e) => (e.target.style.transform = 'translateY(0)')}
                            >
                                확인
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </>
    );
}

export default SidebarStack1Expert;
