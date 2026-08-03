import subprocess
import logging
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class ToolResult:
    success: bool
    output: str
    error: str = ""
    exit_code: int = 0


class LegacyParser:
    """Parses legacy code files to extract structured information for conversion."""

    def parse_express_routes(self, routes_file: Path) -> dict:
        """Parse Express router file to extract route definitions.

        Extracts: HTTP method, path, handler name, request body usage,
        path params, query params.
        """
        content = routes_file.read_text(encoding="utf-8")
        routes = []

        import re
        route_pattern = re.compile(
            r"router\.(get|post|put|delete|patch)\s*\(\s*['\"]([^'\"]+)['\"]"
        )
        for match in route_pattern.finditer(content):
            method = match.group(1).upper()
            path = match.group(2)
            handler = self._extract_handler(content, match.end())
            routes.append({
                "method": method,
                "path": path,
                "handler": handler,
                "file": str(routes_file.name),
            })

        # Extract path params like :id
        path_params = set()
        for route in routes:
            for param in re.findall(r":(\w+)", route["path"]):
                path_params.add(param)

        # Extract query params from req.query usage
        query_params = set()
        query_pattern = re.compile(r"req\.query\.(\w+)")
        for match in query_pattern.finditer(content):
            query_params.add(match.group(1))

        # Check for body usage
        has_body = "req.body" in content

        return {
            "routes": routes,
            "path_params": sorted(path_params),
            "query_params": sorted(query_params),
            "has_body": has_body,
            "file": str(routes_file),
        }

    def parse_mongoose_schema(self, model_file: Path) -> dict:
        """Parse Mongoose schema file to extract field definitions.

        Extracts: field names, types, required status, enum values,
        min/max constraints, default values, indexes.
        """
        content = model_file.read_text(encoding="utf-8")
        fields = []

        import re
        # Extract schema field definitions
        field_pattern = re.compile(
            r"(\w+)\s*:\s*\{([^}]+)\}",
            re.DOTALL
        )
        for match in field_pattern.finditer(content):
            field_name = match.group(1)
            if field_name in ("timestamps", "index", "indexes"):
                continue
            field_def = match.group(2)
            field_info = self._parse_field_definition(field_name, field_def)
            fields.append(field_info)

        # Extract indexes
        indexes = []
        index_pattern = re.compile(r"schema\.index\(\s*(\{[^}]+\})")
        for match in index_pattern.finditer(content):
            indexes.append(match.group(1))

        # Check for timestamps
        has_timestamps = "timestamps" in content

        return {
            "fields": fields,
            "indexes": indexes,
            "has_timestamps": has_timestamps,
            "file": str(model_file),
        }

    def parse_controller_logic(self, controller_file: Path) -> dict:
        """Parse Express controller to extract business logic.

        Extracts: function signatures, MongoDB operations, validation logic,
        response formatting.
        """
        content = controller_file.read_text(encoding="utf-8")
        functions = []

        import re
        func_pattern = re.compile(
            r"const\s+(\w+)\s*=\s*async\s*\(req\s*,\s*res\)\s*=>\s*\{",
            re.DOTALL
        )
        for match in func_pattern.finditer(content):
            func_name = match.group(1)
            func_body = self._extract_function_body(content, match.end())
            operations = self._extract_operations(func_body)
            functions.append({
                "name": func_name,
                "operations": operations,
                "has_validation": "validate" in func_body.lower(),
                "has_error_handling": "catch" in func_body or "try" in func_body,
            })

        return {
            "functions": functions,
            "file": str(controller_file),
        }

    def parse_react_component(self, component_file: Path) -> dict:
        """Parse React component to extract UI structure.

        Extracts: component name, props, state variables, form fields,
        API calls, imports, dependencies.
        """
        content = component_file.read_text(encoding="utf-8")
        imports = self._extract_imports(content)
        state_vars = self._extract_state_variables(content)
        api_calls = self._extract_api_calls(content)
        form_fields = self._extract_form_fields(content)

        # Detect component type
        is_form = "Form.useForm" in content or "onFinish" in content
        is_list = "AGrid" in content or "ag-grid" in content.lower() or "rowData" in content
        is_detail = "useParams" in content or "edit" in component_file.name.lower()

        return {
            "name": component_file.stem,
            "imports": imports,
            "state_variables": state_vars,
            "api_calls": api_calls,
            "form_fields": form_fields,
            "is_form": is_form,
            "is_list": is_list,
            "is_detail": is_detail,
            "file": str(component_file),
        }

    def _extract_handler(self, content: str, start_pos: int) -> str:
        """Extract handler function name after route definition."""
        import re
        match = re.search(
            r"\.\s*(get|post|put|delete|patch)\s*\(\s*['\"][^'\"]+['\"]\s*\)\s*(\.get|\.post|\.put|\.delete|\.patch)?\s*\(\s*(\w+)",
            content[start_pos:start_pos + 500]
        )
        if match:
            return match.group(3)
        # Try direct handler reference
        match = re.search(r"(\w+)", content[start_pos:start_pos + 200])
        if match:
            return match.group(1)
        return "unknown"

    def _parse_field_definition(self, name: str, definition: str) -> dict:
        """Parse individual Mongoose field definition."""
        import re
        field_info = {"name": name}

        # Type
        type_match = re.search(r"type:\s*(\w+)", definition)
        if type_match:
            field_info["type"] = type_match.group(1)
        else:
            type_match = re.search(r"type:\s*String", definition)
            if type_match:
                field_info["type"] = "String"

        # Required
        field_info["required"] = "required" in definition

        # Enum
        enum_match = re.search(r"enum:\s*\[([^\]]+)\]", definition)
        if enum_match:
            values = [v.strip().strip("'\"") for v in enum_match.group(1).split(",")]
            field_info["enum_values"] = values

        # Min/Max
        min_match = re.search(r"min:\s*(\d+)", definition)
        if min_match:
            field_info["min"] = int(min_match.group(1))
        max_match = re.search(r"max:\s*(\d+)", definition)
        if max_match:
            field_info["max"] = int(max_match.group(1))

        # Default
        default_match = re.search(r"default:\s*['\"]([^'\"]+)['\"]", definition)
        if default_match:
            field_info["default"] = default_match.group(1)
        else:
            default_match = re.search(r"default:\s*(\w+)", definition)
            if default_match:
                field_info["default"] = default_match.group(1)

        # Maxlength
        maxlength_match = re.search(r"maxlength:\s*(\d+)", definition)
        if maxlength_match:
            field_info["maxlength"] = int(maxlength_match.group(1))

        # Trim
        field_info["trim"] = "trim" in definition

        return field_info

    def _extract_function_body(self, content: str, start_pos: int) -> str:
        """Extract the body of an async function."""
        depth = 0
        i = start_pos
        body_start = content.find("{", start_pos)
        if body_start == -1:
            return ""
        for i in range(body_start, len(content)):
            if content[i] == "{":
                depth += 1
            elif content[i] == "}":
                depth -= 1
                if depth == 0:
                    return content[body_start + 1:i]
        return content[body_start + 1:]

    def _extract_operations(self, body: str) -> list[str]:
        """Extract MongoDB/Express operations from function body."""
        import re
        operations = []
        patterns = [
            (r"await\s+(\w+)\.(\w+)\(", "mongodb"),
            (r"res\.(json|status)\(", "response"),
            (r"req\.(body|params|query)\.", "request"),
            (r"try\s*\{", "error_handling"),
        ]
        for pattern, category in patterns:
            matches = re.findall(pattern, body)
            if matches:
                operations.append(f"{category}:{','.join(str(m) for m in matches)}")
        return operations

    def _extract_imports(self, content: str) -> list[str]:
        """Extract import statements."""
        import re
        imports = []
        pattern = re.compile(r"import\s+(?:{\s*([^}]+)\s*}|(\w+))\s+from\s+['\"]([^'\"]+)['\"]")
        for match in pattern.finditer(content):
            named = match.group(1)
            default = match.group(2)
            source = match.group(3)
            if named:
                imports.extend([f"{n.strip()}:from:{source}" for n in named.split(",")])
            if default:
                imports.append(f"{default}:from:{source}")
        return imports

    def _extract_state_variables(self, content: str) -> list[str]:
        """Extract useState declarations."""
        import re
        states = []
        pattern = re.compile(r"useState\(([^)]*)\)\s*=\s*use\(\s*useState\)\s*\?\s*\[([^\]]+)\]|const\s+\[([^\]]+)\]\s*=\s*useState")
        for match in pattern.finditer(content):
            vars_list = match.group(2) or match.group(3) or match.group(1)
            if vars_list:
                for v in vars_list.split(","):
                    v = v.strip().strip("[")
                    if v and not v.startswith("("):
                        states.append(v)
        return states

    def _extract_api_calls(self, content: str) -> list[str]:
        """Extract API call patterns."""
        import re
        calls = []
        pattern = re.compile(r"(evaluationApi\.\w+|axios\.\w+|fetch\()")
        for match in pattern.finditer(content):
            calls.append(match.group(1))
        return list(set(calls))

    def _extract_form_fields(self, content: str) -> list[dict]:
        """Extract antd Form.Item definitions."""
        import re
        fields = []
        pattern = re.compile(
            r"<Form\.Item\s+[^>]*name=\{?['\"](\w+)['\"]?\s*[^>]*label=\{?['\"]([^'\"]+)['\"]?",
            re.DOTALL
        )
        for match in pattern.finditer(content):
            fields.append({
                "name": match.group(1),
                "label": match.group(2),
            })
        return fields


