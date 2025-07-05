import abc

from dependency_injector import containers, providers
from dependency_injector.wiring import Provide, inject

from aiogram.types import User
from typing import Any, Dict, Tuple

from teamlimits.models.base import PersonModel, MemberModel
from teamlimits.models.fields import fields

class PersonService(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def make_person(self, user: User) -> PersonModel:
        ...

class PersonUserService(PersonService):
    def make_person(self, user: User) -> PersonModel:
        return PersonModel(
            userId=user.id,
            userName=user.username,
            firstName=user.first_name,
            lastName=user.last_name,
        )


class PersonContainer(containers.DeclarativeContainer):
    personService = providers.Singleton(PersonUserService)


@inject
def make_person(user: User, personService: PersonService = Provide[PersonContainer.personService]) -> PersonModel:
    """
    Make a [PersonModel] from Telegram User.
    """
    # return PersonModel(
    #     userId=user.id,
    #     userName=user.username,
    #     firstName=user.first_name,
    #     lastName=user.last_name,
    # )
    return personService.make_person(user)


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



