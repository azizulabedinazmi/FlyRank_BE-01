## AI v1

| Check | Result | Detail |
|---|---|---|
| valid note -> 200 with the six fields | PASS | 200 {"title":"Pay the electricity bill","category":"finance","priority":"high","confidence":0. |
| bad input -> 400 (the assignment's code) | FAIL | [422, 422, 422, 422, 422] |
| bad input -> zero model calls | PASS | 0 calls |
| bad input error names the field | PASS | {"detail":[{"type":"missing","loc":["body","text"],"msg":"Field required","input":{"txt":"hi"}},{"ty |
| fenced / chatty JSON is parsed | FAIL | 422 {"detail":"Model returned an invalid answer twice: Expecting |
| invalid answer -> one repair -> 200 | PASS | 200, 2 calls |
| repair hands the model its error | PASS | {"role": "user", "content": "Your previous answer was invalid: category: Input should be 'work', 'errands', 'h |
| invalid twice -> 422 after exactly 2 calls | PASS | 422, 2 calls |
| raw model text never returned (bad answer) | PASS | {"detail":"Model returned an invalid answer twice: category: Input should be 'work', 'errands', 'health', 'fin |
| refusal -> clean error, no raw text | PASS | 422 {"detail":"Model returned an invalid answer twice: Expecting value: line 1 column 1 (char 0)"} |
| 401 is never retried (1 call) | PASS | 1 calls, HTTP 503 |
| 401 -> clean error, process alive | PASS | 503 {"detail":"model call failed after 1 attempt(s): AuthenticationError"} |
| 500 retried, but bounded (2-4 calls) | PASS | 3 calls in 1.7s, HTTP 503 |
| 429 + Retry-After -> retried -> 200 | PASS | 200, 2 calls |
| timeout <= 60 s fires (mock stalls 70 s) | PASS | HTTP 200 after 21s, 2 calls |
| stub -> 200, schema-shaped, zero model calls | PASS | 200 source=stub calls=0 |
| kill switch -> 200, schema-shaped, zero model calls | PASS | 200 source=fallback calls=0 |
| every call logged with token counts | PASS | _app-AI_v1.log |

**16/18 passed**
