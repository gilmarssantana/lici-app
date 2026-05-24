# LICI App

Sistema operacional modular da LICI — inteligência viva de licitações.

## MVP 1: LICI Memory Core

Funções implementadas:

- registrar memória;
- listar memórias;
- buscar memórias por termo;
- classificar por tipo;
- persistir em JSON;
- gerar espelho Markdown por tipo;
- preparar interface de serviço para futura migração PostgreSQL.

## Executar

API principal modular:

```bash
cd /root/lici-app/backend
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 127.0.0.1 --port 8100
```

MVP oficial isolado do Memory Core:

```bash
cd /root/lici-app/backend
. .venv/bin/activate
uvicorn app.memory.main:app --host 127.0.0.1 --port 8010
```

## Endpoints

API principal:

- `GET /health`
- `POST /memoria/registrar`
- `GET /memoria/listar?tipo=risco`
- `GET /memoria/buscar?termo=atestado&tipo=tese`

Memory Core oficial:

- `GET /`
- `POST /memoria/registrar`
- `GET /memoria/listar/{tipo}` — aceita `tese` ou `teses`
- `GET /memoria/buscar?q=atestado`

Integração do fluxo principal:

- `GET /fluxo/protocolo/analise-viva` — retorna o Protocolo Oficial de Análise Viva.
- `POST /fluxo/memoria/consultar` — consulta o Memory Core oficial por termo estratégico.
- `POST /fluxo/analise/preparar` — identifica intenção, consulta memória viva, indica necessidade de RAG e retorna template de memória sugerida.
- `POST /fluxo/memoria/registrar-sugerida` — registra aprendizado sugerido no Memory Core oficial após aprovação do usuário.

Regra operacional: toda análise sobre edital, impugnação, recurso, concorrente, habilitação, contrato, pagamento, órgão, tese ou oportunidade deve consultar a memória viva antes da resposta. Quando houver aprendizado novo, a resposta deve terminar com `MEMÓRIA SUGERIDA`; o registro só ocorre se o usuário aprovar.

Decision Engine:

- `GET /decisao/engine` — metadados do LICI Decision Engine.
- `POST /decisao/decidir` — retorna decisão operacional: `PARTICIPAR`, `IMPUGNAR`, `ESTRATÉGIA HÍBRIDA`, `DESISTIR` ou `ANALISAR MAIS`.

O motor avalia aderência técnica, risco de habilitação, risco jurídico, oportunidade competitiva, risco de execução, histórico/memória viva, necessidade de impugnação e chance estratégica de vitória. A resposta inclui decisão, score 0-100, justificativa objetiva, riscos críticos, ação imediata e memória sugerida quando aplicável.

Edital Analyzer:

- `GET /edital/analyzer` — metadados do LICI Edital Analyzer.
- `POST /edital/analisar-texto` — analisa texto de edital, identifica riscos/oportunidades/checklist e alimenta o Decision Engine.
- `POST /edital/checklist` — gera checklist operacional de habilitação, julgamento, execução, blindagem e ataque lícito a concorrentes.

A análise identifica objeto, modalidade, prazos críticos, habilitação, qualificação técnica, atestados, riscos de inabilitação, cláusulas restritivas, oportunidades de impugnação, pontos de ataque a concorrentes, blindagem do usuário e decisão recomendada.

Case Engine:

- `GET /casos` — lista casos operacionais.
- `POST /casos/criar` — cria caso com cliente, órgão, objeto, modalidade, fase, riscos, oportunidades e memória relacionada.
- `GET /casos/{id}` — consulta caso completo.
- `POST /casos/{id}/atualizar-fase` — altera fase/status e gera evento de timeline.
- `POST /casos/{id}/registrar-evento` — registra evento operacional e memória sugerida.
- `GET /casos/{id}/timeline` — retorna histórico operacional do caso.

O Case Engine transforma análises isoladas em acompanhamento vivo do ciclo licitatório, integrado ao Memory Core, Decision Engine, Edital Analyzer e RAG/base.

Consultor Full Profundo — Fase 1:

- `GET /consultor-full/engine`
- `GET /consultor-full/dashboard`
- `GET /consultor-full/pipeline`
- `GET /consultor-full/central-360`
- `GET /consultor-full/leads`
- `POST /consultor-full/leads`
- `PATCH /consultor-full/leads/{lead_id}`
- `GET /consultor-full/followups`
- `POST /consultor-full/followups`
- `PATCH /consultor-full/followups/{followup_id}`

O módulo entrega CRM real do consultor, pipeline Kanban, carteira A/B/C, follow-ups, tarefas, produtividade, dashboard consultor real e Central do Cliente 360°. Mantém JWT, multi-org, ownership, Audit Log, observabilidade, PostgreSQL híbrido e fallback JSON. Não usa IA livre.

Persistência profunda:

- PostgreSQL: `consultor_leads`, `consultor_followups`.
- JSON fallback: `/root/lici-app/consultor_full/leads.json`, `/root/lici-app/consultor_full/followups.json`.

Documental Empresarial 360° — Fase 1:

- `GET /documental/engine`
- `GET /documental/dashboard`
- `GET /documental/documentos`
- `POST /documental/documentos`
- `POST /documental/documentos/upload`
- `PATCH /documental/documentos/{document_id}`
- `GET /documental/dossie`
- `POST /documental/checklist`

O módulo cria repositório documental empresarial/cliente para contrato social, alterações, cartão CNPJ, certidões, balanço, índices contábeis, atestados, procurações, alvarás, ISO, compliance, declarações, documentos técnicos, trabalhistas e fiscais. Entrega controle de validade, alertas, risco documental, score, dossiê empresarial, biblioteca de atestados e checklist documental por licitação. Não substitui nem quebra o Upload Engine; integra-se a ele via `upload_document_id` no checklist.

IA Assistiva Contextual — Fase 1:

- `GET /ia-assistiva/engine`
- `POST /ia-assistiva/responder`
- `POST /ia-assistiva/feedback`
- `GET /ia-assistiva/telemetria`

A camada é assistiva, contextual e supervisionada. Consulta casos, memória viva, clientes, documentos, checklist, concorrentes, órgãos, dashboard, alertas, tarefas e pipeline consultivo. Produz resumos, explicações e sugestões supervisionadas, sempre com fontes internas, confiança, Audit Log, telemetria e `executa_automaticamente=false`. Não é IA autônoma e não executa ações operacionais.

Persistência IA Assistiva:

- JSON: `/root/lici-app/ia_assistiva/respostas.json`.
- JSON: `/root/lici-app/ia_assistiva/telemetria.json`.

Healthcheck Central:

- `GET /health` — verifica disponibilidade básica da API principal.
- `GET /health/full` — valida API, Memory Core, frontend, rotas protegidas, diretórios operacionais, arquivos JSON, permissões de autenticação, disco, PostgreSQL, logs e serviços/timers systemd.

O healthcheck completo cobre os módulos reais em produção: Radar, Triagem, Alertas, Casos, Scheduler, Fornecedor Full, Consultor Full, Documental 360°, IA Assistiva, Memory Core, Auth e PostgreSQL híbrido. Alertas de segurança, como credencial bootstrap ainda presente, aparecem como `alerta` sem expor conteúdo sensível.

