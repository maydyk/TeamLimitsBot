import base
import asyncio
import logging

from datetime import datetime
from dependency_injector.wiring import Provide, inject

from teamlimits.application import Application, bound_resources
from teamlimits.models.base import MemberModel, TeamModel
from teamlimits.user.tg_bot.main import setup_application
from tests.generate_fake_persons import readFakePersons


@inject
async def main(application: Application = Provide[Application]):
    # Setup logging
    logging.basicConfig(level=logging.DEBUG if __debug__ else logging.ERROR)

    # Prepare Repository
    async with bound_resources(application):
        repository = application.repository

        persons = readFakePersons()

        # Make the team
        admin = persons[0]

        try:

            fellowShip = TeamModel(
                id = None,
                title = "The fellowship of the Ring",
                description = "Make the Middle-earth great again!",
                minimalMembers=2,
                maximalMembers=10,
                enableCrews=False,
                minimalCrews=0,
                maximalCrews=0,
                deadline=None,
                suspendCompanions=True,
                suspendRecruitment=False,
                suspendOnDeadline=False,
            )
            teamId = await repository.insertTeam(admin, fellowShip)

            # Add all members
            for person in persons:
                await repository.insertTeamMember(member = person.combineId(MemberModel, teamId), crewId = None, date = datetime.now())
        
        except Exception as e:
            print(f"Exception!:\n{e}")
        
        else:
            print("The fellowship of the Ring is waiting for adventures!")
        


if __name__ == "__main__":
    application = Application()
    setup_application(application)

    asyncio.run(main())
