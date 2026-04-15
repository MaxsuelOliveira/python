const socket = new WebSocket("ws://192.168.3.19:8765");

// Evento disparado quando a conexão é aberta
socket.addEventListener("open", (event) => {
  console.log("Conexão WebSocket estabelecida.");
});

// Evento disparado quando uma mensagem é recebida do servidor
socket.addEventListener("message", (event) => {
  callback(event.data);
  console.log("Mensagem recebida do servidor:", event.data);
});

// Evento disparado quando a conexão é fechada
socket.addEventListener("close", (event) => {
  console.log("Conexão WebSocket fechada.");
});

// Evento disparado quando ocorre um erro
socket.addEventListener("error", (event) => {
  console.error("Erro na conexão WebSocket:", event);
});

// Envia uma mensagem para o servidor quando o botão é clicado
document.getElementById("sendButton").addEventListener("click", () => {
  if (socket.readyState === WebSocket.OPEN) {
    socket.send("Olá, servidor!");
  } else {
    console.log("A conexão WebSocket não está aberta.");
  }
});

function callback(mensagem) {
  alert(mensagem);
}
