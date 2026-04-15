import datetime

def obter_quantidade_semanas_mes():
    hoje = datetime.datetime.now()
    primeiro_dia_mes = hoje.replace(day=1)
    ultimo_dia_mes = primeiro_dia_mes + datetime.timedelta(days=32)
    ultimo_dia_mes = ultimo_dia_mes.replace(day=1) - datetime.timedelta(days=1)
    
    quantidade_semanas = (ultimo_dia_mes.day - 1) // 7 + 1
    return quantidade_semanas

def main():
    quantidade_semanas = obter_quantidade_semanas_mes()
    saldo_total = 2000
    saldo_semanal = 350

    semana_atual = 1
    saldo_atual = saldo_semanal
    contas_pagas_por_semana = {}

    print(f"O mês atual possui {quantidade_semanas} semanas.")

    while semana_atual <= quantidade_semanas and saldo_total > 0:
        valor_pago = float(input(f"Digite o valor a pagar na semana {semana_atual}: "))

        if valor_pago > saldo_atual:
            saldo_total -= saldo_atual
            saldo_anterior = saldo_atual
            semana_atual += 1
            saldo_atual = saldo_semanal + (valor_pago - saldo_atual)
            print(f"Saldo insuficiente! Movendo para a próxima semana. Saldo restante: R$ {saldo_total}. Saldo da semana anterior somado: R$ {saldo_anterior}.")
        else:
            saldo_total -= valor_pago
            saldo_atual -= valor_pago
            if saldo_atual == 0:
                semana_atual += 1
                saldo_atual = saldo_semanal
                contas_pagas_por_semana[semana_atual - 1] = contas_pagas_por_semana.get(semana_atual - 1, []) + [valor_pago]
            else:
                contas_pagas_por_semana[semana_atual] = contas_pagas_por_semana.get(semana_atual, []) + [valor_pago]
            print(f"Pagamento de R$ {valor_pago} realizado. Saldo restante da semana: R$ {saldo_atual}. Saldo total restante: R$ {saldo_total}.")

    if saldo_total <= 0:
        print("Saldo total zerado. Todas as semanas do mês foram utilizadas.")
    else:
        print(f"Todas as semanas do mês foram utilizadas. Saldo total restante: R$ {saldo_total}.")

    print("\nRelatório de contas pagas por semana:")
    for semana, contas in contas_pagas_por_semana.items():
        print(f"Semana {semana}: {', '.join(map(str, contas))} reais")

if __name__ == "__main__":
    main()
