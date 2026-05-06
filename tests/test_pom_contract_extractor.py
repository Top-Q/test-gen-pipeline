"""Tests for the POM contract extractor."""

from pathlib import Path

from pipeline.pom_contract_extractor import extract_contracts


def test_extract_class_name(fixtures_dir: Path):
    """Extract the class name from a sample PO file."""
    sample = fixtures_dir / "sample_po.ts"
    contracts = extract_contracts([sample])

    assert len(contracts) == 1
    assert contracts[0].class_name == "ExamplePage"


def test_extract_extends(fixtures_dir: Path):
    """Extract the base class from a sample PO file."""
    sample = fixtures_dir / "sample_po.ts"
    contracts = extract_contracts([sample])

    assert contracts[0].extends == "BasePage<ExamplePage>"


def test_extract_async_methods(fixtures_dir: Path):
    """Extract async method signatures."""
    sample = fixtures_dir / "sample_po.ts"
    contracts = extract_contracts([sample])
    contract = contracts[0]

    action_methods = contract.action_methods
    method_names = [m.name for m in action_methods]

    assert "waitForLoad" in method_names
    assert "fillName" in method_names
    assert "clickCreate" in method_names


def test_extract_getter_locators(fixtures_dir: Path):
    """Extract getter-style locator methods."""
    sample = fixtures_dir / "sample_po.ts"
    contracts = extract_contracts([sample])
    contract = contracts[0]

    getters = contract.getter_locators
    getter_names = [m.name for m in getters]

    assert "getHeading" in getter_names
    assert "getCreateButton" in getter_names


def test_extract_method_returns(fixtures_dir: Path):
    """Verify return types are captured."""
    sample = fixtures_dir / "sample_po.ts"
    contracts = extract_contracts([sample])
    contract = contracts[0]

    fill_method = next(m for m in contract.methods if m.name == "fillName")
    assert "Promise<void>" in fill_method.returns

    click_method = next(m for m in contract.methods if m.name == "clickCreate")
    assert "Promise<ExamplePage>" in click_method.returns


def test_extract_nonexistent_file():
    """Non-existent files are silently skipped."""
    contracts = extract_contracts([Path("/nonexistent/file.ts")])
    assert contracts == []


def test_extract_non_ts_file(tmp_path: Path):
    """Non-TS files are skipped."""
    js_file = tmp_path / "file.js"
    js_file.write_text("export class Foo {}")
    contracts = extract_contracts([js_file])
    assert contracts == []
