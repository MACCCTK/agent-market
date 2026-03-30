from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, Field, field_validator


class ApiErrorResponse(BaseModel):
    code: str
    message: str
    request_id: str


class PaginationQuery(BaseModel):
    page: int = Field(default=0, ge=0)
    size: int = Field(default=20, ge=1)
    sort: str = "id,asc"


class SearchOpenClawQuery(BaseModel):
    keyword: str | None = None
    page: int = Field(default=0, ge=0)
    size: int = Field(default=20, ge=1)


class PriceRangeMixin(BaseModel):
    price_min: Decimal | None = None
    price_max: Decimal | None = None

    @field_validator("price_max")
    @classmethod
    def check_price_range(cls, value: Decimal | None, info):
        price_min = info.data.get("price_min")
        if value is not None and price_min is not None and price_min > value:
            raise ValueError("price_max must be >= price_min")
        return value
