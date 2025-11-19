package com.danawa.webservice.service;

import com.danawa.webservice.domain.Part;
import com.danawa.webservice.dto.CompatibilityResult;
import com.danawa.webservice.repository.CompatibilityRuleRepository;
import com.danawa.webservice.repository.PartRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.json.JSONObject;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.HashMap;
import java.util.List;
import java.util.Map;

@Slf4j
@Service
@Transactional(readOnly = true)
@RequiredArgsConstructor
public class CompatibilityService {
    
    private final PartRepository partRepository;
    private final CompatibilityRuleRepository compatibilityRuleRepository;
    
    /**
     * 선택된 부품들의 호환성을 검사합니다.
     * @param partIds 부품 ID 목록
     * @return 호환성 검사 결과
     */
    public CompatibilityResult checkCompatibility(List<Long> partIds) {
        CompatibilityResult result = CompatibilityResult.builder()
                .isCompatible(true)
                .build();
        
        if (partIds == null || partIds.isEmpty()) {
            result.addError("부품이 선택되지 않았습니다.");
            return result;
        }
        
        // 1. 부품 정보 조회
        List<Part> parts = partRepository.findAllById(partIds);
        Map<String, Part> partsByCategory = new HashMap<>();
        Map<String, JSONObject> specsByCategory = new HashMap<>();
        
        for (Part part : parts) {
            partsByCategory.put(part.getCategory(), part);
            
            // 스펙 JSON 파싱
            if (part.getPartSpec() != null && part.getPartSpec().getSpecs() != null) {
                try {
                    JSONObject specs = new JSONObject(part.getPartSpec().getSpecs());
                    specsByCategory.put(part.getCategory(), specs);
                } catch (Exception e) {
                    log.warn("스펙 파싱 실패: {} - {}", part.getName(), e.getMessage());
                }
            }
        }
        
        // 2. 호환성 검사 실행
        checkCpuMotherboardCompatibility(partsByCategory, specsByCategory, result);
        checkRamCompatibility(partsByCategory, specsByCategory, result);
        checkPowerSupplyCompatibility(partsByCategory, specsByCategory, result);
        checkCaseCompatibility(partsByCategory, specsByCategory, result);
        
        // 3. 결과 요약 생성
        generateSummary(result);
        
        return result;
    }
    
