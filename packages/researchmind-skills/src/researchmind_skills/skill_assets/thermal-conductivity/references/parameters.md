# 参数

## simulation.validate_cif

{
  "type": "object",
  "properties": {
    "artifact_id": {
      "type": "string"
    },
    "cif_content": {
      "type": "string"
    },
    "artifact_ids": {
      "type": "array",
      "items": {
        "type": "string",
        "minLength": 1
      },
      "minItems": 1,
      "maxItems": 100
    }
  },
  "required": [],
  "additionalProperties": false
}

## simulation.kappa

{
  "type": "object",
  "properties": {
    "artifact_id": {
      "type": "string"
    },
    "cif_content": {
      "type": "string"
    },
    "device": {
      "type": "string",
      "enum": [
        "cpu",
        "cuda"
      ]
    },
    "method": {
      "type": "string",
      "enum": [
        "kappa_p",
        "kappa_mtp"
      ]
    },
    "temperature": {
      "type": "number",
      "minimum": 1,
      "maximum": 5000
    },
    "artifact_ids": {
      "type": "array",
      "items": {
        "type": "string",
        "minLength": 1
      },
      "minItems": 1,
      "maxItems": 100
    }
  },
  "required": [],
  "additionalProperties": false
}
