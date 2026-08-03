import time
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from enum import Enum

logger = logging.getLogger(__name__)


@dataclass
class TaskResult:
    """Single task execution result."""
    name: str
    success: bool
    data: dict = field(default_factory=dict)
    error: str = ""
    duration_ms: float = 0

    @classmethod
    def success_result(cls, name: str, data: dict = None) -> "TaskResult":
        return cls(name=name, success=True, data=data or {})

    @classmethod
    def failure_result(cls, name: str, error: str) -> "TaskResult":
        return cls(name=name, success=False, error=error)


class PipelineStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"


@dataclass
class PipelineResult:
    """Overall pipeline execution result."""
    status: PipelineStatus
    backend: TaskResult | None = None
    frontend: TaskResult | None = None
    duration_ms: float = 0
    errors: list[str] = field(default_factory=list)


class Task:
    """Base task for workflow pipeline."""

    def __init__(self, name: str):
        self.name = name

    def execute(self, context: dict) -> TaskResult:
        raise NotImplementedError

    def __repr__(self):
        return f"Task({self.name})"


class ParseExpressRoutesTask(Task):
    """Parse Express router files to extract route definitions."""

    def __init__(self):
        super().__init__("parse_express_routes")

    def execute(self, context: dict) -> TaskResult:
        import time
        start = time.time()

        try:
            from dotori.parsers.express_parser import parse_express_routes

            routes_dir = context.get("legacy_backend_dir") / "routes"
            if not routes_dir.exists():
                return TaskResult.failure_result(self.name, f"Routes dir not found: {routes_dir}")

            results = {}
            for route_file in routes_dir.glob("*.js"):
                parsed = parse_express_routes(route_file)
                results[route_file.stem] = {
                    "routes": [
                        {
                            "method": r.method,
                            "path": r.path,
                            "handler": r.handler,
                            "path_params": r.path_params,
                            "query_params": r.query_params,
                            "has_body": r.request_body,
                        }
                        for r in parsed.routes
                    ],
                    "controller": parsed.controller_file,
                }

            elapsed = (time.time() - start) * 1000
            logger.info(f"[{self.name}] Parsed {len(results)} route files")
            return TaskResult.success_result(self.name, {"routes": results, "duration_ms": elapsed})

        except Exception as e:
            elapsed = (time.time() - start) * 1000
            logger.error(f"[{self.name}] Failed: {e}", exc_info=True)
            return TaskResult.failure_result(self.name, str(e))


class ParseMongooseSchemasTask(Task):
    """Parse Mongoose model files to extract schema definitions."""

    def __init__(self):
        super().__init__("parse_mongoose_schemas")

    def execute(self, context: dict) -> TaskResult:
        import time
        start = time.time()

        try:
            from dotori.parsers.mongoose_parser import parse_mongoose_schema

            models_dir = context.get("legacy_backend_dir") / "models"
            if not models_dir.exists():
                return TaskResult.failure_result(self.name, f"Models dir not found: {models_dir}")

            results = {}
            for model_file in models_dir.glob("*.js"):
                parsed = parse_mongoose_schema(model_file)
                results[model_file.stem] = {
                    "collection": parsed.collection_name,
                    "fields": [
                        {
                            "name": f.name,
                            "type": f.type,
                            "required": f.required,
                            "enum_values": f.enum_values,
                            "default": f.default,
                            "min": f.min,
                            "max": f.max,
                            "maxlength": f.maxlength,
                            "trim": f.trim,
                        }
                        for f in parsed.fields
                    ],
                    "indexes": parsed.indexes,
                    "timestamps": parsed.timestamps,
                }

            elapsed = (time.time() - start) * 1000
            logger.info(f"[{self.name}] Parsed {len(results)} models")
            return TaskResult.success_result(self.name, {"schemas": results, "duration_ms": elapsed})

        except Exception as e:
            elapsed = (time.time() - start) * 1000
            logger.error(f"[{self.name}] Failed: {e}", exc_info=True)
            return TaskResult.failure_result(self.name, str(e))


class ParseReactComponentsTask(Task):
    """Parse React component files to extract UI structure."""

    def __init__(self):
        super().__init__("parse_react_components")

    def execute(self, context: dict) -> TaskResult:
        import time
        start = time.time()

        try:
            from dotori.parsers.react_parser import parse_react_component

            pages_dir = context.get("legacy_frontend_dir") / "src" / "pages"
            if not pages_dir.exists():
                return TaskResult.failure_result(self.name, f"Pages dir not found: {pages_dir}")

            results = {}
            for page_file in pages_dir.glob("*.jsx"):
                parsed = parse_react_component(page_file)
                results[page_file.stem] = {
                    "name": parsed.name,
                    "imports": parsed.imports,
                    "state_variables": parsed.state_variables,
                    "api_calls": parsed.api_calls,
                    "form_fields": [
                        {"name": f.name, "label": f.label, "component": f.component}
                        for f in parsed.form_fields
                    ],
                    "is_form": parsed.is_form,
                    "is_list": parsed.is_list,
                    "is_detail": parsed.is_detail,
                }

            elapsed = (time.time() - start) * 1000
            logger.info(f"[{self.name}] Parsed {len(results)} components")
            return TaskResult.success_result(self.name, {"components": results, "duration_ms": elapsed})

        except Exception as e:
            elapsed = (time.time() - start) * 1000
            logger.error(f"[{self.name}] Failed: {e}", exc_info=True)
            return TaskResult.failure_result(self.name, str(e))


