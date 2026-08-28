from .schema import Module15Input, Module15Output


class Module15Validator:
    def validate_input(self, input_data: Module15Input) -> bool:
        return bool(input_data.task_id)

    def validate_output(self, output: Module15Output) -> bool:
        return output.success and bool(output.research_memory)
