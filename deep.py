from openai import OpenAI

client = OpenAI(api_key="sk-883fc6075b204c5c880dd0b5d04f44f3", base_url="https://api.deepseek.com")

response = client.chat.completions.create(
    model="deepseek-chat",
    messages=[
        {"role": "system", "content": "You are a helpful assistant"},
        {"role": "user", "content": "Quien es el mejor jugador de futbol de la historia?"},
    ],
    stream=False
)

print(response.choices[0].message.content)