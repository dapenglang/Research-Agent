try:
    from .schema import Module14Input, Module14Output
except ImportError:
    from schema import Module14Input, Module14Output


class Module14Validator:
    def validate_input(self, input_data: Module14Input) -> bool:
        upstream_12 = getattr(input_data, "upstream_module_12", None)
        if upstream_12 and isinstance(upstream_12, dict):
            output_files = upstream_12.get("output_files", {})
            if output_files:
                return True
        if getattr(input_data, "input_files", None):
            return True
        return True

    def validate_output(self, output: Module14Output) -> bool:
        if not output.review_report or not output.review_report.strip():
            return False
        if output.decision not in ["accept", "minor_revision", "major_revision", "reject", ""]:
            return False
        return True
