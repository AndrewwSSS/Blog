import httpx

from app.core.reply_generators.base_ai_reply_generator import BaseAIReplyGenerator


class GroqReplyGenerator(BaseAIReplyGenerator):
    MODEL = "llama3-8b-8192"
    prompt = "Generate reply for post with title: '{title}',and content: '{content}'"

    def _get_prompt(self, title: str, content: str) -> str:
        return self.prompt.format(title=title, content=content)

    async def generate_post_reply(self, title: str, content: str) -> str:
        from app.core.config import settings
        headers = {
            "Authorization": f"Bearer {settings.GROQ_API_KEY}",
            "Content-Type": "application/json"
        }

        body = {
            "model": self.MODEL,
            "messages": [
                {"role": "user", "content": self._get_prompt(
                    title, content
                )}
            ],
            "temperature": 0
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers=headers,
                json=body
            )

        if response.status_code == 200:
            response_data = response.json()
            return response_data["choices"][0]["message"]["content"].strip()
        else:
            raise Exception(f"Groq API returned an error: {response.status_code=}, {response.text=}")
