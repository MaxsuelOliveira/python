# 🛰️ Monitoramento SEFAZ - Disponibilidade de Serviços

Este projeto realiza a consulta automática da tabela de disponibilidade da SEFAZ (Nota Fiscal Eletrônica) e envia alertas via Telegram caso algum serviço esteja indisponível.

## 🔧 Funcionalidades

- Consulta a tabela de disponibilidade da SEFAZ (NFe).
- Converte a tabela HTML em JSON estruturado.
- Verifica estados com serviços indisponíveis.
- Envia notificação automática via Telegram.

## 📦 Requisitos

- Python 3.8+
- Conta no Telegram com bot criado via [@BotFather](https://t.me/BotFather)
- Chat ID obtido via [@userinfobot](https://t.me/userinfobot)

### Instale as dependências

```bash
pip install -r requirements.txt
```

## 📁 Estrutura esperada

py_monitor_sefaz
    ├── get.py
    ├── main.py
    ├── .env
    ├── README.md
    └── requirements.txt

## 🧪 Variáveis de ambiente (.env)

Crie um arquivo .env com o seguinte conteúdo:

```env
URL_SEFAZ=https://www.nfe.fazenda.gov.br/portal/disponibilidade.aspx?versao=0.00&tipoConteudo=P2c98tUpxrI=
TELEGRAM_TOKEN=seu_token_aqui
TELEGRAM_CHAT_ID=seu_chat_id_aqui
```

## 🚀 Como executar

```bash
python main.py
```

### Rodando como serviço / agendador

Recomenda-se executar o monitor como um serviço/scheduled job em produção. Antes de configurar, crie um arquivo `.env` local baseado em `.env.exemple` e NÃO o comite no repositório.

Exemplo: criar `.env` localmente com os valores reais (não commitar):

```bash
cp .env.exemple .env
# editar .env e preencher TELEGRAM_TOKEN/TELEGRAM_CHAT_ID
```

Systemd (Linux) - exemplo de unit file `/etc/systemd/system/sefaz_monitor.service`:

```ini
[Unit]
Description=Monitor SEFAZ
After=network.target

[Service]
Type=simple
WorkingDirectory=/caminho/para/py_monitor_sefaz
ExecStart=/usr/bin/python3 /caminho/para/py_monitor_sefaz/main.py
Restart=on-failure
EnvironmentFile=/caminho/para/py_monitor_sefaz/.env

[Install]
WantedBy=multi-user.target
```

Depois de criar a unit:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now sefaz_monitor.service
sudo journalctl -u sefaz_monitor -f
```

Agendamento com cron (alternativa simples):

```cron
# editar crontab com: crontab -e
# exemplo: executar a cada 5 minutos
*/5 * * * * cd /caminho/para/py_monitor_sefaz && /usr/bin/python3 main.py >> monitor.log 2>&1
```

Windows Task Scheduler (resumo):

1. Abra o Task Scheduler > Create Task
2. Em Actions, aponte o programa para o executável Python e em Arguments coloque o caminho para `main.py`
3. Em Triggers, defina o agendamento (ex: a cada 5 minutos usando um trigger repetido)

## 📬 Exemplo de alerta no Telegram

🚨 SERVIÇOS INDISPONÍVEIS DETECTADOS</br>

❌ BA - Status Serviço4 </br>
❌ SP - Consulta Cadastro4</br>

## 🛡️ Licença

Este projeto é de uso livre e educativo.
