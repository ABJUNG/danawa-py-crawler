package com.danawa.webservice.domain;

import jakarta.persistence.*;
import lombok.Getter;
import lombok.NoArgsConstructor;
import org.hibernate.annotations.CreationTimestamp;
import org.hibernate.annotations.UpdateTimestamp;

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

    // ▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼
    // CPU 상세 필드
    @Column(name = "manufacturer")
    private String manufacturer;

    @Column(name = "codename")
    private String codename;

    @Column(name = "cpu_series")
    private String cpuSeries;

    @Column(name = "cpu_class")
    private String cpuClass;

    @Column(name = "socket")
    private String socket;

    @Column(name = "cores")
    private String cores;

    @Column(name = "threads")
    private String threads;

    @Column(name = "integrated_graphics")
    private String integratedGraphics;

    @Column(name = "review_count")
    private Integer reviewCount;

    @Column(name = "core_type")
    private String coreType;

    //쿨러 상세 필드
    @Column(name = "product_type")
    private String productType;

    @Column(name = "cooling_method")
    private String coolingMethod;

    @Column(name = "air_cooling_form")
    private String airCoolingForm;

    @Column(name = "cooler_height")
    private String coolerHeight;

    @Column(name = "radiator_length")
    private String radiatorLength;

    @Column(name = "fan_size")
    private String fanSize;

    @Column(name = "fan_connector")
    private String fanConnector;


    //메인보드 상세 필드

    @Column(name = "chipset")
    private String chipset;

    @Column(name = "memory_slots")
    private String memorySlots;

    @Column(name = "vga_connection")
    private String vgaConnection;

    @Column(name = "m2_slots")
    private String m2Slots;

    @Column(name = "wireless_lan")
    private String wirelessLan;

    @Column(name = "form_factor")
    private String formFactor;

    @Column(name = "memory_spec")
    private String memorySpec;

    //램 상세 필드
    @Column(name = "device_type")
    private String deviceType;

    @Column(name = "product_class")
    private String productClass;

    @Column(name = "capacity")
    private String capacity;

    @Column(name = "ram_count")
    private String ramCount;

    @Column(name = "clock_speed")
    private String clockSpeed;

    @Column(name = "ram_timing")
    private String ramTiming;

    @Column(name = "heatsink_presence")
    private String heatsinkPresence;

    //그래픽카드 상세 필드
    @Column(name = "nvidia_chipset")
    private String nvidiaChipset;

    @Column(name = "amd_chipset")
    private String amdChipset;

    @Column(name = "intel_chipset")
    private String intelChipset;

    @Column(name = "gpu_interface")
    private String gpuInterface;

    @Column(name = "gpu_memory_capacity")
    private String gpuMemoryCapacity;

    @Column(name = "output_ports")
    private String outputPorts;

    @Column(name = "recommended_psu")
    private String recommendedPsu;

    @Column(name = "fan_count")
    private String fanCount;

    @Column(name = "gpu_length")
    private String gpuLength;

    // SSD 상세 필드
    @Column(name = "ssd_interface")
    private String ssdInterface;

    @Column(name = "memory_type")
    private String memoryType;

    @Column(name = "ram_mounted")
    private String ramMounted;

    @Column(name = "sequential_read")
    private String sequentialRead;

    @Column(name = "sequential_write")
    private String sequentialWrite;

    // HDD 상세 필드

    @Column(name = "hdd_series")
    private String hddSeries;

    @Column(name = "disk_capacity")
    private String diskCapacity;

    @Column(name = "rotation_speed")
    private String rotationSpeed;

    @Column(name = "buffer_capacity")
    private String bufferCapacity;

    @Column(name = "hdd_warranty")
    private String hddWarranty;

    //케이스 상세 필드
    @Column(name = "case_size")
    private String caseSize;

    @Column(name = "supported_board")
    private String supportedBoard;

    @Column(name = "side_panel")
    private String sidePanel;

    @Column(name = "psu_length")
    private String psuLength;

    @Column(name = "vga_length")
    private String vgaLength;

    @Column(name = "cpu_cooler_height_limit")
    private String cpuCoolerHeightLimit;

    @Column(name = "created_at", updatable = false)
    @CreationTimestamp
    private LocalDateTime createdAt;

    @Column(name = "updated_at")
    @UpdateTimestamp
    private LocalDateTime updatedAt;
}