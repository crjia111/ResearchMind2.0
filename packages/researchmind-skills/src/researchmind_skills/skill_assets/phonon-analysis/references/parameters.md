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

## simulation.relax

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
    "max_steps": {
      "type": "integer",
      "minimum": 1,
      "maximum": 10000
    },
    "fmax": {
      "type": "number",
      "minimum": 1e-06
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

## simulation.phonon

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
    "supercell_matrix": {
      "type": "array",
      "items": {
        "type": "integer",
        "minimum": 1,
        "maximum": 10
      },
      "minItems": 3,
      "maxItems": 3
    },
    "amplitude": {
      "type": "number",
      "minimum": 1e-06
    },
    "relax_first": {
      "type": "boolean"
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
