# coding=utf-8
"""AST allow-list for user-supplied map-algebra expressions.

Raster Calculator and vt7/utils evaluate the expression the user types (``map1[1] * 2``) with
``eval``. ``eval`` runs *any* Python, not just arithmetic, and these expressions are not confined to
the keyboard: the GUI saves and loads argument JSONs (``save_arguments`` / ``load_arguments``) and
json_to_python turns them into code, so an expression can arrive in a file someone else wrote.
Opening a colleague's configuration would run whatever it contained, with the user's permissions.

The one thing that looked like a filter -- ``expression.replace(" ", "")`` in
_convert_expression_to_numpy -- is not one. It normalises the formula; it only breaks payloads that
happen to need spaces. Verified: ``(__import__('pathlib').Path(r'...').write_text('x'),map1[1])[1]``
has no spaces, passed validation, and wrote the file. It ran inside
``_validate_expression_with_dummy`` -- at validation time, before anyone pressed Run.

So instead of blocking known-bad patterns (a losing game), this parses the converted expression and
walks the AST, rejecting anything that is not on the allow-list below. `__builtins__`-stripping was
not enough on its own: ``().__class__.__mro__[1].__subclasses__()`` reaches back out, and it also
needs no spaces. Attribute access is the hinge -- it is allowed *only* as ``np.<known function>``,
which is what closes that door.

Used by raster_calculator (validation + execution) and vt7/utils.
"""

import ast

# Names the converted expression may reference. `array` is the raster data injected by the caller,
# `np` is numpy, `no_data` is the sentinel the conversion step leaves behind.
_ALLOWED_NAMES = frozenset({"array", "np", "no_data"})

# numpy attributes reachable as np.<attr>. This is _NUMPY_FUNCTIONS' values (what the conversion
# step can emit) plus the few the conversion adds directly (isnan, nan, isinf).
_ALLOWED_NP_ATTRS = frozenset({
    "where", "log1p", "log", "log10", "cbrt", "sqrt", "square", "minimum", "maximum",
    "sin", "cos", "tan", "arcsin", "arccos", "arctan", "abs", "ceil", "floor",
    "isnan", "isinf", "nan", "power", "exp",
})

_ALLOWED_NODES = (
    ast.Expression, ast.Constant, ast.Name, ast.Load,
    ast.BinOp, ast.UnaryOp, ast.Compare, ast.BoolOp, ast.Call, ast.Attribute,
    ast.Subscript, ast.Tuple, ast.List,
    # arithmetic / bitwise operators
    ast.Add, ast.Sub, ast.Mult, ast.Div, ast.FloorDiv, ast.Mod, ast.Pow,
    ast.BitAnd, ast.BitOr, ast.BitXor, ast.Invert, ast.USub, ast.UAdd,
    # comparisons and boolean joins
    ast.Eq, ast.NotEq, ast.Lt, ast.LtE, ast.Gt, ast.GtE, ast.And, ast.Or, ast.Not,
)

# Python < 3.9 wrapped subscripts in ast.Index; harmless to allow when present.
if hasattr(ast, "Index"):  # pragma: no cover - version dependent
    _ALLOWED_NODES = _ALLOWED_NODES + (ast.Index,)


class UnsafeExpressionError(ValueError):
    """Raised when an expression contains constructs outside the allow-list."""


def assert_expression_is_safe(converted_expr: str) -> None:
    """Raise UnsafeExpressionError unless every node of the expression is on the allow-list.

    Args:
        converted_expr: the expression AFTER _convert_expression_to_numpy, i.e. numpy syntax
            (``np.where(array[0][0]==1,1,0)``), not the user-facing form.

    Raises:
        UnsafeExpressionError: on any disallowed construct.
        SyntaxError: if the expression does not parse (callers already handle this).
    """
    tree = ast.parse(converted_expr, mode="eval")

    for node in ast.walk(tree):
        if not isinstance(node, _ALLOWED_NODES):
            raise UnsafeExpressionError(
                f"'{type(node).__name__}' is not allowed in an expression. Use map algebra only "
                f"(arithmetic, comparisons, and the documented functions)."
            )

        if isinstance(node, ast.Name) and node.id not in _ALLOWED_NAMES:
            raise UnsafeExpressionError(
                f"Unknown name '{node.id}' in expression. Only {sorted(_ALLOWED_NAMES)} and the "
                f"documented functions are available."
            )

        # The hinge: attributes exist only as np.<known function>. Without this, dunder chains
        # (().__class__...) walk straight out of the sandbox.
        if isinstance(node, ast.Attribute):
            if not (isinstance(node.value, ast.Name) and node.value.id == "np"):
                raise UnsafeExpressionError(
                    "Attribute access is only allowed on numpy functions in an expression."
                )
            if node.attr not in _ALLOWED_NP_ATTRS:
                raise UnsafeExpressionError(f"numpy function 'np.{node.attr}' is not allowed.")

        # Only np.<fn>(...) may be called -- never a bare name, a subscript, or a returned object.
        if isinstance(node, ast.Call) and not isinstance(node.func, ast.Attribute):
            raise UnsafeExpressionError(
                "Only the documented functions may be called in an expression."
            )

    return None


def safe_eval(converted_expr: str, array=None, np=None, no_data=None):
    """Validate `converted_expr` against the allow-list, then eval it with a bare namespace.

    Belt and braces: the AST check is what actually blocks escapes; the empty ``__builtins__`` means
    that even if something slipped past, there is no ``__import__``/``open``/``eval`` to reach.
    """
    assert_expression_is_safe(converted_expr)
    namespace = {"__builtins__": {}}
    if array is not None:
        namespace["array"] = array
    if np is not None:
        namespace["np"] = np
    if no_data is not None:
        namespace["no_data"] = no_data
    return eval(converted_expr, namespace)  # noqa: S307 - guarded by assert_expression_is_safe
