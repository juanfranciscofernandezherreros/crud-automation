"""Utilidades de escritura del proyecto generado."""

import os
import re
from pathlib import Path


_MAIN_JAVA_MARKER = os.path.join("src", "main", "java")
_PACKAGE_RE = re.compile(r"^package\s+([\w.]+);", re.MULTILINE)
_CLASS_RE = re.compile(r"public\s+class\s+(\w+)")
_FINAL_FIELD_RE = re.compile(r"private\s+final\s+([\w.$<>?, ]+)\s+(\w+)\s*;")
_CONSTRUCTOR_RE = re.compile(r"public\s+(\w+)\s*\((.*?)\)\s*\{", re.DOTALL)
_NEW_TYPE_RE = re.compile(r"new\s+(\w+)\s*\(")


def _project_root(path):
    normalized = os.path.normpath(path)
    marker = os.sep + _MAIN_JAVA_MARKER + os.sep
    if marker not in normalized:
        return None
    return normalized.split(marker, 1)[0]


def _transform_java_source(path, content):
    filename = os.path.basename(path)

    if filename.endswith("Mapper.java"):
        content = content.replace('@Mapper(componentModel = "spring")', "@Mapper")

    if "@Service" in content:
        content = content.replace("import org.springframework.stereotype.Service;\n", "")
        content = content.replace("@Service\n", "")

    if filename == "CrudApplication.java" and "@ComponentScan(" not in content:
        content = content.replace(
            "import org.springframework.boot.autoconfigure.SpringBootApplication;\n",
            "import org.springframework.boot.autoconfigure.SpringBootApplication;\n"
            "import org.springframework.context.annotation.ComponentScan;\n"
            "import org.springframework.context.annotation.FilterType;\n"
            "import org.springframework.web.bind.annotation.RestController;\n",
        )
        content = content.replace(
            "@SpringBootApplication\n",
            "@SpringBootApplication\n"
            "@ComponentScan(\n"
            "        excludeFilters = @ComponentScan.Filter(\n"
            "                type = FilterType.ANNOTATION,\n"
            "                classes = RestController.class))\n",
        )

    return content


def _read_package(content):
    match = _PACKAGE_RE.search(content)
    return match.group(1) if match else None


def _constructor_dependencies(content, class_name):
    match = _CONSTRUCTOR_RE.search(content)
    if match and match.group(1) == class_name:
        params = []
        raw = match.group(2).strip()
        if raw:
            for parameter in raw.split(","):
                pieces = parameter.strip().split()
                if len(pieces) >= 2:
                    params.append((" ".join(pieces[:-1]), pieces[-1]))
        return params

    return [(field_type.strip(), name) for field_type, name in _FINAL_FIELD_RE.findall(content)]


def _bean_method_name(class_name):
    return class_name[:1].lower() + class_name[1:]


def _qualified_type(field_type, source_package, type_packages):
    clean = field_type.strip()
    if "." in clean or clean.startswith("java."):
        return clean
    simple = re.sub(r"<.*>", "", clean).strip()
    qualified = type_packages.get(simple)
    if qualified:
        return clean.replace(simple, qualified, 1)
    return clean


def _existing_instantiated_types(java_root):
    instantiated = set()
    for path in java_root.rglob("*.java"):
        if "configuration" not in path.parts:
            continue
        content = path.read_text(encoding="utf-8")
        instantiated.update(_NEW_TYPE_RE.findall(content))
    return instantiated


def _collect_candidates(java_root):
    candidates = []
    type_packages = {}

    for path in java_root.rglob("*.java"):
        if path.name == "GeneratedBeanConfiguration.java":
            continue
        content = path.read_text(encoding="utf-8")
        package = _read_package(content)
        if not package:
            continue

        class_match = _CLASS_RE.search(content)
        if class_match:
            type_packages[class_match.group(1)] = f"{package}.{class_match.group(1)}"
        elif "public interface " in content:
            interface_match = re.search(r"public\s+interface\s+(\w+)", content)
            if interface_match:
                type_packages[interface_match.group(1)] = f"{package}.{interface_match.group(1)}"

    instantiated = _existing_instantiated_types(java_root)

    for path in java_root.rglob("*.java"):
        if path.name == "GeneratedBeanConfiguration.java":
            continue
        content = path.read_text(encoding="utf-8")
        package = _read_package(content)
        if not package:
            continue

        if path.name.endswith("Mapper.java") and "@Mapper" in content:
            interface_match = re.search(r"public\s+interface\s+(\w+)", content)
            if interface_match:
                class_name = interface_match.group(1)
                candidates.append(("mapper", package, class_name, []))
            continue

        class_match = _CLASS_RE.search(content)
        if not class_match:
            continue
        class_name = class_match.group(1)

        if "@RestController" in content:
            candidates.append(
                ("controller", package, class_name, _constructor_dependencies(content, class_name))
            )
            continue

        if (class_name.endswith("Service") or class_name.endswith("ServiceImpl")) and class_name not in instantiated:
            candidates.append(
                ("service", package, class_name, _constructor_dependencies(content, class_name))
            )

    return candidates, type_packages


def _find_application_package(java_root):
    for path in java_root.rglob("CrudApplication.java"):
        package = _read_package(path.read_text(encoding="utf-8"))
        if package:
            return package
    return "com.example.crud"


def _render_configuration(application_package, candidates, type_packages):
    methods = []
    seen = set()

    for kind, package, class_name, dependencies in sorted(candidates, key=lambda item: item[2]):
        qualified_class = f"{package}.{class_name}"
        method_name = _bean_method_name(class_name)
        if method_name in seen:
            continue
        seen.add(method_name)

        if kind == "mapper":
            body = (
                f"    @org.springframework.context.annotation.Bean\n"
                f"    public {qualified_class} {method_name}() {{\n"
                f"        return org.mapstruct.factory.Mappers.getMapper({qualified_class}.class);\n"
                f"    }}"
            )
        else:
            params = []
            args = []
            for field_type, name in dependencies:
                params.append(f"{_qualified_type(field_type, package, type_packages)} {name}")
                args.append(name)
            body = (
                f"    @org.springframework.context.annotation.Bean\n"
                f"    public {qualified_class} {method_name}({', '.join(params)}) {{\n"
                f"        return new {qualified_class}({', '.join(args)});\n"
                f"    }}"
            )
        methods.append(body)

    return (
        f"package {application_package}.configuration;\n\n"
        "@org.springframework.context.annotation.Configuration\n"
        "public class GeneratedBeanConfiguration {\n\n"
        + "\n\n".join(methods)
        + "\n}\n"
    )


def _refresh_generated_bean_configuration(project_root):
    java_root = Path(project_root) / "src" / "main" / "java"
    if not java_root.is_dir():
        return

    candidates, type_packages = _collect_candidates(java_root)
    if not candidates:
        return

    application_package = _find_application_package(java_root)
    config_dir = java_root / Path(*application_package.split(".")) / "configuration"
    config_dir.mkdir(parents=True, exist_ok=True)
    config_file = config_dir / "GeneratedBeanConfiguration.java"
    config_file.write_text(
        _render_configuration(application_package, candidates, type_packages),
        encoding="utf-8",
    )


def write_file(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if path.endswith(".java") and _project_root(path):
        content = _transform_java_source(path, content)

    with open(path, "w", encoding="utf-8") as file:
        file.write(content)

    project_root = _project_root(path)
    if project_root and path.endswith(".java"):
        _refresh_generated_bean_configuration(project_root)
