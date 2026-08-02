from enum import Enum, auto


class RuntimeState(Enum):
    IDLE = auto()
    ANALYZE = auto()
    COLLECT_CONTEXT = auto()
    EXECUTE = auto()
    PATCH = auto()
    VALIDATE = auto()
    REVIEW = auto()
    DONE = auto()
    FAILED = auto()


class AtlasRuntime:
    def __init__(self):
        self.state = RuntimeState.IDLE

    def set_state(self, state: RuntimeState):
        self.state = state

    def get_state(self) -> RuntimeState:
        return self.state
