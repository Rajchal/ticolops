"""
API documentation validation tests.
"""

import pytest
import json
from httpx import AsyncClient
from app.main import app


class TestAPIDocumentation:
    """Test API documentation generation and completeness"""

    @pytest.fixture
    async def client(self):
        async with AsyncClient(app=app, base_url="http://test") as ac:
            yield ac

    @pytest.mark.asyncio
    async def test_openapi_schema_generation(self, client):
        """Test that OpenAPI schema is generated correctly"""
        
        response = await client.get("/openapi.json")
        assert response.status_code == 200
        
        schema = response.json()
        
        # Verify basic schema structure
        assert "openapi" in schema
        assert "info" in schema
        assert "paths" in schema
        assert "components" in schema
        
        # Verify API info
        info = schema["info"]
        assert info["title"] == "Ticolops API"
        assert info["version"] == "1.0.0"
        assert "description" in info
        
        # Verify paths exist
        paths = schema["paths"]
        assert len(paths) > 0
        
        # Check for key endpoints
        expected_paths = [
            "/api/auth/register",
            "/api/auth/login",
            "/api/auth/me",
            "/api/projects",
            "/api/users"
        ]
        
        for expected_path in expected_paths:
            assert expected_path in paths, f"Expected path {expected_path} not found in OpenAPI schema"

    @pytest.mark.asyncio
    async def test_swagger_ui_accessibility(self, client):
        """Test that Swagger UI is accessible"""
        
        response = await client.get("/docs")
        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")

    @pytest.mark.asyncio
    async def test_redoc_accessibility(self, client):
        """Test that ReDoc is accessible"""
        
        response = await client.get("/redoc")
        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")

    @pytest.mark.asyncio
    async def test_endpoint_documentation_completeness(self, client):
        """Test that all endpoints have proper documentation"""
        
        response = await client.get("/openapi.json")
        schema = response.json()
        
        paths = schema["paths"]
        
        for path, methods in paths.items():
            for method, details in methods.items():
                # Each endpoint should have summary and description
                assert "summary" in details or "description" in details, \
                    f"Endpoint {method.upper()} {path} missing summary/description"
                
                # Check for response documentation
                assert "responses" in details, \
                    f"Endpoint {method.upper()} {path} missing response documentation"
                
                responses = details["responses"]
                
                # Should have at least success response
                success_codes = ["200", "201", "202", "204"]
                has_success = any(code in responses for code in success_codes)
                assert has_success, \
                    f"Endpoint {method.upper()} {path} missing success response documentation"

    @pytest.mark.asyncio
    async def test_security_scheme_documentation(self, client):
        """Test that security schemes are properly documented"""
        
        response = await client.get("/openapi.json")
        schema = response.json()
        
        # Check for security schemes
        assert "components" in schema
        components = schema["components"]
        
        if "securitySchemes" in components:
            security_schemes = components["securitySchemes"]
            
            # Should have Bearer auth
            assert "BearerAuth" in security_schemes or "HTTPBearer" in security_schemes, \
                "Bearer authentication scheme not documented"

    @pytest.mark.asyncio
    async def test_error_response_documentation(self, client):
        """Test that error responses are properly documented"""
        
        response = await client.get("/openapi.json")
        schema = response.json()
        
        paths = schema["paths"]
        
        # Check that endpoints document common error responses
        common_error_codes = ["400", "401", "403", "404", "422", "500"]
        
        for path, methods in paths.items():
            for method, details in methods.items():
                responses = details.get("responses", {})
                
                # Protected endpoints should document 401
                if "security" in details or any("Authorization" in str(param) for param in details.get("parameters", [])):
                    assert "401" in responses, \
                        f"Protected endpoint {method.upper()} {path} should document 401 response"

    @pytest.mark.asyncio
    async def test_request_body_documentation(self, client):
        """Test that request bodies are properly documented"""
        
        response = await client.get("/openapi.json")
        schema = response.json()
        
        paths = schema["paths"]
        
        for path, methods in paths.items():
            for method, details in methods.items():
                # POST and PUT methods should have request body documentation
                if method.lower() in ["post", "put", "patch"]:
                    if "requestBody" in details:
                        request_body = details["requestBody"]
                        
                        # Should have content
                        assert "content" in request_body, \
                            f"Endpoint {method.upper()} {path} request body missing content"
                        
                        content = request_body["content"]
                        
                        # Should have application/json
                        assert "application/json" in content, \
                            f"Endpoint {method.upper()} {path} should accept JSON"

    @pytest.mark.asyncio
    async def test_parameter_documentation(self, client):
        """Test that parameters are properly documented"""
        
        response = await client.get("/openapi.json")
        schema = response.json()
        
        paths = schema["paths"]
        
        for path, methods in paths.items():
            for method, details in methods.items():
                if "parameters" in details:
                    parameters = details["parameters"]
                    
                    for param in parameters:
                        # Each parameter should have required fields
                        assert "name" in param, \
                            f"Parameter in {method.upper()} {path} missing name"
                        
                        assert "in" in param, \
                            f"Parameter {param.get('name')} in {method.upper()} {path} missing 'in' field"
                        
                        # Should have description for clarity
                        assert "description" in param or "schema" in param, \
                            f"Parameter {param.get('name')} in {method.upper()} {path} missing description"

    @pytest.mark.asyncio
    async def test_tag_organization(self, client):
        """Test that endpoints are properly organized with tags"""
        
        response = await client.get("/openapi.json")
        schema = response.json()
        
        # Should have tags defined
        assert "tags" in schema, "API schema should define tags for organization"
        
        tags = schema["tags"]
        tag_names = [tag["name"] for tag in tags]
        
        # Check for expected tags
        expected_tags = ["authentication", "users", "projects", "repository", "deployment"]
        
        for expected_tag in expected_tags:
            assert expected_tag in tag_names, f"Expected tag '{expected_tag}' not found"
        
        # Check that endpoints use tags
        paths = schema["paths"]
        
        for path, methods in paths.items():
            for method, details in methods.items():
                assert "tags" in details, \
                    f"Endpoint {method.upper()} {path} should have tags for organization"

    @pytest.mark.asyncio
    async def test_example_completeness(self, client):
        """Test that endpoints have comprehensive examples"""
        
        response = await client.get("/openapi.json")
        schema = response.json()
        
        paths = schema["paths"]
        
        # Check for examples in request/response schemas
        for path, methods in paths.items():
            for method, details in methods.items():
                # Check request body examples
                if "requestBody" in details:
                    request_body = details["requestBody"]
                    content = request_body.get("content", {})
                    
                    for media_type, media_details in content.items():
                        if "schema" in media_details:
                            # Should have examples or example
                            has_examples = "examples" in media_details or "example" in media_details.get("schema", {})
                            
                            # For important endpoints, examples are crucial
                            if any(keyword in path for keyword in ["/auth/", "/projects", "/deploy"]):
                                assert has_examples, \
                                    f"Important endpoint {method.upper()} {path} should have request examples"

    @pytest.mark.asyncio
    async def test_response_schema_validation(self, client):
        """Test that response schemas are properly defined"""
        
        response = await client.get("/openapi.json")
        schema = response.json()
        
        paths = schema["paths"]
        
        for path, methods in paths.items():
            for method, details in methods.items():
                responses = details.get("responses", {})
                
                for status_code, response_details in responses.items():
                    if "content" in response_details:
                        content = response_details["content"]
                        
                        for media_type, media_details in content.items():
                            if media_type == "application/json":
                                # Should have schema for JSON responses
                                assert "schema" in media_details, \
                                    f"JSON response for {method.upper()} {path} ({status_code}) should have schema"

    @pytest.mark.asyncio
    async def test_api_versioning_documentation(self, client):
        """Test that API versioning is properly documented"""
        
        response = await client.get("/openapi.json")
        schema = response.json()
        
        # Check version in info
        info = schema["info"]
        assert "version" in info, "API should have version information"
        
        version = info["version"]
        assert version, "API version should not be empty"
        
        # Version should follow semantic versioning pattern
        import re
        version_pattern = r'^\d+\.\d+\.\d+.*$'
        assert re.match(version_pattern, version), \
            f"API version '{version}' should follow semantic versioning"

    @pytest.mark.asyncio
    async def test_server_documentation(self, client):
        """Test that server information is documented"""
        
        response = await client.get("/openapi.json")
        schema = response.json()
        
        # Should have servers defined
        if "servers" in schema:
            servers = schema["servers"]
            
            for server in servers:
                assert "url" in server, "Server should have URL"
                assert "description" in server, "Server should have description"

    @pytest.mark.asyncio
    async def test_contact_and_license_info(self, client):
        """Test that contact and license information is included"""
        
        response = await client.get("/openapi.json")
        schema = response.json()
        
        info = schema["info"]
        
        # Should have contact information
        if "contact" in info:
            contact = info["contact"]
            assert "name" in contact or "email" in contact, \
                "Contact information should include name or email"
        
        # Should have license information
        if "license" in info:
            license_info = info["license"]
            assert "name" in license_info, "License should have name"

    @pytest.mark.asyncio
    async def test_deprecated_endpoint_marking(self, client):
        """Test that deprecated endpoints are properly marked"""
        
        response = await client.get("/openapi.json")
        schema = response.json()
        
        paths = schema["paths"]
        
        # Check for deprecated field in endpoints
        for path, methods in paths.items():
            for method, details in methods.items():
                if details.get("deprecated", False):
                    # Deprecated endpoints should have clear documentation
                    assert "description" in details, \
                        f"Deprecated endpoint {method.upper()} {path} should have description explaining deprecation"

    @pytest.mark.asyncio
    async def test_webhook_documentation(self, client):
        """Test that webhook endpoints are properly documented"""
        
        response = await client.get("/openapi.json")
        schema = response.json()
        
        paths = schema["paths"]
        
        # Look for webhook endpoints
        webhook_paths = [path for path in paths.keys() if "webhook" in path.lower()]
        
        for webhook_path in webhook_paths:
            methods = paths[webhook_path]
            
            # Webhook endpoints should be POST
            assert "post" in methods, f"Webhook endpoint {webhook_path} should support POST"
            
            post_details = methods["post"]
            
            # Should have security documentation for signature verification
            assert "security" in post_details or "description" in post_details, \
                f"Webhook endpoint {webhook_path} should document security requirements"