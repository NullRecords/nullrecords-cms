"""APICredential ORM model — stores third-party API keys in the local DB."""

from sqlalchemy import Column, Integer, String, Text

from app.core.database import Base


class APICredential(Base):
    __tablename__ = "api_credentials"

    id = Column(Integer, primary_key=True, index=True)
    service = Column(String, nullable=False, unique=True, index=True)
    api_key = Column(String, nullable=False)
    extra_json = Column(Text, default="{}")  # JSON blob for additional config
