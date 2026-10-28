# Contrato MQTT do AquaNível

**Versão: v1, congelada em 27/10/2026.** Qualquer mudança gera uma nova versão registrada no fim deste arquivo.

## Regras gerais

- Toda mensagem é JSON com `v` (versão do contrato, hoje `1`).
- Mensagens de dispositivo levam `deviceId` e `ts` (ISO 8601 em UTC). Sem NTP, o dispositivo envia `"relogio":"NAO_SINCRONIZADO"` no lugar de `ts` e o backend usa o horário de chegada.
- Grandezas sempre como objeto `{"valor": ..., "unidade": "..."}`.
- Só o backend publica em `cmd` e em `backend/heartbeat` (garantido pela ACL do Mosquitto).
- O backend valida toda mensagem contra este contrato; mensagem inválida é descartada e registrada com o código `PAYLOAD_INVALIDO`.

## Árvore de tópicos

```
catolicasc-g4/reservatorio/
├── rsv-medidor-01/
│   ├── telemetria   medidor → backend   QoS 0  retain não  a cada 10 s
│   ├── alerta       medidor → backend   QoS 1  retain não  por evento
│   ├── status       LWT / online        QoS 1  retain sim
│   └── config       backend → medidor   QoS 1  retain sim
├── rsv-controlador-01/
│   ├── cmd          backend → contr.    QoS 1  retain não
│   ├── ack          contr. → backend    QoS 1  retain não
│   ├── estado       contr. → backend    QoS 1  retain sim  ao mudar
│   ├── status       LWT / online        QoS 1  retain sim
│   └── config       backend → contr.    QoS 1  retain sim
└── backend/
    └── heartbeat    backend → contr.    QoS 0  retain não  a cada 10 s
```

### Justificativa de QoS e retain

| Tópicos | Escolha | Por quê |
|---|---|---|
| telemetria, heartbeat | QoS 0, sem retain | Chegam a cada 10 s; uma perda isolada é coberta pela próxima. Heartbeat com retain seria perigoso: um heartbeat velho entregue na reconexão pareceria comunicação viva. |
| cmd, ack, alerta | QoS 1, sem retain | Não podem se perder. QoS 1 pode duplicar, então o controlador guarda os últimos 8 `commandId` e responde `COMANDO_DUPLICADO` sem executar de novo. Sem retain para um comando antigo não ser reexecutado. |
| estado, status, config | QoS 1, com retain | Quem assina depois recebe na hora o último estado, se o dispositivo está online e a configuração vigente. |

## Payloads

### rsv-medidor-01/telemetria

```json
{"v":1,"deviceId":"rsv-medidor-01","ts":"2026-11-10T22:15:30Z","seq":1042,
 "nivel":{"valor":63.4,"unidade":"%"},
 "distancia":{"valor":10.7,"unidade":"cm"},
 "temperatura":{"valor":24.8,"unidade":"°C"},
 "sensor":"OK"}
```

`sensor`: `OK` ou `FALHA`. Faixas plausíveis: distância 2 a 400 cm, temperatura -10 a 60 °C, nível 0 a 100 %.

### rsv-medidor-01/alerta

```json
{"v":1,"deviceId":"rsv-medidor-01","ts":"2026-11-10T22:40:12Z",
 "codigo":"NIVEL_CRITICO","nivel":{"valor":8.2,"unidade":"%"}}
```

`codigo`: `NIVEL_CRITICO` (≤ 10 %), `NIVEL_TRANSBORDO` (≥ 95 %), `SENSOR_FALHA`, `NORMALIZADO`.

### rsv-medidor-01/config

```json
{"v":1,"d_vazio_cm":23.5,"d_cheio_cm":4.0,"alerta_baixo_pct":10,"alerta_alto_pct":95,"periodo_s":10}
```

Gravado na NVS ao receber. Valor fora da faixa é recusado (`VALOR_FORA_FAIXA`) e o anterior é mantido.

### rsv-controlador-01/cmd

```json
{"v":1,"commandId":"c-20261110-0007","origem":"manual",
 "acao":"LIGAR","usuario":"admin","ts":"2026-11-10T22:16:02Z"}
```

| Campo | Valores aceitos |
|---|---|
| `acao` | `LIGAR`, `DESLIGAR`, `MODO_AUTO`, `LIBERAR` |
| `origem` | `regra` (histerese do backend) ou `manual` (painel) |
| `commandId` | texto único gerado pelo backend |

### rsv-controlador-01/ack

Uma mensagem por etapa do ciclo de comando:

```json
{"v":1,"deviceId":"rsv-controlador-01","commandId":"c-20261110-0007",
 "etapa":"EXECUTADO","motivo":null,"ts":"2026-11-10T22:16:03Z"}
```

`etapa`: `RECEBIDO`, `EXECUTADO` ou `REJEITADO` (com `motivo`). O estado `ENVIADO` é registrado pelo backend ao publicar, e `CONFIRMADO` quando o `estado` publicado bate com o comando.

### rsv-controlador-01/estado

```json
{"v":1,"deviceId":"rsv-controlador-01","ts":"2026-11-10T22:16:03Z",
 "modo":"MANUAL","bomba":"LIGADA","ligadaHa":{"valor":1,"unidade":"s"},
 "ultimoCommandId":"c-20261110-0007","fw":"1.0.0"}
```

`modo`: `AUTOMATICO`, `MANUAL` ou `SEGURO` (com `motivoSeguro`). `bomba`: `LIGADA` ou `DESLIGADA`.

### rsv-controlador-01/config

```json
{"v":1,"t_manual_s":300,"t_max_ligada_s":600,"hb_timeout_s":30}
```

### backend/heartbeat

```json
{"v":1,"ts":"2026-11-10T22:16:10Z","seq":381,"liberaBomba":true,"motivo":null}
```

`liberaBomba` é `false` quando o nível está em 90 % ou mais (`motivo: NIVEL_ALTO`) ou quando a última leitura do medidor tem mais de 30 s ou veio com falha (`motivo: SEM_LEITURA`). Sem heartbeat por 30 s o controlador desliga a bomba e entra em `SEGURO`.

### .../status (Last Will)

```json
{"v":1,"deviceId":"rsv-medidor-01","online":false}
```

Registrado como Last Will na conexão; ao conectar, o dispositivo publica `online:true` com `fw` e `ip`.

## Códigos de erro

| Código | Quando |
|---|---|
| `PAYLOAD_INVALIDO` | JSON malformado ou campo obrigatório ausente |
| `VERSAO_INCOMPATIVEL` | `v` diferente de 1 |
| `COMANDO_DESCONHECIDO` | `acao` fora da lista |
| `COMANDO_DUPLICADO` | `commandId` já processado |
| `MODO_SEGURO` | LIGAR recebido no estado SEGURO |
| `TEMPO_MAXIMO` | bomba atingiu o tempo máximo ligada |
| `NIVEL_ALTO` | LIGAR com `liberaBomba=false` por nível ≥ 90 % |
| `SEM_LEITURA` | LIGAR com `liberaBomba=false` por medidor offline ou leitura antiga |
| `SENSOR_FALHA` | leitura fora da faixa plausível |
| `VALOR_FORA_FAIXA` | parâmetro de config fora da faixa aceita |

## Histórico de versões

| Versão | Data | Mudança |
|---|---|---|
| v1 | 27/10/2026 | Contrato congelado no CP12 |