Backup e restauração:

- Timer: `lici-backup.timer` executa diariamente às 03:00.
- Script: `/root/lici-app/scripts/backup_lici.sh`.
- Destino local: `/root/backups/lici`.
- Archive principal: `lici-backup-YYYYmmdd-HHMM.tar.gz`.
- Dump PostgreSQL: `postgres/lici-YYYYmmdd-HHMM.sql.gz`.
- Manifesto verificável: `lici-backup-YYYYmmdd-HHMM.manifest.json`, com tamanho e SHA-256 do archive e do dump.
- Restore seguro: `/root/lici-app/scripts/restore_lici.sh` roda em `dry-run` por padrão.

Exemplo de validação de restore:

```bash
/root/lici-app/scripts/restore_lici.sh \
  --archive /root/backups/lici/lici-backup-YYYYmmdd-HHMM.tar.gz \
  --pg-dump /root/backups/lici/postgres/lici-YYYYmmdd-HHMM.sql.gz
```

Restauração real exige confirmação explícita:

```bash
CONFIRM_RESTORE_LICI=YES /root/lici-app/scripts/restore_lici.sh --apply \
  --archive /root/backups/lici/lici-backup-YYYYmmdd-HHMM.tar.gz \
  --pg-dump /root/backups/lici/postgres/lici-YYYYmmdd-HHMM.sql.gz
```

Observação crítica: GitHub protege o código. Backups protegem dados reais, documentos, banco e credenciais locais. Para desastre total da VPS, é necessário copiar `/root/backups/lici` para armazenamento externo seguro.

Persistência documental:

- PostgreSQL: `company_documents`, `company_document_versions`, `company_document_alerts`.
- Filesystem protegido: `/root/lici-app/company_documents/files`.
- JSON fallback: `/root/lici-app/company_documents/documents.json`, `/root/lici-app/company_documents/versions.json`, `/root/lici-app/company_documents/alerts.json`.

## Auth Engine — autenticação própria da LICI

A LICI possui autenticação própria em paralelo ao Basic Auth do Nginx. O Basic Auth **não deve ser removido ainda**; ele permanece como camada externa temporária enquanto JWT, usuários e permissões amadurecem.

Persistência inicial:

- Usuários: `/root/lici-app/auth/usuarios.json`
- Config/secret JWT: `/root/lici-app/auth/config.json`
- Credencial bootstrap inicial: `/root/lici-app/auth/admin_bootstrap_credentials`

Segurança aplicada no MVP:

- Senhas nunca são salvas em texto puro.
- Hash de senha: `pbkdf2_sha256` com salt individual e 210.000 iterações.
- JWT assinado com `HS256`.
- Expiração padrão do access token: 8 horas.
- Arquivos de autenticação com permissão `600`; diretório `/root/lici-app/auth` com permissão `700`.
- Eventos de login, criação de usuário, alteração de perfil e desativação são registrados no Audit Log.

Perfis suportados:

- `admin`
- `consultor`
- `fornecedor`
- `comprador`
- `leitura`

Mapeamento inicial para perfil operacional:

- `admin` → `fornecedor`
- `consultor` → `consultor`
- `fornecedor` → `fornecedor`
- `comprador` → `comprador`
- `leitura` → `fornecedor`

Endpoints:

- `POST /auth/login`
- `GET /auth/me`
- `POST /auth/usuarios`
- `GET /auth/usuarios`
- `POST /auth/usuarios/{id}/alterar-perfil`
- `POST /auth/usuarios/{id}/desativar`

Fluxo operacional:

```bash
# Login
curl -X POST http://127.0.0.1:8100/auth/login   -H 'Content-Type: application/json'   -d '{"usuario":"admin","senha":"SENHA"}'

# Usar token
curl http://127.0.0.1:8100/auth/me   -H "Authorization: Bearer TOKEN"
```

Observações:

- O primeiro usuário pode ser criado sem JWT apenas enquanto `usuarios.json` estiver vazio; ele é forçado para `admin`.
- Depois do bootstrap, criação/listagem/alteração/desativação exigem usuário `admin` via Bearer token.
- A próxima etapa é proteger gradualmente os endpoints operacionais por permissão.

Recuperação de acesso admin:

- Script seguro: `/root/lici-app/scripts/reset_admin_password.py`.
- Uso padrão:

```bash
/root/lici-app/scripts/reset_admin_password.py --usuario liciadmin --remove-bootstrap
```

- A senha gerada é salva somente em `/root/lici-app/auth/admin_recovery_credentials`, com permissão `600`.
- O arquivo de recuperação não é versionado no Git e deve ser removido após login e rotação segura da senha.
- `GET /health/full` alerta enquanto `admin_recovery_credentials` existir.

## Login JWT no Frontend

O frontend React já possui tela de login da LICI integrada ao Auth Engine.

Comportamento implementado:

- Se não houver token JWT salvo, a interface exibe a tela **Entrar na LICI**.
- O login chama `POST /api/auth/login`.
- Após login, o token JWT é salvo em `localStorage`.
- O usuário atual é salvo em `localStorage`.
- A sessão é validada com `GET /api/auth/me` ao abrir a aplicação.
- Todas as chamadas internas feitas por `src/services/api.js` passam a enviar `Authorization: Bearer TOKEN` quando houver token.
- Se uma chamada autenticada retornar `401`, o frontend limpa a sessão e volta para o login.
- O menu lateral/topo exibe o usuário logado.
- O botão **Sair** limpa token/usuário e retorna ao login.
- O perfil operacional inicial é selecionado a partir do usuário autenticado.

Chaves de sessão no navegador:

- `lici.auth.token`
- `lici.auth.user`

Mapeamento visual de perfil:

- `admin` → `fornecedor`
- `consultor` → `consultor`
- `fornecedor` → `fornecedor`
- `comprador` → `comprador`
- `leitura` → `fornecedor`

Importante: o Basic Auth do Nginx permanece ativo em paralelo. O navegador primeiro passa pelo Basic Auth e, dentro da aplicação, usa o login JWT da LICI.

## Proteção gradual de endpoints por JWT/permissões

O backend possui dependências reutilizáveis para autenticação real:

- `get_current_user` — exige `Authorization: Bearer TOKEN` e retorna o usuário ativo.
- `require_admin` — exige perfil/permissão administrativa.
- `require_permission(...)` — exige ao menos uma permissão específica; registra acesso negado no Audit Log.

Arquivo principal:

- `/root/lici-app/backend/app/api/security.py`

Rotas protegidas na primeira camada:

- `/auth/usuarios`
- `/auth/usuarios/{id}/alterar-perfil`
- `/auth/usuarios/{id}/desativar`
- `/audit/logs`
- `/casos/*`
- `/upload/*`
- `/documentos/*`
- `/export/*`
- `/consultor/*`
- `/orgaos/*`
- `/perfil/selecionar`
- `/memoria/*`
- `/radar/*`
- `/alertas` e ações sensíveis de alertas

Rotas mantidas sem bloqueio JWT para operação/boot:

- `/health`
- `/health/full`
- `/perfil/atual`
- `/perfil/configuracoes`
- dashboards agregados enquanto o frontend estabiliza o fluxo autenticado

