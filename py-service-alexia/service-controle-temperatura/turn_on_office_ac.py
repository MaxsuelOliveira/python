import os


def main() -> None:
    city = os.getenv("ALEXA_WEATHER_CITY", "sua cidade")
    temperature = os.getenv("ALEXA_WEATHER_TEMPERATURE", "")
    threshold = os.getenv("ALEXA_WEATHER_THRESHOLD", "")
    office_name = os.getenv("OFFICE_NAME", "escritorio")

    print(
        f"Ligando o ar do {office_name}. "
        f"Cidade={city} temperatura={temperature} limite={threshold}"
    )

    # Exemplo:
    # - chamar uma API do seu ar-condicionado
    # - enviar um webhook para Home Assistant
    # - acionar um servico interno da empresa


if __name__ == "__main__":
    main()
