package com.danawa.webservice.repository;

import com.danawa.webservice.domain.Part;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

import java.util.List;

public interface PartRepository extends JpaRepository<Part, Long> {

    Page<Part> findByCategory(String category, Pageable pageable);

    Page<Part> findByCategoryAndNameStartsWith(String category, String manufacturer, Pageable pageable);

    Page<Part> findByCategoryAndNameContainingIgnoreCase(String category, String keyword, Pageable pageable);

    // [추가된 부분] JPQL을 사용하여 DB에서 직접 제조사 이름만 중복 없이 가져옵니다. (성능 최적화)
    @Query("SELECT DISTINCT SUBSTRING_INDEX(p.name, ' ', 1) FROM Part p WHERE p.category = :category ORDER BY 1")
    List<String> findDistinctManufacturersByCategory(@Param("category") String category);
}