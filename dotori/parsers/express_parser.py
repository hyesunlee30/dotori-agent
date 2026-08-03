import re
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class ParsedRoute:
    method: str
    path: str
    handler: str
    request_body: bool = False
    path_params: list[str] = field(default_factory=list)
    query_params: list[str] = field(default_factory=list)


@dataclass
class ParsedRoutes:
    routes: list[ParsedRoute]
    controller_file: str
    file: str


def parse_express_routes(routes_file: Path) -> ParsedRoutes:
    """Parse Express router file and return structured route definitions."""
    content = routes_file.read_text(encoding="utf-8")
    routes = []

    # Pattern 1: router.route('/path').get(handler).post(handler)
    chained_pattern = re.compile(
        r"router\.route\(['\"]([^'\"]+)['\"]\)\s*\n((?:\s*\.\w+\([^)]+\);?\s*\n?)+)"
    )
    for match in chained_pattern.finditer(content):
        path = match.group(1)
        chain = match.group(2)
        path_params = list(set(re.findall(r":(\w+)", path)))

        method_pattern = re.compile(r"\.(\w+)\s*\(\s*(\w+)\s*\)")
        for method_match in method_pattern.finditer(chain):
            method = method_match.group(1).upper()
            handler = method_match.group(2)
            routes.append(ParsedRoute(
                method=method,
                path=path,
                handler=handler,
                path_params=path_params,
            ))

    # Pattern 2: router.get('/path', handler) / router.get('/path', handler)
    direct_pattern = re.compile(
        r"router\.(get|post|put|delete|patch)\s*\(\s*['\"]([^'\"]+)['\"]\s*,\s*(\w+)\s*\)"
    )
    for match in direct_pattern.finditer(content):
        method = match.group(1).upper()
        path = match.group(2)
        handler = match.group(3)
        path_params = list(set(re.findall(r":(\w+)", path)))

        # Avoid duplicates
        if not any(r.path == path and r.method == method for r in routes):
            routes.append(ParsedRoute(
                method=method,
                path=path,
                handler=handler,
                path_params=path_params,
            ))

    # Extract query params from req.query usage
    query_params = list(set(re.findall(r"req\.query\.(\w+)", content)))

    # Check for body usage
    has_body = "req.body" in content

    # Update routes with query params and body info
    for route in routes:
        route.query_params = query_params
        route.request_body = has_body

    return ParsedRoutes(
        routes=routes,
        controller_file=_extract_controller(content),
        file=str(routes_file),
    )


def _extract_handler(content: str, start_pos: int) -> str:
    """Extract handler function name after route definition."""
    # Look for handler reference in the chain
    chunk = content[start_pos:start_pos + 300]
    match = re.search(r"\.\s*(get|post|put|delete|patch)\s*\(\s*(\w+)", chunk)
    if match:
        return match.group(2)
    match = re.search(r"\(\s*(\w+)", chunk)
    if match:
        return match.group(1)
    return "unknown"


def _extract_controller(content: str) -> str:
    """Extract controller file name from require/import."""
    match = re.search(r"require\(['\"]\.\/(.+?)['\"]\)", content)
    if match:
        return match.group(1)
    match = re.search(r"from\s+['\"]\.\/(.+?)['\"]", content)
    if match:
        return match.group(1)
    return "unknown"
