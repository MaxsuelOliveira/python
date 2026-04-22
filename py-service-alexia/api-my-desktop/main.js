// Write your code in the same way as for native WebSocket:
const ws = new WebSocket('ws://localhost:8765');
let messagem = null;


ws.addEventListener('open', function (event) {
    // Conexão estabelecida
    document.querySelector("#status").innerHTML = "Servidor ligado";

    document.querySelector("#tempo").addEventListener("click", (e) => {
        e.preventDefault();

        messagem = JSON.stringify({
            function: "tempo",
        });

        ws.send(messagem);
    });

    document.querySelector("#clima").addEventListener("click", (e) => {
        e.preventDefault();

        ws.send(JSON.stringify({
            function: "clima",
        }));
    });

    document.querySelector("#rede_ips").addEventListener("click", (e) => {
        e.preventDefault();

        ws.send(JSON.stringify({
            function: "rede",
        }));
    });


});

//Listen to messages
ws.addEventListener('message', function (event) {
    // Recebendo mensagem do servidor
    let data = JSON.parse(event.data);
    let fun = data.resultado
    let logs = data.logs

    $("#resultado").append(`<span>resultado : ${fun}</span> - <span> log : ${logs}</span>`);
});


ws.onclose = function (e) {
    document.querySelector("#status").innerHTML = "Servidor desligado";
};
