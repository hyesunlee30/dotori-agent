import logging
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI

from dotori.config import config
from dotori.agent.session import Session
from dotori.hooks.base import HookRegistry, HookContext, OnRequestHook, BeforeSendHook, OnToolCallHook, OnToolResultHook
from dotori.tools import LegacyParser, ShellTool, ToolResult
from dotori.parsers.express_parser import parse_express_routes
from dotori.parsers.mongoose_parser import parse_mongoose_schema
from dotori.parsers.react_parser import parse_react_component
from dotori.validators.base import JavaValidator, FrontendValidator

logger = logging.getLogger(__name__)


class ModuleType(Enum):
    BACKEND = "backend-api"
    FRONTEND = "frontend-ui"


class ConversionStatus(Enum):
    PENDING = "pending"
    PARSING = "parsing"
    CONVERTING = "converting"
    VALIDATING = "validating"
    CORRECTING = "correcting"
    COMPLETE = "complete"
    FAILED = "failed"


@dataclass
class AgentState:
    module: str = ""
    module_type: ModuleType | None = None
    status: ConversionStatus = ConversionStatus.PENDING
    retry_count: int = 0
    legacy_code: dict = field(default_factory=dict)
    parsed_data: dict = field(default_factory=dict)
    converted_code: dict = field(default_factory=dict)
    validation_result: dict = field(default_factory=dict)
    error_message: str = ""
    messages: list[dict] = field(default_factory=list)
    needs_correction: bool = False
    skills_injected: bool = False


def create_agent_graph():
    """Build the LangGraph state machine graph for legacy conversion."""
    graph = StateGraph(AgentState)

    graph.add_node("select_module", select_module_node)
    graph.add_node("parse_legacy", parse_legacy_node)
    graph.add_node("inject_skills", inject_skills_node)
    graph.add_node("convert", convert_node)
    graph.add_node("validate", validate_node)
    graph.add_node("self_reflect", self_reflect_node)
    graph.add_node("error_correction", error_correction_node)

    graph.set_entry_point("select_module")
    graph.add_edge("select_module", "parse_legacy")
    graph.add_edge("parse_legacy", "inject_skills")
    graph.add_edge("inject_skills", "convert")
    graph.add_edge("convert", "validate")
    graph.add_edge("validate", "self_reflect")

    # Self-reflection routing
    graph.add_conditional_edges(
        "self_reflect",
        should_correct,
        {
            "correct": "error_correction",
            "complete": END,
        }
    )
    graph.add_edge("error_correction", "convert")

    return graph.compile()


def select_module_node(state: AgentState) -> dict:
    """Select which legacy module to convert."""
    if isinstance(state, AgentState):
        state = {f: getattr(state, f, None) for f in state.__dataclass_fields__}
    
    legacy_dir = config.paths.LEGACY_BACKEND_DIR
    frontend_dir = config.paths.LEGACY_FRONTEND_DIR

    modules = {}
    if legacy_dir.exists():
        modules["backend-api"] = {"type": ModuleType.BACKEND.value, "path": str(legacy_dir)}
    if frontend_dir.exists():
        modules["frontend-ui"] = {"type": ModuleType.FRONTEND.value, "path": str(frontend_dir)}

    if not modules:
        return {
            "status": ConversionStatus.FAILED.value,
            "error_message": "No legacy modules found",
        }

    logger.info(f"Available modules: {list(modules.keys())}")
    return {"legacy_code": modules, "status": ConversionStatus.PENDING.value}


def parse_legacy_node(state: AgentState) -> dict:
    """Parse the selected legacy module to extract structured data."""
    if isinstance(state, AgentState):
        state = {f: getattr(state, f, None) for f in state.__dataclass_fields__}
    
    module = state.get("module", "")
    module_info = state.get("legacy_code", {}).get(module, {})
    module_path = Path(module_info.get("path", ""))

    if not module_path.exists():
        return {
            "status": ConversionStatus.FAILED.value,
            "error_message": f"Module path not found: {module_path}",
        }

    parsed = {}
    module_type = module_info.get("type")

    if module_type == ModuleType.BACKEND.value:
        parsed = _parse_backend(module_path)
    elif module_type == ModuleType.FRONTEND.value:
        parsed = _parse_frontend(module_path)

    return {
        "status": ConversionStatus.PARSING.value,
        "parsed_data": parsed,
    }


