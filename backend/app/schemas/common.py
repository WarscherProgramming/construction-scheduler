from pydantic import BaseModel, ConfigDict, model_validator


MAX_LONG_TEXT_LENGTH = 10_000


class MutationModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class UpdateMutationModel(MutationModel):
    @model_validator(mode="after")
    def require_at_least_one_field(self):
        if not self.model_fields_set:
            raise ValueError("At least one field is required")
        return self


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class MessageResponse(BaseModel):
    message: str
