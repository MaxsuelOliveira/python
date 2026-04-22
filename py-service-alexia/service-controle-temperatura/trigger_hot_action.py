import os


def main() -> None:
    city = os.getenv("ALEXA_WEATHER_CITY", "sua cidade")
    temperature = os.getenv("ALEXA_WEATHER_TEMPERATURE", "")
    threshold = os.getenv("ALEXA_WEATHER_THRESHOLD", "")

    print(
        "Temperatura acima do limite: "
        f"cidade={city} temperatura={temperature} limite={threshold}"
    )

    # Exemplo: aqui voce pode chamar uma API interna, enviar um webhook,
    # acionar outro servico ou integrar com alguma automacao.


if __name__ == "__main__":
    main()
