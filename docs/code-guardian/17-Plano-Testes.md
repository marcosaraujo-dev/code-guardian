# Plano de Testes — Code Guardian

**Versão**: 1.0
**Data**: 2026-03-13
**Autor**: QA Engineering
**Escopo**: Scripts Python em `code_guardian/`

---

## Sumario

- [Visao Geral](#visao-geral)
- [Fixtures de Teste](#fixtures-de-teste)
- [TC-RE — rule_engine.py](#tc-re--rule_enginepy)
- [TC-ME — metrics.py](#tc-me--metricspy)
- [TC-DP — diff_parser.py](#tc-dp--diff_parserpy)
- [TC-AI — ai_client.py](#tc-ai--ai_clientpy)
- [TC-RU — runner.py](#tc-ru--runnerpy)
- [Testes de Integracao](#testes-de-integracao)
- [Script de Execucao Automatizada](#script-de-execucao-automatizada)
- [Criterios de Aceite por Script](#criterios-de-aceite-por-script)
- [Resumo de Cobertura](#resumo-de-cobertura)

---

## Visao Geral

### Arquitetura dos Scripts

```
runner.py  (orquestrador)
  ├── rule_engine.py   (analise estatica via regex — 25 regras)
  ├── metrics.py       (metricas de qualidade — tamanho, nesting, God Class)
  ├── diff_parser.py   (extracao de arquivos alterados via git)
  └── ai_client.py     (analise de IA com fallback: Gemini → Claude → OpenAI → Ollama)
```

### Piramide de Testes Aplicada

```
         Integracao (TC-INT — runner orquestrando todos)
        /                                               \
   Unitarios por script (TC-RE, TC-ME, TC-DP, TC-AI, TC-RU)
```

### Convencoes dos Test Cases

| Campo | Descricao |
|-------|-----------|
| ID | Identificador unico: `TC-{SIGLA}-{NNN}` |
| Severidade Esperada | `critical / error / warning / info` |
| Exit Code | `0` = sucesso, `1` = falha/bloqueio |
| Fixture | Arquivo `.cs` em `tests/fixtures/` |

### Diretorio Base dos Testes

Todos os comandos assumem que o diretorio de trabalho e:

```
code_guardian/
```

Fixtures ficam em:

```
code_guardian/tests/fixtures/
```

---

## Fixtures de Teste

Crie o diretorio e os arquivos abaixo antes de executar qualquer teste.

```bash
mkdir -p code_guardian/tests/fixtures
```

### clean.cs

Arquivo sem nenhum problema detectavel. Serve como linha de base para confirmar ausencia de falsos positivos.

```csharp
// code_guardian/tests/fixtures/clean.cs
using System.Threading.Tasks;

namespace CodeGuardian.Tests.Fixtures
{
    public class UserService
    {
        private readonly IUserRepository _userRepository;
        private readonly IEmailService _emailService;

        public UserService(IUserRepository userRepository, IEmailService emailService)
        {
            _userRepository = userRepository;
            _emailService = emailService;
        }

        public async Task<Result<UserDto>> GetUserAsync(int userId)
        {
            var user = await _userRepository.FindByIdAsync(userId);
            if (user == null)
                return Result<UserDto>.Failure("Usuario nao encontrado");

            return Result<UserDto>.Success(new UserDto(user.Id, user.Name, user.Email));
        }

        public async Task<Result<bool>> UpdateEmailAsync(int userId, string newEmail)
        {
            if (string.IsNullOrWhiteSpace(newEmail))
                return Result<bool>.Failure("Email invalido");

            var updated = await _userRepository.UpdateEmailAsync(userId, newEmail);
            return Result<bool>.Success(updated);
        }
    }
}
```

### sql_injection.cs

Contem concatenacao de string em SQL e interpolacao com `$"` — deve disparar `SQL_INJECTION_CONCAT` (critical).

```csharp
// code_guardian/tests/fixtures/sql_injection.cs
using System.Data.SqlClient;

namespace CodeGuardian.Tests.Fixtures
{
    public class UserRepository
    {
        private readonly string _connectionString = "Server=.;Database=App;";

        public object GetUserByName(string name)
        {
            // SQL Injection por concatenacao
            var query = "SELECT * FROM Users WHERE Name = '" + name + "'";
            using var conn = new SqlConnection(_connectionString);
            using var cmd = new SqlCommand(query, conn);
            conn.Open();
            return cmd.ExecuteScalar();
        }

        public object SearchByEmail(string email)
        {
            // SQL Injection por interpolacao
            var query = $"SELECT * FROM Users WHERE Email = '{email}'";
            using var conn = new SqlConnection(_connectionString);
            using var cmd = new SqlCommand(query, conn);
            conn.Open();
            return cmd.ExecuteScalar();
        }
    }
}
```

### deadlock.cs

Contem `.Result` e `.Wait()` em contexto async — deve disparar `TASK_RESULT_DEADLOCK` e `TASK_WAIT_DEADLOCK` (error).

```csharp
// code_guardian/tests/fixtures/deadlock.cs
using System.Threading.Tasks;

namespace CodeGuardian.Tests.Fixtures
{
    public class OrderService
    {
        private readonly IOrderRepository _orderRepository;

        public OrderService(IOrderRepository orderRepository)
        {
            _orderRepository = orderRepository;
        }

        public int GetTotalOrders(int userId)
        {
            // Deadlock: .Result bloqueia a thread
            var orders = _orderRepository.GetByUserAsync(userId).Result;
            return orders.Count;
        }

        public void ProcessOrder(int orderId)
        {
            // Deadlock: .Wait() bloqueia a thread
            _orderRepository.ProcessAsync(orderId).Wait();
        }
    }
}
```

### async_void.cs

Contem `async void` em metodo nao relacionado a event handler — deve disparar `ASYNC_VOID` (error).

```csharp
// code_guardian/tests/fixtures/async_void.cs
using System.Threading.Tasks;

namespace CodeGuardian.Tests.Fixtures
{
    public class NotificationService
    {
        private readonly IEmailSender _emailSender;

        public NotificationService(IEmailSender emailSender)
        {
            _emailSender = emailSender;
        }

        // async void perde excecoes
        public async void SendWelcomeEmail(string email)
        {
            await _emailSender.SendAsync(email, "Bem-vindo!", "Conteudo do email");
        }

        // async void perde excecoes
        private async void ProcessQueueInternal()
        {
            await Task.Delay(1000);
        }
    }
}
```

### secrets.cs

Contem senha hardcoded e API key hardcoded — deve disparar `HARDCODED_PASSWORD` e `HARDCODED_API_KEY` (critical).

```csharp
// code_guardian/tests/fixtures/secrets.cs
namespace CodeGuardian.Tests.Fixtures
{
    public class PaymentService
    {
        // Senha hardcoded
        private string password = "MinhaS3nh@Secreta123";

        // API Key hardcoded
        private string apiKey = "sk-abcdefghijklmnopqrstuvwxyz123456";

        // Token hardcoded
        private string token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.payload.signature";

        public bool Authenticate()
        {
            return password != null && apiKey != null;
        }
    }
}
```

### empty_catch.cs

Contem bloco catch vazio — deve disparar `EMPTY_CATCH` (error).

```csharp
// code_guardian/tests/fixtures/empty_catch.cs
using System;
using System.Threading.Tasks;

namespace CodeGuardian.Tests.Fixtures
{
    public class DataProcessor
    {
        public async Task<string> ProcessDataAsync(string input)
        {
            try
            {
                if (string.IsNullOrEmpty(input))
                    throw new ArgumentException("Input invalido");

                return await Task.FromResult(input.ToUpper());
            }
            catch { }

            return string.Empty;
        }

        public int ParseInt(string value)
        {
            try
            {
                return int.Parse(value);
            }
            catch (Exception ex) { }

            return 0;
        }
    }
}
```

### god_class.cs

Classe com mais de 5 dependencias injetadas e mais de 10 metodos publicos — deve disparar issues de God Class no metrics.py.

```csharp
// code_guardian/tests/fixtures/god_class.cs
using System.Threading.Tasks;

namespace CodeGuardian.Tests.Fixtures
{
    public class MegaService
    {
        private readonly IUserRepository _userRepository;
        private readonly IOrderRepository _orderRepository;
        private readonly IEmailService _emailService;
        private readonly IPaymentService _paymentService;
        private readonly IReportService _reportService;
        private readonly INotificationService _notificationService;
        private readonly IAuditService _auditService;

        public MegaService(
            IUserRepository userRepository,
            IOrderRepository orderRepository,
            IEmailService emailService,
            IPaymentService paymentService,
            IReportService reportService,
            INotificationService notificationService,
            IAuditService auditService)
        {
            _userRepository = userRepository;
            _orderRepository = orderRepository;
            _emailService = emailService;
            _paymentService = paymentService;
            _reportService = reportService;
            _notificationService = notificationService;
            _auditService = auditService;
        }

        public async Task<object> CreateUser(string name) => await Task.FromResult(name);
        public async Task<object> GetUser(int id) => await Task.FromResult(id);
        public async Task<object> UpdateUser(int id, string name) => await Task.FromResult(name);
        public async Task<object> DeleteUser(int id) => await Task.FromResult(id);
        public async Task<object> CreateOrder(int userId) => await Task.FromResult(userId);
        public async Task<object> GetOrder(int id) => await Task.FromResult(id);
        public async Task<object> CancelOrder(int id) => await Task.FromResult(id);
        public async Task<object> ProcessPayment(int orderId) => await Task.FromResult(orderId);
        public async Task<object> GenerateReport(string type) => await Task.FromResult(type);
        public async Task<object> SendNotification(int userId) => await Task.FromResult(userId);
        public async Task<object> GetAuditLog(int entityId) => await Task.FromResult(entityId);
        public async Task<object> ExportData(string format) => await Task.FromResult(format);
    }
}
```

### deep_nesting.cs

Contem estrutura com mais de 3 niveis de nesting — deve disparar issue de Deep Nesting no metrics.py.

```csharp
// code_guardian/tests/fixtures/deep_nesting.cs
using System.Collections.Generic;
using System.Threading.Tasks;

namespace CodeGuardian.Tests.Fixtures
{
    public class OrderProcessor
    {
        public async Task<string> ProcessOrders(List<Order> orders)
        {
            if (orders != null)
            {
                foreach (var order in orders)
                {
                    if (order.IsValid)
                    {
                        if (order.Items.Count > 0)
                        {
                            foreach (var item in order.Items)
                            {
                                if (item.Quantity > 0)
                                {
                                    // Nesting nivel 6 — profundo demais
                                    await ProcessItemAsync(item);
                                }
                            }
                        }
                    }
                }
            }

            return "Concluido";
        }

        private async Task ProcessItemAsync(object item)
        {
            await Task.CompletedTask;
        }
    }

    public class Order
    {
        public bool IsValid { get; set; }
        public List<OrderItem> Items { get; set; } = new();
    }

    public class OrderItem
    {
        public int Quantity { get; set; }
    }
}
```

### long_methods.cs

Contem metodo com mais de 30 linhas — deve disparar issue de Metodo Longo no metrics.py.

```csharp
// code_guardian/tests/fixtures/long_methods.cs
using System;
using System.Collections.Generic;
using System.Threading.Tasks;

namespace CodeGuardian.Tests.Fixtures
{
    public class ReportService
    {
        public async Task<string> GenerateFullReport(int userId, DateTime startDate, DateTime endDate)
        {
            // Este metodo tem mais de 30 linhas intencionalmente
            var report = new System.Text.StringBuilder();
            report.AppendLine("=== Relatorio Completo ===");
            report.AppendLine($"Usuario: {userId}");
            report.AppendLine($"Periodo: {startDate:yyyy-MM-dd} a {endDate:yyyy-MM-dd}");
            report.AppendLine("");

            // Secao 1
            report.AppendLine("--- Secao 1: Dados Gerais ---");
            report.AppendLine("Item 1: processando...");
            report.AppendLine("Item 2: processando...");
            report.AppendLine("Item 3: processando...");
            report.AppendLine("Item 4: processando...");
            report.AppendLine("Item 5: processando...");
            await Task.Delay(10);

            // Secao 2
            report.AppendLine("--- Secao 2: Estatisticas ---");
            report.AppendLine("Total de transacoes: calculando...");
            report.AppendLine("Valor total: calculando...");
            report.AppendLine("Media por transacao: calculando...");
            report.AppendLine("Maior transacao: calculando...");
            report.AppendLine("Menor transacao: calculando...");
            await Task.Delay(10);

            // Secao 3
            report.AppendLine("--- Secao 3: Resumo ---");
            report.AppendLine("Status geral: OK");
            report.AppendLine("Alertas: nenhum");
            report.AppendLine("Recomendacoes: nenhuma");
            await Task.Delay(10);

            // Secao 4
            report.AppendLine("--- Secao 4: Rodape ---");
            report.AppendLine($"Gerado em: {DateTime.UtcNow:yyyy-MM-dd HH:mm:ss}");
            report.AppendLine("Sistema: Code Guardian Reports");
            report.AppendLine("Versao: 1.0");
            report.AppendLine("=== Fim do Relatorio ===");

            return report.ToString();
        }
    }
}
```

### console_warning.cs

Contem `Console.WriteLine` — deve disparar `CONSOLE_WRITELINE` (warning).

```csharp
// code_guardian/tests/fixtures/console_warning.cs
using System;

namespace CodeGuardian.Tests.Fixtures
{
    public class DebugHelper
    {
        public void PrintStatus(string message)
        {
            Console.WriteLine($"[STATUS] {message}");
            Console.Write("Processando... ");
        }
    }
}
```

### todo_comment.cs

Contem comentarios TODO e FIXME — deve disparar `TODO_COMMENT` e `FIXME_COMMENT` (info).

```csharp
// code_guardian/tests/fixtures/todo_comment.cs
using System.Threading.Tasks;

namespace CodeGuardian.Tests.Fixtures
{
    public class CacheService
    {
        // TODO: implementar cache distribuido com Redis
        public async Task<object> GetAsync(string key)
        {
            // FIXME: remover simulacao e usar cache real
            return await Task.FromResult<object>(null);
        }

        // HACK: solucao temporaria para contornar bug do provider
        public void InvalidateAll()
        {
        }
    }
}
```

### httpclient_new.cs

Contem `new HttpClient()` — deve disparar `HTTPCLIENT_NEW` (warning).

```csharp
// code_guardian/tests/fixtures/httpclient_new.cs
using System.Net.Http;
using System.Threading.Tasks;

namespace CodeGuardian.Tests.Fixtures
{
    public class ApiClient
    {
        public async Task<string> GetDataAsync(string url)
        {
            // Socket exhaustion: HttpClient criado com new
            var client = new HttpClient();
            var response = await client.GetStringAsync(url);
            return response;
        }
    }
}
```

---

## TC-RE — rule_engine.py

**Criterios de aceite**: O script deve detectar os 25 padroes de problemas via regex, filtrar comentarios e duplicatas, e retornar exit 1 quando houver issues de severidade critical ou error.

### Deteccao de SQL Injection

| ID | Descricao | Fixture | Severidade Esperada |
|----|-----------|---------|---------------------|
| TC-RE-001 | Detecta SQL por concatenacao com `+` | sql_injection.cs | critical |
| TC-RE-002 | Detecta SQL por interpolacao `$"SELECT...{var}"` | sql_injection.cs | critical |

**TC-RE-001 / TC-RE-002**

Pre-condicao: fixture `sql_injection.cs` criada.

Comando:
```bash
python rule_engine.py tests/fixtures/sql_injection.cs --format json
```

Resultado esperado:
- Exit code: `1`
- JSON contem pelo menos 1 objeto com `"rule_id": "SQL_INJECTION_CONCAT"` e `"severity": "critical"`
- Campo `line` deve ser um numero inteiro positivo

Verificacao adicional (formato text):
```bash
python rule_engine.py tests/fixtures/sql_injection.cs --format text
```
- Saida contem `[SQL Injection]`
- Saida contem `🔴`

---

### Deteccao de Deadlocks Async

| ID | Descricao | Fixture | Severidade Esperada |
|----|-----------|---------|---------------------|
| TC-RE-003 | Detecta `.Result` em chamada async | deadlock.cs | error |
| TC-RE-004 | Detecta `.Wait()` em chamada async | deadlock.cs | error |

**TC-RE-003 / TC-RE-004**

Comando:
```bash
python rule_engine.py tests/fixtures/deadlock.cs --format json
```

Resultado esperado:
- Exit code: `1`
- JSON contem objeto com `"rule_id": "TASK_RESULT_DEADLOCK"` e `"severity": "error"`
- JSON contem objeto com `"rule_id": "TASK_WAIT_DEADLOCK"` e `"severity": "error"`
- `source` igual a `"rule_engine"` em todos os objetos

---

### Deteccao de async void

| ID | Descricao | Fixture | Severidade Esperada |
|----|-----------|---------|---------------------|
| TC-RE-005 | Detecta `async void` em metodo nao-event | async_void.cs | error |
| TC-RE-006 | Nao dispara para `async void` em event handler (_Click, _Load) | N/A (inline) | nenhuma |

**TC-RE-005**

Comando:
```bash
python rule_engine.py tests/fixtures/async_void.cs --format json
```

Resultado esperado:
- Exit code: `1`
- JSON contem pelo menos 1 objeto com `"rule_id": "ASYNC_VOID"` e `"severity": "error"`

**TC-RE-006** — Verificar que a excecao para event handlers funciona.

Pre-condicao: criar arquivo inline:
```csharp
// tests/fixtures/event_handler.cs
public class Form1
{
    private async void Button_Click(object sender, EventArgs e)
    {
        await Task.Delay(100);
    }
    private async void Form_Load(object sender, EventArgs e)
    {
        await Task.Delay(100);
    }
}
```

Comando:
```bash
python rule_engine.py tests/fixtures/event_handler.cs --format json
```

Resultado esperado:
- Exit code: `0`
- JSON e um array vazio `[]` (nenhuma issue de ASYNC_VOID)

---

### Deteccao de Secrets Hardcoded

| ID | Descricao | Fixture | Severidade Esperada |
|----|-----------|---------|---------------------|
| TC-RE-007 | Detecta senha hardcoded (HARDCODED_PASSWORD) | secrets.cs | critical |
| TC-RE-008 | Detecta API key/token hardcoded (HARDCODED_API_KEY) | secrets.cs | critical |

**TC-RE-007 / TC-RE-008**

Comando:
```bash
python rule_engine.py tests/fixtures/secrets.cs --format json
```

Resultado esperado:
- Exit code: `1`
- JSON contem objeto com `"rule_id": "HARDCODED_PASSWORD"` e `"severity": "critical"`
- JSON contem pelo menos 1 objeto com `"rule_id": "HARDCODED_API_KEY"` e `"severity": "critical"`

---

### Deteccao de Empty Catch

| ID | Descricao | Fixture | Severidade Esperada |
|----|-----------|---------|---------------------|
| TC-RE-009 | Detecta `catch { }` completamente vazio | empty_catch.cs | error |
| TC-RE-010 | Detecta `catch (Exception ex) { }` com corpo vazio | empty_catch.cs | error |

**TC-RE-009 / TC-RE-010**

Comando:
```bash
python rule_engine.py tests/fixtures/empty_catch.cs --format json
```

Resultado esperado:
- Exit code: `1`
- JSON contem pelo menos 2 objetos com `"rule_id": "EMPTY_CATCH"` e `"severity": "error"`

---

### Deteccao de Console.WriteLine

| ID | Descricao | Fixture | Severidade Esperada |
|----|-----------|---------|---------------------|
| TC-RE-011 | Detecta `Console.WriteLine` (warning) | console_warning.cs | warning |
| TC-RE-012 | Detecta `Console.Write(` (warning) | console_warning.cs | warning |

**TC-RE-011 / TC-RE-012**

Comando:
```bash
python rule_engine.py tests/fixtures/console_warning.cs --format json
```

Resultado esperado:
- Exit code: `0` (apenas warnings nao causam exit 1)
- JSON contem objeto com `"rule_id": "CONSOLE_WRITELINE"` e `"severity": "warning"`
- JSON contem objeto com `"rule_id": "CONSOLE_WRITE"` e `"severity": "warning"`

---

### Deteccao de TODO / FIXME

| ID | Descricao | Fixture | Severidade Esperada |
|----|-----------|---------|---------------------|
| TC-RE-013 | Detecta `// TODO` (info) | todo_comment.cs | info |
| TC-RE-014 | Detecta `// FIXME` (info) | todo_comment.cs | info |
| TC-RE-015 | Detecta `// HACK` (info) | todo_comment.cs | info |

**TC-RE-013 / TC-RE-014 / TC-RE-015**

Comando:
```bash
python rule_engine.py tests/fixtures/todo_comment.cs --format json
```

Resultado esperado:
- Exit code: `0` (apenas info nao causa exit 1)
- JSON contem objeto com `"rule_id": "TODO_COMMENT"`
- JSON contem objeto com `"rule_id": "FIXME_COMMENT"`
- JSON contem objeto com `"rule_id": "HACK_COMMENT"`

---

### Deteccao de HttpClient com new

| ID | Descricao | Fixture | Severidade Esperada |
|----|-----------|---------|---------------------|
| TC-RE-016 | Detecta `new HttpClient()` (warning) | httpclient_new.cs | warning |

**TC-RE-016**

Comando:
```bash
python rule_engine.py tests/fixtures/httpclient_new.cs --format json
```

Resultado esperado:
- Exit code: `0`
- JSON contem objeto com `"rule_id": "HTTPCLIENT_NEW"` e `"severity": "warning"`

---

### Filtro de Severidade

| ID | Descricao | Fixture | Flag | Resultado |
|----|-----------|---------|------|-----------|
| TC-RE-017 | `--severity error` filtra warnings e infos | todo_comment.cs | `--severity error` | array vazio |
| TC-RE-018 | `--severity critical` retorna apenas criticals | secrets.cs | `--severity critical` | apenas critical |
| TC-RE-019 | `--severity warning` inclui warning, error e critical | console_warning.cs + secrets.cs | `--severity warning` | todos esses niveis |

**TC-RE-017**

Comando:
```bash
python rule_engine.py tests/fixtures/todo_comment.cs --format json --severity error
```

Resultado esperado:
- Exit code: `0`
- JSON e `[]`

**TC-RE-018**

Comando:
```bash
python rule_engine.py tests/fixtures/secrets.cs --format json --severity critical
```

Resultado esperado:
- Exit code: `1`
- JSON contem apenas objetos com `"severity": "critical"` (nenhum error/warning/info)

---

### Arquivo Limpo e Arquivo Inexistente

| ID | Descricao | Fixture | Resultado |
|----|-----------|---------|-----------|
| TC-RE-020 | Arquivo sem problemas retorna array vazio | clean.cs | `[]`, exit 0 |
| TC-RE-021 | Arquivo inexistente retorna issue FILE_NOT_FOUND | nao_existe.cs | issue com `rule_id: FILE_NOT_FOUND`, exit 1 |

**TC-RE-020**

Comando:
```bash
python rule_engine.py tests/fixtures/clean.cs --format json
```

Resultado esperado:
- Exit code: `0`
- JSON e `[]`

**TC-RE-021**

Comando:
```bash
python rule_engine.py tests/fixtures/nao_existe.cs --format json
```

Resultado esperado:
- Exit code: `1`
- JSON contem objeto com `"rule_id": "FILE_NOT_FOUND"` e `"severity": "error"`

---

### Filtragem de Comentarios (Sem Falsos Positivos)

| ID | Descricao | Fixture (inline) | Resultado |
|----|-----------|-----------------|-----------|
| TC-RE-022 | Padrao em comentario `//` nao dispara issue | inline | `[]`, exit 0 |
| TC-RE-023 | Duplicata na mesma linha nao gera dois registros | inline | apenas 1 issue por linha por regra |

**TC-RE-022**

Pre-condicao: criar arquivo:
```csharp
// tests/fixtures/comment_false_positive.cs
public class Exemplo
{
    // Console.WriteLine - apenas um comentario, nao deve disparar
    // password = "teste123" - apenas documentacao
    public void MetodoVazio() { }
}
```

Comando:
```bash
python rule_engine.py tests/fixtures/comment_false_positive.cs --format json
```

Resultado esperado:
- Exit code: `0`
- JSON e `[]`

---

### Formato de Saida TEXT

| ID | Descricao | Fixture | Resultado |
|----|-----------|---------|-----------|
| TC-RE-024 | Formato text mostra icone correto por severidade | secrets.cs | linha com `🔴` |
| TC-RE-025 | Formato text mostra linha correta no formato `L{n}` | deadlock.cs | linha com `L` seguido de numero |

**TC-RE-024**

Comando:
```bash
python rule_engine.py tests/fixtures/secrets.cs --format text
```

Resultado esperado:
- Exit code: `1`
- Saida contem `🔴`
- Saida contem `[Secrets Hardcoded]`
- Saida contem linha de sumario com contagem de issues

---

**Total de casos TC-RE: 25**

---

## TC-ME — metrics.py

**Criterios de aceite**: O script deve calcular corretamente as metricas de metodos, nesting, dependencias e God Class, e retornar exit 1 quando qualquer issue for detectada.

### Arquivo Limpo

| ID | Descricao | Fixture | Resultado |
|----|-----------|---------|-----------|
| TC-ME-001 | Arquivo limpo retorna issues vazio | clean.cs | `issues: []`, exit 0 |

**TC-ME-001**

Comando:
```bash
python metrics.py tests/fixtures/clean.cs --format json
```

Resultado esperado:
- Exit code: `0`
- JSON com estrutura `{file, total_lines, classes, issues: []}`
- `issues` e array vazio
- `total_lines` e um inteiro positivo

---

### Deteccao de Metodo Longo

| ID | Descricao | Fixture | Resultado |
|----|-----------|---------|-----------|
| TC-ME-002 | Metodo com mais de 30 linhas dispara issue "Metodo Longo" | long_methods.cs | issue categoria "Metodo Longo" |
| TC-ME-003 | Saida JSON contem nome correto do metodo e linha de inicio | long_methods.cs | `message` contem `GenerateFullReport` |

**TC-ME-002 / TC-ME-003**

Comando:
```bash
python metrics.py tests/fixtures/long_methods.cs --format json
```

Resultado esperado:
- Exit code: `1`
- `issues` contem objeto com `"category": "Metodo Longo"` (ou equivalente em portugues)
- `message` menciona o metodo `GenerateFullReport`
- `message` menciona `30` como limite

---

### Deteccao de Deep Nesting

| ID | Descricao | Fixture | Resultado |
|----|-----------|---------|-----------|
| TC-ME-004 | Nesting acima de 3 dispara issue "Deep Nesting" | deep_nesting.cs | issue categoria "Deep Nesting" |
| TC-ME-005 | Valor de nesting e reportado na mensagem | deep_nesting.cs | `message` contem numero > 3 |

**TC-ME-004 / TC-ME-005**

Comando:
```bash
python metrics.py tests/fixtures/deep_nesting.cs --format json
```

Resultado esperado:
- Exit code: `1`
- `issues` contem objeto com `"category": "Deep Nesting"`
- `classes[0].max_nesting` e maior que `3`

---

### Deteccao de God Class — Dependencias

| ID | Descricao | Fixture | Resultado |
|----|-----------|---------|-----------|
| TC-ME-006 | Mais de 5 dependencias injetadas dispara issue God Class | god_class.cs | issue categoria "God Class" |
| TC-ME-007 | `constructor_deps` e reportado corretamente no JSON | god_class.cs | `constructor_deps >= 7` |

**TC-ME-006 / TC-ME-007**

Comando:
```bash
python metrics.py tests/fixtures/god_class.cs --format json
```

Resultado esperado:
- Exit code: `1`
- `issues` contem objeto com `"category": "God Class"` relacionado a dependencias
- `classes[0].constructor_deps` e `7` (sete dependencias readonly na fixture)

---

### Deteccao de God Class — Metodos Publicos

| ID | Descricao | Fixture | Resultado |
|----|-----------|---------|-----------|
| TC-ME-008 | Mais de 10 metodos publicos dispara issue God Class | god_class.cs | segunda issue de God Class |
| TC-ME-009 | `public_method_count` e reportado corretamente | god_class.cs | `public_method_count >= 12` |

**TC-ME-008 / TC-ME-009**

Resultado esperado (mesmo comando do TC-ME-006):
- `issues` contem pelo menos 2 objetos com `"category": "God Class"` (um para deps, um para metodos publicos)
- `classes[0].public_method_count` e maior que `10`

---

### Formato Text

| ID | Descricao | Fixture | Resultado |
|----|-----------|---------|-----------|
| TC-ME-010 | Formato text mostra sumario legivel | god_class.cs | saida contem "Dependencias injetadas" e "metodos publicos" |
| TC-ME-011 | Arquivo sem issues mostra mensagem positiva | clean.cs | saida contem "dentro dos padroes" |

**TC-ME-010**

Comando:
```bash
python metrics.py tests/fixtures/god_class.cs --format text
```

Resultado esperado:
- Exit code: `1`
- Saida contem linha com `Dependencias injetadas:`
- Saida contem secao `Issues`

**TC-ME-011**

Comando:
```bash
python metrics.py tests/fixtures/clean.cs --format text
```

Resultado esperado:
- Exit code: `0`
- Saida contem texto indicando conformidade (ex: `dentro dos padroes`)

---

### Arquivo Inexistente

| ID | Descricao | Resultado |
|----|-----------|-----------|
| TC-ME-012 | Arquivo inexistente retorna issue de erro e exit 1 | `issues` com erro de arquivo, exit 1 |

**TC-ME-012**

Comando:
```bash
python metrics.py tests/fixtures/nao_existe.cs --format json
```

Resultado esperado:
- Exit code: `1`
- `issues` contem objeto com `"category": "File"` e mensagem indicando arquivo nao encontrado

---

### Estrutura do JSON de Saida

| ID | Descricao | Resultado |
|----|-----------|-----------|
| TC-ME-013 | JSON contem todos os campos obrigatorios | `file`, `total_lines`, `classes`, `issues` presentes |
| TC-ME-014 | Cada classe contem `methods`, `constructor_deps`, `public_method_count`, `max_nesting` | Campos presentes e com tipos corretos |

**TC-ME-013 / TC-ME-014**

Comando:
```bash
python metrics.py tests/fixtures/clean.cs --format json
```

Resultado esperado — estrutura minima:
```json
{
  "file": "tests/fixtures/clean.cs",
  "total_lines": <inteiro>,
  "classes": [
    {
      "name": <string>,
      "start_line": <inteiro>,
      "line_count": <inteiro>,
      "methods": [],
      "constructor_deps": <inteiro>,
      "public_method_count": <inteiro>,
      "max_nesting": <inteiro>
    }
  ],
  "issues": []
}
```

---

**Total de casos TC-ME: 14**

---

## TC-DP — diff_parser.py

**Criterios de aceite**: O script deve extrair corretamente os arquivos .cs alterados do git, filtrar arquivos excluidos (Migrations, obj, bin, Designer.cs) e retornar exit 1 apenas com `--files-only` quando nenhum arquivo for encontrado.

> **Nota**: Os testes de diff_parser.py dependem de um repositorio git com commits ou arquivos staged. Os cenarios abaixo descrevem as condicoes necessarias e o comportamento esperado. Para execucao em ambiente de CI, preparar o estado do repositorio conforme a pre-condicao de cada caso.

---

### Filtro de Extensao e Exclusao

| ID | Descricao | Resultado |
|----|-----------|-----------|
| TC-DP-001 | Arquivos `.cs` em `/Migrations/` sao excluidos | arquivo nao aparece na lista |
| TC-DP-002 | Arquivos `.Designer.cs` sao excluidos | arquivo nao aparece na lista |
| TC-DP-003 | Arquivos em `/obj/` e `/bin/` sao excluidos | arquivos nao aparecem |
| TC-DP-004 | `AssemblyInfo.cs` e excluido | arquivo nao aparece |
| TC-DP-005 | Arquivos `.py`, `.json`, `.md` sao excluidos | apenas `.cs` retornam |

**TC-DP-001 a TC-DP-005** — Teste unitario da funcao `_should_include`:

Estes casos podem ser testados diretamente importando o modulo. Criar `tests/test_should_include.py`:

```python
import sys
sys.path.insert(0, '..')
from diff_parser import _should_include

# TC-DP-001
assert _should_include("src/Data/Migrations/20240101_Init.cs") == False

# TC-DP-002
assert _should_include("src/Forms/MainForm.Designer.cs") == False

# TC-DP-003
assert _should_include("src/obj/Debug/Service.cs") == False
assert _should_include("src/bin/Release/App.cs") == False

# TC-DP-004
assert _should_include("Properties/AssemblyInfo.cs") == False

# TC-DP-005
assert _should_include("scripts/build.py") == False
assert _should_include("config.json") == False
assert _should_include("README.md") == False

# Deve incluir
assert _should_include("src/Services/UserService.cs") == True
assert _should_include("src/Controllers/UserController.cs") == True

print("TC-DP-001 a TC-DP-005: PASSOU")
```

Comando:
```bash
python tests/test_should_include.py
```

Resultado esperado:
- Exit code: `0`
- Saida: `TC-DP-001 a TC-DP-005: PASSOU`

---

### Modo Staged

| ID | Descricao | Pre-condicao | Resultado |
|----|-----------|--------------|-----------|
| TC-DP-006 | `--staged` sem arquivos staged retorna `[]` | nenhum arquivo staged | JSON `[]`, exit 0 |
| TC-DP-007 | `--staged --files-only` sem staged retorna exit 1 | nenhum staged | exit 1 |
| TC-DP-008 | `--staged` com arquivo .cs staged retorna o arquivo | arquivo .cs no staging area | JSON com caminho do arquivo |

**TC-DP-006**

Pre-condicao: nenhum arquivo staged (usar repositorio limpo).

Comando:
```bash
python diff_parser.py --staged --format json
```

Resultado esperado:
- Exit code: `0`
- Saida: `[]`

**TC-DP-007**

Comando:
```bash
python diff_parser.py --staged --files-only --format json
```

Resultado esperado:
- Exit code: `1`
- Saida: `[]`

---

### Modo Branch

| ID | Descricao | Resultado |
|----|-----------|-----------|
| TC-DP-009 | Sem argumentos, executa diff contra `origin/main` | retorna lista de .cs ou `[]` |
| TC-DP-010 | `--base origin/develop` usa branch correto como base | retorna lista sem erro de execucao |
| TC-DP-011 | `--files-only --format text` imprime um arquivo por linha | cada linha e um caminho de arquivo |

**TC-DP-011**

Pre-condicao: branch atual com pelo menos 1 arquivo .cs diferente da base.

Comando:
```bash
python diff_parser.py --staged --files-only --format text
```

Resultado esperado (quando ha arquivos staged):
- Um caminho por linha
- Todos os caminhos terminam em `.cs`
- Nenhum caminho contem `/Migrations/`, `/obj/`, `/bin/`

---

### Formato for-ai

| ID | Descricao | Resultado |
|----|-----------|-----------|
| TC-DP-012 | `--for-ai` gera saida legivel com `=== arquivo ===` e linhas prefixadas | formato especifico para IA |

**TC-DP-012**

Pre-condicao: branch com arquivo .cs staged ou alterado.

Comando:
```bash
python diff_parser.py --staged --for-ai
```

Resultado esperado:
- Saida contem `=== ` seguido do nome do arquivo
- Linhas adicionadas prefixadas com `+`
- Linhas de contexto prefixadas com espaco

---

### JSON Estruturado

| ID | Descricao | Resultado |
|----|-----------|-----------|
| TC-DP-013 | JSON de saida contem `file`, `lines_added` e `changes` | estrutura correta |
| TC-DP-014 | Cada change contem `file`, `line`, `content` e `change_type` | campos obrigatorios presentes |

**TC-DP-013 / TC-DP-014**

Pre-condicao: branch com arquivo .cs staged.

Comando:
```bash
python diff_parser.py --staged --format json
```

Resultado esperado — estrutura minima:
```json
[
  {
    "file": "<caminho>.cs",
    "lines_added": <inteiro>,
    "changes": [
      {
        "file": "<caminho>.cs",
        "line": <inteiro>,
        "content": "<texto da linha>",
        "change_type": "added"
      }
    ]
  }
]
```

---

**Total de casos TC-DP: 14**

---

## TC-AI — ai_client.py

**Criterios de aceite**: O script deve sempre retornar exit 0 (mesmo sem IA disponivel), retornar JSON valido com `--format json`, listar provedores corretamente e usar fallback quando o provedor primario estiver indisponivel.

> **Nota**: Testes que dependem de API real (Gemini, Claude, OpenAI) requerem chaves configuradas. Os cenarios marcados com `[SEM API]` funcionam sem nenhuma chave configurada e sem Ollama rodando.

---

### Sem Nenhum Provedor Disponivel [SEM API]

| ID | Descricao | Pre-condicao | Resultado |
|----|-----------|--------------|-----------|
| TC-AI-001 | Com nenhuma API key e sem Ollama, retorna exit 0 | sem keys, sem Ollama | exit 0 |
| TC-AI-002 | `--format json` retorna `ai_available: false` | sem keys, sem Ollama | JSON valido |
| TC-AI-003 | `--format text` explica como configurar provedores | sem keys, sem Ollama | texto de instrucoes |

**TC-AI-001**

Pre-condicao: garantir que `GEMINI_API_KEY`, `ANTHROPIC_API_KEY` e `OPENAI_API_KEY` nao estao definidas e Ollama nao esta rodando.

Comando:
```bash
python ai_client.py tests/fixtures/clean.cs
```

Resultado esperado:
- Exit code: `0`
- Saida contem aviso de nenhum provedor disponivel
- Nao lanca excecao

**TC-AI-002**

Comando:
```bash
python ai_client.py tests/fixtures/clean.cs --format json
```

Resultado esperado:
- Exit code: `0`
- JSON valido com:
  ```json
  {
    "file": "tests/fixtures/clean.cs",
    "ai_available": false,
    "provider": null,
    "model": null,
    "analysis": null,
    "elapsed_seconds": 0
  }
  ```

**TC-AI-003**

Comando:
```bash
python ai_client.py tests/fixtures/clean.cs --format text
```

Resultado esperado:
- Saida contem `GEMINI_API_KEY` ou `ANTHROPIC_API_KEY` ou `OPENAI_API_KEY`
- Saida contem `ollama`

---

### Listagem de Provedores [SEM API]

| ID | Descricao | Pre-condicao | Resultado |
|----|-----------|--------------|-----------|
| TC-AI-004 | `--list-providers` sem nenhuma API retorna mensagem "nenhum disponivel" | sem keys | exit 0 + mensagem |
| TC-AI-005 | `--list-providers` com GEMINI_API_KEY configurada inclui "gemini" | GEMINI_API_KEY definida | "gemini" na lista |

**TC-AI-004**

Comando:
```bash
python ai_client.py tests/fixtures/clean.cs --list-providers
```

Resultado esperado:
- Exit code: `0`
- Saida contem "Nenhum provedor" ou lista vazia

---

### Arquivo Inexistente [SEM API]

| ID | Descricao | Resultado |
|----|-----------|-----------|
| TC-AI-006 | Arquivo inexistente retorna exit 1 com mensagem de erro | exit 1, stderr com "nao encontrado" |

**TC-AI-006**

Comando:
```bash
python ai_client.py tests/fixtures/nao_existe.cs
```

Resultado esperado:
- Exit code: `1`
- Stderr contem "nao encontrado" ou similar

---

### Configuracao via config.json [SEM API]

| ID | Descricao | Resultado |
|----|-----------|-----------|
| TC-AI-007 | config.json invalido usa configuracao padrao | script executa sem erro |
| TC-AI-008 | config.json com `primary: "none"` nao tenta nenhum provedor | `ai_available: false` |

**TC-AI-007**

Pre-condicao: renomear temporariamente `config.json` para `config.json.bak`.

Comando:
```bash
python ai_client.py tests/fixtures/clean.cs --format json
```

Resultado esperado:
- Exit code: `0`
- JSON valido (usa DEFAULT_CONFIG interno)

Pos-condicao: restaurar `config.json.bak` para `config.json`.

---

### Fallback entre Provedores

| ID | Descricao | Pre-condicao | Resultado |
|----|-----------|--------------|-----------|
| TC-AI-009 | Quando primario falha, usa fallback | primario com key invalida | `is_fallback: true` na saida |

**TC-AI-009**

Pre-condicao: definir `GEMINI_API_KEY` com valor invalido e Ollama rodando localmente.

Resultado esperado no JSON:
- `"is_fallback": true`
- `"provider": "ollama"`
- `"warning"` contem texto sobre fallback

---

**Total de casos TC-AI: 9**

---

## TC-RU — runner.py

**Criterios de aceite**: O runner deve orquestrar corretamente rule_engine e metrics, calcular o Risk Score, respeitar `--fail-on`, resolver arquivos por nome parcial e retornar JSON valido no modo CI/CD.

---

### Analise de Arquivo Especifico

| ID | Descricao | Fixture | Resultado |
|----|-----------|---------|-----------|
| TC-RU-001 | `--file` com caminho exato executa analise completa | sql_injection.cs | relatorio com issues, exit 1 |
| TC-RU-002 | `--file` com nome parcial resolve para arquivo correto | `sql_injection.cs` (sem prefixo) | mesmo resultado que caminho exato |
| TC-RU-003 | `--file` com arquivo inexistente reporta erro | nao_existe.cs | issue de arquivo, exit 1 |

**TC-RU-001**

Comando:
```bash
python runner.py --file tests/fixtures/sql_injection.cs --rules-only --format text
```

Resultado esperado:
- Exit code: `1`
- Saida contem `SQL Injection`
- Saida contem `Risk Score`
- Saida contem `Risco Critico` ou `Alto Risco`

**TC-RU-002**

Comando (executado a partir de `code_guardian/`):
```bash
python runner.py --file sql_injection.cs --rules-only --format text
```

Resultado esperado:
- Exit code: `1`
- Mesmo conteudo do TC-RU-001 (o `_resolve_file` encontra pelo nome)

**TC-RU-003**

Comando:
```bash
python runner.py --file tests/fixtures/nao_existe.cs --rules-only --format text
```

Resultado esperado:
- Exit code: `1`
- Saida menciona o arquivo

---

### Risk Score

| ID | Descricao | Fixture | Resultado |
|----|-----------|---------|-----------|
| TC-RU-004 | Arquivo limpo tem Risk Score 0 e classificacao "Baixo Risco" | clean.cs | `score <= 10`, label "Baixo Risco" |
| TC-RU-005 | Arquivo com SQL Injection tem Risk Score >= 25 | sql_injection.cs | `score >= 25`, label "Alto Risco" ou "Critico" |
| TC-RU-006 | Calculo correto: critical=25, error=10, warning=3, info=1 | inline | score calculado corretamente |

**TC-RU-004**

Comando:
```bash
python runner.py --file tests/fixtures/clean.cs --rules-only --format json
```

Resultado esperado:
- Exit code: `0`
- `"risk_score"` entre `0` e `10`
- `"risk_label"` contem "Baixo"

**TC-RU-005**

Comando:
```bash
python runner.py --file tests/fixtures/sql_injection.cs --rules-only --format json
```

Resultado esperado:
- Exit code: `1`
- `"risk_score"` maior que `24`
- `"risk_label"` contem "Alto" ou "Critico"
- `"has_blockers": true`

---

### Flag --rules-only

| ID | Descricao | Resultado |
|----|-----------|-----------|
| TC-RU-007 | `--rules-only` nao chama ai_client.py | relatorio sem secao "Analise de IA" |
| TC-RU-008 | Sem `--rules-only` e sem IA disponivel, relatorio nao quebra | relatorio completo sem IA, exit respeitando --fail-on |

**TC-RU-007**

Comando:
```bash
python runner.py --file tests/fixtures/deadlock.cs --rules-only --format text
```

Resultado esperado:
- Saida nao contem `"Analise de IA"` como secao com conteudo de IA
- Execucao conclui sem aguardar timeout de IA

---

### Flag --severity

| ID | Descricao | Fixture | Resultado |
|----|-----------|---------|-----------|
| TC-RU-009 | `--severity error` exclui warnings e infos do relatorio | todo_comment.cs | sem issues de TODO no relatorio |
| TC-RU-010 | `--severity critical` reporta apenas criticals | secrets.cs | apenas critical no JSON |

**TC-RU-009**

Comando:
```bash
python runner.py --file tests/fixtures/todo_comment.cs --rules-only --severity error --format json
```

Resultado esperado:
- Exit code: `0`
- `"summary"` com `info: 0` e `warning: 0`
- `"has_blockers": false`

---

### Flag --fail-on

| ID | Descricao | Fixture | Resultado |
|----|-----------|---------|-----------|
| TC-RU-011 | `--fail-on error` (padrao) — warning nao causa exit 1 | console_warning.cs | exit 0 |
| TC-RU-012 | `--fail-on warning` — warning causa exit 1 | console_warning.cs | exit 1 |
| TC-RU-013 | `--fail-on critical` — error nao causa exit 1 | deadlock.cs | exit 0 |

**TC-RU-011**

Comando:
```bash
python runner.py --file tests/fixtures/console_warning.cs --rules-only --fail-on error
```

Resultado esperado:
- Exit code: `0` (apenas warnings presentes, nao ha errors)

**TC-RU-012**

Comando:
```bash
python runner.py --file tests/fixtures/console_warning.cs --rules-only --fail-on warning
```

Resultado esperado:
- Exit code: `1` (warnings causam falha com `--fail-on warning`)

**TC-RU-013**

Comando:
```bash
python runner.py --file tests/fixtures/deadlock.cs --rules-only --fail-on critical
```

Resultado esperado:
- Exit code: `0` (errors presentes mas `--fail-on critical` so falha em critical)

---

### Formato JSON para CI/CD

| ID | Descricao | Fixture | Resultado |
|----|-----------|---------|-----------|
| TC-RU-014 | `--format json` retorna JSON valido parsavel | sql_injection.cs | JSON com `risk_score`, `has_blockers`, `files`, `summary` |
| TC-RU-015 | Campo `summary` contem contagens por severidade | sql_injection.cs | `critical`, `error`, `warning`, `info` presentes |
| TC-RU-016 | Campo `files` e array com detalhes por arquivo | sql_injection.cs | cada item tem `file`, `issues`, `metrics` |

**TC-RU-014**

Comando:
```bash
python runner.py --file tests/fixtures/sql_injection.cs --rules-only --format json
```

Resultado esperado — estrutura minima:
```json
{
  "risk_score": <inteiro>,
  "risk_label": "<string>",
  "has_blockers": true,
  "files_analyzed": ["<caminho>"],
  "summary": {
    "critical": <inteiro>,
    "error": <inteiro>,
    "warning": <inteiro>,
    "info": <inteiro>
  },
  "files": [
    {
      "file": "<caminho>",
      "issues": [ ... ],
      "metrics": { ... }
    }
  ]
}
```

---

### Nenhum Arquivo Encontrado

| ID | Descricao | Resultado |
|----|-----------|-----------|
| TC-RU-017 | Sem arquivos staged e sem `--file`, imprime mensagem informativa e exit 0 | mensagem "Nenhum arquivo .cs encontrado", exit 0 |
| TC-RU-018 | `--format json` com lista vazia retorna JSON com `files_analyzed: []` | JSON valido, exit 0 |

**TC-RU-017**

Pre-condicao: nenhum arquivo .cs staged, branch sem alteracoes vs base.

Comando:
```bash
python runner.py --staged --rules-only --format text
```

Resultado esperado:
- Exit code: `0`
- Saida contem "Nenhum arquivo .cs" ou similar

---

**Total de casos TC-RU: 18**

---

## Testes de Integracao

**Criterios de aceite**: O runner deve orquestrar corretamente todos os scripts em cenarios reais de uso, produzindo relatorios completos e exit codes corretos para uso em pipelines CI/CD.

---

### Integracao Completa: Rule Engine + Metrics

| ID | Descricao | Fixture | Resultado |
|----|-----------|---------|-----------|
| TC-INT-001 | God class dispara issues de rule_engine E de metrics no mesmo relatorio | god_class.cs | relatorio tem issues de ambas as fontes |
| TC-INT-002 | `source` diferencia issues de `rule_engine` e `metrics` | god_class.cs | campo `source` e `"rule_engine"` ou `"metrics"` |
| TC-INT-003 | Risk Score acumula pontuacao de rule_engine e metrics | god_class.cs | `risk_score` maior que 0 |

**TC-INT-001**

Comando:
```bash
python runner.py --file tests/fixtures/god_class.cs --rules-only --format json
```

Resultado esperado:
- Exit code: `1`
- Em `files[0].issues`, existem objetos com `"source": "rule_engine"` e objetos com `"source": "metrics"`

**TC-INT-002**

Mesmo comando acima. Verificar que campo `source` existe em todos os objetos de issues.

---

### Pipeline CI/CD Simulado

| ID | Descricao | Fixtures | Resultado |
|----|-----------|----------|-----------|
| TC-INT-004 | PR sem problemas — pipeline aprova | clean.cs | exit 0, `has_blockers: false` |
| TC-INT-005 | PR com SQL Injection — pipeline bloqueia | sql_injection.cs | exit 1, `has_blockers: true` |
| TC-INT-006 | PR com apenas warnings — pipeline aprova com `--fail-on error` | console_warning.cs | exit 0 |
| TC-INT-007 | PR com apenas warnings — pipeline bloqueia com `--fail-on warning` | console_warning.cs | exit 1 |

**TC-INT-004** — Pipeline verde

Comando:
```bash
python runner.py --file tests/fixtures/clean.cs --rules-only --format json --fail-on error
echo "Exit code: $?"
```

Resultado esperado:
- `Exit code: 0`
- JSON com `"has_blockers": false`

**TC-INT-005** — Pipeline vermelho

Comando:
```bash
python runner.py --file tests/fixtures/sql_injection.cs --rules-only --format json --fail-on error
echo "Exit code: $?"
```

Resultado esperado:
- `Exit code: 1`
- JSON com `"has_blockers": true`
- `"summary"."critical"` maior que `0`

---

### Multiplos Arquivos Simultaneos

| ID | Descricao | Resultado |
|----|-----------|-----------|
| TC-INT-008 | Runner processa lista de arquivos e agrega todos os resultados | `files_analyzed` com multiplos arquivos |
| TC-INT-009 | Risk Score reflete soma de todos os arquivos | score maior do que analise individual |

**TC-INT-008** — Simulado via staged files com dois arquivos.

Alternativa sem git: passar arquivos via chamada programatica ao `run_review`:

```python
# tests/test_multi_file.py
import sys
sys.path.insert(0, '..')
from runner import run_review

files = [
    'tests/fixtures/clean.cs',
    'tests/fixtures/sql_injection.cs'
]
report, has_blockers = run_review(files=files, severity='info', rules_only=True, output_format='json')

import json
data = json.loads(report)

assert len(data['files_analyzed']) == 2, "Deve analisar 2 arquivos"
assert data['has_blockers'] == True, "Deve detectar bloqueadores"
assert data['risk_score'] > 0, "Risk score deve ser positivo"

print("TC-INT-008 / TC-INT-009: PASSOU")
```

Comando:
```bash
python tests/test_multi_file.py
```

---

### Resolucao de Arquivo por Nome Parcial

| ID | Descricao | Resultado |
|----|-----------|-----------|
| TC-INT-010 | `_resolve_file` encontra arquivo pelo nome sem caminho completo | arquivo correto resolvido |
| TC-INT-011 | `_resolve_file` com caminho exato retorna o mesmo caminho | sem modificacao |
| TC-INT-012 | `_resolve_file` com arquivo ambiguo avisa e usa o primeiro | aviso no stdout, analise continua |

**TC-INT-010 / TC-INT-011**

```python
# tests/test_resolve_file.py
import sys
sys.path.insert(0, '..')
from runner import _resolve_file
from pathlib import Path

# TC-INT-011: caminho exato
caminho = 'tests/fixtures/clean.cs'
resultado = _resolve_file(caminho)
assert Path(resultado).exists(), f"Arquivo nao encontrado: {resultado}"

# TC-INT-010: nome parcial
resultado2 = _resolve_file('clean.cs')
assert Path(resultado2).exists(), f"Resolucao por nome parcial falhou: {resultado2}"

print("TC-INT-010 / TC-INT-011: PASSOU")
```

---

**Total de casos TC-INT: 12**

---

## Script de Execucao Automatizada

Salvar como `code_guardian/tests/run_tests.sh` e executar a partir do diretorio `code_guardian/`.

```bash
#!/usr/bin/env bash
# Script de execucao automatizada dos testes do Code Guardian
# Uso: bash tests/run_tests.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
FIXTURES="$SCRIPT_DIR/fixtures"
PASS=0
FAIL=0
ERRORS=()

cd "$ROOT_DIR"

log_pass() { echo "[PASS] $1"; PASS=$((PASS + 1)); }
log_fail() { echo "[FAIL] $1"; FAIL=$((FAIL + 1)); ERRORS+=("$1"); }

check_exit() {
    local id="$1"
    local expected="$2"
    local actual="$3"
    if [ "$actual" -eq "$expected" ]; then
        log_pass "$id (exit=$actual)"
    else
        log_fail "$id (esperado exit=$expected, obtido exit=$actual)"
    fi
}

check_json_contains() {
    local id="$1"
    local json="$2"
    local key="$3"
    if echo "$json" | python -c "import sys,json; d=json.load(sys.stdin); assert '$key' in str(d)" 2>/dev/null; then
        log_pass "$id (contem '$key')"
    else
        log_fail "$id (nao contem '$key')"
    fi
}

echo "============================================="
echo "  Code Guardian — Suite de Testes"
echo "============================================="
echo ""

# ---------------------------------------------------------------------------
echo "--- rule_engine.py ---"

# TC-RE-001 / TC-RE-002: SQL Injection
OUTPUT=$(python rule_engine.py "$FIXTURES/sql_injection.cs" --format json 2>/dev/null); RC=$?
check_exit "TC-RE-001/002" 1 $RC
check_json_contains "TC-RE-001" "$OUTPUT" "SQL_INJECTION_CONCAT"

# TC-RE-003 / TC-RE-004: Deadlocks
OUTPUT=$(python rule_engine.py "$FIXTURES/deadlock.cs" --format json 2>/dev/null); RC=$?
check_exit "TC-RE-003/004" 1 $RC
check_json_contains "TC-RE-003" "$OUTPUT" "TASK_RESULT_DEADLOCK"
check_json_contains "TC-RE-004" "$OUTPUT" "TASK_WAIT_DEADLOCK"

# TC-RE-005: async void
OUTPUT=$(python rule_engine.py "$FIXTURES/async_void.cs" --format json 2>/dev/null); RC=$?
check_exit "TC-RE-005" 1 $RC
check_json_contains "TC-RE-005" "$OUTPUT" "ASYNC_VOID"

# TC-RE-007 / TC-RE-008: Secrets
OUTPUT=$(python rule_engine.py "$FIXTURES/secrets.cs" --format json 2>/dev/null); RC=$?
check_exit "TC-RE-007/008" 1 $RC
check_json_contains "TC-RE-007" "$OUTPUT" "HARDCODED_PASSWORD"
check_json_contains "TC-RE-008" "$OUTPUT" "HARDCODED_API_KEY"

# TC-RE-009 / TC-RE-010: Empty catch
OUTPUT=$(python rule_engine.py "$FIXTURES/empty_catch.cs" --format json 2>/dev/null); RC=$?
check_exit "TC-RE-009/010" 1 $RC
check_json_contains "TC-RE-009" "$OUTPUT" "EMPTY_CATCH"

# TC-RE-011 / TC-RE-012: Console.WriteLine
OUTPUT=$(python rule_engine.py "$FIXTURES/console_warning.cs" --format json 2>/dev/null); RC=$?
check_exit "TC-RE-011/012" 0 $RC
check_json_contains "TC-RE-011" "$OUTPUT" "CONSOLE_WRITELINE"
check_json_contains "TC-RE-012" "$OUTPUT" "CONSOLE_WRITE"

# TC-RE-013/014/015: TODO / FIXME / HACK
OUTPUT=$(python rule_engine.py "$FIXTURES/todo_comment.cs" --format json 2>/dev/null); RC=$?
check_exit "TC-RE-013/014/015" 0 $RC
check_json_contains "TC-RE-013" "$OUTPUT" "TODO_COMMENT"
check_json_contains "TC-RE-014" "$OUTPUT" "FIXME_COMMENT"
check_json_contains "TC-RE-015" "$OUTPUT" "HACK_COMMENT"

# TC-RE-016: HttpClient new
OUTPUT=$(python rule_engine.py "$FIXTURES/httpclient_new.cs" --format json 2>/dev/null); RC=$?
check_exit "TC-RE-016" 0 $RC
check_json_contains "TC-RE-016" "$OUTPUT" "HTTPCLIENT_NEW"

# TC-RE-017: --severity error filtra info
OUTPUT=$(python rule_engine.py "$FIXTURES/todo_comment.cs" --format json --severity error 2>/dev/null); RC=$?
check_exit "TC-RE-017" 0 $RC
if [ "$OUTPUT" = "[]" ]; then log_pass "TC-RE-017 (array vazio)"; else log_fail "TC-RE-017 (esperado [])"; fi

# TC-RE-020: arquivo limpo
OUTPUT=$(python rule_engine.py "$FIXTURES/clean.cs" --format json 2>/dev/null); RC=$?
check_exit "TC-RE-020" 0 $RC
if [ "$OUTPUT" = "[]" ]; then log_pass "TC-RE-020 (array vazio)"; else log_fail "TC-RE-020 (esperado [])"; fi

# TC-RE-021: arquivo inexistente
OUTPUT=$(python rule_engine.py "$FIXTURES/nao_existe.cs" --format json 2>/dev/null); RC=$?
check_exit "TC-RE-021" 1 $RC
check_json_contains "TC-RE-021" "$OUTPUT" "FILE_NOT_FOUND"

echo ""
# ---------------------------------------------------------------------------
echo "--- metrics.py ---"

# TC-ME-001: arquivo limpo
OUTPUT=$(python metrics.py "$FIXTURES/clean.cs" --format json 2>/dev/null); RC=$?
check_exit "TC-ME-001" 0 $RC
if echo "$OUTPUT" | python -c "import sys,json; d=json.load(sys.stdin); assert d['issues']==[]" 2>/dev/null; then
    log_pass "TC-ME-001 (issues vazio)"
else
    log_fail "TC-ME-001 (issues nao esta vazio)"
fi

# TC-ME-002/003: metodo longo
OUTPUT=$(python metrics.py "$FIXTURES/long_methods.cs" --format json 2>/dev/null); RC=$?
check_exit "TC-ME-002" 1 $RC
check_json_contains "TC-ME-002" "$OUTPUT" "Metodo Longo"

# TC-ME-004/005: deep nesting
OUTPUT=$(python metrics.py "$FIXTURES/deep_nesting.cs" --format json 2>/dev/null); RC=$?
check_exit "TC-ME-004" 1 $RC
check_json_contains "TC-ME-004" "$OUTPUT" "Deep Nesting"

# TC-ME-006/007: god class deps
OUTPUT=$(python metrics.py "$FIXTURES/god_class.cs" --format json 2>/dev/null); RC=$?
check_exit "TC-ME-006" 1 $RC
check_json_contains "TC-ME-006" "$OUTPUT" "God Class"

# TC-ME-012: arquivo inexistente
OUTPUT=$(python metrics.py "$FIXTURES/nao_existe.cs" --format json 2>/dev/null); RC=$?
check_exit "TC-ME-012" 1 $RC
check_json_contains "TC-ME-012" "$OUTPUT" "nao encontrado"

echo ""
# ---------------------------------------------------------------------------
echo "--- runner.py ---"

# TC-RU-001: arquivo especifico com caminho completo
OUTPUT=$(python runner.py --file "$FIXTURES/sql_injection.cs" --rules-only --format json 2>/dev/null); RC=$?
check_exit "TC-RU-001" 1 $RC
check_json_contains "TC-RU-001" "$OUTPUT" "has_blockers"

# TC-RU-004: risk score arquivo limpo
OUTPUT=$(python runner.py --file "$FIXTURES/clean.cs" --rules-only --format json 2>/dev/null); RC=$?
check_exit "TC-RU-004" 0 $RC
if echo "$OUTPUT" | python -c "import sys,json; d=json.load(sys.stdin); assert d['risk_score']<=10" 2>/dev/null; then
    log_pass "TC-RU-004 (risk_score <= 10)"
else
    log_fail "TC-RU-004 (risk_score > 10 para arquivo limpo)"
fi

# TC-RU-011: --fail-on error com apenas warnings
OUTPUT=$(python runner.py --file "$FIXTURES/console_warning.cs" --rules-only --fail-on error 2>/dev/null); RC=$?
check_exit "TC-RU-011" 0 $RC

# TC-RU-012: --fail-on warning com warnings
OUTPUT=$(python runner.py --file "$FIXTURES/console_warning.cs" --rules-only --fail-on warning 2>/dev/null); RC=$?
check_exit "TC-RU-012" 1 $RC

# TC-RU-013: --fail-on critical com errors
OUTPUT=$(python runner.py --file "$FIXTURES/deadlock.cs" --rules-only --fail-on critical 2>/dev/null); RC=$?
check_exit "TC-RU-013" 0 $RC

# TC-RU-014: formato json CI/CD
OUTPUT=$(python runner.py --file "$FIXTURES/sql_injection.cs" --rules-only --format json 2>/dev/null); RC=$?
for field in risk_score risk_label has_blockers files_analyzed summary; do
    check_json_contains "TC-RU-014-$field" "$OUTPUT" "$field"
done

echo ""
# ---------------------------------------------------------------------------
echo "--- ai_client.py (sem API) ---"

# TC-AI-001: sem API, exit 0
python ai_client.py "$FIXTURES/clean.cs" > /dev/null 2>&1; RC=$?
check_exit "TC-AI-001" 0 $RC

# TC-AI-002: sem API, JSON com ai_available=false
OUTPUT=$(python ai_client.py "$FIXTURES/clean.cs" --format json 2>/dev/null); RC=$?
check_exit "TC-AI-002-exit" 0 $RC
check_json_contains "TC-AI-002" "$OUTPUT" "ai_available"

# TC-AI-006: arquivo inexistente exit 1
python ai_client.py "$FIXTURES/nao_existe.cs" > /dev/null 2>&1; RC=$?
check_exit "TC-AI-006" 1 $RC

echo ""
# ---------------------------------------------------------------------------
echo "============================================="
echo "  RESULTADO FINAL"
echo "============================================="
echo "  PASSOU: $PASS"
echo "  FALHOU: $FAIL"
echo ""
if [ ${#ERRORS[@]} -gt 0 ]; then
    echo "  Falhas:"
    for e in "${ERRORS[@]}"; do
        echo "    - $e"
    done
fi
echo "============================================="

[ $FAIL -eq 0 ] && exit 0 || exit 1
```

### Como Preparar e Executar

```bash
# 1. Entrar no diretorio dos scripts
cd code_guardian

# 2. Criar diretorio de fixtures
mkdir -p tests/fixtures

# 3. Criar cada arquivo .cs de fixture conforme a secao "Fixtures de Teste"
#    (copiar o conteudo de cada bloco de codigo para o arquivo correspondente)

# 4. Tornar o script executavel
chmod +x tests/run_tests.sh

# 5. Executar todos os testes
bash tests/run_tests.sh

# 6. Para executar apenas os testes de um script especifico:
bash -c 'cd code_guardian && python rule_engine.py tests/fixtures/sql_injection.cs --format json'
```

---

## Criterios de Aceite por Script

### rule_engine.py

| Criterio | Verificacao |
|----------|-------------|
| Detecta SQL Injection por concatenacao | `rule_id: SQL_INJECTION_CONCAT` presente |
| Detecta SQL Injection por interpolacao | `rule_id: SQL_INJECTION_CONCAT` presente |
| Detecta `.Result` e `.Wait()` | `TASK_RESULT_DEADLOCK` e `TASK_WAIT_DEADLOCK` |
| Detecta `async void` (nao event handlers) | `ASYNC_VOID` presente |
| Detecta secrets hardcoded | `HARDCODED_PASSWORD` e `HARDCODED_API_KEY` |
| Detecta `catch {}` vazio | `EMPTY_CATCH` presente |
| Detecta `Console.WriteLine` | `CONSOLE_WRITELINE` e `CONSOLE_WRITE` |
| Detecta TODO/FIXME/HACK | `TODO_COMMENT`, `FIXME_COMMENT`, `HACK_COMMENT` |
| Detecta `new HttpClient()` | `HTTPCLIENT_NEW` presente |
| Filtra matches em comentarios | Sem falsos positivos em `//` |
| Evita duplicatas na mesma linha | Um issue por (linha, regra) |
| `--severity error` filtra infos/warnings | Array vazio para arquivo so com TODO |
| Exit 1 para critical ou error | `sys.exit(1)` quando ha bloqueadores |
| Exit 0 para apenas warnings/infos | `sys.exit(0)` para console_warning.cs |
| Arquivo inexistente retorna FILE_NOT_FOUND | Issue especifica, exit 1 |

### metrics.py

| Criterio | Verificacao |
|----------|-------------|
| Detecta metodo > 30 linhas | Issue "Metodo Longo" com nome do metodo |
| Detecta nesting > 3 | Issue "Deep Nesting" com nivel real |
| Detecta > 5 dependencias | Issue "God Class" para constructor deps |
| Detecta > 10 metodos publicos | Issue "God Class" para public methods |
| JSON tem todos os campos obrigatorios | `file`, `total_lines`, `classes`, `issues` |
| Cada classe tem `constructor_deps`, `max_nesting`, `public_method_count` | Campos numericos presentes |
| Arquivo limpo retorna `issues: []` | Array vazio, exit 0 |
| Exit 1 quando ha qualquer issue | Qualquer issue detectada causa exit 1 |
| Arquivo inexistente reportado como error | Issue com categoria File |

### diff_parser.py

| Criterio | Verificacao |
|----------|-------------|
| Exclui `/Migrations/` | Arquivo nao aparece na lista |
| Exclui `.Designer.cs` | Arquivo nao aparece |
| Exclui `/obj/` e `/bin/` | Arquivos nao aparecem |
| Exclui `AssemblyInfo.cs` | Arquivo nao aparece |
| Exclui arquivos nao-.cs | `.py`, `.json`, `.md` excluidos |
| `--files-only` com lista vazia da exit 1 | `sys.exit(1)` |
| `--for-ai` gera formato legivel | Formato `=== arquivo ===` |
| JSON tem `file`, `lines_added`, `changes` | Estrutura correta |
| Cada change tem `line`, `content`, `change_type` | Campos obrigatorios |

### ai_client.py

| Criterio | Verificacao |
|----------|-------------|
| Sempre exit 0 (com ou sem IA) | Nao lanca excecao nao tratada |
| JSON valido quando sem IA | `ai_available: false`, campos nulos |
| Texto de instrucoes quando sem IA | Menciona como configurar |
| `--list-providers` funciona sem crash | Exit 0 |
| Arquivo inexistente causa exit 1 | Mensagem de erro clara |
| config.json invalido usa padrao | Executa sem quebrar |
| Fallback gera `is_fallback: true` | Campo presente quando fallback |

### runner.py

| Criterio | Verificacao |
|----------|-------------|
| `--file` com caminho exato funciona | Relatorio gerado |
| `_resolve_file` encontra por nome parcial | Arquivo correto resolvido |
| Risk Score calculado corretamente | critical=25, error=10, warning=3, info=1 |
| Risk Score <= 10 = "Baixo Risco" | Label correto |
| Risk Score > 60 = "Critico" | Label correto |
| `--rules-only` nao chama IA | Sem timeout de IA |
| `--severity error` filtra infos/warnings | Issues filtradas |
| `--fail-on error` (padrao) — so bloqueia em error+ | Warnings nao causam exit 1 |
| `--fail-on warning` — bloqueia em warning+ | Warning causa exit 1 |
| `--fail-on critical` — so bloqueia em critical | Error nao causa exit 1 |
| `--format json` retorna JSON valido | Parsavel por `json.loads` |
| JSON tem `risk_score`, `has_blockers`, `summary`, `files` | Estrutura completa |
| `has_blockers: true` quando ha critical/error | Campo correto |
| Sem arquivos — exit 0 com mensagem | Nao quebra |

---

## Resumo de Cobertura

| Script | Casos Unitarios | Casos Integracao | Total |
|--------|----------------|------------------|-------|
| rule_engine.py | 25 | — | 25 |
| metrics.py | 14 | — | 14 |
| diff_parser.py | 14 | — | 14 |
| ai_client.py | 9 | — | 9 |
| runner.py | 18 | — | 18 |
| Integracao (runner orquestrando) | — | 12 | 12 |
| **Total** | **80** | **12** | **92** |

### Distribuicao por Tipo

```
Testes Unitarios:    80  (87%)
Testes Integracao:   12  (13%)
Total:               92
```

### Cobertura por Area Funcional

| Area | Casos | Fixtures Necessarias |
|------|-------|---------------------|
| Deteccao de vulnerabilidades (SQL, secrets) | 12 | sql_injection.cs, secrets.cs |
| Deteccao de anti-patterns async | 8 | deadlock.cs, async_void.cs |
| Deteccao de qualidade de codigo | 14 | empty_catch.cs, console_warning.cs, todo_comment.cs, httpclient_new.cs |
| Metricas de estrutura | 14 | long_methods.cs, deep_nesting.cs, god_class.cs, clean.cs |
| Integracao git (diff) | 14 | (estado do repositorio) |
| Cliente IA e fallback | 9 | clean.cs |
| Orquestracao e CI/CD | 21 | todos os acima |

---

> Documento gerado em 2026-03-13. Atualizar apos adicionar novas regras ao `rule_engine.py` ou novos limiares ao `metrics.py`.
