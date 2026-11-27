## AI v2

| Check | Result | Detail |
|---|---|---|
| valid note -> 200 with the six fields | PASS | 200 {"title":"Pay the electricity bill","category":"finance","priority":"high","confidence":0. |
| bad input -> 400 (the assignment's code) | PASS | [400, 400, 400, 400, 400] |
| bad input -> zero model calls | PASS | 0 calls |
| bad input error names the field | PASS | {"error":"text is required"} |
| fenced / chatty JSON is parsed | PASS | 200 {"title":"Pay the electricity bill","category":"finance","pr |
| invalid answer -> one repair -> 200 | PASS | 200, 2 calls |
| repair hands the model its error | PASS | {"role": "user", "content": "Your previous answer was rejected by the validator with this error:\ncategory: In |
| invalid twice -> 422 after exactly 2 calls | PASS | 422, 2 calls |
| raw model text never returned (bad answer) | PASS | {"error":"the model's answer failed schema validation twice"} |
| refusal -> clean error, no raw text | PASS | 422 {"error":"the model's answer failed schema validation twice"} |
| 401 is never retried (1 call) | PASS | 1 calls, HTTP 502 |
| 401 -> clean error, process alive | PASS | 502 {"error":"the language model rejected our credentials"} |
| 500 retried, but bounded (2-4 calls) | PASS | 3 calls in 1.1s, HTTP 502 |
| 429 + Retry-After -> retried -> 200 | PASS | 200, 2 calls |
| timeout <= 60 s fires (mock stalls 70 s) | PASS | HTTP 200 after 30s, 2 calls |
| stub -> 200, schema-shaped, zero model calls | PASS | 200 source=stub calls=0 |
| kill switch -> 200, schema-shaped, zero model calls | PASS | 200 source=fallback calls=0 |
| every call logged with token counts | PASS | llm-calls.jsonl |

**18/18 passed**
