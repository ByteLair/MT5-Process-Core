# Guia de Debug do EA MT5

## 📋 Informações da API

### Endpoint de Ingestão
- **URL**: `http://localhost:18001/ingest` (ou seu IP externo)
- **Método**: POST
- **Header obrigatório**: `X-API-Key: supersecretkey`
- **Content-Type**: `application/json`

### Formato dos Dados

#### Opção 1: Single Candle
```json
{
  "ts": "2025-10-17T21:30:00Z",
  "symbol": "EURUSD",
  "timeframe": "M1",
  "open": 1.0850,
  "high": 1.0855,
  "low": 1.0848,
  "close": 1.0852,
  "volume": 1250
}
```

#### Opção 2: Batch (múltiplos candles)
```json
{
  "items": [
    {
      "ts": "2025-10-17T21:30:00Z",
      "symbol": "EURUSD",
      "timeframe": "M1",
      "open": 1.0850,
      "high": 1.0855,
      "low": 1.0848,
      "close": 1.0852,
      "volume": 1250
    },
    {
      "ts": "2025-10-17T21:31:00Z",
      "symbol": "EURUSD",
      "timeframe": "M1",
      "open": 1.0852,
      "high": 1.0857,
      "low": 1.0851,
      "close": 1.0856,
      "volume": 980
    }
  ]
}
```

## ⚠️ Campos Obrigatórios

1. **ts** (timestamp): Formato ISO 8601 com timezone UTC (ex: "2025-10-17T21:30:00Z")
2. **symbol** (string): Nome do par (ex: "EURUSD", "GBPUSD")
3. **timeframe** (string): Deve ser um de: M1, M5, M15, M30, H1, H4, D1
4. **open** (float): Preço de abertura
5. **high** (float): Preço máximo
6. **low** (float): Preço mínimo
7. **close** (float): Preço de fechamento
8. **volume** (int): Volume (opcional, pode ser null)

## 🔍 Checklist de Problemas Comuns no EA

### 1. Formato do Timestamp
❌ **ERRADO**: 
- `"2025-10-17 21:30:00"` (falta o 'T' e timezone)
- `"2025-10-17T21:30:00"` (falta o timezone 'Z')

✅ **CORRETO**:
- `"2025-10-17T21:30:00Z"`
- `"2025-10-17T21:30:00+00:00"`

### 2. Timeframe
❌ **ERRADO**: 
- `"1"`, `"m1"`, `"1m"`, `"PERIOD_M1"`

✅ **CORRETO**:
- `"M1"`, `"M5"`, `"M15"`, `"M30"`, `"H1"`, `"H4"`, `"D1"`

### 3. Header X-API-Key
❌ **ERRADO**:
- Sem header
- `"ApiKey: supersecretkey"`
- `"Authorization: supersecretkey"`

✅ **CORRETO**:
- `"X-API-Key: supersecretkey"`

### 4. Content-Type
✅ **OBRIGATÓRIO**:
- `"Content-Type: application/json"`

### 5. URL
Verifique se o EA está usando:
- IP correto (localhost, 127.0.0.1 ou IP externo)
- Porta correta: **18001** (não 8001!)
- Endpoint: `/ingest`

## 🧪 Teste Manual

### Teste 1: Usando curl (do Linux)
```bash
curl -X POST http://localhost:18001/ingest \
  -H "Content-Type: application/json" \
  -H "X-API-Key: supersecretkey" \
  -d '{
    "ts": "2025-10-17T21:40:00Z",
    "symbol": "EURUSD",
    "timeframe": "M1",
    "open": 1.0850,
    "high": 1.0855,
    "low": 1.0848,
    "close": 1.0852,
    "volume": 1250
  }'
```

**Resposta esperada**:
```json
{"ok":true,"inserted":1}
```

### Teste 2: Verificar se o dado foi inserido
```bash
docker-compose exec db psql -U trader -d mt5_trading -c \
  "SELECT * FROM market_data ORDER BY ts DESC LIMIT 5;"
```

## 🐛 Como Debugar o EA

### 1. Verifique os Logs da API
```bash
# Monitore em tempo real
docker-compose logs -f api

# Ou veja os últimos logs
docker-compose logs api --tail=50
```

**O que procurar**:
- ✅ Se aparecer `POST /ingest` = EA está enviando
- ❌ Se aparecer `401` = API Key incorreta
- ❌ Se aparecer `422` = Formato JSON inválido
- ❌ Se não aparecer nada = EA não está enviando ou URL errada

### 2. Verifique se o EA está ativo no MT5
- Expert Advisor está habilitado?
- AutoTrading está ligado?
- Há mensagens de erro no log do MT5?

### 3. Código MQL5 - Exemplo Correto

