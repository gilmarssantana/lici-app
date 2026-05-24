const API_BASE = '/api'
const TOKEN_KEY = 'lici.auth.token'
const USER_KEY = 'lici.auth.user'
const ORG_KEY = 'lici.active.organization'

let authToken = localStorage.getItem(TOKEN_KEY) || ''
let activeOrganizationId = localStorage.getItem(ORG_KEY) || ''
let unauthorizedHandler = null

export function getStoredSession() {
  const token = localStorage.getItem(TOKEN_KEY) || ''
  const rawUser = localStorage.getItem(USER_KEY)
  let user = null
  if (rawUser) {
    try {
      user = JSON.parse(rawUser)
    } catch {
      localStorage.removeItem(USER_KEY)
    }
  }
  authToken = token
  return { token, user }
}

export function setStoredSession(token, user) {
  authToken = token || ''
  if (token) localStorage.setItem(TOKEN_KEY, token)
  else localStorage.removeItem(TOKEN_KEY)
  if (user) localStorage.setItem(USER_KEY, JSON.stringify(user))
  else localStorage.removeItem(USER_KEY)
}

export function clearStoredSession() {
  authToken = ''
  activeOrganizationId = ''
  localStorage.removeItem(TOKEN_KEY)
  localStorage.removeItem(USER_KEY)
  localStorage.removeItem(ORG_KEY)
}

export function setUnauthorizedHandler(handler) {
  unauthorizedHandler = handler
}

export async function request(path, options = {}) {
  const headers = options.body instanceof FormData
    ? { ...(options.headers || {}) }
    : { 'Content-Type': 'application/json', ...(options.headers || {}) }

  if (authToken && !headers.Authorization) {
    headers.Authorization = `Bearer ${authToken}`
  }
  if (activeOrganizationId && !headers['X-Organization-Id']) {
    headers['X-Organization-Id'] = activeOrganizationId
  }

  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers,
  })

  if (!response.ok) {
    const text = await response.text().catch(() => '')
    if (response.status === 401 && authToken && unauthorizedHandler) {
      unauthorizedHandler()
    }
    const message = `Erro ${response.status} em ${path}: ${text || response.statusText}`
    notifyApiFeedback({ type: 'error', path, method: options.method || 'GET', message })
    throw new Error(message)
  }

  const result = await response.json()
  const method = String(options.method || 'GET').toUpperCase()
  if (method !== 'GET' && !path.startsWith('/auth/')) {
    notifyApiFeedback({ type: 'success', path, method, message: successMessageFor(method, path) })
  }
  return result
}

function notifyApiFeedback(detail) {
  if (typeof window !== 'undefined') {
    window.dispatchEvent(new CustomEvent('lici:api-feedback', { detail }))
  }
}

function successMessageFor(method, path) {
  if (path.includes('/arquivar')) return 'Registro arquivado com segurança. Ele não foi excluído definitivamente.'
  if (method === 'PATCH') return 'Alteração salva com sucesso.'
  if (method === 'POST') return 'Registro criado/ação executada com sucesso.'
  return 'Operação concluída com sucesso.'
}

