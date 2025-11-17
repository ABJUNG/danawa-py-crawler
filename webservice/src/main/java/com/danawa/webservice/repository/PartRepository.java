package com.danawa.webservice.repository;

import com.danawa.webservice.domain.Part;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.JpaSpecificationExecutor;

import java.util.List;

/**
 * JpaSpecificationExecutor는 PartService의 동적 필터링(findByFilters)을 위해 필요합니다.
 */
public interface PartRepository extends JpaRepository<Part, Long>, JpaSpecificationExecutor<Part> {

    // [수정] PartService에서 EntityManager로 직접 동적 쿼리를 생성하므로,
    // 이 곳에 있던 모든 커스텀 @Query 메서드들은 삭제합니다.
    // Repository는 Spring Data JPA가 제공하는 기본 기능에만 집중하게 됩니다.

    /**
     * 특정 카테고리의 모든 부품을 조회합니다.
     * AI Builder에서 가격 범위 계산 등에 사용됩니다.
     */
    List<Part> findAllByCategory(String category);

}