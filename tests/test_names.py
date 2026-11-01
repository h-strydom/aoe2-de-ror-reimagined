from reimagined.aoede.names import object_name, terrain_name


def test_known_names():
    assert object_name(83) == "Villager" and object_name(59) == "Berry Bush" and object_name(94) == "Phalanx"
    assert object_name(99999) == "#99999"
    assert terrain_name(34) == "Sand Dunes" and terrain_name(63) == "terrain #63"