export const api = {
  baseUrl: API_BASE,
  setAuthToken: (token) => { authToken = token || '' },
  setActiveOrganization: (organizationId) => {
    activeOrganizationId = organizationId || ''
    if (organizationId) localStorage.setItem(ORG_KEY, organizationId)
    else localStorage.removeItem(ORG_KEY)
  },
  organizacoesContexto: () => request('/organizacoes/contexto'),
  organizacoes: () => request('/organizacoes'),
  trocarOrganizacao: (organizationId) => request('/organizacoes/trocar', { method: 'POST', body: JSON.stringify({ organization_id: organizationId }) }),
  login: (payload) => request('/auth/login', { method: 'POST', body: JSON.stringify(payload || {}) }),
  me: () => request('/auth/me'),
  dashboardResumo: () => request('/dashboard/resumo'),
  dashboardOportunidades: () => request('/dashboard/oportunidades'),
  dashboardCasos: () => request('/dashboard/casos'),
  casos: () => request('/casos'),
  caso: (id) => request(`/casos/${id}`),
  criarCaso: (payload) => request('/casos/criar', { method: 'POST', body: JSON.stringify(payload || {}) }),
  atualizarCaso: (id, payload) => request(`/casos/${id}`, { method: 'PATCH', body: JSON.stringify(payload || {}) }),
  arquivarCaso: (id) => request(`/casos/${id}/arquivar`, { method: 'POST' }),
  atualizarFaseCaso: (id, payload) => request(`/casos/${id}/atualizar-fase`, { method: 'POST', body: JSON.stringify(payload || {}) }),
  registrarEventoCaso: (id, payload) => request(`/casos/${id}/registrar-evento`, { method: 'POST', body: JSON.stringify(payload || {}) }),
  dashboardAlertas: () => request('/dashboard/alertas'),
  dashboardMemorias: () => request('/dashboard/memorias'),
  dashboardKpis: () => request('/dashboard/kpis'),
  healthFull: () => request('/health/full'),
  observabilidadeStatus: () => request('/observabilidade/status'),
  buscaGlobal: (q) => request(`/busca/global?q=${encodeURIComponent(q || '')}`),
  casoTimeline: (id) => request(`/casos/${id}/timeline`),
  chatEngine: () => request('/chat/engine'),
  chatMensagem: (payload) => request('/chat/mensagem', { method: 'POST', body: JSON.stringify(payload || {}) }),
  chatHistorico: (conversaId = '', limite = 100) => request(`/chat/historico?limite=${limite}${conversaId ? `&conversa_id=${encodeURIComponent(conversaId)}` : ''}`),
  chatConversas: () => request('/chat/conversas'),
  chatMetricas: () => request('/chat/metricas'),
  chatAcao: (payload) => request('/chat/acao', { method: 'POST', body: JSON.stringify(payload || {}) }),
  perfilAtual: () => request('/perfil/atual'),
  perfilConfiguracoes: () => request('/perfil/configuracoes'),
  selecionarPerfil: (perfil, motivo = '') => request('/perfil/selecionar', { method: 'POST', body: JSON.stringify({ perfil, motivo }) }),
  alertas: () => request('/alertas'),
  auditLogs: (limite = 10) => request(`/audit/logs?limite=${limite}`),
  uploadEdital: (file) => {
    const form = new FormData()
    form.append('file', file)
    return request('/upload/edital', { method: 'POST', body: form })
  },
  listarDocumentosUpload: (incluirArquivados = false) => request(`/upload/documentos?incluir_arquivados=${incluirArquivados ? 'true' : 'false'}`),
  obterDocumentoUpload: (id) => request(`/upload/documentos/${id}`),
  atualizarDocumentoUpload: (id, payload) => request(`/upload/documentos/${id}`, { method: 'PATCH', body: JSON.stringify(payload || {}) }),
  arquivarDocumentoUpload: (id) => request(`/upload/documentos/${id}/arquivar`, { method: 'POST' }),
  analisarDocumentoUpload: (id, payload) => request(`/upload/documentos/${id}/analisar`, { method: 'POST', body: JSON.stringify(payload || {}) }),
  documentosEngine: () => request('/documentos/engine'),
  documentosGerados: (incluirArquivados = false) => request(`/documentos/gerados?incluir_arquivados=${incluirArquivados ? 'true' : 'false'}`),
  documentoGerado: (id) => request(`/documentos/gerados/${id}`),
  atualizarDocumentoGerado: (id, payload) => request(`/documentos/gerados/${id}`, { method: 'PATCH', body: JSON.stringify(payload || {}) }),
  arquivarDocumentoGerado: (id) => request(`/documentos/gerados/${id}/arquivar`, { method: 'POST' }),
  gerarImpugnacao: (payload) => request('/documentos/gerar-impugnacao', { method: 'POST', body: JSON.stringify(payload || {}) }),
  gerarRecurso: (payload) => request('/documentos/gerar-recurso', { method: 'POST', body: JSON.stringify(payload || {}) }),
  gerarContrarrazoes: (payload) => request('/documentos/gerar-contrarrazoes', { method: 'POST', body: JSON.stringify(payload || {}) }),
  exportDocumentoUrl: (id, formato) => `${API_BASE}/export/documentos/${id}/${formato}`,
  exportCasoUrl: (id, formato) => `${API_BASE}/export/casos/${id}/relatorio-${formato}`,
  marcarAlertaLido: (id) => request(`/alertas/${id}/marcar-lido`, { method: 'POST' }),
  arquivarAlerta: (id) => request(`/alertas/${id}/arquivar`, { method: 'POST' }),
  notificacoesEngine: () => request('/notificacoes/engine'),
  notificacoesLogs: () => request('/notificacoes/logs'),
  notificacaoLog: (id) => request(`/notificacoes/logs/${id}`),
  arquivarNotificacaoLog: (id) => request(`/notificacoes/logs/${id}/arquivar`, { method: 'POST' }),
  testarNotificacao: (payload) => request('/notificacoes/testar', { method: 'POST', body: JSON.stringify(payload || {}) }),
  consultorEngine: () => request('/consultor/engine'),
  consultorClientes: () => request('/consultor/clientes'),
  consultorCriarCliente: (payload) => request('/consultor/clientes', { method: 'POST', body: JSON.stringify(payload || {}) }),
  consultorCliente: (id) => request(`/consultor/clientes/${id}`),
  consultorRegistrarDemanda: (id, payload) => request(`/consultor/clientes/${id}/registrar-demanda`, { method: 'POST', body: JSON.stringify(payload || {}) }),
  consultorDemandas: () => request('/consultor/demandas'),
  consultorAtualizarDemanda: (id, payload) => request(`/consultor/demandas/${id}/atualizar-status`, { method: 'POST', body: JSON.stringify(payload || {}) }),
  concorrentesEngine: () => request('/concorrentes/engine'),
  concorrentes: () => request('/concorrentes'),
  concorrentesRegistrar: (payload) => request('/concorrentes/registrar', { method: 'POST', body: JSON.stringify(payload || {}) }),
  concorrente: (id) => request(`/concorrentes/${id}`),
  concorrenteAtualizar: (id, payload) => request(`/concorrentes/${id}`, { method: 'PATCH', body: JSON.stringify(payload || {}) }),
  concorrenteArquivar: (id) => request(`/concorrentes/${id}/arquivar`, { method: 'POST' }),
  concorrenteHistorico: (id) => request(`/concorrentes/${id}/historico`),
  concorrenteRegistrarEvento: (id, payload) => request(`/concorrentes/${id}/registrar-evento`, { method: 'POST', body: JSON.stringify(payload || {}) }),
  concorrentesAnalise: () => request('/concorrentes/analise'),
  orgaosEngine: () => request('/orgaos/engine'),
  orgaos: () => request('/orgaos'),
  orgaoRegistrar: (payload) => request('/orgaos/registrar', { method: 'POST', body: JSON.stringify(payload || {}) }),
  orgao: (id) => request(`/orgaos/${id}`),
  orgaoAtualizar: (id, payload) => request(`/orgaos/${id}`, { method: 'PATCH', body: JSON.stringify(payload || {}) }),
  orgaoArquivar: (id) => request(`/orgaos/${id}/arquivar`, { method: 'POST' }),
  orgaoRegistrarEvento: (id, payload) => request(`/orgaos/${id}/registrar-evento`, { method: 'POST', body: JSON.stringify(payload || {}) }),
  radarEngine: () => request('/radar/engine'),
  radarOportunidades: () => request('/radar/oportunidades'),
  triagemEngine: () => request('/triagem/engine'),
  triagemFila: () => request('/triagem/fila'),
  triagemLogs: () => request('/triagem/logs'),
  fornecedorFullEngine: () => request('/fornecedor-full/engine'),
  fornecedorFullDashboard: () => request('/fornecedor-full/dashboard'),
  fornecedorFullRegistros: (tipo = '', limit = 200, offset = 0) => request(`/fornecedor-full/registros?limit=${limit}&offset=${offset}${tipo ? `&tipo=${encodeURIComponent(tipo)}` : ''}`),
  fornecedorFullCriar: (payload) => request('/fornecedor-full/registros', { method: 'POST', body: JSON.stringify(payload || {}) }),
  fornecedorFullAtualizar: (id, payload) => request(`/fornecedor-full/registros/${id}`, { method: 'PATCH', body: JSON.stringify(payload || {}) }),
  consultorFullEngine: () => request('/consultor-full/engine'),
  consultorFullDashboard: () => request('/consultor-full/dashboard'),
  consultorFullPipeline: () => request('/consultor-full/pipeline'),
  consultorFullCentral360: () => request('/consultor-full/central-360'),
  consultorFullLeads: (status = '', pipelineEtapa = '', limit = 200, offset = 0) => request(`/consultor-full/leads?limit=${limit}&offset=${offset}${status ? `&status=${encodeURIComponent(status)}` : ''}${pipelineEtapa ? `&pipeline_etapa=${encodeURIComponent(pipelineEtapa)}` : ''}`),
  consultorFullCriarLead: (payload) => request('/consultor-full/leads', { method: 'POST', body: JSON.stringify(payload || {}) }),
  consultorFullAtualizarLead: (id, payload) => request(`/consultor-full/leads/${id}`, { method: 'PATCH', body: JSON.stringify(payload || {}) }),
  consultorFullFollowups: (leadId = '', status = '', limit = 200, offset = 0) => request(`/consultor-full/followups?limit=${limit}&offset=${offset}${leadId ? `&lead_id=${encodeURIComponent(leadId)}` : ''}${status ? `&status=${encodeURIComponent(status)}` : ''}`),
  consultorFullCriarFollowup: (payload) => request('/consultor-full/followups', { method: 'POST', body: JSON.stringify(payload || {}) }),
  consultorFullAtualizarFollowup: (id, payload) => request(`/consultor-full/followups/${id}`, { method: 'PATCH', body: JSON.stringify(payload || {}) }),
  consultorFullRegistros: (tipo = '', limit = 200, offset = 0) => request(`/consultor-full/registros?limit=${limit}&offset=${offset}${tipo ? `&tipo=${encodeURIComponent(tipo)}` : ''}`),
  consultorFullCriar: (payload) => request('/consultor-full/registros', { method: 'POST', body: JSON.stringify(payload || {}) }),
  consultorFullAtualizar: (id, payload) => request(`/consultor-full/registros/${id}`, { method: 'PATCH', body: JSON.stringify(payload || {}) }),
  documentalEngine: () => request('/documental/engine'),
  documentalDashboard: () => request('/documental/dashboard'),
  documentalDocumentos: (params = {}) => {
    const query = new URLSearchParams()
    Object.entries(params || {}).forEach(([key, value]) => { if (value !== undefined && value !== null && value !== '') query.set(key, value) })
    return request(`/documental/documentos${query.toString() ? `?${query}` : ''}`)
  },
  documentalCriar: (payload) => request('/documental/documentos', { method: 'POST', body: JSON.stringify(payload || {}) }),
  documentalAtualizar: (id, payload) => request(`/documental/documentos/${id}`, { method: 'PATCH', body: JSON.stringify(payload || {}) }),
  documentalUpload: (file, metadata) => {
    const form = new FormData()
    form.append('file', file)
    form.append('metadata', JSON.stringify(metadata || {}))
    return request('/documental/documentos/upload', { method: 'POST', body: form })
  },
  documentalDossie: (empresaNome = '', empresaId = '') => request(`/documental/dossie?empresa_nome=${encodeURIComponent(empresaNome || '')}${empresaId ? `&empresa_id=${encodeURIComponent(empresaId)}` : ''}`),
  documentalChecklist: (payload) => request('/documental/checklist', { method: 'POST', body: JSON.stringify(payload || {}) }),
  memorias: (tipo = '') => request(`/memoria/listar${tipo ? `?tipo=${encodeURIComponent(tipo)}` : ''}`),
  memoriaBuscar: (termo = '', tipo = '') => request(`/memoria/buscar?termo=${encodeURIComponent(termo || '')}${tipo ? `&tipo=${encodeURIComponent(tipo)}` : ''}`),
  memoriaRegistrar: (payload) => request('/memoria/registrar', { method: 'POST', body: JSON.stringify(payload || {}) }),
  memoria: (id) => request(`/memoria/${id}`),
  memoriaAtualizar: (id, payload) => request(`/memoria/${id}`, { method: 'PATCH', body: JSON.stringify(payload || {}) }),
  memoriaArquivar: (id) => request(`/memoria/${id}/arquivar`, { method: 'POST' }),
  iaAssistivaEngine: () => request('/ia-assistiva/engine'),
  iaAssistivaResponder: (payload) => request('/ia-assistiva/responder', { method: 'POST', body: JSON.stringify(payload || {}) }),
  iaAssistivaFeedback: (payload) => request('/ia-assistiva/feedback', { method: 'POST', body: JSON.stringify(payload || {}) }),
  iaAssistivaTelemetria: () => request('/ia-assistiva/telemetria'),
}


