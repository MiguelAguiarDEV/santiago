import requests
import json

url = "https://api.deepseek.com/chat/completions"
api_key = "sk-883fc6075b204c5c880dd0b5d04f44f3"

headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json"
}

data = {
    "model": "deepseek-chat",
    "messages": [
        {"role": "system", "content": "You are a helpful assistant"},
        {"role": "user", "content": "Quien es el mejor jugador de futbol de la historia?"}
    ],
    "stream": False
}

response = requests.post(url, headers=headers, data=json.dumps(data))

if response.status_code == 200:
    response_data = response.json()
    print(response_data['choices'][0]['message']['content'])
else:
    print(f"Error: {response.status_code}")
    print(response.text)