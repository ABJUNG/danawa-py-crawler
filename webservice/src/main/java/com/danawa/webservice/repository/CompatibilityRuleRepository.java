package com.danawa.webservice.repository;

import com.danawa.webservice.domain.CompatibilityRule;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.util.Optional;

@Repository
public interface CompatibilityRuleRepository extends JpaRepository<CompatibilityRule, Long> {
    
    @Query("SELECT cr FROM CompatibilityRule cr WHERE cr.ruleType = :ruleType AND cr.sourceValue = :sourceValue AND cr.targetValue = :targetValue")
    Optional<CompatibilityRule> findByRuleTypeAndValues(
        @Param("ruleType") String ruleType,
        @Param("sourceValue") String sourceValue,
        @Param("targetValue") String targetValue
    );
}

