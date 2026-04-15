# py-service-transcrever-audio

Script simples para transcrever audio para texto em portugues usando Vosk e `pydub`.

## Arquivos principais

- `main.py`: converte um MP3 para WAV e processa a transcricao.
- `models/`: pasta esperada para os modelos locais.

## Requisitos

- Python 3.8+
- Dependencias instaladas manualmente no ambiente local
- Modelo Vosk em portugues disponivel localmente

## Uso

```bash
python main.py
```

## Observacao

O script atual espera arquivos locais com nomes fixos e pode precisar de ajustes antes de uso em producao.