Matriz de permissões inicial:

- `admin`: acesso total.
- `consultor`: casos, consultor, upload, documentos/peças, exportação e memória.
- `fornecedor`: radar, casos, upload, documentos/peças, exportação e memória.
- `comprador`: órgãos, casos, documentos, exportação e memória de leitura.
- `leitura`: leitura geral; sem criação/alteração.

Validações esperadas:

```bash
# Sem token em rota protegida deve retornar 401
curl -i http://127.0.0.1:8100/audit/logs

# Com token admin deve retornar 200
curl -H "Authorization: Bearer TOKEN" http://127.0.0.1:8100/audit/logs

# Usuário leitura deve conseguir GET protegido de leitura, mas receber 403 em POST/alteração
curl -H "Authorization: Bearer TOKEN_LEITURA" http://127.0.0.1:8100/casos
```

Acesso negado é registrado no Audit Log com módulo `security` e ação `acesso_negado`.

## Frontend MVP

Interface React/Vite/Tailwind da central de comando visual da LICI.

Local:

```bash
/root/lici-app/frontend
```

Comandos de desenvolvimento:

```bash
cd /root/lici-app/frontend
npm install
npm run dev
```

Build:

```bash
cd /root/lici-app/frontend
npm run build
```

Preview local:

```bash
cd /root/lici-app/frontend
npm run preview -- --host 127.0.0.1 --port 5173
```

## Serviço systemd do Frontend

O Frontend MVP roda continuamente via systemd:

- Unit: `/etc/systemd/system/lici-frontend.service`
- URL local: `http://127.0.0.1:5173`
- WorkingDirectory: `/root/lici-app/frontend`
- Comando: `npm run preview -- --host 127.0.0.1 --port 5173`
- Restart: `always`
- RestartSec: `10`

Comandos úteis:

```bash
systemctl status lici-frontend --no-pager
systemctl restart lici-frontend
journalctl -u lici-frontend.service --no-pager -n 100
curl http://127.0.0.1:5173
```

A interface consome a API principal em `http://127.0.0.1:8100`.

## Serviço systemd da API Principal

A API principal da LICI roda continuamente via systemd:

- Unit: `/etc/systemd/system/lici-api.service`
- URL local: `http://127.0.0.1:8100`
- WorkingDirectory: `/root/lici-app/backend`
- Comando: `/root/lici-app/backend/venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8100`
- Restart: `always`
- RestartSec: `10`

Comandos úteis:

```bash
systemctl status lici-api --no-pager
systemctl restart lici-api
journalctl -u lici-api.service --no-pager -n 100
curl http://127.0.0.1:8100/dashboard/resumo
```

Observação: `backend/venv` é um link simbólico para `backend/.venv`, preservando o caminho esperado pelos serviços systemd.

Serviços relacionados que devem permanecer ativos:

- Memory Core: `lici-memory.service` em `127.0.0.1:8010`
- Frontend MVP: `lici-frontend.service` em `127.0.0.1:5173`
- Scheduler: `lici-scheduler.timer`

## Nginx Reverse Proxy + HTTPS

A LICI está publicada via Nginx com TLS obrigatório.

Domínios:

- `https://licitaprobrasil.com`
- `https://www.licitaprobrasil.com`

Configuração:

- `/etc/nginx/sites-available/lici`
- `/etc/nginx/sites-enabled/lici`
- Certificado: `/etc/letsencrypt/live/licitaprobrasil.com/fullchain.pem`
- Chave: `/etc/letsencrypt/live/licitaprobrasil.com/privkey.pem`
- Renovação automática: `certbot.timer`

Rotas:

- `/` → Frontend MVP em `http://127.0.0.1:5173`
- `/api/` → API principal em `http://127.0.0.1:8100/`
- `/memory/` → Memory Core em `http://127.0.0.1:8010/`

Validação:

```bash
/usr/sbin/nginx -t
systemctl reload nginx
certbot certificates
curl -I https://licitaprobrasil.com
curl -I http://licitaprobrasil.com
source /root/lici-app/.lici_basic_auth_credentials
curl -u "$usuario:$senha" https://licitaprobrasil.com/api/health
curl -u "$usuario:$senha" https://licitaprobrasil.com/memory/
```

Observação: o frontend consome a API por `/api`, mantendo a API principal protegida em loopback e evitando dependência direta do navegador em `127.0.0.1:8100`.

## Proteção de acesso público

O Nginx protege a LICI com HTTP Basic Auth sobre HTTPS. A porta 80 redireciona para HTTPS.

- Arquivo htpasswd: `/etc/nginx/.htpasswd`
- Credenciais operacionais root-only: `/root/lici-app/.lici_basic_auth_credentials`
- Usuário criado: `liciadmin`

Rotas protegidas:

- `/`
- `/api/`
- `/memory/`

Validação:

```bash
curl -I https://licitaprobrasil.com/
source /root/lici-app/.lici_basic_auth_credentials
curl -u "$usuario:$senha" https://licitaprobrasil.com/api/dashboard/resumo
```

A LICI não deve ficar exposta publicamente sem senha.

## Backup automático diário

A LICI possui backup automático via systemd.

- Script: `/root/lici-app/scripts/backup_lici.sh`
- Diretório: `/root/backups/lici`
- Service: `/etc/systemd/system/lici-backup.service`
- Timer: `/etc/systemd/system/lici-backup.timer`
- Horário: diariamente às `03:00`
- Retenção: últimos 7 backups
- Arquivo: `lici-backup-YYYYMMDD-HHMM.tar.gz`

Inclui:

- `/root/lici-app`
- `/root/lici-docs`
- `/root/agente-licitacoes`
- configuração Nginx da LICI
- units systemd `lici-*.service` e `lici-*.timer`

Exclui ambientes virtuais e artefatos recriáveis para manter o backup diário viável, incluindo `frontend/node_modules`, `frontend/dist`, `backend/.venv`, `backend/venv` e `agente-licitacoes/venv`.

Comandos úteis:

```bash
systemctl status lici-backup.timer --no-pager
systemctl start lici-backup.service
systemctl status lici-backup.service --no-pager
ls -lah /root/backups/lici
tail -100 /root/backups/lici/backup.log
```

## Healthcheck Central

A LICI possui um healthcheck consolidado da plataforma.

Endpoint:

```bash
curl http://127.0.0.1:8100/health/full
```

O retorno traz:

- status geral: `ok`, `alerta` ou `erro`
- timestamp
- lista de componentes
- status individual
- mensagem e detalhes por componente

O endpoint verifica API principal, Memory Core, Dashboard, Radar, Triage, Alertas, Casos, Scheduler, diretórios críticos, JSONs principais, disco e serviços systemd.

Script operacional:

```bash
/root/lici-app/scripts/healthcheck_lici.sh
```

Log:

```bash
/root/lici-app/health/healthcheck.log
```

O script testa `nginx`, `lici-api`, `lici-memory`, `lici-frontend`, `lici-scheduler.timer`, `lici-backup.timer`, endpoints locais, proteção Basic Auth e espaço em disco.

## Healthcheck automático

O Healthcheck Central também roda automaticamente por systemd.

