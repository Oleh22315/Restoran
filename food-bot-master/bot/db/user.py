from sqlalchemy import BigInteger, Column, String

from db.base import Base


class User(Base):
    __tablename__ = "users"

    id = Column(BigInteger, primary_key=True, unique=True, autoincrement=False)
    locale = Column(String, nullable=False, default="en")
