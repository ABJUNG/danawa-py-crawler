package com.danawa.webservice.service;

import com.danawa.webservice.domain.Part;
import com.danawa.webservice.repository.PartRepository;
import jakarta.persistence.criteria.Predicate;
import lombok.RequiredArgsConstructor;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.domain.Specification;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.util.MultiValueMap;

import java.util.List;
import java.util.Map;
import java.util.Set;

@Service
@Transactional(readOnly = true)
@RequiredArgsConstructor
public class PartService {

    private final PartRepository partRepository;

    public Page<Part> findByFilters(MultiValueMap<String, String> filters, Pageable pageable) {
        Specification<Part> spec = createSpecification(filters);
        return partRepository.findAll(spec, pageable);
    }

    /**
     * 필터 맵을 기반으로 JPA Specification (동적 쿼리 조건)을 생성합니다.
     * 이제 name을 분석하지 않고, 각각의 전용 컬럼을 직접 조회하여 매우 빠릅니다.
     */
    private Specification<Part> createSpecification(MultiValueMap<String, String> filters) {
        return (root, query, criteriaBuilder) -> {
            Predicate predicate = criteriaBuilder.conjunction();

            for (Map.Entry<String, List<String>> entry : filters.entrySet()) {
                String key = entry.getKey();
                List<String> values = entry.getValue();

                if (values == null || values.isEmpty() || values.get(0).isEmpty()) {
                    continue;
                }

                switch (key) {
                    case "category":
                        predicate = criteriaBuilder.and(predicate, root.get("category").in(values));
                        break;
                    case "manufacturer":
                        // 제조사는 여전히 name 필드의 시작 부분으로 검색합니다.
                        Predicate[] manufacturerPredicates = values.stream()
                                .map(val -> criteriaBuilder.like(root.get("name"), val + "%"))
                                .toArray(Predicate[]::new);
                        predicate = criteriaBuilder.and(predicate, criteriaBuilder.or(manufacturerPredicates));
                        break;
                    case "socketType":
                        // 이제 'socket' 컬럼을 직접 조회합니다.
                        predicate = criteriaBuilder.and(predicate, root.get("socket").in(values));
                        break;
                    case "coreType":
                        // 이제 'core_type' 컬럼을 직접 조회합니다.
                        predicate = criteriaBuilder.and(predicate, root.get("coreType").in(values));
                        break;
                    case "ramCapacity":
                        // 이제 'ram_capacity' 컬럼을 직접 조회합니다.
                        predicate = criteriaBuilder.and(predicate, root.get("ramCapacity").in(values));
                        break;
                    case "chipset":
                        // 이제 'chipset' 컬럼을 직접 조회합니다.
                        predicate = criteriaBuilder.and(predicate, root.get("chipset").in(values));
                        break;
                    case "keyword":
                        predicate = criteriaBuilder.and(predicate, criteriaBuilder.like(root.get("name"), "%" + values.get(0) + "%"));
                        break;
                }
            }
            return predicate;
        };
    }

    // --- 이하 필터 옵션 생성 로직 (Repository 직접 호출로 단순화) ---

    public List<String> getManufacturersByCategory(String category) {
        return partRepository.findDistinctManufacturersByCategory(category);
    }

    public Set<String> getSocketTypes(String category) {
        return partRepository.findDistinctSocketByCategory(category);
    }

    public Set<String> getRamCapacities(String category) {
        return partRepository.findDistinctRamCapacityByCategory(category);
    }

    public Set<String> getChipsetManufacturers(String category) {
        return partRepository.findDistinctChipsetByCategory(category);
    }

    public Set<String> getCoreTypes(String category) {
        return partRepository.findDistinctCoreTypeByCategory(category);
    }

    // [삭제] 내장그래픽 필터는 현재 DB에 컬럼이 없으므로 잠시 제외합니다.
    // public List<String> getIntegratedGraphicsOptions() { ... }
}