- Service: `/etc/systemd/system/lici-healthcheck.service`
- Timer: `/etc/systemd/system/lici-healthcheck.timer`
- Frequência: a cada 30 minutos
- Script: `/root/lici-app/scripts/healthcheck_lici.sh`
- Log: `/root/lici-app/health/healthcheck.log`

Comandos úteis:

```bash
systemctl status lici-healthcheck.timer --no-pager
systemctl start lici-healthcheck.service
systemctl list-timers 'lici-*' --no-pager
tail -100 /root/lici-app/health/healthcheck.log
```

## LICI Audit Log

O LICI Audit Log registra ações importantes da plataforma para rastreabilidade operacional.

- Serviço interno: `app.services.audit_log.LiciAuditLog`
- Arquivo: `/root/lici-app/audit/audit.log`
- Endpoint: `GET /audit/logs`
- Formato: JSON Lines

Campos por evento:

- `timestamp`
- `modulo`
- `acao`
- `status`
- `detalhes`
- `id_relacionado`, quando existir

Eventos registrados no MVP:

- criação de caso;
- mudança de fase;
- criação de alerta;
- marcação de alerta como lido;
- execução do scheduler;
- geração de decisão;
- registro de memória;
- execução de backup;
- healthcheck com alerta ou erro.

Consulta:

```bash
curl http://127.0.0.1:8100/audit/logs
curl 'http://127.0.0.1:8100/audit/logs?limite=50&status=erro'
tail -100 /root/lici-app/audit/audit.log
```

O Audit Log é best-effort: se a escrita de auditoria falhar, a operação principal continua para não quebrar endpoints existentes.

## LICI Upload Engine

O LICI Upload Engine permite receber edital/documento pelo frontend, salvar o arquivo, extrair texto, registrar o documento e enviar o conteúdo para análise automática.

Endpoints:

- `GET /upload/engine` — metadados do módulo.
- `POST /upload/edital` — recebe arquivo `multipart/form-data` no campo `file` (`PDF`, `DOCX` ou `TXT`).
- `GET /upload/documentos` — lista documentos recebidos.
- `POST /upload/documentos/{id}/analisar` — analisa o texto com o Edital Analyzer e, opcionalmente, cria caso vivo.

Persistência:

- Arquivos: `/root/lici-app/storage/editais`
- Registro JSON: `/root/lici-app/storage/documentos.json`

Integrações:

- Edital Analyzer
- Case Engine
- Decision Engine
- Memory Core
- Audit Log

Exemplo de upload:

```bash
curl -F "file=@/caminho/edital.pdf" http://127.0.0.1:8100/upload/edital
```

Exemplo de análise com criação de caso vivo:

```bash
curl -X POST http://127.0.0.1:8100/upload/documentos/{id}/analisar \
  -H 'Content-Type: application/json' \
  -d '{"consultar_rag": false, "criar_caso": true, "cliente": "cliente", "orgao": "Órgão", "contexto_usuario": "análise inicial do edital"}'
```

A resposta da análise inclui `memoria_sugerida` quando houver aprendizado operacional reutilizável. O registro efetivo da memória continua dependendo de aprovação humana pelo fluxo oficial da LICI.

## LICI Document Generator

O LICI Document Generator cria peças administrativas a partir da análise da LICI, caso vivo ou documento enviado pelo Upload Engine.

Endpoints:

- `GET /documentos/engine` — metadados do módulo.
- `POST /documentos/gerar-impugnacao` — gera impugnação administrativa.
- `POST /documentos/gerar-recurso` — gera recurso administrativo.
- `POST /documentos/gerar-contrarrazoes` — gera contrarrazões administrativas.
- `GET /documentos/gerados` — lista peças geradas.

Persistência:

- Arquivos gerados: `/root/lici-app/storage/documentos_gerados`
- Índice: `/root/lici-app/storage/documentos_gerados/index.json`

Integrações:

- Upload Engine: aceita `documento_id` e reaproveita análise/texto extraído.
- Edital Analyzer: analisa texto quando necessário.
- Case Engine: aceita `case_id` e reaproveita dados do caso vivo.
- Decision Engine: gera decisão-base para orientar a peça.
- Memory Core: sugere memória viva de tese nova e pode registrar se `registrar_memoria=true`.
- Audit Log: registra cada peça gerada.

Exemplo:

```bash
curl -X POST http://127.0.0.1:8100/documentos/gerar-impugnacao \
  -H 'Content-Type: application/json' \
  -d '{"orgao":"Órgão","objeto":"Serviços de TI","tese_principal":"exigência de atestado 100% sem justificativa técnica","pedidos":["retificar o edital","reabrir prazo"]}'
```

## LICI Export Engine

O LICI Export Engine exporta peças geradas e relatórios de casos vivos em TXT/DOCX para uso operacional real.

Endpoints:

- `GET /export/engine` — metadados do módulo.
- `GET /export/documentos/{id}/txt` — exporta peça gerada em TXT.
- `GET /export/documentos/{id}/docx` — exporta peça gerada em DOCX.
- `GET /export/casos/{id}/relatorio-txt` — exporta relatório de caso vivo em TXT.
- `GET /export/casos/{id}/relatorio-docx` — exporta relatório de caso vivo em DOCX.

Persistência:

- Cópias exportadas: `/root/lici-app/storage/exportados`

Integrações:

- Document Generator: localiza peças geradas por `id`.
- Case Engine: localiza casos vivos por `id` e monta relatório operacional.
- Audit Log: registra cada exportação.

Dependência:

- `python-docx==1.1.2`

Exemplos:

```bash
curl -OJ http://127.0.0.1:8100/export/documentos/{id}/docx
curl -OJ http://127.0.0.1:8100/export/casos/{id}/relatorio-docx
```

## LICI Órgãos Engine

O LICI Órgãos Engine transforma órgãos compradores em memória estratégica viva para análise de risco, oportunidade, comportamento, impugnações, recursos, pagamento e execução contratual.

Endpoints:

- `GET /orgaos/engine` — metadados do módulo.
- `GET /orgaos` — lista órgãos registrados.
- `GET /orgaos/{id}` — obtém um órgão comprador.
- `POST /orgaos/registrar` — registra ou atualiza órgão por nome/CNPJ.
- `POST /orgaos/{id}/registrar-evento` — registra evento estratégico do órgão.
- `GET /orgaos/{id}/historico` — lista histórico/eventos do órgão.

Persistência:

- `/root/lici-app/orgaos/orgaos.json`
- `/root/lici-app/orgaos/historico.json`

Eventos estratégicos suportados:

- edital publicado
- impugnação deferida
- impugnação indeferida
- recurso acolhido
- recurso negado
- pagamento atrasado
- contrato bem executado
- exigência restritiva
- concorrência baixa
- concorrência alta

Integrações:

- Memory Core: registra memória do órgão e eventos relevantes.
- Case Engine: relaciona casos existentes do mesmo órgão e ajusta oportunidade.
- Radar Engine: aceita `radar_id` nos eventos para rastrear origem da oportunidade.
- Audit Log: registra criação/atualização de órgão e eventos.

## LICI Operational Profile Engine

O LICI Operational Profile Engine permite que a LICI opere com perfis diferentes sem quebrar funcionalidades existentes.

