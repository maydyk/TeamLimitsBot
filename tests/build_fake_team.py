import base
import asyncio
import logging

from teamlimits.repository.repository import Repository
from teamlimits.models.base import MemberModel, TeamModel
from tests.generate_fake_persons import readFakePersons
# Extract token and DB connection
import teamlimits.user.tg_bot.config as config


async def main():
    # Setup logging
    logging.basicConfig(level=logging.DEBUG if __debug__ else logging.ERROR)

    # Read config
    settings = config.Config()

    # Prepare Repository
    async with Repository.build(settings.make_db_url()):
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
            teamId = await Repository().insertTeam(admin, fellowShip)

            # Add all members
            for person in persons:
                await Repository().addTeamMember(member = person.combineId(MemberModel, teamId), crewId = None)
        
        except Exception as e:
            print(f"Exception!:\n{e}")
        
        else:
            print("The fellowship of the Ring is waiting for adventures!")
        


if __name__ == "__main__":
    asyncio.run(main())
