package com.danawa.webservice.service;

import com.danawa.webservice.domain.Part;
import com.danawa.webservice.repository.PartRepository;
import jakarta.persistence.EntityManager;
import jakarta.persistence.PersistenceContext;
import jakarta.persistence.criteria.Predicate;
import lombok.RequiredArgsConstructor;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.domain.Specification;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.util.MultiValueMap;

import java.util.*;
import com.danawa.webservice.dto.PartResponseDto; // 1. 이 줄을 추가
import java.util.stream.Collectors; // 2. 이 줄을 추가

@Service
@Transactional(readOnly = true)
@RequiredArgsConstructor
public class PartService {

    private final PartRepository partRepository;

    @PersistenceContext
    private final EntityManager em;

    private static final Map<String, List<String>> FILTERABLE_COLUMNS = Map.of(
            "CPU", List.of("manufacturer", "codename", "cpuSeries", "cpuClass", "socket", "cores", "threads", "integratedGraphics"),
            "쿨러", List.of("manufacturer", "productType", "coolingMethod", "airCoolingForm", "coolerHeight", "radiatorLength", "fanSize", "fanConnector"),
            "메인보드", List.of("manufacturer", "socket", "chipset", "formFactor", "memorySpec", "memorySlots", "vgaConnection", "m2Slots", "wirelessLan"),
            "RAM", List.of("manufacturer", "deviceType", "productClass", "capacity", "ramCount", "clockSpeed", "ramTiming", "heatsinkPresence"),
            "그래픽카드", List.of("manufacturer", "nvidiaChipset", "amdChipset", "intelChipset", "gpuInterface", "gpuMemoryCapacity", "outputPorts", "recommendedPsu", "fanCount", "gpuLength"),
            "SSD", List.of("manufacturer", "formFactor", "ssdInterface", "capacity", "memoryType", "ramMounted", "sequentialRead", "sequentialWrite"),
            "HDD", List.of("manufacturer", "hddSeries", "diskCapacity", "rotationSpeed", "bufferCapacity", "hddWarranty"),
            "케이스", List.of("manufacturer", "productType", "caseSize", "supportedBoard", "sidePanel", "psuLength", "vgaLength", "cpuCoolerHeightLimit"),
            "파워", List.of("manufacturer", "productType", "ratedOutput", "eightyPlusCert", "etaCert", "cableConnection", "pcie16pin")
    );

    public Map<String, Set<String>> getAvailableFiltersForCategory(String category) {
        Map<String, Set<String>> availableFilters = new HashMap<>();
        List<String> columns = FILTERABLE_COLUMNS.get(category);

        if (columns == null) return availableFilters;
        /*
        for (String columnFieldName : columns) {
            if ("coolerHeight".equals(columnFieldName) && "쿨러".equals(category)) {
                Set<String> heightRanges = getHeightRanges();
                if (!heightRanges.isEmpty()) {
                    availableFilters.put("coolerHeight", heightRanges);
                }
                continue;
            }

            String jpql = String.format("SELECT DISTINCT p.%s FROM Part p WHERE p.category = :category AND p.%s IS NOT NULL AND p.%s != ''",
                    columnFieldName, columnFieldName, columnFieldName);

            Query query = em.createQuery(jpql, String.class);
            query.setParameter("category", category);

            @SuppressWarnings("unchecked")
            List<String> results = query.getResultList();

            if (!results.isEmpty()) {
                availableFilters.put(columnFieldName, new HashSet<>(results));
            }
        }
        */
        return availableFilters;
    }

    // 제거된 높이 범위 계산 함수 (현재 필터링 스펙 단순화로 미사용)

    public Page<PartResponseDto> findByFilters(MultiValueMap<String, String> filters, Pageable pageable) {
        Specification<Part> spec = createSpecification(filters);
        Page<Part> partPage = partRepository.findAll(spec, pageable);

        // Page<Part>를 Page<PartResponseDto>로 변환하여 반환
        return partPage.map(part -> new PartResponseDto(part));
    }

    // [신설] ID 목록으로 부품들을 찾는 서비스 메서드
    public List<PartResponseDto> findByIds(List<Long> ids) {
        List<Part> parts = partRepository.findAllById(ids);

        // List<Part>를 List<PartResponseDto>로 변환하여 반환
        return parts.stream()
                .map(part -> new PartResponseDto(part))
                .collect(Collectors.toList());
    }

    private Specification<Part> createSpecification(MultiValueMap<String, String> filters) {
        return (root, query, cb) -> {
            Predicate predicate = cb.conjunction();
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
                /*
                } else if (key.equals("coolerHeight")) {
                    Predicate[] heightPredicates = values.stream().map(range -> {
                        Matcher m = Pattern.compile("(\\d+(\\.\\d+)?)").matcher(range);
                        List<Double> nums = new ArrayList<>();
                        while (m.find()) {
                            nums.add(Double.parseDouble(m.group(1)));
                        }
                        if (range.startsWith("~") && !nums.isEmpty()) {
                            return cb.lessThanOrEqualTo(root.get("coolerHeight"), nums.get(0));
                        } else if (range.contains("~mm") && !nums.isEmpty()) {
                            return cb.greaterThanOrEqualTo(root.get("coolerHeight"), nums.get(0));
                        } else if (nums.size() == 2) {
                            return cb.between(root.get("coolerHeight"), nums.get(0), nums.get(1));
                        }
                        return null;
                    }).filter(Objects::nonNull).toArray(Predicate[]::new);
                    if (heightPredicates.length > 0) {
                        predicate = cb.and(predicate, cb.or(heightPredicates));
                    }
                } else if (allFilterKeys.contains(key)) {
                    predicate = cb.and(predicate, root.get(key).in(values)); */
                }
            }
            return predicate;
        };
    }
}
