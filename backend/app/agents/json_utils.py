import json
import re


def extract_json(text: str):
    fenced = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
    candidate = fenced.group(1) if fenced else text

    for start_char, end_char in (("[", "]"), ("{", "}")):
        start = candidate.find(start_char)
        if start == -1:
            continue
        depth = 0
        for i in range(start, len(candidate)):
            if candidate[i] == start_char:
                depth += 1
            elif candidate[i] == end_char:
                depth -= 1
                if depth == 0:
                    snippet = candidate[start : i + 1]
                    try:
                        return json.loads(snippet)
                    except json.JSONDecodeError:
                        break

    raise ValueError("No valid JSON found in model output")
