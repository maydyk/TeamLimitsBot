import abc

from dependency_injector import containers, providers
from dependency_injector.wiring import Provide, inject

from aiogram.types import User
from typeguard import typechecked
from typing import Any, Dict, Optional

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


_personContainer: PersonContainer =  PersonContainer()

@typechecked
def setup(container: Optional[PersonContainer] = None):
    """
    Call from main to setup DI
    """
    if container is not None and container != _personContainer:
        _personContainer.override(container)
    _personContainer.wire([__name__])


@inject
@typechecked
def make_person(user: User, personService: PersonService = Provide[PersonContainer.personService]) -> PersonModel:
    """
    Make a [PersonModel] from Telegram User.
    """
    return personService.make_person(user)


@typechecked
def get_person(data: Dict[str, Any]) -> PersonModel:
    return PersonModel.model_validate(data)


@typechecked
def get_member(data: Dict[str, Any]) -> MemberModel:
    """
    Extracts team id and person data from specifies dictionary.
    """
    teamId = data[fields(MemberModel).teamId]
    person = get_person(data)
    return person.combineId(MemberModel, teamId)


@typechecked
def set_person_team(teamId: int, person: PersonModel) -> Dict[str, Any]:
    """
    Combine person with teamId
    """
    return person.model_dump() | { fields(MemberModel).teamId : teamId }