```mql5
//+------------------------------------------------------------------+
//| Função para enviar candle                                         |
//+------------------------------------------------------------------+
bool SendCandle(string symbol, ENUM_TIMEFRAMES period)
{
   string url = "http://SEU_IP:18001/ingest";
   string api_key = "supersecretkey";
   
   // Pega o último candle fechado
   MqlRates rates[];
   if(CopyRates(symbol, period, 1, 1, rates) != 1)
      return false;
   
   // Converte timestamp para ISO 8601
   datetime dt = rates[0].time;
   string timestamp = TimeToString(dt, TIME_DATE|TIME_MINUTES|TIME_SECONDS);
   StringReplace(timestamp, ".", "-");
   StringReplace(timestamp, " ", "T");
   timestamp += "Z";  // Adiciona timezone UTC
   
   // Converte timeframe
   string tf = "M1";
   switch(period)
   {
      case PERIOD_M1:  tf = "M1"; break;
      case PERIOD_M5:  tf = "M5"; break;
      case PERIOD_M15: tf = "M15"; break;
      case PERIOD_M30: tf = "M30"; break;
      case PERIOD_H1:  tf = "H1"; break;
      case PERIOD_H4:  tf = "H4"; break;
      case PERIOD_D1:  tf = "D1"; break;
   }
   
   // Monta JSON
   string json = StringFormat(
      "{\"ts\":\"%s\",\"symbol\":\"%s\",\"timeframe\":\"%s\","
      "\"open\":%.5f,\"high\":%.5f,\"low\":%.5f,\"close\":%.5f,\"volume\":%d}",
      timestamp, symbol, tf,
      rates[0].open, rates[0].high, rates[0].low, rates[0].close,
      (int)rates[0].tick_volume
   );
   
   // Prepara headers
   string headers = "Content-Type: application/json\r\n";
   headers += "X-API-Key: " + api_key + "\r\n";
   
   // Envia request
   char post[];
   char result[];
   string result_headers;
   
   ArrayResize(post, StringToCharArray(json, post, 0, WHOLE_ARRAY) - 1);
   
   int timeout = 5000; // 5 segundos
   int res = WebRequest("POST", url, headers, timeout, post, result, result_headers);
   
   if(res == 200)
   {
      Print("✅ Candle enviado com sucesso: ", symbol, " ", tf);
      return true;
   }
   else
   {
      Print("❌ Erro ao enviar candle. HTTP Code: ", res);
      Print("Response: ", CharArrayToString(result));
      return false;
   }
}

//+------------------------------------------------------------------+
//| Expert initialization function                                     |
//+------------------------------------------------------------------+
int OnInit()
{
   // Adicione a URL na lista de permitidas:
   // Tools -> Options -> Expert Advisors -> Allow WebRequest for listed URL
   Print("EA iniciado. Certifique-se de adicionar a URL na lista de permitidas!");
   return(INIT_SUCCEEDED);
}

//+------------------------------------------------------------------+
//| Expert tick function                                               |
//+------------------------------------------------------------------+
void OnTick()
{
   static datetime last_bar = 0;
   datetime current_bar = iTime(_Symbol, PERIOD_M1, 0);
   
   // Envia apenas quando fechar uma nova barra
   if(current_bar != last_bar)
   {
      last_bar = current_bar;
      SendCandle(_Symbol, PERIOD_M1);
   }
}
```

### Pontos Importantes no Código MQL5:

1. **WebRequest deve estar habilitado no MT5**:
   - Ferramentas → Opções → Expert Advisors
   - Marcar "Permitir WebRequest para as seguintes URLs"
   - Adicionar: `http://SEU_IP:18001`

2. **Formato do timestamp**: Muito importante!
   - MT5 usa formato americano
   - Precisa converter para ISO 8601

3. **Volume**: MT5 pode ter `tick_volume` ou `real_volume`

## 📊 Monitoramento

### Script de monitoramento contínuo
```bash
#!/bin/bash
# Salve como monitor_ingest.sh

while true; do
    clear
    echo "=== MONITOR DE INGESTÃO MT5 ==="
    echo "Hora: $(date)"
    echo ""
    
    echo "📊 Últimos 5 registros:"
    docker-compose exec -T db psql -U trader -d mt5_trading -c \
      "SELECT ts, symbol, timeframe, close, volume FROM market_data ORDER BY ts DESC LIMIT 5;"
    
    echo ""
    echo "📈 Registros nos últimos 5 minutos:"
    docker-compose exec -T db psql -U trader -d mt5_trading -t -c \
      "SELECT COUNT(*) FROM market_data WHERE ts > NOW() - INTERVAL '5 minutes';"
    
    sleep 10
done
```

## 🔧 Troubleshooting

### Problema: Nenhum dado chegando

1. **Teste a API manualmente** com curl (veja acima)
   - ✅ Se funcionar: problema está no EA
   - ❌ Se não funcionar: problema na API ou firewall

2. **Verifique o IP/Porta**
   - De dentro do Windows MT5, consegue acessar `http://SEU_IP:18001/health`?
   - Use navegador ou PowerShell: `Invoke-WebRequest http://SEU_IP:18001/health`

3. **Firewall**
   - A porta 18001 está aberta?
   - `sudo ufw status` (Linux)
   - Se necessário: `sudo ufw allow 18001/tcp`

4. **Logs do EA no MT5**
   - Abra a aba "Experts" no MetaTrader
   - Procure por mensagens de erro
   - Ative prints detalhados no código

### Problema: Dados chegando irregularmente

- **Causa**: EA pode estar enviando apenas quando há tick
- **Solução**: Use timer em vez de OnTick(), ou verifique se há ticks suficientes

### Problema: HTTP 401 (Unauthorized)

- **Causa**: API Key incorreta
- **Solução**: Verifique se está usando `supersecretkey`

### Problema: HTTP 422 (Validation Error)

- **Causa**: JSON com formato inválido
- **Solução**: 
  - Verifique o formato do timestamp
  - Verifique o timeframe (M1, M5, etc)
  - Use um validador JSON online

## 📞 Próximos Passos

Se quiser que eu analise o código do seu EA:

1. Envie o arquivo .mq5
2. Ou cole o código aqui
3. Posso identificar problemas específicos!

## ✅ Status Atual do Sistema

- ✅ API rodando na porta 18001
- ✅ Banco de dados funcionando
- ✅ Endpoint /ingest pronto
- ❌ EA não está enviando dados (0 requests POST nos logs)
