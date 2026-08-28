from abc import ABC, abstractmethod
try:
    from .schema import Module14Input, Module14Output
except ImportError:
    from schema import Module14Input, Module14Output


class Module14Interface(ABC):
    @abstractmethod
    def execute(self, input_data: Module14Input) -> Module14Output:
        pass

    @abstractmethod
    def validate_input(self, input_data: Module14Input) -> bool:
        pass

    @abstractmethod
    def validate_output(self, output: Module14Output) -> bool:
        pass
