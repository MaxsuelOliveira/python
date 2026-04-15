import json
import logging
import os
import shlex
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests
from ask_sdk_core.api_client import DefaultApiClient
from ask_sdk_core.dispatch_components import (
    AbstractExceptionHandler,
    AbstractRequestHandler,
)
from ask_sdk_core.skill_builder import CustomSkillBuilder
from ask_sdk_core.utils import is_intent_name, is_request_type
from ask_sdk_model.services import ServiceException
from ask_sdk_model.ui import AskForPermissionsConsentCard, SimpleCard

LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.INFO)

BASE_DIR = Path(__file__).resolve().parent
DEVICE_LOCATIONS_FILE = BASE_DIR / "config" / "device_locations.json"
ADDRESS_PERMISSION = "read::alexa:device:all:address"
DEFAULT_COUNTRY_CODE = os.getenv("DEFAULT_COUNTRY_CODE", "BR")
GEOCODING_URL = os.getenv(
    "OPEN_METEO_GEOCODING_URL",
    "https://geocoding-api.open-meteo.com/v1/search",
)
WEATHER_URL = os.getenv(
    "OPEN_METEO_WEATHER_URL",
    "https://api.open-meteo.com/v1/forecast",
)
HTTP_HEADERS = {"User-Agent": "alexa-weather-monitor/1.0"}
HELP_PROMPT = (
    "Voce pode dizer, por exemplo, como esta o tempo na minha cidade, "
    "ou perguntar como esta o tempo em Salvador."
)
try:
    HOT_TEMPERATURE_THRESHOLD = float(os.getenv("HOT_TEMPERATURE_THRESHOLD", "23"))
except ValueError:
    LOGGER.warning(
        "HOT_TEMPERATURE_THRESHOLD invalido. Usando o valor padrao de 23 graus."
    )
    HOT_TEMPERATURE_THRESHOLD = 23.0

HOT_TEMPERATURE_COMMAND = os.getenv("HOT_TEMPERATURE_COMMAND", "").strip()
HOT_TEMPERATURE_COMMAND_JSON = os.getenv("HOT_TEMPERATURE_COMMAND_JSON", "").strip()

try:
    HOT_TEMPERATURE_COMMAND_TIMEOUT_SECONDS = int(
        os.getenv("HOT_TEMPERATURE_COMMAND_TIMEOUT_SECONDS", "10")
    )
except ValueError:
    LOGGER.warning(
        "HOT_TEMPERATURE_COMMAND_TIMEOUT_SECONDS invalido. Usando 10 segundos."
    )
    HOT_TEMPERATURE_COMMAND_TIMEOUT_SECONDS = 10

try:
    HOT_TEMPERATURE_COOLDOWN_MINUTES = int(
        os.getenv("HOT_TEMPERATURE_COOLDOWN_MINUTES", "15")
    )
except ValueError:
    LOGGER.warning(
        "HOT_TEMPERATURE_COOLDOWN_MINUTES invalido. Usando 15 minutos."
    )
    HOT_TEMPERATURE_COOLDOWN_MINUTES = 15

MONITOR_DEVICE_IDS = os.getenv("MONITOR_DEVICE_IDS", "").strip()
MONITOR_ALL_CONFIGURED_DEVICES = os.getenv(
    "MONITOR_ALL_CONFIGURED_DEVICES",
    "",
).strip().lower() in {"1", "true", "yes", "on"}

STATE_DIR = Path("/tmp") if os.getenv("AWS_EXECUTION_ENV") else BASE_DIR / "state"
HOT_TEMPERATURE_STATE_FILE = Path(
    os.getenv(
        "HOT_TEMPERATURE_STATE_FILE",
        str(STATE_DIR / "hot_temperature_state.json"),
    )
)


@dataclass(frozen=True)
class Location:
    label: str
    latitude: float
    longitude: float


@dataclass(frozen=True)
class WeatherSnapshot:
    temperature: float
    apparent_temperature: float
    humidity: float
    wind_speed: float
    weather_code: int
    temperature_unit: str
    wind_speed_unit: str