def inject_skills_node(state: AgentState) -> dict:
    """Inject conversion skill documents into the context."""
    if isinstance(state, AgentState):
        state = {f: getattr(state, f, None) for f in state.__dataclass_fields__}
    
    skills = {}

    backend_skill = config.paths.DOCS_DIR / "backend-conversion.md"
    if backend_skill.exists():
        skills["backend"] = backend_skill.read_text(encoding="utf-8")

    frontend_skill = config.paths.DOCS_DIR / "frontend-conversion.md"
    if frontend_skill.exists():
        skills["frontend"] = frontend_skill.read_text(encoding="utf-8")

    # Also use built-in prompts from config
    skills["prompts"] = {
        "system_role": config.prompts.SYSTEM_ARCHITECT_ROLE,
        "coding_guidelines": config.prompts.CODING_GUIDELINES,
        "backend_guide": config.prompts.BACKEND_CONVERSION_GUIDE,
        "frontend_guide": config.prompts.FRONTEND_CONVERSION_GUIDE,
    }

    return {
        "status": ConversionStatus.CONVERTING.value,
        "skills_injected": True,
        "parsed_data": {**state.get("parsed_data", {}), "skills": skills},
    }


def convert_node(state: AgentState) -> dict:
    """Convert parsed legacy code to modern architecture using LLM."""
    if isinstance(state, AgentState):
        state = {f: getattr(state, f, None) for f in state.__dataclass_fields__}
    
    module_type = state.get("module_type")
    parsed_data = state.get("parsed_data", {})
    skills = parsed_data.get("skills", {})
    prompts = skills.get("prompts", {})

    # Build conversion prompt
    system_prompt = prompts.get("system_role", config.prompts.SYSTEM_ARCHITECT_ROLE)
    coding_guidelines = prompts.get("coding_guidelines", config.prompts.CODING_GUIDELINES)

    if module_type == ModuleType.BACKEND.value:
        backend_guide = prompts.get("backend_guide", config.prompts.BACKEND_CONVERSION_GUIDE)
        user_prompt = _build_backend_conversion_prompt(parsed_data, backend_guide)
    elif module_type == ModuleType.FRONTEND.value:
        frontend_guide = prompts.get("frontend_guide", config.prompts.FRONTEND_CONVERSION_GUIDE)
        user_prompt = _build_frontend_conversion_prompt(parsed_data, frontend_guide)
    else:
        user_prompt = "Please convert the legacy code."

    # Build messages
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "system", "content": coding_guidelines},
        {"role": "user", "content": user_prompt},
    ]

    # Add correction feedback if retrying
    if state.get("error_message"):
        messages.append({
            "role": "user",
            "content": f"[Correction Required]\n{config.prompts.ERROR_CORRECTION_INSTRUCTION}\n\nError: {state['error_message']}",
        })

    return {
        "status": ConversionStatus.CONVERTING.value,
        "messages": messages,
    }


def validate_node(state: AgentState) -> dict:
    """Validate the converted code."""
    if isinstance(state, AgentState):
        state = {f: getattr(state, f, None) for f in state.__dataclass_fields__}
    
    module_type = state.get("module_type")
    converted_code = state.get("converted_code", {})
    result = {"passed": True, "errors": [], "warnings": []}

    if module_type == ModuleType.BACKEND.value:
        for name, code in converted_code.items():
            validator = JavaValidator()
            syntax_result = validator.validate_syntax(code)
            structure_result = validator.validate_structure(code, name)
            result["errors"].extend(syntax_result.errors)
            result["warnings"].extend(syntax_result.warnings)
            result["errors"].extend(structure_result.errors)
            result["warnings"].extend(structure_result.warnings)
            if not syntax_result.passed or not structure_result.passed:
                result["passed"] = False

    elif module_type == ModuleType.FRONTEND.value:
        for name, code in converted_code.items():
            validator = FrontendValidator()
            export_result = validator.validate_named_export(code, name)
            result["errors"].extend(export_result.errors)
            result["warnings"].extend(export_result.warnings)
            if not export_result.passed:
                result["passed"] = False

    return {
        "status": ConversionStatus.VALIDATING.value,
        "validation_result": result,
    }


