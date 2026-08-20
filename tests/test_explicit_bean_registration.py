import tempfile
import unittest
from pathlib import Path

from crud_generator.writer import write_file


class ExplicitBeanRegistrationTest(unittest.TestCase):
    def _java_root(self, directory):
        return Path(directory) / "crud-demo" / "src" / "main" / "java" / "com" / "example" / "crud"

    def test_layered_service_mapper_and_controller_are_registered_as_beans(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self._java_root(directory)

            write_file(
                str(root / "CrudApplication.java"),
                """package com.example.crud;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

@SpringBootApplication
public class CrudApplication {
    public static void main(String[] args) {
        SpringApplication.run(CrudApplication.class, args);
    }
}
""",
            )
            write_file(
                str(root / "repository" / "UserRepository.java"),
                """package com.example.crud.repository;
public interface UserRepository {}
""",
            )
            write_file(
                str(root / "mapper" / "UserMapper.java"),
                """package com.example.crud.mapper;
import org.mapstruct.Mapper;
@Mapper(componentModel = "spring")
public interface UserMapper {}
""",
            )
            write_file(
                str(root / "service" / "impl" / "UserServiceImpl.java"),
                """package com.example.crud.service.impl;
import com.example.crud.mapper.UserMapper;
import com.example.crud.repository.UserRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;

@Service
@RequiredArgsConstructor
public class UserServiceImpl {
    private final UserRepository repository;
    private final UserMapper mapper;
}
""",
            )
            write_file(
                str(root / "controller" / "UserController.java"),
                """package com.example.crud.controller;
import com.example.crud.service.impl.UserServiceImpl;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequiredArgsConstructor
public class UserController {
    private final UserServiceImpl service;
}
""",
            )

            mapper = (root / "mapper" / "UserMapper.java").read_text(encoding="utf-8")
            service = (root / "service" / "impl" / "UserServiceImpl.java").read_text(encoding="utf-8")
            application = (root / "CrudApplication.java").read_text(encoding="utf-8")
            config = (root / "configuration" / "GeneratedBeanConfiguration.java").read_text(encoding="utf-8")

            self.assertIn("@Mapper\n", mapper)
            self.assertNotIn("componentModel", mapper)
            self.assertNotIn("@Service", service)
            self.assertNotIn("org.springframework.stereotype.Service", service)
            self.assertIn("@ComponentScan", application)
            self.assertIn("RestController.class", application)
            self.assertIn("UserMapper userMapper()", config)
            self.assertIn("Mappers.getMapper(com.example.crud.mapper.UserMapper.class)", config)
            self.assertIn("UserServiceImpl userServiceImpl(", config)
            self.assertIn("UserController userController(", config)

    def test_existing_use_case_bean_is_not_duplicated(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self._java_root(directory)

            write_file(
                str(root / "CrudApplication.java"),
                """package com.example.crud;
import org.springframework.boot.autoconfigure.SpringBootApplication;
@SpringBootApplication
public class CrudApplication {}
""",
            )
            write_file(
                str(root / "application" / "port" / "out" / "UserPersistencePort.java"),
                """package com.example.crud.application.port.out;
public interface UserPersistencePort {}
""",
            )
            write_file(
                str(root / "application" / "service" / "UserService.java"),
                """package com.example.crud.application.service;
import com.example.crud.application.port.out.UserPersistencePort;
public class UserService {
    private final UserPersistencePort persistencePort;
    public UserService(UserPersistencePort persistencePort) {
        this.persistencePort = persistencePort;
    }
}
""",
            )
            write_file(
                str(root / "configuration" / "UseCaseConfiguration.java"),
                """package com.example.crud.configuration;
import com.example.crud.application.port.out.UserPersistencePort;
import com.example.crud.application.service.UserService;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
@Configuration
public class UseCaseConfiguration {
    @Bean
    public Object userUseCase(UserPersistencePort persistencePort) {
        return new UserService(persistencePort);
    }
}
""",
            )

            config = (root / "configuration" / "GeneratedBeanConfiguration.java").read_text(encoding="utf-8")
            self.assertNotIn("UserService userService(", config)


if __name__ == "__main__":
    unittest.main()