class LocationPermissionRequired(Exception):
    """Raised when the skill needs address permission to resolve the location."""


class LocationNotConfigured(Exception):
    """Raised when there is no city configured for the device."""


class WeatherLookupError(Exception):
    """Raised when weather data cannot be fetched or parsed."""


def load_json_file(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}

    try:
        content = path.read_text(encoding="utf-8").strip()
        if not content:
            return {}
        data = json.loads(content)
    except (OSError, json.JSONDecodeError):
        LOGGER.exception("Nao foi possivel ler o arquivo de configuracao: %s", path)
        return {}

    if isinstance(data, dict):
        return data

    LOGGER.warning(
        "Arquivo de configuracao ignorado porque nao contem um objeto JSON: %s",
        path,
    )
    return {}


def load_device_locations() -> Dict[str, Any]:
    locations = load_json_file(DEVICE_LOCATIONS_FILE)
    raw_env = os.getenv("DEVICE_CITY_MAP_JSON", "").strip()
    if not raw_env:
        return locations

    try:
        env_locations = json.loads(raw_env)
    except json.JSONDecodeError:
        LOGGER.exception("A variavel DEVICE_CITY_MAP_JSON nao contem JSON valido.")
        return locations

    if isinstance(env_locations, dict):
        merged = dict(locations)
        merged.update(env_locations)
        return merged

    LOGGER.warning(
        "A variavel DEVICE_CITY_MAP_JSON foi ignorada porque nao contem um objeto JSON."
    )
    return locations


def get_city_slot(handler_input) -> Optional[str]:
    intent = getattr(handler_input.request_envelope.request, "intent", None)
    if intent is None or not intent.slots:
        return None

    city_slot = intent.slots.get("city")
    if not city_slot or not city_slot.value:
        return None

    return city_slot.value.strip()


def get_device_id(handler_input) -> str:
    return handler_input.request_envelope.context.system.device.device_id


def parse_device_ids(raw_value: Any) -> List[str]:
    if isinstance(raw_value, list):
        return [str(item).strip() for item in raw_value if str(item).strip()]

    if isinstance(raw_value, str):
        return [part.strip() for part in raw_value.split(",") if part.strip()]

    return []


def resolve_default_location() -> Optional[Location]:
    latitude = os.getenv("DEFAULT_LATITUDE")
    longitude = os.getenv("DEFAULT_LONGITUDE")
    label = os.getenv("DEFAULT_LOCATION_LABEL") or os.getenv("DEFAULT_CITY") or "sua cidade"

    if latitude and longitude:
        try:
            return Location(label=label, latitude=float(latitude), longitude=float(longitude))
        except ValueError:
            LOGGER.exception("DEFAULT_LATITUDE/DEFAULT_LONGITUDE contem valores invalidos.")

    default_city = os.getenv("DEFAULT_CITY", "").strip()
    if default_city:
        return geocode_location(
            default_city,
            country_code=DEFAULT_COUNTRY_CODE,
            label_override=label,
        )

    return None


def resolve_location_from_mapping(device_id: str) -> Optional[Location]:
    locations = load_device_locations()
    mapping = locations.get(device_id)
    if mapping is None:
        return None

    if isinstance(mapping, str):
        return geocode_location(
            mapping,
            country_code=DEFAULT_COUNTRY_CODE,
            label_override=mapping,
        )

    if not isinstance(mapping, dict):
        LOGGER.warning(
            "Configuracao ignorada para o deviceId %s porque nao e valida.",
            device_id,
        )
        return None

    label = str(
        mapping.get("label")
        or mapping.get("city")
        or mapping.get("postal_code")
        or "sua cidade"
    )
    latitude = mapping.get("latitude")
    longitude = mapping.get("longitude")
    if latitude is not None and longitude is not None:
        try:
            return Location(label=label, latitude=float(latitude), longitude=float(longitude))
        except ValueError:
            LOGGER.exception(
                "Latitude/longitude invalidas na configuracao do deviceId %s.",
                device_id,
            )

    search_query = mapping.get("city") or mapping.get("postal_code") or mapping.get("query")
    if not search_query:
        LOGGER.warning(
            "Nenhuma cidade ou coordenada foi informada para o deviceId %s.",
            device_id,
        )
        return None

    country_code = str(mapping.get("country_code") or DEFAULT_COUNTRY_CODE)
    return geocode_location(
        str(search_query),
        country_code=country_code,
        label_override=label,
    )