def self_reflect_node(state: AgentState) -> dict:
    """Self-reflection: evaluate if conversion goals are met."""
    if isinstance(state, AgentState):
        state = {f: getattr(state, f, None) for f in state.__dataclass_fields__}
    
    validation = state.get("validation_result", {})
    retry_count = state.get("retry_count", 0)

    if validation.get("passed", False):
        logger.info("Validation passed. Conversion complete.")
        return {
            "status": ConversionStatus.COMPLETE.value,
            "needs_correction": False,
        }

    if retry_count >= config.agent.MAX_RETRY_COUNT:
        logger.error(f"Max retries ({config.agent.MAX_RETRY_COUNT}) reached. Giving up.")
        return {
            "status": ConversionStatus.FAILED.value,
            "error_message": f"Max retry count ({config.agent.MAX_RETRY_COUNT}) exceeded",
            "needs_correction": False,
        }

    # Build error summary for correction
    errors = validation.get("errors", [])
    error_text = "\n".join(f"- {e}" for e in errors) if errors else "Validation failed"

    return {
        "status": ConversionStatus.CORRECTING.value,
        "error_message": error_text,
        "needs_correction": True,
    }


def error_correction_node(state: AgentState) -> dict:
    """Error correction: increment retry and loop back to conversion."""
    if isinstance(state, AgentState):
        state = {f: getattr(state, f, None) for f in state.__dataclass_fields__}
    
    return {
        "retry_count": state.get("retry_count", 0) + 1,
        "status": ConversionStatus.CONVERTING.value,
    }


def should_correct(state: AgentState) -> str:
    """Route based on self-reflection result."""
    if isinstance(state, AgentState):
        state = {f: getattr(state, f, None) for f in state.__dataclass_fields__}
    
    if state.get("needs_correction"):
        return "correct"
    return "complete"


def _parse_backend(module_path: Path) -> dict:
    """Parse backend legacy code."""
    parsed = {"files": {}, "routes": [], "schemas": [], "controllers": []}

    # Parse routes
    routes_file = module_path / "routes" / "evaluations.js"
    if routes_file.exists():
        try:
            routes = parse_express_routes(routes_file)
            parsed["routes"] = [r.__dict__ for r in routes.routes]
            parsed["files"]["routes"] = routes_file.read_text(encoding="utf-8")
        except Exception as e:
            logger.warning(f"Failed to parse routes: {e}")

    # Parse models
    models_dir = module_path / "models"
    if models_dir.exists():
        for model_file in models_dir.glob("*.js"):
            try:
                schema = parse_mongoose_schema(model_file)
                parsed["schemas"].append(schema.__dict__)
                parsed["files"][model_file.stem] = model_file.read_text(encoding="utf-8")
            except Exception as e:
                logger.warning(f"Failed to parse model {model_file}: {e}")

    # Parse controllers
    controllers_dir = module_path / "controllers"
    if controllers_dir.exists():
        for controller_file in controllers_dir.glob("*.js"):
            try:
                parser = LegacyParser()
                logic = parser.parse_controller_logic(controller_file)
                parsed["controllers"].append(logic)
                parsed["files"][controller_file.stem] = controller_file.read_text(encoding="utf-8")
            except Exception as e:
                logger.warning(f"Failed to parse controller {controller_file}: {e}")

    return parsed


def _parse_frontend(module_path: Path) -> dict:
    """Parse frontend legacy code."""
    parsed = {"files": {}, "components": []}

    pages_dir = module_path / "src" / "pages"
    if pages_dir.exists():
        for page_file in pages_dir.glob("*.jsx"):
            try:
                component = parse_react_component(page_file)
                parsed["components"].append(component.__dict__)
                parsed["files"][page_file.stem] = page_file.read_text(encoding="utf-8")
            except Exception as e:
                logger.warning(f"Failed to parse component {page_file}: {e}")

    # Parse API client
    api_file = module_path / "src" / "api" / "index.js"
    if api_file.exists():
        parsed["files"]["api"] = api_file.read_text(encoding="utf-8")

    # Parse App
    app_file = module_path / "src" / "App.jsx"
    if app_file.exists():
        parsed["files"]["app"] = app_file.read_text(encoding="utf-8")

    return parsed


