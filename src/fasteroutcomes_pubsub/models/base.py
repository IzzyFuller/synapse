"""Base models for pub-sub messaging."""

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class CamelCaseModel(BaseModel):
    """Base model that uses camelCase for field aliases to match Firestore and JSON APIs."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )
