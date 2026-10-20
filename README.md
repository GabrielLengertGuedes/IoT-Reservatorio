# Projeto N1 — Medidor de Nível de Água do Reservatório

## 1. Integrantes

* Anttonio Osorio Molinaro Maccagnini - @anttonio06
* Gabriel Lengert Guedes - @GabrielLengertGuedes
* João Pedro Alves de Lima - @CapJao
* João Vitor Paranhos - @joaoparanhoss
* Rafael Alexandre Alves Bandoch - @RafaelBandoch
* Heitor Lopes Reis - @dev-heitorreis

---

## 2. Família temática

**Família 4 — Nível de reservatório**

---

## 3. Projeto

**Sistema IoT de medição de nível de um reservatório de água, com ESP32, sensor ultrassônico, Wi-Fi e MQTT.** O nível é lido, publicado na rede e só então aciona a bomba (LED) automaticamente — a decisão nunca é tomada localmente no mesmo ciclo da leitura. A telemetria é gravada em PostgreSQL e acompanhada em tempo real por um painel web.

---

## 4. Problema

É importante acompanhar a quantidade de água disponível em um reservatório para evitar que ele fique vazio ou transborde. A verificação manual do nível é imprecisa e exige alguém conferindo o reservatório constantemente, sem histórico e sem aviso a distância.

O projeto mede o nível de água do reservatório, publica essa leitura pela rede, aciona automaticamente uma bomba quando o nível está baixo, permite ligar/desligar remotamente, alerta (display + MQTT, e buzzer no nível crítico alto e ao fim do enchimento) em situações de nível baixo ou crítico e guarda o histórico em banco de dados.

---

## 5. Usuário ou contexto de uso

O sistema pode ser usado em residências, pequenos estabelecimentos, laboratórios ou qualquer ambiente com um reservatório de água. O usuário acompanha o nível pelo display físico (LCD 16x2) ou por um painel web que recebe os dados em tempo real, pode ligar/desligar a bomba manualmente pelo mesmo painel e consulta o histórico no banco (pgAdmin).

---

## 6. Objetivo da N1

Um protótipo com ESP32 que:

1. mede a distância até a água com um sensor ultrassônico HC-SR04, com a velocidade do som corrigida pela temperatura (DS18B20);
2. converte essa distância em percentual de 0% a 100%;
3. publica essa leitura via MQTT **antes** de qualquer decisão de acionamento;
4. decide ligar/desligar a bomba (simulada por um LED) a partir do próprio tópico MQTT que ele assina de volta — não a partir do valor calculado localmente;
5. aceita comando remoto (ligar/desligar manual) por outro tópico MQTT;
6. confirma o estado da bomba e a execução dos comandos;
7. sinaliza alertas de nível baixo/crítico no display e via MQTT, com buzzer no nível crítico alto e ao concluir o enchimento;
8. reconecta sozinho ao Wi-Fi e ao broker depois de uma queda.

---

## 7. Componentes usados

* ESP32 DevKit (ESP32-D0WD-V3);
* Sensor ultrassônico HC-SR04 — TRIG no D33, ECHO no D34 através de um divisor resistivo 1kΩ + 1kΩ (o ECHO do sensor sai em 5V, e o ESP32 não é 5V-tolerante);
* Display LCD 16x2 com módulo I2C (PCF8574, endereço 0x27 ou 0x3F detectado automaticamente) — SDA no D21, SCL no D22. Sem display, o firmware segue funcionando;
* LED — representa a bomba/válvula, no D26 (com resistor em série);
* Buzzer ativo 5V — alerta sonoro, no D27;
* Sensor de temperatura DS18B20 — DQ no D4, com resistor de pull-up de 4k7 para o 3V3. A temperatura lida a cada 3s corrige a velocidade do som no cálculo da distância; sem o sensor, o firmware assume 25°C;
* Protoboard, jumpers, cabo USB-C;
* Computador com Arduino CLI (compilação/gravação) e Docker (broker, banco e coletor).

---

## 8. Arquitetura

```text
HC-SR04 + DS18B20 ──▶ ESP32 (firmware)
                         │  mede a cada 100ms, filtra (mediana de 5 + média móvel)
                         ▼
                  publica "nivel" a cada 2s (MQTT 1883)
                         │
                         ▼
            Mosquitto (docker, broker do projeto)
         │                    │                         │
         ▼                    ▼                         ▼
 ESP32 assina o próprio   coletor Python ──▶ PostgreSQL ──▶ pgAdmin
 "nivel" de volta e SÓ   (amostragem)                       (histórico)
 AÍ decide ligar/desligar
 a bomba (LED)           painel-reservatorio.html
         │               (navegador, WebSocket 9001)
         ▼
 LED (bomba) + buzzer + LCD
```

A leitura sempre atravessa a rede (publica → broker → assina de volta) antes de qualquer atuação. O sensor nunca aciona o atuador diretamente dentro do mesmo `loop()`.