    /**
     * CPU와 메인보드 소켓 호환성 검사
     */
    private void checkCpuMotherboardCompatibility(
            Map<String, Part> partsByCategory,
            Map<String, JSONObject> specsByCategory,
            CompatibilityResult result) {
        
        Part cpu = partsByCategory.get("CPU");
        Part motherboard = partsByCategory.get("메인보드");
        
        if (cpu == null || motherboard == null) {
            return; // CPU나 메인보드가 없으면 검사 건너뜀
        }
        
        JSONObject cpuSpecs = specsByCategory.get("CPU");
        JSONObject motherboardSpecs = specsByCategory.get("메인보드");
        
        if (cpuSpecs == null || motherboardSpecs == null) {
            result.addWarning("CPU 또는 메인보드의 상세 스펙 정보가 없어 호환성을 확인할 수 없습니다.");
            return;
        }
        
        String cpuSocket = cpuSpecs.optString("socket", "");
        // 메인보드 소켓: socket과 cpu_socket 둘 다 확인
        String motherboardSocket = motherboardSpecs.optString("socket", "");
        if (motherboardSocket.isEmpty()) {
            motherboardSocket = motherboardSpecs.optString("cpu_socket", "");
        }
        
        // 소켓 정보가 없으면 칩셋이나 제품명에서 추론 시도
        if (motherboardSocket.isEmpty() && motherboard != null) {
            String chipset = motherboardSpecs.optString("chipset", "");
            String motherboardName = motherboard.getName().toUpperCase();
            
            // 칩셋 기반 추론
            if (chipset.contains("B850") || chipset.contains("X870") || chipset.contains("A620") || 
                chipset.contains("B650") || chipset.contains("X670") || chipset.contains("A520")) {
                motherboardSocket = "AM5";
            } else if (chipset.contains("B550") || chipset.contains("X570") || chipset.contains("A520")) {
                motherboardSocket = "AM4";
            } else if (chipset.contains("Z890") || chipset.contains("B860") || chipset.contains("H810") ||
                       chipset.contains("Z790") || chipset.contains("B760") || chipset.contains("H770")) {
                motherboardSocket = "LGA1851";
            } else if (chipset.contains("Z690") || chipset.contains("B660") || chipset.contains("H670")) {
                motherboardSocket = "LGA1700";
            }
            
            // 제품명 기반 추론 (B850M 등)
            if (motherboardSocket.isEmpty()) {
                if (motherboardName.contains("B850") || motherboardName.contains("X870") || 
                    motherboardName.contains("B650") || motherboardName.contains("X670")) {
                    motherboardSocket = "AM5";
                } else if (motherboardName.contains("B550") || motherboardName.contains("X570")) {
                    motherboardSocket = "AM4";
                } else if (motherboardName.contains("Z890") || motherboardName.contains("B860") ||
                           motherboardName.contains("Z790") || motherboardName.contains("B760")) {
                    motherboardSocket = "LGA1851";
                } else if (motherboardName.contains("Z690") || motherboardName.contains("B660")) {
                    motherboardSocket = "LGA1700";
                }
            }
        }
        
        if (cpuSocket.isEmpty() || motherboardSocket.isEmpty()) {
            if (cpuSocket.isEmpty()) {
                result.addWarning("CPU 소켓 정보가 없어 호환성을 확인할 수 없습니다. CPU 스펙을 확인하세요.");
            }
            if (motherboardSocket.isEmpty()) {
                result.addWarning("메인보드 소켓 정보가 없어 호환성을 확인할 수 없습니다. 메인보드 스펙을 확인하세요.");
            }
            return;
        }
        
        // 소켓 정규화 (공백, 특수문자 제거)
        cpuSocket = normalizeValue(cpuSocket);
        motherboardSocket = normalizeValue(motherboardSocket);
        
        if (!cpuSocket.equals(motherboardSocket)) {
            result.addError(String.format(
                "CPU 소켓(%s)과 메인보드 소켓(%s)이 호환되지 않습니다. 소켓을 일치시켜야 조립이 가능합니다.",
                cpuSocket, motherboardSocket
            ));
        } else {
            log.info("CPU-메인보드 소켓 호환 확인: {}", cpuSocket);
        }
    }
    
    /**
     * RAM과 메인보드 호환성 검사
     */
    private void checkRamCompatibility(
            Map<String, Part> partsByCategory,
            Map<String, JSONObject> specsByCategory,
            CompatibilityResult result) {
        
        Part ram = partsByCategory.get("RAM");
        Part motherboard = partsByCategory.get("메인보드");
        
        if (ram == null || motherboard == null) {
            return;
        }
        
        JSONObject ramSpecs = specsByCategory.get("RAM");
        JSONObject motherboardSpecs = specsByCategory.get("메인보드");
        
        if (ramSpecs == null || motherboardSpecs == null) {
            result.addWarning("RAM 또는 메인보드의 상세 스펙 정보가 없어 호환성을 확인할 수 없습니다.");
            return;
        }
        
        // RAM 타입 확인 (DDR4, DDR5 등)
        String ramType = extractRamType(ramSpecs);
        String motherboardRamType = extractRamType(motherboardSpecs);
        
        // 메인보드 메모리 타입이 없으면 칩셋/제품명에서 추론 시도
        if (motherboardRamType.isEmpty() && motherboard != null) {
            motherboardRamType = inferMotherboardRamType(motherboardSpecs, motherboard);
        }
        
        if (ramType.isEmpty() || motherboardRamType.isEmpty()) {
            if (ramType.isEmpty()) {
                result.addWarning("RAM 타입 정보가 없어 호환성을 확인할 수 없습니다. RAM 스펙(DDR4/DDR5)을 확인하세요.");
            }
            if (motherboardRamType.isEmpty()) {
                result.addWarning("메인보드 메모리 타입 정보가 없어 호환성을 확인할 수 없습니다.");
            }
            return;
        }
        
        if (!ramType.equals(motherboardRamType)) {
            result.addError(String.format(
                "RAM 타입(%s)이 메인보드가 지원하는 타입(%s)과 호환되지 않습니다. DDR4와 DDR5는 서로 호환되지 않습니다.",
                ramType, motherboardRamType
            ));
        } else {
            log.info("RAM-메인보드 타입 호환 확인: {}", ramType);
        }
    }
    
