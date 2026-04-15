let info, questions;
const url_get = "https://api-ava.uniasselvi.com.br/test/question/get";

const url_informations = "";

const token = window.APP_CONFIG?.UNIASSELVI_BEARER_TOKEN || "";

// Criar modais =>

let form = document.querySelector("form");
form.addEventListener("submit", function (e) {
  e.preventDefault();
  console.log(e);

  specialization = form[0].value;
  testCode = form[1].value;
  examCode = form[2].value;
  semester = form[3].value;
  subjectCode = form[4].value;
  classCode = form[5].value;

  // get("3524024", "768957", "51813472", "2022/2", "ADS16", "5550ADS");
  get(specialization, testCode, examCode, semester, subjectCode, classCode);
});

function get(
  specialization,
  testCode,
  examCode,
  semester,
  subjectCode,
  classCode,
) {
  if (!token) {
    alert(
      "Defina UNIASSELVI_BEARER_TOKEN em js/config.js antes de usar esta tela.",
    );
    return;
  }

  let div_result = document.querySelector("#result");
  $("#result").empty();

  let data = {
    specialization: specialization,
    modality: "2",
    testCode: testCode,
    examCode: examCode,
    semester: semester,
    subjectCode: subjectCode,
    classCode: classCode,
    typeDescription: "null",
    answerBook: "false",
  };

  let promise = fetch(url_get, {
    method: "POST",
    headers: {
      "Content-Type": "application/json;charset=utf-8",
      authorization: token,
    },
    body: JSON.stringify(data),
  });

  promise
    .then((res) => res.json())
    .catch((error) => error)
    .then((response) => {
      console.log(response);

      info = response.info;
      title = info.subject_name + " - " + info.description;
      console.log(info);

      // Título
      document.querySelector("title").innerHTML = title;

      questions = response.questions;
      questions.forEach((element) => {
        const description_question = document.createElement("div");
        const description_question_text = document.createElement("div");

        description_question.innerHTML = `<div> 
            <small class="badge text-bg-primary">${element.number}</small>
             <small class="badge text-bg-secondary">${info.subject_name}</small> 
             <small class="badge text-bg-secondary">${info.description}</small> 
            </div>`;

        description_question.setAttribute("class", "respostas");
        div_result.appendChild(description_question);

        description_question_text.innerHTML = `${element.description}`;
        try {
          description_question_text
            .querySelector("p")
            .setAttribute("class", "title");
        } catch (error) {
          description_question_text.setAttribute("class", "title");
        }
        description_question.appendChild(description_question_text);

        const respostas = document.createElement("div");
        respostas.setAttribute("class", "correct");
        const respostas_titulo = document.createElement("span");
        const respostas_texto = document.createElement("div");

        element.alternatives.forEach((alternative) => {
          if (alternative.correct === "S") {
            respostas_titulo.innerHTML = `<span> Resposta correta é a letra </span> <span class="badge text-bg-success">${alternative.letter}</span>`;

            respostas.appendChild(respostas_titulo);

            respostas_texto.innerHTML = `${alternative.description}`;
            respostas_titulo.appendChild(respostas_texto);

            description_question.appendChild(respostas);
          }
        });
      });
    });

  // "done!"
}
