# Skill Alexa de clima em Python

Este projeto cria uma skill Alexa em Python para consultar o clima atual da sua cidade. A skill usa o `deviceId` da Alexa como chave principal para descobrir qual cidade monitorar, consegue tentar o endereco configurado no dispositivo e pode executar um comando quando a temperatura passar do limite configurado. Agora ele tambem tem um modo de monitor agendado de 15 em 15 minutos para ligar o ar do escritorio automaticamente.

## O que foi montado

- Handler pronto para AWS Lambda em [lambda_function.py](lambda_function.py)
- Modelo de interacao em portugues do Brasil em [interaction-models/pt-BR.json](interaction-models/pt-BR.json)
- Arquivo de configuracao por `deviceId` em [config/device_locations.json](config/device_locations.json)
- Exemplo de mapeamento em [config/device_locations.example.json](config/device_locations.example.json)

## Como a skill decide a cidade

Ela tenta nesta ordem:

1. Cidade configurada para o `deviceId` da Alexa em `config/device_locations.json`
2. Endereco do dispositivo via permissao da Alexa
3. Cidade padrao por variaveis de ambiente (`DEFAULT_CITY` ou `DEFAULT_LATITUDE` / `DEFAULT_LONGITUDE`)

## Como vincular a cidade ao id da sua Alexa

1. Faca um teste da skill no Alexa Developer Console ou no dispositivo.
2. Veja os logs do Lambda ou do ambiente hospedado pela Alexa.
3. Procure pela linha `Requisicao recebida para deviceId=...`.
4. Edite `config/device_locations.json` usando esse `deviceId`.

Exemplo:

```json
{
  "amzn1.ask.device.XXXXXXXXXXXX": {
    "city": "Salvador",
    "country_code": "BR",
    "label": "Salvador"
  }
}
```

Se preferir trabalhar com coordenadas:

```json
{
  "amzn1.ask.device.XXXXXXXXXXXX": {
    "latitude": -12.9777,
    "longitude": -38.5016,
    "label": "Salvador"
  }
}
```

## Variaveis de ambiente opcionais

- `DEFAULT_CITY=Salvador`
- `DEFAULT_COUNTRY_CODE=BR`
- `DEFAULT_LATITUDE=-12.9777`
- `DEFAULT_LONGITUDE=-38.5016`
- `DEFAULT_LOCATION_LABEL=Salvador`
- `DEVICE_CITY_MAP_JSON={"amzn1.ask.device.SEUID":{"city":"Salvador","country_code":"BR"}}`
- `HOT_TEMPERATURE_THRESHOLD=23`
- `HOT_TEMPERATURE_COMMAND=python turn_on_office_ac.py`
- `HOT_TEMPERATURE_COMMAND_JSON=["python","turn_on_office_ac.py"]`
- `HOT_TEMPERATURE_COMMAND_TIMEOUT_SECONDS=10`
- `HOT_TEMPERATURE_COOLDOWN_MINUTES=15`
- `MONITOR_DEVICE_IDS=amzn1.ask.device.SEUID`
- `MONITOR_ALL_CONFIGURED_DEVICES=true`
- `MONITOR_INTERVAL_MINUTES=15`
- `HOT_TEMPERATURE_STATE_FILE=state/hot_temperature_state.json`
- `OFFICE_NAME=escritorio`

## Ligar o ar do escritorio acima de 23 graus

Quando a skill consultar o clima e a temperatura atual estiver acima de `HOT_TEMPERATURE_THRESHOLD`, ela executa o comando configurado.

Importante: esse comando roda no mesmo ambiente da skill. Se a skill estiver no AWS Lambda, o comando vai rodar dentro do Lambda, nao no seu dispositivo Echo nem diretamente no seu computador.

Se o comando para ligar o ar so funciona dentro da rede do escritorio ou no seu PC, o melhor caminho e rodar o monitor localmente com [run_temperature_monitor.py](run_temperature_monitor.py) em vez de depender do Lambda.

Opcao simples:

```text
HOT_TEMPERATURE_THRESHOLD=23
HOT_TEMPERATURE_COMMAND=python turn_on_office_ac.py
HOT_TEMPERATURE_COOLDOWN_MINUTES=15
```

Opcao mais segura, sem depender de parsing da linha de comando:

