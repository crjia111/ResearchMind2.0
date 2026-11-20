# 参数

## papers.list

{
  "type": "object",
  "properties": {
    "fields": {
      "type": "array",
      "items": {
        "type": "string"
      }
    },
    "topic": {
      "type": "string"
    }
  },
  "required": [],
  "additionalProperties": false
}

## papers.selection.get

{
  "type": "object",
  "properties": {},
  "required": [],
  "additionalProperties": false
}

## papers.info

{
  "type": "object",
  "properties": {
    "paper_id": {
      "type": "string",
      "minLength": 1
    }
  },
  "required": [
    "paper_id"
  ],
  "additionalProperties": false
}

## papers.download

{
  "type": "object",
  "properties": {
    "url": {
      "type": "string",
      "minLength": 1
    },
    "name": {
      "type": "string"
    }
  },
  "required": [
    "url"
  ],
  "additionalProperties": false
}

## papers.content.get

{
  "type": "object",
  "properties": {
    "paper_id": {
      "type": "string"
    },
    "url": {
      "type": "string"
    }
  },
  "required": [],
  "additionalProperties": false
}

## papers.content.batch_get

{
  "type": "object",
  "properties": {
    "paper_ids": {
      "type": "array",
      "items": {
        "type": "string"
      },
      "minItems": 1
    }
  },
  "required": [
    "paper_ids"
  ],
  "additionalProperties": false
}

## papers.content.read

{
  "type": "object",
  "properties": {
    "artifact_id": {
      "type": "string",
      "minLength": 1
    }
  },
  "required": [
    "artifact_id"
  ],
  "additionalProperties": false
}

## papers.content.read_segment

{
  "type": "object",
  "properties": {
    "artifact_id": {
      "type": "string",
      "minLength": 1
    },
    "start": {
      "type": "integer",
      "minimum": 0
    },
    "length": {
      "type": "integer",
      "minimum": 1,
      "maximum": 100000
    }
  },
  "required": [
    "artifact_id"
  ],
  "additionalProperties": false
}

## papers.content.find

{
  "type": "object",
  "properties": {
    "artifact_id": {
      "type": "string",
      "minLength": 1
    },
    "search_term": {
      "type": "string",
      "minLength": 1
    },
    "context_length": {
      "type": "integer",
      "minimum": 0,
      "maximum": 10000
    }
  },
  "required": [
    "artifact_id",
    "search_term"
  ],
  "additionalProperties": false
}

## papers.analyze

{
  "type": "object",
  "properties": {
    "paper_ids": {
      "type": "array",
      "items": {
        "type": "string"
      },
      "minItems": 1
    },
    "instruction": {
      "type": "string"
    }
  },
  "required": [
    "paper_ids"
  ],
  "additionalProperties": false
}

## papers.export_csv

{
  "type": "object",
  "properties": {
    "records": {
      "type": "array",
      "items": {
        "type": "object"
      }
    },
    "fields": {
      "type": "array",
      "items": {
        "type": "string"
      }
    },
    "name": {
      "type": "string"
    }
  },
  "required": [],
  "additionalProperties": false
}
