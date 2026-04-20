# Environment Monitor

Projeto completo para monitoramento de ambiente com câmera, detecção por YOLO, regras configuráveis, painel React e disparo de alertas.

## O que está incluído

- **Backend FastAPI** com:
  - captura de webcam/RTSP/vídeo local
  - inferência com **YOLO (Ultralytics)**
  - regras em JSON
  - persistência de eventos em SQLite
  - snapshots automáticos
  - ações: WebSocket, webhook, Slack, Telegram e email
- **Frontend React + Vite** com:
  - dashboard ao vivo
  - editor de regras
  - editor visual de zonas com arrastar e redimensionar
  - tela de configurações
  - tela de alertas / teste de integrações
  - histórico de eventos

## Estrutura

```text
env-monitor/
  backend/
    app.py
    requirements.txt
    data/
      rules.json
      settings.json
    snapshots/
  frontend/
    package.json
    vite.config.js
    src/
  README.md
```

## Requisitos

### Backend
- Python 3.10+
- Webcam local, stream RTSP ou arquivo de vídeo

### Frontend
- Node.js 18+
- npm 9+

## Instalação

### 1. Backend

```bash
cd backend
python -m venv .venv
```

#### Windows PowerShell

```powershell
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

#### Linux / macOS

```bash
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Frontend

```bash
cd ../frontend
npm install
```

## Execução

### Backend

```bash
cd backend
python app.py --host 0.0.0.0 --port 8000
```

A API ficará disponível em:

- `http://127.0.0.1:8000/health`
- `http://127.0.0.1:8000/api/state`
- `ws://127.0.0.1:8000/ws`

### Frontend

```bash
cd frontend
npm run dev
```

Painel web:

- `http://127.0.0.1:5173`

O Vite já está configurado para fazer proxy do frontend para o backend em `localhost:8000`.

---

## Configuração inicial

### Fonte da câmera

Edite `backend/data/settings.json`:

```json
{
  "camera": {
    "source": "0"
  }
}
```

Exemplos:

- Webcam padrão: `"0"`
- Outra webcam: `"1"`
- RTSP: `"rtsp://usuario:senha@ip:554/stream"`
- Arquivo: `"video.mp4"`

### Modelo YOLO

Por padrão:

```json
"path": "yolov8n.pt"
```

Você pode trocar por outro checkpoint compatível, por exemplo:

- `yolov8s.pt`
- `yolov8m.pt`
- modelo customizado treinado por você

### Classes monitoradas

No `settings.json`:

```json
"classes": ["person", "dog", "cat", "couch", "chair", "bed", "bird"]
```

Se quiser focar apenas no cachorro e reduzir ruído:

```json
"classes": ["dog", "person", "couch"]
```

---

## Regras

As regras ficam em `backend/data/rules.json`.

### Exemplo: cachorro no sofá

```json
{
  "id": "dog_on_sofa",
  "name": "Cachorro no sofá",
  "enabled": true,
  "cooldown_seconds": 30,
  "condition": {
    "type": "object_in_zone",
    "object": "dog",
    "zone_id": "sofa_area",
    "min_confidence": 0.4,
    "min_overlap": 0.15,
    "for_frames": 5
  },
  "actions": [
    { "type": "websocket" },
    { "type": "snapshot" }
  ]
}
```

### Exemplo: quarto sem ninguém

```json
{
  "id": "room_without_person",
  "name": "Quarto sem ninguém",
  "enabled": true,
  "cooldown_seconds": 60,
  "condition": {
    "type": "object_absent",
    "object": "person",
    "zone_id": "room_area",
    "min_confidence": 0.35,
    "for_seconds": 20
  },
  "actions": [
    { "type": "websocket" },
    { "type": "snapshot" }
  ]
}
```

### Tipos de condição suportados

- `object_present`
- `object_in_zone`
- `object_absent`
- `overlap`

### Zonas

As zonas são normalizadas entre `0` e `1`.

```json
{
  "id": "sofa_area",
  "name": "Sofá",
  "shape": "rect",
  "x": 0.45,
  "y": 0.45,
  "w": 0.45,
  "h": 0.40
}
```

---

## Actions / alertas

As actions ficam dentro de cada regra.

### WebSocket

```json
{ "type": "websocket" }
```

### Snapshot

```json
{ "type": "snapshot" }
```

### Webhook HTTP

```json
{ "type": "webhook", "enabled": true, "url": "https://seu-endpoint/webhook" }
```

### Slack

```json
{ "type": "slack", "enabled": true, "webhook_url": "https://hooks.slack.com/services/..." }
```

### Telegram

```json
{ "type": "telegram", "enabled": true, "bot_token": "SEU_TOKEN", "chat_id": "SEU_CHAT_ID" }
```

### Email

```json
{
  "type": "email",
  "enabled": true,
  "smtp_host": "smtp.gmail.com",
  "smtp_port": 587,
  "username": "seu@email.com",
  "password": "sua_senha_ou_app_password",
  "from_email": "seu@email.com",
  "to": ["destino@email.com"]
}
```

---

## Endpoints principais

### Saúde

```http
GET /health
```

### Estado atual

```http
GET /api/state
```

### Configurações

```http
GET /api/settings
PUT /api/settings
```

### Regras

```http
GET /api/rules
PUT /api/rules
```

### Zonas

```http
GET /api/zones
PUT /api/zones
```

### Eventos

```http
GET /api/events?limit=100
```

### Snapshots

```http
GET /api/snapshots/{filename}
```

### Teste de alerta

```http
POST /api/alerts/test
```

### WebSocket

```text
/ws
```

Mensagens emitidas:

- `type: state`
- `type: event`

---

## Fluxo recomendado de teste

1. Inicie o backend.
2. Inicie o frontend.
3. Abra o painel web.
4. Ajuste `settings.json` ou use a tela de Configurações.
5. Abra a tela de Zonas, congele mentalmente o frame atual e ajuste a zona do sofá arrastando e redimensionando a área visual.
6. Habilite a regra `dog_on_sofa`.
7. Vá para o dashboard e verifique se a câmera está ativa.
8. Faça um teste de alerta pela tela de Alertas.

---

## Melhorias futuras já preparadas pela arquitetura

- importação/exportação de zonas e regras
- autenticação
- múltiplas câmeras
- fila de eventos com retry robusto
- gravação de vídeo por evento
- treinamento de modelo customizado com fotos do seu cachorro
- classificação secundária para reduzir falsos positivos
- detector específico do seu sofá / cama / áreas internas

---

## Observações técnicas

- O backend recarrega `settings.json` e `rules.json` automaticamente durante a execução.
- Os eventos são persistidos em SQLite (`backend/data/events.db`).
- Os snapshots são salvos em `backend/snapshots/`.
- A UI foi feita para ser simples, limpa e já utilizável, mas é uma base inicial de produto.

---

## Solução para o problema de falso positivo do cachorro

Se o YOLO ainda confundir seu cachorro com outro animal em alguns casos, a ordem recomendada é:

1. reduzir classes monitoradas
2. aumentar `min_confidence`
3. usar zona de sofá mais precisa
4. aumentar `for_frames`
5. trocar para um modelo mais forte (`yolov8s.pt` / `yolov8m.pt`)
6. treinar um modelo customizado com imagens do seu ambiente

---

## Licença / uso

Base livre para adaptação no seu projeto.
