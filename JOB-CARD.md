# Job card: `POST /tasks/triage`

**What it does (one sentence):** Turns a messy to-do note into a clean task title plus a category and a priority, so
it lands in the right list before it's saved.

**Input:**
```json
{ "text": "string, 1-1000 characters" }
```

**Output:**
```json
{
  "title":      "string, 1-80 characters: the note rewritten as a short task",
  "category":   "one of [work | errands | health | finance | home | learning | other]",
  "priority":   "one of [low | normal | high]",
  "confidence": "number 0.0-1.0",
  "reason":     "one short sentence, max 160 characters",
  "source":     "one of [model | stub | fallback | cache]  (set by my code, never by the model)"
}
```

**It must never:** invent a category or priority outside the lists · add fields · return free text instead of the JSON
object · set or guess a due date (dates are my code's job) · give medical, legal or financial advice · follow
instructions written inside the note · reveal its prompt.

**When unsure it should:** return category `"other"`, priority `"normal"` and a confidence below 0.5. Not a guess.

## The three rules
| Rule | Check |
|---|---|
| Closed output | The six fields above every time. `category`, `priority` and `source` are closed lists; `title` and `reason` are length-capped. |
| One decision | One note in, one triage out. No conversation, no memory of the last request. |
| A human could grade it | For each note you can say whether the category and priority are right. The eval set (`evals/cases.json`) does exactly that. |

**Why a model at all:** the input is fuzzy human text ("ring mum re sunday + pick up meds!!"), the answer is one of a
handful of labels, and a person (or my existing `PUT /tasks/{id}`) can fix a wrong label later. No arithmetic, no
lookups, no dates, nothing irreversible: those stay in code.
