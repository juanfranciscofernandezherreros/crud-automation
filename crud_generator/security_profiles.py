"""Configuración de seguridad por endpoint para proyectos generados."""

from .parsing import pluralize


def _csv(value):
    return [item.strip() for item in value.split(",") if item.strip()]


def ask_endpoint_security(entity_name, endpoints, custom_endpoints=None):
    """Pregunta roles y permisos para cada endpoint seleccionado en el wizard."""
    entity_lower = entity_name.lower()
    resource = pluralize(entity_lower)
    defaults = {
        "list": ("GET", f"/api/{resource}", ["USER", "ADMIN"], [f"{entity_lower}:read"]),
        "get": ("GET", f"/api/{resource}/{{id}}", ["USER", "ADMIN"], [f"{entity_lower}:read"]),
        "create": ("POST", f"/api/{resource}", ["ADMIN"], [f"{entity_lower}:create"]),
        "update": ("PUT", f"/api/{resource}/{{id}}", ["ADMIN"], [f"{entity_lower}:update"]),
        "patch": ("PATCH", f"/api/{resource}/{{id}}", ["ADMIN"], [f"{entity_lower}:update"]),
        "delete": ("DELETE", f"/api/{resource}/{{id}}", ["ADMIN"], [f"{entity_lower}:delete"]),
    }

    rules = []
    print("\nSeguridad por endpoint (roles y permisos/authorities):")
    for endpoint in endpoints:
        if endpoint not in defaults:
            continue
        method, path, default_roles, default_permissions = defaults[endpoint]
        print(f"\n  {method} {path}")
        roles_raw = input(
            f"    Roles permitidos [{','.join(default_roles)}]: "
        ).strip()
        permissions_raw = input(
            f"    Permisos requeridos [{','.join(default_permissions)}]: "
        ).strip()
        rules.append({
            "name": endpoint,
            "method": method,
            "path": path,
            "roles": _csv(roles_raw) if roles_raw else default_roles,
            "permissions": _csv(permissions_raw) if permissions_raw else default_permissions,
        })

    for endpoint in custom_endpoints or []:
        method = endpoint["method"].upper()
        suffix = endpoint["path"]
        path = f"/api/{resource}{suffix}"
        default_roles = ["ADMIN"]
        default_permissions = [f"{entity_lower}:{endpoint['name']}"]
        print(f"\n  {method} {path} (personalizado)")
        roles_raw = input(
            f"    Roles permitidos [{','.join(default_roles)}]: "
        ).strip()
        permissions_raw = input(
            f"    Permisos requeridos [{','.join(default_permissions)}]: "
        ).strip()
        rules.append({
            "name": endpoint["name"],
            "method": method,
            "path": path,
            "roles": _csv(roles_raw) if roles_raw else default_roles,
            "permissions": _csv(permissions_raw) if permissions_raw else default_permissions,
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
