import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class FormField:
    name: str
    label: str
    component: str = "Input"


@dataclass
class ParsedComponent:
    name: str
    imports: list[dict] = field(default_factory=list)
    state_variables: list[str] = field(default_factory=list)
    form_fields: list[FormField] = field(default_factory=list)
    api_calls: list[str] = field(default_factory=list)
    is_form: bool = False
    is_list: bool = False
    is_detail: bool = False
    file: str = ""


def parse_react_component(component_file: Path) -> ParsedComponent:
    """Parse React component file and return structured component information."""
    content = component_file.read_text(encoding="utf-8")

    imports = _extract_imports(content)
    state_variables = _extract_state_variables(content)
    api_calls = _extract_api_calls(content)
    form_fields = _extract_form_fields(content)

    is_form = "Form.useForm" in content or "onFinish" in content
    is_list = "rowData" in content or "ag-grid" in content.lower() or "AGrid" in content
    is_detail = "useParams" in content or "edit" in component_file.name.lower()

    return ParsedComponent(
        name=component_file.stem,
        imports=imports,
        state_variables=state_variables,
        form_fields=form_fields,
        api_calls=api_calls,
        is_form=is_form,
        is_list=is_list,
        is_detail=is_detail,
        file=str(component_file),
    )


def _extract_imports(content: str) -> list[dict]:
    """Extract import statements."""
    imports = []
    pattern = re.compile(
        r"import\s+(?:{\s*([^}]+)\s*}|(\w+))\s+from\s+['\"]([^'\"]+)['\"]"
    )
    for match in pattern.finditer(content):
        named = match.group(1)
        default = match.group(2)
        source = match.group(3)
        if named:
            for n in named.split(","):
                n = n.strip()
                as_match = re.search(r"(\w+)\s+as\s+(\w+)", n)
                if as_match:
                    imports.append({"name": as_match.group(2), "original": as_match.group(1), "source": source})
                else:
                    imports.append({"name": n, "original": n, "source": source})
        if default:
            imports.append({"name": default, "original": default, "source": source})
    return imports


def _extract_state_variables(content: str) -> list[str]:
    """Extract useState declarations."""
    states = []
    pattern = re.compile(r"const\s+\[([^\]]+)\]\s*=\s*useState")
    for match in pattern.finditer(content):
        vars_list = match.group(1).split(",")
        for v in vars_list:
            v = v.strip().strip("[")
            if v and not v.startswith("("):
                states.append(v)
    return states


def _extract_api_calls(content: str) -> list[str]:
    """Extract API call patterns."""
    calls = []
    pattern = re.compile(r"(evaluationApi\.\w+|axios\.\w+|fetch\()")
    for match in pattern.finditer(content):
        calls.append(match.group(1))
    return list(set(calls))


def _extract_form_fields(content: str) -> list[FormField]:
    """Extract antd Form.Item definitions (handles multi-line JSX)."""
    fields = []

    # Find all Form.Item blocks (multi-line)
    form_item_pattern = re.compile(
        r"<Form\.Item\s+([^>]+)>\s*<(Input|Select|InputNumber|DatePicker|TextArea|Checkbox|RangePicker)\b",
        re.DOTALL
    )
    for match in form_item_pattern.finditer(content):
        attrs = match.group(1)
        component = match.group(2)

        # Extract name (handles name="..." and name={...})
        name_match = re.search(r'name=\{?[\'\"](\w+)[\'\"]\}?', attrs)
        # Extract label (handles label="..." and label={...})
        label_match = re.search(r'label=\{?[\'\"]([^\'\"]+)[\'\"]\}?', attrs)

        if name_match:
            name = name_match.group(1)
            label = label_match.group(1) if label_match else name
            fields.append(FormField(name=name, label=label, component=component))

    return fields


def _detect_form_component(content: str, pos: int) -> str:
    """Detect which antd component is used in a Form.Item."""
    chunk = content[max(0, pos - 100):pos + 100]
    if "Select" in chunk:
        return "Select"
    if "DatePicker" in chunk or "RangePicker" in chunk:
        return "DatePicker"
    if "Input.TextArea" in chunk:
        return "TextArea"
    if "Checkbox" in chunk:
        return "Checkbox"
    if "InputNumber" in chunk:
        return "InputNumber"
    return "Input"
