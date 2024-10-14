from sqlalchemy import Column, Integer, String
from db.base import Base


class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, unique=True, autoincrement=True)

    name_ukr = Column(String, nullable=False)
    name_en = Column(String, nullable=False)

    def name(self, locale):
        return self.name_ukr if locale == "ukr" else self.name_en
