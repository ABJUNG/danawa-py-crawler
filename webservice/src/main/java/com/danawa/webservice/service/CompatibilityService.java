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
        String motherboardSocket = motherboardSpecs.optString("socket", "");
        
        if (cpuSocket.isEmpty() || motherboardSocket.isEmpty()) {
            result.addWarning("소켓 정보가 없어 CPU-메인보드 호환성을 확인할 수 없습니다.");
            return;
        }
        
        // 소켓 정규화 (공백, 특수문자 제거)
        cpuSocket = normalizeValue(cpuSocket);
        motherboardSocket = normalizeValue(motherboardSocket);
        
        if (!cpuSocket.equals(motherboardSocket)) {
            result.addError(String.format(
                "CPU 소켓(%s)과 메인보드 소켓(%s)이 호환되지 않습니다.",
                cpuSocket, motherboardSocket
            ));
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
        
        if (ramType.isEmpty() || motherboardRamType.isEmpty()) {
            result.addWarning("RAM 타입 정보가 없어 호환성을 확인할 수 없습니다.");
            return;
        }
        
        if (!ramType.equals(motherboardRamType)) {
            result.addError(String.format(
                "RAM 타입(%s)이 메인보드가 지원하는 타입(%s)과 호환되지 않습니다.",
                ramType, motherboardRamType
            ));
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
            result.addWarning("폼팩터 정보가 없어 케이스-메인보드 호환성을 확인할 수 없습니다.");
            return;
        }
        
        // 간단한 호환성 체크 (실제로는 DB의 compatibility_rules 참조 가능)
        if (boardFormFactor.contains("ATX") && !caseFormFactor.contains("ATX") && !caseFormFactor.contains("타워")) {
            result.addWarning(String.format(
                "메인보드(%s)가 케이스(%s)에 들어가지 않을 수 있습니다.",
                boardFormFactor, caseFormFactor
            ));
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
        return value.replaceAll("[\\s-]", "").toUpperCase();
    }
    
    private String extractRamType(JSONObject specs) {
        // product_class, memory_standard 등에서 DDR4/DDR5 추출
        String productClass = specs.optString("product_class", "");
        String memoryStandard = specs.optString("memory_standard", "");
        
        String combined = productClass + " " + memoryStandard;
        
        if (combined.contains("DDR5")) return "DDR5";
        if (combined.contains("DDR4")) return "DDR4";
        if (combined.contains("DDR3")) return "DDR3";
        
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

