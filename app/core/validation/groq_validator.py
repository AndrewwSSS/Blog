import httpx

from app.core.validation.base_content_validator import BaseContentValidator


class GroqValidator(BaseContentValidator):
    MODEL = "llama3-8b-8192"
    VALIDATE_POST_PROMT_TEMPLATE = '''
        Title: "{title}"
        Content: "{content}"
        Task: Based on the content of the post, determine if it contains any offensive language or profanity.
        Respond only with a clear 'yes' or 'no'.
    '''

    def _get_content_by_template(self, content: str, title: str) -> str:
        return self.VALIDATE_POST_PROMT_TEMPLATE.format(title=title, content=content)

    async def validate_post(self, content: str, title: str) -> bool:
        from app.core.config import settings
        headers = {
            "Authorization": f"Bearer {settings.GROQ_API_KEY}",
            "Content-Type": "application/json"
        }

        body = {
            "model": self.MODEL,
            "messages": [
                {"role": "user", "content": self._get_content_by_template(
                    content, title
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
            answer = response_data["choices"][0]["message"]["content"].strip().lower()
            return answer == "no"
        else:
            raise Exception(f"Groq API returned an error: {response.status_code=}, {response.text=}")

    async def validate_comment(self, content: str) -> bool:
        return await self.validate_post(content, "no title provided")
