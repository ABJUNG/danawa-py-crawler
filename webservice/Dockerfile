# JDK 17 이미지를 기반으로 설정 (.idea/misc.xml 참고)
FROM maven:3.9-eclipse-temurin-17-focal AS builder

# 작업 디렉토리 설정
WORKDIR /app

# Maven 관련 파일 복사
COPY ./pom.xml ./pom.xml
COPY ./.mvn ./.mvn
COPY ./mvnw .
COPY ./mvnw.cmd .

# --- 👇 [핵심 수정] ---
# Linux 빌드 환경에서 mvnw 파일에 실행 권한을 부여합니다.
RUN chmod +x ./mvnw
# --- [수정 완료] ---

# 의존성 다운로드 (소스코드 변경과 별도로 캐싱하기 위함)
RUN ./mvnw dependency:go-offline -B

# 소스코드 복사
COPY ./src ./src

# 애플리케이션 빌드 (테스트는 생략)
RUN ./mvnw package -DskipTests

# --- 실행 단계 ---
FROM eclipse-temurin:17-jre-focal

WORKDIR /app

# 빌드된 JAR 파일 복사
COPY --from=builder /app/target/*.jar app.jar

# 애플리케이션 실행 포트 노출
EXPOSE 8080

# 애플리케이션 실행
ENTRYPOINT ["java", "-jar", "app.jar"]