from zeep import Client
from zeep.transports import Transport
import requests
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def consulta_nfe_chave_acesso(chave_acesso):
    # URL do serviço de consulta de NFe
    url_servico = 'https://www.sefazvirtual.fazenda.gov.br/NFeConsulta2/NFeConsulta2.asmx?wsdl'

    # Configuração da verificação SSL usando a biblioteca requests
    session = requests.Session()
    session.verify = False  # Defina como True se você possuir o certificado do servidor

    # Criação do transporte com a sessão configurada
    transport = Transport(session=session)

    # Criação do cliente SOAP com o transporte configurado
    client = Client(url_servico, transport=transport)

    # Parâmetros da consulta
    parametros = {
        'nfeConsultaNF': {
            'consulta': {
                'xServ': 'CONSULTAR',
                'chNFe': chave_acesso
            }
        }
    }

    # Chamada ao serviço
    response = client.service.nfeConsultaNF(**parametros)

    # Recupera o XML da NFe
    xml_nfe = response['retConsSitNFe']['protNFe']['infProt']['chNFe']

    return xml_nfe

# Substitua 'SuaChaveDeAcesso' pela chave de acesso real da NFe que você deseja consultar
chave_acesso = '29231148677331000278550010000009261100721079'

try:
    xml_nfe = consulta_nfe_chave_acesso(chave_acesso)
    print(xml_nfe)
except Exception as e:
    print(f"Erro ao consultar NFe: {e}")
