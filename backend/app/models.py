"""Strict public API inputs; draft controls never supply authoritative outputs."""

from typing import Self
from uuid import UUID
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StrictBool,
    StrictInt,
    field_validator,
    model_validator,
)


class StrictModel(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")


class Draft(StrictModel):
    values: list[StrictInt] = Field(min_length=4, max_length=4)
    connectivity_mask: StrictInt = Field(ge=0, le=15)
    fault_injection: StrictBool

    @model_validator(mode="after")
    def bounds(self) -> Self:
        if any(not 0 <= v <= 255 for v in self.values):
            raise ValueError("sensor values must be0..255")
        if any(v > 100 for v in self.values) and not self.fault_injection:
            raise ValueError("range faults require explicit fault_injection")
        return self


class Version(StrictModel):
    generation: StrictInt = Field(ge=0)
    revision: StrictInt = Field(ge=0)


class Request(Version):
    request_id: str

    @field_validator("request_id")
    @classmethod
    def identifier(cls, value: str) -> str:
        return str(UUID(value))


class Append(Request):
    sample: Draft


class Batch(Request):
    samples: list[Draft] = Field(min_length=1, max_length=600)