Perfis oficiais:

- `fornecedor` — perfil padrão; mantém menus e módulos atuais, focado em empresas que vendem ao governo.
- `consultor` — perfil estrutural para analistas e consultorias que atendem múltiplos clientes.
- `comprador` — perfil estrutural para órgãos, pregoeiros, agentes de contratação e equipes públicas.

Endpoints:

- `GET /perfil/engine` — metadados do módulo.
- `GET /perfil/atual` — retorna perfil atual, menus, prioridades, linguagem, módulos, fluxos, casos, alertas, memórias, documentos e schema de dashboard.
- `POST /perfil/selecionar` — seleciona o perfil operacional atual.
- `GET /perfil/configuracoes` — retorna todas as configurações de perfil.

Persistência:

- `/root/lici-app/perfis/perfil_atual.json`
- `/root/lici-app/perfis/configuracoes.json`

Integrações:

- Dashboard: fornece schema e prioridades para dashboards dinâmicos.
- Case Engine: fornece tipos de caso e fluxos por perfil.
- Memory Core: registra seleção de perfil como memória operacional.
- Audit Log: audita mudanças de perfil.

Exemplo:

```bash
curl http://127.0.0.1:8100/perfil/atual
curl -X POST http://127.0.0.1:8100/perfil/selecionar \
  -H 'Content-Type: application/json' \
  -d '{"perfil":"fornecedor","motivo":"perfil padrão operacional"}'
```

## LICI Consultor Engine

O LICI Consultor Engine implementa a rota operacional `consultor`, focada em gestão de clientes, demandas, atendimento, prazos e carteira de consultoria em licitações.

Endpoints:

- `GET /consultor/engine` — metadados do módulo.
- `GET /consultor/clientes` — lista clientes da consultoria.
- `POST /consultor/clientes` — cria ou atualiza cliente por nome/documento.
- `GET /consultor/clientes/{id}` — detalha cliente, demandas e casos relacionados.
- `POST /consultor/clientes/{id}/registrar-demanda` — registra demanda do cliente.
- `GET /consultor/demandas` — lista demandas.
- `POST /consultor/demandas/{id}/atualizar-status` — atualiza status de demanda.

Persistência:

- `/root/lici-app/consultor/clientes.json`
- `/root/lici-app/consultor/demandas.json`

Tipos de demanda:

- edital
- impugnação
- recurso
- habilitação
- proposta
- contrato
- cobrança

Integrações:

- Case Engine: demanda pode referenciar `caso_vivo_id`; detalhe do cliente mostra casos relacionados pelo nome/documento do cliente.
- Memory Core: registra clientes e demandas como memória operacional de atendimento.
- Audit Log: registra criação/atualização de cliente, demanda e status.
- Operational Profile Engine: módulo pertence à rota `consultor` e prepara dashboards/menus dinâmicos.


### Ajuste operacional 2026-05-11 — Basic Auth e API JWT

Para evitar falhas de `fetch()` em navegadores móveis, especialmente Safari/iPhone, o Basic Auth ficou restrito à interface `/` e `/memory/`. A rota `/api/` fica com `auth_basic off` no Nginx e é protegida pela autenticação JWT do backend.

Validação:

- `https://licitaprobrasil.com/` sem Basic Auth retorna `401`.
- `POST /api/auth/login` funciona sem Basic Auth adicional, usando usuário/senha JWT.
- `/api/dashboard/resumo` sem Bearer token retorna `401`.
- `/api/dashboard/resumo` com Bearer token retorna `200`.
- `/api/audit/logs` com Bearer token admin retorna `200`.

## Regra definitiva de segurança — Basic Auth visual + JWT operacional

A LICI usa segurança em duas camadas:

1. **HTTPS obrigatório** em todo acesso público.
2. **Basic Auth somente na entrada visual** e **JWT/permissões na API operacional**.

Estado atual:

- Basic Auth ativo em `/`.
- Basic Auth ativo em `/memory/`.
- Basic Auth desativado em `/api/` no Nginx com `auth_basic off`.
- `/api/` protegido pelo backend com JWT e permissões.

Motivo técnico:

- O Basic Auth em `/api/` gerou conflito com chamadas `fetch()` do frontend, especialmente em Safari/iPhone.
- O navegador passava pelo Basic Auth para abrir a interface, mas algumas chamadas XHR/fetch subsequentes para `/api/...` não reenviavam as credenciais Basic Auth.
- Resultado observado: login JWT funcionava, mas chamadas operacionais retornavam `401` no Nginx antes de chegar ao backend.

Regra definitiva:

- **Acesso visual passa por Basic Auth.**
- **Ações operacionais passam por JWT/permissões.**

Testes obrigatórios:

```bash
# / sem Basic Auth = 401
curl -sS -o /dev/null -w '%{http_code}
' https://licitaprobrasil.com/

# /api/auth/login = 200 com credenciais válidas
curl -sS -o /dev/null -w '%{http_code}
'   -H 'Content-Type: application/json'   -d '{"usuario":"USUARIO","senha":"SENHA"}'   https://licitaprobrasil.com/api/auth/login

# /api/dashboard/resumo sem JWT = 401
curl -sS -o /dev/null -w '%{http_code}
'   https://licitaprobrasil.com/api/dashboard/resumo

# /api/dashboard/resumo com JWT = 200
curl -sS -o /dev/null -w '%{http_code}
'   -H "Authorization: Bearer TOKEN"   https://licitaprobrasil.com/api/dashboard/resumo
```

Documento detalhado: `/root/lici-docs/arquitetura/SEGURANCA.md`.


---

## PostgreSQL Fase 1 — Auth

A primeira etapa PostgreSQL foi implementada somente para autenticação.

Escopo ativo:

- PostgreSQL 16 instalado.
- Banco: `lici`.
- Usuário de aplicação: `lici_app`.
- DSN root-only: `/root/lici-app/secrets/postgres.env`.
- Tabelas:
  - `users`
  - `roles`
  - `permissions`
  - `user_roles`
  - `role_permissions`
  - `audit_events`

Arquivos novos:

- `backend/app/services/auth_pg_store.py`
- `backend/app/services/auth_migration.py`

Comportamento do Auth Engine:

- Leitura tenta PostgreSQL primeiro.
- Se PostgreSQL estiver indisponível, cai automaticamente para `/root/lici-app/auth/usuarios.json`.
- Escrita grava no JSON e tenta gravar no PostgreSQL.
- Falhas de PostgreSQL são registradas no Audit Log e não devem derrubar login.

JSON preservado:

- `/root/lici-app/auth/usuarios.json` continua sendo fallback obrigatório.
- `/root/lici-app/auth/config.json` continua guardando o JWT secret nesta fase.

Comandos úteis:

```bash
source /root/lici-app/secrets/postgres.env
psql "$LICI_DATABASE_URL" -c "select username, profile, status from users;"
cd /root/lici-app/backend
./venv/bin/python -m app.services.auth_migration
```

Validação esperada:

```bash
# Login continua funcionando
curl -sS -o /dev/null -w '%{http_code}\n' \
  -H 'Content-Type: application/json' \
  -d '{"usuario":"liciadmin","senha":"SENHA"}' \
  https://licitaprobrasil.com/api/auth/login
# esperado: 200
```

