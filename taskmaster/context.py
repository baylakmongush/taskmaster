class Context:
    _pid_to_process: dict = dict()# pid(int) to process(Process)

    @classmethod
    def insert_process(cls, pid, process):
        cls._pid_to_process[pid] = process

    @classmethod
    def get_process(cls, pid):
        if pid in cls._pid_to_process.keys():
            return cls._pid_to_process[pid]
        return None

