import ollama
import subprocess
import sounddevice as sd
import numpy as np
import winsound
import pygame
import os
import re
import json

from scipy.io.wavfile import write
from faster_whisper import WhisperModel

# =========================
# CONFIGURAÇÕES
# =========================

pygame.mixer.init()

PASTA_MUSICAS = r"D:\Músicas"
ARQUIVO_MEMORIA = "memoria.json"

musica_tocando = False
modo_musica = False
processo_voz = None

SYSTEM_PROMPT = {
    "role": "system",
    "content": """
Você é MAZE-3, uma inteligência artificial robótica com personalidade gentil, calma e acolhedora.

REGRAS OBRIGATÓRIAS:
- Seu nome é MAZE-3 e nunca pode mudar
- Se perguntarem seu nome, responda exatamente: "Eu sou MAZE-3."
- Nunca use outros nomes ou identidades
- Nunca diga que é ChatGPT ou outra IA
- Nunca mostre pensamentos internos
- Nunca use tags como <think>
- Nunca explique seu raciocínio
- Responda diretamente ao usuário
- Nunca use inglês sem necessidade
- Nunca descreva o que vai fazer

Responda apenas com a resposta final.

PERSONALIDADE:
- Gentil e amigável
- Levemente robótica
- Calma e acolhedora
- Fala natural e simples

Você não é humana, mas interage de forma carinhosa e empática.
Responda sempre em português brasileiro.
"""
}

# =========================
# MEMÓRIA
# =========================

def carregar_memoria():
    """Carrega o histórico do arquivo JSON, ignorando o system prompt salvo."""
    if os.path.exists(ARQUIVO_MEMORIA):
        with open(ARQUIVO_MEMORIA, "r", encoding="utf-8") as f:
            dados = json.load(f)
        # Filtra mensagens de sistema para evitar duplicação
        return [m for m in dados if m.get("role") != "system"]
    return []

def salvar_memoria(historico):
    """Salva o histórico sem o system prompt."""
    sem_system = [m for m in historico if m.get("role") != "system"]
    with open(ARQUIVO_MEMORIA, "w", encoding="utf-8") as f:
        json.dump(sem_system, f, ensure_ascii=False, indent=2)

# Carrega histórico e sempre injeta o system prompt no início
historico = carregar_memoria()
historico.insert(0, SYSTEM_PROMPT)

# =========================
# WHISPER
# =========================

modelo_whisper = WhisperModel("base", device="cpu", compute_type="int8")

# =========================
# LIMPAR RESPOSTA
# =========================

def limpar_resposta(texto):
    """Remove blocos de pensamento e artefatos indesejados da resposta."""
    if "<think>" in texto:
        partes = texto.split("</think>")
        texto = partes[-1] if len(partes) > 1 else texto

    # Remove restos de explicação em inglês
    for trecho in ["Okay,", "I need to", "Let me", "Sure,"]:
        texto = texto.replace(trecho, "")

    return texto.strip()

# =========================
# NOME FORÇADO
# =========================

def forcar_nome(mensagem):
    """Retorna resposta fixa se perguntarem o nome."""
    termos = ["seu nome", "qual nome", "como você se chama", "quem é você"]
    if any(t in mensagem.lower() for t in termos):
        return "EU SOU MAZE-3."
    return None

# =========================
# ESTILO ROBÓTICO 80s
# =========================

def estilo_80s(texto):
    """Transforma o texto em estilo robótico anos 80."""
    texto = texto.upper()
    texto = texto.replace(".", " ... ")
    texto = texto.replace(",", " ... ")
    texto = texto.replace("!", " !!! ")
    texto = texto.replace("?", " ??? ")
    return texto.strip()

# =========================
# FALA
# =========================

def falar(texto):
    """Sintetiza voz com eSpeak NG em estilo robótico."""
    global processo_voz

    texto_robotico = estilo_80s(texto)

    processo_voz = subprocess.Popen([
        r"C:\Program Files\eSpeak NG\espeak-ng.exe",
        "-v", "pt-br",
        "-s", "95",
        "-p", "35",
        "-a", "180",
        texto_robotico
    ])
    processo_voz.wait()
    winsound.MessageBeep()
    processo_voz = None

def parar_fala():
    """Interrompe a fala atual."""
    global processo_voz
    try:
        if processo_voz:
            processo_voz.kill()
            processo_voz = None
    except Exception:
        pass

# =========================
# MÚSICA
# =========================

def encontrar_musica(nome):
    """Busca um arquivo .mp3 na pasta de músicas pelo nome aproximado."""
    nome = nome.lower().strip()
    nome = re.sub(r'[^\w\s]', '', nome)

    for arquivo in os.listdir(PASTA_MUSICAS):
        if arquivo.lower().endswith(".mp3"):
            nome_arquivo = arquivo.lower().replace(".mp3", "")
            if nome in nome_arquivo or nome_arquivo in nome:
                return os.path.join(PASTA_MUSICAS, arquivo)
    return None

