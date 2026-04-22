// exibidor de respostas /// brainly


let respostas = document.querySelectorAll('[data-testid="answer_box_text"]');
respostas.forEach(element => {
    console.log(element.innerText)
});