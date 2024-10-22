import httpx

from app.core.config import settings
from app.core.validation.base_content_validator import BaseContentValidator


class OpenContentValidator(BaseContentValidator):
    MODEL = "gpt-3.5-turbo"
    VALIDATE_POST_PROMT_TEMPLATE = '''
        Title: "{title}"
        Content: "{content}"
        Task: Based on the content of the post, determine if it contains any offensive language or profanity. Respond only with a clear 'yes' or 'no'.
    '''

    def _get_content_by_template(self, content: str, title: str) -> str:
        return self.VALIDATE_POST_PROMT_TEMPLATE.format(title=title, content=content)

    async def validate_post(self, content: str, title: str) -> bool:
        headers = {
            "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
            "Content-Type": "application/json"
        }

        body = {
            "model": self.MODEL,
            "messages": [
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": self._get_content_by_template(
                    content, title
                )}
            ],
            "temperature": 0
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers=headers,
                json=body
            )

        if response.status_code == 200:
            response_data = response.json()
            answer = response_data["choices"][0]["message"]["content"].strip().lower()
            return answer == "no"
        else:
            raise Exception(f"OpenAI API returned an error: {response.status_code}, {response.text}")

    async def validate_comment(self, content: str) -> bool:
        return await self.validate_post(content, "no title provided")
