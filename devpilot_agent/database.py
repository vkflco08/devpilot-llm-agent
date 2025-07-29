import os
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# 환경 변수에서 데이터베이스 URL 가져오기
# .env 파일에 DATABASE_URL="mysql+pymysql://user:password@host:3306/dbname" 형태로 설정
DATABASE_URL = os.getenv("DATABASE_URL", "mysql+pymysql://root:ss4015@localhost:3306/devpilot")

# SQLAlchemy 엔진 생성
engine = create_engine(DATABASE_URL, pool_pre_ping=True)

# 세션 생성기
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# ORM 모델의 베이스 클래스
Base = declarative_base()

# --- 데이터베이스 모델 정의 ---
class ChatMessage(Base):
    """
    채팅 메시지를 저장하기 위한 데이터베이스 모델.
    """
    __tablename__ = "chat_messages" # 데이터베이스 테이블 이름

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True, nullable=False) # 사용자 ID
    sender = Column(String(10), nullable=False) # 'user' 또는 'assistant'
    content = Column(Text, nullable=False) # 메시지 내용
    timestamp = Column(DateTime, default=func.now(), nullable=False) # 메시지 생성 시간

    def __repr__(self):
        return f"<ChatMessage(id={self.id}, user_id={self.user_id}, sender='{self.sender}', timestamp='{self.timestamp}')>"

# 데이터베이스 테이블 생성 함수
def create_db_tables():
    """
    정의된 ORM 모델에 따라 데이터베이스 테이블을 생성합니다.
    테이블이 이미 존재하면 생성하지 않습니다.
    """
    print("데이터베이스 테이블 생성/확인 중...")
    Base.metadata.create_all(bind=engine)
    print("데이터베이스 테이블 생성/확인 완료.")

# FastAPI 의존성 주입을 위한 DB 세션 함수
def get_db():
    """
    FastAPI의 Depends에 사용될 DB 세션 제너레이터.
    각 요청마다 새로운 세션을 생성하고, 요청 완료 후 세션을 닫습니다.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()