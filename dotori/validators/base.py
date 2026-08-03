import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    passed: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def add_error(self, error: str):
        self.errors.append(error)
        self.passed = False

    def add_warning(self, warning: str):
        self.warnings.append(warning)

    def merge(self, other: "ValidationResult"):
        self.errors.extend(other.errors)
        self.warnings.extend(other.warnings)
        if not other.passed:
            self.passed = False


class JavaValidator:
    """Validates Java/Spring Boot code structure and conventions."""

    def validate_syntax(self, java_code: str) -> ValidationResult:
        """Basic Java syntax validation."""
        result = ValidationResult(passed=True)
        if not java_code.strip():
            result.add_error("Java code is empty")
            return result

        # Check for basic syntax issues
        open_braces = java_code.count("{")
        close_braces = java_code.count("}")
        if open_braces != close_braces:
            result.add_error(f"Mismatched braces: {open_braces} open, {close_braces} close")

        open_parens = java_code.count("(")
        close_parens = java_code.count(")")
        if open_parens != close_parens:
            result.add_error(f"Mismatched parentheses: {open_parens} open, {close_parens} close")

        # Check for common issues
        if "package " not in java_code and "import " not in java_code:
            result.add_warning("No package or import declarations found")

        return result

    def validate_structure(self, java_code: str, entity_name: str) -> ValidationResult:
        """Validate Java code structure and conventions."""
        result = ValidationResult(passed=True)
        expected_class = f"class {entity_name}"
        if expected_class not in java_code:
            result.add_error(f"Expected class declaration: {expected_class}")

        # Check for required annotations
        if "@Entity" in java_code:
            if "@Table" not in java_code:
                result.add_warning("Entity missing @Table annotation")
            if "@Id" not in java_code:
                result.add_error("Entity missing @Id annotation")
        elif "@RestController" in java_code:
            if "@RequestMapping" not in java_code:
                result.add_warning("RestController missing @RequestMapping")

        return result

    def validate_package_structure(self, file_path: Path, expected_package: str) -> ValidationResult:
        """Validate that file is in the correct package directory."""
        result = ValidationResult(passed=True)
        parts = expected_package.replace(".", "/").split("/")
        for part in parts:
            if part not in file_path.parts:
                result.add_error(f"File path missing package segment: {part}")
                break
        return result


class FrontendValidator:
    """Validates React FSD code structure and conventions."""

    def validate_fsd_imports(self, component_code: str, component_layer: str) -> ValidationResult:
        """Validate FSD import rules (lower layers cannot import from higher layers)."""
        result = ValidationResult(passed=True)
        layer_hierarchy = {
            "shared": 0,
            "entities": 1,
            "features": 2,
            "widgets": 3,
            "app": 4,
        }
        current_level = layer_hierarchy.get(component_layer, 0)

        import re
        import_pattern = re.compile(r"from\s+['\"]@/(.+?)['\"]")
        for match in import_pattern.finditer(component_code):
            import_path = match.group(1)
            for layer, level in layer_hierarchy.items():
                if layer in import_path and level > current_level:
                    result.add_error(
                        f"FSD violation: {component_layer} imports from {layer} "
                        f"(higher layer cannot import from lower layer)"
                    )
        return result

    def validate_named_export(self, component_code: str, component_name: str) -> ValidationResult:
        """Validate that component uses named export, not default export."""
        result = ValidationResult(passed=True)
        if "export default" in component_code:
            result.add_error(
                f"Component '{component_name}' uses 'export default'. "
                "FSD requires named exports (export const)."
            )
        if f"export const {component_name}" not in component_code and \
           f"export function {component_name}" not in component_code:
            result.add_warning(
                f"Component '{component_name}' may not have a named export."
            )
        return result

    def validate_fsdl_structure(self, component_path: Path) -> ValidationResult:
        """Validate that component is in the correct FSD folder."""
        result = ValidationResult(passed=True)
        parts = component_path.parts

        # Check for features/{domain}/ui/ pattern
        if "features" in parts:
            features_idx = parts.index("features")
            if features_idx + 2 >= len(parts):
                result.add_error("Missing domain and ui folders under features/")
            else:
                if parts[features_idx + 2] != "ui":
                    result.add_error(
                        f"Component should be under features/{{domain}}/ui/, "
                        f"found: features/{parts[features_idx + 1]}/{parts[features_idx + 2]}"
                    )

        return result

    def validate_translation_usage(self, component_code: str) -> ValidationResult:
        """Validate that translation hook is used for user-facing strings."""
        result = ValidationResult(passed=True)
        if "usePageTranslation" not in component_code:
            result.add_warning("Component does not use usePageTranslation hook")
        return result