Importante:

- Não migrar casos, memória, radar, triagem, alertas, órgãos, consultor ou documentos ainda.
- Antes da próxima fase, incluir `pg_dump` na rotina de backup diário.

---

## Backup PostgreSQL no backup diário

O backup automático da LICI inclui PostgreSQL a partir da Fase 1 — Auth.

Script:

- `/root/lici-app/scripts/backup_lici.sh`

Diretórios:

- Backup principal: `/root/backups/lici/lici-backup-YYYYMMDD-HHMM.tar.gz`
- Dump PostgreSQL: `/root/backups/lici/postgres/lici-YYYYMMDD-HHMM.sql.gz`

Comportamento:

- O script carrega `/root/lici-app/secrets/postgres.env`.
- Executa `pg_dump` do banco `lici`.
- Compacta o dump em `.sql.gz`.
- Valida o dump com `gunzip -t`.
- Verifica conteúdo SQL básico do dump.
- Inclui o `.sql.gz` no backup principal `.tar.gz`.
- Mantém rotação dos últimos 7 backups principais.
- Mantém rotação dos últimos 7 dumps PostgreSQL.
- Se `pg_dump` falhar, o backup retorna erro.
- A execução é registrada no Audit Log quando possível.

Validação manual:

```bash
systemctl start lici-backup.service
systemctl status lici-backup.service --no-pager
ls -lah /root/backups/lici
ls -lah /root/backups/lici/postgres
gunzip -t /root/backups/lici/postgres/lici-YYYYMMDD-HHMM.sql.gz
tar -tzf /root/backups/lici/lici-backup-YYYYMMDD-HHMM.tar.gz | grep 'postgres/lici-'
```

---

## PostgreSQL Fase 2 — Casos Vivos

A segunda etapa PostgreSQL foi implementada somente para o domínio de Casos Vivos.

Tabelas:

- `cases`
- `case_events`

Arquivos novos:

- `backend/app/services/case_pg_store.py`
- `backend/app/services/case_migration.py`

Arquivos alterados:

- `backend/app/services/case_store.py`
- `backend/app/services/case_engine.py`

Persistência atual dos casos:

- JSON continua preservado em `/root/lici-app/casos_vivos`.
- PostgreSQL passa a receber os casos em dual-write.
- Leitura tenta PostgreSQL primeiro e cai para JSON se o banco falhar.
- Escrita grava no JSON e tenta gravar no PostgreSQL.
- Falha no PostgreSQL é registrada no Audit Log e não quebra operação.

Comando de migração manual:

```bash
cd /root/lici-app/backend
./venv/bin/python -m app.services.case_migration
```

Validação esperada:

```bash
source /root/lici-app/secrets/postgres.env
psql "$LICI_DATABASE_URL" -c "select id, client_name, current_phase, status from cases;"
psql "$LICI_DATABASE_URL" -c "select count(*) from case_events;"
```

Fora de escopo nesta fase:

- Memória viva.
- Radar/oportunidades.
- Triagem.
- Alertas.
- Órgãos.
- Consultor.
- Documentos.

---

## PostgreSQL Fase 3 — Memória Viva

A terceira etapa PostgreSQL foi implementada somente para o domínio de Memória Viva.

Tabela:

- `memories`

Arquivos novos:

- `backend/app/services/memory_pg_store.py`
- `backend/app/services/memory_migration.py`

Arquivos alterados:

- `backend/app/services/memory_store.py`
- `backend/app/api/memory.py`

Persistência atual da memória:

- JSON continua preservado em `/root/lici-app/memoria_viva/memorias.json`.
- Espelhos por tipo continuam preservados em `/root/lici-app/memoria_viva/*`.
- PostgreSQL passa a receber memórias em dual-write.
- Leitura tenta PostgreSQL primeiro e cai para JSON se o banco falhar.
- Escrita grava no JSON e tenta gravar no PostgreSQL.
- Falha no PostgreSQL é registrada no Audit Log e não quebra registro de memória.

Comando de migração manual:

```bash
cd /root/lici-app/backend
./venv/bin/python -m app.services.memory_migration
```

Validação esperada:

```bash
source /root/lici-app/secrets/postgres.env
psql "$LICI_DATABASE_URL" -c "select tipo, count(*) from memories group by tipo order by tipo;"
```

Fora de escopo nesta fase:

- Radar/oportunidades.
- Triagem.
- Alertas.
- Órgãos.
- Consultor.
- Documentos.

---

## PostgreSQL Fase 4 — Operação Radar

Status: **implementada e validada em 2026-05-11**.

A quarta etapa PostgreSQL migrou Radar, Triagem e Alertas para operação híbrida, mantendo JSON como fallback operacional.

Tabelas criadas:

- `radar_opportunities`
- `triage_items`
- `alerts`

Arquivos novos:

- `backend/app/services/radar_pg_store.py`
- `backend/app/services/radar_migration.py`

Arquivos alterados:

- `backend/app/services/radar_store.py`
- `backend/app/services/triage_store.py`
- `backend/app/services/alert_store.py`
- `backend/app/services/radar_engine.py`
- `backend/app/services/triage_engine.py`
- `backend/app/services/alert_engine.py`
- `backend/app/services/dashboard.py`
- `backend/app/services/scheduler.py`

Persistência atual:

- JSONs preservados e continuam obrigatórios:
  - `/root/lici-app/radar/oportunidades.json`
  - `/root/lici-app/triagem/fila.json`
  - `/root/lici-app/triagem/logs.json`
  - `/root/lici-app/alertas/alertas.json`
  - `/root/lici-app/alertas/logs.json`
- Leitura tenta PostgreSQL primeiro e cai para JSON se PostgreSQL falhar.
- Escrita grava no JSON e tenta gravar no PostgreSQL.
- Falha PostgreSQL é registrada no Audit Log e não quebra Radar, Triagem ou Alertas.

Migração inicial executada:

- `radar_opportunities`: 39 oportunidades.
- `triage_items`: 5 itens de fila.
- `triage_items` como logs: 2 logs de triagem.
- `alerts`: 3 alertas.
- `alerts` como logs: 2 logs de geração de alertas.

Comando de migração manual:

```bash
cd /root/lici-app
PYTHONPATH=/root/lici-app/backend ./backend/venv/bin/python backend/app/services/radar_migration.py
```

Validações realizadas:

- `compileall` dos serviços/APIs OK.
- Listar oportunidades OK.
- Executar Radar OK.
- Executar Triagem OK.
- Gerar Alertas OK.
- Marcar alerta como lido OK.
- Fallback JSON com PostgreSQL indisponível simulado OK.

Fora de escopo nesta fase:

- Órgãos.
- Consultor.
- Documentos.

---

## PostgreSQL Fase 5 — Órgãos + Consultor

Status: **implementada e validada em 2026-05-11**.

A quinta etapa PostgreSQL migrou os domínios Órgãos e Consultor para operação híbrida, preservando JSON como fallback operacional.

Tabelas criadas:

- `orgaos`
- `orgao_events`
- `consultor_clientes`
- `consultor_demandas`

Arquivos novos:

