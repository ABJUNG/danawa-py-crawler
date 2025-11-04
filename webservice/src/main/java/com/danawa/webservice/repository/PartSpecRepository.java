package com.danawa.webservice.repository;

import com.danawa.webservice.domain.PartSpec;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.JpaSpecificationExecutor; // 👈 1. (신규) Specification 사용 위해 추가
import org.springframework.data.jpa.repository.Query; // 👈 2. (신규) Query import
import org.springframework.data.repository.query.Param; // 👈 3. (신규) Param import

import java.util.List; // 👈 4. (신규) List import

// 5. (신규) JpaSpecificationExecutor 인터페이스 상속
public interface PartSpecRepository extends JpaRepository<PartSpec, Long>, JpaSpecificationExecutor<PartSpec> {

    // 6. (신규) Category로 PartSpec을 찾되, N+1 문제를 피하기 위해 Part 엔티티를 함께 Fetch Join 하는 쿼리
    @Query("SELECT ps FROM PartSpec ps JOIN FETCH ps.part p WHERE p.category = :category")
    List<PartSpec> findAllWithPartByCategory(@Param("category") String category);
}