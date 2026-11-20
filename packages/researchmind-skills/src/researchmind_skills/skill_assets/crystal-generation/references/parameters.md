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

## simulation.generate

{
  "type": "object",
  "properties": {
    "composition": {
      "type": "string",
      "minLength": 1
    },
    "device": {
      "type": "string",
      "enum": [
        "cpu",
        "cuda"
      ]
    },
    "num_samples": {
      "type": "integer",
      "minimum": 1,
      "maximum": 100
    },
    "top_k": {
      "type": "integer",
      "minimum": 1,
      "maximum": 1000
    },
    "max_new_tokens": {
      "type": "integer",
      "minimum": 1,
      "maximum": 20000
    },
    "spacegroup": {
      "type": "string"
    }
  },
  "required": [
    "composition"
  ],
  "additionalProperties": false
}
