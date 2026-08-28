from abc import ABC, abstractmethod

try:
    from .schema import Module15Input, Module15Output
except ImportError:
    from schema import Module15Input, Module15Output


class Module15Interface(ABC):
    @abstractmethod
    def execute(self, input_data: Module15Input) -> Module15Output:
        pass

    @abstractmethod
    def validate_input(self, input_data: Module15Input) -> bool:
        pass

    @abstractmethod
    def validate_output(self, output: Module15Output) -> bool:
        pass
