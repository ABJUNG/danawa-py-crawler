package com.danawa.webservice.service;

import com.danawa.webservice.domain.Part;
import com.danawa.webservice.domain.PartSpec; // 👈 1. (신규) PartSpec import
import com.danawa.webservice.dto.PartResponseDto; // 👈 5단계에서 추가됨
import com.danawa.webservice.repository.PartRepository;
import com.danawa.webservice.repository.PartSpecRepository; // 👈 2. (신규) PartSpecRepository import
import jakarta.persistence.EntityManager;
import jakarta.persistence.PersistenceContext;
import jakarta.persistence.criteria.Join;
import jakarta.persistence.criteria.Predicate;
import lombok.RequiredArgsConstructor;
import org.json.JSONObject; // 👈 4. (신규) JSON 파싱 라이브러리 import
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.domain.Specification;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.util.MultiValueMap;

import java.util.*;
import java.util.stream.Collectors; // 👈 5.2 단계에서 추가됨

@Service
@Transactional(readOnly = true)
@RequiredArgsConstructor
public class PartService {

    private final PartRepository partRepository;
    private final PartSpecRepository partSpecRepository; // 👈 5. (신규) PartSpecRepository 주입
    
    @PersistenceContext
    private final EntityManager em; // (참고: 현재 코드에서는 em이 사용되지 않으나, 추후 필요할 수 있어 유지)

    // (필터 순서 정의 - 기존과 동일)
    private static final Map<String, List<String>> FILTERABLE_COLUMNS = Map.of(
            "CPU", List.of("manufacturer", "socket", "cores", "threads", "cpu_series", "codename", "integrated_graphics"),
            "쿨러", List.of("product_type", "manufacturer", "cooling_method", "air_cooling_form", "cooler_height", "radiator_length", "fan_size", "fan_connector"), // 👈 product_type (snake_case)
            "메인보드", List.of("manufacturer", "socket", "chipset", "form_factor", "memory_spec", "memory_slots", "vga_connection", "m2_slots", "wireless_lan"),
            "RAM", List.of("manufacturer", "device_type", "product_class", "capacity", "ram_count", "clock_speed", "ram_timing", "heatsink_presence"),
            "그래픽카드", List.of("manufacturer", "nvidia_chipset", "amd_chipset", "intel_chipset", "gpu_interface", "gpu_memory_capacity", "output_ports", "recommended_psu", "fan_count", "gpu_length"),
            "SSD", List.of("manufacturer", "form_factor", "ssd_interface", "capacity", "memory_type", "ram_mounted", "sequential_read", "sequential_write"),
            "HDD", List.of("manufacturer", "hdd_series", "disk_capacity", "rotation_speed", "buffer_capacity", "hdd_warranty"),
            "케이스", List.of("manufacturer", "product_type", "case_size", "supported_board", "side_panel", "psu_length", "vga_length", "cpu_cooler_height_limit"),
            "파워", List.of("manufacturer", "product_type", "rated_output", "eighty_plus_cert", "eta_cert", "cable_connection", "pcie_16pin")
    );

    /**
     * [수정됨] JSON 스펙을 파싱하여 동적 필터 목록을 생성합니다.
     */
    public Map<String, Set<String>> getAvailableFiltersForCategory(String category) {
        Map<String, Set<String>> availableFilters = new HashMap<>();
        List<String> columns = FILTERABLE_COLUMNS.get(category);
        if (columns == null) {
            return availableFilters;
        }

        List<PartSpec> specsForCategory = partSpecRepository.findAllWithPartByCategory(category);

        if (specsForCategory.isEmpty()) {
            return availableFilters;
        }

        for (String columnKey : columns) {
            Set<String> values = new HashSet<>();
            for (PartSpec partSpec : specsForCategory) {
                try {
                    if (partSpec.getSpecs() != null) {
                        JSONObject specsJson = new JSONObject(partSpec.getSpecs());
                        if (specsJson.has(columnKey) && specsJson.get(columnKey) != null) {
                            String value = specsJson.optString(columnKey); // .getString() 대신 optString()
                            if (value != null && !value.isBlank()) {
                                values.add(value);
                            }
                        }
                    }
                } catch (Exception e) {
                    // JSON 파싱 오류 등 무시
                }
            }
            if (!values.isEmpty()) {
                // 맵의 키는 App.js가 사용하는 키 (snake_case)
                availableFilters.put(columnKey, values);
            }
        }
        
        return availableFilters;
    }

    /**
     * DTO를 반환합니다.
     */
    public Page<PartResponseDto> findByFilters(MultiValueMap<String, String> filters, Pageable pageable) {
        Specification<Part> spec = createSpecification(filters); // 👈 수정된 Specification 호출
        Page<Part> partPage = partRepository.findAll(spec, pageable);
        return partPage.map(PartResponseDto::new); 
    }

    /**
     * DTO를 반환합니다.
     */
    public List<PartResponseDto> findByIds(List<Long> ids) {
        List<Part> parts = partRepository.findAllById(ids);
        return parts.stream()
                    .map(PartResponseDto::new)
                    .collect(Collectors.toList());
    }

    /**
     * [수정됨] JSON 스펙 필터링 로직을 복구합니다.
     */
    private Specification<Part> createSpecification(MultiValueMap<String, String> filters) {
        return (root, query, cb) -> {
            Predicate predicate = cb.conjunction();
            
            // 3. [복구] 필터링 가능한 모든 스펙 키 목록을 가져옵니다.
            List<String> allFilterKeys = new ArrayList<>();
            FILTERABLE_COLUMNS.values().forEach(allFilterKeys::addAll);

            for (Map.Entry<String, List<String>> entry : filters.entrySet()) {
                String key = entry.getKey();
                List<String> values = entry.getValue();
                if (values == null || values.isEmpty() || values.get(0).isEmpty()) continue;

                if (key.equals("category")) {
                    predicate = cb.and(predicate, root.get("category").in(values));
                } else if (key.equals("keyword")) {
                    predicate = cb.and(predicate, cb.like(root.get("name"), "%" + values.get(0) + "%"));
                }
                
                // 4. [복구] 'product_type' 및 기타 스펙 필터링 로직
                else if (allFilterKeys.contains(key)) {
                    // Part 엔티티와 PartSpec 엔티티를 'partSpec' 필드로 조인합니다.
                    Join<Part, PartSpec> specJoin = root.join("partSpec");

                    // 5. (핵심) JSON 컬럼('specs') 내부의 값(key)을 검색합니다.
                    //    MySQL의 JSON_EXTRACT(specs, '$.product_type')와 동일한 JPA Criteria
                    //    (참고: JSON_UNQUOTE는 따옴표를 제거하기 위해 사용합니다. 예: "CPU 쿨러" -> CPU 쿨러)
                    Predicate[] specPredicates = values.stream().map(value -> 
                        cb.equal(
                            cb.function("JSON_UNQUOTE", String.class, 
                                cb.function("JSON_EXTRACT", String.class, specJoin.get("specs"), cb.literal("$." + key))
                            ), 
                            value
                        )
                    ).toArray(Predicate[]::new);

                    // 6. 여러 값 중 하나라도 일치하면 (OR 조건)
                    if (specPredicates.length > 0) {
                        predicate = cb.and(predicate, cb.or(specPredicates));
                    }
                }
                // (TODO: coolerHeight 같은 숫자 범위 검색은 별도 로직 필요)
            }
            return predicate;
        };
    }
}