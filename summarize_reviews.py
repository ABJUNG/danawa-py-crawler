import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from google.cloud.sql.connector import Connector
import pymysql

# [수정] Vertex AI SDK 임포트
import vertexai
from vertexai.generative_models import GenerativeModel, GenerationConfig

# --- 1. DB 설정 (Cloud Run 환경 변수에서 가져옴) ---
DB_USER = os.environ.get("DB_USER")
DB_PASSWORD = os.environ.get("DB_PASS")
DB_NAME = os.environ.get("DB_NAME")
INSTANCE_CONNECTION_NAME = os.environ.get("INSTANCE_CONNECTION_NAME")

# --- 2. Vertex AI 프로젝트 설정 (환경 변수) ---
PROJECT_ID = os.environ.get("GCP_PROJECT_ID") # 👈 [추가] GCP 프로젝트 ID
LOCATION = "asia-northeast3"                 # 서울 리전

if not all([DB_USER, DB_PASSWORD, DB_NAME, INSTANCE_CONNECTION_NAME, PROJECT_ID]):
    print("오류: 필요한 환경 변수(DB_*, INSTANCE_*, GCP_PROJECT_ID)가 모두 설정되지 않았습니다.")
    exit()

# [수정] Vertex AI 초기화 (API 키 필요 없음)
vertexai.init(project=PROJECT_ID, location=LOCATION)

# --- 3. AI 모델 및 프롬프트 설정 ---
generation_config = GenerationConfig(temperature=0.5) # [수정] GenerationConfig 객체 사용
model = GenerativeModel(
    'gemini-2.5-flash', # Vertex AI 모델명
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
    """Vertex AI Gemini API를 호출하여 텍스트를 요약합니다."""
    try:
        truncated_text = text_to_summarize[:15000]
        
        prompt = SUMMARIZE_PROMPT_TEMPLATE.format(review_text=truncated_text)
        
        # [수정] Vertex AI SDK 호출 방식
        response = model.generate_content(prompt)
        
        return response.text.strip()
    except Exception as e:
        print(f"   -> AI 요약 실패: {e}")
        return None

def main():
    connector = None
    try:
        # [수정] Cloud SQL Connector 사용
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
        if connector:
            connector.close()
            print("DB 연결 종료.")

if __name__ == "__main__":
    main()