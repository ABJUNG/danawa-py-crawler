# 크롤러 사용법

## 대화형 메뉴 (추천)

```bash
docker-compose up crawler
```

또는

```bash
docker-compose run -it --rm crawler python crawler.py
```

메뉴가 나타나면 번호 선택:
- **1**: 다나와만 (5-10분) - 기본값
- **2**: 다나와 + 리뷰 (15-25분)
- **3**: 다나와 + 벤치마크 (20-30분)
- **4**: 모두 수집 (30-45분)
- **0**: 취소

## 플래그 사용 (자동화)

```bash
# 다나와만 (기본값)
docker-compose run --rm crawler python crawler.py

# 리뷰 포함
docker-compose run --rm crawler python crawler.py --reviews

# 벤치마크 포함
docker-compose run --rm crawler python crawler.py --benchmarks

# 모두 포함
docker-compose run --rm crawler python crawler.py --reviews --benchmarks
```

## 리뷰 AI 요약 생성

```bash
docker-compose up summarizer
```
