# raspc-notificacao

Envia notificações push para o app **RaspController** quando a presença no
quarto muda, usando a biblioteca `raspc_notif`.

O estado vem do `~/presenca-quarto/estado.json`, gravado pelo serviço
`presenca-quarto` a cada mudança. O script lê esse arquivo a cada 1 s e
notifica só quando `presenca` muda (o estado ao iniciar serve de referência):

| Mudança | Mensagem | Prioridade |
|---|---|---|
| ausente → presente | `Presença detectada às HH:MM` | alta |
| presente → ausente | `Quarto vazio às HH:MM (ocupado por 12min30s)` | normal |

Falhas temporárias (rede, servidor, excesso de requisições) são tentadas de
novo até 3 vezes; chave inválida ou parâmetro errado só vão para o log.

## Instalação

```
git clone https://github.com/rtavares-g/raspc-notificacao.git ~/raspc-notificacao
cd ~/raspc-notificacao
./install.sh
```

O `install.sh` instala as dependências, cria o `.env` a partir do
`.env.example` pedindo a API Key (se o `.env` ainda não existir), cria o
`venv`, instala e inicia o serviço e oferece enviar uma notificação de teste.
Pode ser rodado de novo para reinstalar/atualizar.

## Arquivos

| Arquivo | Função |
|---|---|
| `notificar_presenca.py` | monitora o `estado.json` e envia as notificações |
| `install.sh` | instalação/reinstalação completa |
| `raspc-notificacao.service` | unit do systemd (cópia instalada em `/etc/systemd/system/`) |
| `.env` | chave da API (`RASPC_APIKEY`), `chmod 600`, não compartilhar |
| `.env.example` | modelo do `.env` |
| `requirements.txt` | dependências Python (`raspc-notif`) |
| `venv/` | ambiente Python com a biblioteca `raspc_notif` |

## Configuração

Chave da API (no app RaspController, tela de notificações), no `.env`:

```
RASPC_APIKEY=sua_chave_aqui
```

Variáveis opcionais (ambiente):

| Variável | Padrão | Descrição |
|---|---|---|
| `RASPC_APIKEY` | — | tem prioridade sobre o `.env` |
| `ARQUIVO_ESTADO` | `~/presenca-quarto/estado.json` | arquivo de estado monitorado |
| `INTERVALO_SEG` | `1.0` | intervalo de leitura do arquivo |

## Serviço

Instalado pelo `install.sh`. Sobe depois do `presenca-quarto` e reinicia sozinho em 5 s se cair.

```
journalctl -u raspc-notificacao -f        # log ao vivo
sudo systemctl restart raspc-notificacao  # após editar o script ou o .env
```

## Rodar manualmente

```
venv/bin/python notificar_presenca.py
```

Notificação de teste:

```
venv/bin/python -c "
import notificar_presenca as m
from raspc_notif import notif
r = notif.Sender(m.carregar_apikey()).send_notification(notif.Notification('Teste', 'Notificação de teste'))
print(r.status, r.message)
"
```

`status` 0 = enviado. Códigos de erro: 1 socket, 2 excesso de requisições,
3 servidor, 4 chave inválida, 5 parâmetro inválido, 6 nenhum dispositivo
registrado.
