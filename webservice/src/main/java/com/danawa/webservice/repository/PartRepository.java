package com.danawa.webservice.repository;

import com.danawa.webservice.domain.Part;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.JpaSpecificationExecutor;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

import java.util.List;
import java.util.Optional;

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

    /**
     * 벤치마크와 리뷰를 함께 조회 (AI 설명 생성용)
     * MultipleBagFetchException 방지를 위해 벤치마크만 fetch join
     */
    @Query("SELECT DISTINCT p FROM Part p " +
           "LEFT JOIN FETCH p.benchmarkResults " +
           "WHERE p.id = :id")
    Optional<Part> findByIdWithBenchmarks(@Param("id") Long id);
    
    /**
     * 리뷰만 함께 조회 (AI 설명 생성용)
     */
    @Query("SELECT DISTINCT p FROM Part p " +
           "LEFT JOIN FETCH p.communityReviews " +
           "WHERE p.id = :id")
    Optional<Part> findByIdWithReviews(@Param("id") Long id);

}