document.querySelector("form").addEventListener("submit", function (event) {
    event.preventDefault();

    let comando = 2212121;
    let resultado = "sucesso";
    let msg_error = null;

    document.querySelector(".resultado").innerHTML = `<div>
        <span>
           ${comando}
        </span>
        <span>
            ${resultado}
        </span>
        <span>${msg_error}</span>
    </div>`
});