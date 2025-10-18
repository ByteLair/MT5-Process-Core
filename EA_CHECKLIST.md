# Checklist Rápido - Análise de EA MQL5

## 🔍 O que vou verificar no código do EA:

### 1. Configuração da URL e API Key
```mql5
// ✅ CORRETO
string api_url = "http://SEU_IP:18001/ingest";
string api_key = "supersecretkey";

// ❌ ERRADO
string api_url = "http://localhost:8001/ingest";  // porta errada!
string api_key = "wrong_key";
```

### 2. Formato do Timestamp
```mql5
// ✅ CORRETO - ISO 8601 com timezone
datetime dt = iTime(_Symbol, PERIOD_M1, 1);
string timestamp = TimeToString(dt, TIME_DATE|TIME_MINUTES|TIME_SECONDS);
StringReplace(timestamp, ".", "-");
StringReplace(timestamp, " ", "T");
timestamp += "Z";  // Adiciona UTC
// Resultado: "2025-10-17T21:30:00Z"

// ❌ ERRADO
string timestamp = TimeToString(TimeCurrent());
// Resultado: "2025.10.17 21:30" (formato inválido!)
```

### 3. Conversão de Timeframe
```mql5
// ✅ CORRETO
string GetTimeframeString(ENUM_TIMEFRAMES period)
{
    switch(period)
    {
        case PERIOD_M1:  return "M1";
        case PERIOD_M5:  return "M5";
        case PERIOD_M15: return "M15";
        case PERIOD_M30: return "M30";
        case PERIOD_H1:  return "H1";
        case PERIOD_H4:  return "H4";
        case PERIOD_D1:  return "D1";
        default:         return "M1";
    }
}

// ❌ ERRADO
string tf = IntegerToString(period);  // Retorna "1" em vez de "M1"
```

### 4. Montagem do JSON
```mql5
// ✅ CORRETO - JSON válido
string json = StringFormat(
    "{\"ts\":\"%s\",\"symbol\":\"%s\",\"timeframe\":\"%s\","
    "\"open\":%.5f,\"high\":%.5f,\"low\":%.5f,\"close\":%.5f,\"volume\":%d}",
    timestamp, symbol, timeframe,
    open, high, low, close, volume
);

// ❌ ERRADO - aspas faltando, formato incorreto
string json = "{ts:" + timestamp + ",symbol:" + symbol + "}";
```

### 5. Headers HTTP
```mql5
// ✅ CORRETO
string headers = "Content-Type: application/json\r\n";
headers += "X-API-Key: supersecretkey\r\n";

// ❌ ERRADO
string headers = "Content-Type: text/plain\r\n";
string headers = "ApiKey: supersecretkey\r\n";  // nome do header errado
```

### 6. WebRequest
```mql5
// ✅ CORRETO
char post[];
char result[];
string result_headers;

ArrayResize(post, StringToCharArray(json, post, 0, WHOLE_ARRAY) - 1);

int res = WebRequest(
    "POST",
    url,
    headers,
    5000,        // timeout 5s
    post,
    result,
    result_headers
);

if(res == 200)
{
    Print("✅ Sucesso: ", CharArrayToString(result));
}
else if(res == -1)
{
    Print("❌ Erro: WebRequest não permitido. Adicione URL nas configurações!");
    Print("Código de erro: ", GetLastError());
}
else
{
    Print("❌ HTTP ", res, ": ", CharArrayToString(result));
}

// ❌ ERRADO - sem tratamento de erro
WebRequest("POST", url, headers, 5000, post, result, result_headers);
```

### 7. Trigger Correto (OnTick vs OnTimer)
```mql5
// ✅ MELHOR - Usa timer de 60 segundos
int OnInit()
{
    EventSetTimer(60);  // A cada 60 segundos
    return INIT_SUCCEEDED;
}

void OnTimer()
{
    SendCandle(_Symbol, PERIOD_M1);
}

// ✅ OK - Detecta nova barra
void OnTick()
{
    static datetime last_bar = 0;
    datetime current_bar = iTime(_Symbol, PERIOD_M1, 0);
    
    if(current_bar != last_bar)
    {
        last_bar = current_bar;
        SendCandle(_Symbol, PERIOD_M1);
    }
}

// ❌ RUIM - Envia em todo tick (sobrecarga)
void OnTick()
{
    SendCandle(_Symbol, PERIOD_M1);  // Vai enviar centenas de vezes!
}
```

### 8. Permissão WebRequest no MT5
```
OBRIGATÓRIO:
1. Ferramentas → Opções → Expert Advisors
2. ☑ Permitir WebRequest para as seguintes URLs
3. Adicionar: http://SEU_IP:18001
   (ou https:// se usar SSL)
```

### 9. Logs e Debug
```mql5
// ✅ BOM - Logs detalhados
Print("=== Enviando candle ===");
Print("Timestamp: ", timestamp);
Print("Symbol: ", symbol);
Print("Timeframe: ", timeframe);
Print("JSON: ", json);
Print("HTTP Response: ", res);
Print("Body: ", CharArrayToString(result));

// ❌ RUIM - Sem logs
SendCandle();  // Como vou saber se deu erro?
```

### 10. Tratamento de Erros Comuns
```mql5
// Verifica se tem dados
if(CopyRates(symbol, period, 1, 1, rates) != 1)
{
    Print("❌ Erro ao obter candle: ", GetLastError());
    return false;
}

// Verifica valores válidos
if(rates[0].close <= 0 || rates[0].high <= 0)
{
    Print("❌ Preços inválidos");
    return false;
}

// Verifica se timestamp não é futuro
if(rates[0].time > TimeCurrent())
{
    Print("⚠️ Timestamp no futuro!");
    return false;
}
```

## 🎯 Erros Mais Comuns que vou procurar:

1. ❌ Porta 8001 em vez de 18001
2. ❌ Timestamp sem timezone (falta o "Z")
3. ❌ Timeframe como número (1) em vez de string ("M1")
4. ❌ JSON malformado (aspas faltando)
5. ❌ Header "ApiKey" em vez de "X-API-Key"
6. ❌ WebRequest não permitido nas configurações
7. ❌ Volume como double em vez de int
8. ❌ Enviando candle aberto (index 0) em vez do fechado (index 1)
9. ❌ Sem tratamento de erro HTTP
10. ❌ Sem verificação de última barra (envia duplicado)

## 📝 Informações que vou precisar:

- [ ] Código completo do EA (.mq5)
- [ ] Mensagens de erro no log do MT5 (aba Experts)
- [ ] IP/hostname que o EA está tentando acessar
- [ ] Se WebRequest está habilitado

## ✅ Quando você enviar o código:

1. Cole aqui ou compartilhe o arquivo .mq5
2. Me diga qual erro aparece no log do MT5
3. Vou identificar o problema específico
4. Vou fornecer a correção exata

---

**Estou pronto para analisar! 🚀**
