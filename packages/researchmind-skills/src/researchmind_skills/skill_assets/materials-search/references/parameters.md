# 参数

## materials.query_mp

{
  "type": "object",
  "properties": {
    "formula": {
      "type": "string",
      "minLength": 1
    },
    "num_return": {
      "type": "integer",
      "minimum": 1,
      "maximum": 100
    }
  },
  "required": [
    "formula"
  ],
  "additionalProperties": false
}

## materials.query_oqmd

{
  "type": "object",
  "properties": {
    "formula": {
      "type": "string",
      "minLength": 1
    },
    "num_return": {
      "type": "integer",
      "minimum": 1,
      "maximum": 100
    }
  },
  "required": [
    "formula"
  ],
  "additionalProperties": false
}

## materials.query_cod

{
  "type": "object",
  "properties": {
    "formula": {
      "type": "string",
      "minLength": 1
    },
    "num_return": {
      "type": "integer",
      "minimum": 1,
      "maximum": 100
    }
  },
  "required": [
    "formula"
  ],
  "additionalProperties": false
}

## materials.query_aflow

{
  "type": "object",
  "properties": {
    "formula": {
      "type": "string",
      "minLength": 1
    },
    "num_return": {
      "type": "integer",
      "minimum": 1,
      "maximum": 100
    }
  },
  "required": [
    "formula"
  ],
  "additionalProperties": false
}

## materials.search

{
  "type": "object",
  "properties": {
    "formula": {
      "type": "string",
      "minLength": 1
    },
    "num_return": {
      "type": "integer",
      "minimum": 1,
      "maximum": 100
    },
    "sources": {
      "type": "array",
      "items": {
        "type": "string",
        "enum": [
          "mp",
          "oqmd",
          "cod",
          "aflow"
        ]
      },
      "minItems": 1
    }
  },
  "required": [
    "formula"
  ],
  "additionalProperties": false
}

## materials.recommend

{
  "type": "object",
  "properties": {
    "formula": {
      "type": "string",
      "minLength": 1
    },
    "num_return": {
      "type": "integer",
      "minimum": 1,
      "maximum": 100
    },
    "sources": {
      "type": "array",
      "items": {
        "type": "string",
        "enum": [
          "mp",
          "oqmd",
          "cod",
          "aflow"
        ]
      },
      "minItems": 1
    }
  },
  "required": [
    "formula"
  ],
  "additionalProperties": false
}
