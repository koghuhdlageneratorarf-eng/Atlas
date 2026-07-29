from .runtime import AtlasRuntime, RuntimeState


class RuntimeEngine:
    def __init__(self):
        self.runtime = AtlasRuntime()

    def run(self, task: str):
        self.runtime.set_state(RuntimeState.ANALYZE)

        while self.runtime.state != RuntimeState.DONE:
            match self.runtime.state:

                case RuntimeState.ANALYZE:
                    self.runtime.set_state(RuntimeState.COLLECT_CONTEXT)

                case RuntimeState.COLLECT_CONTEXT:
                    self.runtime.set_state(RuntimeState.EXECUTE)

                case RuntimeState.EXECUTE:
                    self.runtime.set_state(RuntimeState.PATCH)

                case RuntimeState.PATCH:
                    self.runtime.set_state(RuntimeState.VALIDATE)

                case RuntimeState.VALIDATE:
                    self.runtime.set_state(RuntimeState.REVIEW)

                case RuntimeState.REVIEW:
                    self.runtime.set_state(RuntimeState.DONE)

                case RuntimeState.FAILED:
                    break

        return self.runtime.state