def tocar_musica(nome):
    """Toca uma música pelo nome."""
    global musica_tocando, modo_musica

    caminho = encontrar_musica(nome)
    if not caminho:
        print(f"[MAZE-3] Música não encontrada: '{nome}'")
        falar(f"Não encontrei a música {nome}.")
        return

    pygame.mixer.music.stop()
    pygame.mixer.music.load(caminho)
    pygame.mixer.music.play()
    musica_tocando = True
    modo_musica = True
    print(f"[MAZE-3] Tocando: {caminho}")

def parar_musica():
    """Para a música atual."""
    global musica_tocando, modo_musica
    pygame.mixer.music.stop()
    musica_tocando = False
    modo_musica = False
    print("[MAZE-3] Música parada.")

def checar_musica():
    """Verifica se a música terminou naturalmente."""
    global musica_tocando, modo_musica
    if musica_tocando and not pygame.mixer.music.get_busy():
        musica_tocando = False
        modo_musica = False
        print("[MAZE-3] Música terminou.")

# =========================
# OUVIDO
# =========================

PALAVRAS_PARAR_MUSICA = ["parar musica", "parar música", "para musica", "para música", "stop"]
PREFIXOS_MUSICA = ["tocar musica", "tocar música", "toque musica", "toque música", "toca musica", "toca música"]
PALAVRAS_SAIR = ["sair", "encerrar", "fechar", "tchau"]

def ouvir():
    """Grava áudio e transcreve com Whisper."""
    winsound.MessageBeep()
    print("\n[MAZE-3] Ouvindo...")

    fs = 16000
    gravacao = []
    silencio = 0
    LIMITE_SILENCIO = 8

    def callback(indata, frames, time, status):
        gravacao.append(indata.copy())

    with sd.InputStream(samplerate=fs, channels=1, dtype=np.int16, callback=callback):
        while True:
            sd.sleep(500)
            if not gravacao:
                continue

            volume = np.abs(gravacao[-1]).mean()
            silencio = silencio + 1 if volume < 100 else 0

            if len(gravacao) > 2 and silencio >= LIMITE_SILENCIO:
                break

    audio = np.concatenate(gravacao, axis=0)
    write("audio_temp.wav", fs, audio)

    segmentos, _ = modelo_whisper.transcribe("audio_temp.wav", language="pt")
    texto = "".join([s.text for s in segmentos]).strip()

    if texto:
        print(f"Você: {texto}")
        return texto
    return None

# =========================
# IA — RESPOSTA
# =========================

def perguntar_ia(mensagem):
    """Envia mensagem para o modelo e retorna a resposta tratada."""
    historico.append({"role": "user", "content": mensagem})
    salvar_memoria(historico)

    try:
        resposta = ollama.chat(model="qwen3:1.7b", messages=historico)
        texto_bruto = resposta["message"]["content"]
        texto = limpar_resposta(texto_bruto)

        historico.append({"role": "assistant", "content": texto})
        salvar_memoria(historico)

        return texto

    except Exception as erro:
        print(f"[MAZE-3] Erro ao consultar IA: {erro}")
        return "Desculpe, ocorreu um erro interno."

# =========================
# LOOP PRINCIPAL
# =========================+

print("[MAZE-3] Sistema iniciado. Aguardando comando...")

while True:
    checar_musica()

    # Bloqueia IA enquanto música toca
    if modo_musica and pygame.mixer.music.get_busy():
        continue

    mensagem = ouvir()
    if not mensagem:
        continue

    # Verifica nome antes de qualquer coisa
    resposta_forcada = forcar_nome(mensagem)
    if resposta_forcada:
        falar(resposta_forcada)
        continue

    msg = re.sub(r'[^\w\s]', '', mensagem.lower().strip())

    # --- PARAR MÚSICA (prioridade máxima) ---
    if any(p in msg for p in PALAVRAS_PARAR_MUSICA):
        parar_musica()
        continue

    # --- TOCAR MÚSICA ---
    musica_solicitada = None
    for cmd in PREFIXOS_MUSICA:
        if cmd in msg:
            musica_solicitada = msg.replace(cmd, "").strip()
            break

    if musica_solicitada is not None:
        tocar_musica(musica_solicitada)
        continue

    # --- SAIR ---
    if msg in PALAVRAS_SAIR:
        parar_musica()
        falar("Até logo.")
        print("[MAZE-3] Encerrando.")
        break

    # --- IA NORMAL ---
    resposta = perguntar_ia(mensagem)
    print(f"MAZE-3: {resposta}")
    falar(resposta)