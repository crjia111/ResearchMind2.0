"""Versioned JSON contracts shared by every execution entry point."""

SCHEMA_VERSION = "1.0"


class CapabilityError(Exception):
    def __init__(self, code, message, retryable=False):
        super().__init__(message)
        self.code, self.retryable = code, retryable


def result(
    operation,
    request_id,
    status="completed",
    data=None,
    artifacts=None,
    error=None,
    warnings=None,
    usage=None,
    **extra,
):
    return dict(
        schema_version=SCHEMA_VERSION,
        operation=operation,
        request_id=request_id,
        status=status,
        summary=(error or {}).get("message", status),
        data=data if data is not None else {},
        artifacts=artifacts or [],
        warnings=warnings or [],
        error=error,
        usage=usage or {"successful_units": 0, "real_compute_units": 0},
        **extra,
    )


def failure(operation, request_id, error):
    return result(
        operation,
        request_id,
        "failed",
        error={"code": error.code, "message": str(error), "retryable": error.retryable},
    )


def validate(schema, value, path="input"):
    expected = schema.get("type")
    valid = {
        "object": lambda v: isinstance(v, dict),
        "array": lambda v: isinstance(v, list),
        "string": lambda v: isinstance(v, str),
        "integer": lambda v: type(v) is int,
        "number": lambda v: type(v) in (int, float),
        "boolean": lambda v: type(v) is bool,
        "null": lambda v: v is None,
    }
    if expected and not valid[expected](value):
        raise CapabilityError("INVALID_ARGUMENT", f"{path} must be {expected}")
    if "enum" in schema and value not in schema["enum"]:
        raise CapabilityError(
            "INVALID_ARGUMENT", f"{path} must be one of {schema['enum']}"
        )
    if expected == "object":
        properties = schema.get("properties", {})
        missing = set(schema.get("required", [])) - value.keys()
        unknown = (
            value.keys() - properties.keys()
            if schema.get("additionalProperties") is False
            else set()
        )
        if missing or unknown:
            raise CapabilityError(
                "INVALID_ARGUMENT",
                f"{path}: missing {sorted(missing)}, unknown {sorted(unknown)}",
            )
        for key, item in value.items():
            if key in properties:
                validate(properties[key], item, f"{path}.{key}")
    elif expected == "array":
        if len(value) < schema.get("minItems", 0) or len(value) > schema.get(
            "maxItems", 10000
        ):
            raise CapabilityError("INVALID_ARGUMENT", f"{path}: invalid item count")
        for item in value:
            validate(schema.get("items", {}), item, path + "[]")
    elif expected == "string" and len(value) < schema.get("minLength", 0):
        raise CapabilityError("INVALID_ARGUMENT", f"{path} cannot be empty")
    elif expected in ("integer", "number"):
        import math

        if (
            not math.isfinite(value)
            or value < schema.get("minimum", float("-inf"))
            or value > schema.get("maximum", float("inf"))
        ):
            raise CapabilityError("INVALID_ARGUMENT", f"{path} outside allowed range")
