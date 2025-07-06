if __package__:
    from . import base
else:
    import base

import random
import string

from pathlib import Path
from pydantic import TypeAdapter
from teamlimits.models.base import PersonModel
from typing import Final, List

ADD_USERS: Final[int] = 10
FILE_NAME: Final[str] = Path(base.module_dir, "fake_persons.json")


def readFakePersons(filePath = FILE_NAME) -> List[PersonModel]:
    ta = TypeAdapter(List[PersonModel])
    try:
        with open(FILE_NAME, encoding="utf-8") as f:
            json = f.read()
            persons = ta.validate_json(json)
            # Check unique
            assert len(set(map(lambda person: person.userId, persons))) == len(persons)
            assert len(set(map(lambda person: person.userName, persons))) == len(persons)
            return persons
    except IOError:
        # File not found etc
        return []


if __name__ == "__main__":
        
    # Read existing users
    existingUsers = readFakePersons()
    existingIds = set(map(lambda person: person.userId, existingUsers))
    assert len(existingUsers) == len(existingIds)

    # Append new users with random userId
    total = len(existingIds) + ADD_USERS
    while len(existingIds) < total:
        userId = random.randint(100000, 10000000000)

        if userId not in existingIds:
            existingIds.add(userId)
            
            # Generate a person
            characters = string.ascii_letters
            userName = "".join(random.choice(characters) for i in range(10))
            person = PersonModel(
                userId=userId,
                userName=userName,
                firstName="",
                lastName="",
            )

            existingUsers.append(person)

    # Store generated list
    with open(FILE_NAME, "w", encoding="utf-8") as f:
        ta = TypeAdapter(List[PersonModel])
        json = ta.dump_json(existingUsers, indent=4)
        f.write(json.decode("utf-8"))

    

