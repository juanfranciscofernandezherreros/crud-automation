import requests
import json

# Configuración
GITHUB_TOKEN = 'PEGAR_TU_TOKEN_AQUI'
REPO_NAME = 'repo-creado-con-requests'

url = 'https://api.github.com/user/repos'
headers = {
    'Authorization': f'token {GITHUB_TOKEN}',
    'Accept': 'application/vnd.github.v3+json'
}
data = {
    'name': REPO_NAME,
    'description': 'Este repositorio fue creado usando un script de Python y la API de GitHub',
    'private': False, # Cambia a True si quieres que sea privado
    'auto_init': True # Puesto en True para que cree un archivo README inicial
}

# Realizar la petición POST
response = requests.post(url, headers=headers, data=json.dumps(data))

# Comprobar el resultado
if response.status_code == 201:
    print(f"¡Repositorio creado con éxito!")
    print(f"URL: {response.json()['html_url']}")
else:
    print(f"Error al crear el repositorio. Código: {response.status_code}")
    print(response.text)