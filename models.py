from sqlalchemy.orm import declarative_base
from sqlalchemy import Column, Integer, String, DateTime, Text, BigInteger

Base = declarative_base()

class MessageLog(Base):
    __tablename__ = "messages"
    id = Column(Integer, primary_key=True, index=True)
    direction = Column(String(4))
    chat_id = Column(BigInteger)
    chat_title = Column(String(256))
    chat_type = Column(String(32))
    sender_id = Column(BigInteger)
    sender_username = Column(String(128))
    sender_first_name = Column(String(128))
    sender_last_name = Column(String(128))
    message_id = Column(BigInteger)
    date = Column(DateTime)
    text = Column(Text)
    raw_json = Column(Text)
