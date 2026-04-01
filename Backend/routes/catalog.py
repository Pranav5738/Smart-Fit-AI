from typing import Optional

from fastapi import APIRouter, Query

from models.schemas import CatalogProductResponse
from services.catalog import CatalogService

router = APIRouter(prefix="/catalog", tags=["Catalog"])
catalog_service = CatalogService()


def _parse_query_list(raw_value: Optional[str]) -> list[str]:
    if not raw_value:
        return []
    return [value.strip().lower() for value in raw_value.split(",") if value.strip()]


@router.get("/products", response_model=list[CatalogProductResponse])
def get_catalog_products(
    categories: Optional[str] = Query(default=None, description="Comma-separated category filters"),
    occasions: Optional[str] = Query(default=None, description="Comma-separated occasion filters"),
    weather: Optional[str] = Query(default=None, description="Comma-separated weather filters"),
    colors: Optional[str] = Query(default=None, description="Comma-separated color filters"),
    limit: int = Query(default=24, ge=1, le=100),
) -> list[CatalogProductResponse]:
    products = catalog_service.list_products(
        categories=_parse_query_list(categories),
        occasions=_parse_query_list(occasions),
        weather=_parse_query_list(weather),
        colors=_parse_query_list(colors),
        limit=limit,
    )
    return [CatalogProductResponse(**product) for product in products]


@router.get("/brands", response_model=list[str])
def get_catalog_brands() -> list[str]:
    return catalog_service.list_brands()
