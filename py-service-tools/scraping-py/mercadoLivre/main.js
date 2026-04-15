let query = "cabo 6 metros preto";
query = query.replace(/ /g, "-");
let urlDownloadImagens = `https://lista.mercadolivre.com.br/${query}`;

let imgs = [];
// window.addEventListener("load", () => {
//   document.querySelectorAll(".ui-search-results img").forEach((element) => {
//     if (element.classList.length >= 1) {
//       imgs.push({ src: element.src, alt: element.alt });
//     }
//   });
// });

fetch(urlDownloadImagens)
  .then((response) => {
    return response.text();
  })
  .then((html) => {
    let parser = new DOMParser();
    let doc = parser.parseFromString(html, "text/html");
    let imgs = [];
    doc.querySelectorAll(".ui-search-results img").forEach((element) => {
      if (element.classList.length >= 1) {
        imgs.push({ src: element.src, alt: element.alt });
      }
    });
    console.log(imgs);
  })
  .catch((error) => {
    console.error(error);
  });
