<a name="readme-top"></a>

[![LinkedIn](https://custom-icon-badges.demolab.com/badge/LinkedIn-0A66C2?logo=linkedin-white&logoColor=fff)](https://www.linkedin.com/in/azizulabedin/)
[![GitHub](https://img.shields.io/badge/GitHub-181717?logo=github&logoColor=white)](https://github.com/azizulabedinazmi)
[![Portfolio](https://img.shields.io/badge/Portfolio-00C7B7?logo=netlify&logoColor=white)](https://azizulabedinazmi.netlify.app/)
[![FlyRank verified](https://img.shields.io/badge/FlyRank_verified-FR--D1--A84A9--AB526-1A7A4A)](https://internship.flyrank.ai/verify?id=FR-D1-A84A9-AB526&first_name=Azizul)
[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)

<div align="center">
  <h3>Task API</h3>
  <p>
    A small to-do list REST API with full CRUD, built by hand with Python and FastAPI.
    Data lives in memory, every error is JSON, and Swagger UI documents every endpoint.
    <br /><br />
    FlyRank AI Internship · Backend AI Engineering · Week 2 · Assignment BE-01
  </p>
</div>

<details>
  <summary>Table of Contents</summary>
  <ol>
    <li><a href="#about-the-project">About The Project</a></li>
    <li><a href="#built-with">Built With</a></li>
    <li><a href="#getting-started">Getting Started</a></li>
    <li><a href="#endpoints">Endpoints</a></li>
    <li><a href="#curl-example">Example: curl -i</a></li>
    <li><a href="#swagger-ui">Swagger UI</a></li>
    <li><a href="#mortality">The Mortality Experiment</a></li>
    <li><a href="#ai-vs-me">AI vs Me (Stage 7)</a></li>
    <li><a href="#repository-structure">Repository Structure</a></li>
    <li><a href="#about-me">About Me</a></li>
    <li><a href="#about-flyrank">About FlyRank</a></li>
    <li><a href="#license">License</a></li>
    <li><a href="#contact">Contact</a></li>
  </ol>
</details>

## 📋 About The Project <a name="about-the-project"></a>

This API manages a to-do list: you can create tasks, read them, update them and delete them. Those are the four
CRUD operations behind almost every backend.

- **Five task endpoints** plus `GET /` (API info) and `GET /health` (liveness check).
- **Correct status codes:** 200 for reads and updates, 201 for create, 204 for delete, 400 for invalid input, 404 for an unknown id.
- **Strict validation.** The server never trusts the client: empty titles, `{}` updates and `"yes"` instead of `true` are all rejected.
- **In-memory storage on purpose.** There's no database yet, so data disappears on restart. That lesson leads into Week 3.
- **Built in 7 stages**, each with its own commit, so `git log` tells the story.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

## 🛠️ Built With <a name="built-with"></a>

- [Python 3.10+](https://www.python.org/)
- [FastAPI](https://fastapi.tiangolo.com/) for routing, validation and the OpenAPI schema
- [Uvicorn](https://www.uvicorn.org/) as the server
- [Pydantic](https://docs.pydantic.dev/) strict types (`StrictStr`, `StrictBool`)
- Swagger UI (built into FastAPI) at `/docs`

<p align="right">(<a href="#readme-top">back to top</a>)</p>

## 🎯 Getting Started <a name="getting-started"></a>

You need Python 3.10 or newer.

```bash
git clone https://github.com/azizulabedinazmi/FlyRank_BE-01.git
cd FlyRank_BE-01
python -m venv .venv
```

Activate the virtual environment:

- Windows: `.venv\Scripts\activate`
- macOS / Linux: `source .venv/bin/activate`

Install dependencies and start the server:

```bash
pip install -r requirements.txt
uvicorn main:app --reload
```

The API runs at http://localhost:8000. Swagger UI is at http://localhost:8000/docs.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

## 🔌 Endpoints <a name="endpoints"></a>

| Method | Path | What it does | Success | Errors |
|--------|------|--------------|---------|--------|
| GET | `/` | Describes the API | 200 | – |
| GET | `/health` | Health check, returns `{"status": "ok"}` | 200 | – |
| GET | `/tasks` | Lists all tasks | 200 | – |
| GET | `/tasks/{id}` | Gets one task | 200 | 404 unknown id |
| POST | `/tasks` | Creates a task from `{"title": "..."}` | 201 | 400 missing/empty title |
| PUT | `/tasks/{id}` | Updates `title` and/or `done` | 200 | 400 empty/invalid body, 404 unknown id |
| DELETE | `/tasks/{id}` | Deletes a task (empty body) | 204 | 404 unknown id |

Every error returns JSON like `{"error": "Task 99 not found"}`.

A task looks like this:

```json
{ "id": 1, "title": "Learn HTTP methods", "done": true }
```

### Validation rules

- `POST /tasks`: `title` must be present, must be a string, and cannot be empty or only spaces.
- `PUT /tasks/{id}`: send `title`, `done`, or both. `{}` is rejected. `title` cannot be empty, and `done` must be `true` or `false`.
- Malformed JSON, or a non-number id like `/tasks/abc`, also returns 400.

FastAPI normally answers invalid input with **422**. This project replaces that with **400 + `{"error": ...}`** so it
matches the assignment.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

## 💻 Example: `curl -i` <a name="curl-example"></a>

```text
$ curl -i -X POST http://localhost:8000/tasks -H "Content-Type: application/json" -d '{"title":"Buy milk"}'
HTTP/1.1 201 Created
date: Fri, 20 Nov 2026 12:02:41 GMT
server: uvicorn
content-length: 40
content-type: application/json

{"id":4,"title":"Buy milk","done":false}
```

```text
$ curl -i http://localhost:8000/tasks/99
HTTP/1.1 404 Not Found
date: Fri, 20 Nov 2026 12:02:41 GMT
server: uvicorn
content-length: 29
content-type: application/json

{"error":"Task 99 not found"}
```

> On Windows PowerShell, use `curl.exe` instead of `curl`. Pass the JSON body from a file
> (`--data-binary "@body.json"`) because PowerShell mangles the quotes in `-d '{"title":"Buy milk"}'`.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

## 📖 Swagger UI <a name="swagger-ui"></a>

Open http://localhost:8000/docs. Every endpoint is listed, and **Try it out** sends real requests.

![Swagger UI showing all endpoints](docs/swagger-endpoints.png)

<p align="right">(<a href="#readme-top">back to top</a>)</p>

## 🧪 The Mortality Experiment <a name="mortality"></a>

I created a task (`id 4`, "Buy milk"), restarted the server, and called `GET /tasks` again. Only the 3 starting
tasks came back. The task list is a Python variable in the server's memory, so it is rebuilt from the source code
every time the program starts, and anything added while it ran is gone. A database keeps data outside the
process, which is the problem Week 3 solves.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

## 🤖 AI vs Me (Stage 7) <a name="ai-vs-me"></a>

I gave an AI assistant (Claude) a prompt asking for the same API, ran its code, and fired the same checkpoint
requests at it as at mine. The AI's code is kept apart in [`ai-version/`](ai-version/), and my own `main.py` was
not changed.

- `ai-version/PROMPT-v1.md` and `ai-version/v1/main.py`: first prompt and the code it produced
- `ai-version/PROMPT-v2.md` and `ai-version/v2/main.py`: the improved prompt (rematch)
- `ai-version/checkpoint.py`: the 19 test requests (`python ai-version/checkpoint.py http://127.0.0.1:8000`)
- `ai-version/results-*.md`: the full test output for each version

### My prompt (v1)

```text
Build me a to-do list REST API in Python using FastAPI.

- Keep the tasks in memory in a Python list (no database, no files). Start with 3 example tasks.
- Each task has an id (number), a title (text) and done (true/false).
- Endpoints:
  - GET / returns a short JSON description of the API
  - GET /health returns {"status": "ok"}
  - GET /tasks returns all tasks
  - GET /tasks/{id} returns one task
  - POST /tasks creates a task from {"title": "..."}; the server picks the next id and sets done to false
  - PUT /tasks/{id} updates the title and/or done
  - DELETE /tasks/{id} deletes a task
- Status codes: 200 for reads and updates, 201 for create, 204 for delete, 404 if the id doesn't exist, 400 if the title is missing or empty.
- Errors should be returned as JSON.
- I want Swagger UI at /docs.
- Put everything in one file called main.py.
```

### Results

v1 started on the first try with no extra packages.

| Test | Mine | AI v1 | AI v2 |
|---|---|---|---|
| Reads, create, delete, unknown id (11 tests) | all pass | all pass | all pass |
| `POST {}`, empty or blank title, number title, bad JSON | 400 | 400 | 400 |
| `PUT {}` (empty body) | **400** | **200**, silently changes nothing ❌ | 400 |
| `PUT {"done": "yes"}` | **400** | **200**, stores `done: true` ❌ | 400 |
| `PUT {"done": 1}` | 400 | 200, stores `done: true` ❌ | 400 |
| `GET /tasks/abc` | 400 | 400 | 400 |
| 422 listed in Swagger docs | no | **yes, 4 times** (never actually sent) ❌ | no |
| **Score** | **19/19** | **17/19** | **19/19** |

### 1. What the AI did better

- **Ids are never reused.** v1 uses a `next_id` counter. Mine uses `max(id) + 1`, so if I delete the newest task
  (id 4) and create another, the new one gets id 4 again. A client that still remembers the old task 4 would
  silently get a different task. The counter is the safer design, and I can explain why.
- **Errors use exceptions.** The AI raises `HTTPException(404, ...)` inside a helper and converts it to
  `{"error": ...}` once, in a global handler. In my code, every endpoint has to check `if task is None: return not_found(...)`.
  Its approach means less repeated code.
- **It tells "not sent" apart from "sent as null".** It uses `payload.model_fields_set`, so `{"title": null}` is
  rejected, not ignored.

### 2. What it got wrong or quietly ignored

- **`PUT {}` returns 200 and does nothing.** Accepting an empty update hides client bugs. My API returns 400.
- **`done` is coerced.** Pydantic's default "lax" mode turns `"yes"` and `1` into `true`. I used
  `StrictBool`/`StrictStr` so that only real JSON booleans and strings are accepted.
- **The docs don't match the API.** Swagger still lists a 422 "Validation Error" response on 4 endpoints, but the
  API returns 400 instead. Documentation that lies is worse than none.
- **The error shape is inconsistent.** Most errors are `{"error": "..."}`, but validation errors add an extra
  `details` list.

### 3. What my prompt forgot to specify (the AI decided for me)

- **The exact error body.** I only wrote "errors as JSON". The AI happened to choose `{"error": ...}`, but it could
  just as easily have used FastAPI's default `{"detail": ...}`.
- **What PUT does with an empty body**, and **whether types are strict**. I didn't say, so it picked the lenient option.
- **Malformed JSON and non-numeric ids.** I never mentioned them. The AI chose 400 on its own, which happens to match mine.
- **Id reuse, the exact `GET /` response, the port, and the sample tasks.** All were left to the AI.

### Rematch (v2)

[`PROMPT-v2.md`](ai-version/PROMPT-v2.md) spelled out the exact error shape, "`PUT {}` is a 400", "no type coercion",
"never use 422, and do not list it in the docs", and "ids are never reused". The new code passed 19/19. The cost
was size: v2 is 256 lines against my 139, because it reads the raw request and validates by hand instead of using
Pydantic models, so it also had to describe the request bodies in the OpenAPI docs by hand.

**Lesson:** the AI didn't guess wrong at random. Every failure in v1 traced back to something my prompt didn't say.
I could only spot those failures because I had built and tested the API myself first.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

## 🗂️ Repository Structure <a name="repository-structure"></a>

| Path | Purpose |
|---|---|
| `main.py` | The whole API, built by hand in Stages 0–6. |
| `requirements.txt` | Pinned `fastapi` and `uvicorn` versions. |
| `docs/` | README screenshots. |
| `ai-version/` | Stage 7: the AI-generated code (v1, v2), both prompts, the test script and the results. |
| `LICENSE` | MIT License. |
| `README.md` | This file. |

<p align="right">(<a href="#readme-top">back to top</a>)</p>

## 👋 About Me <a name="about-me"></a>

I'm **Azizul Abedin Azmi**, a Computer Science and Engineering graduate from East West University (2026) and a
**Machine Learning Intern at FlyRank AI** (remote).

My main work is **self-supervised computer vision**: image classifiers built on self-supervised Vision Transformers
(SimCLR variants, BYOL, ViT) that need fewer labeled examples, for areas like medical imaging and agriculture.
This repo is part of the backend side of my internship: learning to serve and expose the systems I build.

**Peer-reviewed publications**

- *Detection of Cleft and Non-Cleft Lip Features with a Multi-Task Image Processing Network.* ICCIIR 2025, Springer LNNS vol. 1593. [DOI](https://link.springer.com/chapter/10.1007/978-3-032-02790-0_9)
- *PotatoCare: A Deep Learning-Powered Framework for Automated Detection and Classification of Potato Disease.* ICDSIS 2025, IEEE. [DOI](https://ieeexplore.ieee.org/document/11070388/)
- *A Vision Transformer Adaptation of SimCLRv2 for Self-Supervised Galaxy Detection.* SPICSCON 2025, IEEE. [DOI](https://ieeexplore.ieee.org/document/11504180/)

**Selected projects**

- [E-waste Detection System](https://github.com/azizulabedinazmi/E-waste-Detection-System): real-time YOLOv8 detection in a Gradio app
- [Crop Classification System](https://github.com/azizulabedinazmi/Crop-Classification-GradioApp): Vision Transformer classifier as a Gradio app
- [Image Caption Generator](https://github.com/azizulabedinazmi/Image-Caption-Generator-ICG): InceptionV3 + Transformer trained on COCO, served with Streamlit
- [RMP Classification Models](https://huggingface.co/spaces/azizulabedinazmi/RMP-Classification-System): self-supervised ViT models for rare medicinal plants

More about me: [Portfolio](https://azizulabedinazmi.netlify.app/) ·
[ORCID](https://orcid.org/0009-0003-5269-6900) ·
[ResearchGate](https://www.researchgate.net/profile/Azizul-Abedin-Azmi)

<p align="right">(<a href="#readme-top">back to top</a>)</p>

## 🚀 About FlyRank <a name="about-flyrank"></a>

[FlyRank AI](https://www.flyrank.ai/) is an AI search growth platform. It helps brands rank on Google and become
the trusted answer across AI engines.

The [FlyRank AI Internship](https://internship.flyrank.ai/) is a free, remote, self-paced program built around real
work, expert feedback and verifiable credentials. It has six tracks: General AI Fluency, Machine Learning,
AI Marketing, Front-end AI Engineering, Backend AI Engineering, and UI/UX Design. This project is assignment
**BE-01** of the Backend AI Engineering track.

My internship credential can be checked here:

[![FlyRank verified](https://img.shields.io/badge/FlyRank_verified-FR--D1--A84A9--AB526-1A7A4A?style=for-the-badge)](https://internship.flyrank.ai/verify?id=FR-D1-A84A9-AB526&first_name=Azizul)

<p align="right">(<a href="#readme-top">back to top</a>)</p>

## 📜 License <a name="license"></a>

Distributed under the MIT License. See `LICENSE` for more information.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

## 📧 Contact <a name="contact"></a>

Azizul Abedin Azmi · [LinkedIn](https://www.linkedin.com/in/azizulabedin/) · [Portfolio](https://azizulabedinazmi.netlify.app/)

Project Link: [https://github.com/azizulabedinazmi/FlyRank_BE-01](https://github.com/azizulabedinazmi/FlyRank_BE-01)

<p align="right">(<a href="#readme-top">back to top</a>)</p>