Por padrão o broker é o **Mosquitto local** do `docker-compose.yml`: o ESP32, o painel e o coletor conectam nele, sem depender da internet. Opcionalmente o Mosquitto pode fazer *bridge* com um broker remoto (`broker.hivemq.com` ou um cluster HiveMQ Cloud com TLS) — detalhes em [EXECUCAO.md](EXECUCAO.md).

### Lógica de controle

| Situação | Ação |
| --- | --- |
| nível ≤ 10% e bomba parada | liga a bomba (`LIGADA:AUTO`, alerta `ACIONAMENTO_AUTOMATICO`) |
| nível ≥ 90% com a bomba ligada | desliga a bomba, toca o buzzer 3 vezes (alerta `ENCHIMENTO_CONCLUIDO`) |
| nível < 15% | alerta `NIVEL_BAIXO` |
| nível ≥ 95% | alerta `CRITICO_ALTO` e buzzer intermitente |
| `PARAR` manual com nível ≤ 10% | a bomba não religa sozinha até o nível passar de 15% |

### Tópicos MQTT (prefixo `catolicasc-g4/reservatorio`)

| Tópico | Sentido | Conteúdo |
| --- | --- | --- |
| `.../nivel` | ESP32 → broker → ESP32 (e painel/coletor) | percentual 0-100, publicado a cada 2s; é a mensagem que dispara a decisão automática |
| `.../distancia` | ESP32 → broker | distância filtrada em cm |
| `.../temperatura` | ESP32 → broker | temperatura do DS18B20 em °C, usada no cálculo da distância |
| `.../bomba` | ESP32 → broker | `DESLIGADA`, `LIGADA:AUTO` ou `LIGADA:MANUAL` (retido) |
| `.../alerta/nivel` | ESP32 → broker | `NORMAL`, `NIVEL_BAIXO`, `CRITICO_ALTO`, `ACIONAMENTO_AUTOMATICO`, `ENCHIMENTO_CONCLUIDO` |
| `.../status` | ESP32 → broker | `online` (retido) / `offline` (Last Will) |
| `.../comando/bomba` | painel → broker → ESP32 | `LIGAR` ou `PARAR` (QoS 1) |
| `.../comando/bomba/confirmacao` | ESP32 → broker | `LIGAR:OK`, `PARAR:OK` ou `ERRO:comando_invalido` |

### Persistência

O coletor (`collector/collector.py`) assina `catolicasc-g4/reservatorio/#` e grava em duas tabelas (`db/init.sql`):

* `leituras` — nível, distância, temperatura e bomba, com amostragem: uma linha a cada 30s, ou na hora se o nível variar mais de 5 pontos percentuais;
* `eventos` — toda publicação em `bomba`, `status`, `alerta/nivel` e `comando/bomba/confirmacao`.

> Atenção: hoje o `docker-compose.yml` fixa o coletor em `MQTT_HOST: broker.hivemq.com`. Com o firmware publicando no Mosquitto local e a bridge desligada (padrão), o coletor não recebe nada e o banco fica vazio — é preciso apontar o coletor para `mosquitto` ou ligar a bridge.

O `db/views.sql` cria views prontas para a apresentação (`v_estado_atual`, `v_historico_1h`, `v_eventos_hoje`, `v_bomba_janelas`, `v_tempo_bomba`, `v_resumo_diario`).

### Estrutura do repositório

| Caminho | O que é |
| --- | --- |
| `sketch.ino` | firmware do ESP32 |
| `credenciais.exemplo.h` | modelo de Wi-Fi/broker (copiar para `credenciais.h`, que não é versionado) |
| `compilar.sh` | compila o firmware com o Arduino CLI para `build/` |
| `libraries.txt` | bibliotecas Arduino usadas |
| `docker-compose.yml`, `.env.example`, `.env.publico` | stack Mosquitto + PostgreSQL + coletor + pgAdmin |
| `mosquitto/mosquitto.conf` | template do broker (bridge opcional) |
| `collector/` | coletor MQTT → PostgreSQL em Python |
| `db/` | schema e views do banco |
| `pgadmin/` | servidor do pgAdmin pré-cadastrado |
| `painel-reservatorio.html` | painel web em tempo real |
| `limpar.sh` | zera as tabelas antes de uma demonstração |
| `relay-mqtt.py` | relay para a bridge em redes só IPv6 (ver EXECUCAO.md) |
| `wokwi.toml`, `diagram.json` | simulação no Wokwi (circuito principal) |
| `protoboard/`, `protoboard-bancada/` | variantes do circuito no Wokwi (com protoboard; bancada sem DS18B20 e buzzer) |
| `EXECUCAO.md` | guia detalhado de execução, banco, bridge e teste de reconexão |

---

## 9. Como rodar

### 9.1 Stack (broker, banco e coletor)

```bash
cp .env.example .env
cp pgadmin/pgpass.example pgadmin/pgpass   # trocar o placeholder pela senha do .env
docker compose up -d --build
```

