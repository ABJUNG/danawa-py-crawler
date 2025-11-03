package com.danawa.webservice.dto;

import com.danawa.webservice.domain.BenchmarkResult;
import lombok.Getter;

@Getter
public class BenchmarkResultDto {
    private String testName;
    private String testVersion;
    private String scenario;
    private Double value;
    private String unit;

    public BenchmarkResultDto(BenchmarkResult entity) {
        this.testName = entity.getTestName();
        this.testVersion = entity.getTestVersion();
        this.scenario = entity.getScenario();
        this.value = entity.getValue();
        this.unit = entity.getUnit();
    }
}