def resolve_location_from_device_address(handler_input, device_id: str) -> Optional[Location]:
    permissions = getattr(handler_input.request_envelope.context.system.user, "permissions", None)
    consent_token = getattr(permissions, "consent_token", None)
    if not consent_token:
        raise LocationPermissionRequired

    try:
        address_client = handler_input.service_client_factory.get_device_address_service()
        address = address_client.get_full_address(device_id)
    except ServiceException:
        LOGGER.exception("Falha ao consultar o endereco do dispositivo %s.", device_id)
        return None

    search_query = address.city or address.postal_code
    if not search_query:
        return None

    label = address.city or "sua regiao"
    country_code = address.country_code or DEFAULT_COUNTRY_CODE
    return geocode_location(
        search_query,
        country_code=country_code,
        label_override=label,
    )


def resolve_location(handler_input, requested_city: Optional[str]) -> Location:
    if requested_city:
        return geocode_location(
            requested_city,
            country_code=DEFAULT_COUNTRY_CODE,
            label_override=requested_city,
        )

    device_id = get_device_id(handler_input)
    LOGGER.info("Requisicao recebida para deviceId=%s", device_id)

    mapped_location = resolve_location_from_mapping(device_id)
    if mapped_location:
        return mapped_location

    permission_required = False
    try:
        address_location = resolve_location_from_device_address(handler_input, device_id)
    except LocationPermissionRequired:
        permission_required = True
    else:
        if address_location:
            return address_location

    default_location = resolve_default_location()
    if default_location:
        return default_location

    if permission_required:
        raise LocationPermissionRequired

    raise LocationNotConfigured(
        "Eu ainda nao sei qual cidade devo monitorar para esse dispositivo. "
        "Configure o arquivo config/device_locations.json com o deviceId da sua Alexa."
    )


