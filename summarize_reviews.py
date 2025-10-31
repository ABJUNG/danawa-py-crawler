import os
import google.generativeai as genai
from sqlalchemy import create_engine, text, update, select
from sqlalchemy.orm import sessionmaker

# --- 1. DB 설정 (crawler.py와 동일하게) ---
DB_USER = 'root'
DB_PASSWORD = '1234'
# (주의!) 이 스크립트를 Docker 밖(로컬)에서 실행한다면 DB_HOST를 'db'가 아닌 'localhost' (또는 3307 포트)로 접속해야 합니다.
# (만약 이 스크립트도 Docker로 실행한다면 'db'가 맞습니다.)
DB_HOST = 'db' # 
DB_PORT = '3306' # 1단계에서 DB 포트를 3307로 변경했었습니다.
DB_NAME = 'danawa'

# --- 2. Gemini API 키 설정 ---
# (API 키를 여기에 직접 넣거나, 환경 변수에서 가져오세요)
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")
if not GOOGLE_API_KEY:
    print("오류: GOOGLE_API_KEY 환경 변수가 설정되지 않았습니다.")
    exit()
genai.configure(api_key=GOOGLE_API_KEY)

# --- 3. AI 모델 및 프롬프트 설정 ---
generation_config = {"temperature": 0.5}
model = genai.GenerativeModel(

    'gemini-2.5-flash', # (또는 gemini-pro)
    generation_config=generation_config
)

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
    """Gemini API를 호출하여 텍스트를 요약합니다."""
    try:
        # (주의) 텍스트가 너무 길면 API 제한(예: 32k 토큰)에 걸릴 수 있습니다.
        # 실제로는 텍스트를 적절히 잘라서 보내야 할 수도 있습니다. (예: 앞 10000자)
        truncated_text = text_to_summarize[:15000]
        
        prompt = SUMMARIZE_PROMPT_TEMPLATE.format(review_text=truncated_text)
        response = model.generate_content(prompt)
        
        return response.text.strip()
    except Exception as e:
        print(f"  -> AI 요약 실패: {e}")
        return None

def main():
    try:
        engine = create_engine(f'mysql+mysqlconnector://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}')
        Session = sessionmaker(bind=engine)
        session = Session()
        print("DB 연결 성공. AI 요약 작업을 시작합니다...")

        # 1. 요약이 필요한 리뷰 조회 (ai_summary가 NULL인 것)
        reviews_to_summarize = session.execute(
            text("SELECT id, raw_text FROM community_reviews WHERE ai_summary IS NULL")
        ).fetchall()

        if not reviews_to_summarize:
            print("새롭게 요약할 리뷰가 없습니다. 종료합니다.")
            return

        print(f"총 {len(reviews_to_summarize)}개의 리뷰를 요약합니다.")

        # 2. 각 리뷰를 순회하며 AI 요약 및 DB 업데이트
        for review in reviews_to_summarize:
            review_id = review[0]
            raw_text = review[1]
            
            print(f"  -> 리뷰 ID {review_id} 요약 시도...")
            
            ai_summary = summarize_text(raw_text)
            
            if ai_summary:
                # 3. DB에 요약본 업데이트
                session.execute(
                    text("UPDATE community_reviews SET ai_summary = :summary WHERE id = :id"),
                    {"summary": ai_summary, "id": review_id}
                )
                session.commit()
                print(f"  -> 리뷰 ID {review_id} 요약 완료 및 저장 성공.")
            else:
                print(f"  -> 리뷰 ID {review_id} 요약 실패, 건너뜁니다.")

        session.close()
        print("모든 AI 요약 작업을 완료했습니다.")

    except Exception as e:
        print(f"DB 연결 또는 작업 중 오류 발생: {e}")

if __name__ == "__main__":
    main()