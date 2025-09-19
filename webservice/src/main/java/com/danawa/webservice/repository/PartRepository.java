package com.danawa.webservice.repository;

import com.danawa.webservice.domain.Part;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List; // List import 추가

public interface PartRepository extends JpaRepository<Part, Long> {

    // [추가된 부분 1]
    // 지정된 카테고리에 속하는 모든 부품을 찾습니다.
    List<Part> findByCategory(String category);

    // [추가된 부분 2]
    // 지정된 카테고리 내에서 이름에 키워드가 포함된 부품을 검색합니다.
    List<Part> findByCategoryAndNameContainingIgnoreCase(String category, String keyword);

    // [추가된 부분]
    // name 필드에서 keyword가 포함된 데이터를 대소문자 구분 없이 검색합니다.
    // ex) 'findByNameContainingIgnoreCase' -> SQL: SELECT * FROM parts WHERE name LIKE '%keyword%' (case-insensitive)
    List<Part> findByNameContainingIgnoreCase(String keyword);

    // 지정된 카테고리 내에서 특정 제조사(이름으로 시작하는)의 부품을 찾습니다.
    List<Part> findByCategoryAndNameStartsWith(String category, String manufacturer);
}