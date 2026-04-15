# python

Monorepo com APIs, servicos e utilitarios em Python, alem de alguns projetos web de apoio.

## Objetivo

Este repositorio centraliza projetos independentes em um unico lugar para facilitar versionamento, organizacao e manutencao.

## Estrutura

### APIs e integracoes

- `py-api-alexia/`: projetos ligados a automacao, desktop e controle de temperatura.
- `py-api-buscador-de-dados/`: consultas, scrapers e versoes de uma API de busca de dados.
- `py-api-erp/`: esqueleto de ERP com controllers, services, schema e database.
- `py-baixar-xmls-sefaz/`: utilitarios para baixar XMLs da SEFAZ.

### Servicos e automacoes

- `py-service-focus-agenda/`: placeholder de integracao com agenda.
- `py-service-monitor-sefaz/`: monitoramento de disponibilidade da SEFAZ com alerta.
- `py-service-opencv-faces/`: experimentos versionados com OpenCV.
- `py-service-transcrever-audio/`: transcricao de audio para texto.
- `py-service-uniasselvi-agenda/`: automacoes ligadas a Uniasselvi, agenda e ChatGPT.
- `py-service-webcam-ia/`: deteccao de cachorro com OpenCV e WebSocket.

### Caixa de ferramentas

- `py-service-tools/`: colecao de utilitarios e pequenos servicos auxiliares.

## Como navegar

Cada pasta principal possui seu proprio contexto. Quando houver subprojetos, o `README.md` local lista os diretorios e pontos de entrada mais importantes.

## Convencoes deste monorepo

- Cada projeto pode ter dependencias e modo de execucao proprios.
- Arquivos sensiveis e artefatos locais devem ficar fora do versionamento.
- O `.gitignore` raiz cobre padroes globais; projetos especificos podem complementar com regras locais.

## Proximos passos recomendados

1. Inicializar o repositorio Git na raiz deste diretorio.
2. Revisar arquivos sensiveis ja existentes antes do primeiro commit.
3. Evoluir os READMEs de cada projeto com comandos reais de execucao conforme necessario.
