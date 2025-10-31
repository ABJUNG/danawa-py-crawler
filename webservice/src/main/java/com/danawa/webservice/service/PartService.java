package com.danawa.webservice.service;

import com.danawa.webservice.domain.Part;
import com.danawa.webservice.repository.PartRepository;
import jakarta.persistence.EntityManager;
import jakarta.persistence.PersistenceContext;
import jakarta.persistence.Query;
import jakarta.persistence.criteria.Predicate;
import lombok.RequiredArgsConstructor;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.domain.Specification;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.util.MultiValueMap;

import java.util.*;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

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

    private Set<String> getHeightRanges() {
        /*  
        Query query = em.createNativeQuery("SELECT DISTINCT CAST(cooler_height AS REAL) FROM parts WHERE category = '쿨러' AND cooler_height IS NOT NULL", Double.class);
        @SuppressWarnings("unchecked")
        List<Double> heights = query.getResultList();
        Set<String> ranges = new TreeSet<>();
        for (Double h : heights) {
            if (h >= 200) ranges.add("200~mm");
            else if (h >= 170) ranges.add("170~199mm");
            else if (h >= 160) ranges.add("160~169mm");
            else if (h >= 150) ranges.add("150~159mm");
            else if (h >= 125) ranges.add("125~149mm");
            else if (h >= 100) ranges.add("100~124mm");
            else if (h >= 75) ranges.add("75~99mm");
            else if (h >= 50) ranges.add("50~74mm");
            else if (h >= 19) ranges.add("19~49mm");
            else if (h >= 16) ranges.add("16~18mm");
            else if (h >= 13) ranges.add("13~15mm");
            else if (h >= 10) ranges.add("10~12mm");
            else if (h >= 7) ranges.add("7~9mm");
            else if (h >= 4) ranges.add("4~6mm");
            else if (h > 0) ranges.add("~3mm");
        }
        return ranges;
         */
        return new TreeSet<>(); // 빈 Set 반환
    }

    public Page<Part> findByFilters(MultiValueMap<String, String> filters, Pageable pageable) {
        Specification<Part> spec = createSpecification(filters);
        return partRepository.findAll(spec, pageable);
    }

    // [신설] ID 목록으로 부품들을 찾는 서비스 메서드
    public List<Part> findByIds(List<Long> ids) {
        return partRepository.findAllById(ids);
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
