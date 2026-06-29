from uuid import UUID
from decimal import Decimal
from fastapi import HTTPException
from sqlalchemy.orm import Session
from app.repositories.product_repository import ProductRepository
from app.schemas.product_schema import (
    CompanyProductUpdate,
    ProductCreate,
    SalesQuantityCreate,
    SellerProductCreate,
    SellerProductUpdate,
)
from app.services.product_resolver import build_normalized_key


def build_product_name(brand: str | None, model: str | None, fallback: str | None = None) -> str:
    name = " ".join(part.strip() for part in (brand, model) if part and part.strip())
    return name or fallback or "Adsiz Urun"


class ProductService:
    def __init__(self, db: Session):
        self.repo = ProductRepository(db)

    def create_product(self, payload: ProductCreate):
        payload = payload.model_copy(
            update={"name": build_product_name(payload.brand, payload.model, payload.name)}
        )
        normalized_key = build_normalized_key(payload)
        if normalized_key:
            existing_product = self.repo.get_product_by_normalized_key(normalized_key)
            if existing_product:
                return existing_product

        fingerprint_product = self.repo.find_product_by_fingerprint(payload)
        if fingerprint_product:
            return self.repo.complete_product_resolution(
                product=fingerprint_product,
                payload=payload,
                normalized_key=normalized_key,
            )

        return self.repo.create_product(
            payload.model_copy(update={"normalized_key": normalized_key})
        )

    def list_products(self, limit: int = 100, offset: int = 0):
        return self.repo.list_products(limit, offset)

    def get_product(self, product_id: UUID):
        obj = self.repo.get_product(product_id)
        if not obj:
            raise HTTPException(status_code=404, detail="Product not found")
        return obj

    def _serialize_seller_product(self, seller_product):
        product = self.repo.get_product(seller_product.product_id)
        commission_rate = self.repo.get_commission_rate(
            marketplace=seller_product.marketplace,
            category_id=product.category_id if product else None,
        )

        return {
            "id": seller_product.id,
            "company_id": seller_product.company_id,
            "product_id": seller_product.product_id,
            "marketplace": seller_product.marketplace,
            "display_name": seller_product.display_name,
            "marketplace_url": seller_product.marketplace_url,
            "marketplace_product_id": seller_product.marketplace_product_id,
            "our_price": seller_product.our_price,
            "cost_price": seller_product.cost_price,
            "commission_rate": commission_rate or Decimal("0"),
            "shipping_cost": seller_product.shipping_cost,
            "packaging_cost": seller_product.packaging_cost,
            "stock_quantity": seller_product.stock_quantity,
            "min_margin_rate": seller_product.min_margin_rate,
            "is_active": seller_product.is_active,
            "created_at": seller_product.created_at,
        }

    def create_seller_product(self, payload: SellerProductCreate):
        existing_seller_product = self.repo.get_seller_product_by_company_product_marketplace(
            company_id=payload.company_id,
            product_id=payload.product_id,
            marketplace=payload.marketplace,
        )
        if existing_seller_product:
            raise HTTPException(
                status_code=409,
                detail=(
                    "Bu ürün seçtiğiniz pazaryerinde zaten şirket listenizde var. "
                    "Mevcut ürünü düzenleyebilir veya farklı bir pazaryeri seçebilirsiniz."
                ),
            )

        return self._serialize_seller_product(self.repo.create_seller_product(payload))

    def update_company_product(self, company_id: UUID, product_id: UUID, payload: CompanyProductUpdate):
        product = self.repo.get_product(product_id)
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")

        seller_products = self.repo.list_seller_products_by_company_product(company_id, product_id)
        if not seller_products:
            raise HTTPException(status_code=404, detail="Company product not found")

        product_values = payload.model_dump(
            exclude_unset=True,
            include={
                "name",
                "brand",
                "model",
                "category",
                "category_id",
                "color",
                "connection_type",
                "storage_capacity",
                "ram_capacity",
                "sim_type",
                "switch_type",
                "keyboard_layout",
                "barcode",
                "description",
            },
        )

        merged_product = ProductCreate(
            name=build_product_name(
                product_values.get("brand", product.brand),
                product_values.get("model", product.model),
                product_values.get("name", product.name),
            ),
            brand=product_values.get("brand", product.brand),
            model=product_values.get("model", product.model),
            category=product_values.get("category", product.category),
            category_id=product_values.get("category_id", product.category_id),
            color=product_values.get("color", product.color),
            connection_type=product_values.get("connection_type", product.connection_type),
            storage_capacity=product_values.get("storage_capacity", product.storage_capacity),
            ram_capacity=product_values.get("ram_capacity", product.ram_capacity),
            sim_type=product_values.get("sim_type", product.sim_type),
            switch_type=product_values.get("switch_type", product.switch_type),
            keyboard_layout=product_values.get("keyboard_layout", product.keyboard_layout),
            barcode=product_values.get("barcode", product.barcode),
            description=product_values.get("description", product.description),
        )
        product_values["name"] = merged_product.name
        normalized_key = build_normalized_key(merged_product)
        if normalized_key:
            existing_product = self.repo.get_product_by_normalized_key(normalized_key)
            if existing_product and existing_product.id != product_id:
                raise HTTPException(
                    status_code=409,
                    detail=(
                        "Bu ürün bilgileri sistemdeki başka bir ürünle eşleşiyor. "
                        "Lütfen mevcut ürünü düzenleyin veya ayırt edici bilgileri kontrol edin."
                    ),
                )
            product_values["normalized_key"] = normalized_key

        if product_values:
            self.repo.update_product(product, product_values)

        seller_values = payload.model_dump(
            exclude_unset=True,
            include={
                "display_name",
                "marketplace_url",
                "marketplace_product_id",
                "our_price",
                "cost_price",
                "shipping_cost",
                "packaging_cost",
                "stock_quantity",
                "min_margin_rate",
            },
        )

        updated_seller_products = []
        if seller_values:
            seller_update = SellerProductUpdate(**seller_values)
            for seller_product in seller_products:
                updated_seller_products.append(
                    self.repo.update_seller_product(seller_product, seller_update)
                )
        else:
            updated_seller_products = seller_products

        return [
            self._serialize_seller_product(seller_product)
            for seller_product in updated_seller_products
        ]

    def delete_company_product(self, company_id: UUID, product_id: UUID):
        seller_products = self.repo.list_seller_products_by_company_product(company_id, product_id)
        if not seller_products:
            raise HTTPException(status_code=404, detail="Company product not found")

        self.repo.deactivate_seller_products_by_company_product(company_id, product_id)
        return {"status": "deleted", "product_id": str(product_id)}

    def list_seller_products_by_company(self, company_id: UUID, limit: int = 100, offset: int = 0):
        seller_products = self.repo.list_seller_products_by_company(company_id, limit, offset)
        return [
            self._serialize_seller_product(seller_product)
            for seller_product in seller_products
        ]

    def update_price(self, seller_product_id: UUID, payload, user_id=None):
        sp = self.repo.get_seller_product(seller_product_id)
        if not sp:
            raise HTTPException(status_code=404, detail="Seller product not found")
        return self._serialize_seller_product(
            self.repo.update_price(
                sp,
                payload.new_price,
                payload.change_source,
                user_id,
                payload.recommendation_id,
            )
        )

    def update_stock(self, seller_product_id: UUID, payload):
        sp = self.repo.get_seller_product(seller_product_id)
        if not sp:
            raise HTTPException(status_code=404, detail="Seller product not found")
        return self._serialize_seller_product(
            self.repo.update_stock(sp, payload.new_stock, payload.change_source)
        )

    def create_sales_quantity(self, seller_product_id: UUID, payload: SalesQuantityCreate):
        sp = self.repo.get_seller_product(seller_product_id)
        if not sp:
            raise HTTPException(status_code=404, detail="Seller product not found")
        if payload.sales_quantity < 0:
            raise HTTPException(status_code=422, detail="Sales quantity cannot be negative")
        current_stock = sp.stock_quantity or 0
        if payload.sales_quantity > current_stock:
            raise HTTPException(
                status_code=422,
                detail="Satış miktarı mevcut stoktan fazla olamaz.",
            )
        return self.repo.create_sales_quantity(sp, payload)
