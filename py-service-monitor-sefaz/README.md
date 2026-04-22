# Monitoramento SEFAZ - Disponibilidade de Servicos

Este projeto monitora a tabela de disponibilidade da SEFAZ, persiste a configuracao em SQLite e disponibiliza um painel web simples para administracao do processo.

## Funcionalidades

- Consulta a tabela de disponibilidade da SEFAZ.
- Detecta servicos indisponiveis por UF.
- Envia alerta via Telegram quando houver indisponibilidade.
- Envia alerta opcional via webhook HTTP quando houver indisponibilidade.
- Persiste configuracao em SQLite.
- Mantem historico local dos alertas enviados em SQLite.
- Fornece frontend em HTML + Bootstrap + JavaScript puro.
- Permite salvar configuracao, ativar ou pausar o monitor, executar uma verificacao imediata, reiniciar o processo e proteger o painel com autenticacao simples.

## Requisitos

- Python 3.8+
- Conta no Telegram com bot criado via @BotFather.
- Chat ID obtido via @userinfobot.

## Instalacao

```bash
pip install -r requirements.txt
```

## Variaveis iniciais de ambiente

O arquivo .env continua opcional e agora serve apenas para popular os valores iniciais do banco no primeiro start.

Exemplo:

```env
URL_SEFAZ=https://www.nfe.fazenda.gov.br/portal/disponibilidade.aspx?versao=0.00&tipoConteudo=P2c98tUpxrI=&AspxAutoDetectCookieSupport=1
TELEGRAM_TOKEN=seu_token_aqui
TELEGRAM_CHAT_ID=seu_chat_id_aqui
WEBHOOK_URL=https://seu-endpoint/webhook
PANEL_USERNAME=admin
PANEL_PASSWORD=admin123
SECRET_KEY=troque-esta-chave
```

Depois da primeira execucao, os valores passam a ser mantidos em config.db.

As credenciais padrao sao apenas um bootstrap inicial. Antes de expor o painel fora da maquina local, troque usuario, senha e SECRET_KEY.

## Execucao

```bash
python app.py
```

O servidor sobe em <http://localhost:5000>.

## Estrutura principal

```text
py-service-monitor-sefaz
├── app.py
├── database.py
├── monitor_service.py
├── models/
│   └── get.py
├── static/
│   ├── css/
│   │   └── styles.css
│   └── js/
│       └── app.js
├── templates/
│   └── index.html
├── config.db
└── requirements.txt
```

## Operacao pelo painel

No painel web voce pode:

- editar URL da SEFAZ e credenciais do Telegram;
- configurar uma URL de webhook para receber o payload dos alertas;
- ajustar intervalo de verificacao e timeout HTTP;
- habilitar ou desabilitar monitor, Telegram e webhook;
- consultar historico local dos alertas enviados;
- alterar o usuario e a senha do painel autenticado;
- executar uma verificacao manual imediatamente;
- reiniciar o servidor.

## Payload do webhook

O endpoint esperado e um receptor HTTP que aceite POST com Content-Type application/json.

O schema de referencia tambem fica disponivel autenticado em /api/webhook/schema.

Quando o webhook estiver habilitado e houver indisponibilidade, o sistema envia um POST JSON com a estrutura abaixo:

```json
{
  "event": "sefaz_alert",
  "source": "py-service-monitor-sefaz",
  "generated_at": "2026-04-20T20:00:00+00:00",
  "summary": {
    "message": "<b>🚨 SERVIÇOS INDISPONÍVEIS DETECTADOS</b>\n\n❌ UF - Servico",
    "indisponiveis_count": 1
  },
  "indisponiveis": ["UF - Servico"],
  "status": {}
}
```

## Autenticacao do painel

O painel agora exige login por sessao para acessar a interface e as rotas administrativas.

Fluxo simples:

- acesse /login;
- entre com PANEL_USERNAME e PANEL_PASSWORD;
- depois de autenticado, altere as credenciais pelo proprio painel.

## Historico local de alertas

Cada tentativa de envio para Telegram ou webhook e registrada na tabela alert_history do SQLite com:

- canal;
- destino;
- status de sucesso ou falha;
- codigo de resposta, quando houver;
- mensagem de erro, quando houver;
- quantidade de indisponibilidades;
- payload enviado;
- data e hora do envio.

## Observacoes sobre o restart

O botao de reinicio faz um reexec do processo Python atual. Em ambiente produtivo, o ideal continua sendo executar isso sob um supervisor de processo, como systemd, NSSM, Docker ou outro gerenciador equivalente.

## Licenca

Este projeto e de uso livre e educativo.
