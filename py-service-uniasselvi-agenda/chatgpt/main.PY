import os
import openai
# import yaml

# set the API Key
# yaml_file = open('API Keys/api_config_openai.yml', 'r')
# p = yaml.load(yaml_file, Loader=yaml.FullLoader)
openai.api_key = os.getenv("OPENAI_API_KEY")

if not openai.api_key:
    raise RuntimeError("Defina OPENAI_API_KEY no ambiente antes de executar este script.")

# show available models
modellist = openai.Model.list()
for i in modellist.data:
    # print(i.id)
    pass

    # Define the request


def send_openai_request(engine, prompt, max_tokens=1024):
    response = openai.Completion.create(
        engine=engine,
        prompt=prompt,
        max_tokens=max_tokens,
        n=1,
        stop=None,
        temperature=0.7
    )
    return response


    # Define the prompt
prompt = "Está tudo bem com  você ?"
model = "babbage"

# Generate a response
response = send_openai_request(model, prompt)

# Print the response
print(response["choices"][0]["text"])
