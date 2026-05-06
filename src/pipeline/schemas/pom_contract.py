"""POM contract schema — lightweight TS class signature representation."""

from pydantic import BaseModel


class PomMethod(BaseModel):
    """A method signature extracted from a Page Object or Component."""

    name: str
    signature: str  # e.g. "(email: string, role: string)"
    returns: str  # e.g. "Promise<void>", "Locator"
    description: str = ""  # from JSDoc comment
    is_getter: bool = False  # True for getter-style locator methods


class PomContract(BaseModel):
    """Lightweight representation of a TS Page Object or Component class."""

    class_name: str  # e.g. "MembersPage"
    file_path: str  # relative to project root
    extends: str = ""  # e.g. "BasePage<MembersPage>"
    methods: list[PomMethod] = []

    @property
    def getter_locators(self) -> list[PomMethod]:
        """Methods that return Locator (getter-style)."""
        return [m for m in self.methods if m.is_getter]

    @property
    def action_methods(self) -> list[PomMethod]:
        """Methods that perform actions (non-getter)."""
        return [m for m in self.methods if not m.is_getter]
