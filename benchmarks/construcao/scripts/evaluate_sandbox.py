import os
import sys
import json
import shutil
import tempfile
import subprocess
import logging
from pathlib import Path

# Add project root to path to allow importing workspace utils if needed
sys.path.append(str(Path(__file__).resolve().parents[3]))

logger = logging.getLogger("benchmark.evaluate_sandbox")


def run_local_pytest(temp_dir_path: Path) -> dict:
    """Executes pytest locally in a subprocess under a clean, isolated directory."""
    report_json_path = temp_dir_path / "report.json"
    
    # Run pytest with json-report
    cmd = [
        sys.executable,
        "-m",
        "pytest",
        "tests/test_code.py",
        "--json-report",
        f"--json-report-file={report_json_path}",
        "--tb=short"
    ]
    
    compilation_success = True
    tests_passed = False
    total_tests = 0
    passed_tests = 0
    failed_tests = 0
    error_details = None

    try:
        # Run subprocess with a 5-second timeout
        res = subprocess.run(
            cmd,
            cwd=str(temp_dir_path),
            capture_output=True,
            text=True,
            timeout=5
        )
        
        # Check if pytest was able to load/compile and run
        # Exit code 4 means no tests collected or command error; exit code 1 or 0 means tests ran
        if report_json_path.exists():
            try:
                with open(report_json_path, "r", encoding="utf-8") as f:
                    report_data = json.load(f)
                
                summary = report_data.get("summary", {})
                passed_tests = summary.get("passed", 0)
                failed_tests = summary.get("failed", 0) + summary.get("error", 0)
                total_tests = summary.get("total", 0)
                
                # Check for syntax/import errors
                tests_passed = (failed_tests == 0 and passed_tests > 0)
                
                # Extract error tracebacks if any failed
                if not tests_passed:
                    errors = []
                    for t in report_data.get("tests", []):
                        if t.get("outcome") != "passed":
                            call = t.get("call", {})
                            traceback = call.get("crash", {}).get("message", "Test failed")
                            errors.append(f"{t.get('nodeid')}: {traceback}")
                    error_details = "\n".join(errors) if errors else "Tests failed but no crash details found."
            except Exception as e:
                compilation_success = False
                error_details = f"Failed to parse report.json: {str(e)}\nSubprocess output:\n{res.stdout}\n{res.stderr}"
        else:
            # If report.json wasn't created, there was likely a compilation/syntax error
            compilation_success = False
            tests_passed = False
            error_details = f"Pytest did not generate report.json. SyntaxError or ModuleNotFoundError is highly likely.\nStdout:\n{res.stdout}\nStderr:\n{res.stderr}"

    except subprocess.TimeoutExpired:
        compilation_success = True
        tests_passed = False
        error_details = "Execution timed out (5 seconds limit exceeded). Possible infinite loop in generated code."
    except Exception as e:
        compilation_success = False
        tests_passed = False
        error_details = f"Internal runner error: {str(e)}"

    return {
        "compilation_success": compilation_success,
        "tests_passed": tests_passed,
        "total_tests": total_tests,
        "passed_tests": passed_tests,
        "failed_tests": failed_tests,
        "error_details": error_details,
    }


