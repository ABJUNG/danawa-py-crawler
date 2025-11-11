package com.danawa.webservice.service;

import com.danawa.webservice.domain.Part;
import com.danawa.webservice.domain.PartSpec; // 👈 1. (신규) PartSpec import
import com.danawa.webservice.dto.PartResponseDto; // 👈 5단계에서 추가됨
import com.danawa.webservice.repository.PartRepository;
import com.danawa.webservice.repository.PartSpecRepository; // 👈 2. (신규) PartSpecRepository import
import jakarta.persistence.EntityManager;
import jakarta.persistence.PersistenceContext;
// import jakarta.persistence.Query; // 👈 3. (삭제) 더 이상 Query를 직접 사용하지 않음
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
            "쿨러", List.of("manufacturer", "product_type", "cooling_method", "air_cooling_form", "fan_size", "radiator_length"),
            "메인보드", List.of("manufacturer", "socket", "chipset", "form_factor", "memory_spec"),
            "RAM", List.of("manufacturer", "product_class", "capacity", "clock_speed", "ram_timing"),
            "그래픽카드", List.of("manufacturer", "nvidia_chipset", "amd_chipset", "gpu_memory_capacity", "gpu_length"),
            "SSD", List.of("manufacturer", "form_factor", "ssd_interface", "capacity", "sequential_read"),
            "HDD", List.of("manufacturer", "disk_capacity", "rotation_speed", "buffer_capacity"),
            "케이스", List.of("manufacturer", "case_size", "supported_board", "cpu_cooler_height_limit", "vga_length"),
            "파워", List.of("manufacturer", "rated_output", "eighty_plus_cert", "cable_connection")
            // (참고: App.js와 일관성을 위해 Python의 snake_case 키 이름으로 일부 수정했습니다.)
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

        // 1. 해당 카테고리의 모든 PartSpec을 조회 (Part 엔티티와 함께 Fetch Join)
        List<PartSpec> specsForCategory = partSpecRepository.findAllWithPartByCategory(category);

        if (specsForCategory.isEmpty()) {
            return availableFilters; // 스펙 정보가 없으면 빈 맵 반환
        }

        // 2. 각 스펙(JSON)을 파싱하여 필터 목록을 동적으로 생성
        for (String columnKey : columns) {
            Set<String> values = new HashSet<>();
            for (PartSpec partSpec : specsForCategory) {
                try {
                    if (partSpec.getSpecs() != null) {
                        JSONObject specsJson = new JSONObject(partSpec.getSpecs());

                        // 3. JSON에서 키(columnKey)로 값을 찾음
                        if (specsJson.has(columnKey) && specsJson.get(columnKey) != null) {
                            String value = specsJson.getString(columnKey);
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
                // 4. 맵의 키는 App.js가 사용하는 키 (columnKey)
                availableFilters.put(columnKey, values);
            }
        }
        
        return availableFilters;
    }

    // (기존 getHeightRanges 함수는 JSON으로 대체되었으므로 삭제 또는 주석 처리)
    // private Set<String> getHeightRanges() { ... }


    /**
     * [수정됨] Part 엔티티가 아닌 DTO를 반환합니다.
     */
    public Page<PartResponseDto> findByFilters(MultiValueMap<String, String> filters, Pageable pageable) {
        // (주의!) 현재 createSpecification 함수는 JSON 필터링을 지원하지 않습니다.
        // (App.js에서 필터 선택 시, 해당 로직을 추가 구현해야 합니다.)
        Specification<Part> spec = createSpecification(filters);
        Page<Part> partPage = partRepository.findAll(spec, pageable);
        
        // Page<Part>를 Page<PartResponseDto>로 변환하여 반환
        // (N+1 문제 경고: DTO 생성자가 PartSpec, CommunityReviews를 Lazy Loading 할 수 있음)
        return partPage.map(PartResponseDto::new); // 람다를 메서드 레퍼런스로 변경
    }

    /**
     * [수정됨] Part 엔티티가 아닌 DTO를 반환합니다.
     */
    public List<PartResponseDto> findByIds(List<Long> ids) {
        List<Part> parts = partRepository.findAllById(ids);
        
        // List<Part>를 List<PartResponseDto>로 변환하여 반환
        // (N+1 문제 경고)
        return parts.stream()
                    .map(PartResponseDto::new) // 람다를 메서드 레퍼런스로 변경
                    .collect(Collectors.toList());
    }

    /**
     * [수정됨] JSON 스펙 필터링 로직이 비활성화되었습니다.
     * (현재 'category'와 'keyword' 필터만 작동합니다.)
     */
    private Specification<Part> createSpecification(MultiValueMap<String, String> filters) {
        return (root, query, cb) -> {
            Predicate predicate = cb.conjunction();
            
            // (1단계에서 삭제한 스펙 필드 필터링 로직은 비활성화 상태 유지)
            // List<String> allFilterKeys = new ArrayList<>();
            // FILTERABLE_COLUMNS.values().forEach(allFilterKeys::addAll);

            for (Map.Entry<String, List<String>> entry : filters.entrySet()) {
                String key = entry.getKey();
                List<String> values = entry.getValue();
                if (values == null || values.isEmpty() || values.get(0).isEmpty()) continue;

                if (key.equals("category")) {
                    predicate = cb.and(predicate, root.get("category").in(values));
                } else if (key.equals("keyword")) {
                    predicate = cb.and(predicate, cb.like(root.get("name"), "%" + values.get(0) + "%"));
                }
                
                // (1단계에서 주석 처리한 JSON 스펙 필터링 로직)
                // TODO: 'key'가 'cores', 'socket' 등 스펙 필드일 경우, 
                // PartSpec 테이블의 'specs' JSON 컬럼을 검색하는 로직 (Native Query 또는 H2 JSON 함수) 추가 필요
                /*
                else if (key.equals("coolerHeight")) { ... } 
                else if (allFilterKeys.contains(key)) { ... }
                */
            }
            return predicate;
        };
    }
}