    /**
     * 파워 용량 검사
     */
    private void checkPowerSupplyCompatibility(
            Map<String, Part> partsByCategory,
            Map<String, JSONObject> specsByCategory,
            CompatibilityResult result) {
        
        Part psu = partsByCategory.get("파워");
        Part cpu = partsByCategory.get("CPU");
        Part gpu = partsByCategory.get("그래픽카드");
        
        if (psu == null) {
            return;
        }
        
        JSONObject psuSpecs = specsByCategory.get("파워");
        if (psuSpecs == null) {
            result.addWarning("파워 스펙 정보가 없어 용량을 확인할 수 없습니다.");
            return;
        }
        
        // 파워 정격 출력 추출 (예: "650W" -> 650)
        int psuWattage = extractWattage(psuSpecs);
        
        if (psuWattage == 0) {
            result.addWarning("파워 용량 정보를 찾을 수 없습니다.");
            return;
        }
        
        // CPU, GPU TDP 합산
        int totalTdp = 0;
        
        if (cpu != null) {
            JSONObject cpuSpecs = specsByCategory.get("CPU");
            if (cpuSpecs != null) {
                totalTdp += extractTdp(cpuSpecs);
            }
        }
        
        if (gpu != null) {
            JSONObject gpuSpecs = specsByCategory.get("그래픽카드");
            if (gpuSpecs != null) {
                totalTdp += extractTdp(gpuSpecs);
            }
        }
        
        // 기본 시스템 소비 전력 + 20% 여유 추가
        int recommendedWattage = (int) ((totalTdp + 100) * 1.2);
        
        if (psuWattage < recommendedWattage) {
            result.addError(String.format(
                "파워 용량(%dW)이 부족합니다. 권장 용량: %dW 이상 (CPU+GPU TDP: %dW + 여유)",
                psuWattage, recommendedWattage, totalTdp
            ));
        } else if (psuWattage < recommendedWattage * 1.1) {
            result.addWarning(String.format(
                "파워 용량(%dW)이 다소 여유롭지 않습니다. 권장 용량: %dW 이상",
                psuWattage, recommendedWattage
            ));
        }
    }
    
