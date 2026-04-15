from appium import webdriver

# Configurações do driver do Appium
desired_caps = {
    "platformName": "Android",
    "deviceName": "Android Emulator",
    "appPackage": "com.google.android.apps.messaging",
    "appActivity": "com.google.android.apps.messaging.ui.ConversationListActivity"
}

# Inicializa o driver do Appium
driver = webdriver.Remote("http://localhost:4723/wd/hub", desired_caps)

# Encontra o botão de nova mensagem e clica nele
new_message_button = driver.find_element_by_id(
    "com.google.android.apps.messaging:id/start_new_conversation_button")
new_message_button.click()

# Encontra o campo de destinatário e preenche com o número de telefone
recipient_field = driver.find_element_by_id(
    "com.google.android.apps.messaging:id/recipient_text_view")
recipient_field.send_keys("5551234567")

# Encontra o campo de mensagem e preenche com o texto
message_field = driver.find_element_by_id(
    "com.google.android.apps.messaging:id/compose_message_text")
message_field.send_keys("Hello World!")

# Encontra o botão de enviar e clica nele
send_button = driver.find_element_by_id(
    "com.google.android.apps.messaging:id/send_message_button")
send_button.click()

# Fecha o driver
driver.quit()
