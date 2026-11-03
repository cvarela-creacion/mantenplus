# mantenplus: bot de trading híbrido (Python + comité de IA)

Bot de trading automatizado para **Binance Spot** con una arquitectura híbrida
pensada para gastar lo menos posible:

- **Python hace el trabajo pesado gratis.** Descarga velas con `ccxt`, calcula
  los indicadores con `pandas` y puntúa las señales. Esto corre en cada ciclo y
  no cuesta nada de IA.
- **La IA (Claude) actúa como comité de inversiones.** Solo se le consulta
  cuando Python encuentra una señal de alta probabilidad *y* la operación ya
  pasó un primer filtro de rentabilidad. La IA aprueba o rechaza, estima la
  probabilidad de éxito y puede ajustar el SL y el TP.

> ⚠️ **Aviso.** Este código es una base de ingeniería, no una garantía de
> ganancias. La estrategia incluida es un punto de partida razonable, no una
> ventaja probada. Antes de arriesgar dinero real, valídala durante semanas en
> Testnet o en `DRY_RUN` y después empieza con poco capital.

---

## Arquitectura

```
main.py                    Punto de entrada (CLI: --check, --once, bucle continuo)
tradingbot/
├── config.py              Configuración central (.env). Interruptor SANDBOX_MODE
├── exchange.py            Capa ccxt: el ÚNICO módulo que sabe si es Testnet o Producción
├── indicators.py          EMA, RSI, MACD, ATR, ADX, Bollinger, volumen (pandas puro)
├── signals.py             Puntaje de confluencia local, niveles SL/TP con ATR, alertas de salida
├── risk.py                SL/TP obligatorios, tamaño de posición, kill switch diario
├── costs.py               Filtro de rentabilidad neta + contabilidad del gasto en IA
├── ai_committee.py        Comité de inversiones (Claude, salida JSON estructurada)
├── engine.py              Bucle lógico híbrido (orquestación)
└── state.py               Persistencia atómica de posiciones, PnL y gasto de IA
tests/                     69 pruebas (exchange y API de IA simulados)
```

### Flujo de una vela cerrada

```
OHLCV (ccxt) ─▶ indicadores (pandas) ─▶ señal local (puntaje 0..1)
                                           │ sin señal ─────────────▶ fin (IA = $0)
                                           ▼
             reglas de riesgo + plan con SL/TP obligatorios
                                           ▼
             COMPUERTA 1 (pre-IA): comisiones + deslizamiento + IA amortizada
                                           │ no rentable ──────────▶ fin (IA = $0)
                                           ▼
             presupuesto diario + enfriamiento por símbolo
                                           ▼
             COMITÉ DE IA ── rechaza / error / respuesta inválida ─▶ fin (no se opera)
                                           ▼
             revalidación local de los niveles de la IA + COMPUERTA 2 (VE neto)
                                           ▼
             compra a mercado ─▶ OCO de venta (TP + SL) en el exchange
                                           │ falla la protección ──▶ cierre de emergencia
                                           ▼
             seguimiento: OCO ejecutado ─▶ PnL neto (incluye IA) ─▶ trades.jsonl
```

Cada vela cerrada se evalúa **una sola vez** por símbolo. El bucle puede
consultar el exchange cada 30 s para seguir las posiciones, pero nunca repite
una consulta a la IA sobre la misma vela.

---

## Las cuatro directrices y dónde se cumplen

### 1. Arquitectura híbrida de eficiencia de costos
- `indicators.py` y `signals.py` son 100 % locales.
- La IA se llama desde un único punto (`engine._seek_entry`) y solo después de
  la señal local (`MIN_SIGNAL_SCORE`, 0.75 por defecto), las reglas de riesgo y
  la compuerta 1.
- Límites duros de gasto: `AI_DAILY_BUDGET_USD`, `AI_SYMBOL_COOLDOWN_MINUTES`
  y el contexto de mercado compacto (24 velas) para que cada consulta use pocos
  tokens.

### 2. Testnet y Producción sin reescribir código
```env
SANDBOX_MODE=true    # Binance Spot Testnet (https://testnet.binance.vision)
SANDBOX_MODE=false   # Binance Producción (dinero real)
```
- `ExchangeClient` llama a `exchange.set_sandbox_mode(True)` de `ccxt`. El resto
  del sistema no sabe en qué entorno está.