def _build_backend_conversion_prompt(parsed_data: dict, guide: str) -> str:
    """Build conversion prompt for backend."""
    routes = parsed_data.get("routes", [])
    schemas = parsed_data.get("schemas", [])
    controllers = parsed_data.get("controllers", [])

    prompt = f"""Convert the following Node.js/Express backend to Spring Boot 3.3.

[Conversion Guide]
{guide}

[Routes Found]
"""
    for route in routes:
        prompt += f"- {route.get('method', 'GET')} {route.get('path', '/')} -> {route.get('handler', 'unknown')}\n"

    prompt += f"\n[Schema Definitions]\n"
    for schema in schemas:
        if hasattr(schema, 'collection_name'):
            collection = schema.collection_name
            fields = schema.fields
        else:
            collection = schema.get('collection_name', 'unknown')
            fields = schema.get('fields', [])
        
        prompt += f"Collection: {collection}\n"
        for field in fields:
            if hasattr(field, 'name'):
                name, ftype = field.name, field.type
                required = field.required
                enum_values = field.enum_values
                min_val, max_val = field.min, field.max
            else:
                name, ftype = field.get('name'), field.get('type')
                required = field.get('required')
                enum_values = field.get('enum_values')
                min_val, max_val = field.get('min'), field.get('max')
            
            prompt += f"- {name}: {ftype}"
            if required:
                prompt += " (required)"
            if enum_values:
                prompt += f" enum: {enum_values}"
            if min_val or max_val:
                prompt += f" range: [{min_val or '?'}, {max_val or '?'}]"
            prompt += "\n"

    prompt += f"\n[Controller Logic]\n"
    for controller in controllers:
        for func in controller.get("functions", []):
            prompt += f"- Function: {func['name']}\n"
            prompt += f"  Operations: {func.get('operations', [])}\n"

    prompt += f"\n[Legacy Source Files]\n"
    for name, content in parsed_data.get("files", {}).items():
        prompt += f"\n--- {name} ---\n{content}\n"

    prompt += f"\n[Output Format]\n"
    prompt += f"Output all converted Java/Spring Boot files with their full paths.\n"
    prompt += f"Follow BeyondF Intranet coding conventions strictly.\n"
    prompt += f"Include: Entity, Repository, Service, Controller, DTO, Mapper\n"

    return prompt
    prompt += f"Include: Entity, Repository, Service, Controller, DTO, Mapper\n"

    return prompt


def _build_frontend_conversion_prompt(parsed_data: dict, guide: str) -> str:
    """Build conversion prompt for frontend."""
    components = parsed_data.get("components", [])

    prompt = f"""Convert the following React SPA to FSD architecture.

[Conversion Guide]
{guide}

[Components Found]
"""
    for comp in components:
        prompt += f"- {comp.get('name', 'unknown')}: form={comp.get('is_form')}, list={comp.get('is_list')}, detail={comp.get('is_detail')}\n"
        prompt += f"  API calls: {comp.get('api_calls', [])}\n"
        prompt += f"  State: {comp.get('state_variables', [])}\n"

    prompt += f"\n[Legacy Source Files]\n"
    for name, content in parsed_data.get("files", {}).items():
        prompt += f"\n--- {name} ---\n{content}\n"

    prompt += f"\n[Output Format]\n"
    prompt += f"Output all converted TypeScript/FSD files with their full paths.\n"
    prompt += f"Follow FSD architecture strictly.\n"
    prompt += f"Include: types, API client, hooks, UI components\n"

    return prompt


class ConversionAgent:
    """High-level agent for legacy-to-modern conversion."""

    def __init__(self):
        self.graph = create_agent_graph()
        self.sessions: dict[str, Session] = {}

    def get_session(self, module: str) -> Session:
        if module not in self.sessions:
            self.sessions[module] = Session(module)
        return self.sessions[module]

    def convert(self, module: str, module_type: ModuleType) -> dict:
        """Run the full conversion pipeline for a module."""
        initial_state = {
            "module": module,
            "module_type": module_type.value,
            "status": ConversionStatus.PENDING.value,
        }

        # Set up hooks
        registry = HookRegistry()
        registry.register(OnRequestHook())
        registry.register(OnToolCallHook())

        session = self.get_session(module)

        # Execute through graph
        try:
            result = self.graph.invoke(initial_state)
            return {
                "success": result["status"] == ConversionStatus.COMPLETE.value,
                "status": result["status"],
                "module": module,
                "retry_count": result.get("retry_count", 0),
                "validation": result.get("validation_result", {}),
                "error": result.get("error_message", ""),
            }
        except Exception as e:
            logger.error(f"Conversion failed for {module}: {e}", exc_info=True)
            return {
                "success": False,
                "status": ConversionStatus.FAILED.value,
                "module": module,
                "error": str(e),
            }