class ExtractBusinessLogicTask(Task):
    """Extract business logic from controllers."""

    def __init__(self):
        super().__init__("extract_business_logic")

    def execute(self, context: dict) -> TaskResult:
        import time
        start = time.time()

        try:
            from dotori.tools import LegacyParser

            controllers_dir = context.get("legacy_backend_dir") / "controllers"
            if not controllers_dir.exists():
                return TaskResult.failure_result(self.name, f"Controllers dir not found: {controllers_dir}")

            parser = LegacyParser()
            results = {}
            for ctrl_file in controllers_dir.glob("*.js"):
                parsed = parser.parse_controller_logic(ctrl_file)
                results[ctrl_file.stem] = parsed

            elapsed = (time.time() - start) * 1000
            logger.info(f"[{self.name}] Extracted logic from {len(results)} controllers")
            return TaskResult.success_result(self.name, {"logic": results, "duration_ms": elapsed})

        except Exception as e:
            elapsed = (time.time() - start) * 1000
            logger.error(f"[{self.name}] Failed: {e}", exc_info=True)
            return TaskResult.failure_result(self.name, str(e))


class ConvertBackendTask(Task):
    """Convert backend code using LLM (single call, no loop)."""

    def __init__(self, llm_client=None):
        super().__init__("convert_backend_to_spring")
        self.llm_client = llm_client

    def execute(self, context: dict) -> TaskResult:
        import time
        start = time.time()

        try:
            parsed_data = context.get("parsed_data", {})
            routes = parsed_data.get("routes", {})
            schemas = parsed_data.get("schemas", {})

            prompt_parts = []
            prompt_parts.append("# Backend Conversion Request")
            prompt_parts.append("\n## Routes")
            for file_name, file_data in routes.items():
                for route in file_data.get("routes", []):
                    prompt_parts.append(f"- {route['method']} {route['path']} -> {route['handler']}")

            prompt_parts.append("\n## Schemas")
            for model_name, schema in schemas.items():
                prompt_parts.append(f"\n### {schema.get('collection', model_name)}")
                for field in schema.get("fields", []):
                    prompt_parts.append(f"- {field['name']}: {field['type']}" +
                                      (" (required)" if field.get("required") else "") +
                                      (f" enum={field.get('enum_values')}" if field.get("enum_values") else "") +
                                      (f" [{field.get('min')},{field.get('max')}]" if field.get("min") or field.get("max") else ""))

            prompt_parts.append("\n## Conversion Rules")
            prompt_parts.append("- Express Router -> Spring Controller")
            prompt_parts.append("- Mongoose Schema -> JPA Entity")
            prompt_parts.append("- Follow Spring Boot 3.3 Layered+Domain DDD")

            prompt = "\n".join(prompt_parts)

            if self.llm_client:
                messages = [
                    {"role": "system", "content": context.get("system_prompt", "")},
                    {"role": "user", "content": prompt},
                ]
                llm_response = self.llm_client.chat(messages)
                converted_code = llm_response.content
            else:
                converted_code = f"// Converted code would be here.\n// Input:\n{prompt}"

            elapsed = (time.time() - start) * 1000
            logger.info(f"[{self.name}] LLM call completed in {elapsed:.0f}ms")
            return TaskResult.success_result(
                self.name,
                {"converted_code": converted_code, "duration_ms": elapsed}
            )

        except Exception as e:
            elapsed = (time.time() - start) * 1000
            logger.error(f"[{self.name}] Failed: {e}", exc_info=True)
            return TaskResult.failure_result(self.name, str(e))


class ConvertFrontendTask(Task):
    """Convert frontend code using LLM (single call, no loop)."""

    def __init__(self, llm_client=None):
        super().__init__("convert_frontend_to_fsd")
        self.llm_client = llm_client

    def execute(self, context: dict) -> TaskResult:
        import time
        start = time.time()

        try:
            parsed_data = context.get("parsed_data", {})
            components = parsed_data.get("components", {})

            prompt_parts = []
            prompt_parts.append("# Frontend Conversion Request")
            prompt_parts.append("\n## Components")
            for comp_name, comp_data in components.items():
                prompt_parts.append(f"\n### {comp_name}")
                prompt_parts.append(f"- Type: form={comp_data.get('is_form')}, list={comp_data.get('is_list')}")
                prompt_parts.append(f"- API calls: {comp_data.get('api_calls', [])}")
                for field in comp_data.get("form_fields", []):
                    prompt_parts.append(f"- Form: {field['name']} ({field['component']})")

            prompt_parts.append("\n## Conversion Rules")
            prompt_parts.append("- React SPA -> FSD Architecture")
            prompt_parts.append("- Named Export only (no default export)")
            prompt_parts.append("- FSD folder structure: features/{domain}/ui/, api/, model/, hooks/")

            prompt = "\n".join(prompt_parts)

            if self.llm_client:
                messages = [
                    {"role": "system", "content": context.get("system_prompt", "")},
                    {"role": "user", "content": prompt},
                ]
                llm_response = self.llm_client.chat(messages)
                converted_code = llm_response.content
            else:
                converted_code = f"// Converted code would be here.\n// Input:\n{prompt}"

            elapsed = (time.time() - start) * 1000
            logger.info(f"[{self.name}] LLM call completed in {elapsed:.0f}ms")
            return TaskResult.success_result(
                self.name,
                {"converted_code": converted_code, "duration_ms": elapsed}
            )

        except Exception as e:
            elapsed = (time.time() - start) * 1000
            logger.error(f"[{self.name}] Failed: {e}", exc_info=True)
            return TaskResult.failure_result(self.name, str(e))


