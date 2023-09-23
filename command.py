class Command:
    process_group_name: str
    index: int | None

class Status(Command):
    pass

class Start(Command):
    pass

class Stop(Command):
    pass

class Restart(Command):
    pass
