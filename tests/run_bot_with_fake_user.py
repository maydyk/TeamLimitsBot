if __package__:
    from . import base
else:
    import base

import asyncio

from dependency_injector import containers, providers
from dependency_injector.wiring import Provide, inject
from tests.generate_fake_persons import readFakePersons
from teamlimits.application import Application
from teamlimits.models.base import PersonModel
from teamlimits.user.tg_bot.main import main, setup_application
import teamlimits.user.tg_bot.make_person as make_person
from typing import List


class FakePersonService(make_person.PersonService):
    fakePersons: List[PersonModel]

    def __init__(self):
        self.fakePersons = readFakePersons()

    def make_person(self, user) -> PersonModel:
        return self.fakePersons[0]
    

class FakePersonContainer(containers.DeclarativeContainer):
    personService = providers.Singleton(FakePersonService)


if __name__ == "__main__":
    # Setup DI
    application = Application()
    setup_application(application)
    make_person.setup(FakePersonContainer())

    asyncio.run(main())
