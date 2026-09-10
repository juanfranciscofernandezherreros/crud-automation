"""Configuración de seguridad por endpoint para proyectos generados."""

from .parsing import DEFAULT_ENDPOINTS, pluralize


def _csv(value):
    return [item.strip() for item in value.split(",") if item.strip()]


def _default_security_rule(entity_lower, resource, endpoint):
    defaults = {
        "list": ("GET", f"/api/{resource}", ["USER", "ADMIN"], [f"{entity_lower}:read"]),
        "get": ("GET", f"/api/{resource}/{{id}}", ["USER", "ADMIN"], [f"{entity_lower}:read"]),
        "create": ("POST", f"/api/{resource}", ["ADMIN"], [f"{entity_lower}:create"]),
        "update": ("PUT", f"/api/{resource}/{{id}}", ["ADMIN"], [f"{entity_lower}:update"]),
        "patch": ("PATCH", f"/api/{resource}/{{id}}", ["ADMIN"], [f"{entity_lower}:update"]),
        "delete": ("DELETE", f"/api/{resource}/{{id}}", ["ADMIN"], [f"{entity_lower}:delete"]),
    }
    if endpoint not in defaults:
        return None
    method, path, roles, permissions = defaults[endpoint]
    return {
        "name": endpoint,
        "method": method,
        "path": path,
        "roles": roles,
        "permissions": permissions,
    }


def _default_custom_security_rule(entity_lower, resource, endpoint):
    return {
        "name": endpoint["name"],
        "method": endpoint["method"].upper(),
        "path": f"/api/{resource}{endpoint['path']}",
        "roles": ["ADMIN"],
        "permissions": [f"{entity_lower}:{endpoint['name']}"],
    }


def ask_endpoint_security(entity_name, endpoints, custom_endpoints=None):
    """Aplica seguridad sensata por defecto y solo pregunta si se quiere personalizar."""
    entity_lower = entity_name.lower()
    resource = pluralize(entity_lower)
    selected_endpoints = list(endpoints or DEFAULT_ENDPOINTS)
    custom_endpoints = custom_endpoints or []

    default_rules = []
    for endpoint in selected_endpoints:
        rule = _default_security_rule(entity_lower, resource, endpoint)
        if rule:
            default_rules.append(rule)
    default_rules.extend(
        _default_custom_security_rule(entity_lower, resource, endpoint)
        for endpoint in custom_endpoints
    )

    raw = input(
        "¿Personalizar seguridad por endpoint? "
        "(Enter = usar roles/permisos recomendados) (s/N): "
    ).strip().lower()
    if raw not in ("s", "si", "sí", "y", "yes"):
        print(f"  Seguridad por defecto aplicada a {len(default_rules)} endpoints.")
        return default_rules

    rules = []
    print("\nSeguridad por endpoint (Enter conserva el valor recomendado):")
    for rule in default_rules:
        custom = any(endpoint.get("name") == rule["name"] for endpoint in custom_endpoints)
        suffix = " (personalizado)" if custom else ""
        print(f"\n  {rule['method']} {rule['path']}{suffix}")
        roles_raw = input(
            f"    Roles permitidos [{','.join(rule['roles'])}]: "
        ).strip()
        permissions_raw = input(
            f"    Permisos requeridos [{','.join(rule['permissions'])}]: "
        ).strip()
        rules.append({
            **rule,
            "roles": _csv(roles_raw) if roles_raw else rule["roles"],
            "permissions": _csv(permissions_raw) if permissions_raw else rule["permissions"],
        })
    return rules


def _access_expression(rule):
    checks = []
    roles = rule.get("roles") or []
    permissions = rule.get("permissions") or []
    if roles:
        quoted = ", ".join(f"'{role}'" for role in roles)
        checks.append(f"hasAnyRole({quoted})")
    for permission in permissions:
        checks.append(f"hasAuthority('{permission}')")
    return " and ".join(checks) if checks else "isAuthenticated()"


def build_security_config(rules):
    """Genera SecurityConfiguration usando roles y permisos por endpoint."""
    matcher_lines = []
    roles = {"ADMIN", "USER"}
    permissions = set()
    for rule in rules:
        roles.update(rule.get("roles") or [])
        permissions.update(rule.get("permissions") or [])
        path = rule["path"].replace("{id}", "*")
        expression = _access_expression(rule)
        matcher_lines.append(
            "                        .requestMatchers(org.springframework.http.HttpMethod."
            f"{rule['method']}, \"{path}\")\n"
            "                        .access(new WebExpressionAuthorizationManager("
            f"\"{expression}\"))"
        )

    authorities = [f"ROLE_{role}" for role in sorted(roles)] + sorted(permissions)
    authority_args = ", ".join(f'\"{value}\"' for value in authorities)
    matchers = "\n".join(matcher_lines)

    return f'''package com.example.crud.configuration;

import lombok.RequiredArgsConstructor;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.security.config.Customizer;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.core.userdetails.User;
import org.springframework.security.core.userdetails.UserDetailsService;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.security.provisioning.InMemoryUserDetailsManager;
import org.springframework.security.web.SecurityFilterChain;
import org.springframework.security.web.authentication.UsernamePasswordAuthenticationFilter;
import org.springframework.security.config.http.SessionCreationPolicy;
import org.springframework.security.web.access.expression.WebExpressionAuthorizationManager;

@Configuration
@RequiredArgsConstructor
public class SecurityConfiguration {{
    private final RateLimitFilter rateLimitFilter;

    @Bean
    SecurityFilterChain securityFilterChain(HttpSecurity http) throws Exception {{
        return http
                .csrf(csrf -> csrf.disable())
                .sessionManagement(session -> session
                        .sessionCreationPolicy(SessionCreationPolicy.STATELESS))
                .authorizeHttpRequests(auth -> auth
                        .requestMatchers("/actuator/health", "/v3/api-docs/**", "/swagger-ui/**").permitAll()
                        .requestMatchers("/actuator/**").hasRole("ADMIN")
{matchers}
                        .requestMatchers("/api/**").denyAll()
                        .anyRequest().authenticated())
                .httpBasic(Customizer.withDefaults())
                .addFilterBefore(rateLimitFilter, UsernamePasswordAuthenticationFilter.class)
                .build();
    }}

    @Bean
    PasswordEncoder passwordEncoder() {{
        return new BCryptPasswordEncoder();
    }}

    @Bean
    UserDetailsService userDetailsService(
            @Value("${{app.security.user}}") String username,
            @Value("${{app.security.password}}") String password,
            PasswordEncoder encoder) {{
        return new InMemoryUserDetailsManager(User.withUsername(username)
                .password(encoder.encode(password))
                .authorities({authority_args})
                .build());
    }}
}}
'''


def install_endpoint_security(rules):
    """Instala la plantilla de seguridad para la ejecución actual del wizard."""
    from . import templates
    templates.SECURITY_CONFIG = build_security_config(rules)
