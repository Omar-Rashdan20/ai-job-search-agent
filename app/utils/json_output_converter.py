import json
import re
import csv
from io import StringIO
from typing import Any

from crewai.utilities.converter import Converter, ConverterError
from json_repair import repair_json
from pydantic import BaseModel

# Fields that are serialised as semicolon-separated lists inside a TOON row.
_TOON_LIST_FIELDS: frozenset[str] = frozenset({
    "required_skills",
    "recommendation_notes",
    "skill_gap",
    "queries",
})


class JsonOutputConverter(Converter):
    """Convert messy LLM JSON text into the expected Pydantic model."""

    def to_pydantic(self, current_attempt: int = 1) -> BaseModel:
        try:
            parsed = self._parse_json_value(self.text)
            parsed = self._fit_to_model(parsed)
            return self.model.model_validate(parsed)
        except Exception as exc:
            try:
                return self.model.model_validate(self._empty_payload())
            except Exception as fallback_exc:
                raise ConverterError(
                    f"Failed to parse LLM output: {exc}. "
                    f"Empty-payload fallback also failed: {fallback_exc}"
                ) from fallback_exc

    def to_json(self, current_attempt: int = 1) -> dict:
        return self.to_pydantic(current_attempt).model_dump()

    def _fit_to_model(self, parsed: Any) -> Any:
        model_fields = getattr(self.model, "model_fields", {})

        if isinstance(parsed, str):
            try:
                parsed = json.loads(parsed)
            except json.JSONDecodeError:
                raise ValueError("Repaired output is plain text, not JSON")

        if isinstance(parsed, dict):
            if len(model_fields) == 1:
                field_name = next(iter(model_fields))
                if field_name not in parsed:
                    # Try to find a list value to wrap
                    list_value = next(
                        (v for v in parsed.values() if isinstance(v, list)), None
                    )
                    if list_value is not None:
                        return {field_name: list_value}
                    return {field_name: [parsed]}
            return parsed

        if isinstance(parsed, list) and len(model_fields) == 1:
            field_name = next(iter(model_fields))
            return {field_name: parsed}

        raise ValueError("Repaired output is incompatible with the expected schema")

    def _empty_payload(self) -> dict:
        model_fields = getattr(self.model, "model_fields", {})
        payload: dict = {}
        for field_name, field in model_fields.items():
            annotation = getattr(field, "annotation", None)
            if _is_list_annotation(annotation):
                payload[field_name] = []
            elif getattr(field, "default", None) is not None:
                continue
            else:
                payload[field_name] = None
        return payload

    @staticmethod
    def _parse_json_value(text: str) -> Any:
        cleaned = text.strip()

        fenced = re.search(r"```(?:json)?\s*(.*?)```", cleaned, re.DOTALL | re.IGNORECASE)
        if fenced:
            cleaned = fenced.group(1).strip()

        try:
            return json.loads(cleaned)
        except (TypeError, json.JSONDecodeError):
            pass

        for pattern in (r"(\{.*\})", r"(\[.*\])"):
            for match in re.findall(pattern, cleaned, re.DOTALL):
                try:
                    return repair_json(match, return_objects=True)
                except Exception:
                    continue

        return repair_json(cleaned, return_objects=True)


class ToonOutputConverter(JsonOutputConverter):
    """Convert TOON or JSON-like LLM text into the expected Pydantic model."""

    @staticmethod
    def _parse_json_value(text: str) -> Any:
        cleaned = text.strip()

        fenced = re.search(
            r"```(?:toon|json)?\s*(.*?)```", cleaned, re.DOTALL | re.IGNORECASE
        )
        if fenced:
            cleaned = fenced.group(1).strip()

        if cleaned.startswith(("{", "[")):
            try:
                return JsonOutputConverter._parse_json_value(cleaned)
            except Exception:
                pass

        return _parse_toon_value(cleaned)


# ---------------------------------------------------------------------------
# TOON parsing helpers
# ---------------------------------------------------------------------------

def _parse_toon_value(text: str) -> dict[str, Any]:
    lines = [
        line.rstrip()
        for line in text.splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]
    if not lines:
        return {}

    header = lines[0].strip()

    # Table format:  key[N]{field1,field2,...}:
    table_match = re.match(r"^([A-Za-z_]\w*)\[\d+\]\{([^}]+)\}:$", header)
    if table_match:
        key = table_match.group(1)
        fields = [f.strip() for f in table_match.group(2).split(",")]
        rows = [_parse_toon_row(line.strip(), fields) for line in lines[1:]]
        return {key: [r for r in rows if any(str(v).strip() for v in r.values())]}

    # List format:  key[N]: item1,item2,...
    list_match = re.match(r"^([A-Za-z_]\w*)\[\d+\]:\s*(.*)$", header)
    if list_match:
        key = list_match.group(1)
        rest = list_match.group(2).strip()
        values = _split_csv(rest) if rest else [
            line.strip().lstrip("- ").strip() for line in lines[1:]
        ]
        return {key: [_coerce_scalar(v) for v in values if str(v).strip()]}

    # Key: value pairs
    payload: dict[str, Any] = {}
    for line in lines:
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        payload[key.strip()] = _coerce_scalar(value.strip())
    return payload


def _parse_toon_row(line: str, fields: list[str]) -> dict[str, Any]:
    """
    Parse one data row of a TOON table.

    List fields (required_skills, skill_gap, …) use semicolons as separators
    and must be extracted *before* CSV splitting so commas inside them are safe.
    """
    # Strategy: replace semicolons in list fields after we know which column they
    # land in. We do this by splitting on commas but treating semicolon-delimited
    # segments as atomic values.
    parts = _split_csv(line)

    record: dict[str, Any] = {}
    for i, field in enumerate(fields):
        raw = parts[i].strip() if i < len(parts) else ""
        if field in _TOON_LIST_FIELDS:
            record[field] = [
                item.strip()
                for item in re.split(r"[;|]+", raw)
                if item.strip()
            ]
        else:
            record[field] = _coerce_scalar(raw)
    return record


def _split_csv(line: str) -> list[str]:
    reader = csv.reader(StringIO(line), skipinitialspace=True)
    return next(reader, [])


def _coerce_scalar(value: Any) -> Any:
    if value is None:
        return None
    text = str(value).strip()
    if text in {"", "null", "None", "none"}:
        return None
    if text.lower() == "true":
        return True
    if text.lower() == "false":
        return False
    if re.fullmatch(r"-?\d+", text):
        return int(text)
    if re.fullmatch(r"-?\d+\.\d+", text):
        return float(text)
    return text


def _is_list_annotation(annotation: Any) -> bool:
    origin = getattr(annotation, "__origin__", None)
    return annotation is list or origin is list
