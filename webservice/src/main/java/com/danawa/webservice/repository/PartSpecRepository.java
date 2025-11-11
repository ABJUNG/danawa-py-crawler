package com.danawa.webservice.repository;

import com.danawa.webservice.domain.PartSpec;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.JpaSpecificationExecutor;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

import java.util.List;

public interface PartSpecRepository extends JpaRepository<PartSpec, Long>, JpaSpecificationExecutor<PartSpec> {

    // (신규) Category로 PartSpec을 찾되, N+1 문제를 피하기 위해 Part 엔티티를 함께 Fetch Join 하는 쿼리
    @Query("SELECT ps FROM PartSpec ps JOIN FETCH ps.part p WHERE p.category = :category")
    List<PartSpec> findAllWithPartByCategory(@Param("category") String category);
}