    /**
     * 케이스와 메인보드 폼팩터 호환성 검사
     */
    private void checkCaseCompatibility(
            Map<String, Part> partsByCategory,
            Map<String, JSONObject> specsByCategory,
            CompatibilityResult result) {
        
        Part caseP = partsByCategory.get("케이스");
        Part motherboard = partsByCategory.get("메인보드");
        
        if (caseP == null || motherboard == null) {
            return;
        }
        
        JSONObject caseSpecs = specsByCategory.get("케이스");
        JSONObject motherboardSpecs = specsByCategory.get("메인보드");
        
        if (caseSpecs == null || motherboardSpecs == null) {
            result.addWarning("케이스 또는 메인보드의 상세 스펙 정보가 없어 호환성을 확인할 수 없습니다.");
            return;
        }
        
        // 메인보드 폼팩터 (ATX, M-ATX, ITX 등)
        String boardFormFactor = extractFormFactor(motherboardSpecs);
        String caseFormFactor = extractFormFactor(caseSpecs);
        
        if (boardFormFactor.isEmpty() || caseFormFactor.isEmpty()) {
            if (boardFormFactor.isEmpty()) {
                result.addWarning("메인보드 폼팩터 정보가 없어 호환성을 확인할 수 없습니다.");
            }
            if (caseFormFactor.isEmpty()) {
                result.addWarning("케이스 폼팩터 정보가 없어 호환성을 확인할 수 없습니다.");
            }
            return;
        }
        
        // 호환성 체크 강화
        boolean compatible = false;
        String boardSize = boardFormFactor.toUpperCase();
        String caseSize = caseFormFactor.toUpperCase();
        
        // ATX 메인보드
        if (boardSize.contains("ATX") && !boardSize.contains("M-ATX") && !boardSize.contains("MINI")) {
            // Full ATX는 미들타워, 풀타워, ATX 케이스에 장착 가능
            compatible = caseSize.contains("타워") || caseSize.contains("ATX") || caseSize.contains("TOWER");
        }
        // M-ATX 메인보드
        else if (boardSize.contains("M-ATX") || boardSize.contains("MATX")) {
            // M-ATX는 대부분의 케이스에 장착 가능
            compatible = caseSize.contains("타워") || caseSize.contains("ATX") || 
                        caseSize.contains("TOWER") || caseSize.contains("MINI");
        }
        // Mini-ITX 메인보드
        else if (boardSize.contains("ITX") || boardSize.contains("MINI")) {
            // Mini-ITX는 모든 케이스에 장착 가능
            compatible = true;
        }
        // 기타
        else {
            compatible = true; // 정보가 불명확한 경우 호환 가능으로 간주
        }
        
        if (!compatible) {
            result.addError(String.format(
                "메인보드(%s)가 케이스(%s)에 들어가지 않을 수 있습니다. 케이스 크기를 확인하세요.",
                boardFormFactor, caseFormFactor
            ));
        } else {
            log.info("케이스-메인보드 폼팩터 호환 확인: 보드={}, 케이스={}", boardFormFactor, caseFormFactor);
        }
    }
    
    /**
     * 결과 요약 생성
     */
    private void generateSummary(CompatibilityResult result) {
        if (result.isCompatible()) {
            int warningCount = result.getWarnings() != null ? result.getWarnings().size() : 0;
            if (warningCount == 0) {
                result.setSummary("모든 부품이 호환됩니다. 문제없이 조립 가능합니다.");
            } else {
                result.setSummary(String.format(
                    "기본 호환성은 확인되었으나 %d개의 경고사항이 있습니다. 확인 후 조립하시기 바랍니다.",
                    warningCount
                ));
            }
        } else {
            int errorCount = result.getErrors() != null ? result.getErrors().size() : 0;
            result.setSummary(String.format(
                "호환되지 않는 부품이 있습니다. %d개의 오류를 해결해야 합니다.",
                errorCount
            ));
        }
    }
    
    // === 유틸리티 메서드 ===
    
    private String normalizeValue(String value) {
        if (value == null || value.isEmpty()) {
            return "";
        }
        String normalized = value.trim();
        // "소켓" 접두사 제거 (한글)
        if (normalized.startsWith("소켓")) {
            normalized = normalized.substring(2).trim();
        }
        // "SOCKET" 접두사 제거 (영문, 대소문자 무시)
        normalized = normalized.replaceAll("(?i)^SOCKET", "").trim();
        // 공백, 하이픈, 언더스코어 제거 및 대문자 변환
        normalized = normalized.replaceAll("[\\s\\-_]", "").toUpperCase();
        return normalized;
    }
    
    private String extractRamType(JSONObject specs) {
        // product_class, memory_standard, memory_type, memory_spec 등에서 DDR4/DDR5 추출
        String productClass = specs.optString("product_class", "");
        String memoryStandard = specs.optString("memory_standard", "");
        String memoryType = specs.optString("memory_type", ""); // 메인보드의 경우 "메모리 종류" 필드
        String memorySpec = specs.optString("memory_spec", ""); // 크롤러가 수집한 메모리 스펙 필드
        
        String combined = productClass + " " + memoryStandard + " " + memoryType + " " + memorySpec;
        
        if (combined.contains("DDR5")) return "DDR5";
        if (combined.contains("DDR4")) return "DDR4";
        if (combined.contains("DDR3")) return "DDR3";
        
        return "";
    }
    
