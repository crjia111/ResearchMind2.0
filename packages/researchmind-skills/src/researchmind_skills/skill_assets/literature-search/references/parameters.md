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

## papers.topics

{
  "type": "object",
  "properties": {},
  "required": [],
  "additionalProperties": false
}

## papers.filter

{
  "type": "object",
  "properties": {
    "topic": {
      "type": "string"
    }
  },
  "required": [
    "topic"
  ],
  "additionalProperties": false
}

## papers.selection.update

{
  "type": "object",
  "properties": {
    "paper_ids": {
      "type": "array",
      "items": {
        "type": "string"
      }
    }
  },
  "required": [
    "paper_ids"
  ],
  "additionalProperties": false
}

## papers.selection.get

{
  "type": "object",
  "properties": {},
  "required": [],
  "additionalProperties": false
}

## papers.selection.clear

{
  "type": "object",
  "properties": {},
  "required": [],
  "additionalProperties": false
}

## papers.plan

{
  "type": "object",
  "properties": {
    "query": {
      "type": "string",
      "minLength": 1
    }
  },
  "required": [
    "query"
  ],
  "additionalProperties": false
}

## papers.search

{
  "type": "object",
  "properties": {
    "query": {
      "type": "string",
      "minLength": 1
    },
    "max_results": {
      "type": "integer",
      "minimum": 1,
      "maximum": 100
    },
    "sources": {
      "type": "array",
      "items": {
        "type": "string",
        "enum": [
          "arxiv",
          "tavily",
          "semantic_scholar"
        ]
      },
      "minItems": 1
    },
    "year_from": {
      "type": "integer",
      "minimum": 1900,
      "maximum": 2200
    }
  },
  "required": [
    "query"
  ],
  "additionalProperties": false
}

## papers.search_by_author

{
  "type": "object",
  "properties": {
    "author": {
      "type": "string",
      "minLength": 1
    },
    "max_results": {
      "type": "integer",
      "minimum": 1,
      "maximum": 100
    }
  },
  "required": [
    "author"
  ],
  "additionalProperties": false
}

## papers.import_uploads

{
  "type": "object",
  "properties": {
    "artifact_ids": {
      "type": "array",
      "items": {
        "type": "string"
      },
      "minItems": 1
    }
  },
  "required": [
    "artifact_ids"
  ],
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

## papers.web_search

{
  "type": "object",
  "properties": {
    "query": {
      "type": "string",
      "minLength": 1
    },
    "max_results": {
      "type": "integer",
      "minimum": 1,
      "maximum": 100
    }
  },
  "required": [
    "query"
  ],
  "additionalProperties": false
}

## papers.news_search

{
  "type": "object",
  "properties": {
    "query": {
      "type": "string",
      "minLength": 1
    },
    "max_results": {
      "type": "integer",
      "minimum": 1,
      "maximum": 100
    }
  },
  "required": [
    "query"
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
