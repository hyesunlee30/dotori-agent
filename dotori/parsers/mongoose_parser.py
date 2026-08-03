import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class MongooseField:
    name: str
    type: str
    required: bool = False
    enum_values: list[str] | None = None
    default: Any = None
    min: int | None = None
    max: int | None = None
    maxlength: int | None = None
    trim: bool = False


@dataclass
class ParsedSchema:
    collection_name: str
    fields: list[MongooseField]
    indexes: list[str]
    timestamps: bool
    file: str


def parse_mongoose_schema(model_file: Path) -> ParsedSchema:
    """Parse Mongoose schema file and return structured field definitions."""
    content = model_file.read_text(encoding="utf-8")
    fields = []

    # Find the schema body using brace matching
    schema_start = content.find("new mongoose.Schema(")
    if schema_start == -1:
        schema_start = content.find("mongoose.Schema(")
    if schema_start == -1:
        return ParsedSchema(collection_name="unknown", fields=[], indexes=[], timestamps=False, file=str(model_file))

    # Find the opening brace after Schema(
    brace_start = content.find("{", schema_start)
    if brace_start == -1:
        return ParsedSchema(collection_name="unknown", fields=[], indexes=[], timestamps=False, file=str(model_file))

    # Extract the schema body with balanced braces
    schema_body = _extract_braced_block(content, brace_start)

    # Parse individual fields
    field_pattern = re.compile(
        r"(\w+)\s*:\s*\{([^}]+)\}",
        re.DOTALL
    )
    for match in field_pattern.finditer(schema_body):
        field_name = match.group(1)
        if field_name in ("timestamps", "options", "index", "indexes"):
            continue
        field_def = match.group(2)
        field_info = _parse_field_definition(field_name, field_def)
        fields.append(field_info)

    # Extract indexes
    indexes = []
    index_pattern = re.compile(r"schema\.index\(\s*(\{[^}]+\})")
    for match in index_pattern.finditer(content):
        indexes.append(match.group(1))

    # Check for timestamps
    has_timestamps = "timestamps" in content

    # Extract collection name
    collection_match = re.search(r"mongoose\.model\s*\(\s*['\"](\w+)['\"]", content)
    collection_name = collection_match.group(1) if collection_match else "unknown"

    return ParsedSchema(
        collection_name=collection_name,
        fields=fields,
        indexes=indexes,
        timestamps=has_timestamps,
        file=str(model_file),
    )


def _parse_field_definition(name: str, definition: str) -> MongooseField:
    """Parse individual Mongoose field definition."""
    field_type = "String"
    type_match = re.search(r"type:\s*(\w+)", definition)
    if type_match:
        field_type = type_match.group(1)

    required = "required" in definition

    enum_values = None
    # Handle both enum: [...] and enum: { values: [...] }
    enum_match = re.search(r"enum:\s*\{[^}]*values:\s*\[([^\]]+)\]", definition)
    if not enum_match:
        enum_match = re.search(r"enum:\s*\[([^\]]+)\]", definition)
    if enum_match:
        enum_values = [v.strip().strip("'\"") for v in enum_match.group(1).split(",")]

    default = None
    default_match = re.search(r"default:\s*['\"]([^'\"]+)['\"]", definition)
    if default_match:
        default = default_match.group(1)
    else:
        default_match = re.search(r"default:\s*(\w+)", definition)
        if default_match:
            default = default_match.group(1)

    min_val = None
    min_match = re.search(r"min:\s*\[\s*(\d+)", definition)
    if not min_match:
        min_match = re.search(r"min:\s*(\d+)", definition)
    if min_match:
        min_val = int(min_match.group(1))

    max_val = None
    max_match = re.search(r"max:\s*\[\s*(\d+)", definition)
    if not max_match:
        max_match = re.search(r"max:\s*(\d+)", definition)
    if max_match:
        max_val = int(max_match.group(1))

    maxlength = None
    maxlength_match = re.search(r"maxlength:\s*\[\s*(\d+)", definition)
    if not maxlength_match:
        maxlength_match = re.search(r"maxlength:\s*(\d+)", definition)
    if maxlength_match:
        maxlength = int(maxlength_match.group(1))

    trim = "trim" in definition

    return MongooseField(
        name=name,
        type=field_type,
        required=required,
        enum_values=enum_values,
        default=default,
        min=min_val,
        max=max_val,
        maxlength=maxlength,
        trim=trim,
    )


def _extract_braced_block(content: str, start: int) -> str:
    """Extract content within balanced braces starting from position."""
    if start >= len(content) or content[start] != "{":
        return ""
    depth = 0
    result = []
    for i in range(start, len(content)):
        if content[i] == "{":
            depth += 1
        elif content[i] == "}":
            depth -= 1
            if depth == 0:
                return "".join(result)
        result.append(content[i])
    return "".join(result)
