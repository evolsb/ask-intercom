"""Tests for Docker deployment setup."""

from pathlib import Path


def test_env_example_exists():
    """Test that .env.example exists and has required variables."""
    env_example = Path(".env.example")
    assert env_example.exists(), ".env.example file is missing"

    content = env_example.read_text()
    assert "INTERCOM_ACCESS_TOKEN=" in content
    assert "OPENAI_API_KEY=" in content


def test_dockerfile_exists():
    """Test that Dockerfile exists."""
    dockerfile = Path("Dockerfile")
    assert dockerfile.exists(), "Dockerfile is missing"


def test_docker_compose_exists():
    """Test that docker-compose.yml exists and is valid."""
    compose_file = Path("docker-compose.yml")
    assert compose_file.exists(), "docker-compose.yml is missing"

    content = compose_file.read_text()
    assert "ask-intercom:" in content
    assert "8000:8000" in content
