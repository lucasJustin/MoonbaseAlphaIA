import requests

MODELO = "tinyllama"
historico = []

print("🤖 Chatbot offline iniciado! Digite 'sair' para fechar.\n")

while True:
    pergunta = input("Você: ").strip()
    if pergunta.lower() == "sair":
        break
    if not pergunta:
        continue

    historico.append({"role": "user", "content": pergunta})

    try:
        resposta = requests.post("http://localhost:11434/api/chat", json={
            "model": MODELO,
            "messages": historico,
            "stream": False
        }, timeout=60)

        dados = resposta.json()

        if "message" in dados:
            mensagem = dados["message"]["content"]
            historico.append({"role": "assistant", "content": mensagem})
            print(f"\nIA: {mensagem}\n")
        else:
            print(f"\n⚠️ Resposta inesperada do Ollama: {dados}\n")
            historico.pop()  # remove a pergunta do histórico se falhou

    except requests.exceptions.ConnectionError:
        print("\n❌ Erro: Ollama não está rodando! Abra o Ollama primeiro.\n")
        historico.pop()
    except Exception as e:
        print(f"\n❌ Erro inesperado: {e}\n")
        historico.pop()