# Git Hooks — Análise Automática no pre-commit e pre-push

## O que faz

Instala hooks git que executam o Code Guardian **automaticamente** em dois momentos do fluxo de trabalho:

| Hook | Quando dispara | Analisa | Velocidade |
| ---- | -------------- | ------- | ---------- |
| `pre-commit` | Antes de cada `git commit` | Arquivos staged (em stage) | < 2s |
| `pre-push` | Antes de cada `git push` | Todos os arquivos alterados | < 2s |

Ambos rodam em **modo estático** (sem IA) para não atrasar o fluxo.

---

## Instalação

```bash
# Instalar os dois hooks (recomendado)
python code_guardian/install_hooks.py install

# Instalar apenas o pre-commit
python code_guardian/install_hooks.py install --pre-commit

# Instalar apenas o pre-push
python code_guardian/install_hooks.py install --pre-push

# Ver o que está instalado
python code_guardian/install_hooks.py status

# Remover ambos os hooks
python code_guardian/install_hooks.py uninstall

# Remover apenas um
python code_guardian/install_hooks.py uninstall --pre-commit
python code_guardian/install_hooks.py uninstall --pre-push
```

---

## Como o pre-commit funciona

Dispara em cada `git commit`. Analisa **só os arquivos em staging area** (os que você deu `git add`).

```text
git add Services/PedidoService.cs
git commit -m "feat: novo método de pagamento"
        ↓
[guardian] Verificando arquivos antes do commit...

  🔴 L42 [SQL_INJECTION_CONCAT] Possível SQL Injection...
  🟠 L87 [TASK_RESULT_DEADLOCK] Task.Result pode causar deadlock...

[guardian] BLOQUEADO: issues criticas encontradas.
   Corrija os problemas ou use: git commit --no-verify
```

Se não houver blockers:

```text
[guardian] Verificando arquivos antes do commit...

[guardian] Nenhum bloqueador. Commit liberado.

[master abc1234] feat: novo método de pagamento
```

Se não houver arquivos `.cs` no stage (apenas `.json`, `.md`, etc.), o hook encerra imediatamente sem fazer nada.

---

## Como o pre-push funciona

Dispara em cada `git push`. Analisa o **diff completo do branch** vs `origin/main` — a barreira final antes do código sair da máquina.

```text
git push origin feature/pagamentos
        ↓
[guardian] Verificando branch antes do push...

  ✅ Nenhum bloqueador encontrado.

[guardian] Push liberado.

Enumerating objects: 5, done.
...
```

---

## Relatório HTML automático

A cada execução do hook, um relatório HTML é gerado automaticamente em `.codeguardian/`:

| Hook | Arquivo gerado |
| ---- | -------------- |
| `pre-commit` | `.codeguardian/last-commit-report.html` |
| `pre-push` | `.codeguardian/last-push-report.html` |

O arquivo é **sempre sobrescrito** — representa o estado do último commit/push analisado.

Quando o commit é **bloqueado**, a mensagem exibe o caminho:

```text
[guardian] BLOQUEADO: issues criticas encontradas.
   Relatorio detalhado: C:/projeto/.codeguardian/last-commit-report.html
   Para pular a verificacao: git commit --no-verify
```

Abra o HTML no browser para ver as issues com cores, métricas por arquivo e Risk Score.

> A pasta `.codeguardian/` está no `.gitignore` — os relatórios são locais e não entram no repositório.

---

## Trailer automático na mensagem do commit

Quando a análise passa (sem blockers), o Code Guardian **injeta automaticamente** um trailer na mensagem do commit com o resultado da análise. O revisor do PR pode verificar que o desenvolvedor rodou o guardian antes de commitar.

Exemplo no `git log`:

```text
feat: implementar validacao de CPF

Guardian-Review: ✅ Passou | Score: 4 | Critical: 0 | Error: 0 | Warning: 1 | Arquivos: 2
```

### Como funciona

O mecanismo usa dois hooks coordenados:

| Hook | Função |
| ---- | ------ |
| `pre-commit` | Executa análise; se passou, grava resumo em `.codeguardian/last-commit-summary.txt` |
| `prepare-commit-msg` | Lê o resumo e appenda como trailer na mensagem do commit |

### Detalhes técnicos