def run_docker_pytest(temp_dir_path: Path) -> dict:
    """Executes pytest inside a secure, lightweight Docker container."""
    import docker
    from docker.errors import DockerException

    report_json_path = temp_dir_path / "report.json"
    
    # We must absolute resolve paths to mount them in Docker
    abs_temp_dir = temp_dir_path.resolve()
    
    compilation_success = True
    tests_passed = False
    total_tests = 0
    passed_tests = 0
    failed_tests = 0
    error_details = None

    client = None
    container = None
    try:
        client = docker.from_env()
        # Use python:3.12-slim as a safe sandbox
        image_name = "python:3.12-slim"
        
        # Verify if image exists locally, otherwise pull it
        try:
            client.images.get(image_name)
        except docker.errors.ImageNotFound:
            logger.info(f"Pulling Docker image {image_name}...")
            client.images.pull(image_name)

        # Run container mounting the temp dir to /workspace
        # We install pytest and pytest-json-report on the fly or pre-install
        # To avoid internet dependency, we check if pytest is installed, otherwise pip install it
        container_cmd = (
            "sh -c 'pip install pytest pytest-json-report --quiet && "
            "pytest /workspace/tests/test_code.py --json-report "
            "--json-report-file=/workspace/report.json --tb=short'"
        )

        container = client.containers.run(
            image=image_name,
            command=container_cmd,
            volumes={
                str(abs_temp_dir): {
                    "bind": "/workspace",
                    "mode": "rw"
                }
            },
            working_dir="/workspace",
            detach=True,
            network_mode="bridge",  # allow pip install
            user="root"
        )

        # Wait with timeout of 10 seconds (gives time for pip install)
        result = container.wait(timeout=15)
        
        if report_json_path.exists():
            with open(report_json_path, "r", encoding="utf-8") as f:
                report_data = json.load(f)
            
            summary = report_data.get("summary", {})
            passed_tests = summary.get("passed", 0)
            failed_tests = summary.get("failed", 0) + summary.get("error", 0)
            total_tests = summary.get("total", 0)
            tests_passed = (failed_tests == 0 and passed_tests > 0)
            
            if not tests_passed:
                errors = []
                for t in report_data.get("tests", []):
                    if t.get("outcome") != "passed":
                        call = t.get("call", {})
                        traceback = call.get("crash", {}).get("message", "Test failed")
                        errors.append(f"{t.get('nodeid')}: {traceback}")
                error_details = "\n".join(errors) if errors else "Tests failed in Docker."
        else:
            compilation_success = False
            logs = container.logs().decode("utf-8")
            error_details = f"Pytest did not generate report.json in Docker. Logs:\n{logs}"

    except DockerException as de:
        logger.warning(f"Docker sandbox failed: {str(de)}. Falling back to local run.")
        return run_local_pytest(temp_dir_path)
    except Exception as e:
        compilation_success = False
        error_details = f"Docker execution failed/timed out: {str(e)}"
    finally:
        # Cleanup container
        if container:
            try:
                container.remove(force=True)
            except Exception:
                pass
        if client:
            try:
                client.close()
            except Exception:
                pass

    return {
        "compilation_success": compilation_success,
        "tests_passed": tests_passed,
        "total_tests": total_tests,
        "passed_tests": passed_tests,
        "failed_tests": failed_tests,
        "error_details": error_details,
    }


def evaluate_code(code_content: str, test_suite: str, use_docker: bool = False) -> dict:
    """Orchestrates writing generated code and test suite to a temp directory

    and evaluating it using either Docker or local pytest runner.
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # 1. Setup python package scaffolding required for pytest collection
        app_dir = temp_path / "app"
        tests_dir = temp_path / "tests"
        
        app_dir.mkdir(parents=True, exist_ok=True)
        tests_dir.mkdir(parents=True, exist_ok=True)
        
        # Create empty __init__.py files
        (app_dir / "__init__.py").write_text("", encoding="utf-8")
        (tests_dir / "__init__.py").write_text("", encoding="utf-8")
        (temp_path / "conftest.py").write_text("", encoding="utf-8")
        
        # Write code to app/main.py
        # To make sure imports work correctly in test_code.py (e.g. from app.main import function_name)
        # We append a simple __all__ or define it inside app/main.py
        (app_dir / "main.py").write_text(code_content, encoding="utf-8")
        
        # Write test suite to tests/test_code.py
        # Add dynamic import from app.main in the beginning of tests/test_code.py
        # If the test_suite does not contain import of the function, we inject it.
        # Standard format of tests: we assume function is in scope, so we import everything from app.main
        import_header = "from app.main import *\n\n"
        full_test_code = import_header + test_suite
        (tests_dir / "test_code.py").write_text(full_test_code, encoding="utf-8")
        
        # 2. Execute tests
        if use_docker:
            return run_docker_pytest(temp_path)
        else:
            return run_local_pytest(temp_path)


if __name__ == "__main__":
    # Quick self-test
    sample_code = "def is_palindrome(text: str) -> bool:\n    return text == text[::-1]\n"
    sample_test = "def test_palindrome():\n    assert is_palindrome('aba') == True\n    assert is_palindrome('abc') == False\n"
    
    print("Testing local execution...")
    result = evaluate_code(sample_code, sample_test, use_docker=False)
    print(json.dumps(result, indent=2))
