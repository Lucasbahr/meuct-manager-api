from pydantic import BaseModel, ConfigDict


class GymResponse(BaseModel):
    id: int
    name: str

    model_config = ConfigDict(from_attributes=True)


class GymCreate(BaseModel):
    name: str