    /**
     * 메인보드의 메모리 타입을 칩셋/제품명에서 추론
     */
    private String inferMotherboardRamType(JSONObject motherboardSpecs, Part motherboard) {
        String chipset = motherboardSpecs.optString("chipset", "");
        String motherboardName = motherboard != null ? motherboard.getName().toUpperCase() : "";
        
        // 칩셋 기반 추론
        if (!chipset.isEmpty()) {
            // AM5 칩셋은 DDR5 전용
            if (chipset.contains("B850") || chipset.contains("X870") || 
                chipset.contains("B650") || chipset.contains("X670") || 
                chipset.contains("A620")) {
                return "DDR5";
            }
            // AM4 칩셋은 DDR4 전용
            if (chipset.contains("B550") || chipset.contains("X570") || 
                chipset.contains("A520") || chipset.contains("B450") || 
                chipset.contains("X470")) {
                return "DDR4";
            }
            // 최신 Intel 칩셋 (14세대 이후)는 주로 DDR5
            if (chipset.contains("Z890") || chipset.contains("B860") || 
                chipset.contains("H810")) {
                return "DDR5";
            }
            // Intel 12-13세대 칩셋은 메모리 클럭으로 판단 시도
            if (chipset.contains("Z790") || chipset.contains("B760") || 
                chipset.contains("H770")) {
                String memoryClock = motherboardSpecs.optString("memory_clock", "");
                if (!memoryClock.isEmpty()) {
                    // 숫자만 추출
                    String clockNumStr = memoryClock.replaceAll("[^0-9]", "");
                    if (!clockNumStr.isEmpty()) {
                        try {
                            int clockNum = Integer.parseInt(clockNumStr);
                            // DDR5는 일반적으로 4800MHz 이상
                            if (clockNum >= 4800) {
                                return "DDR5";
                            }
                            // DDR4는 일반적으로 2133~3200MHz
                            if (clockNum >= 2000 && clockNum < 4800) {
                                return "DDR4";
                            }
                        } catch (NumberFormatException e) {
                            // 파싱 실패 시 무시
                        }
                    }
                }
            }
        }
        
        // 칩셋에서 찾지 못한 경우 제품명에서 추론
        if (!motherboardName.isEmpty()) {
            // AM5 제품명은 DDR5 전용
            if (motherboardName.contains("B850") || motherboardName.contains("X870") || 
                motherboardName.contains("B650") || motherboardName.contains("X670") || 
                motherboardName.contains("A620")) {
                return "DDR5";
            }
            // AM4 제품명은 DDR4 전용
            if (motherboardName.contains("B550") || motherboardName.contains("X570") || 
                motherboardName.contains("A520") || motherboardName.contains("B450")) {
                return "DDR4";
            }
            // Intel 최신 칩셋
            if (motherboardName.contains("Z890") || motherboardName.contains("B860") || 
                motherboardName.contains("H810")) {
                return "DDR5";
            }
        }
        
        return "";
    }
    
    private int extractWattage(JSONObject specs) {
        // rated_output 필드에서 "650W" 형태의 값 추출
        String ratedOutput = specs.optString("rated_output", "");
        
        try {
            return Integer.parseInt(ratedOutput.replaceAll("[^0-9]", ""));
        } catch (Exception e) {
            return 0;
        }
    }
    
    private int extractTdp(JSONObject specs) {
        // tdp, thermal_design_power 필드에서 추출
        String tdp = specs.optString("tdp", specs.optString("thermal_design_power", ""));
        
        try {
            return Integer.parseInt(tdp.replaceAll("[^0-9]", ""));
        } catch (Exception e) {
            // 기본값: CPU 150W, GPU 250W 가정
            return 150;
        }
    }
    
    private String extractFormFactor(JSONObject specs) {
        // form_factor, product_class 등에서 폼팩터 정보 추출
        String formFactor = specs.optString("form_factor", "");
        String productClass = specs.optString("product_class", "");
        String boardFormFactor = specs.optString("board_form_factor", "");
        
        String combined = formFactor + " " + productClass + " " + boardFormFactor;
        return combined.toUpperCase();
    }
}