- `backend/app/services/orgao_pg_store.py`
- `backend/app/services/orgao_migration.py`

Arquivos alterados:

- `backend/app/services/orgao_store.py`
- `backend/app/services/consultor_store.py`
- `backend/app/services/orgao_engine.py`
- `backend/app/services/consultor_engine.py`

Persistência atual:

- JSONs preservados e continuam obrigatórios:
  - `/root/lici-app/orgaos/orgaos.json`
  - `/root/lici-app/orgaos/historico.json`
  - `/root/lici-app/consultor/clientes.json`
  - `/root/lici-app/consultor/demandas.json`
- Leitura tenta PostgreSQL primeiro e cai para JSON se PostgreSQL falhar.
- Escrita grava no JSON e tenta gravar no PostgreSQL.
- Falha PostgreSQL é registrada no Audit Log e não quebra Órgãos ou Consultor.

Migração inicial executada:

- `orgaos`: 0 órgãos existentes no JSON.
- `orgao_events`: 0 eventos existentes no JSON.
- `consultor_clientes`: 0 clientes existentes no JSON.
- `consultor_demandas`: 0 demandas existentes no JSON.

Comando de migração manual:

```bash
cd /root/lici-app
PYTHONPATH=/root/lici-app/backend ./backend/venv/bin/python backend/app/services/orgao_migration.py
```

Validações realizadas:

- `compileall` dos serviços/APIs OK.
- Listar órgãos OK.
- Registrar órgão OK.
- Registrar evento de órgão OK.
- Consultar histórico OK.
- Listar clientes OK.
- Cadastrar cliente OK.
- Registrar demanda OK.
- Atualizar status da demanda OK.
- Fallback JSON com PostgreSQL indisponível simulado OK.

Fora de escopo nesta fase:

- Documentos enviados.
- Documentos gerados.
- Exports.
- Audit Log completo em PostgreSQL.

---

## PostgreSQL Fase 6 — Documentos e Exportações

Status: **implementada e validada em 2026-05-11**.

A sexta etapa PostgreSQL migrou metadados de documentos enviados, documentos gerados e exportações para operação híbrida, mantendo JSON e arquivos físicos como fallback operacional.

Tabelas criadas:

- `uploaded_documents`
- `generated_documents`
- `exported_files`

Arquivos novos:

- `backend/app/services/document_pg_store.py`
- `backend/app/services/document_migration.py`

Arquivos alterados:

- `backend/app/services/upload_store.py`
- `backend/app/services/document_generator_store.py`
- `backend/app/services/upload_engine.py`
- `backend/app/services/document_generator.py`
- `backend/app/services/export_engine.py`

Persistência atual:

- JSONs preservados e continuam obrigatórios:
  - `/root/lici-app/storage/documentos.json`
  - `/root/lici-app/storage/documentos_gerados/index.json`
- Arquivos físicos preservados e continuam no filesystem:
  - `/root/lici-app/storage/editais`
  - `/root/lici-app/storage/documentos_gerados`
  - `/root/lici-app/storage/exportados`
- PostgreSQL guarda metadados e payload operacional; o conteúdo binário permanece no filesystem.
- Leitura tenta PostgreSQL primeiro e cai para JSON/arquivos se PostgreSQL falhar.
- Escrita grava no JSON/arquivo físico e tenta gravar no PostgreSQL.
- Falha PostgreSQL é registrada no Audit Log e não quebra Upload, Document Generator ou Export Engine.

Migração inicial executada:

- `uploaded_documents`: 0 documentos enviados existentes no JSON.
- `generated_documents`: 1 documento gerado existente no JSON.
- `exported_files`: 0 arquivos existentes em `/root/lici-app/storage/exportados` antes da validação.

Comando de migração manual:

```bash
cd /root/lici-app
PYTHONPATH=/root/lici-app/backend ./backend/venv/bin/python backend/app/services/document_migration.py
```

Validações realizadas:

- `compileall` dos serviços/APIs OK.
- Listar documentos enviados OK.
- Upload de documento TXT OK.
- Analisar documento OK.
- Gerar peça OK.
- Listar peças geradas OK.
- Exportar TXT OK.
- Exportar DOCX OK.
- Fallback JSON com PostgreSQL indisponível simulado OK.

Fora de escopo nesta fase:

- Audit Log completo em PostgreSQL.

## Observabilidade Robusta

Camada técnica criada para monitorar estabilidade operacional da LICI sem criar novos módulos de negócio.

Endpoint principal:

- `GET /observabilidade/status`

Central de logs estruturados:

- `/root/lici-app/logs/api.jsonl`
- `/root/lici-app/logs/memory_core.jsonl`
- `/root/lici-app/logs/scheduler.jsonl`
- `/root/lici-app/logs/backup.jsonl`
- `/root/lici-app/logs/healthcheck.jsonl`
- `/root/lici-app/logs/alerts.jsonl`

O endpoint retorna:

- tempo de resposta da API;
- erros 4xx/5xx;
- uso e disponibilidade do PostgreSQL;
- uso de disco;
- status de serviços systemd;
- status de timers;
- backups recentes;
- healthchecks;
- dashboard técnico básico;
- alertas técnicos.

Alertas críticos registrados no Audit Log:

- backup falhou;
- PostgreSQL indisponível;
- timer parado;
- API lenta;
- healthcheck com erro;
- serviço crítico parado.

Rotação de logs:

- rotação interna leve no serviço de observabilidade;
- rotação própria diária via `/root/lici-app/scripts/rotate_logs.sh`;
- timer systemd `lici-log-rotate.timer`;
- configuração futura compatível em `/etc/logrotate.d/lici-observability` caso o pacote logrotate seja instalado.

Documentação completa:

- `/root/lici-docs/arquitetura/OBSERVABILIDADE.md`

## LICI Chat Telemetry

O Chat LICI possui telemetria operacional sem IA externa e sem ações automáticas.

### Endpoints

- `GET /chat/engine`
- `POST /chat/mensagem`
- `GET /chat/historico`
- `GET /chat/conversas`
- `GET /chat/metricas`

Todos são protegidos por JWT/permissão de leitura operacional.

### Persistência

JSON obrigatório:

- `/root/lici-app/chat/conversas.json`
- `/root/lici-app/chat/metricas.json`

PostgreSQL quando disponível:

- `chat_sessions`
- `chat_messages`
- `chat_metrics`

### Métricas coletadas

- intenção detectada;
- ferramentas usadas;
- sucesso/falha;
- resposta encontrada/não encontrada;
- tempo de resposta;
- tamanho da conversa;
- usuário e perfil;
- sessão;
- endpoint;
- erros.

### Dashboard frontend

A tela `Chat LICI` exibe um dashboard técnico com uso do chat, principais intenções, falhas, consultas sem resposta, módulos acionados e uso por perfil.

## LICI Concorrentes Engine — Fase 1

Módulo operacional estratégico para inteligência de concorrentes em licitações.

### Endpoints

- `GET /concorrentes/engine`
- `GET /concorrentes`
- `POST /concorrentes/registrar`
- `GET /concorrentes/{id}`
- `POST /concorrentes/{id}/registrar-evento`
- `GET /concorrentes/{id}/historico`
- `GET /concorrentes/analise`

### Persistência

