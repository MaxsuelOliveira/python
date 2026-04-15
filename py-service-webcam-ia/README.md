# Detector de cachorro com OpenCV + WebSocket

Este projeto detecta cães em imagens usando OpenCV (MobileNet-SSD) e envia
uma notificação via WebSocket quando um cachorro é encontrado.

Requisitos
- Python 3.8+
- Instalar dependências:

  pip install -r requirements.txt

Uso

  python main.py --images picture/ --ws ws://localhost:8765 --conf 0.5

Explicação breve
- O detector usa MobileNet-SSD (Caffe). Se os arquivos do modelo não existirem
  na pasta `models/`, eles serão baixados automaticamente.
- Ao detectar um cachorro, o programa envia um JSON ao WebSocket com a forma:

  {"event":"dog_detected","image":"nome.jpg","confidence":0.87}

Notas
- Você precisa de um servidor WebSocket escutando no endereço informado para
  receber as notificações (por exemplo, um servidor simples com `websockets`)
