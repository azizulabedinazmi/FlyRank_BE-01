## Mine

| Check | Result | Detail |
|---|---|---|
| valid note -> 200 with the six fields | PASS | 200 {"title":"Pay the electricity bill","category":"finance","priority":"high","confidence":0. |
| bad input -> 400 (the assignment's code) | PASS | [400, 400, 400, 400, 400] |
| bad input -> zero model calls | PASS | 0 calls |
| bad input error names the field | PASS | {"error":"Invalid text: Field required"} |
| fenced / chatty JSON is parsed | PASS | 200 {"title":"Pay the electricity bill","category":"finance","pr |
| invalid answer -> one repair -> 200 | PASS | 200, 2 calls |
| repair hands the model its error | PASS | {"role": "user", "content": "Your previous answer was rejected for this reason: category: Input should be 'wor |
| invalid twice -> 422 after exactly 2 calls | PASS | 422, 2 calls |
| raw model text never returned (bad answer) | PASS | {"error":"The model's answer failed the schema twice (invalid fields: category). It was quarantined; nothing w |
| refusal -> clean error, no raw text | PASS | 422 {"error":"The model's answer failed the schema twice (the answer contained no JSON object). It was q |
| 401 is never retried (1 call) | PASS | 1 calls, HTTP 502 |
| 401 -> clean error, process alive | PASS | 502 {"error":"The model provider rejected this server's credentials. An operator nee |
| 500 retried, but bounded (2-4 calls) | PASS | 3 calls in 3.9s, HTTP 502 |
| 429 + Retry-After -> retried -> 200 | PASS | 200, 2 calls |
| timeout <= 60 s fires (mock stalls 70 s) | PASS | HTTP 200 after 31s, 2 calls |
| stub -> 200, schema-shaped, zero model calls | PASS | 200 source=stub calls=0 |
| kill switch -> 200, schema-shaped, zero model calls | PASS | 200 source=fallback calls=0 |
| every call logged with token counts | PASS | logs\llm-calls.jsonl |

**18/18 passed**
