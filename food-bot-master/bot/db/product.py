from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship

from db.category import Category
from db.base import Base


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, unique=True, autoincrement=True)

    name_ukr = Column(String, nullable=False)
    name_en = Column(String, nullable=False)

    price = Column(Integer, nullable=False)
    calories = Column(Integer, nullable=False)

    url = Column(String)

    category_id = Column(Integer, ForeignKey("categories.id"))
    category = relationship(Category, backref="products")

    def name(self, locale):
        return self.name_ukr if locale == "ukr" else self.name_en
