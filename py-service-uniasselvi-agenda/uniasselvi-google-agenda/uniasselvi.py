import os
import requests
from datetime import datetime

from agenda import main


def require_env(name):
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"Defina {name} no ambiente antes de executar este script.")
    return value

class Provas:

    def __init__(self):

        # VARIAVEIS
        self.URL_API = "https://api-ava.uniasselvi.com.br"
        self.URL_API_UNI = "https://api.uniasselvi.com.br"
        self.JWT_var = require_env("UNIASSELVI_JWT")
        self.header  = {"authorization": f"Bearer {self.JWT_var}"}

        self.student = "3524024"
        self.modality = 2
        self.gabarito = False
        self.diciplinas = []

        response = requests.post(
            f"{self.URL_API}/parameter/value/get", headers=self.header, data={
            "parameter": "PARA_SEME_CONTRATO"
        })

        # Retorna o semester
        if response.status_code == 200:
            self.semester = response.json()['value']

            data = {
                "id": self.buscaDados()[0]['disciplina'],
                "semester": self.semester,
                "specialization": self.student,
                "modality": self.modality,
                "area": "5456",
                "variant": "full",
                "noCache": True
            }

            # Buscar valor do getClassCode
            response = requests.post(
                f"{self.URL_API}/academic/subject/getById", headers=self.header, data=data)

            if response.status_code == 200:
                self.classCode =  response.json()['class']
            else : 
                print(response.json())

        else : 
            print(response.json())
            exit()

    
    # {'code': 401, 'message': 'Expired JWT Token'}

    def token(self):

        data = {
            "type": "login",
            "espe_codi": self.student
        }

        response = requests.post("https://www.uniasselvi.com.br/extranet/o-2.0/paginas/atendimento/chat/index.php", data=data)

        if response.status_code == 200:
            return response.json()['token']
        else:
            print(response.json())

    # Informações gerais sobre a diciplina
    def getbyId(self, id):

        data = {
            "id": id,
            "semester": self.semester,
            "specialization": self.student,
            "modality": self.modality,
            "area": "5456",
            "variant": "full",
            "noCache": True
        }

        response = requests.post(f"{self.URL_API}/academic/subject/getById", headers=self.header, data=data)

        if response.status_code == 200:
            return response.json()
        else:
            print(response.json())

    # Busca as diciplinas que estou cadastrado.
    def buscaDados(self):

        header = {"authorization": require_env("UNIASSELVI_BASIC_AUTH")}

        data = {"aluno": self.student, "semestre": self.semester, "posead": False}

        response = requests.post(
            f"{self.URL_API_UNI}/dashboard-aluno/busca-dados", headers=header, data=data)

        if response.status_code == 200:
            return response.json()['data'][0]['disciplinas']
        else:
            print(response.json())

    """
    getTestSchedules :  Busca os testes agendados de uma disciplina
    """
    def getTestSchedules(self, schedules):

        data_schedules = {
            "student": self.student,
            "subject": schedules
        }

        response = requests.post(f'{self.URL_API}/test-schedule/schedules', headers=self.header, data=data_schedules)

        if response.status_code == 200:
            return response.json()

    """
    setSchedules : Definindo as provas agendadas.
    """
    def setSchedules(schedules):
        print(schedules)


    """
    setTest : Definindo as infomações sobre uma disciplina
    """
    def setTest(self, provas, data , exam_realizado = False):
        
        # informações sobre ás disciplinas -> data
        
        # array para salvar dados
        teste_realizados = []
        testes_nao_realizados = []
     
        # gabarito da provas
        provas_gabarito = []

        try : 

            for test in provas:
                
                # Tratando erro na data de inicialização
                if test['description'] == 'Avaliação Final (Objetiva) - Individual':
                    data_start = datetime.strptime(test['realization_window_start'], '%Y-%m-%d %H:%M:%S').strftime('%d/%m/%Y')
                    data_end = datetime.strptime(test['realization_window_end'], '%Y-%m-%d %H:%M:%S').strftime('%d/%m/%Y')
                else:
                    data_start = test['begin_date']
                    data_end = test['end_date']
                   
                data_start_formart = str(datetime.strptime(data_start  , "%d/%m/%Y").date())+"T"+"09:00:00"
                data_end_formart =  str(datetime.strptime(data_end  , "%d/%m/%Y").date())+"T"+"23:59:00"

                summary = data['name'] +"-"+ test['description']

                # Então salvando no array de não realizados
                if test['exam_made'] == 0:

                    description =  f"ATENÇÃO\n {test['description']}\nPeso : {test['weight']}\nAté : {data_end} ás 23:59"

                    datas = {
                        'summary': summary,
                        'description': description,
                        'start_dateTime': data_start_formart,
                        'end_dateTime':data_end_formart 
                    }

                    testes_nao_realizados.append(datas)

                else:
                    description = f"Você já realizou a {test['description']}, com peso de {test['weight']} é tirou {test['grade']}."
                    
                    datas = {
                        'summary': summary,
                        'description': description,
                        'start_dateTime': data_start_formart,
                        'end_dateTime':data_end_formart 
                    }

                    teste_realizados.append(datas)
                
                # Gabarito da prova
                if test['code'] and test['test_code'] :
                
                    data_gabarito = {
                        "testCode" : test['code'],
                        "examCode" : test['test_code'],
                        "subject" : test['subject'] , 
                        "test_class" : test['test_class']
                    }

                    # Salvando questões das provas, busncando informações sobre ela.
                    provas_gabarito.append(data_gabarito)
            
            if exam_realizado == False : 
                return testes_nao_realizados
            elif(exam_realizado) == True: 
                return teste_realizados
            elif exam_realizado == None:
                return provas_gabarito

        except Exception as e:
            print(e)
    
    """
    getTest : Buscando todas as provas registradas.
    """
    def getTest(self, subjectCode , classCode):

        data = {
            "specialization": self.student,
            "modality": self.modality,
            "semester": self.semester,
            "subjectCode": subjectCode,
            "classCode": classCode,
            "noCache": True
        }

        response = requests.post(
            f'{self.URL_API}/test/get', headers=self.header, data=data)

        if response.status_code == 200:
            return response.json()
        else :
            return False
           
    """
    setbyId : Exibindo as informações sobre a disciplina
    """
    def setbyId(disciplina):

        print(f"{disciplina['begin_date']} até {disciplina['end_date']}")
        print(f"{disciplina['description']} ás {disciplina['desc_week_day']} - {disciplina['order_progress']}ª ")
        
        try:
            print("Material : " , disciplina['interactive_learning_trail_link'])
            print("Livro    : " ,disciplina['digital_book_link'])
        except KeyError :
            pass

        disciplina['class_code_grouping']
        disciplina['class_whatsapp_link']
        disciplina['teacher']['formation']
        disciplina['teacher']['person_mail']
        disciplina['teacher']['person_name']
        disciplina['teacher']['person_phone']
        disciplina['teacher']['teacher_code']

    """
    getQuestions : Buscando questões da prova.
    """
    def getQuestions(self, testCode , examCode , subjectCode , ClassCode):
            
        data = {
            "specialization": self.student,
            "modality": "2",
            "testCode": testCode,  
            "examCode": examCode,  
            "semester": self.semester,  
            "subjectCode": subjectCode,  
            "classCode": ClassCode,
            "typeDescription": "null",
            "answerBook": True
        }

        response = requests.post(f'{self.URL_API}/test/question/get', headers=self.header, data=data)

        if response.status_code == 200 : 
            return response.json()
    

    def setQuestions(questions):
        print("Buscando gabarito da prova ...")

        for question in questions:
            
            question_buscar = Provas.getQuestions(Provas(), question['testCode'], question['examCode'], question['subject'],question['test_class'])

            print(question_buscar['info']['description'])
            
            for quest in question_buscar['questions']:
                print(quest['description'])

                for q in quest['alternatives']:
                    print(q['letter'],")", q['description'])
                    # print(q[''])

            # for buscar in question_buscar:
            #     print(buscar[""])
            exit()


    def getAcademicSubject(self , semestre = None):

        data = {
            "specialization": "3524024",
            "semester": semestre,  #"self.semestre"
            "modality": "2",
            "class": None, # null
            "area": "5456",
            "onlyWithTest": False,
            "order": "semester",
            "type": None,
            "variant": "light"
        }

        response = requests.post(f'https://api-ava.uniasselvi.com.br/academic/subject/get', headers=self.header, data=data)

        if response.status_code == 200:
            return response.json()
        else :
            return False
    
