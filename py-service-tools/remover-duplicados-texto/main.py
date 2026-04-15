def remove_duplicates(input_file, output_file):
    # Lendo o arquivo de entrada
    with open(input_file, 'r') as file:
        lines = file.readlines()
    
    # Removendo linhas duplicadas usando um conjunto
    unique_lines = list(set(lines))
    
    # Ordenando as linhas para manter a ordem original
    unique_lines.sort(key=lines.index)
    
    # Escrevendo as linhas únicas no arquivo de saída
    with open(output_file, 'w') as file:
        file.writelines(unique_lines)

# Exemplo de uso
input_file = 'input.txt'
output_file = 'output.txt'
remove_duplicates(input_file, output_file)
