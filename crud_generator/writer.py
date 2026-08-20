"""Utilidades de escritura del proyecto generado."""

import os
import re
from pathlib import Path


_MAIN_JAVA_MARKER = os.path.join("src", "main", "java")
_PACKAGE_RE = re.compile(r"^package\s+([\w.]+);", re.MULTILINE)
_CLASS_RE = re.compile(r"public\s+class\s+(\w+)")
_NEW_TYPE_RE = re.compile(r"new\s+([\w.]+)\s*\(")


def _project_root(path):
    normalized = os.path.normpath(path)
    marker = os.sep + _MAIN_JAVA_MARKER + os.sep
    if marker not in normalized:
        return None
    return normalized.split(marker, 1)[0]


def _transform_java_source(path, content):
    """Aplica la politica de registro explicito antes de escribir Java.

    Los mappers y services dejan de registrarse por component scanning. Los
    controllers conservan @RestController por su semantica MVC, pero la clase
    principal excluye esa anotacion del component scan para que sus instancias
    procedan exclusivamente de GeneratedBeanConfiguration.
    """
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


def _bean_method_name(class_name):
    return class_name[:1].lower() + class_name[1:]


def _existing_instantiated_types(java_root):
    """Tipos ya construidos por configuraciones escritas por el generador.

    Hexagonal/clean, por ejemplo, crean el servicio desde UseCaseConfiguration.
    No se debe generar un segundo @Bean para el mismo tipo.
    """
    instantiated = set()
    for path in java_root.rglob("*.java"):
        if "configuration" not in path.parts or path.name == "GeneratedBeanConfiguration.java":
            continue
        content = path.read_text(encoding="utf-8")
        for constructed_type in _NEW_TYPE_RE.findall(content):
            instantiated.add(constructed_type.rsplit(".", 1)[-1])
    return instantiated


def _collect_candidates(java_root):
    """Localiza mappers, services y controllers que deben ser @Bean.

    Deliberadamente no intenta reconstruir constructores ni resolver imports.
    Esa aproximacion era fragil con Lombok, genericos y dependencias externas.
    La resolucion real del constructor se delega al BeanFactory de Spring.
    """
    candidates = []
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
                candidates.append(("mapper", package, interface_match.group(1)))
            continue

        class_match = _CLASS_RE.search(content)
        if not class_match:
            continue
        class_name = class_match.group(1)

        if "@RestController" in content:
            candidates.append(("controller", package, class_name))
            continue

        if (
            class_name.endswith("Service") or class_name.endswith("ServiceImpl")
        ) and class_name not in instantiated:
            candidates.append(("service", package, class_name))

    return candidates


def _find_application_package(java_root):
    for path in java_root.rglob("CrudApplication.java"):
        package = _read_package(path.read_text(encoding="utf-8"))
        if package:
            return package
    return "com.example.crud"


def _render_configuration(application_package, candidates):
    """Genera la configuracion explicita de beans.

    Para services/controllers usamos AutowireCapableBeanFactory#createBean.
    Sigue siendo un @Bean explicito, pero evita que el generador tenga que
    parsear constructores Java. Spring elige el constructor e inyecta sus
    dependencias exactamente igual que al crear un componente escaneado.
    """
    methods = []
    seen = set()

    for kind, package, class_name in sorted(candidates, key=lambda item: item[2]):
        qualified_class = f"{package}.{class_name}"
        method_name = _bean_method_name(class_name)
        if method_name in seen:
            continue
        seen.add(method_name)

        if kind == "mapper":
            body = (
                "    @org.springframework.context.annotation.Bean\n"
                f"    public {qualified_class} {method_name}() {{\n"
                f"        return org.mapstruct.factory.Mappers.getMapper({qualified_class}.class);\n"
                "    }"
            )
        else:
            body = (
                "    @org.springframework.context.annotation.Bean\n"
                f"    public {qualified_class} {method_name}(\n"
                "            org.springframework.beans.factory.config.AutowireCapableBeanFactory beanFactory) {\n"
                f"        return beanFactory.createBean({qualified_class}.class);\n"
                "    }"
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

    candidates = _collect_candidates(java_root)
    if not candidates:
        return

    application_package = _find_application_package(java_root)
    config_dir = java_root / Path(*application_package.split(".")) / "configuration"
    config_dir.mkdir(parents=True, exist_ok=True)
    config_file = config_dir / "GeneratedBeanConfiguration.java"
    config_file.write_text(
        _render_configuration(application_package, candidates),
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