```text
HOT_TEMPERATURE_THRESHOLD=23
HOT_TEMPERATURE_COMMAND_JSON=["python","turn_on_office_ac.py"]
HOT_TEMPERATURE_COOLDOWN_MINUTES=15
```

O comando recebe estas variaveis de ambiente:

- `ALEXA_WEATHER_CITY`
- `ALEXA_WEATHER_LATITUDE`
- `ALEXA_WEATHER_LONGITUDE`
- `ALEXA_WEATHER_TEMPERATURE`
- `ALEXA_WEATHER_APPARENT_TEMPERATURE`
- `ALEXA_WEATHER_HUMIDITY`
- `ALEXA_WEATHER_WIND_SPEED`
- `ALEXA_WEATHER_WEATHER_CODE`
- `ALEXA_WEATHER_THRESHOLD`

O arquivo [turn_on_office_ac.py](turn_on_office_ac.py) foi deixado como exemplo para voce adaptar.

## Modo monitor

O monitor foi pensado para verificar a temperatura sem voce precisar perguntar para a Alexa toda hora. A configuracao padrao agora considera checagem de 15 em 15 minutos.

Ele pode rodar de 2 jeitos:

1. Localmente, chamando [run_temperature_monitor.py](run_temperature_monitor.py)
2. No AWS Lambda, via evento agendado do EventBridge

O monitor resolve as cidades nesta ordem:

1. `MONITOR_DEVICE_IDS`
2. Todos os `deviceId` configurados em `config/device_locations.json`
3. `DEFAULT_CITY` ou coordenadas padrao

Quando a temperatura estiver acima do limite, ele executa o comando configurado e respeita `HOT_TEMPERATURE_COOLDOWN_MINUTES` para nao tentar ligar o ar repetidamente.

### Rodar localmente

Se voce for executar fora do AWS Lambda, use o ambiente virtual do projeto para garantir que o ASK SDK esteja disponivel:

```powershell
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Use este comando:

```powershell
python run_temperature_monitor.py
```

Para deixar rodando continuamente a cada 15 minutos:

```powershell
python run_temperature_monitor.py --loop --interval-minutes 15
```

Se quiser automatizar no Windows sem deixar um terminal aberto, voce pode agendar `python run_temperature_monitor.py` no Agendador de Tarefas para rodar a cada 15 minutos.

### Rodar no Lambda com agendamento

No EventBridge, crie uma regra agendada e aponte para a sua Lambda. O handler ja detecta automaticamente eventos do tipo `Scheduled Event`.

Expressao recomendada:

```text
rate(15 minutes)
```

Voce tambem pode testar manualmente com este payload:

```json
{
  "action": "monitor_temperature"
}
```

Ou monitorar um `deviceId` especifico:

```json
{
  "action": "monitor_temperature",
  "device_id": "amzn1.ask.device.SEUID"
}
```

## Empacotar para teste

Para gerar o `.zip` da Lambda automaticamente:

```powershell
.\build_lambda_package.ps1
```

O pacote sera criado em:

```text
dist\service-controle-temperatura.zip
```

## Publicacao no AWS Lambda

1. Crie e ative um ambiente virtual:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

1. Se preferir fazer manualmente, instale as dependencias em uma pasta de empacotamento:

```powershell
pip install -r requirements.txt -t package
```

1. Copie o codigo da skill e a pasta de configuracao:

```powershell
Copy-Item lambda_function.py package\
Copy-Item run_temperature_monitor.py package\
Copy-Item turn_on_office_ac.py package\
Copy-Item -Recurse config package\config
```

1. Entre na pasta `package`, compacte o conteudo em `.zip` e envie para uma funcao Lambda Python.

1. No Alexa Developer Console:
   - Crie uma Custom Skill
   - Importe o modelo de interacao `interaction-models/pt-BR.json`
   - Aponte o endpoint para a funcao Lambda
   - Ative a permissao de endereco do dispositivo em `Build > Permissions`

## Falas de exemplo

- `Alexa, abrir clima local`
- `Alexa, pedir clima local para verificar o tempo`
- `Alexa, pedir clima local para saber o clima em Salvador`

## API usada para o clima

O projeto consulta a geocodificacao e o clima atual via Open-Meteo, sem necessidade de chave de API.
