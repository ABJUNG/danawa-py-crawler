package com.danawa.webservice.repository;

import com.danawa.webservice.domain.Part;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.JpaSpecificationExecutor;

/**
 * JpaSpecificationExecutor는 PartService의 동적 필터링(findByFilters)을 위해 필요합니다.
 */
public interface PartRepository extends JpaRepository<Part, Long>, JpaSpecificationExecutor<Part> {

    // [수정] PartService에서 EntityManager로 직접 동적 쿼리를 생성하므로,
    // 이 곳에 있던 모든 커스텀 @Query 메서드들은 삭제합니다.
    // Repository는 Spring Data JPA가 제공하는 기본 기능에만 집중하게 됩니다.

}