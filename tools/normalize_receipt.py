#!/usr/bin/env python3
"""Normalize a raw YAML note into an Information Compost Receipt.

This tool is intentionally conservative. It normalizes structure, timestamps,
IDs, and defaults, but it does not invent interpretations or life advice.
Existing facts, inferences, unknowns, and reflections are preserved when they
are supplied explicitly.

Examples:
    python tools/normalize_receipt.py raw.yaml -o receipt.yaml \
        --default-offset +09:00

    python tools/normalize_receipt.py \
        examples/daily_life/sample_receipt.yaml --check

Dependencies:
    pip install pyyaml jsonschema
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
import sys
from dataclasses import dataclass
from datetime import date, datetime, time, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any, Mapping, MutableMapping, Sequence

try:
    import yaml
except ImportError as exc:  # pragma: no cover - environment-dependent
    raise SystemExit(
        "PyYAML is required. Install it with: pip install pyyaml"
    ) from exc


VERSION = "0.1.0"
DEFAULT_SCHEMA = Path(__file__).resolve().parents[1] / "schemas" / "receipt.schema.yaml"


class NormalizationError(ValueError):
    """Raised when a raw Receipt cannot be normalized safely."""


@dataclass(frozen=True)
class SchemaEnums:
    """Allowed values pulled from the Receipt schema.

    The schema is the single source of truth for these vocabularies. The
    normalizer never hardcodes them, so schema and code cannot silently
    drift apart from one another.
    """

    source_mode: frozenset[str]
    trace_type: frozenset[str]
    trace_confidence: frozenset[str]
    normalization_status: frozenset[str]
    inferred_confidence: frozenset[str]
    pause_status: frozenset[str]
    pause_method: frozenset[str]
    reflection_status: frozenset[str]
    reflection_confidence: frozenset[str]
    output_type: frozenset[str]


def _walk(node: Any, path: Sequence[str]) -> Any:
    for key in path:
        if not isinstance(node, Mapping) or key not in node:
            raise NormalizationError(
                "Schema is missing expected path "
                f"'{'/'.join(path)}'; the normalizer and the Receipt schema "
                "have drifted apart."
            )
        node = node[key]
    return node


def _enum(schema: Mapping[str, Any], *path: str) -> frozenset[str]:
    values = _walk(schema, path)
    if not isinstance(values, Sequence) or isinstance(values, (str, bytes, bytearray)):
        raise NormalizationError(f"Schema path '{'/'.join(path)}' is not an enum list.")
    return frozenset(value for value in values if isinstance(value, str))


@lru_cache(maxsize=8)
def _load_schema_enums(schema_path: Path) -> SchemaEnums:
    """Load the vocabularies the normalizer needs to validate against.

    This only parses YAML; it does not require the optional jsonschema
    dependency, so the enums stay authoritative even when full schema
    validation is skipped with --no-validate.
    """
    if not schema_path.exists():
        raise NormalizationError(f"Schema not found: {schema_path}")
    schema = yaml.safe_load(schema_path.read_text(encoding="utf-8"))
    receipt = ("properties", "receipt", "properties")

    return SchemaEnums(
        source_mode=_enum(schema, *receipt, "source", "properties", "mode", "enum"),
        trace_type=_enum(schema, *receipt, "traces", "items", "properties", "type", "enum"),
        trace_confidence=_enum(
            schema, *receipt, "traces", "items", "properties", "confidence", "enum"
        ),
        normalization_status=_enum(
            schema, *receipt, "normalization", "properties", "status", "enum"
        ),
        inferred_confidence=_enum(
            schema,
            *receipt,
            "normalization",
            "properties",
            "inferred",
            "items",
            "properties",
            "confidence",
            "enum",
        ),
        pause_status=_enum(schema, *receipt, "pause", "properties", "status", "enum"),
        pause_method=_enum(schema, *receipt, "pause", "properties", "method", "enum"),
        reflection_status=_enum(schema, *receipt, "reflection", "properties", "status", "enum"),
        reflection_confidence=_enum(
            schema, *receipt, "reflection", "properties", "confidence", "enum"
        ),
        output_type=_enum(schema, *receipt, "outputs", "items", "properties", "type", "enum"),
    )


def _plain(value: Any) -> Any:
    """Convert YAML date objects and nested containers to JSON-safe values."""
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Mapping):
        return {str(key): _plain(item) for key, item in value.items()}
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [_plain(item) for item in value]
    return value


def _parse_offset(raw: str | None) -> timezone | None:
    if raw is None:
        return None
    if raw.upper() == "Z":
        return timezone.utc

    match = re.fullmatch(r"([+-])(\d{2}):(\d{2})", raw)
    if not match:
        raise NormalizationError(
            f"Invalid UTC offset {raw!r}; use a value such as +09:00 or Z."
        )

    sign = 1 if match.group(1) == "+" else -1
    hours = int(match.group(2))
    minutes = int(match.group(3))
    if hours > 23 or minutes > 59:
        raise NormalizationError(f"Invalid UTC offset {raw!r}.")

    from datetime import timedelta

    return timezone(sign * timedelta(hours=hours, minutes=minutes))


def _normalize_datetime(
    value: Any,
    *,
    field_name: str,
    default_tz: timezone | None,
) -> str:
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, date):
        parsed = datetime.combine(value, time.min)
    elif isinstance(value, str):
        text = value.strip()
        if not text:
            raise NormalizationError(f"{field_name} must not be empty.")
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        try:
            parsed = datetime.fromisoformat(text)
        except ValueError as exc:
            raise NormalizationError(
                f"{field_name} must be an ISO 8601 date-time; received {value!r}."
            ) from exc
    else:
        raise NormalizationError(
            f"{field_name} must be an ISO 8601 date-time; received {type(value).__name__}."
        )

    if parsed.tzinfo is None:
        if default_tz is None:
            raise NormalizationError(
                f"{field_name} has no UTC offset. Add one to the value or pass "
                "--default-offset, for example --default-offset +09:00."
            )
        parsed = parsed.replace(tzinfo=default_tz)

    return parsed.isoformat(timespec="seconds")


def _generated_id(payload: Mapping[str, Any], occurred_at: str) -> str:
    canonical = json.dumps(_plain(payload), sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:10]
    day = occurred_at[:10]
    return f"receipt-{day}-{digest}"


def _normalize_source(value: Any, enums: SchemaEnums) -> dict[str, Any]:
    if value is None:
        return {"mode": "manual", "refs": []}
    if isinstance(value, str):
        return {"mode": "manual", "refs": [value]}
    if not isinstance(value, Mapping):
        raise NormalizationError("source must be a mapping, string, or null.")

    mode = str(value.get("mode", "manual"))
    if mode not in enums.source_mode:
        raise NormalizationError(f"Unsupported source.mode: {mode!r}.")

    refs_raw = value.get("refs", [])
    if refs_raw is None:
        refs: list[str] = []
    elif isinstance(refs_raw, str):
        refs = [refs_raw]
    elif isinstance(refs_raw, Sequence):
        refs = list(dict.fromkeys(str(item) for item in refs_raw if str(item).strip()))
    else:
        raise NormalizationError("source.refs must be a string, list, or null.")

    return {"mode": mode, "refs": refs}


def _normalize_action(value: Any) -> dict[str, Any]:
    if isinstance(value, str):
        summary = value.strip()
        data: Mapping[str, Any] = {}
    elif isinstance(value, Mapping):
        data = value
        summary = str(data.get("summary", "")).strip()
    else:
        raise NormalizationError("action must be a string or mapping.")

    if not summary:
        raise NormalizationError("action.summary is required.")

    intentional = data.get("intentional")
    if intentional is not None and not isinstance(intentional, bool):
        raise NormalizationError("action.intentional must be true, false, or null.")

    return {
        "summary": summary,
        "category": data.get("category"),
        "intentional": intentional,
        "outcome": data.get("outcome"),
    }


def _guess_trace_type(value: Any) -> str:
    if isinstance(value, str):
        return "note"
    if isinstance(value, Mapping):
        return "other"
    return "other"


def _normalize_trace(
    value: Any,
    *,
    index: int,
    default_tz: timezone | None,
    enums: SchemaEnums,
) -> dict[str, Any]:
    if isinstance(value, Mapping) and ("type" in value or "value" in value):
        trace_type = str(value.get("type", _guess_trace_type(value.get("value"))))
        trace_value = value.get("value")
        observed_at = value.get("observed_at")
        provenance = value.get("provenance")
        confidence = value.get("confidence", "unknown")
    else:
        trace_type = _guess_trace_type(value)
        trace_value = value
        observed_at = None
        provenance = None
        confidence = "unknown"

    if trace_type not in enums.trace_type:
        raise NormalizationError(
            f"traces[{index}].type must be one of {sorted(enums.trace_type)}; "
            f"received {trace_type!r}."
        )
    if trace_value is None:
        raise NormalizationError(f"traces[{index}].value is required.")
    if confidence is not None and confidence not in enums.trace_confidence:
        raise NormalizationError(
            f"traces[{index}].confidence must be one of "
            f"{sorted(enums.trace_confidence)} or null."
        )

    normalized_observed_at = None
    if observed_at is not None:
        normalized_observed_at = _normalize_datetime(
            observed_at,
            field_name=f"traces[{index}].observed_at",
            default_tz=default_tz,
        )

    return {
        "type": trace_type,
        "value": _plain(trace_value),
        "observed_at": normalized_observed_at,
        "provenance": None if provenance is None else str(provenance),
        "confidence": confidence,
    }


def _normalize_traces(
    value: Any, default_tz: timezone | None, enums: SchemaEnums
) -> list[dict[str, Any]]:
    if value is None:
        raise NormalizationError("traces is required and must contain at least one trace.")
    if isinstance(value, (str, bytes, bytearray, Mapping)):
        values = [value]
    elif isinstance(value, Sequence):
        values = list(value)
    else:
        values = [value]

    if not values:
        raise NormalizationError("traces must contain at least one trace.")

    return [
        _normalize_trace(item, index=index, default_tz=default_tz, enums=enums)
        for index, item in enumerate(values)
    ]


def _string_list(value: Any, field_name: str) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        value = [value]
    if not isinstance(value, Sequence) or isinstance(value, (bytes, bytearray)):
        raise NormalizationError(f"{field_name} must be a string, list, or null.")
    return [str(item).strip() for item in value if str(item).strip()]


def _normalize_context(value: Any) -> dict[str, Any]:
    """Preserve context mappings without silently coercing invalid values."""
    if value is None:
        return {}
    if not isinstance(value, Mapping):
        raise NormalizationError("context must be a mapping or null.")
    return _plain(value)


def _normalize_inferred(value: Any, enums: SchemaEnums) -> list[dict[str, Any]]:
    if value is None:
        return []
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        raise NormalizationError("normalization.inferred must be a list.")

    result: list[dict[str, Any]] = []
    for index, item in enumerate(value):
        if isinstance(item, str):
            statement = item.strip()
            confidence = "low"
            basis = None
        elif isinstance(item, Mapping):
            statement = str(item.get("statement", "")).strip()
            confidence = str(item.get("confidence", "low"))
            basis = item.get("basis")
        else:
            raise NormalizationError(f"normalization.inferred[{index}] must be a string or mapping.")

        if not statement:
            raise NormalizationError(f"normalization.inferred[{index}].statement is required.")
        if confidence not in enums.inferred_confidence:
            raise NormalizationError(
                f"normalization.inferred[{index}].confidence must be one of "
                f"{sorted(enums.inferred_confidence)}."
            )
        result.append(
            {
                "statement": statement,
                "confidence": confidence,
                "basis": None if basis is None else str(basis),
            }
        )
    return result


def _normalize_normalization(value: Any, enums: SchemaEnums) -> dict[str, Any]:
    if value is None:
        return {"status": "raw", "facts": [], "inferred": [], "unknowns": []}
    if not isinstance(value, Mapping):
        raise NormalizationError("normalization must be a mapping or null.")

    status = str(value.get("status", "raw"))
    if status not in enums.normalization_status:
        raise NormalizationError(f"Unsupported normalization.status: {status!r}.")

    return {
        "status": status,
        "facts": _string_list(value.get("facts"), "normalization.facts"),
        "inferred": _normalize_inferred(value.get("inferred"), enums),
        "unknowns": _string_list(value.get("unknowns"), "normalization.unknowns"),
    }


def _normalize_pause(
    value: Any, default_tz: timezone | None, enums: SchemaEnums
) -> dict[str, Any]:
    if value is None:
        return {
            "status": "not_started",
            "method": None,
            "duration_minutes": None,
            "revisited_at": None,
        }
    if not isinstance(value, Mapping):
        raise NormalizationError("pause must be a mapping or null.")

    status = str(value.get("status", "not_started"))
    if status not in enums.pause_status:
        raise NormalizationError(
            f"pause.status must be one of {sorted(enums.pause_status)}; received {status!r}."
        )

    method = value.get("method")
    if method is not None and method not in enums.pause_method:
        raise NormalizationError(
            f"pause.method must be one of {sorted(enums.pause_method)} or null; "
            f"received {method!r}."
        )

    revisited_at = value.get("revisited_at")
    if revisited_at is not None:
        revisited_at = _normalize_datetime(
            revisited_at,
            field_name="pause.revisited_at",
            default_tz=default_tz,
        )

    return {
        "status": status,
        "method": method,
        "duration_minutes": value.get("duration_minutes"),
        "revisited_at": revisited_at,
    }


def _normalize_reflection(value: Any, enums: SchemaEnums) -> dict[str, Any]:
    if value is None:
        data: Mapping[str, Any] = {}
    elif isinstance(value, str):
        data = {"status": "drafted", "observation": value}
    elif isinstance(value, Mapping):
        data = value
    else:
        raise NormalizationError("reflection must be a string, mapping, or null.")

    status = str(data.get("status", "pending"))
    if status not in enums.reflection_status:
        raise NormalizationError(
            f"reflection.status must be one of {sorted(enums.reflection_status)}; "
            f"received {status!r}."
        )

    confidence = data.get("confidence", "insufficient_context")
    if confidence is not None and confidence not in enums.reflection_confidence:
        raise NormalizationError(
            f"reflection.confidence must be one of {sorted(enums.reflection_confidence)} "
            "or null."
        )

    # The normalizer enforces the protocol boundary even when the input says otherwise.
    return {
        "status": status,
        "observation": data.get("observation"),
        "repeated_pattern": data.get("repeated_pattern"),
        "new_question": data.get("new_question"),
        "next_experiment": data.get("next_experiment"),
        "non_prescriptive": True,
        "confidence": confidence,
    }


def _normalize_outputs(
    value: Any, default_tz: timezone | None, enums: SchemaEnums
) -> list[dict[str, Any]]:
    if value is None:
        return []
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        raise NormalizationError("outputs must be a list or null.")

    outputs: list[dict[str, Any]] = []
    for index, item in enumerate(value):
        if not isinstance(item, Mapping):
            raise NormalizationError(f"outputs[{index}] must be a mapping.")

        output_type = item.get("type")
        if output_type not in enums.output_type:
            raise NormalizationError(
                f"outputs[{index}].type must be one of {sorted(enums.output_type)}; "
                f"received {output_type!r}."
            )

        generated_at = item.get("generated_at")
        if generated_at is not None:
            generated_at = _normalize_datetime(
                generated_at,
                field_name=f"outputs[{index}].generated_at",
                default_tz=default_tz,
            )
        outputs.append(
            {
                "type": output_type,
                "path": item.get("path"),
                "generated_at": generated_at,
            }
        )
    return outputs


def normalize_receipt(
    raw_document: Mapping[str, Any],
    *,
    recorded_at: str | None = None,
    default_offset: str | None = None,
    schema_path: Path = DEFAULT_SCHEMA,
) -> dict[str, Any]:
    """Return one canonical Receipt document without adding interpretations."""
    if not isinstance(raw_document, Mapping):
        raise NormalizationError("The YAML root must be a mapping.")

    source_payload = raw_document.get("receipt", raw_document)
    if not isinstance(source_payload, Mapping):
        raise NormalizationError("receipt must be a mapping.")

    payload: MutableMapping[str, Any] = copy.deepcopy(dict(source_payload))
    default_tz = _parse_offset(default_offset)
    enums = _load_schema_enums(schema_path.resolve())

    # Small aliases make handwritten notes convenient without guessing at meaning.
    if "action" not in payload and "summary" in payload:
        payload["action"] = payload.pop("summary")
    if "traces" not in payload and "notes" in payload:
        payload["traces"] = payload.pop("notes")

    allowed_keys = {
        "id",
        "version",
        "occurred_at",
        "recorded_at",
        "source",
        "action",
        "traces",
        "context",
        "normalization",
        "pause",
        "reflection",
        "outputs",
    }
    unknown_keys = sorted(set(payload) - allowed_keys)
    if unknown_keys:
        joined = ", ".join(unknown_keys)
        raise NormalizationError(
            f"Unknown Receipt field(s): {joined}. Move raw evidence into traces "
            "and situational data into context; the normalizer will not discard data silently."
        )

    if "occurred_at" not in payload:
        raise NormalizationError("occurred_at is required.")
    occurred_at = _normalize_datetime(
        payload["occurred_at"],
        field_name="occurred_at",
        default_tz=default_tz,
    )

    raw_recorded_at = recorded_at or payload.get("recorded_at")
    if raw_recorded_at is None:
        raw_recorded_at = datetime.now(timezone.utc)
    normalized_recorded_at = _normalize_datetime(
        raw_recorded_at,
        field_name="recorded_at",
        default_tz=default_tz,
    )

    receipt_id = str(payload.get("id") or _generated_id(payload, occurred_at))

    normalized = {
        "receipt": {
            "id": receipt_id,
            "version": VERSION,
            "occurred_at": occurred_at,
            "recorded_at": normalized_recorded_at,
            "source": _normalize_source(payload.get("source"), enums),
            "action": _normalize_action(payload.get("action")),
            "traces": _normalize_traces(payload.get("traces"), default_tz, enums),
            "context": _normalize_context(payload.get("context")),
            "normalization": _normalize_normalization(payload.get("normalization"), enums),
            "pause": _normalize_pause(payload.get("pause"), default_tz, enums),
            "reflection": _normalize_reflection(payload.get("reflection"), enums),
            "outputs": _normalize_outputs(payload.get("outputs"), default_tz, enums),
        }
    }
    return normalized


def validate_document(document: Mapping[str, Any], schema_path: Path) -> None:
    """Validate a normalized Receipt against the repository schema."""
    try:
        from jsonschema import Draft202012Validator, FormatChecker
    except ImportError as exc:  # pragma: no cover - environment-dependent
        raise NormalizationError(
            "jsonschema is required for validation. Install it with: pip install jsonschema"
        ) from exc

    if not schema_path.exists():
        raise NormalizationError(f"Schema not found: {schema_path}")

    schema = yaml.safe_load(schema_path.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    errors = sorted(validator.iter_errors(document), key=lambda error: list(error.path))
    if not errors:
        return

    messages: list[str] = []
    for error in errors:
        location = ".".join(str(part) for part in error.absolute_path) or "<root>"
        messages.append(f"{location}: {error.message}")
    raise NormalizationError("Schema validation failed:\n  - " + "\n  - ".join(messages))


def _dump_yaml(document: Mapping[str, Any]) -> str:
    return yaml.safe_dump(
        document,
        allow_unicode=True,
        sort_keys=False,
        default_flow_style=False,
        width=100,
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Normalize a raw YAML note into the Information Compost Receipt schema "
            "without inventing interpretations."
        )
    )
    parser.add_argument("input", type=Path, help="Input YAML file.")
    parser.add_argument("-o", "--output", type=Path, help="Write normalized YAML to this path.")
    parser.add_argument(
        "--in-place",
        action="store_true",
        help="Replace the input file atomically after successful validation.",
    )
    parser.add_argument(
        "--schema",
        type=Path,
        default=DEFAULT_SCHEMA,
        help=f"Receipt schema path (default: {DEFAULT_SCHEMA}).",
    )
    parser.add_argument(
        "--default-offset",
        help="Attach this UTC offset to naive timestamps, for example +09:00 or Z.",
    )
    parser.add_argument(
        "--recorded-at",
        help="Override recorded_at with an ISO 8601 date-time.",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Validate only; do not emit normalized YAML.",
    )
    parser.add_argument(
        "--no-validate",
        action="store_true",
        help="Skip JSON Schema validation (not recommended).",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.in_place and args.output:
        parser.error("--in-place and --output cannot be used together.")

    try:
        if not args.input.exists():
            raise NormalizationError(f"Input file not found: {args.input}")
        raw = yaml.safe_load(args.input.read_text(encoding="utf-8"))

        if args.check:
            validate_document(_plain(raw), args.schema)
            print(f"OK: {args.input}", file=sys.stderr)
            return 0

        document = normalize_receipt(
            raw,
            recorded_at=args.recorded_at,
            default_offset=args.default_offset,
            schema_path=args.schema,
        )
        if not args.no_validate:
            validate_document(document, args.schema)

        rendered = _dump_yaml(document)
        if args.in_place:
            temporary = args.input.with_suffix(args.input.suffix + ".tmp")
            temporary.write_text(rendered, encoding="utf-8")
            temporary.replace(args.input)
        elif args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(rendered, encoding="utf-8")
        else:
            sys.stdout.write(rendered)
        return 0

    except (NormalizationError, OSError, yaml.YAMLError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
