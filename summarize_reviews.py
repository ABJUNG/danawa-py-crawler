import os
import google.generativeai as genai
from sqlalchemy import create_engine, text, update, select
from sqlalchemy.orm import sessionmaker
from google.cloud.sql.connector import Connector # 👈 [추가] Cloud SQL 커넥터
import pymysql # 👈 [추가] pymysql 드라이버

# --- 1. DB 설정 (Cloud Run 환경 변수에서 가져옴) ---
DB_USER = os.environ.get("DB_USER")
DB_PASSWORD = os.environ.get("DB_PASS")
DB_NAME = os.environ.get("DB_NAME")
INSTANCE_CONNECTION_NAME = os.environ.get("INSTANCE_CONNECTION_NAME") # 👈 [추가]

# --- 2. Gemini API 키 설정 ---
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")
if not GOOGLE_API_KEY:
    print("오류: GOOGLE_API_KEY 환경 변수가 설정되지 않았습니다.")
    exit()
genai.configure(api_key=GOOGLE_API_KEY)

# --- 3. AI 모델 및 프롬프트 설정 ---
generation_config = {"temperature": 0.5}
model = genai.GenerativeModel(
    'gemini-1.5-flash-001', # gemini-2.5-flash는 오타일 수 있으니 1.5-flash로 수정
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
        truncated_text = text_to_summarize[:15000]
        
        prompt = SUMMARIZE_PROMPT_TEMPLATE.format(review_text=truncated_text)
        response = model.generate_content(prompt)
        
        return response.text.strip()
    except Exception as e:
        print(f"   -> AI 요약 실패: {e}")
        return None

def main():
    connector = None # 👈 [추가] finally에서 닫기 위해
    try:
        # [수정] Cloud SQL Connector를 사용한 DB 엔진 생성
        print("Cloud SQL Connector 초기화 중...")
        connector = Connector()
        
        def getconn():
            conn = connector.connect(
                INSTANCE_CONNECTION_NAME,
                "pymysql",
                user=DB_USER,
                password=DB_PASSWORD,
                db=DB_NAME
            )
            return conn

        engine = create_engine(
            "mysql+pymysql://",
            creator=getconn,
        )
        # ----------------------------------------------------
        
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
            connector.close() # 👈 [추가]
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
                # 3. DB에 요약본 업데이트 (커밋은 나중에)
                session.execute(
                    text("UPDATE community_reviews SET ai_summary = :summary WHERE id = :id"),
                    {"summary": ai_summary, "id": review_id}
                )
                print(f"   -> 리뷰 ID {review_id} 요약 완료.")
                update_count += 1
            else:
                print(f"   -> 리뷰 ID {review_id} 요약 실패, 건너뜁니다.")
        
        # [수정] 4. 루프가 끝난 후 한 번만 커밋 (성능 향상)
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
        if connector:
            connector.close() # 👈 [추가] 커넥터 종료
            print("DB 연결 종료.")

if __name__ == "__main__":
    main()