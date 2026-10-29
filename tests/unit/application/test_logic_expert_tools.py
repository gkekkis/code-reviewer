from src.application.agents.logic_expert.tools import get_changed_function

DIFF = (
    "diff --git a/app/services/fx.py b/app/services/fx.py\n"
    "--- a/app/services/fx.py\n"
    "+++ b/app/services/fx.py\n"
    "@@ -1,9 +1,10 @@\n"
    " def convert(amount, rate):\n"
    "-    return amount * rate\n"
    "+    if rate <= 0:\n"
    '+        raise ValueError("rate must be positive")\n'
    "+\n"
    "+    return amount * rate\n"
    " \n"
    " \n"
    " class Converter:\n"
    "     def apply(self, amount):\n"
    "+        return convert(amount, self.rate)\n"
    " \n"
    "     def reset(self):\n"
    "         self.rate = 1\n"
    "diff --git a/app/other.py b/app/other.py\n"
    "--- a/app/other.py\n"
    "+++ b/app/other.py\n"
    "@@ -1,1 +1,2 @@\n"
    "+def only_here():\n"
    "+    return 1\n"
)


def test_get_changed_function_returns_the_new_version():
    function = get_changed_function(file_path="app/services/fx.py", function_name="convert", diff=DIFF)

    assert function == (
        "def convert(amount, rate):\n"
        "    if rate <= 0:\n"
        '        raise ValueError("rate must be positive")\n'
        "\n"
        "    return amount * rate\n"
        "\n"
    )


def test_get_changed_function_stops_at_the_next_definition():
    function = get_changed_function(file_path="app/services/fx.py", function_name="apply", diff=DIFF)

    assert function == "    def apply(self, amount):\n        return convert(amount, self.rate)\n"


def test_get_changed_function_only_looks_at_the_requested_file():
    result = get_changed_function(file_path="app/services/fx.py", function_name="only_here", diff=DIFF)

    assert result == "Function 'only_here' not found in the changed lines of app/services/fx.py"


def test_get_changed_function_not_found():
    result = get_changed_function(file_path="app/services/fx.py", function_name="missing", diff=DIFF)

    assert result == "Function 'missing' not found in the changed lines of app/services/fx.py"
