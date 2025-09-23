package com.danawa.webservice.repository;

import com.danawa.webservice.domain.Part;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.JpaSpecificationExecutor;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

import java.util.List;
import java.util.Set;

public interface PartRepository extends JpaRepository<Part, Long>, JpaSpecificationExecutor<Part> {

    @Query("SELECT DISTINCT SUBSTRING_INDEX(p.name, ' ', 1) FROM Part p WHERE p.category = :category ORDER BY 1")
    List<String> findDistinctManufacturersByCategory(@Param("category") String category);

    List<Part> findByCategory(String category);

    // ▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼
    // [수정된 부분] DB 컬럼 이름(snake_case) -> 자바 필드 이름(camelCase)
    @Query("SELECT DISTINCT p.socket FROM Part p WHERE p.category = :category AND p.socket IS NOT NULL ORDER BY p.socket")
    Set<String> findDistinctSocketByCategory(@Param("category") String category);

    @Query("SELECT DISTINCT p.coreType FROM Part p WHERE p.category = :category AND p.coreType IS NOT NULL ORDER BY p.coreType")
    Set<String> findDistinctCoreTypeByCategory(@Param("category") String category);

    @Query("SELECT DISTINCT p.ramCapacity FROM Part p WHERE p.category = :category AND p.ramCapacity IS NOT NULL ORDER BY p.ramCapacity")
    Set<String> findDistinctRamCapacityByCategory(@Param("category") String category);

    @Query("SELECT DISTINCT p.chipset FROM Part p WHERE p.category = :category AND p.chipset IS NOT NULL ORDER BY p.chipset")
    Set<String> findDistinctChipsetByCategory(@Param("category") String category);
    // ▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲
}