import requests

# Lê o arquivo de texto
with open("input.txt", "r") as file:
    lines = file.readlines()

# Executa uma consulta HTTP para cada linha do arquivo
results = []
for line in lines:
    response = requests.get(line.strip())
    results.append(response.text)

# Escreve os resultados em um novo arquivo de texto
with open("output.txt", "w") as file:
    file.write("\n".join(results))