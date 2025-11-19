/**
 * 부품명에서 용량/개수 정보를 추출하는 유틸리티 함수
 */

/**
 * 상품명에서 용량 정보 추출 (SSD, HDD)
 * 예: "삼성전자 990 PRO M.2 NVMe (1TB)" -> "1TB"
 *     "Western Digital WD BLACK SN850X M.2 NVMe (2TB)" -> "2TB"
 */
export function extractCapacityFromName(name) {
    if (!name) return null;
    
    // 괄호 안의 용량 정보 추출: (1TB), (2TB), (512GB) 등
    const capacityMatch = name.match(/\((\d+(?:\.\d+)?\s*(?:TB|GB))\)/i);
    if (capacityMatch) {
        return capacityMatch[1];
    }
    
    // 괄호 없이 용량이 포함된 경우: "1TB", "2TB" 등
    const directMatch = name.match(/(\d+(?:\.\d+)?\s*(?:TB|GB))/i);
    if (directMatch) {
        return directMatch[1];
    }
    
    return null;
}

/**
 * 상품명에서 RAM 패키지 개수 추출
 * 예: "ESSENCORE KLEVV DDR5-6000 CL30 URBANE V RGB 패키지 서린 (32GB (16GB x2))" -> "32GB (16GB x2)"
 *     "G.SKILL DDR5-6000 CL32 TRIDENT Z5 NEO RGB J 패키지" -> "J 패키지" (2개)
 *     "Samsung DDR5 32GB (16GB x2)" -> "32GB (16GB x2)"
 */
export function extractRamPackageFromName(name) {
    if (!name) return null;
    
    // 패턴 1: "32GB (16GB x2)" 또는 "32GB(16GBx2)" - 괄호 안에 패키지 정보
    const pattern1 = name.match(/(\d+GB)\s*\((\d+GB)\s*x\s*(\d+)\)/i);
    if (pattern1) {
        const totalCapacity = pattern1[1];  // 예: "32GB"
        const singleCapacity = pattern1[2];  // 예: "16GB"
        const count = pattern1[3];  // 예: "2"
        return `${totalCapacity} (${singleCapacity} x${count})`;
    }
    
    // 패턴 2: "32GB(16Gx2)" - 축약형 (G만 사용)
    const pattern2 = name.match(/(\d+GB)\((\d+)Gx(\d+)\)/i);
    if (pattern2) {
        const totalCapacity = pattern2[1];  // 예: "32GB"
        const singleCapacityNum = pattern2[2];  // 예: "16"
        const count = pattern2[3];  // 예: "2"
        return `${totalCapacity} (${singleCapacityNum}GB x${count})`;
    }
    
    // 패턴 3: "32GB(16GBx2)" - 공백 없음
    const pattern3 = name.match(/(\d+GB)\((\d+GB)x(\d+)\)/i);
    if (pattern3) {
        const totalCapacity = pattern3[1];
        const singleCapacity = pattern3[2];
        const count = pattern3[3];
        return `${totalCapacity} (${singleCapacity} x${count})`;
    }
    
    // 패턴 4: "J 패키지", "K 패키지" 등 (J=2개, K=4개)
    const packageMatch = name.match(/([JK]\s*패키지)/i);
    if (packageMatch) {
        const packageType = packageMatch[1].toUpperCase();
        if (packageType.includes('J')) {
            return '2개 (J 패키지)';
        } else if (packageType.includes('K')) {
            return '4개 (K 패키지)';
        }
        return packageMatch[1];
    }
    
    // 패턴 5: x2, x4 패턴 추출: "16GB x2", "8GB x4" 등
    const xPattern = name.match(/(\d+GB)\s*x\s*(\d+)/i);
    if (xPattern) {
        const singleCapacity = xPattern[1];
        const count = xPattern[2];
        const singleCapacityNum = parseInt(singleCapacity.replace('GB', ''));
        const totalCapacityNum = singleCapacityNum * parseInt(count);
        return `${totalCapacityNum}GB (${singleCapacity} x${count})`;
    }
    
    return null;
}

/**
 * 부품명을 포맷팅하여 용량/개수 정보를 함께 표시
 * @param {string} name - 원본 상품명
 * @param {string} category - 부품 카테고리
 * @returns {object} { displayName: 포맷된 이름, capacity: 용량 정보, package: 패키지 정보 }
 */
export function formatPartName(name, category) {
    if (!name) return { displayName: name, capacity: null, package: null };
    
    let displayName = name;
    let capacity = null;
    let packageInfo = null;
    
    // SSD, HDD의 경우 용량 추출
    if (category === 'SSD' || category === 'HDD') {
        capacity = extractCapacityFromName(name);
        // 용량 정보가 괄호 안에 있으면 제거 (중복 방지)
        if (capacity) {
            // 괄호와 용량 정보 제거: "Western Digital WD BLACK SN850X M.2 NVMe (1TB)" -> "Western Digital WD BLACK SN850X M.2 NVMe"
            displayName = name.replace(/\s*\([^)]*\)\s*$/, '').trim();
        }
    }
    
    // RAM의 경우 패키지 정보 추출
    if (category === 'RAM') {
        packageInfo = extractRamPackageFromName(name);
        // 패키지 정보가 괄호 안에 있으면 제거 (중복 방지)
        if (packageInfo) {
            // "32GB (16GB x2)" 패턴이 포함된 경우 괄호 부분 제거
            // 예: "ESSENCORE KLEVV DDR5-6000 CL30 URBANE V RGB 패키지 서린 (32GB (16GB x2))" 
            // -> "ESSENCORE KLEVV DDR5-6000 CL30 URBANE V RGB 패키지 서린"
            displayName = name.replace(/\s*\([^)]*\)\s*$/, '').trim();
            // 중첩된 괄호도 처리
            displayName = displayName.replace(/\s*\([^)]*\)\s*$/, '').trim();
        }
    }
    
    return {
        displayName,
        capacity,
        package: packageInfo
    };
}

