const socket = new WebSocket('ws://localhost:5000');

socket.addEventListener('open', (event) => {
  console.log('Conexão aberta:', event);

  // Envia uma mensagem para o servidor
  socket.send('Olá, sou o cliente!');
});

socket.addEventListener('message', (event) => {
  console.log('Mensagem recebida:', event);

  // Recebe a resposta do servidor e exibe no console
  console.log('Resposta do servidor:', event.data);
});

socket.addEventListener('close', (event) => {
  console.log('Conexão fechada:', event);
});