- O trailer **só aparece** quando a análise passou (sem critical/error)
- Se o commit for bloqueado, o summary file é deletado
- O `prepare-commit-msg` verifica se o arquivo tem **menos de 5 minutos** (evita reutilizar resultado de commit anterior quando `--no-verify` é usado depois)
- Em `git commit --amend`, merge e squash, o trailer **não é duplicado**
- O hook `prepare-commit-msg` **não é pulado** por `--no-verify`, mas a verificação de idade do arquivo impede o uso de dados stale

### Instalação

Os dois hooks são instalados juntos automaticamente:

```bash
python code_guardian/install_hooks.py install --pre-commit
# Instala: pre-commit + prepare-commit-msg
```

---

## Pular os hooks (emergências)

```bash
# Pular o pre-commit
git commit --no-verify -m "hotfix urgente"

# Pular o pre-push
git push --no-verify origin main
```

> Use com responsabilidade. O `--no-verify` pula **todos** os hooks, não só o Code Guardian.

---

## Fluxo completo com os hooks instalados

```text
Desenvolvedor escreve código
        ↓
git add Services/PedidoService.cs
        ↓
git commit -m "feat: ..."
        ↓
   [pre-commit hook dispara]
   Analisa arquivos staged
        ↓
   Issues críticas?
   ├── SIM → commit bloqueado → dev corrige → tenta de novo
   └── NÃO → commit realizado
        ↓
git push origin feature/x
        ↓
   [pre-push hook dispara]
   Analisa diff completo do branch
        ↓
   Issues críticas?
   ├── SIM → push bloqueado → dev corrige → tenta de novo
   └── NÃO → push realizado
        ↓
Abre PR no TFS
        ↓
   [Pipeline TFS dispara — ver 14-TFS-Pipeline.md]
   Análise completa (com IA, se configurado)
```

---

## Diferença entre os dois hooks

| Aspecto | pre-commit | pre-push |
| ------- | ---------- | -------- |
| **Quando** | A cada commit | A cada push |
| **O que analisa** | Só arquivos staged | Diff completo do branch |
| **Por que útil** | Feedback imediato, antes de salvar | Barreira final, antes de enviar |
| **Mais granular** | Sim — arquivo por arquivo | Não — analisa o conjunto |
| **Pode ter falso negativo?** | Sim, se o arquivo não estiver staged | Não — pega tudo |

**Recomendação**: instalar os dois. O `pre-commit` dá feedback rápido durante o desenvolvimento; o `pre-push` garante que nada escapou.

---

## Configuração dos hooks

O `pre-commit` executa:

```bash
runner.py --staged --rules-only --severity warning --fail-on error --summary-file .codeguardian/last-commit-summary.txt
```

O `prepare-commit-msg` executa:

```bash
_append_guardian_trailer.py <commit-msg-file> <commit-source>
```

O `pre-push` executa:

```bash
runner.py --rules-only --severity warning --fail-on error
```

Todos usam `--severity warning` (para o HTML mostrar tudo) e `--fail-on error` (bloqueia apenas em critical/error).

---

## Coexistência com hooks existentes

Se já houver um hook no repositório (criado por outra ferramenta), o instalador **avisa e pede confirmação** antes de sobrescrever.

Para **adicionar o Code Guardian a um hook existente sem sobrescrever**, inserir ao final do arquivo:

```sh
# Code Guardian - analise estatica
python code_guardian/runner.py \
  --staged --rules-only --severity error --fail-on error
if [ $? -ne 0 ]; then
    echo "[guardian] BLOQUEADO. Corrija os problemas."
    exit 1
fi
```

---

## Comportamento quando o Code Guardian não está disponível

O hook não bloqueia o fluxo se o próprio Code Guardian falhar:

- Python não instalado → aviso + segue normalmente
- `runner.py` não encontrado → aviso + segue normalmente
- Erro interno no script → segue normalmente

Só bloqueia quando o guardian funciona e encontra issues reais no código.

---

## Documentação relacionada

| Documento | Conteúdo |
| --------- | -------- |
| [16-Fluxo-Desenvolvedor.md](16-Fluxo-Desenvolvedor.md) | Guia completo de uso no dia a dia |
| [13-Runner-CLI.md](13-Runner-CLI.md) | Parâmetros do runner.py |
| [14-TFS-Pipeline.md](14-TFS-Pipeline.md) | Análise automática em PRs no TFS |
| [08-Uso-rule-engine.md](08-Uso-rule-engine.md) | Regras verificadas pelos hooks |