Sobe o Mosquitto (1883 e WebSocket 9001), o PostgreSQL (5432), o coletor e o pgAdmin (http://localhost:5050). Passo a passo completo em [EXECUCAO.md](EXECUCAO.md).

### 9.2 Firmware

1. Copie o modelo de credenciais:
   ```bash
   cp credenciais.exemplo.h credenciais.h
   ```
   Ele já vem pronto para o simulador Wokwi (`Wokwi-GUEST` + `host.wokwi.internal`). Na placa real, preencha `WIFI_SSID`/`WIFI_SENHA` com uma rede 2,4 GHz e troque `MQTT_BROKER` pelo IP do computador que roda o Docker, na mesma rede. Para usar o broker público, ponha `"broker.hivemq.com"`; para um cluster HiveMQ Cloud, `MQTT_TLS 1` e as credenciais.
2. Compile (Linux/macOS ou Git Bash no Windows):
   ```bash
   ./compilar.sh
   ```
3. **Simulador:** no VS Code/Cursor com a extensão Wokwi, `F1 > Wokwi: Start Simulator` (usa `wokwi.toml` e `diagram.json`). Atenção: os diagramas do Wokwi usam um display OLED SSD1306, e o firmware atual só controla o LCD 16x2 — no simulador a tela não mostra os dados; acompanhe pelo monitor serial e pelo painel.
   **Placa real:** com o ESP32 conectado por USB:
   ```bash
   arduino-cli upload -p COM3 --fqbn esp32:esp32:esp32doit-devkit-v1 --input-dir build build
   ```
   (troque `COM3` pela porta serial correta)
4. Acompanhe pelo monitor serial (115200 baud). Comandos disponíveis: `QUEDA` (derruba o Wi-Fi para testar a reconexão), `STATUS`, `LIGAR`, `PARAR`, `I2C` (varre o barramento do display).

### 9.3 Painel

Abra `painel-reservatorio.html` no navegador. Ele conecta em `ws://localhost:9001` (Mosquitto local), mostra nível, distância, temperatura, bomba e alerta em tempo real e tem o botão de ligar/desligar a bomba. Para abrir em outro aparelho da rede, troque `localhost` pelo IP do computador na constante `BROKER`.

---

## 10. Backlog

| Tarefa | Status |
| --- | --- |
| Criar repositório | Feito |
| Migrar de Arduino Uno para ESP32 | Feito |
| Ligar sensor ultrassônico (com divisor resistivo) | Feito |
| Ligar display LCD 16x2 via I2C (com detecção automática de endereço) | Feito |
| Calcular nível em porcentagem, com filtro de mediana + média móvel | Feito |
| Conectar ao Wi-Fi com reconexão automática | Feito |
| Publicar telemetria via MQTT | Feito |
| Reestruturar decisão automática para depender do tópico, não do cálculo local | Feito |
| Implementar comando remoto (ligar/desligar) | Feito |
| Confirmar estado/ação via MQTT | Feito |
| Adicionar alerta sonoro (buzzer) e visual (display) | Feito |
| Montar painel web (MQTT sobre WebSocket) | Feito |
| Subir broker próprio (Mosquitto) com bridge opcional para broker remoto | Feito |
| Persistir telemetria e eventos em PostgreSQL (coletor + views) | Feito |
| Integrar sensor de temperatura (DS18B20) | Feito |
| Calibrar `D_VAZIO`/`D_CHEIO` para o recipiente real (23,5cm vazio / 4cm cheio) | Feito |
| Testar reconexão após queda de Wi-Fi/broker (comando `QUEDA`, ver EXECUCAO.md) | Feito |

---

## 11. Primeiro risco técnico

### Risco

O sensor ultrassônico pode apresentar leituras imprecisas, instáveis ou inválidas, dependendo da fiação (o ECHO sai em 5V e passa por um divisor resistivo até o ESP32), do posicionamento e de ruído elétrico no barramento.

### Impacto

Leituras inválidas poderiam travar o cálculo do nível ou, pior, ser interpretadas como "reservatório cheio" por engano.

### Mitigação já implementada

* Leituras fora da faixa fisicamente possível (`d < 2cm` ou `d > 450cm`) ou sem eco são descartadas, não usadas no cálculo.
* Um contador de falhas seguidas (`falhasSensor`) loga no serial, a cada 50 falhas, um diagnóstico de fiação (nível do ECHO em repouso, pinos usados). O DS18B20 tem diagnóstico equivalente.
* As leituras válidas passam por filtro de mediana (últimas 5) + média móvel exponencial, reduzindo o efeito de picos isolados.
* A velocidade do som é corrigida pela temperatura medida, em vez de um valor fixo.

---

## 12. Dúvidas para o professor

* O broker próprio (Mosquitto local, sem autenticação) é suficiente para a demonstração da N1, ou é esperado um broker na internet (público ou HiveMQ Cloud com TLS)?
