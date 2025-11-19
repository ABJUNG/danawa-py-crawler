package com.danawa.webservice.repository;

import com.danawa.webservice.domain.PcFaq;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public interface PcFaqRepository extends JpaRepository<PcFaq, Long> {
    
    // 카테고리로 검색
    List<PcFaq> findByCategory(String category);
    
    // 질문에 키워드 포함 검색 (대소문자 무시)
    @Query("SELECT f FROM PcFaq f WHERE LOWER(f.question) LIKE LOWER(CONCAT('%', :keyword, '%')) OR LOWER(f.keywords) LIKE LOWER(CONCAT('%', :keyword, '%'))")
    List<PcFaq> findByQuestionContainingOrKeywordsContaining(@Param("keyword") String keyword);
    
    // 인기 FAQ (조회수 순)
    List<PcFaq> findTop10ByOrderByViewCountDesc();
    
    // 도움된 FAQ (helpful 순)
    List<PcFaq> findTop10ByOrderByHelpfulCountDesc();
}

