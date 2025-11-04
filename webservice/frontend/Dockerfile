# Node.js LTS 버전을 기반 이미지로 사용
FROM node:lts-alpine

# 작업 디렉토리 설정
WORKDIR /app

# package.json과 package-lock.json 복사
COPY package.json package-lock.json ./

# 의존성 설치 (package-lock.json 기반으로 정확한 버전 설치)
RUN npm install

# 소스 코드 복사
COPY . .

# 애플리케이션 실행 포트 노출
EXPOSE 3000

# 개발 서버 실행 (package.json의 스크립트 참고)
CMD ["npm", "start"]