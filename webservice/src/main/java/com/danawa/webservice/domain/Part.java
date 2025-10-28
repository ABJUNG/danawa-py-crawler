package com.danawa.webservice.domain;

import jakarta.persistence.*;
import lombok.Getter;
import lombok.NoArgsConstructor;
import org.hibernate.annotations.CreationTimestamp;
import org.hibernate.annotations.UpdateTimestamp;

import java.math.BigDecimal;
import java.time.LocalDateTime;

@Getter
@NoArgsConstructor
@Entity
@Table(name = "parts")
public class Part {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(length = 255, nullable = false)
    private String name;

    @Column(length = 50, nullable = false)
    private String category;

    @Column(nullable = false)
    private int price;

    @Column(length = 512, nullable = false, unique = true)
    private String link;

    @Column(name = "img_src", length = 512)
    private String imgSrc;

    @Column(name = "star_rating", precision = 3, scale = 1)
    private BigDecimal starRating;

    @Column(name = "rating_review_count")
    private Integer ratingReviewCount;

    // ▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼
    // CPU 상세 필드
    @Column(name = "manufacturer", columnDefinition = "TEXT")
    private String manufacturer;

    @Column(name = "codename", columnDefinition = "TEXT")
    private String codename;

    @Column(name = "cpu_series", columnDefinition = "TEXT")
    private String cpuSeries;

    @Column(name = "cpu_class", columnDefinition = "TEXT")
    private String cpuClass;

    @Column(name = "socket", columnDefinition = "TEXT")
    private String socket;

    @Column(name = "cores", columnDefinition = "TEXT")
    private String cores;

    @Column(name = "threads", columnDefinition = "TEXT")
    private String threads;

    @Column(name = "integrated_graphics", columnDefinition = "TEXT")
    private String integratedGraphics;

    @Column(name = "review_count")
    private Integer reviewCount;

    @Column(name = "core_type", columnDefinition = "TEXT")
    private String coreType;

    //쿨러 상세 필드
    @Column(name = "product_type", columnDefinition = "TEXT")
    private String productType;

    @Column(name = "cooling_method", columnDefinition = "TEXT")
    private String coolingMethod;

    @Column(name = "air_cooling_form", columnDefinition = "TEXT")
    private String airCoolingForm;

    @Column(name = "cooler_height", columnDefinition = "TEXT")
    private String coolerHeight;

    @Column(name = "radiator_length", columnDefinition = "TEXT")
    private String radiatorLength;

    @Column(name = "fan_size", columnDefinition = "TEXT")
    private String fanSize;

    @Column(name = "fan_connector", columnDefinition = "TEXT")
    private String fanConnector;


    //메인보드 상세 필드

    @Column(name = "chipset", columnDefinition = "TEXT")
    private String chipset;

    @Column(name = "memory_slots", columnDefinition = "TEXT")
    private String memorySlots;

    @Column(name = "vga_connection", columnDefinition = "TEXT")
    private String vgaConnection;

    @Column(name = "m2_slots", columnDefinition = "TEXT")
    private String m2Slots;

    @Column(name = "wireless_lan", columnDefinition = "TEXT")
    private String wirelessLan;

    @Column(name = "form_factor", columnDefinition = "TEXT")
    private String formFactor;

    @Column(name = "memory_spec", columnDefinition = "TEXT")
    private String memorySpec;

    //램 상세 필드
    @Column(name = "device_type", columnDefinition = "TEXT")
    private String deviceType;

    @Column(name = "product_class", columnDefinition = "TEXT")
    private String productClass;

    @Column(name = "capacity", columnDefinition = "TEXT")
    private String capacity;

    @Column(name = "ram_count", columnDefinition = "TEXT")
    private String ramCount;

    @Column(name = "clock_speed", columnDefinition = "TEXT")
    private String clockSpeed;

    @Column(name = "ram_timing", columnDefinition = "TEXT")
    private String ramTiming;

    @Column(name = "heatsink_presence", columnDefinition = "TEXT")
    private String heatsinkPresence;

    //그래픽카드 상세 필드
    @Column(name = "nvidia_chipset", columnDefinition = "TEXT")
    private String nvidiaChipset;

    @Column(name = "amd_chipset", columnDefinition = "TEXT")
    private String amdChipset;

    @Column(name = "intel_chipset", columnDefinition = "TEXT")
    private String intelChipset;

    @Column(name = "gpu_interface", columnDefinition = "TEXT")
    private String gpuInterface;

    @Column(name = "gpu_memory_capacity", columnDefinition = "TEXT")
    private String gpuMemoryCapacity;

    @Column(name = "output_ports", columnDefinition = "TEXT")
    private String outputPorts;

    @Column(name = "recommended_psu", columnDefinition = "TEXT")
    private String recommendedPsu;

    @Column(name = "fan_count", columnDefinition = "TEXT")
    private String fanCount;

    @Column(name = "gpu_length", columnDefinition = "TEXT")
    private String gpuLength;

    // SSD 상세 필드
    @Column(name = "ssd_interface", columnDefinition = "TEXT")
    private String ssdInterface;

    @Column(name = "memory_type", columnDefinition = "TEXT")
    private String memoryType;

    @Column(name = "ram_mounted", columnDefinition = "TEXT")
    private String ramMounted;

    @Column(name = "sequential_read", columnDefinition = "TEXT")
    private String sequentialRead;

    @Column(name = "sequential_write", columnDefinition = "TEXT")
    private String sequentialWrite;

    // HDD 상세 필드

    @Column(name = "hdd_series", columnDefinition = "TEXT")
    private String hddSeries;

    @Column(name = "disk_capacity", columnDefinition = "TEXT")
    private String diskCapacity;

    @Column(name = "rotation_speed", columnDefinition = "TEXT")
    private String rotationSpeed;

    @Column(name = "buffer_capacity", columnDefinition = "TEXT")
    private String bufferCapacity;

    @Column(name = "hdd_warranty", columnDefinition = "TEXT")
    private String hddWarranty;

    //케이스 상세 필드
    @Column(name = "case_size", columnDefinition = "TEXT")
    private String caseSize;

    @Column(name = "supported_board", columnDefinition = "TEXT")
    private String supportedBoard;

    @Column(name = "side_panel", columnDefinition = "TEXT")
    private String sidePanel;

    @Column(name = "psu_length", columnDefinition = "TEXT")
    private String psuLength;

    @Column(name = "vga_length", columnDefinition = "TEXT")
    private String vgaLength;

    @Column(name = "cpu_cooler_height_limit", columnDefinition = "TEXT")
    private String cpuCoolerHeightLimit;

    //파워 상세 필드
    @Column(name = "rated_output", columnDefinition = "TEXT")
    private String ratedOutput;

    @Column(name = "eighty_plus_cert", columnDefinition = "TEXT")
    private String eightyPlusCert;

    @Column(name = "eta_cert", columnDefinition = "TEXT")
    private String etaCert;

    @Column(name = "cable_connection", columnDefinition = "TEXT")
    private String cableConnection;

    @Column(name = "pcie_16pin", columnDefinition = "TEXT")
    private String pcie16pin;

    @Column(name = "created_at", updatable = false)
    @CreationTimestamp
    private LocalDateTime createdAt;

    @Column(name = "updated_at")
    @UpdateTimestamp
    private LocalDateTime updatedAt;
}