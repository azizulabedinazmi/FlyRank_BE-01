"""Stage 0 smoke test: can this machine get one word out of a model?

    python -m llm.hello

Three environment variables are the only difference between a model on your laptop and one in a datacentre:
LLM_BASE_URL, LLM_API_KEY, LLM_MODEL.
"""
import os

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
client = OpenAI(base_url=os.environ["LLM_BASE_URL"], api_key=os.environ["LLM_API_KEY"], timeout=30.0, max_retries=0)
res = client.chat.completions.create(
    model=os.environ["LLM_MODEL"],
    messages=[{"role": "user", "content": "Reply with exactly the word: ready"}],
    temperature=0,
)
print(res.choices[0].message.content)
