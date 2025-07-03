from aiogram.types import User
from typing import Any, Dict, Tuple

from ...models.base import PersonModel, MemberModel
from ...models.fields import fields

def make_person(user: User) -> PersonModel:
    """
    Make a [PersonModel] from Telegram's User.
    """
    return PersonModel(
        userId=user.id,
        userName=user.username,
        firstName=user.first_name,
        lastName=user.last_name,
    )


def make_person_team(data: Dict[str, Any]) -> Tuple[int, PersonModel]:
    """
    Extracts team id and person data from specifies dictionary.
    """
    teamId = data[fields(MemberModel).teamId]
    person = PersonModel.model_validate(data)
    return (teamId, person)


def get_person_team(teamId: int, person: PersonModel) -> Dict[str, Any]:
    """
    Combine person with teamId
    """
    return person.model_dump() | { fields(MemberModel).teamId : teamId }



