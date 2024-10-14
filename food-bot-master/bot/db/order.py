from sqlalchemy import Boolean, Column, Integer, String, ForeignKey, Table
from sqlalchemy.orm import relationship

from db.base import Base
from db.user import User
from db.product import Product

product_order_association = Table(
    "product_orders",
    Base.metadata,
    Column("id", Integer, primary_key=True, unique=True, autoincrement=True),
    Column("product_id", Integer, ForeignKey("products.id")),
    Column("order_id", Integer, ForeignKey("orders.id")),
)


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, unique=True, autoincrement=True)

    user_id = Column(Integer, ForeignKey("users.id"))
    user = relationship(User, backref="orders")
    phone = Column(String, nullable=False)
    location = Column(String, nullable=False)

    delivery_type = Column(String, nullable=True)

    paid = Column(Boolean, nullable=False, default=False)
    price = Column(Integer, nullable=False)

    products = relationship(Product, secondary=product_order_association, backref="orders")

    def name(self, locale):
        return self.name_ukr if locale == "ukr" else self.name_en
