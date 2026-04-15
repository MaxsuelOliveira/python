import os
import requests


def get_google_maps_api_key():
    api_key = os.getenv("GOOGLE_MAPS_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("Defina GOOGLE_MAPS_API_KEY no ambiente antes de executar este script.")
    return api_key


def get_businesses(city):
    api_key = get_google_maps_api_key()
    URL = "https://maps.googleapis.com/maps/api/place/textsearch/json"
    query = f"businesses in {city}"
    params = {
        "query": query,
        "key": api_key
    }
    response = requests.get(URL, params=params)
    businesses = response.json()["results"]

    # Defina o local e o tipo de empresa que você deseja consultar
    location = "cidade,estado"
    type = "lojas"

    # Construa a URL da API
    url = f"https://maps.googleapis.com/maps/api/place/textsearch/json?query={type}+in+{city}&key={api_key}"

    # Execute a consulta à API
    response = requests.get(url)

    # Verifique se a consulta foi bem-sucedida
    if response.status_code == 200:
        # Carregue o resultado da consulta em um objeto JSON
        result = response.json()

        # Imprima o nome e o endereço de cada empresa encontrada
        for business in result["results"]:
            print(business["name"])
            print(business["formatted_address"])
    else:
        print("A consulta à API falhou com o status code:", response.status_code)

    return businesses


if __name__ == "__main__":
    businesses = get_businesses("Barreiras, Bahia")
    for business in businesses:
        # print(business)
        # print(business["name"])
        # print(business["formatted_address"])
        # print("-" * 20)
        break
