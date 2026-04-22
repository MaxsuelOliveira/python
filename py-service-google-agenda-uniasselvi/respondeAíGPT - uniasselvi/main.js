const APIKEY = window.APP_CONFIG?.OPENAI_API_KEY || "";

let resultado = document.querySelector("#texto_para_buscar");

window.addEventListener("DOMContentLoaded", (event) => {
  event.preventDefault();
  console.log("Carregou !");
});

async function gpt(question) {
  if (!APIKEY) {
    console.error(
      "Defina OPENAI_API_KEY em config.js antes de usar este frontend.",
    );
    return;
  }

  fetch("https://api.openai.com/v1/chat/completions", {
    method: "POST",

    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
      Authorization: `Bearer ${APIKEY}`,
    },

    body: JSON.stringify({
      model: "text-davinci-003",
      prompt: question,
    }),
  })
    .then((response) => response.json())
    .then((data) => console.log(data))
    .catch((error) => console.error(error));
}

function getPergunta() {
  const question = document.querySelector("#cdk-step-content-0-0");

  if (question) {
    const question_pergunta = document.querySelector(
      "#cdk-step-content-0-0 > span",
    ).textContent;

    const question_alternativa = document.querySelector(
      "#cdk-step-content-0-0 > div.alternative-container.row.mt-3.ng-star-inserted",
    ).textContent;

    return gpt("Olá mundo em python !");
  }

  console.log("Não achei nenhuma pergunta !");
  console.log("Deseja selecionar o texto manualmente ?");
}

function selecionarTextoManualmente() {
  alert("Precionse CTRL, depois mova o mouse até o texto, realize o clique !");

  document.onkeyup = function (e) {
    if (e.which == 17) {
      document.onclick = function (event) {
        event.preventDefault();

        // Verificar se o alvo do clique é um <p>, <span> ou <b>
        if (
          event.target.tagName === "P" ||
          event.target.tagName === "SPAN" ||
          event.target.tagName === "B"
        ) {
          resultado.textContent = +event.target.textContent;

          console.log(resultado.textContent);
        }
      };
    }
  };
}
