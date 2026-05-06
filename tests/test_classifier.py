"""Tests for the failure classifier."""

from pipeline.classifier import FailureCategory, classify_failure


def test_timeout_classification():
    error = """Error: Timeout 30000ms exceeded.
    waiting for locator('.my-element')"""
    result = classify_failure(error)
    assert result.category == FailureCategory.TIMEOUT
    assert result.route_to == "healer"


def test_locator_not_found_classification():
    error = """Error: strict mode violation: locator('.button') resolved to 3 elements"""
    result = classify_failure(error)
    assert result.category == FailureCategory.LOCATOR_NOT_FOUND
    assert result.route_to == "healer"


def test_assertion_mismatch_classification():
    error = """Error: expect(received).toBe(expected)
    Expected: "Hello"
    Received: "World" """
    result = classify_failure(error)
    assert result.category == FailureCategory.ASSERTION_MISMATCH
    assert result.route_to == "healer"


def test_missing_method_classification():
    error = """TypeError: workPackagesPage.nonExistentMethod is not a function"""
    result = classify_failure(error)
    assert result.category == FailureCategory.MISSING_METHOD
    assert result.route_to == "pom_builder"


def test_import_error_classification():
    error = """Error: Cannot find module '../../../internals'
    at Object.<anonymous> (tests/ui/example/example.spec.ts:3:1)"""
    result = classify_failure(error)
    assert result.category == FailureCategory.IMPORT_ERROR
    assert result.route_to == "pom_builder"


def test_infrastructure_classification():
    error = """Error: net::ERR_CONNECTION_REFUSED at http://localhost:8090"""
    result = classify_failure(error)
    assert result.category == FailureCategory.INFRASTRUCTURE
    assert result.route_to == "abort"


def test_unknown_classification():
    error = """Some completely unexpected error without patterns"""
    result = classify_failure(error)
    assert result.category == FailureCategory.UNKNOWN
    assert result.route_to == "abort"


def test_file_path_extraction():
    error = """Error: Timeout 30000ms exceeded.
    at /home/user/project/src/po/openproject/members/membersPage.ts:42:15
    at /home/user/project/tests/ui/members/members.spec.ts:18:9"""
    result = classify_failure(error)
    assert len(result.file_paths) == 2
    assert any("membersPage.ts" in p for p in result.file_paths)
    assert any("members.spec.ts" in p for p in result.file_paths)


def test_windows_file_path_extraction():
    error = """Error: Cannot find module
    at C:\\Users\\user\\project\\src\\po\\openproject\\example\\examplePage.ts:10:5"""
    result = classify_failure(error)
    assert len(result.file_paths) >= 1
