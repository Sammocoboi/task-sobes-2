import re

from pydantic import BaseModel, Field, field_validator, model_validator


class CampaignCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    geo: list[str] = Field(min_length=1)
    offer_id: int = Field(gt=0)
    domain_id: int = Field(gt=0)
    group_id: int = Field(gt=0)
    traffic_source_id: int = Field(gt=0)

    @field_validator("name")
    @classmethod
    def clean_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Укажите название кампании")
        return value

    @field_validator("geo")
    @classmethod
    def clean_geo(cls, value: list[str]) -> list[str]:
        codes = [item.strip().upper() for item in value]
        if not codes or any(not re.fullmatch(r"[A-Z]{2}", item) for item in codes):
            raise ValueError("ГЕО: двубуквенные коды стран, например RU или US")
        return list(dict.fromkeys(codes))


class OfferShares(BaseModel):
    offers: list[dict[str, int]] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_shares(self):
        ids = [item.get("offer_id") for item in self.offers]
        shares = [item.get("share") for item in self.offers]
        if any(not isinstance(item, int) or item <= 0 for item in ids) or len(ids) != len(set(ids)):
            raise ValueError("ID офферов должны быть уникальными положительными числами")
        if any(not isinstance(item, int) or item < 0 or item > 100 for item in shares) or sum(shares) != 100:
            raise ValueError("Сумма долей должна быть ровно 100%")
        return self


class OfferAdd(BaseModel):
    offer_id: int = Field(gt=0)
