import base

from teamlimits.database.entities import _camel_to_snake

if __name__ == "__main__":

    assert _camel_to_snake("HelloWorld") == "Hello_World"
    assert _camel_to_snake("Hello") == "Hello"
    assert _camel_to_snake("_world") == "_world"
    assert _camel_to_snake("_World") == "__World"
    print("camel_to_snake() test are completed!")