# data-testid="answer_box_text"

if "__main__":

    disciplinas = Provas.getAcademicSubject(Provas(), "2022/2")

    if disciplinas != False:
        print('Buscando informações sobre as disciplinas ...')
    
        for disciplina in disciplinas:
            print(f"\n{disciplina['description']} foi encontrada, buscando provas ...")

            # informações sobre a disciplina
            data = {
                "name" : disciplina['description'], 
                "desc_week_day" : disciplina['desc_week_day'],
                "desc_period" : disciplina['desc_period'] ,
                "semester" : disciplina['semester'] , 
                "begin_date"  : disciplina['begin_date'] , 
                "end_date" : disciplina['end_date']
            }

            # Tempo de duração de cada disciplina,

            # Se a disciplina já começou, quantos dias faltam para começar.
            
            # classcode -> 
            code_class = disciplina['class']
            # code ->
            code = disciplina['code']
            # provas -> 
            provas = Provas.getTest(Provas(), code, code_class)
          
            if provas != False : 
                # provas_nao_realizadas ->
                datas = Provas.setTest(Provas(), provas , data , False)
                provas_realizadas = Provas.setTest(Provas(), provas , data , True)
                gabaritos = Provas.setTest(Provas(), provas , data , None)
             
                print(f"Encontrei {len(provas)}, Provas realizadas : {len(provas_realizadas)}/{len(provas)}")
                print(f"Salvando na agenda as provas não realizadas !")
                # Verificando se a prova pode ser consultada
                # Salvar as disciplinas no google agenda.
                # main(datas)
                Provas.setQuestions(gabaritos)
            
            # break


# # Buscando respostas da prova.
# if self.gabarito is True :       
#     if test['code'] and test['test_code']:
#        
