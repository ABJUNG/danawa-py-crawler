import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import pymysql

# [수정] Google Generative AI (Gemini API) 사용
import google.generativeai as genai

# --- 1. DB 설정 (로컬 모드) ---
DB_HOST = os.environ.get("DB_HOST", "localhost")
DB_PORT = int(os.environ.get("DB_PORT", "3307"))
DB_USER = os.environ.get("DB_USER", "root")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "1234")
DB_NAME = os.environ.get("DB_NAME", "danawa")

# --- 2. Google Gemini API 설정 ---
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")

if not GOOGLE_API_KEY:
    print("오류: GOOGLE_API_KEY 환경 변수가 설정되지 않았습니다.")
    print("     .env 파일에 GOOGLE_API_KEY=your-api-key를 추가하세요.")
    exit()

# Gemini API 초기화
genai.configure(api_key=GOOGLE_API_KEY)

# --- 3. AI 모델 및 프롬프트 설정 ---
model = genai.GenerativeModel('gemini-2.5-flash')

SUMMARIZE_PROMPT_TEMPLATE = """
당신은 PC 부품 전문 리뷰어입니다.
다음 텍스트는 퀘이사존의 전문가 리뷰 본문입니다.
이 리뷰의 핵심 내용(장점, 단점, 주요 성능 포인트, 결론)을 3~5줄로 요약해 주세요.
"요약:" 이라는 말은 빼고, 본문 내용만 생성해 주세요.

--- 리뷰 원본 ---
{review_text}
--- 요약 ---
"""

def summarize_text(text_to_summarize):
    """Google Gemini API를 호출하여 텍스트를 요약합니다."""
    try:
        truncated_text = text_to_summarize[:15000]
        
        prompt = SUMMARIZE_PROMPT_TEMPLATE.format(review_text=truncated_text)
        
        # Gemini API 호출
        response = model.generate_content(prompt)
        
        return response.text.strip()
    except Exception as e:
        print(f"   -> AI 요약 실패: {e}")
        return None

def main():
    try:
        # 로컬 MySQL 연결
        print(f"로컬 MySQL DB 연결 중... ({DB_HOST}:{DB_PORT}/{DB_NAME})")
        
        db_url = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}?charset=utf8mb4"
        
        engine = create_engine(
            db_url,
            pool_pre_ping=True,
            pool_recycle=3600,
            echo=False
        )
        
        Session = sessionmaker(bind=engine)
        session = Session()
        print("DB 연결 성공. AI 요약 작업을 시작합니다...")

        # 1. 요약이 필요한 리뷰 조회
        reviews_to_summarize = session.execute(
            text("SELECT id, raw_text FROM community_reviews WHERE ai_summary IS NULL")
        ).fetchall()

        if not reviews_to_summarize:
            print("새롭게 요약할 리뷰가 없습니다. 종료합니다.")
            session.close()
            connector.close()
            return

        print(f"총 {len(reviews_to_summarize)}개의 리뷰를 요약합니다.")

        # 2. 각 리뷰를 순회하며 AI 요약
        update_count = 0
        for review in reviews_to_summarize:
            review_id = review[0]
            raw_text = review[1]
            
            print(f"   -> 리뷰 ID {review_id} 요약 시도...")
            
            ai_summary = summarize_text(raw_text)
            
            if ai_summary:
                session.execute(
                    text("UPDATE community_reviews SET ai_summary = :summary WHERE id = :id"),
                    {"summary": ai_summary, "id": review_id}
                )
                print(f"   -> 리뷰 ID {review_id} 요약 완료.")
                update_count += 1
            else:
                print(f"   -> 리뷰 ID {review_id} 요약 실패, 건너뜁니다.")
        
        # 3. 루프가 끝난 후 한 번만 커밋
        if update_count > 0:
            print(f"\n총 {update_count}개의 요약본을 DB에 일괄 저장(커밋)합니다...")
            session.commit()
            print("커밋 완료.")
        else:
            print("\n업데이트할 항목이 없어 커밋을 건너뜁니다.")

        session.close()
        print("모든 AI 요약 작업을 완료했습니다.")

    except Exception as e:
        print(f"DB 연결 또는 작업 중 오류 발생: {e}")
    finally:
        print("DB 연결 종료.")

if __name__ == "__main__":
    main()