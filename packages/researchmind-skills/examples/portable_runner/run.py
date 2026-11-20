"""Framework-free example: introspect a capability and execute validated JSON."""
import argparse
import asyncio
import json
from researchmind_skills.api import Runtime,create_local_context
parser=argparse.ArgumentParser()
parser.add_argument("operation");parser.add_argument("input_file");parser.add_argument("--workspace",required=True);parser.add_argument("--skill",required=True)
args=parser.parse_args()
runtime=Runtime()
print(json.dumps(asyncio.run(runtime.execute(args.operation,json.load(open(args.input_file,encoding="utf-8")),create_local_context(args.workspace),args.skill)),ensure_ascii=False))