- Las llaves van separadas por entorno (`BINANCE_TESTNET_*` y `BINANCE_*`), así
  que no se pueden usar por error las llaves reales en pruebas ni al revés.
- El estado también va separado: `state/testnet/` y `state/production/`.
- **Salvaguarda:** para operar con dinero real hay que definir además
  `CONFIRM_LIVE_TRADING=YES_I_UNDERSTAND_REAL_MONEY`. Sin esa línea, el bot no
  arranca en producción (salvo en `DRY_RUN`).

### 3. Filtro estricto de rentabilidad neta (`costs.py`)
Los costos se modelan tal como se ejecutan las órdenes: entrada a mercado
(*taker* + deslizamiento), TP con `LIMIT_MAKER` (*maker*) y SL con stop a
mercado (*taker* + deslizamiento).

| Compuerta | Cuándo | Exige |
|---|---|---|
| **Pre-IA** (gratis) | antes de llamar a la IA | beneficio bruto en TP ≥ `MIN_PROFIT_TO_COST_RATIO` (3×) los costos totales; probabilidad de equilibrio ≤ `MAX_BREAKEVEN_PROBABILITY` (45 %) |
| **Post-IA** | con los niveles finales | lo anterior, más: probabilidad estimada por la IA ≥ probabilidad de equilibrio + `MIN_PROBABILITY_EDGE` (5 pp), y valor esperado neto ≥ `MIN_EV_TO_COST_RATIO` × costos |

**Costo proporcional de la IA.** En la compuerta 1 se imputa el costo
*amortizado*: `costo_por_consulta / tasa_de_aprobación`. Así, cada operación
ejecutada paga también las consultas que terminaron en rechazo. La tasa de
aprobación arranca en `AI_PRIOR_APPROVAL_RATE` y se ajusta con el historial
real. En la compuerta 2 se usa el costo real de la consulta, calculado con los
tokens que devuelve la API. Si respondió un modelo de respaldo, cada tramo se
cobra a la tarifa de su modelo. El PnL registrado de cada operación ya descuenta
comisiones e IA.

> Cuenta orientativa: una consulta con `claude-opus-5-5` y `AI_EFFORT=medium`
> cuesta unos 0.03 a 0.07 USD (≈2.5k tokens de entrada a 4 USD/M y
> ≈1.5k a 3k de salida, incluido el razonamiento, a 20 USD/M). En una operación
> de 20 USD con TP al 1.5 % (0.30 USD brutos), ese costo se come gran parte del
> beneficio y el filtro la descarta *sin llamar a la IA*. Con 500 USD
> (7.50 USD brutos), la consulta pesa menos del 1 %. **El filtro calcula solo
> el tamaño mínimo de operación que justifica consultar.**

### 4. Gestión de riesgo obligatoria (`risk.py`)
- **SL y TP son obligatorios.** Si faltan, si no cumplen SL < entrada < TP, si
  el SL queda fuera de [`MIN_SL_PCT`, `MAX_SL_PCT`] o si el R:R es menor que
  `MIN_REWARD_RISK`, la operación se rechaza. Esto aplica también a los niveles
  que propone la IA.
- **Tamaño de posición:** la pérdida en el SL, *incluidas comisiones y
  deslizamiento*, no supera `RISK_PER_TRADE_PCT` (1 %) del capital. Además, el
  nocional está limitado por `MAX_POSITION_PCT` y por el saldo libre.
- **Protección en el exchange:** tras cada compra se coloca una orden **OCO**
  (`POST /api/v3/orderList/oco`) con TP `LIMIT_MAKER` y SL `STOP_LOSS`. La
  posición sigue protegida aunque el bot se caiga. Si la OCO falla dos veces,
  se hace un **cierre de emergencia** a mercado.
- La posición se guarda en disco *antes* de colocar la OCO. Si el proceso muere
  en medio, el siguiente ciclo la detecta sin protección y la protege o la
  cierra.