def geocode_location(
    query: str,
    *,
    country_code: Optional[str],
    label_override: Optional[str] = None,
) -> Location:
    params = {
        "name": query,
        "count": 1,
        "language": "pt",
        "format": "json",
    }
    if country_code:
        params["countryCode"] = country_code

    try:
        response = requests.get(
            GEOCODING_URL,
            params=params,
            headers=HTTP_HEADERS,
            timeout=10,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        raise WeatherLookupError("Nao consegui localizar essa cidade agora.") from exc

    payload = response.json()
    results = payload.get("results") or []
    if not results:
        raise WeatherLookupError(f"Nao encontrei a localizacao para {query}.")

    result = results[0]
    latitude = result.get("latitude")
    longitude = result.get("longitude")
    if latitude is None or longitude is None:
        raise WeatherLookupError(f"A localizacao para {query} veio incompleta.")

    label = label_override or build_location_label(result)
    return Location(label=label, latitude=float(latitude), longitude=float(longitude))


def build_location_label(result: Dict[str, Any]) -> str:
    name = result.get("name") or "sua cidade"
    region = result.get("admin1")
    if region and region.lower() not in str(name).lower():
        return f"{name}, {region}"
    return str(name)


def load_monitor_state() -> Dict[str, Any]:
    return load_json_file(HOT_TEMPERATURE_STATE_FILE)


def save_monitor_state(state: Dict[str, Any]) -> None:
    try:
        HOT_TEMPERATURE_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        HOT_TEMPERATURE_STATE_FILE.write_text(
            json.dumps(state, indent=2, sort_keys=True),
            encoding="utf-8",
        )
    except OSError:
        LOGGER.exception(
            "Nao foi possivel salvar o estado do monitor em %s.",
            HOT_TEMPERATURE_STATE_FILE,
        )


def build_monitor_state_key(target_id: str, location: Location) -> str:
    return (
        f"{target_id}|{location.label}|"
        f"{location.latitude:.4f}|{location.longitude:.4f}"
    )


def is_monitor_event(event: Any) -> bool:
    if not isinstance(event, dict):
        return False

    return (
        event.get("action") == "monitor_temperature"
        or event.get("monitor") is True
        or event.get("source") == "aws.events"
        or event.get("detail-type") == "Scheduled Event"
    )


def resolve_monitor_targets(event: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    event = event or {}
    configured_locations = load_device_locations()
    requested_device_ids = parse_device_ids(event.get("device_ids"))
    if not requested_device_ids and event.get("device_id"):
        requested_device_ids = [str(event["device_id"]).strip()]

    env_device_ids = parse_device_ids(MONITOR_DEVICE_IDS)
    device_ids = requested_device_ids or env_device_ids

    monitor_all_configured = bool(configured_locations) and (
        event.get("all_configured_devices") is True
        or MONITOR_ALL_CONFIGURED_DEVICES
        or not device_ids
    )

    targets: List[Dict[str, Any]] = []
    selected_ids = device_ids or (
        list(configured_locations.keys()) if monitor_all_configured else []
    )

    for device_id in selected_ids:
        location = resolve_location_from_mapping(device_id)
        if not location:
            LOGGER.warning(
                "O monitor ignorou o deviceId %s porque nao encontrou uma localizacao valida.",
                device_id,
            )
            continue

        targets.append(
            {
                "target_id": device_id,
                "target_type": "device_id",
                "location": location,
            }
        )

    if targets:
        return targets

    default_location = resolve_default_location()
    if default_location:
        return [
            {
                "target_id": "default",
                "target_type": "default",
                "location": default_location,
            }
        ]

    raise LocationNotConfigured(
        "O monitor nao encontrou nenhuma cidade configurada. "
        "Defina MONITOR_DEVICE_IDS, preencha config/device_locations.json "
        "ou configure DEFAULT_CITY."
    )


def parse_hot_temperature_command() -> Optional[List[str]]:
    if HOT_TEMPERATURE_COMMAND_JSON:
        try:
            raw_command = json.loads(HOT_TEMPERATURE_COMMAND_JSON)
        except json.JSONDecodeError:
            LOGGER.exception("HOT_TEMPERATURE_COMMAND_JSON nao contem JSON valido.")
            return None

        if not isinstance(raw_command, list) or not raw_command:
            LOGGER.warning(
                "HOT_TEMPERATURE_COMMAND_JSON foi ignorado porque nao contem uma lista."
            )
            return None

        return [str(item) for item in raw_command]

    if not HOT_TEMPERATURE_COMMAND:
        return None

    return shlex.split(HOT_TEMPERATURE_COMMAND, posix=os.name != "nt")


def execute_hot_temperature_command(
    location: Location,
    weather: WeatherSnapshot,
    *,
    trigger_source: str,
    state_key: Optional[str] = None,
    enforce_cooldown: bool = False,
) -> Dict[str, Any]:
    if weather.temperature <= HOT_TEMPERATURE_THRESHOLD:
        return {
            "executed": False,
            "reason": "below_threshold",
            "temperature": weather.temperature,
        }

    command = parse_hot_temperature_command()
    if not command:
        LOGGER.info(
            "Temperatura acima do limite, mas nenhum comando foi configurado. "
            "Cidade=%s temperatura=%s limite=%s",
            location.label,
            weather.temperature,
            HOT_TEMPERATURE_THRESHOLD,
        )
        return {
            "executed": False,
            "reason": "command_not_configured",
            "temperature": weather.temperature,
        }

    if enforce_cooldown and state_key and HOT_TEMPERATURE_COOLDOWN_MINUTES > 0:
        monitor_state = load_monitor_state()
        last_entry = monitor_state.get(state_key, {})
        last_executed_at = last_entry.get("last_executed_at")
        if isinstance(last_executed_at, (int, float)):
            cooldown_seconds = HOT_TEMPERATURE_COOLDOWN_MINUTES * 60
            elapsed_seconds = time.time() - float(last_executed_at)
            if elapsed_seconds < cooldown_seconds:
                LOGGER.info(
                    "Comando ignorado por cooldown. source=%s target=%s restante=%s",
                    trigger_source,
                    state_key,
                    int(cooldown_seconds - elapsed_seconds),
                )
                return {
                    "executed": False,
                    "reason": "cooldown_active",
                    "temperature": weather.temperature,
                    "cooldown_minutes": HOT_TEMPERATURE_COOLDOWN_MINUTES,
                }

    command_env = os.environ.copy()
    command_env.update(
        {
            "ALEXA_WEATHER_CITY": location.label,
            "ALEXA_WEATHER_LATITUDE": str(location.latitude),
            "ALEXA_WEATHER_LONGITUDE": str(location.longitude),
            "ALEXA_WEATHER_TEMPERATURE": str(weather.temperature),
            "ALEXA_WEATHER_APPARENT_TEMPERATURE": str(weather.apparent_temperature),
            "ALEXA_WEATHER_HUMIDITY": str(weather.humidity),
            "ALEXA_WEATHER_WIND_SPEED": str(weather.wind_speed),
            "ALEXA_WEATHER_WEATHER_CODE": str(weather.weather_code),
            "ALEXA_WEATHER_THRESHOLD": str(HOT_TEMPERATURE_THRESHOLD),
        }
    )

    try:
        result = subprocess.run(
            command,
            cwd=str(BASE_DIR),
            env=command_env,
            capture_output=True,
            text=True,
            timeout=HOT_TEMPERATURE_COMMAND_TIMEOUT_SECONDS,
            check=False,
        )
    except subprocess.TimeoutExpired:
        LOGGER.exception(
            "O comando de temperatura excedeu o tempo limite de %s segundos.",
            HOT_TEMPERATURE_COMMAND_TIMEOUT_SECONDS,
        )
        return {
            "executed": False,
            "reason": "command_timeout",
            "temperature": weather.temperature,
        }
    except OSError:
        LOGGER.exception("Nao foi possivel executar o comando de temperatura.")
        return {
            "executed": False,
            "reason": "command_os_error",
            "temperature": weather.temperature,
        }

    LOGGER.info(
        "Comando de temperatura executado. rc=%s stdout=%s stderr=%s",
        result.returncode,
        (result.stdout or "").strip(),
        (result.stderr or "").strip(),
    )
    executed = result.returncode == 0

    if executed and enforce_cooldown and state_key:
        monitor_state = load_monitor_state()
        monitor_state[state_key] = {
            "last_executed_at": time.time(),
            "location": location.label,
            "temperature": weather.temperature,
        }
        save_monitor_state(monitor_state)

    return {
        "executed": executed,
        "reason": "executed" if executed else "command_failed",
        "return_code": result.returncode,
        "stdout": (result.stdout or "").strip(),
        "stderr": (result.stderr or "").strip(),
        "temperature": weather.temperature,
    }


def run_temperature_monitor(event: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    event = event or {}

    try:
        targets = resolve_monitor_targets(event)
    except LocationNotConfigured as exc:
        LOGGER.exception("Falha ao resolver os alvos do monitor.")
        return {
            "ok": False,
            "error": str(exc),
            "threshold": HOT_TEMPERATURE_THRESHOLD,
        }

    results: List[Dict[str, Any]] = []
    overall_ok = True

    for target in targets:
        target_id = str(target["target_id"])
        location = target["location"]
        state_key = build_monitor_state_key(target_id, location)

        try:
            weather = fetch_weather(location)
            command_result = execute_hot_temperature_command(
                location,
                weather,
                trigger_source="monitor",
                state_key=state_key,
                enforce_cooldown=True,
            )
            result_item = {
                "target_id": target_id,
                "target_type": target["target_type"],
                "location": location.label,
                "temperature": weather.temperature,
                "threshold": HOT_TEMPERATURE_THRESHOLD,
                "command": command_result,
            }
        except WeatherLookupError as exc:
            overall_ok = False
            result_item = {
                "target_id": target_id,
                "target_type": target["target_type"],
                "location": location.label,
                "error": str(exc),
            }
        except Exception as exc:
            overall_ok = False
            LOGGER.exception("Erro inesperado no monitor para o alvo %s.", target_id)
            result_item = {
                "target_id": target_id,
                "target_type": target["target_type"],
                "location": location.label,
                "error": f"Erro inesperado: {exc}",
            }

        LOGGER.info("Resultado do monitor: %s", result_item)
        results.append(result_item)

    return {
        "ok": overall_ok,
        "monitor": True,
        "threshold": HOT_TEMPERATURE_THRESHOLD,
        "cooldown_minutes": HOT_TEMPERATURE_COOLDOWN_MINUTES,
        "results": results,
    }


def fetch_weather(location: Location) -> WeatherSnapshot:
    params = {
        "latitude": location.latitude,
        "longitude": location.longitude,
        "current": (
            "temperature_2m,apparent_temperature,relative_humidity_2m,"
            "weather_code,wind_speed_10m"
        ),
        "timezone": "auto",
        "forecast_days": 1,
    }

    try:
        response = requests.get(
            WEATHER_URL,
            params=params,
            headers=HTTP_HEADERS,
            timeout=10,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        raise WeatherLookupError("Nao consegui consultar o clima agora.") from exc

    payload = response.json()
    current = payload.get("current") or {}
    current_units = payload.get("current_units") or {}
    required_fields = (
        "temperature_2m",
        "apparent_temperature",
        "relative_humidity_2m",
        "weather_code",
        "wind_speed_10m",
    )
    if any(field not in current for field in required_fields):
        raise WeatherLookupError("A resposta do servico de clima veio incompleta.")

    return WeatherSnapshot(
        temperature=float(current["temperature_2m"]),
        apparent_temperature=float(current["apparent_temperature"]),
        humidity=float(current["relative_humidity_2m"]),
        wind_speed=float(current["wind_speed_10m"]),
        weather_code=int(current["weather_code"]),
        temperature_unit=str(current_units.get("temperature_2m", "C")).replace("\xb0", ""),
        wind_speed_unit=str(current_units.get("wind_speed_10m", "km/h")),
    )


def describe_weather_code(weather_code: int) -> str:
    descriptions = {
        0: "ceu limpo",
        1: "ceu quase limpo",
        2: "parcialmente nublado",
        3: "nublado",
        45: "nevoeiro",
        48: "nevoeiro com geada",
        51: "garoa fraca",
        53: "garoa moderada",
        55: "garoa intensa",
        56: "garoa congelante fraca",
        57: "garoa congelante intensa",
        61: "chuva fraca",
        63: "chuva moderada",
        65: "chuva forte",
        66: "chuva congelante fraca",
        67: "chuva congelante forte",
        71: "neve fraca",
        73: "neve moderada",
        75: "neve forte",
        77: "graos de neve",
        80: "pancadas de chuva fracas",
        81: "pancadas de chuva moderadas",
        82: "pancadas de chuva fortes",
        85: "pancadas de neve fracas",
        86: "pancadas de neve fortes",
        95: "trovoadas",
        96: "trovoadas com granizo fraco",
        99: "trovoadas com granizo forte",
    }
    return descriptions.get(weather_code, "condicao indefinida")


def format_measurement(value: float) -> str:
    return str(int(round(value)))


def build_weather_speech(location: Location, weather: WeatherSnapshot) -> str:
    temperature = format_measurement(weather.temperature)
    apparent = format_measurement(weather.apparent_temperature)
    humidity = format_measurement(weather.humidity)
    wind = format_measurement(weather.wind_speed)
    condition = describe_weather_code(weather.weather_code)
    unit = {
        "C": "Celsius",
        "F": "Fahrenheit",
    }.get(weather.temperature_unit or "C", weather.temperature_unit)

    return (
        f"Agora em {location.label} esta fazendo {temperature} graus {unit}, "
        f"com sensacao termica de {apparent} graus. "
        f"O tempo esta com {condition}, umidade de {humidity} por cento "
        f"e vento em {wind} {weather.wind_speed_unit}."
    )


class LaunchRequestHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        return is_request_type("LaunchRequest")(handler_input)

    def handle(self, handler_input):
        speech = (
            "Sua skill de clima esta pronta. "
            "Eu posso consultar o tempo da cidade vinculada a esta Alexa."
        )
        return (
            handler_input.response_builder
            .speak(speech)
            .ask(HELP_PROMPT)
            .set_card(SimpleCard("Skill de Clima", speech))
            .response
        )


class CurrentWeatherIntentHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        return is_intent_name("CurrentWeatherIntent")(handler_input)

    def handle(self, handler_input):
        requested_city = get_city_slot(handler_input)

        try:
            location = resolve_location(handler_input, requested_city)
            weather = fetch_weather(location)
            execute_hot_temperature_command(
                location,
                weather,
                trigger_source="voice",
            )
        except LocationPermissionRequired:
            speech = (
                "Para descobrir o clima usando a localizacao da sua Alexa, "
                "eu preciso da permissao de endereco no aplicativo Alexa."
            )
            return (
                handler_input.response_builder
                .speak(speech)
                .ask("Abra o app Alexa e autorize o acesso ao endereco do dispositivo.")
                .set_card(AskForPermissionsConsentCard(permissions=[ADDRESS_PERMISSION]))
                .response
            )
        except LocationNotConfigured as exc:
            return (
                handler_input.response_builder
                .speak(str(exc))
                .ask(HELP_PROMPT)
                .response
            )
        except WeatherLookupError as exc:
            LOGGER.exception("Falha ao buscar o clima.")
            return (
                handler_input.response_builder
                .speak(str(exc))
                .ask("Tente novamente em alguns instantes.")
                .response
            )

        speech = build_weather_speech(location, weather)
        return (
            handler_input.response_builder
            .speak(speech)
            .ask("Se quiser, eu tambem posso consultar outra cidade.")
            .set_card(SimpleCard(f"Clima em {location.label}", speech))
            .response
        )


class HelpIntentHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        return is_intent_name("AMAZON.HelpIntent")(handler_input)

    def handle(self, handler_input):
        return (
            handler_input.response_builder
            .speak(HELP_PROMPT)
            .ask(HELP_PROMPT)
            .response
        )


class CancelOrStopIntentHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        return (
            is_intent_name("AMAZON.CancelIntent")(handler_input)
            or is_intent_name("AMAZON.StopIntent")(handler_input)
            or is_intent_name("AMAZON.NavigateHomeIntent")(handler_input)
        )

    def handle(self, handler_input):
        return handler_input.response_builder.speak("Tudo bem. Ate mais.").response


class FallbackIntentHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        return is_intent_name("AMAZON.FallbackIntent")(handler_input)

    def handle(self, handler_input):
        speech = (
            "Eu nao entendi esse pedido. "
            "Tente dizer: como esta o tempo na minha cidade."
        )
        return handler_input.response_builder.speak(speech).ask(HELP_PROMPT).response


class SessionEndedRequestHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        return is_request_type("SessionEndedRequest")(handler_input)

    def handle(self, handler_input):
        return handler_input.response_builder.response


class CatchAllExceptionHandler(AbstractExceptionHandler):
    def can_handle(self, handler_input, exception):
        return True

    def handle(self, handler_input, exception):
        LOGGER.exception("Erro nao tratado: %s", exception)
        speech = "Ocorreu um problema ao processar sua solicitacao. Tente novamente."
        return handler_input.response_builder.speak(speech).ask(HELP_PROMPT).response


skill_builder = CustomSkillBuilder(api_client=DefaultApiClient())
skill_builder.add_request_handler(LaunchRequestHandler())
skill_builder.add_request_handler(CurrentWeatherIntentHandler())
skill_builder.add_request_handler(HelpIntentHandler())
skill_builder.add_request_handler(CancelOrStopIntentHandler())
skill_builder.add_request_handler(FallbackIntentHandler())
skill_builder.add_request_handler(SessionEndedRequestHandler())
skill_builder.add_exception_handler(CatchAllExceptionHandler())

ask_lambda_handler = skill_builder.lambda_handler()


def lambda_handler(event, context):
    if is_monitor_event(event):
        return run_temperature_monitor(event)

    return ask_lambda_handler(event, context)