JSON obrigatório:

- `/root/lici-app/concorrentes/concorrentes.json`
- `/root/lici-app/concorrentes/historico.json`

PostgreSQL complementar:

- `competitors`
- `competitor_events`

O padrão permanece dual-write com JSON obrigatório e leitura PostgreSQL-first com fallback JSON.

### Segurança

- JWT obrigatório;
- leitura via `dados:ler`;
- escrita via `dados:escrever`;
- Audit Log em consultas, registros, eventos, análises, fallback e dual-write.

### Integrações

- Busca Global;
- Chat LICI determinístico sem IA externa;
- Memory Core;
- Case Engine;
- Órgãos;
- Radar;
- Observabilidade.

### Frontend

Tela `Concorrentes` com ranking, risco, frequência, taxa de vitória, órgãos relacionados, cadastro e registro de eventos.

Documentação: `/root/lici-docs/arquitetura/CONCORRENTES_ENGINE.md`.

### Integração Concorrentes Engine + Decision Engine

O Decision Engine considera inteligência de concorrentes conhecidos ao decidir `PARTICIPAR`, `IMPUGNAR`, `ESTRATÉGIA HÍBRIDA`, `DESISTIR` ou `ANALISAR MAIS`.

A decisão consulta:

- concorrentes relacionados ao órgão;
- concorrentes relacionados ao segmento/objeto;
- eventos históricos;
- taxa de vitória;
- risco operacional;
- padrão de preço baixo;
- comportamento agressivo;
- padrão documental;
- histórico de inabilitação.

A resposta de `POST /decisao/decidir` inclui campos adicionais e retrocompatíveis:

- `risco_concorrencial`;
- `concorrentes_relevantes`;
- `oportunidade_ataque`;
- `recomendacao_blindagem`.

Se não houver concorrente cadastrado ou relacionado, o fluxo antigo é preservado com fallback concorrencial vazio.

Dashboard/Kanban:

- `/dashboard/resumo` inclui `risco_concorrencial`;
- `/dashboard/kpis` inclui `casos_com_risco_concorrencial_total`;
- `/dashboard/casos` inclui `risco_concorrencial` por caso quando aplicável;
- frontend exibe KPI, ações recomendadas e badge no Kanban.

Validação: `/tmp/decision_concorrentes_validation.json`.

## LICI Notificações Externas — Fase 1

Módulo para enviar alertas críticos fora do painel. A Fase 1 usa Telegram como provedor inicial e não usa WhatsApp.

### Endpoints

Todos exigem JWT e admin:

- `GET /notificacoes/engine`
- `POST /notificacoes/testar`
- `POST /notificacoes/enviar`

### Arquivos

- Configuração: `/root/lici-app/notificacoes/config.json`
- Logs: `/root/lici-app/notificacoes/logs.json`

### Eventos notificáveis

- `oportunidade_prioridade_alta`
- `alerta_critico`
- `risco_concorrencial_alto`
- `falha_backup`
- `healthcheck_erro`
- `prazo_critico`
- `teste`

### Segurança

- `enabled=false` por padrão;
- `dry_run=true` recomendado para teste;
- admin obrigatório;
- anti-spam por cooldown e limite/hora;
- Audit Log e Observabilidade ativos;
- token Telegram preferencialmente via `LICI_TELEGRAM_BOT_TOKEN`.

Documentação: `/root/lici-docs/arquitetura/NOTIFICACOES.md`.

## Multiusuário e Organizações — Fase 1

A LICI agora possui base incremental para operação multi-organização sem quebrar o modo single-org.

Principais pontos:

- organização padrão `default-org` para compatibilidade com dados legados;
- cadastro de organizações e vínculos de usuários via `/organizacoes`;
- papéis: `admin_global`, `admin_org`, `operador` e `leitura`;
- enriquecimento do usuário autenticado com organização ativa, organizações disponíveis e permissões organizacionais;
- suporte a `X-Organization-Id` para troca segura de contexto sem reemitir JWT;
- isolamento por organização em casos, memórias, documentos gerados, consultor/demandas, concorrentes, órgãos, dashboard, chat e ações de chat;
- bloqueio de cancelamento/execução de ações de chat de outra organização;
- métricas de observabilidade por organização;
- fallback `default-org` para registros antigos sem `organization_id`.

Documentação técnica: `/root/lici-docs/arquitetura/MULTIUSUARIO_ORGANIZACOES.md`.

## LICI v0.2 — Fornecedor Full + Consultor Full

A v0.2 inicia a transformação da LICI em plataforma operacional completa para fornecedor/empresário e consultor licitatório, sem evoluir Comprador Público nesta etapa e sem IA livre.

### Fornecedor Full

Endpoints protegidos por JWT e multi-org:

- `GET /fornecedor-full/engine`
- `GET /fornecedor-full/dashboard`
- `GET /fornecedor-full/registros?tipo=`
- `POST /fornecedor-full/registros`
- `PATCH /fornecedor-full/registros/{record_id}`

Cobre gestão contratual, execução contratual, financeiro operacional, risco contratual e dashboard fornecedor. Persistência híbrida: JSON em `/root/lici-app/fornecedor_full/records.json` + PostgreSQL em `fornecedor_full_records` quando disponível.

### Consultor Full

Endpoints protegidos por JWT e multi-org:

- `GET /consultor-full/engine`
- `GET /consultor-full/dashboard`
- `GET /consultor-full/registros?tipo=`
- `POST /consultor-full/registros`
- `PATCH /consultor-full/registros/{record_id}`

Cobre CRM consultivo, leads/prospecção, carteira estratégica, funil, agenda comercial, Central do Cliente 360°, gestão operacional, portal do cliente e financeiro consultivo. Persistência híbrida: JSON em `/root/lici-app/consultor_full/records.json` + PostgreSQL em `consultor_full_records` quando disponível.

Documentação oficial:

- `/root/lici-docs/releases/FORNECEDOR_FULL.md`
- `/root/lici-docs/releases/CONSULTOR_FULL.md`

Garantias preservadas: `v0.1.0-stable`, JWT, multi-org, ownership, observabilidade, Audit Log, fallback JSON, PostgreSQL híbrido e ausência de automações silenciosas.

## Performance & Stability v0.2-beta

Pass de maturidade operacional aplicado após Fornecedor Full + Consultor Full.

Melhorias principais:

- `/observabilidade/status` com cache leve, endpoints mais lentos, taxa de erro por endpoint, requests por organização, métricas PostgreSQL, uso de CPU/load, memória do processo e crescimento de logs.
- `/health/full` com latência HTTP, checagem PostgreSQL, tamanho do banco, tabelas v0.2, diretórios/JSONs v0.2 e crescimento de logs.
- Stores v0.2 com paginação, cache de disponibilidade PostgreSQL, filtros SQL por organização/tipo e índices compostos.
- Frontend com skeleton loading, debounce na Busca Global, carregamento mais progressivo e limite visual para tabelas grandes.

Documento oficial: `/root/lici-docs/releases/PERFORMANCE_STABILITY_v0.2-beta.md`.

Garantias preservadas: JWT, multi-org, ownership, Audit Log, observabilidade, fallback JSON e PostgreSQL híbrido.