class ShellTool:
    """Executes build, compile, and test commands."""

    def run_command(self, command: list[str], cwd: Path, timeout: int = 300) -> ToolResult:
        """Run a shell command and return the result."""
        try:
            result = subprocess.run(
                command,
                cwd=str(cwd),
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            return ToolResult(
                success=result.returncode == 0,
                output=result.stdout,
                error=result.stderr,
                exit_code=result.returncode,
            )
        except subprocess.TimeoutExpired:
            return ToolResult(
                success=False,
                output="",
                error=f"Command timed out after {timeout}s",
                exit_code=-1,
            )
        except FileNotFoundError as e:
            return ToolResult(
                success=False,
                output="",
                error=f"Command not found: {e}",
                exit_code=-1,
            )
        except Exception as e:
            return ToolResult(
                success=False,
                output="",
                error=str(e),
                exit_code=-1,
            )

    def run_backend_build(self, project_dir: Path) -> ToolResult:
        """Run Spring Boot project build (Gradle or Maven)."""
        gradle_wrapper = project_dir / "gradlew"
        maven_wrapper = project_dir / "mvnw"

        if gradle_wrapper.exists():
            return self.run_command(["./gradlew", "build", "-x", "test"], project_dir)
        elif maven_wrapper.exists():
            return self.run_command(["./mvnw", "clean", "package", "-DskipTests"], project_dir)
        else:
            return ToolResult(
                success=False,
                output="",
                error="No Gradle or Maven wrapper found",
                exit_code=-1,
            )

    def run_backend_test(self, project_dir: Path) -> ToolResult:
        """Run Spring Boot tests."""
        gradle_wrapper = project_dir / "gradlew"
        maven_wrapper = project_dir / "mvnw"

        if gradle_wrapper.exists():
            return self.run_command(["./gradlew", "test"], project_dir)
        elif maven_wrapper.exists():
            return self.run_command(["./mvnw", "test"], project_dir)
        else:
            return ToolResult(
                success=False,
                output="",
                error="No Gradle or Maven wrapper found",
                exit_code=-1,
            )

    def run_frontend_build(self, project_dir: Path) -> ToolResult:
        """Run React FSD project build."""
        package_json = project_dir / "package.json"
        if not package_json.exists():
            return ToolResult(
                success=False,
                output="",
                error="package.json not found",
                exit_code=-1,
            )

        # Try pnpm first, then npm
        pnpm_result = self.run_command(["pnpm", "build"], project_dir, timeout=120)
        if pnpm_result.success or pnpm_result.exit_code != -1:
            return pnpm_result

        npm_result = self.run_command(["npx", "vite", "build"], project_dir, timeout=120)
        return npm_result

    def run_frontend_lint(self, project_dir: Path) -> ToolResult:
        """Run ESLint on React FSD project."""
        eslint_result = self.run_command(["npx", "eslint", "src/"], project_dir, timeout=60)
        return eslint_result