- **Kill switch:** si la pérdida realizada del día llega a `MAX_DAILY_LOSS_PCT`
  (3 %), no se abren más posiciones ese día. Las abiertas siguen protegidas por
  su OCO.
- `MAX_OPEN_POSITIONS` limita cuántas posiciones puede haber a la vez.

---

## El comité de IA (`ai_committee.py`)

- Modelo por defecto `claude-opus-5-5` con `thinking: adaptive` y
  `effort: medium` (configurable con `AI_MODEL` y `AI_EFFORT`). La tabla de
  precios de `config.py` alimenta el filtro de costos: si cambias de modelo, el
  filtro se ajusta solo.
- **Salida estructurada** (`output_config.format` con JSON Schema) validada con
  Pydantic: `decision`, `win_probability`, `stop_loss`, `take_profit`,
  `confidence`, `risk_flags` y `rationale`.
- **Fallback del servidor activado** (`fallbacks: "default"`, beta
  `server-side-fallback-2026-07-01`): si el modelo declina una consulta por
  política, la API la reintenta en el modelo de respaldo recomendado dentro de
  la misma llamada. Se desactiva con `AI_USE_SERVER_FALLBACKS=false`.
- **Fail-closed:** cualquier error (red, límite de tasa, rechazo, respuesta
  truncada o JSON inválido) se trata como *no operar*.
- **Revisión de salida:** si una posición abierta muestra deterioro (ruptura de
  tendencia o RSI extremo), se pregunta a la IA si mantenerla (HOLD) o cerrarla
  ya (CLOSE). Solo se consulta si lo que queda en riesgo justifica el costo de
  la consulta y de la salida. Ese costo se carga a la propia posición.

---

## Puesta en marcha

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env              # completa tus llaves
```

1. Crea llaves de Testnet en <https://testnet.binance.vision> (inicia sesión con
   GitHub y usa "Generate HMAC_SHA256 Key").
2. Añade tu `ANTHROPIC_API_KEY`.
3. Verifica la conexión:
   ```bash
   python main.py --check
   ```
4. Ejecuta un ciclo y luego el bucle continuo:
   ```bash
   python main.py --once
   python main.py            # Ctrl+C detiene de forma ordenada
   ```

**Modos de operación**

| `SANDBOX_MODE` | `DRY_RUN` | Resultado |
|---|---|---|
| `true` | `false` | Órdenes reales en **Testnet** (dinero virtual), el modo recomendado para empezar |
| `true`/`false` | `true` | Datos reales + IA, posiciones **simuladas** con `PAPER_EQUITY` |
| `false` | `false` | **Dinero real.** Requiere `CONFIRM_LIVE_TRADING` |

Archivos generados en `state/<entorno>/`:
- `state.json`: posiciones abiertas, gasto de IA y PnL diario.
- `trades.jsonl`: diario de operaciones cerradas, con PnL bruto, comisiones,
  costo de IA y PnL neto.
- `bot.log`: registro rotativo.

## Pruebas

```bash
pytest -q
```

Las pruebas usan un exchange falso y un cliente falso de la API de IA. No
necesitan red ni llaves y cubren:
- indicadores, señales, costos y riesgo;
- las compuertas pre-IA y post-IA;
- el cierre de emergencia;
- la contabilidad del PnL neto;
- el kill switch, el presupuesto de IA, el modo `DRY_RUN` y la persistencia;
- el cambio entre Testnet y Producción.

## Limitaciones conocidas y próximos pasos

- **Solo spot y solo largos.** Para operar en corto hacen falta futuros o
  margen, con otra lógica de protección.
- **El Testnet no se comporta como producción.** La liquidez, el
  deslizamiento y los precios difieren, y no expone las comisiones de la
  cuenta, así que se usan las configuradas.
- **Falta un backtester.** El siguiente paso recomendado es reproducir
  `SignalEngine` sobre datos históricos, con comisiones, para calibrar
  `MIN_SIGNAL_SCORE` y los multiplicadores de ATR *antes* de gastar en IA.
- **No hay trailing stop.** La OCO es fija. Ajustarla exigiría cancelarla y
  reemplazarla.
- **Comisiones en BNB.** Si la comisión se cobra en BNB, se estima de forma
  conservadora al 0.1 %.
