#!/usr/bin/env python3
"""
Envia notificações para o app RaspController quando a presença no quarto
muda, lendo o estado.json gravado pelo serviço presenca-quarto.

Chave da API: variável de ambiente RASPC_APIKEY ou arquivo .env nesta pasta
(linha RASPC_APIKEY=...). A chave fica no app RaspController, na tela de
notificações.

Uso:
    venv/bin/python notificar_presenca.py
"""

import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

from raspc_notif import notif

RAIZ = Path(__file__).resolve().parent
ARQUIVO_ESTADO = Path(os.environ.get(
    "ARQUIVO_ESTADO", Path.home() / "presenca-quarto" / "estado.json"))
INTERVALO_SEG = float(os.environ.get("INTERVALO_SEG", "1.0"))
# Tempo que o arquivo precisa mostrar o novo estado sem voltar atrás para a
# mudança valer. O sensor marca ausência após poucos segundos sem detecção, e
# essas falhas curtas não devem virar notificação de "quarto vazio".
ESTABILIZAR_PRESENCA_SEG = float(os.environ.get("ESTABILIZAR_PRESENCA_SEG", "0"))
ESTABILIZAR_AUSENCIA_SEG = float(os.environ.get("ESTABILIZAR_AUSENCIA_SEG", "60"))
TENTATIVAS_ENVIO = 3

# Erros que valem nova tentativa (rede/servidor); os demais são definitivos.
ERROS_TEMPORARIOS = {
    notif.Result.SOCKET_ERROR,
    notif.Result.SERVER_ERROR,
    notif.Result.TOO_MANY_REQUESTS,
}


def log(msg: str) -> None:
    print(f"{datetime.now():%Y-%m-%d %H:%M:%S} {msg}", flush=True)


def carregar_apikey() -> str:
    chave = os.environ.get("RASPC_APIKEY", "").strip()
    env = RAIZ / ".env"
    if not chave and env.exists():
        for linha in env.read_text(encoding="utf-8").splitlines():
            nome, _, valor = linha.partition("=")
            if nome.strip() == "RASPC_APIKEY":
                chave = valor.strip().strip("'\"")
    if not chave:
        sys.exit("Defina RASPC_APIKEY no ambiente ou no arquivo .env desta pasta.")
    return chave


def ler_estado() -> dict | None:
    """Lê o estado.json; retorna None se não existir ou estiver inválido."""
    try:
        dados = json.loads(ARQUIVO_ESTADO.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return dados if isinstance(dados, dict) else None


def formatar_duracao(seg: float) -> str:
    seg = int(seg)
    h, resto = divmod(seg, 3600)
    m, s = divmod(resto, 60)
    if h:
        return f"{h}h{m:02d}min"
    if m:
        return f"{m}min{s:02d}s"
    return f"{s}s"


def enviar(sender: notif.Sender, titulo: str, mensagem: str, alta: bool) -> None:
    notificacao = notif.Notification(titulo, mensagem, high_priority=alta)
    for tentativa in range(1, TENTATIVAS_ENVIO + 1):
        resultado = sender.send_notification(notificacao)
        if resultado.status == notif.Result.SUCCESS:
            log(f"NOTIFICAÇÃO enviada: {mensagem}")
            return
        log(f"NOTIFICAÇÃO falhou ({resultado.status}): {resultado.message}")
        if resultado.status not in ERROS_TEMPORARIOS or tentativa == TENTATIVAS_ENVIO:
            return
        # Limite de envios atingido: insistir em poucos segundos só prolonga o bloqueio.
        if resultado.status == notif.Result.TOO_MANY_REQUESTS:
            time.sleep(30 * tentativa)
        else:
            time.sleep(5 * tentativa)


def main() -> None:
    sender = notif.Sender(carregar_apikey())
    log(f"Monitorando {ARQUIVO_ESTADO}")

    # O estado inicial serve só de referência; notifica apenas mudanças.
    anterior = None
    presenca_desde = None
    while anterior is None:
        dados = ler_estado()
        if dados is not None:
            anterior = bool(dados.get("presenca"))
            presenca_desde = dados.get("presenca_desde")
            log(f"Estado inicial: presença {'SIM' if anterior else 'NÃO'}")
        else:
            time.sleep(INTERVALO_SEG)

    # Estado lido do arquivo que ainda não durou o bastante para valer, e
    # desde quando (time.time()) o arquivo o mostra sem interrupção.
    candidato: bool | None = None
    candidato_desde = 0.0

    while True:
        time.sleep(INTERVALO_SEG)
        dados = ler_estado()
        if dados is None:
            continue
        atual = bool(dados.get("presenca"))

        if atual == anterior:
            # Voltou ao estado confirmado antes de estabilizar: era oscilação.
            # presenca_desde só é preenchido se faltar; cada oscilação faz o
            # sensor gravar um novo início, que encurtaria a duração.
            candidato = None
            if atual and presenca_desde is None and dados.get("presenca_desde") is not None:
                presenca_desde = dados["presenca_desde"]
            continue

        if candidato != atual:
            candidato, candidato_desde = atual, time.time()
        espera = ESTABILIZAR_PRESENCA_SEG if atual else ESTABILIZAR_AUSENCIA_SEG
        if time.time() - candidato_desde < espera:
            continue

        horario = datetime.fromtimestamp(candidato_desde).strftime("%H:%M")
        if atual:
            presenca_desde = dados.get("presenca_desde") or candidato_desde
            enviar(sender, "Quarto", f"Presença detectada às {horario}", alta=True)
        else:
            mensagem = f"Quarto vazio às {horario}"
            if presenca_desde is not None:
                mensagem += f" (ocupado por {formatar_duracao(candidato_desde - float(presenca_desde))})"
            presenca_desde = None
            enviar(sender, "Quarto", mensagem, alta=False)
        anterior = atual
        candidato = None


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