class ValidateJavaSyntaxTask(Task):
    """Validate converted Java code syntax."""

    def __init__(self):
        super().__init__("validate_java_syntax")

    def execute(self, context: dict) -> TaskResult:
        try:
            from dotori.validators.base import JavaValidator

            converted = context.get("converted_backend", {})
            code = converted.get("converted_code", "")

            validator = JavaValidator()
            result = validator.validate_syntax(code)

            return TaskResult.success_result(
                self.name,
                {"passed": result.passed, "errors": result.errors, "warnings": result.warnings}
            )

        except Exception as e:
            logger.error(f"[{self.name}] Failed: {e}", exc_info=True)
            return TaskResult.failure_result(self.name, str(e))


class ValidateFSDStructureTask(Task):
    """Validate converted frontend code FSD compliance."""

    def __init__(self):
        super().__init__("validate_fsd_structure")

    def execute(self, context: dict) -> TaskResult:
        try:
            from dotori.validators.base import FrontendValidator

            converted = context.get("converted_frontend", {})
            code = converted.get("converted_code", "")

            validator = FrontendValidator()
            result = validator.validate_named_export(code, "ConvertedComponent")

            return TaskResult.success_result(
                self.name,
                {"passed": result.passed, "errors": result.errors, "warnings": result.warnings}
            )

        except Exception as e:
            logger.error(f"[{self.name}] Failed: {e}", exc_info=True)
            return TaskResult.failure_result(self.name, str(e))


class RunBackendBuildTask(Task):
    """Run backend build (gradlew/mvnw)."""

    def __init__(self):
        super().__init__("run_backend_build")

    def execute(self, context: dict) -> TaskResult:
        try:
            from dotori.tools import ShellTool

            target_dir = context.get("target_backend_dir", Path("./converted/backend"))
            shell = ShellTool()
            result = shell.run_backend_build(target_dir)

            return TaskResult.success_result(
                self.name,
                {
                    "success": result.success,
                    "output": result.output[:2000] if result.output else "",
                    "error": result.error[:2000] if result.error else "",
                    "exit_code": result.exit_code,
                }
            )

        except Exception as e:
            logger.error(f"[{self.name}] Failed: {e}", exc_info=True)
            return TaskResult.failure_result(self.name, str(e))


class RunFrontendBuildTask(Task):
    """Run frontend build (pnpm build / vite build)."""

    def __init__(self):
        super().__init__("run_frontend_build")

    def execute(self, context: dict) -> TaskResult:
        try:
            from dotori.tools import ShellTool

            target_dir = context.get("target_frontend_dir", Path("./converted/frontend"))
            shell = ShellTool()
            result = shell.run_frontend_build(target_dir)

            return TaskResult.success_result(
                self.name,
                {
                    "success": result.success,
                    "output": result.output[:2000] if result.output else "",
                    "error": result.error[:2000] if result.error else "",
                    "exit_code": result.exit_code,
                }
            )

        except Exception as e:
            logger.error(f"[{self.name}] Failed: {e}", exc_info=True)
            return TaskResult.failure_result(self.name, str(e))


class GenerateReportTask(Task):
    """Generate final conversion report."""

    def __init__(self):
        super().__init__("generate_report")

    def execute(self, context: dict) -> TaskResult:
        try:
            backend = context.get("backend_result")
            frontend = context.get("frontend_result")

            report = {
                "status": context.get("pipeline_status", "unknown"),
                "backend": {
                    "success": backend.success if backend else False,
                    "duration_ms": backend.duration_ms if backend else 0,
                    "error": backend.error if backend else "",
                },
                "frontend": {
                    "success": frontend.success if frontend else False,
                    "duration_ms": frontend.duration_ms if frontend else 0,
                    "error": frontend.error if frontend else "",
                },
                "total_duration_ms": context.get("total_duration_ms", 0),
            }

            return TaskResult.success_result(self.name, {"report": report})

        except Exception as e:
            logger.error(f"[{self.name}] Failed: {e}", exc_info=True)
            return TaskResult.failure_result(self.name, str(e))
