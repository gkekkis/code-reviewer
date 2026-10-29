"""Tools of the Logic Expert, as the model sees them."""

from pydantic import BaseModel, Field

from src.application.ports.models import ToolDescription


class GetChangedFunctionArgs(BaseModel):
    """Arguments the model chooses for get_changed_function."""

    file_path: str = Field(description="Path of a file changed in the diff, e.g. app/services/fx.py")
    function_name: str = Field(description="Name of a function in that file, without parentheses, e.g. convert")


GET_CHANGED_FUNCTION = ToolDescription(
    name="get_changed_function",
    description="Return the new version of a function from a file changed in the diff, to check its logic in full.",
    arguments=GetChangedFunctionArgs,
)


def get_changed_function(file_path: str, function_name: str, diff: str) -> str:
    """Return the new version of a function from a file changed in the diff, to check its logic in full."""
    new_lines = []
    current_file = None
    for line in diff.splitlines():
        if line.startswith("+++ "):
            current_file = line[6:].strip() if line.startswith("+++ b/") else None
            continue
        if current_file != file_path or line.startswith(("---", "@@", "diff --git", "index ", "new file")):
            continue
        if line.startswith("-"):
            continue  # removed lines are not part of the new version
        new_lines.append(line[1:])

    for start, line in enumerate(new_lines):
        if line.lstrip().startswith(f"def {function_name}("):
            indent = len(line) - len(line.lstrip())
            body = [line]
            for following in new_lines[start + 1 :]:
                if following.strip() and len(following) - len(following.lstrip()) <= indent:
                    break
                body.append(following)
            return "\n".join(body)

    return f"Function {function_name!r} not found in the changed lines of {file_path}"
