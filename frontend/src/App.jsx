import { useEffect, useMemo, useState } from 'react'
import {
  AlertTriangle,
  BarChart3,
  Bell,
  BookOpen,
  BriefcaseBusiness,
  CheckCircle2,
  Clock,
  Copy,
  Database,
  Download,
  Eye,
  FileText,
  LayoutDashboard,
  LogOut,
  Loader2,
  Menu,
  MessageCircle,
  RefreshCcw,
  Search,
  Send,
  Target,
  UploadCloud,
  UserCircle,
  X,
} from 'lucide-react'
import { api, clearStoredSession, getStoredSession, setStoredSession, setUnauthorizedHandler } from './services/api.js'

const enterpriseNavigation = {
  consultor: [
    { id: 'dashboard', label: 'Central Operacional', icon: LayoutDashboard, enabled: true, status: 'ativo' },
    { id: 'crm', label: 'CRM', icon: UserCircle, enabled: true, status: 'ativo' },
    { id: 'pipeline', label: 'Pipeline', icon: BarChart3, enabled: true, status: 'ativo' },
    { id: 'clientes', label: 'Clientes', icon: BriefcaseBusiness, enabled: true, status: 'ativo' },
    { id: 'operacao', label: 'Operação', icon: CheckCircle2, enabled: true, status: 'ativo' },
    { id: 'documental', label: 'Documental', icon: FileText, enabled: true, status: 'ativo' },
    { id: 'casos', label: 'Casos', icon: BriefcaseBusiness, enabled: true, status: 'ativo' },
    { id: 'financeiro', label: 'Financeiro', icon: Database, enabled: true, status: 'ativo' },
    { id: 'relatorios', label: 'Relatórios', icon: BarChart3, enabled: true, status: 'ativo' },
    { id: 'ia-assistiva', label: 'IA Assistiva', icon: MessageCircle, enabled: true, status: 'ativo' },
  ],
  fornecedor: [
    { id: 'dashboard', label: 'Central Operacional', icon: LayoutDashboard, enabled: true, status: 'ativo' },
    { id: 'oportunidades', label: 'Oportunidades', icon: Target, enabled: true, status: 'ativo' },
    { id: 'casos', label: 'Casos', icon: BriefcaseBusiness, enabled: true, status: 'ativo' },
    { id: 'documental', label: 'Documental', icon: FileText, enabled: true, status: 'ativo' },
    { id: 'contratos', label: 'Contratos', icon: BriefcaseBusiness, enabled: true, status: 'ativo' },
    { id: 'financeiro', label: 'Financeiro', icon: Database, enabled: true, status: 'ativo' },
    { id: 'concorrentes', label: 'Concorrentes', icon: UserCircle, enabled: true, status: 'ativo' },
    { id: 'orgaos', label: 'Órgãos', icon: Database, enabled: true, status: 'ativo' },
    { id: 'ia-assistiva', label: 'IA Assistiva', icon: MessageCircle, enabled: true, status: 'ativo' },
  ],
}

const fallbackNavigation = enterpriseNavigation.fornecedor

const iconMap = {
  AlertTriangle,
  BarChart3,
  Bell,
  BookOpen,
  BriefcaseBusiness,
  CheckCircle2,
  Clock,
  Database,
  FileText,
  LayoutDashboard,
  MessageCircle,
  Search,
  Target,
  UploadCloud,
  UserCircle,
}

const severityStyle = {
  critica: 'bg-red-500/15 text-red-200 ring-1 ring-red-400/30',
  alta: 'bg-orange-500/15 text-orange-200 ring-1 ring-orange-400/30',
  media: 'bg-yellow-500/15 text-yellow-100 ring-1 ring-yellow-400/30',
  baixa: 'bg-sky-500/15 text-sky-100 ring-1 ring-sky-400/30',
}

const triageStyle = {
  prioridade_alta: 'bg-emerald-500/15 text-emerald-200 ring-1 ring-emerald-400/30',
  analisar: 'bg-blue-500/15 text-blue-200 ring-1 ring-blue-400/30',
  monitorar: 'bg-slate-500/20 text-slate-200 ring-1 ring-slate-400/20',
  descartar: 'bg-red-500/10 text-red-200 ring-1 ring-red-400/20',
}

const casePhases = [
  'prospecção',
  'análise',
  'impugnação',
  'habilitação',
  'disputa',
  'recurso',
  'homologação',
  'contrato',
  'execução',
  'pagamento',
  'encerrado',
]

const caseStatuses = ['ativo', 'suspenso', 'vencido', 'perdido', 'encerrado', 'arquivado']

const caseEventTypes = [
  'edital analisado',
  'impugnação enviada',
  'recurso protocolado',
  'concorrente inabilitado',
  'vitória',
  'perda',
  'contrato assinado',
  'pagamento atrasado',
  'reequilíbrio solicitado',
  'caso atualizado',
]

function useAsyncData(loader, deps = []) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [refreshKey, setRefreshKey] = useState(0)

  useEffect(() => {
    let alive = true
    setLoading(true)
    setError('')
    loader()
      .then((result) => alive && setData(result))
      .catch((err) => alive && setError(err.message || 'Erro ao carregar dados'))
      .finally(() => alive && setLoading(false))
    return () => {
      alive = false
    }
  }, [...deps, refreshKey])

  return { data, loading, error, refresh: () => setRefreshKey((key) => key + 1) }
}

function useDebouncedValue(value, delay = 350) {
  const [debounced, setDebounced] = useState(value)
  useEffect(() => {
    const timer = setTimeout(() => setDebounced(value), delay)
    return () => clearTimeout(timer)
  }, [value, delay])
  return debounced
}

function SkeletonCards({ count = 6 }) {
  return (
    <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
      {Array.from({ length: count }).map((_, index) => (
        <div key={index} className="card p-5">
          <div className="skeleton-shimmer h-3 w-24 rounded-full" />
          <div className="skeleton-shimmer mt-5 h-9 w-36 rounded-2xl" />
          <div className="skeleton-shimmer mt-4 h-3 w-full rounded-full" />
          <div className="skeleton-shimmer mt-2 h-3 w-3/4 rounded-full" />
        </div>
      ))}
    </div>
  )
}

function ApiFeedbackToasts() {
  const [items, setItems] = useState([])
  useEffect(() => {
    function onFeedback(event) {
      const detail = event.detail || {}
      const id = `${Date.now()}-${Math.random().toString(16).slice(2)}`
      setItems((current) => [...current.slice(-2), { id, ...detail }])
      window.setTimeout(() => setItems((current) => current.filter((item) => item.id !== id)), detail.type === 'error' ? 6500 : 4200)
    }
    window.addEventListener('lici:api-feedback', onFeedback)
    return () => window.removeEventListener('lici:api-feedback', onFeedback)
  }, [])
  if (!items.length) return null
  return (
    <div className="fixed right-4 top-4 z-50 grid w-[calc(100vw-2rem)] max-w-md gap-3">
      {items.map((item) => {
        const error = item.type === 'error'
        const Icon = error ? AlertTriangle : CheckCircle2
        return (
          <div key={item.id} className={`rounded-2xl border p-4 shadow-2xl backdrop-blur-xl ${error ? 'border-red-400/30 bg-red-950/90 text-red-50 shadow-red-950/30' : 'border-emerald-400/30 bg-emerald-950/90 text-emerald-50 shadow-emerald-950/30'}`}>
            <div className="flex gap-3">
              <Icon size={20} className={error ? 'text-red-200' : 'text-emerald-200'} />
              <div className="min-w-0 flex-1">
                <p className="font-black">{error ? 'Ação não concluída' : 'Ação confirmada'}</p>
                <p className="mt-1 text-sm opacity-90">{item.message}</p>
                <p className="mt-2 text-[11px] uppercase tracking-wide opacity-55">{item.method} · {item.path}</p>
              </div>
              <button onClick={() => setItems((current) => current.filter((toast) => toast.id !== item.id))} className="h-7 w-7 rounded-lg bg-white/10 text-white/80 hover:bg-white/20"><X size={15} className="mx-auto" /></button>
            </div>
          </div>
        )
      })}
    </div>
  )
}

const moduleHelp = {
  dashboard: 'Comece pelo card Primeiros passos. Depois assuma uma prioridade, crie/atualize registros e acompanhe confirmações no canto superior.',
  central: 'Use esta tela para decidir o que fazer agora. Clique em uma prioridade para ver motivo, consequência, responsável e ação sugerida.',
  oportunidades: 'Analise score, prazo e objeto. Quando houver aderência, transforme a oportunidade em caso para controlar a disputa.',
  casos: 'Cada caso deve ter fase, risco, próxima ação e eventos. Use editar para manter contexto e arquivar apenas quando quiser baixa lógica.',
  documental: 'Cadastre certidões e documentos críticos, acompanhe validade e monte dossiês antes da habilitação.',
  concorrentes: 'Registre padrões, falhas, eventos e riscos dos concorrentes para usar em impugnação, recurso ou estratégia de disputa.',
  orgaos: 'Mapeie comportamento do órgão, exigências recorrentes, histórico de pagamento e padrão de julgamento.',
  contratos: 'Controle execução, riscos, financeiro, prazos e registros de contrato após vencer a licitação.',
  financeiro: 'Acompanhe cobranças, pendências, valores e status para proteger caixa e execução contratual.',
  memorias: 'Transforme aprendizados em memória reutilizável: tese, risco, órgão, concorrente, vitória, perda ou padrão.',
  crm: 'Cadastre leads, etapa comercial, potencial, follow-up e risco de churn para organizar a operação consultiva.',
}

function ModuleHelp({ current }) {
  const text = moduleHelp[current]
  if (!text) return null
  return (
    <>
      <details className="mb-4 rounded-2xl border border-cyan-400/20 bg-cyan-500/10 text-sm leading-6 text-cyan-50/90 md:hidden">
        <summary className="flex cursor-pointer items-center gap-2 px-4 py-3 font-black text-white"><BookOpen size={17} className="text-cyan-200" /> Como usar esta tela</summary>
        <div className="border-t border-cyan-300/10 px-4 pb-4 pt-3 text-cyan-50/85">{text}</div>
      </details>
      <div className="mb-5 hidden rounded-2xl border border-cyan-400/20 bg-cyan-500/10 p-4 text-sm leading-6 text-cyan-50/90 md:block">
        <div className="flex gap-3">
          <BookOpen size={18} className="mt-0.5 shrink-0 text-cyan-200" />
          <div><strong className="text-white">Como usar esta tela:</strong> {text}</div>
        </div>
      </div>
    </>
  )
}

function MobileBottomNav({ current, navigation, onNavigate }) {
  const priority = ['dashboard', 'oportunidades', 'casos', 'documental', 'financeiro', 'crm', 'operacao']
  const items = priority.map((id) => navigation.find((item) => item.id === id)).filter(Boolean).slice(0, 5)
  if (!items.length) return null
  return (
    <nav className="fixed inset-x-0 bottom-0 z-40 border-t border-white/10 bg-slate-950/92 px-2 pb-[calc(env(safe-area-inset-bottom)+0.45rem)] pt-2 shadow-[0_-18px_35px_rgba(0,0,0,0.45)] backdrop-blur-xl lg:hidden">
      <div className="mx-auto grid max-w-xl grid-cols-5 gap-1">
        {items.map((item) => {
          const Icon = item.icon || Database
          const selected = item.id === current
          return (
            <button key={item.id} onClick={() => onNavigate(item.id)} className={`flex min-h-14 flex-col items-center justify-center rounded-2xl px-1 py-2 text-[10px] font-black transition ${selected ? 'bg-blue-600 text-white shadow-lg shadow-blue-950/35' : 'text-slate-400 hover:bg-white/5 hover:text-white'}`}>
              <Icon size={18} />
              <span className="mt-1 max-w-full truncate">{item.label}</span>
            </button>
          )
        })}
      </div>
    </nav>
  )
}

function Shell({ current, onNavigate, navigation, profile, profileOptions, profileLoading, profileError, onSelectProfile, sessionUser, onLogout, children }) {
  const active = navigation.find((item) => item.id === current) || fallbackNavigation.find((item) => item.id === current)
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)
  const go = (id) => {
    onNavigate(id)
    setMobileMenuOpen(false)
  }
  return (
    <div className="min-h-screen lg:flex">
      <div className="sticky top-0 z-30 flex items-center justify-between border-b border-white/10 bg-slate-950/90 px-4 py-3 shadow-xl shadow-black/20 backdrop-blur-xl lg:hidden">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-blue-500/15 text-xl ring-1 ring-blue-400/30">⚖️</div>
          <div><p className="font-black text-white">LICI</p><p className="text-xs text-slate-500">{active?.label || 'Módulo'}</p></div>
        </div>
        <button onClick={() => setMobileMenuOpen((value) => !value)} className="rounded-xl border border-white/10 bg-slate-900/90 p-2 text-slate-200 shadow-lg shadow-black/20 transition hover:border-blue-300/40 hover:text-white">
          {mobileMenuOpen ? <X size={20} /> : <Menu size={20} />}
        </button>
      </div>
      <aside className={`${mobileMenuOpen ? 'block' : 'hidden'} max-h-[calc(100vh-65px)] overflow-y-auto border-b border-white/10 bg-slate-950/92 shadow-2xl shadow-black/25 backdrop-blur-xl mobile-scroll lg:fixed lg:inset-y-0 lg:left-0 lg:block lg:h-screen lg:max-h-screen lg:w-72 lg:border-b-0 lg:border-r`}>
        <div className="flex items-center gap-3 px-5 py-5">
          <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-blue-500/15 text-2xl ring-1 ring-blue-400/30">⚖️</div>
          <div>
            <p className="text-lg font-black tracking-tight text-white">LICI</p>
            <p className="text-xs text-slate-400">Central de Comando</p>
          </div>
        </div>
        <nav className="flex gap-2 overflow-x-auto px-3 pb-4 lg:block lg:space-y-1 lg:overflow-visible">
          {navigation.map((item) => {
            const Icon = item.icon || Database
            const selected = item.id === current
            const structural = item.enabled === false || item.status !== 'ativo'
            return (
              <button
                key={item.id}
                onClick={() => go(item.id)}
                className={`flex shrink-0 items-center gap-3 rounded-xl px-4 py-3 text-sm font-semibold transition lg:w-full ${
                  selected
                    ? 'bg-blue-500 text-white shadow-lg shadow-blue-950/40 ring-1 ring-blue-300/30'
                    : structural
                      ? 'text-slate-500 hover:bg-white/[0.04] hover:text-slate-200'
                      : 'text-slate-300 hover:bg-white/[0.06] hover:text-white'
                }`}
              >
                <Icon size={18} />
                <span className="min-w-0 flex-1 text-left">{item.label}</span>
              </button>
            )
          })}
        </nav>
        <div className="px-5 py-4 text-xs text-slate-500">
          <label className="block font-bold uppercase tracking-wide text-slate-500">Perfil operacional</label>
          <select
            value={profile?.perfil_atual || 'fornecedor'}
            onChange={(event) => onSelectProfile(event.target.value)}
            disabled={profileLoading}
            className="input mt-2 w-full rounded-xl px-3 py-2 text-sm font-bold disabled:opacity-60"
          >
            {(profileOptions || []).map((item) => <option key={item.id} value={item.id}>{item.nome}</option>)}
          </select>
          {profileError && <p className="mt-2 text-[11px] text-yellow-200">Perfil em fallback: {profileError}</p>}
          {sessionUser && (
            <div className="mt-4 rounded-2xl border border-white/10 bg-slate-900/55 p-3 text-slate-300 shadow-lg shadow-black/10">
              <div className="flex items-center gap-2 text-sm font-bold text-white">
                <UserCircle size={18} /> {sessionUser.nome || sessionUser.usuario}
              </div>
              <p className="mt-1 text-[11px] uppercase tracking-wide text-slate-500">{sessionUser.perfil} · {sessionUser.usuario}</p>
              <button onClick={onLogout} className="mt-3 flex w-full items-center justify-center gap-2 rounded-xl border border-white/10 bg-slate-800/85 px-3 py-2 text-xs font-bold text-slate-200 transition hover:border-red-300/30 hover:bg-red-500/20 hover:text-red-100">
                <LogOut size={14} /> Sair
              </button>
            </div>
          )}
        </div>
      </aside>
      <main className="pb-24 lg:ml-72 lg:flex-1 lg:pb-0">
        <header className="sticky top-0 z-10 border-b border-white/10 bg-slate-950/72 px-4 py-3 shadow-xl shadow-black/10 backdrop-blur-xl md:px-8 md:py-4">
          <div className="flex flex-col justify-between gap-3 md:flex-row md:items-center">
            <div>
              <p className="hidden text-sm text-slate-400 md:block">{profile?.configuracao?.nome || 'Operação'} · central operacional</p>
              <h1 className="text-xl font-black text-white md:text-3xl">{active?.label || 'Módulo'}</h1>
            </div>
            <div className="flex flex-wrap gap-2">
              {sessionUser && <div className="hidden badge bg-blue-500/15 text-blue-100 ring-1 ring-blue-400/30 sm:inline-flex"><UserCircle size={14} className="mr-1.5" /> {sessionUser.nome || sessionUser.usuario}</div>}
              <div className="badge bg-emerald-500/15 text-emerald-200 ring-1 ring-emerald-400/30">
                <Database size={14} className="mr-1.5" /> Dados atualizados
              </div>
            </div>
          </div>
        </header>
        <section className="p-3 md:p-7 xl:p-10"><ModuleHelp current={current} />{children}</section>
      </main>
      <MobileBottomNav current={current} navigation={navigation} onNavigate={go} />
    </div>
  )
}

function StateGate({ loading, error, onRetry, children }) {
  if (loading) {
    return (
      <div className="card flex min-h-64 items-center justify-center p-5 text-slate-300">
        <div className="w-full space-y-5"><div className="flex items-center text-sm font-bold text-slate-300"><Loader2 className="mr-3 animate-spin text-blue-200" /> Preparando visão operacional...</div><SkeletonCards count={4} /></div>
      </div>
    )
  }
  if (error) {
    return (
      <div className="card p-6">
        <div className="flex items-start gap-3 text-red-200">
          <AlertTriangle className="mt-1" />
          <div>
            <h3 className="font-bold">Falha ao carregar</h3>
            <p className="mt-1 text-sm text-slate-300">{error}</p>
            <button onClick={onRetry} className="premium-button-primary mt-4">
              Tentar novamente
            </button>
          </div>
        </div>
      </div>
    )
  }
  return children
}

function KpiCard({ title, value, icon: Icon, hint }) {
  return (
    <div className="card p-5 transition duration-200 hover:-translate-y-0.5 hover:border-blue-300/25">
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <p className="text-[11px] font-bold uppercase tracking-[0.18em] text-slate-500">{title}</p>
          <p className="mt-3 text-3xl font-black tracking-tight text-white">{value ?? 0}</p>
          {hint && <p className="mt-2 text-sm leading-5 text-slate-400">{hint}</p>}
        </div>
        <div className="rounded-2xl bg-blue-500/12 p-3 text-blue-200 ring-1 ring-blue-400/20">
          <Icon size={21} />
        </div>
      </div>
    </div>
  )
}

function MetricCard({ label, value, tone = 'neutral' }) {
  const styles = {
    neutral: 'border-slate-800/80 bg-slate-950/45 text-white',
    success: 'border-emerald-400/20 bg-emerald-500/10 text-emerald-100',
    warning: 'border-orange-400/20 bg-orange-500/10 text-orange-100',
    danger: 'border-red-400/20 bg-red-500/10 text-red-100',
  }
  return (
    <div className={`rounded-2xl border p-4 ${styles[tone] || styles.neutral}`}>
      <p className="text-[11px] font-black uppercase tracking-[0.18em] opacity-70">{label}</p>
      <p className="mt-2 text-2xl font-black tracking-tight md:text-3xl">{value}</p>
    </div>
  )
}

function Section({ title, subtitle, action, children }) {
  return (
    <div className="card overflow-hidden">
      <div className="flex flex-col justify-between gap-3 border-b border-white/8 bg-white/[0.025] px-5 py-5 md:flex-row md:items-center md:px-6">
        <div className="max-w-3xl">
          <h2 className="text-lg font-black tracking-tight text-white md:text-xl">{title}</h2>
          {subtitle && <p className="mt-1.5 text-sm leading-6 text-slate-400">{subtitle}</p>}
        </div>
        {action}
      </div>
      <div className="p-5 md:p-6">{children}</div>
    </div>
  )
}

function BuscaGlobal() {
  const [q, setQ] = useState('')
  const [submitted, setSubmitted] = useState('')
  const debouncedQ = useDebouncedValue(q, 450)
  const { data, loading, error, refresh } = useAsyncData(() => submitted ? api.buscaGlobal(submitted) : Promise.resolve({ total: 0, resultados: {}, flat: [] }), [submitted])
  useEffect(() => {
    const value = debouncedQ.trim()
    if (value.length >= 3) setSubmitted(value)
  }, [debouncedQ])

  function submit(event) {
    event.preventDefault()
    setSubmitted(q.trim())
  }

  const groups = data?.resultados || {}
  return (
    <div className="space-y-6">
      <Section title="Busca Global" subtitle="Casos, memórias, oportunidades, alertas, documentos, clientes e órgãos">
        <form onSubmit={submit} className="flex flex-col gap-3 md:flex-row">
          <input value={q} onChange={(event) => setQ(event.target.value)} placeholder="Busque por órgão, objeto, tese, cliente, status ou palavra-chave..." className="min-h-12 flex-1 rounded-2xl border border-slate-700 bg-slate-950 px-4 py-3 text-sm text-slate-100 outline-none ring-blue-400/20 focus:ring-4" />
          <button className="rounded-2xl bg-blue-600 px-5 py-3 text-sm font-black text-white hover:bg-blue-500"><Search size={16} className="mr-2 inline" />Buscar</button>
        </form>
        {submitted && <p className="mt-4 text-sm text-slate-400">{data?.total || 0} resultado(s) para <strong className="text-white">{submitted}</strong></p>}
      </Section>
      <StateGate loading={loading} error={error} onRetry={refresh}>
        {!submitted ? <Empty text="Digite um termo para pesquisar em toda a LICI." /> : (
          <div className="grid gap-6 xl:grid-cols-2">
            {Object.entries(groups).map(([grupo, items]) => (
              <Section key={grupo} title={humanizeAction(grupo)} subtitle={`${items?.length || 0} resultado(s)`}>
                {!items?.length ? <Empty text="Nada encontrado neste grupo." /> : <div className="space-y-3">{items.map((item) => <SearchResultCard key={`${grupo}-${item.tipo}-${item.id}`} item={item} />)}</div>}
              </Section>
            ))}
          </div>
        )}
      </StateGate>
    </div>
  )
}

function SearchResultCard({ item }) {
  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-950/50 p-4">
      <div className="flex flex-wrap items-center gap-2"><Badge value={item.tipo} /><span className="text-xs text-slate-500">score busca {item.score}</span></div>
      <p className="mt-2 font-black text-white">{item.titulo || item.id}</p>
      <p className="mt-1 line-clamp-3 text-sm text-slate-400">{item.subtitulo || 'Sem detalhe adicional.'}</p>
      <div className="mt-3 flex flex-wrap gap-2">{Object.entries(item.metadados || {}).slice(0, 6).map(([key, value]) => <Badge key={key} value={`${key}: ${value}`} />)}</div>
    </div>
  )
}

function MiniBarChart({ title, data = {} }) {
  const entries = Object.entries(data).slice(0, 8)
  const max = Math.max(...entries.map(([, value]) => Number(value) || 0), 1)
  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-950/50 p-5">
      <h3 className="font-black text-white">{title}</h3>
      <div className="mt-4 space-y-3">
        {!entries.length ? <Empty text="Sem dados para gráfico." /> : entries.map(([label, value]) => (
          <div key={label}>
            <div className="mb-1 flex justify-between text-xs"><span className="max-w-[70%] truncate text-slate-300">{label}</span><span className="font-bold text-white">{value}</span></div>
            <div className="h-2 overflow-hidden rounded-full bg-slate-800"><div className="h-full rounded-full bg-blue-500" style={{ width: `${Math.max(8, (Number(value) / max) * 100)}%` }} /></div>
          </div>
        ))}
      </div>
    </div>
  )
}

function OperationalFilters({ filters, onChange, options = {}, showProfile = true }) {
  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-950/45 p-4">
      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-5">
        <TextInput label="Órgão" value={filters.orgao || ''} onChange={(value) => onChange({ ...filters, orgao: value })} placeholder="Filtrar por órgão" />
        <TextInput label="UF" value={filters.uf || ''} onChange={(value) => onChange({ ...filters, uf: value.toUpperCase() })} placeholder="SP" />
        <label className="block"><span className="text-sm font-bold text-white">Status</span><select value={filters.status || ''} onChange={(event) => onChange({ ...filters, status: event.target.value })} className="mt-2 w-full rounded-xl border border-slate-700 bg-slate-950 px-4 py-3 text-sm text-slate-200"><option value="">Todos</option>{(options.status || []).map((item) => <option key={item} value={item}>{item}</option>)}</select></label>
        <TextInput label="Score mínimo" type="number" value={filters.score || ''} onChange={(value) => onChange({ ...filters, score: value })} placeholder="70" />
        {showProfile && <label className="block"><span className="text-sm font-bold text-white">Perfil</span><select value={filters.perfil || ''} onChange={(event) => onChange({ ...filters, perfil: event.target.value })} className="mt-2 w-full rounded-xl border border-slate-700 bg-slate-950 px-4 py-3 text-sm text-slate-200"><option value="">Todos</option>{['fornecedor', 'consultor', 'comprador'].map((item) => <option key={item} value={item}>{item}</option>)}</select></label>}
      </div>
    </div>
  )
}

function ChatLici() {
  const [pergunta, setPergunta] = useState('')
  const [mensagens, setMensagens] = useState([])
  const [conversaId, setConversaId] = useState('')
  const [loading, setLoading] = useState(false)
  const [actionLoading, setActionLoading] = useState(false)
  const [pendingAction, setPendingAction] = useState(null)
  const [actionResult, setActionResult] = useState(null)
  const [error, setError] = useState('')
  const { data: engine } = useAsyncData(api.chatEngine)
  const { data: metricas, refresh: refreshMetricas } = useAsyncData(api.chatMetricas)

  async function submit(event) {
    event.preventDefault()
    const texto = pergunta.trim()
    if (!texto || loading) return
    setLoading(true)
    setError('')
    setPergunta('')
    const userMsg = { id: `local-${Date.now()}`, role: 'user', texto, criado_em: new Date().toISOString() }
    setMensagens((items) => [...items, userMsg])
    try {
      const result = await api.chatMensagem({ pergunta: texto, conversa_id: conversaId || undefined })
      setConversaId(result.conversa_id)
      setMensagens((items) => [...items, { id: result.mensagem_id, role: 'assistant', ...result }])
      if (isActionableText(texto)) {
        const preview = await api.chatAcao({ pergunta: texto, conversa_id: result.conversa_id })
        setPendingAction(preview)
        setActionResult(null)
      }
      refreshMetricas()
    } catch (err) {
      setError(err.message || 'Erro ao conversar com a LICI')
    } finally {
      setLoading(false)
    }
  }

  async function confirmAction() {
    if (!pendingAction) return
    setActionLoading(true)
    setError('')
    try {
      const result = await api.chatAcao({ acao_id: pendingAction.acao_id, confirmar: true })
      setActionResult(result)
      setPendingAction(null)
      refreshMetricas()
    } catch (err) {
      setError(err.message || 'Erro ao confirmar ação')
    } finally {
      setActionLoading(false)
    }
  }

  async function cancelAction() {
    if (!pendingAction) return
    setActionLoading(true)
    setError('')
    try {
      const result = await api.chatAcao({ acao_id: pendingAction.acao_id, cancelar: true })
      setActionResult(result)
      setPendingAction(null)
      refreshMetricas()
    } catch (err) {
      setError(err.message || 'Erro ao cancelar ação')
    } finally {
      setActionLoading(false)
    }
  }

  return (
    <div className="space-y-6">
      <Section title="Chat LICI" subtitle="Converse com a LICI para orientar decisões, localizar dados e preparar próximos passos.">
        <div className="mb-4 flex flex-wrap gap-2">
          <Badge value="assistência operacional" />
          <Badge value="dados protegidos" />
          <Badge value="ações com confirmação" />
        </div>
        <div className="mb-4 grid gap-4 lg:grid-cols-2">
          <div className="rounded-2xl border border-slate-800 bg-slate-950/50 p-4">
            <p className="text-xs font-bold uppercase tracking-wide text-slate-500">O que você pode pedir</p>
            <div className="mt-3 flex flex-wrap gap-2">{(engine?.capacidades || engine?.funcoes || ['consultar casos', 'buscar memórias', 'analisar edital', 'consultar órgãos', 'consultar concorrentes']).slice(0, 8).map((item) => <Badge key={item} value={item} />)}</div>
          </div>
          <div className="rounded-2xl border border-slate-800 bg-slate-950/50 p-4">
            <p className="text-xs font-bold uppercase tracking-wide text-slate-500">Ações rápidas</p>
            <div className="mt-3 flex flex-wrap gap-2">{['criar caso', 'gerar peça', 'registrar memória', 'consultar órgão', 'registrar demanda', 'checklist'].map((item) => <Badge key={item} value={item} />)}</div>
          </div>
        </div>
        <div className="h-[58vh] overflow-y-auto rounded-2xl border border-slate-800 bg-slate-950/60 p-4 mobile-scroll">
          {!mensagens.length && <Empty text="Pergunte sobre caso, edital, memória, oportunidade, órgão, cliente consultor, peça ou decisão." />}
          <div className="space-y-4">
            {mensagens.map((msg) => msg.role === 'user' ? <UserChatBubble key={msg.id} msg={msg} /> : <LiciChatBubble key={msg.id} msg={msg} />)}
            {loading && <div className="flex items-center gap-2 text-sm text-slate-400"><Loader2 size={16} className="animate-spin" />Preparando resposta...</div>}
          </div>
        </div>
        {error && <div className="mt-4"><ErrorBox text={error} /></div>}
        {pendingAction && <ChatActionPreview action={pendingAction} loading={actionLoading} onConfirm={confirmAction} onCancel={cancelAction} />}
        {actionResult && <ChatActionResult action={actionResult} />}
        <form onSubmit={submit} className="mt-4 flex flex-col gap-3 md:flex-row">
          <textarea value={pergunta} onChange={(event) => setPergunta(event.target.value)} placeholder="Ex.: Vale a pena participar do edital da Prefeitura X? / Mostre memórias sobre atestado técnico..." className="min-h-24 flex-1 rounded-2xl border border-slate-700 bg-slate-950 px-4 py-3 text-sm text-slate-100 outline-none ring-blue-400/20 focus:ring-4" />
          <button disabled={loading || !pergunta.trim()} className="rounded-2xl bg-blue-600 px-5 py-3 text-sm font-black text-white hover:bg-blue-500 disabled:cursor-not-allowed disabled:opacity-50"><Send size={16} className="mr-2 inline" />Enviar</button>
        </form>
      </Section>
      
    </div>
  )
}

function ChatActionPreview({ action, loading, onConfirm, onCancel }) {
  const canConfirm = !(action.parametros_faltantes || []).length
  return (
    <div className="mt-4 rounded-2xl border border-blue-400/30 bg-blue-500/10 p-4 text-sm text-blue-50">
      <div className="flex flex-wrap items-center gap-2"><Badge value="ação pendente" /><Badge value={action.acao} /></div>
      <pre className="mt-3 max-h-72 overflow-auto whitespace-pre-wrap rounded-xl bg-slate-950/70 p-3 text-xs text-slate-200">{action.previa}</pre>
      {!!action.parametros_faltantes?.length && <p className="mt-3 text-orange-100">Não posso executar ainda. Faltam: {action.parametros_faltantes.join(', ')}.</p>}
      <div className="mt-4 flex flex-wrap gap-3">
        <button disabled={!canConfirm || loading} onClick={onConfirm} className="rounded-xl bg-emerald-600 px-4 py-2 text-xs font-black text-white hover:bg-emerald-500 disabled:cursor-not-allowed disabled:opacity-50">{loading ? 'Processando...' : 'Confirmar execução'}</button>
        <button disabled={loading} onClick={onCancel} className="rounded-xl bg-slate-800 px-4 py-2 text-xs font-black text-white hover:bg-slate-700 disabled:opacity-50">Cancelar</button>
      </div>
    </div>
  )
}

function ChatActionResult({ action }) {
  return (
    <div className={`mt-4 rounded-2xl border p-4 text-sm ${action.status === 'executada' ? 'border-emerald-400/30 bg-emerald-500/10 text-emerald-50' : action.status === 'cancelada' ? 'border-slate-700 bg-slate-900 text-slate-200' : 'border-red-400/30 bg-red-500/10 text-red-50'}`}>
      <div className="flex flex-wrap items-center gap-2"><Badge value={`ação ${action.status}`} /><Badge value={action.acao} /></div>
      {action.erro && <p className="mt-2">Erro: {action.erro}</p>}
      {action.resultado && <pre className="mt-3 max-h-72 overflow-auto whitespace-pre-wrap rounded-xl bg-slate-950/70 p-3 text-xs text-slate-200">{JSON.stringify(action.resultado, null, 2)}</pre>}
    </div>
  )
}

function ChatTechnicalDashboard({ metricas, onRefresh }) {
  return (
    <Section title="Acompanhamento do Chat" subtitle="Uso recente, temas mais frequentes e pontos que precisam de atenção" action={<button onClick={onRefresh} className="rounded-xl bg-slate-800 px-4 py-2 text-sm font-bold text-white hover:bg-slate-700"><RefreshCcw size={15} className="mr-2 inline" />Atualizar</button>}>
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
        <MetricCard label="Mensagens" value={metricas?.total_mensagens || 0} />
        <MetricCard label="Taxa de sucesso" value={`${metricas?.taxa_sucesso || 0}%`} tone={(metricas?.taxa_sucesso || 0) < 70 ? 'danger' : 'success'} />
        <MetricCard label="Sem resposta" value={metricas?.total_sem_resposta || 0} tone={(metricas?.total_sem_resposta || 0) > 5 ? 'warning' : 'neutral'} />
        <MetricCard label="Tempo médio" value={`${metricas?.tempo_medio_ms || 0} ms`} tone={(metricas?.tempo_medio_ms || 0) > 2500 ? 'warning' : 'neutral'} />
        <MetricCard label="Sessões ativas 24h" value={metricas?.sessoes_ativas_24h || 0} />
        <MetricCard label="Ações solicitadas" value={metricas?.acoes?.solicitacoes_total || 0} />
        <MetricCard label="Ações canceladas" value={metricas?.acoes?.acoes_canceladas || 0} tone={(metricas?.acoes?.acoes_canceladas || 0) > 0 ? 'warning' : 'neutral'} />
      </div>
      <div className="mt-6 grid gap-6 xl:grid-cols-3">
        <TelemetryList title="Principais intenções" items={metricas?.top_intencoes || []} />
        <TelemetryList title="Módulos mais acionados" items={metricas?.top_ferramentas || []} />
        <TelemetryList title="Uso por perfil" items={metricas?.uso_por_perfil || []} />
        <TelemetryList title="Ações operacionais" items={metricas?.acoes?.top_acoes || []} />
      </div>
      <div className="mt-6 grid gap-6 xl:grid-cols-2">
        <div className="rounded-2xl border border-slate-800 bg-slate-950/50 p-4">
          <h3 className="font-black text-white">Consultas sem resposta</h3>
          <div className="mt-3 space-y-3">
            {!(metricas?.perguntas_sem_resposta || []).length ? <Empty text="Nenhuma pergunta sem resposta registrada." /> : metricas.perguntas_sem_resposta.slice(0, 6).map((item, index) => (
              <div key={`${item.criado_em}-${index}`} className="rounded-xl bg-slate-900/70 p-3 text-sm text-slate-300"><Badge value={item.intencao || 'intenção'} /><p className="mt-2">{item.pergunta}</p><p className="mt-1 text-xs text-slate-500">{item.usuario || 'usuário'} · {formatDate(item.criado_em)}</p></div>
            ))}
          </div>
        </div>
        <div className="rounded-2xl border border-slate-800 bg-slate-950/50 p-4">
          <h3 className="font-black text-white">Falhas e alertas</h3>
          <div className="mt-3 space-y-3">
            {!(metricas?.alertas_tecnicos || []).length && !(metricas?.erros_recentes || []).length ? <Empty text="Sem pontos de atenção recentes no Chat." /> : null}
            {(metricas?.alertas_tecnicos || []).map((item) => <div key={item.tipo} className="rounded-xl border border-orange-400/20 bg-orange-500/10 p-3 text-sm text-orange-100"><strong>{item.tipo}</strong> · {item.severidade}</div>)}
            {(metricas?.erros_recentes || []).slice(0, 5).map((item, index) => <div key={`${item.message_id}-${index}`} className="rounded-xl border border-red-400/20 bg-red-500/10 p-3 text-sm text-red-100">{(item.errors || []).join('; ') || 'Erro sem detalhe'}<p className="mt-1 text-xs text-red-200/70">{formatDate(item.created_at)}</p></div>)}
          </div>
        </div>
      </div>
    </Section>
  )
}

function IaAssistiva() {
  const [form, setForm] = useState({ tipo: 'chat', foco: 'operacional', pergunta: '', termo: '', empresa_nome: '', edital_texto: '' })
  const [result, setResult] = useState(null)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const { data: telemetria, refresh } = useAsyncData(api.iaAssistivaTelemetria)
  const { data: contexto, loading: contextoLoading, refresh: refreshContexto } = useAsyncData(() => Promise.all([
    api.consultorFullDashboard().catch((err) => ({ erro: err.message })),
    api.consultorFullLeads().catch((err) => ({ erro: err.message, itens: [] })),
    api.consultorFullFollowups().catch((err) => ({ erro: err.message, itens: [] })),
    api.documentalDashboard().catch((err) => ({ erro: err.message })),
    api.documentalDocumentos({ limit: 300 }).catch((err) => ({ erro: err.message, itens: [] })),
    api.dashboardOportunidades().catch((err) => ({ erro: err.message, itens: [], top_5: [] })),
    api.dashboardCasos().catch((err) => ({ erro: err.message })),
    api.concorrentesAnalise().catch((err) => ({ erro: err.message })),
    api.fornecedorFullDashboard().catch((err) => ({ erro: err.message })),
    api.fornecedorFullRegistros('', 300).catch((err) => ({ erro: err.message, itens: [] })),
    api.auditLogs(20).catch((err) => ({ erro: err.message, logs: [] })),
    api.dashboardMemorias().catch((err) => ({ erro: err.message, memorias: [], itens: [] })),
  ]).then(([consultor, leads, followups, documental, documentos, oportunidades, casos, concorrencia, contratos, fornecedorRegistros, audit, memorias]) => ({ consultor, leads, followups, documental, documentos, oportunidades, casos, concorrencia, contratos, fornecedorRegistros, audit, memorias })), [])

  const today = new Date()
  today.setHours(0, 0, 0, 0)
  const daysUntil = (value) => {
    if (!value) return null
    const date = new Date(value)
    if (Number.isNaN(date.getTime())) return null
    date.setHours(0, 0, 0, 0)
    return Math.ceil((date - today) / 86400000)
  }
  const norm = (value) => String(value || '').trim().toLowerCase()
  const prioridades = useMemo(() => {
    const leads = contexto?.leads?.itens || []
    const followups = contexto?.followups?.itens || []
    const docs = contexto?.documentos?.itens || []
    const oportunidades = contexto?.oportunidades?.itens || contexto?.oportunidades?.top_5 || []
    const itens = []
    followups.forEach((item) => {
      const prazo = daysUntil(item.data || item.follow_up_em || item.prazo)
      if (prazo !== null && prazo < 0) itens.push({ tipo: 'follow-up vencido', titulo: item.titulo || item.cliente_nome || item.empresa || 'Follow-up pendente', impacto: 'alto', urgencia: 95, fonte: 'Consultor Full / Follow-ups', confianca: 0.93, motivo: `${Math.abs(prazo)} dia(s) de atraso. Pode gerar perda de ritmo comercial ou falha de atendimento.`, acao: 'Retomar contato, registrar encaminhamento e definir nova data supervisionada.' })
    })
    leads.forEach((lead) => {
      const prazo = daysUntil(lead.follow_up_em)
      const risco = Number(lead.risco_churn || 0)
      if (prazo !== null && prazo < -7) itens.push({ tipo: 'cliente esquecido', titulo: lead.empresa || lead.nome || 'Cliente sem contato', impacto: 'alto', urgencia: 88, fonte: 'Consultor Full / Leads', confianca: 0.86, motivo: `Sem follow-up há mais de ${Math.abs(prazo)} dia(s).`, acao: 'Agendar contato de recuperação e atualizar etapa do fluxo.' })
      if (risco >= 60) itens.push({ tipo: 'risco churn', titulo: lead.empresa || lead.nome || 'Cliente em risco', impacto: risco >= 80 ? 'crítico' : 'alto', urgencia: Math.min(98, risco + 12), fonte: 'Consultor Full / Carteira', confianca: 0.84, motivo: `Risco churn informado em ${risco}/100.`, acao: 'Revisar valor entregue, pendências abertas e proposta de retenção.' })
    })
    docs.forEach((doc) => {
      const prazo = daysUntil(doc.validade)
      const risco = Number(doc.risco_documental || doc.score_risco || 0)
      if (norm(doc.status).includes('vencido') || (prazo !== null && prazo < 0)) itens.push({ tipo: 'risco documental', titulo: doc.titulo || 'Documento vencido', impacto: 'crítico', urgencia: 98, fonte: 'Documental 360°', confianca: 0.94, motivo: `Documento vencido${prazo !== null ? ` há ${Math.abs(prazo)} dia(s)` : ''}. Pode bloquear habilitação.`, acao: 'Regularizar antes de qualquer protocolo ou disputa.' })
      else if (prazo !== null && prazo <= 30) itens.push({ tipo: 'documento crítico', titulo: doc.titulo || 'Documento vencendo', impacto: 'alto', urgencia: 82, fonte: 'Documental 360°', confianca: 0.88, motivo: `Vence em ${prazo} dia(s).`, acao: 'Iniciar renovação e atualizar validade no repositório.' })
      else if (['alta', 'critica', 'crítica'].includes(norm(doc.criticidade)) || risco >= 60) itens.push({ tipo: 'documento crítico', titulo: doc.titulo || 'Documento crítico', impacto: 'alto', urgencia: 76, fonte: 'Documental 360°', confianca: 0.8, motivo: `Criticidade ${doc.criticidade || risco}.`, acao: 'Conferir aderência ao edital e anexos comprobatórios.' })
    })
    oportunidades.forEach((op) => {
      const prazo = daysUntil(op.data_abertura || op.data_limite || op.prazo || op.data_disputa)
      const alta = op.classificacao_triagem === 'prioridade_alta' || norm(op.prioridade).includes('alta') || (prazo !== null && prazo <= 3)
      if (alta) itens.push({ tipo: 'oportunidade urgente', titulo: op.orgao || op.titulo || op.objeto || 'Oportunidade prioritária', impacto: 'alto', urgencia: prazo !== null && prazo <= 1 ? 96 : 78, fonte: 'Radar / Oportunidades', confianca: 0.78, motivo: prazo !== null ? `Prazo em ${prazo} dia(s) ou classificação prioritária.` : 'Classificação operacional indica prioridade.', acao: 'Decidir participação, checar documentos e riscos concorrenciais.' })
    })
    return itens.sort((a, b) => b.urgencia - a.urgencia).slice(0, 12)
  }, [contexto])
  const gargalos = useMemo(() => {
    const d = contexto?.documental || {}
    const c = contexto?.consultor || {}
    const contratos = contexto?.contratos || {}
    const concorrencia = contexto?.concorrencia || {}
    return [
      { titulo: 'Documental', valor: (d.documentos_vencidos || 0) + (d.documentos_vencendo || 0), detalhe: 'vencidos ou vencendo', fonte: 'Documental 360°' },
      { titulo: 'Comercial', valor: (c.tarefas_pendentes || 0) + (c.clientes_risco || 0), detalhe: 'tarefas/clientes em risco', fonte: 'Consultor Full' },
      { titulo: 'Contratos', valor: (contratos.pagamentos_pendentes || 0) + (contratos.risco_contratual_medio >= 60 ? 1 : 0), detalhe: 'pendências financeiras/risco', fonte: 'Fornecedor Full' },
      { titulo: 'Concorrência', valor: concorrencia.total_eventos || concorrencia.total_concorrentes || 0, detalhe: 'sinais competitivos monitorados', fonte: 'Concorrentes' },
    ].filter((item) => item.valor)
  }, [contexto])
  const prioridadesCriticas = prioridades.filter((item) => item.impacto === 'crítico' || item.urgencia >= 90)
  const resumoHoje = prioridades.length
    ? `Hoje exige atenção em ${prioridades.length} ponto(s). Prioridade máxima: ${prioridades[0].titulo} (${prioridades[0].tipo}). Motivo: ${prioridades[0].motivo} Ação sugerida: ${prioridades[0].acao}`
    : 'Hoje não há prioridade crítica consolidada pelos módulos consultados. Manter rotina de monitoramento, follow-ups e revisão documental.'

  async function submit(e) {
    e.preventDefault(); setSaving(true); setError('')
    try {
      const contextoOperacional = {
        tela: form.foco,
        resumo_hoje: resumoHoje,
        prioridades: prioridades.slice(0, 8),
        gargalos,
        documentos_criticos: (contexto?.documentos?.itens || []).filter((doc) => norm(doc.status).includes('venc') || ['alta','critica','crítica'].includes(norm(doc.criticidade))).slice(0, 8),
        casos_criticos: (contexto?.casos?.itens || contexto?.casos?.casos || []).filter((caso) => Number(caso.score_estrategico || 0) >= 70 || caso.risco_concorrencial).slice(0, 8),
        riscos: [
          ...prioridades.filter((item) => item.impacto === 'crítico' || item.urgencia >= 90).slice(0, 8),
          ...((contexto?.fornecedorRegistros?.itens || []).filter((item) => norm(item.tipo) === 'risco' && !['concluido','arquivado'].some((status) => norm(item.status).includes(status))).slice(0, 8)),
        ],
        cliente_ativo: (contexto?.leads?.itens || []).find((lead) => form.empresa_nome && [lead.empresa, lead.nome].join(' ').toLowerCase().includes(norm(form.empresa_nome))) || null,
        fornecedor_ativo: (contexto?.fornecedorRegistros?.itens || []).find((item) => form.empresa_nome && [item.orgao, item.titulo, item.observacoes].join(' ').toLowerCase().includes(norm(form.empresa_nome))) || null,
        ids_reais: {
          leads: (contexto?.leads?.itens || []).slice(0, 12).map((item) => item.id).filter(Boolean),
          followups: (contexto?.followups?.itens || []).slice(0, 12).map((item) => item.id).filter(Boolean),
          documentos: (contexto?.documentos?.itens || []).slice(0, 12).map((item) => item.id).filter(Boolean),
          casos: (contexto?.casos?.itens || contexto?.casos?.casos || []).slice(0, 12).map((item) => item.id).filter(Boolean),
          fornecedor: (contexto?.fornecedorRegistros?.itens || []).slice(0, 12).map((item) => item.id).filter(Boolean),
        },
        timeline_recente: [
          ...((contexto?.audit?.logs || []).slice(0, 10)),
          ...((contexto?.followups?.itens || []).slice(0, 10).map((item) => ({ tipo: 'follow-up', id: item.id, titulo: item.titulo, data: item.data, status: item.status }))),
        ],
        followups_pendentes: (contexto?.followups?.itens || []).filter((item) => !['concluido','arquivado'].some((status) => norm(item.status).includes(status))).slice(0, 12),
        memorias_contextuais: (contexto?.memorias?.memorias || contexto?.memorias?.itens || contexto?.memorias?.recentes || []).slice(0, 8),
        cliente_ou_empresa: form.empresa_nome || form.termo,
        modo: 'contextual_supervisionado_sem_execucao_automatica',
      }
      setResult(await api.iaAssistivaResponder({ ...form, contexto_operacional: contextoOperacional })); refresh()
    } catch (err) { setError(err.message || 'Erro na IA assistiva') }
    finally { setSaving(false) }
  }
  async function feedback(kind) {
    if (!result) return
    try { await api.iaAssistivaFeedback({ resposta_id: result.id, feedback: kind }); refresh() } catch (err) { setError(err.message || 'Erro ao registrar feedback') }
  }
  function responderAtencaoHoje() {
    setResult({
      id: `local-${Date.now()}`,
      resposta: `O que exige atenção hoje?\n\n${resumoHoje}\n\nAções sugeridas supervisionadas:\n${prioridades.slice(0, 5).map((item, index) => `${index + 1}. ${item.acao} — ${item.titulo}`).join('\n') || '1. Revisar carteira, documentação e oportunidades prioritárias.'}\n\nNenhuma ação foi executada automaticamente.`,
      fontes: [{ modulo: 'prioridades_operacionais', total: prioridades.length }, { modulo: 'gargalos', total: gargalos.length }],
      confianca: prioridades.length ? Math.max(...prioridades.map((item) => item.confianca || 0.7)) : 0.72,
    })
  }

  return (
    <div className="space-y-6">
      <Section title="IA Assistiva Operacional — Fase 2" subtitle="Copiloto contextual supervisionado: prioriza, explica e recomenda sem autonomia e sem executar ações automaticamente." action={<button onClick={() => { refresh(); refreshContexto() }} className="rounded-xl bg-slate-800 px-4 py-2 text-sm font-bold text-white hover:bg-slate-700"><RefreshCcw size={15} className="mr-2 inline" />Atualizar contexto</button>}>
        <div className="mb-4 flex flex-wrap gap-2"><Badge value="supervisionada" /><Badge value="explicável" /><Badge value="auditável" /><Badge value="sem execução automática" /></div>
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
          <MetricCard label="Prioridades do dia" value={prioridades.length} tone={prioridades.length ? 'warning' : 'success'} />
          <MetricCard label="Críticas" value={prioridadesCriticas.length} tone={prioridadesCriticas.length ? 'danger' : 'success'} />
          <MetricCard label="Gargalos" value={gargalos.length} tone={gargalos.length ? 'warning' : 'success'} />
          <MetricCard label="Confiança média" value={`${Math.round((telemetria?.confianca_media || 0) * 100)}%`} />
          <MetricCard label="Sugestões aceitas" value={telemetria?.sugestoes_aceitas || 0} tone="success" />
        </div>
        <div className="mt-5 rounded-2xl border border-blue-400/20 bg-blue-500/10 p-4">
          <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
            <div><p className="text-xs font-black uppercase tracking-[0.18em] text-blue-200">Pergunta operacional</p><h3 className="mt-2 text-xl font-black text-white">O que exige atenção hoje?</h3><p className="mt-1 text-sm text-blue-100/80">Resposta baseada nos módulos consultados, com fonte, confiança e motivo.</p></div>
            <button onClick={responderAtencaoHoje} className="rounded-xl bg-blue-600 px-4 py-3 text-sm font-black text-white hover:bg-blue-500">Responder agora</button>
          </div>
        </div>
      </Section>

      <div className="grid gap-6 xl:grid-cols-[1.1fr_0.9fr]">
        <Section title="Prioridades do dia" subtitle="Clientes esquecidos, follow-ups vencidos, documentos críticos, churn, risco documental e oportunidades urgentes.">
          {contextoLoading ? <div className="flex items-center text-sm text-slate-400"><Loader2 className="mr-2 animate-spin" size={16} />Carregando contexto operacional...</div> : <div className="space-y-3">{prioridades.map((item) => <div key={`${item.tipo}-${item.titulo}-${item.urgencia}`} className={`rounded-2xl border p-4 ${item.impacto === 'crítico' ? 'border-red-400/25 bg-red-500/10' : 'border-orange-400/25 bg-orange-500/10'}`}><div className="flex flex-wrap gap-2"><Badge value={item.tipo} /><Badge value={`urgência ${item.urgencia}`} /><Badge value={`confiança ${Math.round((item.confianca || 0) * 100)}%`} /></div><h3 className="mt-3 font-black text-white">{item.titulo}</h3><p className="mt-2 text-sm text-slate-300"><strong>Motivo:</strong> {item.motivo}</p><p className="mt-1 text-sm text-slate-300"><strong>Ação sugerida:</strong> {item.acao}</p><p className="mt-2 text-xs text-slate-500">Fonte: {item.fonte} · sugestão supervisionada, sem execução automática.</p></div>)}{!prioridades.length && <Empty text="Nenhuma prioridade operacional crítica consolidada agora." />}</div>}
        </Section>

        <Section title="Riscos e gargalos" subtitle="Onde a operação pode travar se ninguém agir.">
          <div className="space-y-3">{gargalos.map((item) => <div key={item.titulo} className="rounded-2xl border border-slate-800 bg-slate-950/50 p-4"><div className="flex items-center justify-between gap-3"><div><p className="font-black text-white">{item.titulo}</p><p className="mt-1 text-sm text-slate-400">{item.detalhe}</p></div><span className="text-3xl font-black text-white">{item.valor}</span></div><p className="mt-2 text-xs text-slate-500">Fonte: {item.fonte}</p></div>)}{!gargalos.length && <Empty text="Sem gargalos relevantes nos dados carregados." />}</div>
        </Section>
      </div>

      <div className="grid gap-6 xl:grid-cols-2">
        <Section title="Consulta assistiva" subtitle="Peça resumo executivo de cliente, caso, concorrência, empresa ou contrato.">
          <form onSubmit={submit} className="space-y-3">
            <div className="grid gap-3 md:grid-cols-2"><label className="block"><span className="text-sm font-bold text-white">Tipo</span><select value={form.tipo} onChange={(e) => setForm({ ...form, tipo: e.target.value })} className="input mt-2"><option value="chat">chat</option><option value="resumo">resumo executivo</option><option value="explicacao">explicação</option><option value="sugestao">sugestão supervisionada</option></select></label><label className="block"><span className="text-sm font-bold text-white">Foco</span><select value={form.foco} onChange={(e) => setForm({ ...form, foco: e.target.value })} className="input mt-2">{['operacional','cliente','caso','concorrencial','empresa','contrato','documental','risco','pendencia','decisao','score','inaptidao_documental','proxima_acao','follow_up','regularizacao','prioridade','sugestao_operacional'].map((x) => <option key={x} value={x}>{x}</option>)}</select></label></div>
            <TextInput label="Termo/contexto" value={form.termo} onChange={(v) => setForm({ ...form, termo: v })} placeholder="cliente, caso, concorrente, empresa, contrato..." />
            <TextInput label="Empresa/cliente" value={form.empresa_nome} onChange={(v) => setForm({ ...form, empresa_nome: v })} placeholder="nome para dossiê/checklist" />
            <label className="block"><span className="text-sm font-bold text-white">Pergunta</span><textarea value={form.pergunta} onChange={(e) => setForm({ ...form, pergunta: e.target.value })} className="input mt-2 min-h-[90px]" placeholder="Ex.: O que exige atenção hoje? / Resuma o cliente X / Quais riscos deste contrato?" /></label>
            <label className="block"><span className="text-sm font-bold text-white">Texto do edital/checklist</span><textarea value={form.edital_texto} onChange={(e) => setForm({ ...form, edital_texto: e.target.value })} className="input mt-2 min-h-[90px]" placeholder="Opcional: cole trecho do edital para checklist documental." /></label>
            <button disabled={saving} className="rounded-2xl bg-blue-600 px-4 py-3 font-black text-white disabled:opacity-60">{saving ? 'Consultando contexto...' : 'Gerar assistência supervisionada'}</button>
          </form>
          {error && <div className="mt-4"><ErrorBox text={error} /></div>}
        </Section>
        <Section title="Resposta explicável" subtitle="Fonte, confiança e motivo da recomendação sempre visíveis.">
          {!result ? <Empty text="Gere uma resposta assistiva ou use “O que exige atenção hoje?”" /> : <div className="space-y-4"><div className="rounded-2xl border border-slate-800 bg-slate-950/70 p-4 whitespace-pre-wrap text-sm text-slate-200">{result.resposta}</div><div className="grid gap-3 md:grid-cols-3"><MetricCard label="Confiança" value={`${Math.round((result.confianca || prioridades[0]?.confianca || 0.72) * 100)}%`} /><MetricCard label="Fontes" value={(result.fontes || []).length} /><MetricCard label="Execução" value="manual" tone="success" /></div><div className="flex flex-wrap gap-2">{(result.fontes || []).map((f) => <Badge key={`${f.modulo}-${f.tipo || f.total}`} value={`${f.modulo}: ${f.total ?? ''}`} />)}</div>{!String(result.id || '').startsWith('local-') && <div className="flex flex-wrap gap-2"><button onClick={() => feedback('aceita')} className="rounded-xl bg-emerald-600 px-3 py-2 text-sm font-bold text-white">Sugestão aceita</button><button onClick={() => feedback('ignorada')} className="rounded-xl bg-slate-700 px-3 py-2 text-sm font-bold text-white">Ignorada</button><button onClick={() => feedback('util')} className="rounded-xl bg-blue-600 px-3 py-2 text-sm font-bold text-white">Útil</button><button onClick={() => feedback('insuficiente')} className="rounded-xl bg-orange-600 px-3 py-2 text-sm font-bold text-white">Insuficiente</button></div>}</div>}
        </Section>
      </div>
    </div>
  )
}

function TelemetryList({ title, items }) {
  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-950/50 p-4">
      <h3 className="font-black text-white">{title}</h3>
      <div className="mt-3 space-y-2">
        {!items.length ? <Empty text="Sem dados ainda." /> : items.map((item) => <div key={item.valor} className="flex items-center justify-between rounded-xl bg-slate-900/70 px-3 py-2 text-sm"><span className="max-w-[70%] truncate text-slate-300">{item.valor}</span><span className="font-black text-white">{item.total}</span></div>)}
      </div>
    </div>
  )
}

function UserChatBubble({ msg }) {
  return (
    <div className="flex justify-end">
      <div className="max-w-3xl rounded-2xl bg-blue-600 px-4 py-3 text-sm text-white shadow-lg shadow-blue-950/30">
        {msg.texto}
      </div>
    </div>
  )
}

function LiciChatBubble({ msg }) {
  return (
    <div className="max-w-4xl rounded-2xl border border-slate-800 bg-slate-900/80 p-4 text-sm text-slate-200">
      <div className="mb-2 flex flex-wrap items-center gap-2"><Badge value={msg.intencao} /><Badge value={msg.encontrou_dados ? 'dados encontrados' : 'sem dados'} /></div>
      <div className="whitespace-pre-wrap leading-6">{msg.resposta}</div>
      <div className="mt-4 rounded-xl border border-slate-800 bg-slate-950/70 p-3">
        <p className="text-xs font-black uppercase tracking-wide text-slate-500">Fontes internas consultadas</p>
        <div className="mt-2 flex flex-wrap gap-2">
          {(msg.fontes || []).map((fonte, index) => <Badge key={`${fonte.modulo}-${index}`} value={`${fonte.modulo}: ${fonte.total ?? 0}${fonte.status === 'erro' ? ' erro' : ''}`} />)}
          {!msg.fontes?.length && <span className="text-xs text-slate-500">Nenhuma fonte registrada.</span>}
        </div>
      </div>
    </div>
  )
}

function Dashboard({ profile, onNavigate }) {
  const { data, loading, error, refresh } = useAsyncData(loadDashboardCommandCenter)
  const resumo = data?.resumo || {}
  const totals = resumo?.totais || {}
  const kpis = data?.kpis || {}
  const alertas = data?.alertas?.alertas || []
  const oportunidades = data?.oportunidades || {}
  const casos = data?.casos || {}
  const auditLogs = data?.audit?.logs || []
  const gerados = data?.gerados?.documentos || []
  const alertasNaoLidos = alertas.filter((alerta) => !alerta.lido)
  const prioridadeAlta = (oportunidades.itens || []).filter((item) => item.classificacao_triagem === 'prioridade_alta')
  const casosPendentes = casos.com_acao_pendente || resumo.casos_com_acao_pendente || []
  const riscoConcorrencial = resumo.risco_concorrencial || []
  const topOportunidades = oportunidades.top_5 || resumo.top_5_oportunidades || []

  return (
    <StateGate loading={loading} error={error} onRetry={refresh}>
      <div className="space-y-6">
        
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <KpiCard title="Oportunidades prioritárias" value={prioridadeAlta.length} icon={Target} hint="Itens que merecem decisão hoje" />
          <KpiCard title="Casos com ação" value={kpis.casos_com_acao_pendente_total ?? casosPendentes.length} icon={BriefcaseBusiness} hint="Pendências abertas" />
          <KpiCard title="Alertas críticos" value={kpis.alertas_criticos_abertos ?? resumo.alertas_por_severidade?.critica ?? 0} icon={AlertTriangle} hint={`${kpis.alertas_nao_lidos ?? totals.alertas_nao_lidos ?? 0} não lidos`} />
          <KpiCard title="Risco concorrencial" value={kpis.casos_com_risco_concorrencial_total ?? totals.casos_com_risco_concorrencial ?? 0} icon={UserCircle} hint="Casos que exigem atenção" />
        </div>

        <Section title="Operação rápida" subtitle="Atalhos para abrir cadastros reais, editar dados e acompanhar persistência operacional.">
          <div className="crud-action-bar">
            <span className="crud-action-label">Ações</span>
            <button onClick={() => onNavigate?.('casos')} className="crud-button-primary"><BriefcaseBusiness size={14} className="mr-1.5" />Criar/editar casos</button>
            <button onClick={() => onNavigate?.('documental')} className="crud-button-primary"><FileText size={14} className="mr-1.5" />Editar documentos</button>
            <button onClick={() => onNavigate?.('concorrentes')} className="crud-button"><UserCircle size={14} className="mr-1.5" />Concorrentes</button>
            <button onClick={() => onNavigate?.('orgaos')} className="crud-button"><Database size={14} className="mr-1.5" />Órgãos</button>
            <button onClick={() => onNavigate?.('contratos')} className="crud-button"><CheckCircle2 size={14} className="mr-1.5" />Contratos/financeiro</button>
          </div>
        </Section>

        <Section title="Pulso da operação" subtitle="Somente os indicadores necessários para priorizar o dia.">
          <div className="grid gap-4 xl:grid-cols-2">
            <MiniBarChart title="Casos por fase" data={resumo.casos_por_fase || casos.por_fase || {}} />
            <MiniBarChart title="Alertas por severidade" data={resumo.alertas_por_severidade || data?.alertas?.por_severidade || {}} />
          </div>
        </Section>

        <div className="grid gap-6 xl:grid-cols-2">
          <Section title="Prioridade agora" subtitle="O que precisa de decisão ou ação imediata">
            <RecommendedActions alertas={alertasNaoLidos} oportunidades={prioridadeAlta} casos={casosPendentes} riscosConcorrenciais={riscoConcorrencial} />
          </Section>
          <Section title="Movimentos recentes" subtitle="Últimas mudanças relevantes.">
            <AuditActivityList items={auditLogs} />
          </Section>
        </div>

        <Section title="Oportunidades em foco" subtitle="Onde agir primeiro e qual movimento executar.">
          <TopOpportunityCommandList items={topOportunidades} />
        </Section>
      </div>
    </StateGate>
  )
}

function OrganizationOverview({ organizacao, onChanged }) {
  const orgs = organizacao?.disponiveis || []
  const ativa = organizacao?.ativa || 'default-org'
  async function trocar(e) {
    const organizationId = e.target.value
    api.setActiveOrganization(organizationId)
    await api.trocarOrganizacao(organizationId).catch(() => null)
    onChanged?.()
  }
  return (
    <div className="card flex flex-wrap items-center justify-between gap-4 p-5">
      <div>
        <div className="text-xs font-bold uppercase tracking-[0.2em] text-cyan-300">Organização ativa</div>
        <h2 className="mt-1 text-xl font-black text-white">{ativa}</h2>
        <p className="mt-1 text-sm text-slate-400">Papel: {organizacao?.role || 'não informado'} · usuários ativos: {organizacao?.usuarios_ativos ?? 0}</p>
      </div>
      <select className="rounded-xl border border-white/10 bg-slate-950 px-3 py-2 text-sm text-white" value={ativa} onChange={trocar}>
        {(orgs.length ? orgs : [{ id: ativa, nome: ativa }]).map((org) => (
          <option key={org.id || org.organization_id || org.nome} value={org.id || org.organization_id || org.nome}>{org.nome || org.name || org.id || org.organization_id}</option>
        ))}
      </select>
    </div>
  )
}

function ProfileOverview({ profile }) {
  return (
    <div className="grid gap-4 xl:grid-cols-[1.2fr_1fr]">
      <div className="card p-5">
        <div className="flex flex-wrap items-center gap-2">
          <Badge value={profile.id} />
          <span className="text-xs text-slate-500">perfil operacional ativo</span>
        </div>
        <h2 className="mt-3 text-xl font-black text-white">{profile.nome}</h2>
        <p className="mt-2 text-sm leading-6 text-slate-300">{profile.linguagem_recomendada}</p>
      </div>
      <div className="card p-5">
        <h3 className="font-black text-white">Prioridades do perfil</h3>
        <div className="mt-3 flex flex-wrap gap-2">
          {(profile.prioridades || []).slice(0, 10).map((item) => <Badge key={item} value={item} />)}
        </div>
      </div>
    </div>
  )
}

function FirstStepsGuide({ profile, onNavigate }) {
  const [open, setOpen] = useState(() => localStorage.getItem('lici.first_steps.closed') !== '1')
  const perfil = profile?.perfil_atual || 'fornecedor'
  const steps = perfil === 'consultor'
    ? [
        { title: '1. Cadastre ou revise um lead', detail: 'Abra o CRM, registre empresa, etapa, potencial e próximo follow-up.', target: 'crm', icon: UserCircle },
        { title: '2. Transforme demanda em operação', detail: 'Use Operação para criar tarefas, agenda e controles financeiros do cliente.', target: 'operacao', icon: CheckCircle2 },
        { title: '3. Blindagem documental', detail: 'No Documental, acompanhe certidões, vencimentos e dossiês por cliente.', target: 'documental', icon: FileText },
      ]
    : [
        { title: '1. Comece por uma oportunidade', detail: 'Avalie objeto, prazo, score e risco. Se fizer sentido, crie um caso.', target: 'oportunidades', icon: Target },
        { title: '2. Gerencie o caso', detail: 'Defina fase, risco de habilitação, próximos eventos e estratégia de disputa.', target: 'casos', icon: BriefcaseBusiness },
        { title: '3. Prepare documentos e concorrentes', detail: 'Cheque certidões no Documental e registre padrões de concorrentes/órgãos.', target: 'documental', icon: FileText },
      ]
  function close() {
    localStorage.setItem('lici.first_steps.closed', '1')
    setOpen(false)
  }
  if (!open) {
    return <button onClick={() => setOpen(true)} className="rounded-2xl border border-blue-400/25 bg-blue-500/10 px-4 py-3 text-sm font-black text-blue-100 hover:bg-blue-500/20"><BookOpen size={16} className="mr-2 inline" />Mostrar primeiros passos</button>
  }
  return (
    <Section title="Primeiros passos no LICI" subtitle="Guia rápido para transformar o painel em ação prática. Faça nessa ordem se estiver em dúvida." action={<button onClick={close} className="rounded-xl bg-slate-800 px-3 py-2 text-xs font-black text-slate-200 hover:bg-slate-700">Ocultar guia</button>}>
      <div className="grid gap-4 xl:grid-cols-3">
        {steps.map((step) => {
          const Icon = step.icon
          return (
            <button key={step.title} onClick={() => onNavigate?.(step.target)} className="rounded-2xl border border-blue-400/20 bg-blue-500/10 p-5 text-left transition hover:border-blue-300/50 hover:bg-blue-500/15">
              <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-blue-500/20 text-blue-100 ring-1 ring-blue-300/30"><Icon size={20} /></div>
              <h3 className="mt-4 font-black text-white">{step.title}</h3>
              <p className="mt-2 text-sm leading-6 text-blue-100/80">{step.detail}</p>
              <p className="mt-4 text-xs font-black uppercase tracking-wide text-blue-200">Abrir módulo →</p>
            </button>
          )
        })}
      </div>
      <div className="mt-4 rounded-2xl border border-emerald-400/20 bg-emerald-500/10 p-4 text-sm leading-6 text-emerald-50/90">
        <strong>Como saber se salvou?</strong> Agora toda criação, edição ou arquivamento mostra uma confirmação no canto superior. Arquivar é baixa lógica: o registro fica preservado para histórico e auditoria.
      </div>
    </Section>
  )
}

function GuidedWorkflow({ profile, onNavigate }) {
  const fornecedor = (profile?.perfil_atual || 'fornecedor') !== 'consultor'
  const workflow = fornecedor
    ? [
        { title: 'Radar', detail: 'Encontrar oportunidade com aderência, prazo viável e risco controlável.', target: 'oportunidades', icon: Target, tone: 'blue' },
        { title: 'Caso vivo', detail: 'Converter em caso, definir fase, decisão go/no-go, riscos e próximo movimento.', target: 'casos', icon: BriefcaseBusiness, tone: 'emerald' },
        { title: 'Habilitação', detail: 'Checar certidões, atestados, validade e dossiê antes da disputa.', target: 'documental', icon: FileText, tone: 'cyan' },
        { title: 'Inteligência', detail: 'Mapear órgão e concorrentes para recurso, diligência e vantagem competitiva.', target: 'concorrentes', icon: UserCircle, tone: 'purple' },
        { title: 'Execução', detail: 'Acompanhar contrato, medição, cobrança, risco de sanção e pagamento.', target: 'contratos', icon: CheckCircle2, tone: 'orange' },
      ]
    : [
        { title: 'Lead', detail: 'Registrar oportunidade comercial, origem, potencial e etapa do funil.', target: 'crm', icon: UserCircle, tone: 'blue' },
        { title: 'Diagnóstico', detail: 'Mapear dor, carteira, portais, documentos e maturidade licitatória.', target: 'pipeline', icon: BarChart3, tone: 'emerald' },
        { title: 'Operação', detail: 'Transformar demanda em tarefa, responsável, prazo e entregável.', target: 'operacao', icon: CheckCircle2, tone: 'cyan' },
        { title: 'Documental', detail: 'Manter dossiê do cliente pronto para habilitação e propostas.', target: 'documental', icon: FileText, tone: 'purple' },
        { title: 'Recorrência', detail: 'Acompanhar follow-ups, financeiro, retenção e próximos editais.', target: 'financeiro', icon: Database, tone: 'orange' },
      ]
  const toneMap = {
    blue: 'border-blue-400/25 bg-blue-500/10 text-blue-100',
    emerald: 'border-emerald-400/25 bg-emerald-500/10 text-emerald-100',
    cyan: 'border-cyan-400/25 bg-cyan-500/10 text-cyan-100',
    purple: 'border-purple-400/25 bg-purple-500/10 text-purple-100',
    orange: 'border-orange-400/25 bg-orange-500/10 text-orange-100',
  }
  return (
    <Section title="Fluxo operacional recomendado" subtitle="Um mapa simples para o usuário saber onde começar, para onde ir e por que cada módulo existe.">
      <div className="grid gap-3 xl:grid-cols-5">
        {workflow.map((step, index) => {
          const Icon = step.icon
          return (
            <button key={step.title} onClick={() => onNavigate?.(step.target)} className={`relative rounded-2xl border p-4 text-left transition hover:-translate-y-0.5 hover:shadow-xl ${toneMap[step.tone]}`}>
              <div className="flex items-center justify-between gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-white/10 ring-1 ring-white/15"><Icon size={19} /></div>
                <span className="text-xs font-black uppercase tracking-wide opacity-70">Etapa {index + 1}</span>
              </div>
              <h3 className="mt-4 font-black text-white">{step.title}</h3>
              <p className="mt-2 text-sm leading-6 opacity-85">{step.detail}</p>
              <p className="mt-4 text-xs font-black uppercase tracking-wide opacity-80">Abrir →</p>
            </button>
          )
        })}
      </div>
      <div className="mt-4 grid gap-3 md:grid-cols-3">
        <div className="rounded-2xl border border-white/10 bg-slate-950/55 p-4"><p className="text-xs font-black uppercase tracking-wide text-slate-500">Regra de uso</p><p className="mt-2 text-sm text-slate-300">Todo cadastro deve levar a uma decisão, próximo passo ou memória. Cadastro sem ação vira ruído.</p></div>
        <div className="rounded-2xl border border-white/10 bg-slate-950/55 p-4"><p className="text-xs font-black uppercase tracking-wide text-slate-500">Confiança</p><p className="mt-2 text-sm text-slate-300">Criação, edição e arquivamento agora geram confirmação visual. Se der erro, a tela mostra o motivo.</p></div>
        <div className="rounded-2xl border border-white/10 bg-slate-950/55 p-4"><p className="text-xs font-black uppercase tracking-wide text-slate-500">Aprendizado</p><p className="mt-2 text-sm text-slate-300">Vitórias, perdas, padrões e riscos devem virar memória para melhorar decisões futuras.</p></div>
      </div>
    </Section>
  )
}

async function loadDashboardCommandCenter() {
  const [resumo, kpis, alertas, audit, oportunidades, casos, gerados] = await Promise.all([
    api.dashboardResumo(),
    api.dashboardKpis(),
    api.alertas(),
    api.auditLogs(8),
    api.dashboardOportunidades(),
    api.dashboardCasos(),
    api.documentosGerados(),
  ])
  return { resumo, kpis, alertas, audit, oportunidades, casos, gerados }
}

function RecommendedActions({ alertas, oportunidades, casos, riscosConcorrenciais = [] }) {
  const items = [
    ...alertas.slice(0, 3).map((alerta) => ({
      id: `alerta-${alerta.id}`,
      type: 'Alerta não lido',
      title: alerta.titulo,
      detail: alerta.acao_recomendada || alerta.mensagem,
      badge: alerta.severidade,
    })),
    ...oportunidades.slice(0, 3).map((item) => ({
      id: `oportunidade-${item.id}`,
      type: 'Prioridade alta',
      title: item.orgao || 'Órgão não informado',
      detail: item.objeto,
      badge: `score ${item.score_preliminar}`,
    })),
    ...casos.slice(0, 3).map((caso) => ({
      id: `caso-${caso.id}`,
      type: 'Caso pendente',
      title: caso.orgao || 'Órgão não informado',
      detail: caso.acao_recomendada || caso.objeto,
      badge: caso.fase_atual,
    })),
    ...riscosConcorrenciais.slice(0, 3).map((item) => ({
      id: `concorrencial-${item.id}`,
      type: 'Risco concorrencial',
      title: item.orgao || 'Órgão não informado',
      detail: item.acao_recomendada || `${item.concorrentes_relevantes?.length || 0} concorrente(s) relacionado(s)`,
      badge: `risco ${item.risco_concorrencial_score}`,
    })),
  ]
  if (!items.length) return <Empty text="Nenhuma ação crítica pendente agora." />
  return (
    <div className="space-y-3">
      {items.slice(0, 5).map((item) => (
        <div key={item.id} className="rounded-xl border border-slate-800 bg-slate-950/50 p-4">
          <div className="flex flex-wrap items-center gap-2">
            <Badge value={item.type} />
            <span className="text-xs text-slate-500">{item.badge}</span>
          </div>
          <p className="mt-2 font-bold text-white">{item.title}</p>
          <p className="mt-1 line-clamp-2 text-sm text-slate-400">{item.detail}</p>
        </div>
      ))}
    </div>
  )
}

function AuditActivityList({ items }) {
  if (!items.length) return <Empty text="Nenhuma atividade recente registrada." />
  return (
    <div className="space-y-3">
      {items.slice(0, 5).map((item) => (
        <div key={item.id} className="rounded-xl border border-slate-800 bg-slate-950/50 p-4">
          <div className="flex flex-wrap items-center gap-2">
            <Badge value={item.modulo} />
            <Badge value={item.status} />
            <span className="text-xs text-slate-500">{formatDate(item.timestamp)}</span>
          </div>
          <p className="mt-2 font-bold text-white">{humanizeAction(item.acao)}</p>
          <p className="mt-1 line-clamp-2 text-xs text-slate-500">{activityDetail(item)}</p>
        </div>
      ))}
    </div>
  )
}

function TopOpportunityCommandList({ items }) {
  if (!items.length) return <Empty text="Nenhuma oportunidade encontrada." />
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[860px] text-left text-sm">
        <thead className="text-xs uppercase text-slate-500">
          <tr>
            <th className="px-3 py-3">Score</th>
            <th className="px-3 py-3">Órgão</th>
            <th className="px-3 py-3">Objeto</th>
            <th className="px-3 py-3">Ação recomendada</th>
          </tr>
        </thead>
        <tbody>
          {items.map((item) => (
            <tr key={item.id} className="table-row text-slate-300">
              <td className="px-3 py-4"><span className="badge bg-blue-500/15 text-blue-200 ring-1 ring-blue-400/30">{item.score_preliminar}</span></td>
              <td className="px-3 py-4 font-semibold text-white">{item.orgao || 'Órgão não informado'}</td>
              <td className="max-w-xl px-3 py-4"><p className="line-clamp-2">{item.objeto}</p></td>
              <td className="px-3 py-4 text-slate-300">{recommendedOpportunityAction(item)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function DeadlineList({ items }) {
  if (!items.length) return <Empty text="Sem prazos próximos registrados." />
  return (
    <div className="space-y-3">
      {items.map((item) => (
        <div key={`${item.oportunidade_id}-${item.data_encerramento}`} className="flex gap-3 rounded-xl border border-slate-800 bg-slate-950/50 p-4">
          <Clock className="mt-1 shrink-0 text-yellow-200" size={18} />
          <div className="min-w-0">
            <p className="font-bold text-white">{item.orgao}</p>
            <p className="mt-1 text-sm text-slate-400">{item.dias_ate_encerramento} dias — {item.data_encerramento}</p>
          </div>
        </div>
      ))}
    </div>
  )
}

function Oportunidades() {
  const { data, loading, error, refresh } = useAsyncData(api.dashboardOportunidades)
  const [filters, setFilters] = useState({ orgao: '', uf: '', status: '', score: '', perfil: '' })
  const [savingId, setSavingId] = useState('')
  const [actionError, setActionError] = useState('')
  const itens = filterOperationalItems(data?.itens || [], filters, 'oportunidade')
  async function createCaseFromOpportunity(item) {
    setSavingId(item.id); setActionError('')
    try {
      await api.criarCaso({
        cliente: 'A definir',
        orgao: item.orgao || 'Órgão não informado',
        objeto: item.objeto || item.titulo || 'Oportunidade sem objeto',
        modalidade: item.modalidade || '',
        status: 'ativo',
        fase_atual: 'análise',
        score_estrategico: Number(item.score_preliminar || 50),
        riscos: [],
        oportunidades: [recommendedOpportunityAction(item)],
        contexto: `Caso criado a partir do Radar. Oportunidade: ${item.id || 'sem id'} · prazo: ${item.data_encerramento || item.data_abertura || 'não informado'}`,
      })
      refresh()
    } catch (err) { setActionError(err.message || 'Erro ao criar caso a partir da oportunidade') }
    finally { setSavingId('') }
  }
  return (
    <StateGate loading={loading} error={error} onRetry={refresh}>
      <div className="space-y-4">
        {actionError && <ErrorBox text={actionError} />}
        <OperationalFilters filters={filters} onChange={setFilters} options={{ status: ['capturada', 'monitorando', 'descartado', 'caso_criado'] }} />
        <Section title="Oportunidades do Radar" subtitle={`${itens.length} de ${data?.total || 0} oportunidades | score médio ${data?.score_medio || 0}`}>
        <div className="overflow-x-auto mobile-scroll">
          <table className="w-full min-w-[900px] text-left text-sm">
            <thead className="text-xs uppercase text-slate-500">
              <tr>
                <th className="px-3 py-3">Score</th>
                <th className="px-3 py-3">Órgão</th>
                <th className="px-3 py-3">Objeto</th>
                <th className="px-3 py-3">UF</th>
                <th className="px-3 py-3">Valor</th>
                <th className="px-3 py-3">Triagem</th>
                <th className="px-3 py-3">Prazo</th>
                <th className="sticky-actions px-3 py-3">Ações</th>
              </tr>
            </thead>
            <tbody>
              {itens.map((item) => (
                <tr key={item.id} className="table-row text-slate-300">
                  <td className="px-3 py-4 font-black text-white">{item.score_preliminar}</td>
                  <td className="px-3 py-4 font-semibold text-white">{item.orgao}</td>
                  <td className="max-w-xl px-3 py-4"><p className="line-clamp-2">{item.objeto}</p></td>
                  <td className="px-3 py-4">{item.uf}</td>
                  <td className="px-3 py-4">{formatMoney(item.valor_estimado)}</td>
                  <td className="px-3 py-4"><Badge value={item.classificacao_triagem || 'sem triagem'} map={triageStyle} /></td>
                  <td className="px-3 py-4">{formatDate(item.data_encerramento)}</td>
                  <td className="sticky-actions px-3 py-4"><div className="crud-action-bar"><span className="crud-action-label">Ação</span><button onClick={() => createCaseFromOpportunity(item)} disabled={savingId === item.id} className="crud-button-primary">{savingId === item.id ? 'Criando...' : 'Criar caso'}</button></div></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        </Section>
      </div>
    </StateGate>
  )
}

function Casos() {
  const emptyForm = {
    cliente: '', orgao: '', objeto: '', modalidade: '', status: 'ativo', fase_atual: 'prospecção',
    score_estrategico: 50, riscos: '', oportunidades: '', contexto: '', texto_edital: '',
  }
  const emptyEvent = { tipo: 'edital analisado', descricao: '', impacto: '', aprendizado_operacional: '', gerar_memoria_sugerida: true }
  const { data, loading, error, refresh } = useAsyncData(() => Promise.all([
    api.casos(),
    api.dashboardCasos(),
    api.documentalDocumentos({ limit: 300 }).catch((err) => ({ erro: err.message, itens: [] })),
    api.dashboardMemorias().catch((err) => ({ erro: err.message, memorias: [], itens: [] })),
    api.concorrentesAnalise().catch((err) => ({ erro: err.message })),
  ]).then(([lista, dashboard, documentos, memorias, concorrencia]) => ({ lista, dashboard, documentos, memorias, concorrencia })), [])
  const [exportError, setExportError] = useState('')
  const [actionError, setActionError] = useState('')
  const [filters, setFilters] = useState({ orgao: '', uf: '', status: '', score: '', perfil: '', fase: '', termo: '' })
  const [selected, setSelected] = useState(null)
  const [editing, setEditing] = useState(null)
  const [form, setForm] = useState(emptyForm)
  const [eventForm, setEventForm] = useState(emptyEvent)
  const [timelineCase, setTimelineCase] = useState(null)
  const [timeline, setTimeline] = useState(null)
  const [timelineError, setTimelineError] = useState('')
  const [saving, setSaving] = useState(false)

  const casos = data?.lista?.casos || data?.dashboard?.itens || []
  const dashboard = data?.dashboard || {}
  const documentosCaso = data?.documentos?.itens || []
  const memoriasCaso = data?.memorias?.memorias || data?.memorias?.itens || data?.memorias?.recentes || []
  const concorrenciaCaso = data?.concorrencia || {}
  const casosFiltrados = filterOperationalItems(casos, filters, 'caso').filter((caso) => {
    if (filters.fase && caso.fase_atual !== filters.fase) return false
    const q = (filters.termo || '').toLowerCase()
    if (!q) return true
    return [caso.cliente, caso.orgao, caso.objeto, caso.modalidade, caso.contexto, ...(caso.riscos || []), ...(caso.oportunidades || [])].join(' ').toLowerCase().includes(q)
  })
  const ativos = casos.filter((caso) => ['ativo', 'suspenso'].includes(caso.status)).length
  const arquivados = casos.filter((caso) => caso.status === 'arquivado').length
  const pendentes = dashboard.com_acao_pendente || casos.filter((caso) => ['prospecção', 'análise', 'impugnação', 'habilitação', 'disputa', 'recurso', 'pagamento'].includes(caso.fase_atual))
  const normCaso = (value) => String(value || '').trim().toLowerCase()
  const contextualTerms = (caso) => [caso?.cliente, caso?.orgao, caso?.objeto, caso?.modalidade].filter(Boolean).map(normCaso)
  const relatedDocsForCase = (caso) => {
    const terms = contextualTerms(caso)
    return documentosCaso.filter((doc) => terms.some((term) => term && [doc.empresa_nome, doc.cliente_nome, doc.orgao_emissor, doc.titulo, doc.observacoes, doc.tags].join(' ').toLowerCase().includes(term))).slice(0, 6)
  }
  const relatedMemoriesForCase = (caso) => {
    const terms = contextualTerms(caso)
    return memoriasCaso.filter((mem) => terms.some((term) => term && [mem.titulo, mem.conteudo, mem.resumo, mem.orgao, mem.concorrente, mem.tags].join(' ').toLowerCase().includes(term))).slice(0, 5)
  }
  const caseContextSnapshot = (caso) => {
    const docs = relatedDocsForCase(caso)
    const mems = relatedMemoriesForCase(caso)
    const riscos = caso?.riscos || []
    const score = Number(caso?.score_estrategico || 0)
    const docCritico = docs.find((doc) => ['vencido','pendente','inválido'].some((status) => normCaso(doc.status).includes(status)) || ['alta','critica','crítica'].includes(normCaso(doc.criticidade)))
    const historico = caso?.historico_operacional || caso?.timeline || []
    const ultimoEvento = [...historico].sort((a, b) => new Date(b.data || 0) - new Date(a.data || 0))[0]
    const bloqueador = docCritico ? `Documento: ${docCritico.titulo}` : riscos[0] || (score < 50 ? 'Score estratégico baixo' : 'Sem bloqueador crítico explícito')
    return {
      docs,
      mems,
      bloqueador,
      docCritico,
      ultimoEvento,
      checklistPendente: docCritico ? `Regularizar ${docCritico.titulo}` : (docs.length ? 'Conferir aderência documental antes da próxima fase' : 'Gerar checklist documental do edital'),
      responsavel: caso?.responsavel || caso?.usuario_responsavel || 'definir responsável',
      prazo: caso?.prazo_critico || caso?.data_disputa || caso?.data_abertura || caso?.prazo || 'prazo não informado',
      concorrente: caso?.concorrente_relevante || caso?.concorrente || (concorrenciaCaso?.ranking?.[0]?.nome || concorrenciaCaso?.concorrentes_criticos?.[0]?.nome || 'mapear concorrente'),
      orgao: caso?.orgao || 'órgão não informado',
      peca: caso?.peca_pendente || (['impugnação','recurso'].includes(caso?.fase_atual) ? `Preparar ${caso.fase_atual}` : 'sem peça pendente explícita'),
      recomendacao: nextCaseAction(caso),
    }
  }

  function payloadFromForm(includeText = false) {
    const payload = {
      cliente: form.cliente.trim(),
      orgao: form.orgao.trim(),
      objeto: form.objeto.trim(),
      modalidade: form.modalidade.trim(),
      status: form.status,
      fase_atual: form.fase_atual,
      score_estrategico: Number(form.score_estrategico || 50),
      riscos: splitLines(form.riscos),
      oportunidades: splitLines(form.oportunidades),
      contexto: form.contexto.trim(),
    }
    if (includeText && form.texto_edital.trim()) payload.texto_edital = form.texto_edital.trim()
    return payload
  }

  async function saveCase(event) {
    event.preventDefault()
    setSaving(true); setActionError('')
    try {
      if (editing?.id) await api.atualizarCaso(editing.id, payloadFromForm(false))
      else await api.criarCaso(payloadFromForm(true))
      setForm(emptyForm); setEditing(null); refresh()
    } catch (err) { setActionError(err.message || 'Erro ao salvar caso') }
    finally { setSaving(false) }
  }

  function editCase(caso) {
    setEditing(caso); setSelected(caso)
    setForm({
      cliente: caso.cliente || '', orgao: caso.orgao || '', objeto: caso.objeto || '', modalidade: caso.modalidade || '',
      status: caso.status || 'ativo', fase_atual: caso.fase_atual || 'prospecção', score_estrategico: caso.score_estrategico ?? 50,
      riscos: (caso.riscos || []).join('\n'), oportunidades: (caso.oportunidades || []).join('\n'), contexto: caso.contexto || '', texto_edital: '',
    })
    window.setTimeout(() => document.getElementById('case-editor')?.scrollIntoView({ behavior: 'smooth', block: 'start' }), 60)
  }

  async function quickPatchCase(caso, patch) {
    setSaving(true); setActionError('')
    try {
      await api.atualizarCaso(caso.id, {
        cliente: caso.cliente || '',
        orgao: caso.orgao || '',
        objeto: caso.objeto || '',
        modalidade: caso.modalidade || '',
        status: caso.status || 'ativo',
        fase_atual: caso.fase_atual || 'prospecção',
        score_estrategico: Number(caso.score_estrategico ?? 50),
        riscos: caso.riscos || [],
        oportunidades: caso.oportunidades || [],
        contexto: caso.contexto || '',
        ...patch,
      })
      setSelected((current) => current?.id === caso.id ? { ...current, ...patch } : current)
      refresh()
    } catch (err) { setActionError(err.message || 'Erro ao atualizar caso') }
    finally { setSaving(false) }
  }

  async function archiveCase(caso) {
    if (!window.confirm(`Arquivar o caso de ${caso.orgao || 'órgão não informado'}?`)) return
    setSaving(true); setActionError('')
    try { await api.arquivarCaso(caso.id); if (selected?.id === caso.id) setSelected(null); refresh() }
    catch (err) { setActionError(err.message || 'Erro ao arquivar caso') }
    finally { setSaving(false) }
  }

  async function updatePhase(caso, fase) {
    if (fase === caso.fase_atual) return
    setSaving(true); setActionError('')
    try {
      const ctx = caseContextSnapshot(caso)
      const descricao = [
        `Fase atualizada na mesa operacional: ${caso.fase_atual} → ${fase}.`,
        `Motivo: ${ctx.recomendacao || nextCaseAction(caso)}.`,
        `Impacto: mudança de fase altera prioridade operacional, checklist e peça pendente.`,
        `Responsável: ${ctx.responsavel}.`,
        `Bloqueador: ${ctx.bloqueador}.`,
        `Consequência operacional: se não houver próxima ação, o caso pode perder prazo, habilitação ou vantagem competitiva.`,
        `Próxima ação: ${ctx.recomendacao}.`,
      ].join(' ')
      await api.atualizarFaseCaso(caso.id, { fase_atual: fase, status: fase === 'encerrado' ? 'encerrado' : caso.status, descricao, aprendizado_operacional: `Contexto persistente de fase: ${caso.fase_atual} → ${fase}; prazo ${ctx.prazo}; documento crítico ${ctx.docCritico?.titulo || 'não identificado'}; órgão ${ctx.orgao}; concorrente ${ctx.concorrente}.` })
      refresh()
    } catch (err) { setActionError(err.message || 'Erro ao atualizar fase') }
    finally { setSaving(false) }
  }

  async function registerEvent(event) {
    event.preventDefault()
    if (!selected?.id) return
    setSaving(true); setActionError('')
    try {
      const ctx = caseContextSnapshot(selected)
      const payload = {
        ...eventForm,
        descricao: [
          eventForm.descricao,
          `Contexto persistente: fase=${selected.fase_atual}; órgão=${ctx.orgao}; concorrente=${ctx.concorrente}; bloqueador=${ctx.bloqueador}; prazo=${ctx.prazo}; responsável=${ctx.responsavel}; próxima ação=${ctx.recomendacao}.`,
        ].filter(Boolean).join(' '),
        impacto: [
          eventForm.impacto,
          `Consequência operacional: ${ctx.docCritico ? `documento crítico ${ctx.docCritico.titulo} pode bloquear habilitação` : 'manter rastreabilidade evita ação solta e perda de prazo'}.`,
        ].filter(Boolean).join(' '),
        aprendizado_operacional: [
          eventForm.aprendizado_operacional,
          `Aprendizado/contexto: evento conectado a ${ctx.docs.length} documento(s), ${ctx.mems.length} memória(s), peça ${ctx.peca} e próxima ação ${ctx.recomendacao}.`,
        ].filter(Boolean).join(' '),
      }
      await api.registrarEventoCaso(selected.id, payload)
      setEventForm(emptyEvent); showTimeline(selected); refresh()
    } catch (err) { setActionError(err.message || 'Erro ao registrar evento') }
    finally { setSaving(false) }
  }

  async function showTimeline(caso) {
    setTimelineCase(caso); setSelected(caso); setTimeline(null); setTimelineError('')
    try { setTimeline(await api.casoTimeline(caso.id)) }
    catch (err) { setTimelineError(err.message || 'Erro ao carregar timeline do caso') }
  }

  async function exportCase(caso, formato) {
    setExportError('')
    try { await openExport(api.exportCasoUrl(caso.id, formato), `relatorio-caso-${caso.id}.${formato}`) }
    catch (err) { setExportError(err.message || 'Erro ao exportar relatório do caso') }
  }

  return (
    <div className="space-y-6">
      {actionError && <ErrorBox text={actionError} />}
      <StateGate loading={loading} error={error} onRetry={refresh}>
        <Section
          title="Mesa operacional de Casos Vivos"
          subtitle="Operação real: criar, editar, arquivar, mover fase, registrar evento, consultar timeline e exportar relatório."
          action={<button onClick={refresh} className="rounded-xl bg-slate-800 px-4 py-2 text-sm font-bold text-white hover:bg-slate-700"><RefreshCcw size={15} className="mr-2 inline" />Atualizar</button>}
        >
          <div className="grid gap-4 md:grid-cols-4">
            <MetricCard label="Total" value={casos.length} />
            <MetricCard label="Ativos" value={ativos} tone="success" />
            <MetricCard label="Com ação" value={pendentes.length} tone="warning" />
            <MetricCard label="Arquivados" value={arquivados} />
          </div>
          <div className="mt-5 grid gap-3 md:grid-cols-6">
            <input value={filters.termo} onChange={(e) => setFilters({ ...filters, termo: e.target.value })} placeholder="Buscar cliente/órgão/objeto" className="input md:col-span-2" />
            <input value={filters.orgao} onChange={(e) => setFilters({ ...filters, orgao: e.target.value })} placeholder="Órgão" className="input" />
            <select value={filters.fase} onChange={(e) => setFilters({ ...filters, fase: e.target.value })} className="input"><option value="">Todas as fases</option>{casePhases.map((fase) => <option key={fase} value={fase}>{fase}</option>)}</select>
            <select value={filters.status} onChange={(e) => setFilters({ ...filters, status: e.target.value })} className="input"><option value="">Todos status</option>{caseStatuses.map((status) => <option key={status} value={status}>{status}</option>)}</select>
            <input value={filters.score} onChange={(e) => setFilters({ ...filters, score: e.target.value })} placeholder="Score mínimo" type="number" min="0" max="100" className="input" />
          </div>
        </Section>

        <div className="grid gap-6 xl:grid-cols-[1.3fr_0.9fr]">
          <Section title="Lista operacional" subtitle={`${casosFiltrados.length} caso(s) exibidos`}>
            {exportError && <div className="mb-4"><ErrorBox text={exportError} /></div>}
            {!casosFiltrados.length ? <Empty text="Nenhum caso encontrado. Cadastre um caso para iniciar a operação." /> : (
              <>
                <div className="space-y-3 md:hidden">
                  {casosFiltrados.map((caso) => (
                    <article key={caso.id} className={`overflow-hidden rounded-3xl border border-white/10 bg-gradient-to-br from-slate-950 via-slate-950 to-slate-900 shadow-lg ${selected?.id === caso.id ? 'ring-1 ring-blue-400/50' : ''}`}>
                      <button onClick={() => setSelected(caso)} className="block w-full p-4 text-left">
                        <div className="flex items-start gap-3">
                          <div className="flex h-14 w-14 shrink-0 flex-col items-center justify-center rounded-2xl bg-blue-500/15 text-blue-100 ring-1 ring-blue-400/25">
                            <span className="text-[10px] font-black uppercase tracking-wide text-blue-200/70">Score</span>
                            <strong className="text-lg leading-5">{caso.score_estrategico ?? 0}</strong>
                          </div>
                          <div className="min-w-0 flex-1">
                            <div className="flex flex-wrap gap-2"><Badge value={caso.fase_atual || 'prospecção'} /><Badge value={caso.status || 'ativo'} /></div>
                            <h3 className="mt-2 break-words text-base font-black leading-5 text-white">{caso.cliente || 'Cliente não informado'}</h3>
                            <p className="mt-1 break-words text-sm leading-5 text-slate-300">{caso.orgao || 'Órgão não informado'}</p>
                          </div>
                        </div>
                        <p className="mt-4 line-clamp-2 text-sm leading-6 text-slate-400">{caso.objeto || 'Objeto não informado'}</p>
                        <div className="mt-4 rounded-2xl border border-blue-400/15 bg-blue-500/10 p-3">
                          <p className="text-[10px] font-black uppercase tracking-[0.18em] text-blue-200/80">Próximo movimento</p>
                          <p className="mt-1 line-clamp-2 text-sm leading-5 text-blue-50">{nextCaseAction(caso)}</p>
                        </div>
                      </button>
                      <div className="border-t border-white/10 bg-slate-950/70 p-3">
                        <div className="mb-3 grid gap-2 rounded-2xl border border-white/10 bg-slate-900/55 p-3">
                          <p className="text-[10px] font-black uppercase tracking-[0.18em] text-slate-500">Manipulação rápida</p>
                          <div className="grid grid-cols-2 gap-2">
                            <label className="text-xs font-bold text-slate-400">Fase
                              <select value={caso.fase_atual || 'prospecção'} onChange={(e) => updatePhase(caso, e.target.value)} disabled={saving} className="input mt-1 w-full rounded-xl px-2 py-2 text-xs">
                                {casePhases.map((fase) => <option key={fase} value={fase}>{fase}</option>)}
                              </select>
                            </label>
                            <label className="text-xs font-bold text-slate-400">Status
                              <select value={caso.status || 'ativo'} onChange={(e) => quickPatchCase(caso, { status: e.target.value })} disabled={saving} className="input mt-1 w-full rounded-xl px-2 py-2 text-xs">
                                {caseStatuses.map((status) => <option key={status} value={status}>{status}</option>)}
                              </select>
                            </label>
                          </div>
                        </div>
                        <div className="grid grid-cols-[1fr_auto] gap-2">
                          <button onClick={() => setSelected(caso)} className="rounded-2xl bg-blue-600 px-4 py-3 text-sm font-black text-white">Abrir caso</button>
                          <button onClick={() => editCase(caso)} className="rounded-2xl bg-slate-800 px-4 py-3 text-sm font-black text-white">Editar</button>
                        </div>
                        <details className="mt-2 rounded-2xl border border-white/10 bg-slate-900/70">
                          <summary className="cursor-pointer px-4 py-3 text-sm font-bold text-slate-300">Mais ações</summary>
                          <div className="grid gap-2 border-t border-white/10 p-3">
                            <button onClick={() => showTimeline(caso)} className="crud-button">Ver timeline</button>
                            <button onClick={() => exportCase(caso, 'docx')} className="crud-button">Exportar DOCX</button>
                            <button onClick={() => archiveCase(caso)} disabled={saving || caso.status === 'arquivado'} className="crud-button disabled:opacity-50">Arquivar com segurança</button>
                          </div>
                        </details>
                      </div>
                    </article>
                  ))}
                </div>
                <div className="hidden overflow-x-auto mobile-scroll md:block">
                  <table className="w-full min-w-[1100px] text-left text-sm">
                    <thead className="text-xs uppercase text-slate-500"><tr><th className="px-3 py-3">Score</th><th className="px-3 py-3">Cliente/Órgão</th><th className="px-3 py-3">Objeto</th><th className="px-3 py-3">Fase</th><th className="px-3 py-3">Status</th><th className="px-3 py-3">Próxima ação</th><th className="sticky-actions px-3 py-3">Ações</th></tr></thead>
                    <tbody>
                      {casosFiltrados.map((caso) => (
                        <tr key={caso.id} className={`table-row text-slate-300 ${selected?.id === caso.id ? 'bg-blue-500/5' : ''}`}>
                          <td className="px-3 py-4"><span className="badge bg-blue-500/15 text-blue-200 ring-1 ring-blue-400/30">{caso.score_estrategico}</span></td>
                          <td className="px-3 py-4"><p className="font-bold text-white">{caso.cliente || 'Cliente não informado'}</p><p className="text-xs text-slate-500">{caso.orgao || 'Órgão não informado'}</p></td>
                          <td className="max-w-md px-3 py-4"><p className="line-clamp-2">{caso.objeto}</p><p className="mt-1 text-xs text-slate-500">{caso.modalidade || 'modalidade não informada'}</p></td>
                          <td className="px-3 py-4"><select value={caso.fase_atual || 'prospecção'} onChange={(e) => updatePhase(caso, e.target.value)} disabled={saving} className="rounded-xl border border-slate-700 bg-slate-950 px-3 py-2 text-xs text-slate-200 disabled:opacity-60">{casePhases.map((fase) => <option key={fase} value={fase}>{fase}</option>)}</select></td>
                          <td className="px-3 py-4"><Badge value={caso.status || 'ativo'} /></td>
                          <td className="max-w-xs px-3 py-4"><p className="line-clamp-3 text-xs text-slate-400">{nextCaseAction(caso)}</p></td>
                          <td className="sticky-actions px-3 py-4"><div className="crud-action-bar"><span className="crud-action-label">Ações</span><button onClick={() => setSelected(caso)} className="crud-button">Ver</button><button onClick={() => editCase(caso)} className="crud-button-primary">Editar</button><button onClick={() => showTimeline(caso)} className="crud-button">Timeline</button><button onClick={() => exportCase(caso, 'docx')} className="crud-button">DOCX</button><button onClick={() => archiveCase(caso)} disabled={saving || caso.status === 'arquivado'} className="crud-button disabled:opacity-50">Arquivar</button></div></td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </>
            )}
          </Section>

          <div id="case-editor">
          <Section title={editing ? 'Editar caso selecionado' : 'Criar novo caso'} subtitle={editing ? 'Você está editando um caso real. Altere os campos e toque em Atualizar caso para gravar.' : 'Cadastro operacional com riscos, oportunidades, contexto e texto de edital opcional na criação.'}>
            {editing && <div className="mb-4 rounded-2xl border border-blue-400/25 bg-blue-500/10 p-4 text-sm leading-6 text-blue-50"><strong>Modo edição ativo:</strong> {editing.cliente || 'Cliente não informado'} · {editing.orgao || 'Órgão não informado'}. As alterações só são gravadas ao tocar em <strong>Atualizar caso</strong>.</div>}
            <form onSubmit={saveCase} className="space-y-3">
              <div className="grid gap-3 md:grid-cols-2"><input required value={form.cliente} onChange={(e) => setForm({ ...form, cliente: e.target.value })} placeholder="Cliente/empresa" className="input" /><input required value={form.orgao} onChange={(e) => setForm({ ...form, orgao: e.target.value })} placeholder="Órgão" className="input" /></div>
              <textarea required value={form.objeto} onChange={(e) => setForm({ ...form, objeto: e.target.value })} placeholder="Objeto da licitação" className="input min-h-[90px]" />
              <div className="grid gap-3 md:grid-cols-3"><input value={form.modalidade} onChange={(e) => setForm({ ...form, modalidade: e.target.value })} placeholder="Modalidade" className="input" /><select value={form.fase_atual} onChange={(e) => setForm({ ...form, fase_atual: e.target.value })} className="input">{casePhases.map((fase) => <option key={fase} value={fase}>{fase}</option>)}</select><select value={form.status} onChange={(e) => setForm({ ...form, status: e.target.value })} className="input">{caseStatuses.map((status) => <option key={status} value={status}>{status}</option>)}</select></div>
              <input type="number" min="0" max="100" value={form.score_estrategico} onChange={(e) => setForm({ ...form, score_estrategico: e.target.value })} placeholder="Score estratégico" className="input" />
              <textarea value={form.riscos} onChange={(e) => setForm({ ...form, riscos: e.target.value })} placeholder="Riscos — um por linha" className="input min-h-[80px]" />
              <textarea value={form.oportunidades} onChange={(e) => setForm({ ...form, oportunidades: e.target.value })} placeholder="Oportunidades — uma por linha" className="input min-h-[80px]" />
              <textarea value={form.contexto} onChange={(e) => setForm({ ...form, contexto: e.target.value })} placeholder="Contexto operacional" className="input min-h-[80px]" />
              {!editing && <textarea value={form.texto_edital} onChange={(e) => setForm({ ...form, texto_edital: e.target.value })} placeholder="Opcional: trecho do edital para análise automática na criação" className="input min-h-[100px]" />}
              <div className="sticky bottom-24 z-20 -mx-1 flex flex-wrap gap-2 rounded-2xl border border-white/10 bg-slate-950/90 p-2 shadow-2xl shadow-black/40 backdrop-blur-xl md:static md:mx-0 md:border-0 md:bg-transparent md:p-0 md:shadow-none">
                <button disabled={saving || !form.cliente || !form.orgao || !form.objeto} className="min-h-12 flex-1 rounded-2xl bg-blue-600 px-4 py-3 font-black text-white disabled:opacity-60 md:flex-none">{saving ? 'Salvando...' : editing ? 'Atualizar caso' : 'Criar caso'}</button>
                {editing && <button type="button" onClick={() => { setEditing(null); setForm(emptyForm) }} className="min-h-12 rounded-2xl bg-slate-800 px-4 py-3 font-black text-white">Cancelar</button>}
              </div>
            </form>
          </Section>
          </div>
        </div>

        {selected && (() => {
          const ctx = caseContextSnapshot(selected)
          return <Section title={`Trilha operacional — ${selected.orgao || 'órgão não informado'}`} subtitle="O que falta para ganhar: fase, bloqueador, prazo, documento, memória e próxima ação no mesmo contexto." action={<button onClick={() => setSelected(null)} className="rounded-xl bg-slate-800 px-3 py-2 text-sm font-bold text-white">Fechar</button>}>
            <div className="grid gap-6 xl:grid-cols-[1fr_0.9fr]">
              <div className="space-y-4">
                <div className="rounded-2xl border border-blue-400/20 bg-blue-500/10 p-4">
                  <div className="flex flex-wrap gap-2"><Badge value={`fase ${selected.fase_atual}`} /><Badge value={selected.status} /><Badge value={`score ${selected.score_estrategico}`} /><Badge value={`responsável: ${ctx.responsavel}`} /></div>
                  <h3 className="mt-3 text-xl font-black text-white">{selected.cliente || 'Cliente não informado'}</h3>
                  <p className="mt-1 text-sm text-blue-100/80">{selected.objeto}</p>
                  <div className="mt-4 grid gap-3 md:grid-cols-2">
                    <div className="rounded-xl bg-slate-950/70 p-3"><p className="text-xs text-slate-500">Bloqueador</p><strong className="text-white">{ctx.bloqueador}</strong></div>
                    <div className="rounded-xl bg-slate-950/70 p-3"><p className="text-xs text-slate-500">Prazo crítico</p><strong className="text-white">{ctx.prazo}</strong></div>
                    <div className="rounded-xl bg-slate-950/70 p-3"><p className="text-xs text-slate-500">Órgão</p><strong className="text-white">{ctx.orgao}</strong></div>
                    <div className="rounded-xl bg-slate-950/70 p-3"><p className="text-xs text-slate-500">Concorrente relevante</p><strong className="text-white">{ctx.concorrente}</strong></div>
                  </div>
                  <div className="mt-4 rounded-xl border border-emerald-400/20 bg-emerald-500/10 p-3"><p className="text-xs font-black uppercase tracking-wide text-emerald-200">Próxima ação contextual</p><p className="mt-2 text-sm text-emerald-50">{ctx.recomendacao}</p><p className="mt-1 text-xs text-emerald-100/70">Peça pendente: {ctx.peca}</p></div>
                  <div className="mt-3 grid gap-3 md:grid-cols-2">
                    <div className="rounded-xl bg-slate-950/70 p-3"><p className="text-xs text-slate-500">Último evento</p><strong className="text-white">{ctx.ultimoEvento?.descricao || 'sem evento registrado'}</strong></div>
                    <div className="rounded-xl bg-slate-950/70 p-3"><p className="text-xs text-slate-500">Checklist pendente</p><strong className="text-white">{ctx.checklistPendente}</strong></div>
                  </div>
                </div>
                <div className="grid gap-4 md:grid-cols-2"><MiniList title="Riscos" items={selected.riscos || []} /><MiniList title="Oportunidades" items={selected.oportunidades || []} /></div>
                <div className="rounded-2xl border border-slate-800 bg-slate-950/50 p-4"><p className="text-xs font-black uppercase tracking-wide text-slate-500">Histórico rápido</p><p className="mt-2 text-sm text-slate-300">Atualizado em {formatDate(selected.atualizado_em || selected.criado_em)}. Use a timeline para ver eventos, impacto e memória sugerida.</p><button onClick={() => showTimeline(selected)} className="mt-3 rounded-xl bg-slate-800 px-3 py-2 text-xs font-black text-white">Abrir timeline viva</button></div>
              </div>
              <div className="space-y-4">
                <div className="rounded-2xl border border-slate-800 bg-slate-950/50 p-4"><p className="text-xs font-black uppercase tracking-wide text-slate-500">Checklist/documental relacionado</p><div className="mt-3 space-y-2">{ctx.docs.length ? ctx.docs.map((doc) => <div key={doc.id || doc.titulo} className="rounded-xl bg-slate-900/80 p-3"><div className="flex flex-wrap gap-2"><Badge value={doc.status || 'status'} /><Badge value={doc.criticidade || 'criticidade'} /></div><p className="mt-2 font-bold text-white">{doc.titulo}</p><p className="text-xs text-slate-500">{doc.empresa_nome || doc.cliente_nome || doc.orgao_emissor || 'sem vínculo explícito'}</p></div>) : <Empty text="Nenhum documento vinculado pelos dados atuais." />}</div></div>
                <div className="rounded-2xl border border-purple-400/20 bg-purple-500/10 p-4"><p className="text-xs font-black uppercase tracking-wide text-purple-200">Memória viva contextual</p><div className="mt-3 space-y-2">{ctx.mems.length ? ctx.mems.map((mem) => <div key={mem.id || mem.titulo} className="rounded-xl bg-slate-950/70 p-3"><Badge value={mem.tipo || 'memória'} /><p className="mt-2 font-bold text-white">{mem.titulo || mem.resumo || 'Memória relacionada'}</p><p className="line-clamp-3 text-xs text-purple-100/75">{mem.conteudo || mem.resumo || mem.aprendizado || 'Contexto registrado na memória viva.'}</p></div>) : <p className="text-sm text-purple-100/75">Sem memória explícita relacionada; registrar aprendizado após evento relevante.</p>}</div></div>
                <form onSubmit={registerEvent} className="space-y-3 rounded-2xl border border-slate-800 bg-slate-950/50 p-4"><h3 className="font-black text-white">Registrar evento no caso</h3><select value={eventForm.tipo} onChange={(e) => setEventForm({ ...eventForm, tipo: e.target.value })} className="input">{caseEventTypes.map((tipo) => <option key={tipo} value={tipo}>{tipo}</option>)}</select><textarea required value={eventForm.descricao} onChange={(e) => setEventForm({ ...eventForm, descricao: e.target.value })} placeholder="Descrição do evento" className="input min-h-[90px]" /><textarea value={eventForm.impacto} onChange={(e) => setEventForm({ ...eventForm, impacto: e.target.value })} placeholder="Impacto operacional" className="input min-h-[70px]" /><textarea value={eventForm.aprendizado_operacional} onChange={(e) => setEventForm({ ...eventForm, aprendizado_operacional: e.target.value })} placeholder="Aprendizado operacional" className="input min-h-[70px]" /><button disabled={saving || !eventForm.descricao} className="rounded-2xl bg-emerald-600 px-4 py-3 font-black text-white disabled:opacity-60">Registrar evento</button></form>
              </div>
            </div>
          </Section>
        })()}

        {timelineCase && <Section title={`Timeline operacional — ${timelineCase.orgao}`} subtitle={timelineCase.objeto} action={<button onClick={() => setTimelineCase(null)} className="rounded-xl bg-slate-800 px-3 py-2 text-xs font-bold text-white hover:bg-slate-700">Fechar</button>}>
          {timelineError ? <ErrorBox text={timelineError} /> : <CaseTimelineVisual timeline={timeline?.timeline || []} />}
        </Section>}
      </StateGate>
    </div>
  )
}

function CaseTimelineVisual({ timeline }) {
  if (!timeline.length) return <Empty text="Timeline ainda sem eventos." />
  const ordered = [...timeline].sort((a, b) => new Date(a.data || 0) - new Date(b.data || 0))
  return (
    <div className="relative space-y-4 before:absolute before:left-4 before:top-2 before:h-[calc(100%-1rem)] before:w-px before:bg-slate-700">
      {ordered.map((event) => (
        <div key={event.id} className="relative pl-12">
          <div className="absolute left-1.5 top-2 h-5 w-5 rounded-full border-4 border-slate-950 bg-blue-400 shadow-lg shadow-blue-950/50" />
          <div className="rounded-2xl border border-slate-800 bg-slate-950/60 p-4">
            <div className="flex flex-wrap items-center gap-2"><Badge value={event.fase} /><Badge value={event.tipo} /><span className="text-xs text-slate-500">{formatDate(event.data)}</span></div>
            <p className="mt-2 font-bold text-white">{event.descricao}</p>
            {event.impacto && <p className="mt-1 text-sm text-slate-400"><strong className="text-slate-200">Impacto:</strong> {event.impacto}</p>}
            {event.usuario && <p className="mt-1 text-xs text-slate-500">Usuário: {event.usuario}</p>}
            {event.memoria_sugerida && <div className="mt-3 rounded-xl border border-emerald-400/20 bg-emerald-500/10 p-3 text-xs text-emerald-100">Decisão/aprendizado relacionado: {event.memoria_sugerida.titulo || event.memoria_sugerida.tipo}</div>}
          </div>
        </div>
      ))}
    </div>
  )
}

function Kanban() {
  const { data, loading, error, refresh } = useAsyncData(api.dashboardCasos)
  const [busyId, setBusyId] = useState('')
  const [updateError, setUpdateError] = useState('')

  const casos = data?.itens || []
  const byPhase = casePhases.reduce((acc, fase) => {
    acc[fase] = casos.filter((caso) => (caso.fase_atual || 'prospecção') === fase)
    return acc
  }, {})

  async function updatePhase(caso, fase) {
    if (fase === caso.fase_atual) return
    setBusyId(caso.id)
    setUpdateError('')
    try {
      await api.atualizarFaseCaso(caso.id, {
        fase_atual: fase,
        status: fase === 'encerrado' ? 'encerrado' : caso.status,
        descricao: `Fase atualizada pelo Kanban: ${caso.fase_atual} → ${fase}`,
      })
      refresh()
    } catch (err) {
      setUpdateError(err.message || 'Erro ao atualizar fase do caso')
    } finally {
      setBusyId('')
    }
  }

  return (
    <StateGate loading={loading} error={error} onRetry={refresh}>
      <div className="space-y-6">
        <Section
          title="Kanban de Casos"
          subtitle={`${data?.total || 0} casos vivos por fase operacional`}
          action={<button onClick={refresh} className="rounded-xl bg-slate-800 px-4 py-2 text-sm font-bold text-white hover:bg-slate-700"><RefreshCcw size={15} className="mr-2 inline" />Atualizar</button>}
        >
          {updateError && <div className="mb-4"><ErrorBox text={updateError} /></div>}
          <div className="overflow-x-auto pb-2">
            <div className="grid min-w-[2600px] grid-cols-11 gap-4">
              {casePhases.map((fase) => (
                <div key={fase} className="rounded-2xl border border-slate-800 bg-slate-950/40 p-3">
                  <div className="mb-3 flex items-center justify-between gap-2">
                    <h3 className="text-sm font-black uppercase tracking-wide text-white">{fase}</h3>
                    <span className="badge bg-slate-700/70 text-slate-200 ring-1 ring-slate-500/20">{byPhase[fase]?.length || 0}</span>
                  </div>
                  <div className="space-y-3">
                    {(byPhase[fase] || []).map((caso) => (
                      <KanbanCaseCard key={caso.id} caso={caso} busy={busyId === caso.id} onUpdatePhase={updatePhase} />
                    ))}
                    {!byPhase[fase]?.length && <div className="rounded-xl border border-dashed border-slate-800 p-4 text-center text-xs text-slate-600">Sem casos</div>}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </Section>
      </div>
    </StateGate>
  )
}

function KanbanCaseCard({ caso, busy, onUpdatePhase }) {
  const riscos = (caso.riscos || []).slice(0, 2)
  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-950/75 p-4 shadow-lg shadow-slate-950/20">
      <div className="flex items-start justify-between gap-3">
        <p className="line-clamp-2 text-sm font-black text-white">{caso.orgao || 'Órgão não informado'}</p>
        <span className="badge bg-blue-500/15 text-blue-200 ring-1 ring-blue-400/30">{caso.score_estrategico}</span>
      </div>
      <p className="mt-2 line-clamp-3 text-xs text-slate-400">{caso.objeto}</p>
      <div className="mt-3 flex flex-wrap gap-2">
        <Badge value={caso.fase_atual} />
        <Badge value={caso.status} />
        {caso.risco_concorrencial && <Badge value={`risco concorrencial ${caso.risco_concorrencial.risco_concorrencial_score}`} />}
      </div>
      <div className="mt-3">
        <p className="text-[11px] font-bold uppercase tracking-wide text-slate-500">Riscos principais</p>
        {riscos.length ? (
          <ul className="mt-1 space-y-1 text-xs text-slate-300">
            {riscos.map((risco, index) => <li key={`${caso.id}-risco-${index}`} className="line-clamp-2">• {risco}</li>)}
          </ul>
        ) : <p className="mt-1 text-xs text-slate-500">Não registrados.</p>}
      </div>
      <div className="mt-3 rounded-xl bg-slate-900/70 p-3">
        <p className="text-[11px] font-bold uppercase tracking-wide text-slate-500">Próxima ação</p>
        <p className="mt-1 line-clamp-3 text-xs text-slate-300">{nextCaseAction(caso)}</p>
      </div>
      <label className="mt-3 block text-xs font-bold text-slate-400">
        Atualizar fase
        <select
          value={caso.fase_atual || 'prospecção'}
          onChange={(event) => onUpdatePhase(caso, event.target.value)}
          disabled={busy}
          className="mt-1 w-full rounded-xl border border-slate-700 bg-slate-950 px-3 py-2 text-xs text-slate-200 disabled:opacity-60"
        >
          {casePhases.map((fase) => <option key={fase} value={fase}>{fase}</option>)}
        </select>
      </label>
      {busy && <p className="mt-2 text-xs text-blue-200"><Loader2 size={13} className="mr-1 inline animate-spin" />Atualizando fase...</p>}
    </div>
  )
}

function Alertas() {
  const { data, loading, error, refresh } = useAsyncData(api.dashboardAlertas)
  const [busyId, setBusyId] = useState('')

  async function markRead(id) {
    setBusyId(id)
    try {
      await api.marcarAlertaLido(id)
      refresh()
    } finally {
      setBusyId('')
    }
  }

  async function archiveAlert(id) {
    setBusyId(id)
    try {
      await api.arquivarAlerta(id)
      refresh()
    } finally {
      setBusyId('')
    }
  }

  return (
    <StateGate loading={loading} error={error} onRetry={refresh}>
      <Section
        title="Alertas operacionais"
        subtitle={`${data?.nao_lidos || 0} não lidos de ${data?.total || 0}`}
        action={<button onClick={refresh} className="rounded-xl bg-slate-800 px-4 py-2 text-sm font-bold text-white hover:bg-slate-700"><RefreshCcw size={15} className="mr-2 inline" />Atualizar</button>}
      >
        <div className="space-y-4">
          {(data?.itens || []).map((alerta) => (
            <div key={alerta.id} className={`rounded-2xl border p-5 ${alerta.lido ? 'border-slate-800 bg-slate-950/35 opacity-70' : 'border-slate-700 bg-slate-950/70'}`}>
              <div className="flex flex-col justify-between gap-3 md:flex-row md:items-start">
                <div>
                  <div className="flex flex-wrap items-center gap-2">
                    <Badge value={alerta.severidade} map={severityStyle} />
                    {alerta.lido && <Badge value="lido" />}
                  </div>
                  <h3 className="mt-3 text-lg font-black text-white">{alerta.titulo}</h3>
                  <p className="mt-1 text-sm text-slate-400">{alerta.mensagem}</p>
                </div>
                <div className="flex flex-wrap gap-2">
                  {!alerta.lido && (
                    <button
                      onClick={() => markRead(alerta.id)}
                      disabled={busyId === alerta.id}
                      className="rounded-xl bg-emerald-600 px-4 py-2 text-sm font-bold text-white hover:bg-emerald-500 disabled:opacity-60"
                    >
                      <CheckCircle2 size={15} className="mr-2 inline" /> Marcar lido
                    </button>
                  )}
                  <button
                    onClick={() => archiveAlert(alerta.id)}
                    disabled={busyId === alerta.id}
                    className="rounded-xl bg-slate-800 px-4 py-2 text-sm font-bold text-white hover:bg-slate-700 disabled:opacity-60"
                  >
                    <X size={15} className="mr-2 inline" /> Arquivar
                  </button>
                </div>
              </div>
              <div className="mt-4 grid gap-3 text-sm text-slate-300 md:grid-cols-2">
                <p><strong className="text-slate-100">Risco:</strong> {alerta.risco}</p>
                <p><strong className="text-slate-100">Ação:</strong> {alerta.acao_recomendada}</p>
              </div>
            </div>
          ))}
        </div>
      </Section>
    </StateGate>
  )
}

function Upload() {
  const { data, loading, error, refresh } = useAsyncData(api.listarDocumentosUpload)
  const [file, setFile] = useState(null)
  const [uploading, setUploading] = useState(false)
  const [uploadError, setUploadError] = useState('')
  const [createCase, setCreateCase] = useState(false)
  const [analyzingId, setAnalyzingId] = useState('')
  const [analysisError, setAnalysisError] = useState('')
  const [result, setResult] = useState(null)
  const [filter, setFilter] = useState('')
  const [selectedDoc, setSelectedDoc] = useState(null)

  async function sendUpload(event) {
    event.preventDefault()
    if (!file) {
      setUploadError('Selecione um arquivo PDF, DOCX ou TXT antes de enviar.')
      return
    }
    setUploading(true)
    setUploadError('')
    try {
      const response = await api.uploadEdital(file)
      setFile(null)
      setResult(null)
      refresh()
      if (response?.documento?.status === 'erro') {
        setUploadError(response.documento.erro || 'Arquivo recebido, mas o texto não foi extraído.')
      }
    } catch (err) {
      setUploadError(err.message || 'Erro ao enviar documento')
    } finally {
      setUploading(false)
    }
  }

  async function analyze(documento) {
    setAnalyzingId(documento.id)
    setAnalysisError('')
    try {
      const response = await api.analisarDocumentoUpload(documento.id, {
        consultar_rag: false,
        criar_caso: createCase,
        cliente: 'frontend-upload',
        orgao: 'Órgão não identificado',
        contexto_usuario: `Análise iniciada pelo frontend para ${documento.nome_original}`,
      })
      setResult(response)
      refresh()
    } catch (err) {
      setAnalysisError(err.message || 'Erro ao analisar documento')
    } finally {
      setAnalyzingId('')
    }
  }

  async function archiveDocument(documento) {
    setAnalyzingId(documento.id)
    setAnalysisError('')
    try {
      await api.arquivarDocumentoUpload(documento.id)
      if (selectedDoc?.id === documento.id) setSelectedDoc(null)
      refresh()
    } catch (err) {
      setAnalysisError(err.message || 'Erro ao arquivar documento')
    } finally {
      setAnalyzingId('')
    }
  }

  const documentos = (data?.documentos || []).filter((doc) => {
    const q = filter.toLowerCase()
    if (!q) return true
    return [doc.nome_original, doc.status, doc.extensao, doc.caso_id].join(' ').toLowerCase().includes(q)
  })

  return (
    <StateGate loading={loading} error={error} onRetry={refresh}>
      <div className="space-y-6">
        <Section title="Upload de edital/documento" subtitle="Envie PDF, DOCX ou TXT para extração e análise automática">
          <form onSubmit={sendUpload} className="space-y-4">
            <div className="rounded-2xl border border-dashed border-slate-700 bg-slate-950/50 p-5">
              <label className="block text-sm font-bold text-white">Arquivo</label>
              <input
                type="file"
                accept=".pdf,.docx,.txt,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document,text/plain"
                onChange={(event) => setFile(event.target.files?.[0] || null)}
                className="mt-3 w-full rounded-xl border border-slate-700 bg-slate-950 px-4 py-3 text-sm text-slate-200 file:mr-4 file:rounded-lg file:border-0 file:bg-blue-600 file:px-3 file:py-2 file:text-sm file:font-bold file:text-white hover:file:bg-blue-500"
              />
              <p className="mt-2 text-xs text-slate-500">O arquivo será salvo com segurança e vinculado à operação.</p>
            </div>
            {uploadError && <ErrorBox text={uploadError} />}
            <button
              type="submit"
              disabled={uploading}
              className="rounded-xl bg-blue-600 px-5 py-3 text-sm font-black text-white hover:bg-blue-500 disabled:opacity-60"
            >
              {uploading ? <Loader2 size={16} className="mr-2 inline animate-spin" /> : <UploadCloud size={16} className="mr-2 inline" />}
              {uploading ? 'Enviando...' : 'Enviar'}
            </button>
          </form>
        </Section>

        <Section
          title="Documentos enviados"
          subtitle={`${documentos.length} documento(s) registrados`}
          action={
            <div className="flex flex-wrap items-center gap-2">
              <input value={filter} onChange={(event) => setFilter(event.target.value)} placeholder="Filtrar" className="rounded-xl border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-200" />
              <label className="flex items-center gap-2 rounded-xl bg-slate-800 px-4 py-2 text-sm font-bold text-slate-200">
                <input type="checkbox" checked={createCase} onChange={(event) => setCreateCase(event.target.checked)} className="h-4 w-4 accent-blue-500" />
                criar caso vivo
              </label>
            </div>
          }
        >
          {analysisError && <div className="mb-4"><ErrorBox text={analysisError} /></div>}
          {!documentos.length ? <Empty text="Nenhum documento enviado ainda." /> : (
            <div className="space-y-3">
              {documentos.map((documento) => (
                <div key={documento.id} className="rounded-2xl border border-slate-800 bg-slate-950/50 p-5">
                  <div className="flex flex-col justify-between gap-4 md:flex-row md:items-start">
                    <div className="min-w-0">
                      <div className="flex flex-wrap items-center gap-2">
                        <Badge value={documento.status} />
                        <Badge value={documento.extensao?.toUpperCase?.() || documento.extensao} />
                        {documento.caso_id && <Badge value="caso vivo" />}
                      </div>
                      <h3 className="mt-3 font-black text-white">{documento.nome_original}</h3>
                      <p className="mt-1 text-sm text-slate-400">
                        {documento.caracteres_extraidos || 0} caracteres extraídos · {formatDate(documento.criado_em)}
                      </p>
                      {documento.erro && <p className="mt-2 text-sm text-red-200">{documento.erro}</p>}
                    </div>
                    <div className="flex flex-wrap gap-2">
                      <button onClick={() => setSelectedDoc(documento)} className="rounded-xl bg-slate-800 px-4 py-2 text-sm font-bold text-white hover:bg-slate-700"><Eye size={15} className="mr-2 inline" />Detalhe</button>
                      <button
                        onClick={() => analyze(documento)}
                        disabled={analyzingId === documento.id || !documento.texto_extraido}
                        className="rounded-xl bg-emerald-600 px-4 py-2 text-sm font-bold text-white hover:bg-emerald-500 disabled:opacity-60"
                      >
                        {analyzingId === documento.id ? <Loader2 size={15} className="mr-2 inline animate-spin" /> : <Search size={15} className="mr-2 inline" />}
                        {analyzingId === documento.id ? 'Analisando...' : 'Analisar'}
                      </button>
                      <button onClick={() => archiveDocument(documento)} disabled={analyzingId === documento.id} className="rounded-xl bg-slate-800 px-4 py-2 text-sm font-bold text-white hover:bg-slate-700 disabled:opacity-60"><X size={15} className="mr-2 inline" />Arquivar</button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </Section>

        {selectedDoc && (
          <Section title={`Detalhe do upload: ${selectedDoc.nome_original}`} subtitle={`ID ${selectedDoc.id}`} action={<button onClick={() => setSelectedDoc(null)} className="rounded-xl bg-slate-800 px-3 py-2 text-sm font-bold text-white">Fechar</button>}>
            <pre className="max-h-96 overflow-auto whitespace-pre-wrap rounded-2xl border border-slate-800 bg-slate-950 p-5 text-xs text-slate-300">{JSON.stringify(selectedDoc, null, 2)}</pre>
          </Section>
        )}

        {result && <AnalysisResult result={result} />}
      </div>
    </StateGate>
  )
}

function AnalysisResult({ result }) {
  const analise = result.analise || {}
  const resumo = analise.resumo_edital || {}
  const decisao = analise.decisao_recomendada || {}
  const memoria = result.memoria_sugerida || analise.memoria_sugerida

  return (
    <div className="space-y-6">
      <Section title="Resultado da análise" subtitle={result.caso_id ? `Caso vivo criado: ${result.caso_id}` : 'Análise automática do edital/documento'}>
        <div className="grid gap-4 lg:grid-cols-3">
          <div className="rounded-2xl border border-slate-800 bg-slate-950/50 p-5 lg:col-span-2">
            <h3 className="font-black text-white">Resumo</h3>
            <p className="mt-3 text-sm text-slate-300"><strong className="text-white">Objeto:</strong> {resumo.objeto || '—'}</p>
            <p className="mt-2 text-sm text-slate-300"><strong className="text-white">Modalidade:</strong> {resumo.modalidade || '—'}</p>
          </div>
          <div className="rounded-2xl border border-blue-400/30 bg-blue-500/10 p-5">
            <h3 className="font-black text-white">Decisão recomendada</h3>
            <p className="mt-3 text-2xl font-black text-blue-100">{decisao.decisao || '—'}</p>
            <p className="mt-1 text-sm text-slate-300">Score {decisao.score ?? '—'}/100</p>
            <p className="mt-3 text-xs text-slate-400">{decisao.acao_imediata}</p>
          </div>
        </div>
      </Section>

      <div className="grid gap-6 xl:grid-cols-2">
        <ListSection title="Riscos" items={analise.riscos || []} empty="Nenhum risco retornado." />
        <ListSection title="Oportunidades" items={analise.oportunidades || []} empty="Nenhuma oportunidade retornada." />
      </div>

      {memoria && (
        <Section title="Memória sugerida" subtitle="Aprendizado operacional para aprovação humana antes do registro definitivo">
          <div className="rounded-2xl border border-emerald-400/20 bg-emerald-500/10 p-5">
            <Badge value={memoria.tipo || 'memoria'} />
            <h3 className="mt-3 font-black text-white">{memoria.titulo}</h3>
            <p className="mt-2 text-sm text-slate-300">{memoria.descricao}</p>
            <p className="mt-3 text-sm text-slate-400"><strong className="text-slate-100">Estratégia:</strong> {memoria.estrategia}</p>
            <p className="mt-2 text-sm text-slate-400"><strong className="text-slate-100">Uso operacional:</strong> {memoria.uso_futuro}</p>
          </div>
        </Section>
      )}
    </div>
  )
}

function ListSection({ title, items, empty }) {
  return (
    <Section title={title}>
      {!items.length ? <Empty text={empty} /> : (
        <ul className="space-y-3">
          {items.map((item, index) => (
            <li key={`${title}-${index}`} className="rounded-xl border border-slate-800 bg-slate-950/50 p-4 text-sm text-slate-300">
              {item}
            </li>
          ))}
        </ul>
      )}
    </Section>
  )
}

function ErrorBox({ text }) {
  return (
    <div className="rounded-xl border border-red-400/30 bg-red-500/10 p-4 text-sm text-red-100">
      <AlertTriangle size={16} className="mr-2 inline" /> {text}
    </div>
  )
}

function Pecas() {
  const { data, loading, error, refresh } = useAsyncData(async () => {
    const [engine, documentos, casos, gerados] = await Promise.all([
      api.documentosEngine(),
      api.listarDocumentosUpload(),
      api.dashboardCasos(),
      api.documentosGerados(),
    ])
    return { engine, documentos, casos, gerados }
  })
  const [tipo, setTipo] = useState('impugnacao')
  const [origem, setOrigem] = useState('manual')
  const [selectedId, setSelectedId] = useState('')
  const [contexto, setContexto] = useState('')
  const [tese, setTese] = useState('')
  const [gerando, setGerando] = useState(false)
  const [generateError, setGenerateError] = useState('')
  const [exportError, setExportError] = useState('')
  const [result, setResult] = useState(null)
  const [copied, setCopied] = useState(false)
  const [selectedDoc, setSelectedDoc] = useState(null)
  const [editDoc, setEditDoc] = useState(null)

  const documentos = data?.documentos?.documentos || []
  const casos = data?.casos?.itens || []
  const gerados = data?.gerados?.documentos || []
  const selectedDocument = documentos.find((doc) => doc.id === selectedId)
  const selectedCase = casos.find((caso) => caso.id === selectedId)

  async function gerarPeca(event) {
    event.preventDefault()
    setGerando(true)
    setGenerateError('')
    setCopied(false)
    try {
      const payload = {
        contexto,
        tese_principal: tese,
        cliente: 'frontend-pecas',
        orgao: selectedCase?.orgao || 'Órgão não informado',
        objeto: selectedCase?.objeto || selectedDocument?.analise?.resumo_edital?.objeto || selectedDocument?.nome_original || 'Objeto não informado',
        modalidade: selectedCase?.modalidade || selectedDocument?.analise?.resumo_edital?.modalidade || '',
      }
      if (origem === 'documento' && selectedId) payload.documento_id = selectedId
      if (origem === 'caso' && selectedId) payload.case_id = selectedId

      const response = tipo === 'impugnacao'
        ? await api.gerarImpugnacao(payload)
        : tipo === 'recurso'
          ? await api.gerarRecurso(payload)
          : await api.gerarContrarrazoes(payload)
      setResult(response)
      refresh()
    } catch (err) {
      setGenerateError(err.message || 'Erro ao gerar peça')
    } finally {
      setGerando(false)
    }
  }


  async function archiveGenerated(doc) {
    setExportError('')
    try {
      await api.arquivarDocumentoGerado(doc.id)
      if (selectedDoc?.id === doc.id) setSelectedDoc(null)
      if (editDoc?.id === doc.id) setEditDoc(null)
      refresh()
    } catch (err) {
      setExportError(err.message || 'Erro ao arquivar peça')
    }
  }

  async function saveGeneratedEdit(event) {
    event.preventDefault()
    if (!editDoc?.id) return
    setExportError('')
    try {
      await api.atualizarDocumentoGerado(editDoc.id, { titulo: editDoc.titulo, texto: editDoc.texto })
      setEditDoc(null)
      refresh()
    } catch (err) {
      setExportError(err.message || 'Erro ao atualizar peça')
    }
  }

  async function copyText(text) {
    try {
      await navigator.clipboard.writeText(text)
      setCopied(true)
      setTimeout(() => setCopied(false), 1800)
    } catch {
      setCopied(false)
      setGenerateError('Não foi possível copiar automaticamente. Selecione o texto e copie manualmente.')
    }
  }

  async function exportDocument(doc, formato) {
    setExportError('')
    try {
      await openExport(api.exportDocumentoUrl(doc.id, formato), `${doc.tipo || 'peca'}-${doc.id}.${formato}`)
    } catch (err) {
      setExportError(err.message || 'Erro ao exportar peça')
    }
  }

  return (
    <StateGate loading={loading} error={error} onRetry={refresh}>
      <div className="space-y-6">
        <Section title="Gerar peça administrativa" subtitle="Impugnação, recurso ou contrarrazões a partir de documento, caso vivo ou contexto manual">
          <form onSubmit={gerarPeca} className="space-y-5">
            <div className="grid gap-4 lg:grid-cols-3">
              <label className="block">
                <span className="text-sm font-bold text-white">Tipo de peça</span>
                <select value={tipo} onChange={(event) => setTipo(event.target.value)} className="mt-2 w-full rounded-xl border border-slate-700 bg-slate-950 px-4 py-3 text-sm text-slate-200">
                  <option value="impugnacao">Impugnação</option>
                  <option value="recurso">Recurso</option>
                  <option value="contrarrazoes">Contrarrazões</option>
                </select>
              </label>
              <label className="block">
                <span className="text-sm font-bold text-white">Origem</span>
                <select value={origem} onChange={(event) => { setOrigem(event.target.value); setSelectedId('') }} className="mt-2 w-full rounded-xl border border-slate-700 bg-slate-950 px-4 py-3 text-sm text-slate-200">
                  <option value="manual">Manual</option>
                  <option value="documento">Documento enviado</option>
                  <option value="caso">Caso vivo</option>
                </select>
              </label>
              {origem !== 'manual' && (
                <label className="block">
                  <span className="text-sm font-bold text-white">Selecionar {origem === 'documento' ? 'documento' : 'caso'}</span>
                  <select value={selectedId} onChange={(event) => setSelectedId(event.target.value)} className="mt-2 w-full rounded-xl border border-slate-700 bg-slate-950 px-4 py-3 text-sm text-slate-200">
                    <option value="">Selecione...</option>
                    {origem === 'documento' && documentos.map((doc) => (
                      <option key={doc.id} value={doc.id}>{doc.nome_original}</option>
                    ))}
                    {origem === 'caso' && casos.map((caso) => (
                      <option key={caso.id} value={caso.id}>{caso.orgao} — {caso.objeto}</option>
                    ))}
                  </select>
                </label>
              )}
            </div>

            <label className="block">
              <span className="text-sm font-bold text-white">Tese principal opcional</span>
              <input
                value={tese}
                onChange={(event) => setTese(event.target.value)}
                placeholder="Ex.: exigência de atestado 100% sem justificativa técnica"
                className="mt-2 w-full rounded-xl border border-slate-700 bg-slate-950 px-4 py-3 text-sm text-slate-200 placeholder:text-slate-600"
              />
            </label>

            <label className="block">
              <span className="text-sm font-bold text-white">Contexto adicional opcional</span>
              <textarea
                value={contexto}
                onChange={(event) => setContexto(event.target.value)}
                rows={4}
                placeholder="Inclua fatos, decisão atacada, falha do concorrente, pedido desejado ou observação estratégica."
                className="mt-2 w-full rounded-xl border border-slate-700 bg-slate-950 px-4 py-3 text-sm text-slate-200 placeholder:text-slate-600"
              />
            </label>

            {generateError && <ErrorBox text={generateError} />}
            <button disabled={gerando || (origem !== 'manual' && !selectedId)} className="rounded-xl bg-blue-600 px-5 py-3 text-sm font-black text-white hover:bg-blue-500 disabled:opacity-60">
              {gerando ? <Loader2 size={16} className="mr-2 inline animate-spin" /> : <FileText size={16} className="mr-2 inline" />}
              {gerando ? 'Gerando peça...' : 'Gerar peça'}
            </button>
          </form>
        </Section>

        <div className="grid gap-6 xl:grid-cols-2">
          <Section title="Documentos/casos disponíveis" subtitle={`${documentos.length} documentos · ${casos.length} casos`}>
            <div className="space-y-3">
              {!documentos.length && !casos.length ? <Empty text="Nenhum documento ou caso disponível." /> : (
                <>
                  {documentos.slice(0, 5).map((doc) => (
                    <div key={doc.id} className="rounded-xl border border-slate-800 bg-slate-950/50 p-4">
                      <Badge value="documento" /> <span className="ml-2 text-sm font-bold text-white">{doc.nome_original}</span>
                      <p className="mt-1 text-xs text-slate-500">{doc.status} · {doc.caracteres_extraidos || 0} caracteres</p>
                    </div>
                  ))}
                  {casos.slice(0, 5).map((caso) => (
                    <div key={caso.id} className="rounded-xl border border-slate-800 bg-slate-950/50 p-4">
                      <Badge value="caso" /> <span className="ml-2 text-sm font-bold text-white">{caso.orgao}</span>
                      <p className="mt-1 line-clamp-2 text-xs text-slate-500">{caso.objeto}</p>
                    </div>
                  ))}
                </>
              )}
            </div>
          </Section>

          <Section title="Peças já geradas" subtitle={`${gerados.length} peça(s) salvas`}>
            {exportError && <div className="mb-4"><ErrorBox text={exportError} /></div>}
            {!gerados.length ? <Empty text="Nenhuma peça gerada ainda." /> : (
              <div className="space-y-3">
                {gerados.slice(0, 8).map((doc) => (
                  <div key={doc.id} className="rounded-xl border border-slate-800 bg-slate-950/50 p-4">
                    <div className="flex flex-wrap items-center gap-2">
                      <Badge value={doc.tipo} />
                      <span className="text-xs text-slate-500">{formatDate(doc.criado_em)}</span>
                    </div>
                    <p className="mt-2 font-bold text-white">{doc.titulo}</p>
                    <p className="mt-1 text-xs text-slate-500">{doc.arquivo}</p>
                    <div className="mt-3 flex flex-wrap gap-2">
                      <button onClick={() => setSelectedDoc(doc)} className="rounded-xl bg-slate-800 px-3 py-2 text-xs font-bold text-white hover:bg-slate-700"><Eye size={14} className="mr-1.5 inline" /> Detalhe</button>
                      <button onClick={() => setEditDoc({ ...doc })} className="rounded-xl bg-blue-600 px-3 py-2 text-xs font-bold text-white hover:bg-blue-500"><FileText size={14} className="mr-1.5 inline" /> Editar</button>
                      <button onClick={() => exportDocument(doc, 'txt')} className="rounded-xl bg-slate-800 px-3 py-2 text-xs font-bold text-white hover:bg-slate-700"><Download size={14} className="mr-1.5 inline" /> Baixar TXT</button>
                      <button onClick={() => exportDocument(doc, 'docx')} className="rounded-xl bg-slate-800 px-3 py-2 text-xs font-bold text-white hover:bg-slate-700"><Download size={14} className="mr-1.5 inline" /> Baixar DOCX</button>
                      <button onClick={() => archiveGenerated(doc)} className="rounded-xl bg-slate-800 px-3 py-2 text-xs font-bold text-white hover:bg-slate-700"><X size={14} className="mr-1.5 inline" /> Arquivar</button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </Section>
        </div>

        {selectedDoc && (
          <Section title={`Detalhe da peça: ${selectedDoc.titulo}`} subtitle={`ID ${selectedDoc.id}`} action={<button onClick={() => setSelectedDoc(null)} className="rounded-xl bg-slate-800 px-3 py-2 text-sm font-bold text-white">Fechar</button>}>
            <pre className="max-h-96 overflow-auto whitespace-pre-wrap rounded-2xl border border-slate-800 bg-slate-950 p-5 text-xs text-slate-300">{JSON.stringify(selectedDoc, null, 2)}</pre>
          </Section>
        )}

        {editDoc && (
          <Section title={`Editar peça: ${editDoc.titulo}`} subtitle="Atualização controlada com Audit Log">
            <form onSubmit={saveGeneratedEdit} className="space-y-3">
              <input value={editDoc.titulo || ''} onChange={(e) => setEditDoc({ ...editDoc, titulo: e.target.value })} className="input" />
              <textarea value={editDoc.texto || ''} onChange={(e) => setEditDoc({ ...editDoc, texto: e.target.value })} rows={12} className="input font-mono" />
              <div className="flex flex-wrap gap-2"><button className="rounded-xl bg-blue-600 px-4 py-2 text-sm font-bold text-white">Salvar peça</button><button type="button" onClick={() => setEditDoc(null)} className="rounded-xl bg-slate-800 px-4 py-2 text-sm font-bold text-white">Cancelar</button></div>
            </form>
          </Section>
        )}

        {result?.documento && (
          <Section
            title="Texto gerado"
            subtitle={`${result.documento.tipo} · ${result.documento.arquivo}`}
            action={
              <button onClick={() => copyText(result.documento.texto)} className="rounded-xl bg-emerald-600 px-4 py-2 text-sm font-bold text-white hover:bg-emerald-500">
                <Copy size={15} className="mr-2 inline" /> {copied ? 'Copiado' : 'Copiar texto'}
              </button>
            }
          >
            <pre className="max-h-[560px] overflow-auto whitespace-pre-wrap rounded-2xl border border-slate-800 bg-slate-950 p-5 text-sm leading-6 text-slate-200">
              {result.documento.texto}
            </pre>
            {result.memoria_sugerida && (
              <div className="mt-5 rounded-2xl border border-emerald-400/20 bg-emerald-500/10 p-5">
                <Badge value={result.memoria_sugerida.tipo || 'tese'} />
                <h3 className="mt-3 font-black text-white">{result.memoria_sugerida.titulo}</h3>
                <p className="mt-2 text-sm text-slate-300">{result.memoria_sugerida.descricao}</p>
              </div>
            )}
          </Section>
        )}
      </div>
    </StateGate>
  )
}

function Consultor() {
  const { data, loading, error, refresh } = useAsyncData(loadConsultorWorkspace)
  const [clienteForm, setClienteForm] = useState({ nome: '', documento: '', segmento: '', uf: '', contatos: '', observacoes: '', status: 'prospect', score_potencial: 50 })
  const [demandaForm, setDemandaForm] = useState({ cliente_id: '', tipo: 'edital', descricao: '', prazo: '', prioridade: 'média', status: 'aberta', caso_vivo_id: '' })
  const [selectedClienteId, setSelectedClienteId] = useState('')
  const [clienteDetalhe, setClienteDetalhe] = useState(null)
  const [busy, setBusy] = useState(false)
  const [actionError, setActionError] = useState('')

  const clientes = data?.clientes?.clientes || []
  const demandas = data?.demandas?.demandas || []

  async function salvarCliente(event) {
    event.preventDefault()
    setBusy(true)
    setActionError('')
    try {
      await api.consultorCriarCliente({
        ...clienteForm,
        score_potencial: Number(clienteForm.score_potencial) || 50,
        contatos: clienteForm.contatos.split('\n').map((item) => item.trim()).filter(Boolean),
      })
      setClienteForm({ nome: '', documento: '', segmento: '', uf: '', contatos: '', observacoes: '', status: 'prospect', score_potencial: 50 })
      refresh()
    } catch (err) {
      setActionError(err.message || 'Erro ao salvar cliente')
    } finally {
      setBusy(false)
    }
  }

  async function carregarCliente(id) {
    setSelectedClienteId(id)
    setClienteDetalhe(null)
    if (!id) return
    setActionError('')
    try {
      const detalhe = await api.consultorCliente(id)
      setClienteDetalhe(detalhe)
      setDemandaForm((form) => ({ ...form, cliente_id: id }))
    } catch (err) {
      setActionError(err.message || 'Erro ao carregar cliente')
    }
  }

  async function registrarDemanda(event) {
    event.preventDefault()
    if (!demandaForm.cliente_id) {
      setActionError('Selecione um cliente para registrar a demanda.')
      return
    }
    setBusy(true)
    setActionError('')
    try {
      await api.consultorRegistrarDemanda(demandaForm.cliente_id, {
        tipo: demandaForm.tipo,
        descricao: demandaForm.descricao,
        prazo: demandaForm.prazo,
        prioridade: demandaForm.prioridade,
        status: demandaForm.status,
        caso_vivo_id: demandaForm.caso_vivo_id || null,
      })
      setDemandaForm((form) => ({ ...form, descricao: '', prazo: '', prioridade: 'média', status: 'aberta', caso_vivo_id: '' }))
      refresh()
      if (selectedClienteId) carregarCliente(selectedClienteId)
    } catch (err) {
      setActionError(err.message || 'Erro ao registrar demanda')
    } finally {
      setBusy(false)
    }
  }

  async function atualizarStatus(demanda, status) {
    setBusy(true)
    setActionError('')
    try {
      await api.consultorAtualizarDemanda(demanda.id, { status, observacao: 'Atualizado pela tela Consultor' })
      refresh()
      if (selectedClienteId) carregarCliente(selectedClienteId)
    } catch (err) {
      setActionError(err.message || 'Erro ao atualizar demanda')
    } finally {
      setBusy(false)
    }
  }

  return (
    <StateGate loading={loading} error={error} onRetry={refresh}>
      <div className="space-y-6">
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <KpiCard title="Clientes" value={clientes.length} icon={BriefcaseBusiness} hint="Carteira consultiva" />
          <KpiCard title="Demandas" value={demandas.length} icon={FileText} hint="Atendimentos registrados" />
          <KpiCard title="Abertas" value={demandas.filter((item) => item.status === 'aberta').length} icon={Clock} hint="Exigem triagem" />
          <KpiCard title="Críticas/altas" value={demandas.filter((item) => ['crítica', 'alta'].includes(item.prioridade)).length} icon={AlertTriangle} hint="Prioridade operacional" />
        </div>

        {actionError && <ErrorBox text={actionError} />}

        <div className="grid gap-6 xl:grid-cols-2">
          <Section title="Cadastrar cliente" subtitle="Carteira da consultoria em licitações">
            <form onSubmit={salvarCliente} className="space-y-4">
              <div className="grid gap-4 md:grid-cols-2">
                <TextInput label="Nome" value={clienteForm.nome} onChange={(value) => setClienteForm({ ...clienteForm, nome: value })} required />
                <TextInput label="CNPJ/CPF" value={clienteForm.documento} onChange={(value) => setClienteForm({ ...clienteForm, documento: value })} />
                <TextInput label="Segmento" value={clienteForm.segmento} onChange={(value) => setClienteForm({ ...clienteForm, segmento: value })} />
                <TextInput label="UF" value={clienteForm.uf} onChange={(value) => setClienteForm({ ...clienteForm, uf: value.toUpperCase() })} />
              </div>
              <div className="grid gap-4 md:grid-cols-2">
                <label className="block">
                  <span className="text-sm font-bold text-white">Status</span>
                  <select value={clienteForm.status} onChange={(event) => setClienteForm({ ...clienteForm, status: event.target.value })} className="mt-2 w-full rounded-xl border border-slate-700 bg-slate-950 px-4 py-3 text-sm text-slate-200">
                    {['prospect', 'ativo', 'pausado', 'encerrado', 'inadimplente'].map((item) => <option key={item} value={item}>{item}</option>)}
                  </select>
                </label>
                <TextInput label="Score de potencial" type="number" value={clienteForm.score_potencial} onChange={(value) => setClienteForm({ ...clienteForm, score_potencial: value })} />
              </div>
              <label className="block">
                <span className="text-sm font-bold text-white">Contatos — um por linha</span>
                <textarea value={clienteForm.contatos} onChange={(event) => setClienteForm({ ...clienteForm, contatos: event.target.value })} rows={3} className="mt-2 w-full rounded-xl border border-slate-700 bg-slate-950 px-4 py-3 text-sm text-slate-200" />
              </label>
              <label className="block">
                <span className="text-sm font-bold text-white">Observações</span>
                <textarea value={clienteForm.observacoes} onChange={(event) => setClienteForm({ ...clienteForm, observacoes: event.target.value })} rows={3} className="mt-2 w-full rounded-xl border border-slate-700 bg-slate-950 px-4 py-3 text-sm text-slate-200" />
              </label>
              <button disabled={busy || !clienteForm.nome} className="rounded-xl bg-blue-600 px-5 py-3 text-sm font-black text-white hover:bg-blue-500 disabled:opacity-60">
                {busy ? <Loader2 size={16} className="mr-2 inline animate-spin" /> : <BriefcaseBusiness size={16} className="mr-2 inline" />} Salvar cliente
              </button>
            </form>
          </Section>

          <Section title="Registrar demanda" subtitle="Edital, impugnação, recurso, habilitação, proposta, contrato ou cobrança">
            <form onSubmit={registrarDemanda} className="space-y-4">
              <label className="block">
                <span className="text-sm font-bold text-white">Cliente</span>
                <select value={demandaForm.cliente_id} onChange={(event) => { setDemandaForm({ ...demandaForm, cliente_id: event.target.value }); carregarCliente(event.target.value) }} className="mt-2 w-full rounded-xl border border-slate-700 bg-slate-950 px-4 py-3 text-sm text-slate-200">
                  <option value="">Selecione...</option>
                  {clientes.map((cliente) => <option key={cliente.id} value={cliente.id}>{cliente.nome}</option>)}
                </select>
              </label>
              <div className="grid gap-4 md:grid-cols-3">
                <label className="block">
                  <span className="text-sm font-bold text-white">Tipo</span>
                  <select value={demandaForm.tipo} onChange={(event) => setDemandaForm({ ...demandaForm, tipo: event.target.value })} className="mt-2 w-full rounded-xl border border-slate-700 bg-slate-950 px-4 py-3 text-sm text-slate-200">
                    {['edital', 'impugnação', 'recurso', 'habilitação', 'proposta', 'contrato', 'cobrança'].map((item) => <option key={item} value={item}>{item}</option>)}
                  </select>
                </label>
                <label className="block">
                  <span className="text-sm font-bold text-white">Prioridade</span>
                  <select value={demandaForm.prioridade} onChange={(event) => setDemandaForm({ ...demandaForm, prioridade: event.target.value })} className="mt-2 w-full rounded-xl border border-slate-700 bg-slate-950 px-4 py-3 text-sm text-slate-200">
                    {['baixa', 'média', 'alta', 'crítica'].map((item) => <option key={item} value={item}>{item}</option>)}
                  </select>
                </label>
                <label className="block">
                  <span className="text-sm font-bold text-white">Status</span>
                  <select value={demandaForm.status} onChange={(event) => setDemandaForm({ ...demandaForm, status: event.target.value })} className="mt-2 w-full rounded-xl border border-slate-700 bg-slate-950 px-4 py-3 text-sm text-slate-200">
                    {demandStatusOptions.map((item) => <option key={item} value={item}>{item}</option>)}
                  </select>
                </label>
              </div>
              <TextInput label="Prazo" value={demandaForm.prazo} onChange={(value) => setDemandaForm({ ...demandaForm, prazo: value })} placeholder="2026-05-15T18:00:00Z" />
              <TextInput label="Caso vivo relacionado (opcional)" value={demandaForm.caso_vivo_id} onChange={(value) => setDemandaForm({ ...demandaForm, caso_vivo_id: value })} />
              <label className="block">
                <span className="text-sm font-bold text-white">Descrição</span>
                <textarea value={demandaForm.descricao} onChange={(event) => setDemandaForm({ ...demandaForm, descricao: event.target.value })} rows={4} className="mt-2 w-full rounded-xl border border-slate-700 bg-slate-950 px-4 py-3 text-sm text-slate-200" />
              </label>
              <button disabled={busy || !demandaForm.cliente_id || !demandaForm.descricao} className="rounded-xl bg-emerald-600 px-5 py-3 text-sm font-black text-white hover:bg-emerald-500 disabled:opacity-60">
                {busy ? <Loader2 size={16} className="mr-2 inline animate-spin" /> : <FileText size={16} className="mr-2 inline" />} Registrar demanda
              </button>
            </form>
          </Section>
        </div>

        <div className="grid gap-6 xl:grid-cols-2">
          <Section title="Clientes" subtitle={`${clientes.length} cliente(s) na carteira`}>
            <div className="space-y-3">
              {!clientes.length ? <Empty text="Nenhum cliente cadastrado." /> : clientes.map((cliente) => (
                <button key={cliente.id} onClick={() => carregarCliente(cliente.id)} className={`block w-full rounded-xl border p-4 text-left transition ${selectedClienteId === cliente.id ? 'border-blue-400/40 bg-blue-500/10' : 'border-slate-800 bg-slate-950/50 hover:bg-slate-900/70'}`}>
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <p className="font-black text-white">{cliente.nome}</p>
                      <p className="mt-1 text-xs text-slate-500">{cliente.documento || 'sem documento'} · {cliente.segmento || 'sem segmento'} · {cliente.uf || 'UF —'}</p>
                    </div>
                    <span className="badge bg-blue-500/15 text-blue-200 ring-1 ring-blue-400/30">{cliente.score_potencial}</span>
                  </div>
                  <div className="mt-3 flex flex-wrap gap-2"><Badge value={cliente.status} /></div>
                </button>
              ))}
            </div>
          </Section>

          <Section title="Demandas" subtitle={`${demandas.length} demanda(s) registradas`}>
            <DemandList demandas={demandas} busy={busy} onStatus={atualizarStatus} />
          </Section>
        </div>

        {clienteDetalhe && (
          <Section title={`Cliente: ${clienteDetalhe.cliente.nome}`} subtitle="Demandas e casos vivos relacionados">
            <div className="grid gap-6 xl:grid-cols-2">
              <div>
                <h3 className="font-black text-white">Demandas do cliente</h3>
                <div className="mt-3"><DemandList demandas={clienteDetalhe.demandas || []} busy={busy} onStatus={atualizarStatus} /></div>
              </div>
              <div>
                <h3 className="font-black text-white">Casos relacionados</h3>
                <div className="mt-3 space-y-3">
                  {!clienteDetalhe.casos_relacionados?.length ? <Empty text="Nenhum caso vivo relacionado." /> : clienteDetalhe.casos_relacionados.map((caso) => (
                    <div key={caso.id} className="rounded-xl border border-slate-800 bg-slate-950/50 p-4">
                      <div className="flex items-start justify-between gap-3">
                        <div><p className="font-bold text-white">{caso.orgao}</p><p className="mt-1 line-clamp-2 text-sm text-slate-400">{caso.objeto}</p></div>
                        <Badge value={caso.fase_atual} />
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </Section>
        )}
      </div>
    </StateGate>
  )
}

function DemandList({ demandas, busy, onStatus }) {
  if (!demandas.length) return <Empty text="Nenhuma demanda registrada." />
  return (
    <div className="space-y-3">
      {demandas.map((demanda) => (
        <div key={demanda.id} className="rounded-xl border border-slate-800 bg-slate-950/50 p-4">
          <div className="flex flex-wrap items-center gap-2">
            <Badge value={demanda.tipo} />
            <Badge value={demanda.prioridade} />
            <Badge value={demanda.status} />
          </div>
          <p className="mt-2 font-bold text-white">{demanda.cliente_nome}</p>
          <p className="mt-1 text-sm text-slate-400">{demanda.descricao}</p>
          <p className="mt-2 text-xs text-slate-500">Prazo: {demanda.prazo || 'não informado'} {demanda.caso_vivo_id ? `· Caso: ${demanda.caso_vivo_id}` : ''}</p>
          <div className="mt-3 flex flex-wrap gap-2">
            {demandStatusOptions.map((status) => (
              <button key={status} onClick={() => onStatus(demanda, status)} disabled={busy || demanda.status === status} className="rounded-lg bg-slate-800 px-2.5 py-1.5 text-xs font-bold text-white hover:bg-slate-700 disabled:opacity-40">
                {status}
              </button>
            ))}
          </div>
        </div>
      ))}
    </div>
  )
}

function TextInput({ label, value, onChange, type = 'text', placeholder = '', required = false }) {
  return (
    <label className="block">
      <span className="text-sm font-bold text-white">{label}</span>
      <input required={required} type={type} value={value} onChange={(event) => onChange(event.target.value)} placeholder={placeholder} className="input mt-2 w-full rounded-xl" />
    </label>
  )
}

async function loadConsultorWorkspace() {
  const [engine, clientes, demandas] = await Promise.all([
    api.consultorEngine(),
    api.consultorClientes(),
    api.consultorDemandas(),
  ])
  return { engine, clientes, demandas }
}

const demandStatusOptions = ['aberta', 'em andamento', 'aguardando cliente', 'entregue', 'cancelada', 'atrasada']

function Memorias() {
  const { data, loading, error, refresh } = useAsyncData(() => api.memorias())
  const [form, setForm] = useState({ tipo: 'tese', titulo: '', descricao: '', contexto: '', estrategia: '', tags: '' })
  const [filters, setFilters] = useState({ termo: '', tipo: '' })
  const [selected, setSelected] = useState(null)
  const [editing, setEditing] = useState(null)
  const [busy, setBusy] = useState(false)
  const [actionError, setActionError] = useState('')
  const memorias = data?.items || []
  const filtered = memorias.filter((memoria) => {
    const q = filters.termo.toLowerCase()
    if (filters.tipo && memoria.tipo !== filters.tipo) return false
    if (!q) return true
    return [memoria.titulo, memoria.descricao, memoria.contexto, memoria.estrategia, ...(memoria.tags || [])].join(' ').toLowerCase().includes(q)
  })
  const tipos = ['orgao','concorrente','tese','vitoria','perda','risco','padrao','contrato','impugnacao','recurso']

  async function save(event) {
    event.preventDefault(); setBusy(true); setActionError('')
    try {
      const payload = { ...form, tags: String(form.tags || '').split(',').map((x) => x.trim()).filter(Boolean) }
      if (editing?.id) await api.memoriaAtualizar(editing.id, payload)
      else await api.memoriaRegistrar(payload)
      setForm({ tipo: 'tese', titulo: '', descricao: '', contexto: '', estrategia: '', tags: '' }); setEditing(null); refresh()
    } catch (err) { setActionError(err.message || 'Erro ao salvar memória') }
    finally { setBusy(false) }
  }
  function editMemoria(memoria) {
    setEditing(memoria); setSelected(memoria)
    setForm({ tipo: memoria.tipo || 'tese', titulo: memoria.titulo || '', descricao: memoria.descricao || '', contexto: memoria.contexto || '', estrategia: memoria.estrategia || '', tags: (memoria.tags || []).join(', ') })
  }
  async function archiveMemoria(memoria) {
    setBusy(true); setActionError('')
    try { await api.memoriaArquivar(memoria.id); if (selected?.id === memoria.id) setSelected(null); refresh() }
    catch (err) { setActionError(err.message || 'Erro ao arquivar memória') }
    finally { setBusy(false) }
  }
  return (
    <StateGate loading={loading} error={error} onRetry={refresh}>
      <div className="space-y-6">
        {actionError && <ErrorBox text={actionError} />}
        <Section title="Memórias" subtitle="Base viva de aprendizados, riscos, órgãos, teses e padrões úteis à operação." action={<button onClick={refresh} className="rounded-xl bg-slate-800 px-4 py-2 text-sm font-bold text-white hover:bg-slate-700"><RefreshCcw size={15} className="mr-2 inline" />Atualizar</button>}>
          <div className="grid gap-3 md:grid-cols-3">
            <input value={filters.termo} onChange={(e) => setFilters({ ...filters, termo: e.target.value })} placeholder="Filtrar por texto" className="input" />
            <select value={filters.tipo} onChange={(e) => setFilters({ ...filters, tipo: e.target.value })} className="input"><option value="">Todos os tipos</option>{tipos.map((t) => <option key={t} value={t}>{t}</option>)}</select>
            <MetricCard label="Filtradas" value={filtered.length} />
          </div>
        </Section>
        <div className="grid gap-6 xl:grid-cols-2">
          <Section title={editing ? 'Editar memória' : 'Registrar memória'} subtitle="Aprendizado operacional reutilizável">
            <form onSubmit={save} className="grid gap-3 md:grid-cols-2">
              <select value={form.tipo} onChange={(e) => setForm({ ...form, tipo: e.target.value })} className="input">{tipos.map((t) => <option key={t} value={t}>{t}</option>)}</select>
              <input required value={form.titulo} onChange={(e) => setForm({ ...form, titulo: e.target.value })} placeholder="Título" className="input" />
              <textarea required value={form.descricao} onChange={(e) => setForm({ ...form, descricao: e.target.value })} placeholder="Descrição" className="input md:col-span-2" />
              <textarea value={form.contexto} onChange={(e) => setForm({ ...form, contexto: e.target.value })} placeholder="Contexto" className="input md:col-span-2" />
              <textarea value={form.estrategia} onChange={(e) => setForm({ ...form, estrategia: e.target.value })} placeholder="Estratégia" className="input md:col-span-2" />
              <input value={form.tags} onChange={(e) => setForm({ ...form, tags: e.target.value })} placeholder="tags, separadas, por vírgula" className="input md:col-span-2" />
              <button disabled={busy || !form.titulo || !form.descricao} className="rounded-2xl bg-blue-600 px-4 py-3 font-black text-white disabled:opacity-60 md:col-span-2">{editing ? 'Atualizar memória' : 'Registrar memória'}</button>
              {editing && <button type="button" onClick={() => { setEditing(null); setForm({ tipo: 'tese', titulo: '', descricao: '', contexto: '', estrategia: '', tags: '' }) }} className="rounded-2xl bg-slate-800 px-4 py-3 font-black text-white md:col-span-2">Cancelar edição</button>}
            </form>
          </Section>
          <Section title="Memórias cadastradas" subtitle={`${filtered.length} registro(s) após filtros · ações Detalhe/Editar/Arquivar sempre visíveis`}>
            {!filtered.length ? <Empty text="Nenhuma memória encontrada." /> : <div className="space-y-3">{filtered.map((memoria) => (
              <div key={memoria.id} className="rounded-xl border border-slate-800 bg-slate-950/50 p-4">
                <div className="flex flex-wrap gap-2"><Badge value={memoria.tipo} />{(memoria.tags || []).map((tag) => <Badge key={tag} value={tag} />)}</div>
                <p className="mt-2 font-bold text-white">{memoria.titulo}</p><p className="mt-1 text-sm text-slate-400">{memoria.descricao}</p>
                <div className="crud-action-bar mt-3"><span className="crud-action-label">Ações</span><button onClick={() => setSelected(memoria)} className="crud-button">Detalhe</button><button onClick={() => editMemoria(memoria)} className="crud-button-primary">Editar</button><button onClick={() => archiveMemoria(memoria)} disabled={busy} className="crud-button disabled:opacity-60">Arquivar</button></div>
              </div>
            ))}</div>}
          </Section>
        </div>
        {selected && <Section title={`Detalhe: ${selected.titulo}`} subtitle={`ID ${selected.id}`} action={<button onClick={() => setSelected(null)} className="rounded-xl bg-slate-800 px-3 py-2 text-sm font-bold text-white">Fechar</button>}><pre className="max-h-96 overflow-auto whitespace-pre-wrap rounded-2xl border border-slate-800 bg-slate-950 p-5 text-xs text-slate-300">{JSON.stringify(selected, null, 2)}</pre></Section>}
      </div>
    </StateGate>
  )
}

function Badge({ value, map = {} }) {
  const cls = map[value] || 'bg-slate-700/60 text-slate-200 ring-1 ring-white/10'
  return <span className={`badge ${cls}`}>{value}</span>
}

function Empty({ text }) {
  return (
    <div className="flex min-h-32 flex-col items-center justify-center rounded-2xl border border-dashed border-white/10 bg-slate-950/35 px-5 py-8 text-center text-sm text-slate-500">
      <Eye size={18} className="mb-2 text-slate-400" /> {text}
    </div>
  )
}

async function openExport(url, filename) {
  const response = await fetch(url)
  if (!response.ok) {
    const text = await response.text().catch(() => '')
    throw new Error(`Erro ${response.status} ao exportar: ${text || response.statusText}`)
  }
  const blob = await response.blob()
  const objectUrl = URL.createObjectURL(blob)
  const opened = window.open(objectUrl, '_blank', 'noopener,noreferrer')
  const link = document.createElement('a')
  link.href = objectUrl
  link.download = filename
  if (!opened) link.click()
  setTimeout(() => URL.revokeObjectURL(objectUrl), 30000)
}

function nextCaseAction(caso) {
  if (caso.acao_recomendada) return caso.acao_recomendada
  const actions = {
    prospecção: 'Validar aderência, prazo e margem; decidir se vira análise formal.',
    análise: 'Fechar diagnóstico do edital, riscos de habilitação e decisão go/no-go.',
    impugnação: 'Protocolar ou acompanhar impugnação e controlar resposta do órgão.',
    habilitação: 'Blindar documentos, atestados, certidões e vínculos técnicos.',
    disputa: 'Preparar estratégia de lance, exequibilidade e reação a concorrentes.',
    recurso: 'Mapear falhas objetivas, intenção de recurso, razões e contrarrazões.',
    homologação: 'Monitorar adjudicação/homologação e preparar documentos finais.',
    contrato: 'Revisar obrigações, garantias, prazos, sanções e assinatura.',
    execução: 'Controlar entrega, medição, recebimento e riscos de penalidade.',
    pagamento: 'Acompanhar liquidação, nota fiscal e eventual cobrança administrativa.',
    encerrado: 'Registrar aprendizado, vitória/perda e memória operacional.',
  }
  return actions[caso.fase_atual] || 'Definir próximo movimento operacional.'
}

function recommendedOpportunityAction(item) {
  if (item.caso_id) return 'Acompanhar caso vivo e checklist documental.'
  if (item.classificacao_triagem === 'prioridade_alta') return 'Priorizar análise do edital e criar caso.'
  if ((item.score_preliminar || 0) >= 70) return 'Triar imediatamente; alta chance de virar caso.'
  if ((item.score_preliminar || 0) >= 60) return 'Validar aderência técnica e prazo antes de decidir.'
  return 'Monitorar ou descartar se não houver aderência clara.'
}

function humanizeAction(value) {
  if (!value) return 'Ação registrada'
  return value.replaceAll('_', ' ').replace(/\b\w/g, (char) => char.toUpperCase())
}

function activityDetail(item) {
  const detalhes = item?.detalhes || {}
  return detalhes.titulo || detalhes.orgao || detalhes.objeto || detalhes.arquivo || item.id_relacionado || 'Registro operacional sem detalhe adicional.'
}

function splitLines(value) {
  return String(value || '').split(/\n|;/).map((item) => item.trim()).filter(Boolean)
}

function formatMoney(value) {
  if (!value) return '—'
  return new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL', maximumFractionDigits: 0 }).format(value)
}

function filterOperationalItems(items, filters, kind) {
  const orgao = (filters.orgao || '').casefold?.() || (filters.orgao || '').toLowerCase()
  const uf = (filters.uf || '').toLowerCase()
  const status = (filters.status || '').toLowerCase()
  const score = Number(filters.score || 0)
  const perfil = (filters.perfil || '').toLowerCase()
  return items.filter((item) => {
    const itemOrgao = (item.orgao || '').toLowerCase()
    const itemUf = (item.uf || '').toLowerCase()
    const itemStatus = (item.status || item.classificacao_triagem || '').toLowerCase()
    const itemScore = Number(item.score_estrategico ?? item.score_preliminar ?? 0)
    if (orgao && !itemOrgao.includes(orgao)) return false
    if (uf && itemUf !== uf) return false
    if (status && itemStatus !== status) return false
    if (score && itemScore < score) return false
    if (perfil) {
      const text = `${kind} ${item.modalidade || ''} ${item.objeto || ''} ${item.fase_atual || ''}`.toLowerCase()
      if (perfil === 'consultor' && !['caso', 'cliente'].includes(kind) && !text.includes('consult')) return false
      if (perfil === 'comprador' && !text.includes('órgão') && !text.includes('orgao') && !item.orgao) return false
    }
    return true
  })
}

function isActionableText(text) {
  const value = (text || '').toLowerCase()
  return ['criar caso', 'gerar peça', 'gerar peca', 'registrar memória', 'registrar memoria', 'analisar edital', 'consultar órgão', 'consultar orgao', 'demanda consultor', 'checklist', 'impugnação', 'impugnacao', 'recurso'].some((term) => value.includes(term))
}

function formatDate(value) {
  if (!value) return '—'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return new Intl.DateTimeFormat('pt-BR', { dateStyle: 'short', timeStyle: 'short' }).format(date)
}

function normalizeNavigation(profile) {
  const perfil = profile?.perfil_atual === 'consultor' ? 'consultor' : 'fornecedor'
  return (enterpriseNavigation[perfil] || enterpriseNavigation.fornecedor).map((item) => ({
    ...item,
    icon: iconMap[item.icon?.name] || item.icon || Database,
  }))
}


function Concorrentes() {
  const { data, loading, error, refresh } = useAsyncData(() => Promise.all([api.concorrentes(), api.concorrentesAnalise()]).then(([lista, analise]) => ({ lista, analise })), [])
  const emptyForm = { nome: '', cnpj: '', segmento: '', uf: '', observacoes_estrategicas: '' }
  const [form, setForm] = useState(emptyForm)
  const [eventForm, setEventForm] = useState({ concorrente_id: '', tipo: 'participou', descricao: '', orgao: '', caso_id: '' })
  const [filters, setFilters] = useState({ termo: '', uf: '', risco: '' })
  const [selected, setSelected] = useState(null)
  const [editing, setEditing] = useState(null)
  const [saving, setSaving] = useState(false)
  const [actionError, setActionError] = useState('')
  const concorrentes = data?.lista?.concorrentes || []
  const analise = data?.analise || {}
  const filtered = concorrentes.filter((c) => {
    const q = filters.termo.toLowerCase()
    if (filters.uf && (c.uf || '').toLowerCase() !== filters.uf.toLowerCase()) return false
    if (filters.risco && (c.risco_operacional || '') !== filters.risco) return false
    if (!q) return true
    return [c.nome, c.cnpj, c.segmento, c.observacoes_estrategicas, ...(c.orgaos_relacionados || [])].join(' ').toLowerCase().includes(q)
  })

  async function saveConcorrente(event) {
    event.preventDefault(); setSaving(true); setActionError('')
    try {
      if (editing?.id) await api.concorrenteAtualizar(editing.id, form)
      else await api.concorrentesRegistrar(form)
      setForm(emptyForm); setEditing(null); refresh()
    } catch (err) { setActionError(err.message || 'Erro ao salvar concorrente') }
    finally { setSaving(false) }
  }
  function editConcorrente(c) { setEditing(c); setSelected(c); setForm({ nome: c.nome || '', cnpj: c.cnpj || '', segmento: c.segmento || '', uf: c.uf || '', observacoes_estrategicas: c.observacoes_estrategicas || '' }) }
  async function archiveConcorrente(c) { setSaving(true); setActionError(''); try { await api.concorrenteArquivar(c.id); if (selected?.id === c.id) setSelected(null); refresh() } catch (err) { setActionError(err.message || 'Erro ao arquivar concorrente') } finally { setSaving(false) } }
  async function saveEvento(event) {
    event.preventDefault(); if (!eventForm.concorrente_id) return; setSaving(true); setActionError('')
    try { await api.concorrenteRegistrarEvento(eventForm.concorrente_id, { tipo: eventForm.tipo, descricao: eventForm.descricao, orgao: eventForm.orgao, caso_id: eventForm.caso_id || null }); setEventForm({ concorrente_id: eventForm.concorrente_id, tipo: 'participou', descricao: '', orgao: '', caso_id: '' }); refresh() }
    catch (err) { setActionError(err.message || 'Erro ao registrar evento') }
    finally { setSaving(false) }
  }

  return (
    <div className="space-y-6">
      {actionError && <ErrorBox text={actionError} />}
      <StateGate loading={loading} error={error} onRetry={refresh}>
        <Section title="Concorrentes" subtitle="Mapa competitivo para acompanhar rivais, padrões de atuação e riscos." action={<button onClick={refresh} className="rounded-xl bg-slate-800 px-4 py-2 text-sm font-bold text-white hover:bg-slate-700"><RefreshCcw size={15} className="mr-2 inline" />Atualizar</button>}>
          <div className="grid gap-4 md:grid-cols-4"><MetricCard label="Concorrentes" value={analise.total_concorrentes || concorrentes.length} /><MetricCard label="Eventos" value={analise.total_eventos || 0} /><MetricCard label="Frequência total" value={analise.dashboard?.frequencia_total || 0} tone="warning" /><MetricCard label="Alto/crítico" value={analise.risco_operacional?.alto_ou_critico || 0} tone="danger" /></div>
          <div className="mt-4 grid gap-3 md:grid-cols-3"><input value={filters.termo} onChange={(e) => setFilters({ ...filters, termo: e.target.value })} placeholder="Filtrar por nome/CNPJ/órgão" className="input" /><input value={filters.uf} onChange={(e) => setFilters({ ...filters, uf: e.target.value.toUpperCase() })} placeholder="UF" className="input" /><select value={filters.risco} onChange={(e) => setFilters({ ...filters, risco: e.target.value })} className="input"><option value="">Todos os riscos</option>{['baixo','médio','alto','crítico','desconhecido'].map((r) => <option key={r} value={r}>{r}</option>)}</select></div>
        </Section>
        <div className="grid gap-6 xl:grid-cols-2">
          <Section title="Ranking de concorrentes" subtitle={`${filtered.length} registro(s) após filtros · ações Detalhe/Editar/Arquivar sempre visíveis`}>
            {!filtered.length ? <Empty text="Nenhum concorrente registrado ainda." /> : <div className="space-y-3">{filtered.map((c) => <div key={c.id} className="rounded-xl border border-slate-800 bg-slate-950/50 p-4"><div className="flex flex-wrap gap-2"><Badge value={c.uf || 'UF'} /><Badge value={c.segmento || 'segmento'} /><Badge value={c.risco_operacional || 'risco'} />{c.metadata?.arquivado && <Badge value="arquivado" />}</div><p className="mt-2 font-bold text-white">{c.nome}</p><p className="mt-1 text-sm text-slate-400">{c.cnpj || 'Sem CNPJ'} · freq. {c.frequencia || 0} · score {c.score_competitividade ?? '—'}</p><p className="mt-1 text-xs text-slate-500">Órgãos: {(c.orgaos_relacionados || []).join(', ') || '—'}</p><div className="crud-action-bar mt-3"><span className="crud-action-label">Ações</span><button onClick={() => setSelected(c)} className="crud-button">Detalhe</button><button onClick={() => editConcorrente(c)} className="crud-button-primary">Editar</button><button onClick={() => archiveConcorrente(c)} disabled={saving} className="crud-button disabled:opacity-60">Arquivar</button></div></div>)}</div>}
          </Section>
          <Section title="Análise estratégica" subtitle="Órgãos disputados, padrões de risco e preço"><div className="grid gap-4 md:grid-cols-3"><MiniList title="Órgãos" items={analise.orgaos_mais_disputados || []} /><MiniList title="Riscos" items={analise.padroes_risco || []} /><MiniList title="Preço" items={analise.padroes_preco || []} /></div></Section>
        </div>
      </StateGate>
      <div className="grid gap-6 xl:grid-cols-2">
        <Section title={editing ? 'Editar concorrente' : 'Registrar concorrente'} subtitle="Cadastro estratégico para apoiar disputa, recurso e análise de mercado.">
          <form onSubmit={saveConcorrente} className="grid gap-3 md:grid-cols-2"><input required value={form.nome} onChange={(e) => setForm({ ...form, nome: e.target.value })} placeholder="Nome" className="input" /><input value={form.cnpj} onChange={(e) => setForm({ ...form, cnpj: e.target.value })} placeholder="CNPJ" className="input" /><input value={form.segmento} onChange={(e) => setForm({ ...form, segmento: e.target.value })} placeholder="Segmento" className="input" /><input value={form.uf} onChange={(e) => setForm({ ...form, uf: e.target.value.toUpperCase() })} placeholder="UF" className="input" /><textarea value={form.observacoes_estrategicas} onChange={(e) => setForm({ ...form, observacoes_estrategicas: e.target.value })} placeholder="Observações estratégicas" className="input md:col-span-2" /><button disabled={saving || !form.nome} className="rounded-2xl bg-blue-600 px-4 py-3 font-black text-white disabled:opacity-60 md:col-span-2">{editing ? 'Atualizar' : 'Registrar'}</button>{editing && <button type="button" onClick={() => { setEditing(null); setForm(emptyForm) }} className="rounded-2xl bg-slate-800 px-4 py-3 font-black text-white md:col-span-2">Cancelar edição</button>}</form>
        </Section>
        <Section title="Registrar evento" subtitle="Histórico competitivo: venceu, perdeu, inabilitou, recurso, preço baixo etc.">
          <form onSubmit={saveEvento} className="grid gap-3 md:grid-cols-2"><select required value={eventForm.concorrente_id} onChange={(e) => setEventForm({ ...eventForm, concorrente_id: e.target.value })} className="input md:col-span-2"><option value="">Selecione o concorrente</option>{concorrentes.map((c) => <option key={c.id} value={c.id}>{c.nome}</option>)}</select><select value={eventForm.tipo} onChange={(e) => setEventForm({ ...eventForm, tipo: e.target.value })} className="input">{['participou','venceu','perdeu','inabilitado','recurso','impugnação','abandono','comportamento agressivo','preço muito baixo','padrão documental','vínculo com órgão','vínculo com caso'].map((tipo) => <option key={tipo} value={tipo}>{tipo}</option>)}</select><input value={eventForm.orgao} onChange={(e) => setEventForm({ ...eventForm, orgao: e.target.value })} placeholder="Órgão" className="input" /><input value={eventForm.caso_id} onChange={(e) => setEventForm({ ...eventForm, caso_id: e.target.value })} placeholder="Caso ID" className="input md:col-span-2" /><textarea required value={eventForm.descricao} onChange={(e) => setEventForm({ ...eventForm, descricao: e.target.value })} placeholder="Descrição do evento" className="input md:col-span-2" /><button disabled={saving || !eventForm.concorrente_id} className="rounded-2xl bg-emerald-600 px-4 py-3 font-black text-white disabled:opacity-60 md:col-span-2">Registrar evento</button></form>
        </Section>
      </div>
      {selected && <Section title={`Detalhe do concorrente: ${selected.nome}`} subtitle={`ID ${selected.id}`} action={<button onClick={() => setSelected(null)} className="rounded-xl bg-slate-800 px-3 py-2 text-sm font-bold text-white">Fechar</button>}><pre className="max-h-96 overflow-auto whitespace-pre-wrap rounded-2xl border border-slate-800 bg-slate-950 p-5 text-xs text-slate-300">{JSON.stringify(selected, null, 2)}</pre></Section>}
    </div>
  )
}


async function loadCentralOperacional() {
  const [resumo, oportunidades, casos, alertas, notificacoes, triagem, radar, audit, consultor, leads, followups, documental, documentos, fornecedor, fornecedorRegistros, concorrencia, memorias] = await Promise.all([
    api.dashboardResumo(),
    api.dashboardOportunidades(),
    api.dashboardCasos(),
    api.dashboardAlertas(),
    api.notificacoesEngine().catch((err) => ({ erro: err.message })),
    api.triagemFila().catch((err) => ({ erro: err.message, fila: [] })),
    api.radarOportunidades().catch((err) => ({ erro: err.message, oportunidades: [] })),
    api.auditLogs(16),
    api.consultorFullDashboard().catch((err) => ({ erro: err.message })),
    api.consultorFullLeads().catch((err) => ({ erro: err.message, itens: [] })),
    api.consultorFullFollowups().catch((err) => ({ erro: err.message, itens: [] })),
    api.documentalDashboard().catch((err) => ({ erro: err.message })),
    api.documentalDocumentos({ limit: 300 }).catch((err) => ({ erro: err.message, itens: [] })),
    api.fornecedorFullDashboard().catch((err) => ({ erro: err.message })),
    api.fornecedorFullRegistros('', 300).catch((err) => ({ erro: err.message, itens: [] })),
    api.concorrentesAnalise().catch((err) => ({ erro: err.message })),
    api.dashboardMemorias().catch((err) => ({ erro: err.message, memorias: [], itens: [] })),
  ])
  return { resumo, oportunidades, casos, alertas, notificacoes, triagem, radar, audit, consultor, leads, followups, documental, documentos, fornecedor, fornecedorRegistros, concorrencia, memorias }
}

function CentralOperacional({ profile, onNavigate }) {
  const { data, loading, error, refresh } = useAsyncData(loadCentralOperacional)
  const [selected, setSelected] = useState(null)
  const [centralBusy, setCentralBusy] = useState(false)
  const [centralFeedback, setCentralFeedback] = useState('')
  const [centralList, setCentralList] = useState(null)
  const [centralNote, setCentralNote] = useState('')
  const [centralResponsible, setCentralResponsible] = useState('')
  const [centralRisk, setCentralRisk] = useState('')
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  const daysUntil = (value) => {
    if (!value) return null
    const date = new Date(value)
    if (Number.isNaN(date.getTime())) return null
    date.setHours(0, 0, 0, 0)
    return Math.ceil((date - today) / 86400000)
  }
  const norm = (value) => String(value || '').trim().toLowerCase()
  const alertas = data?.alertas?.itens || data?.alertas?.alertas || []
  const casos = data?.casos?.itens || data?.casos?.casos || []
  const oportunidades = data?.oportunidades?.itens || data?.oportunidades?.top_5 || []
  const triagem = data?.triagem?.fila || data?.triagem?.itens || data?.triagem?.oportunidades || []
  const radar = data?.radar?.oportunidades || data?.radar?.itens || []
  const leads = data?.leads?.itens || []
  const followups = data?.followups?.itens || []
  const docs = data?.documentos?.itens || []
  const fornecedorRegistros = data?.fornecedorRegistros?.itens || []
  const memoriasOperacionais = data?.memorias?.memorias || data?.memorias?.itens || data?.memorias?.recentes || []
  const financeiroPendentes = fornecedorRegistros.filter((item) => item.tipo === 'financeiro' && ['pendente', 'atrasado', 'em atraso', 'a receber'].includes(norm(item.status)))
  const riscosFornecedor = fornecedorRegistros.filter((item) => item.tipo === 'risco' && norm(item.status) !== 'arquivado')
  const oportunidadesReais = [...oportunidades, ...triagem, ...radar].filter((item, index, arr) => (item.id || item.oportunidade_id) && arr.findIndex((x) => (x.id || x.oportunidade_id) === (item.id || item.oportunidade_id)) === index)
  const memoriaParaItem = (item) => memoriasOperacionais.find((mem) => {
    const texto = [mem.titulo, mem.conteudo, mem.resumo, mem.orgao, mem.concorrente, mem.tags].join(' ').toLowerCase()
    return [item?.titulo, item?.detalhe, item?.fonte, item?.tipo].filter(Boolean).some((term) => texto.includes(norm(term)))
  })
  const enrichCentralContext = (item) => {
    const memoria = memoriaParaItem(item)
    return {
      ...item,
      motivo: item.motivo || item.detalhe || 'Sinal operacional consolidado por dados reais da plataforma.',
      consequencia: item.consequencia || (item.impacto === 'crítico' ? 'Pode bloquear habilitação, prazo, receita ou avanço do caso se ninguém agir.' : 'Pode gerar atraso, perda de ritmo ou retrabalho se ficar sem responsável.'),
      prazo: item.prazo || (item.tipo?.includes('certidão') ? 'antes da próxima habilitação' : item.tipo?.includes('follow') || item.tipo?.includes('cliente') ? 'hoje' : 'próximo bloco operacional'),
      responsavel: item.responsavel || item.usuario_responsavel || 'definir responsável',
      historico: item.historico || memoria?.titulo || memoria?.resumo || 'Sem histórico específico vinculado; registrar observação ao agir.',
      memoria,
    }
  }
  const prioridades = useMemo(() => {
    const items = []
    alertas.filter((item) => !item.lido).forEach((item) => items.push({ id: `alerta-${item.id}`, entityId: item.id, eixo: 'operacional', tipo: 'prazo crítico', titulo: item.titulo || item.mensagem || 'Alerta crítico', detalhe: item.acao_recomendada || item.mensagem || 'Alerta não lido exige decisão.', urgencia: item.severidade === 'critica' ? 98 : item.severidade === 'alta' ? 88 : 70, impacto: item.severidade === 'critica' ? 'crítico' : 'alto', fonte: 'Alertas', acao: 'Abrir alerta, confirmar responsável e registrar encaminhamento.' }))
    casos.filter((caso) => (caso.score_estrategico || 0) >= 70 || caso.acao_recomendada || caso.risco_concorrencial).forEach((caso) => items.push({ id: `caso-${caso.id}`, entityId: caso.id, eixo: 'estratégico', tipo: 'caso crítico', titulo: caso.orgao || 'Caso crítico', detalhe: nextCaseAction(caso), urgencia: Math.min(98, Number(caso.score_estrategico || 70)), impacto: caso.risco_concorrencial ? 'crítico' : 'alto', fonte: 'Casos', acao: 'Revisar fase, risco concorrencial e próxima peça/manifestação.' }))
    oportunidades.filter((item) => item.classificacao_triagem === 'prioridade_alta' || Number(item.score_preliminar || 0) >= 70).forEach((item) => items.push({ id: `opp-${item.id || item.oportunidade_id}`, entityId: item.id || item.oportunidade_id, relatedItems: [item], eixo: 'estratégico', tipo: 'oportunidade urgente', titulo: item.orgao || item.titulo || 'Oportunidade', detalhe: recommendedOpportunityAction(item), urgencia: Math.min(96, Number(item.score_preliminar || item.score || 75)), impacto: 'alto', fonte: 'Radar / Triagem', acao: 'Decidir participação, checar documentos e risco concorrencial.' }))
    followups.forEach((item) => { const prazo = daysUntil(item.data || item.follow_up_em || item.prazo); if (prazo !== null && prazo < 0) items.push({ id: `follow-${item.id}`, entityId: item.id, eixo: 'comercial', tipo: 'cliente frio', titulo: item.titulo || item.cliente_nome || item.empresa || 'Follow-up vencido', detalhe: `${Math.abs(prazo)} dia(s) de atraso no contato.`, urgencia: 92, impacto: 'alto', fonte: 'CRM / Follow-ups', acao: 'Retomar contato hoje e registrar nova próxima ação.' }) })
    leads.forEach((lead) => { const prazo = daysUntil(lead.follow_up_em); const risco = Number(lead.risco_churn || 0); if (prazo !== null && prazo < -7) items.push({ id: `lead-frio-${lead.id}`, entityId: lead.id, eixo: 'comercial', tipo: 'cliente frio', titulo: lead.empresa || lead.nome || 'Cliente frio', detalhe: `Sem follow-up há ${Math.abs(prazo)} dia(s).`, urgencia: 86, impacto: 'alto', fonte: 'CRM / Leads', acao: 'Reativar relacionamento e atualizar etapa do pipeline.' }); if (risco >= 60) items.push({ id: `lead-churn-${lead.id}`, entityId: lead.id, eixo: 'comercial', tipo: 'risco churn', titulo: lead.empresa || lead.nome || 'Cliente em risco', detalhe: `Risco churn ${risco}/100.`, urgencia: Math.min(97, risco + 10), impacto: risco >= 80 ? 'crítico' : 'alto', fonte: 'CRM / Carteira', acao: 'Revisar entrega, pendências e plano de retenção.' }) })
    docs.forEach((doc) => { const prazo = daysUntil(doc.validade); if (norm(doc.status).includes('vencido') || (prazo !== null && prazo < 0)) items.push({ id: `doc-vencido-${doc.id}`, entityId: doc.id, eixo: 'documental', tipo: 'certidão vencida', titulo: doc.titulo || 'Documento vencido', detalhe: `${doc.empresa_nome || doc.cliente_nome || 'Empresa'} · vencido${prazo !== null ? ` há ${Math.abs(prazo)} dia(s)` : ''}.`, urgencia: 99, impacto: 'crítico', fonte: 'Documental 360°', acao: 'Regularizar antes de habilitação ou protocolo.' }); else if (prazo !== null && prazo <= 30) items.push({ id: `doc-vencendo-${doc.id}`, entityId: doc.id, eixo: 'documental', tipo: 'certidão vencendo', titulo: doc.titulo || 'Documento vencendo', detalhe: `${doc.empresa_nome || doc.cliente_nome || 'Empresa'} · vence em ${prazo} dia(s).`, urgencia: 84, impacto: 'alto', fonte: 'Documental 360°', acao: 'Iniciar renovação e atualizar repositório documental.' }) })
    const pagamentos = financeiroPendentes.length || Number(data?.fornecedor?.pagamentos_pendentes || 0)
    if (financeiroPendentes.length) financeiroPendentes.slice(0, 4).forEach((fin) => items.push({ id: `financeiro-${fin.id}`, entityId: fin.id, eixo: 'financeiro', tipo: 'cobrança pendente', titulo: fin.titulo || 'Cobrança pendente', detalhe: `${fin.orgao || fin.cliente_nome || 'Fornecedor'} · ${fin.status || 'pendente'} · ${formatMoney(fin.valor || 0)}`, urgencia: 82, impacto: 'alto', fonte: 'Fornecedor Full / Financeiro', acao: 'Conferir contrato, medição, nota fiscal e cobrança.' }))
    else if (pagamentos) items.push({ id: 'financeiro-pagamentos', eixo: 'financeiro', tipo: 'cobrança pendente', titulo: `${pagamentos} pagamento(s) pendente(s)`, detalhe: 'Há pendências financeiras agregadas no dashboard. Abra a lista financeira filtrada para escolher o registro.', urgencia: 82, impacto: 'alto', fonte: 'Fornecedor Full / Financeiro', acao: 'Abrir lista filtrada de financeiros pendentes.', relatedItems: fornecedorRegistros.filter((i) => i.tipo === 'financeiro') })
    const riscoConcorrencial = Number(data?.resumo?.totais?.casos_com_risco_concorrencial || 0) || casos.filter((caso) => caso.risco_concorrencial).length
    if (casos.filter((caso) => caso.risco_concorrencial).length) casos.filter((caso) => caso.risco_concorrencial).slice(0, 4).forEach((caso) => items.push({ id: `risco-caso-${caso.id}`, entityId: caso.id, eixo: 'estratégico', tipo: 'risco concorrencial', titulo: caso.orgao || caso.objeto || 'Caso com risco concorrencial', detalhe: 'Concorrente, preço, habilitação ou estratégia pode afetar resultado.', urgencia: 89, impacto: 'alto', fonte: 'Casos / Concorrentes', acao: 'Mapear falhas de concorrentes e preparar manifestação/recurso se cabível.' }))
    else if (riscoConcorrencial) items.push({ id: 'risco-concorrencial', eixo: 'estratégico', tipo: 'risco concorrencial', titulo: `${riscoConcorrencial} caso(s) com risco concorrencial`, detalhe: 'Indicador agregado sem caso individual no resumo atual. Abra a lista de casos filtrada para escolher o registro.', urgencia: 89, impacto: 'alto', fonte: 'Casos / Concorrentes', acao: 'Abrir lista filtrada de casos com risco concorrencial.', relatedItems: casos.filter((caso) => caso.risco_concorrencial) })
    return items.sort((a, b) => b.urgencia - a.urgencia).slice(0, 18).map(enrichCentralContext)
  }, [data, financeiroPendentes, fornecedorRegistros, memoriasOperacionais])
  const porEixo = ['comercial', 'operacional', 'documental', 'financeiro', 'estratégico'].map((eixo) => ({ eixo, total: prioridades.filter((item) => item.eixo === eixo).length }))
  const timeline = [
    ...prioridades.slice(0, 10).map((item, index) => ({ hora: index < 3 ? 'agora' : index < 6 ? 'hoje' : 'próximo bloco', titulo: item.titulo, tipo: item.tipo, fonte: item.fonte, urgencia: item.urgencia })),
    ...(data?.audit?.logs || []).slice(0, 6).map((log) => ({ hora: formatDate(log.timestamp || log.criado_em), titulo: log.acao || 'Evento registrado', tipo: log.modulo || 'atividade', fonte: 'Audit Log', urgencia: 40 })),
  ]
  function openCentralList(title, items, fallbackText = 'Nenhum registro real encontrado para este filtro.') {
    setCentralList({ title, items: (items || []).filter(Boolean), fallbackText })
    setCentralFeedback('Lista filtrada aberta. Escolha um registro real para executar a ação no módulo de origem.')
  }
  function openRelated(item) {
    if (item?.relatedItems?.length) return openCentralList(item.titulo || 'Registros relacionados', item.relatedItems)
    if (item?.id?.startsWith('financeiro-') || item?.tipo?.includes('cobrança')) return openCentralList('Financeiros pendentes', financeiroPendentes.length ? financeiroPendentes : fornecedorRegistros.filter((i) => i.tipo === 'financeiro'))
    if (item?.id?.startsWith('risco-') || item?.tipo?.includes('risco')) return openCentralList('Casos/riscos relacionados', casos.filter((caso) => caso.risco_concorrencial || Number(caso.score_estrategico || 0) >= 70))
    if (item?.id?.startsWith('opp-') || item?.tipo?.includes('oportunidade')) return openCentralList('Oportunidades urgentes', oportunidadesReais)
    if (item?.tipo?.includes('certidão')) return openCentralList('Documentos críticos', docs.filter((doc) => norm(doc.status).includes('venc') || ['alta','critica','crítica'].includes(norm(doc.criticidade))))
    if (item?.tipo?.includes('cliente')) return openCentralList('Clientes/leads relacionados', leads)
    return openCentralList(item?.titulo || 'Registros relacionados', [])
  }
  function shapeCentralItem(item, source = 'Central Operacional') {
    const realId = item?.id || item?.oportunidade_id || ''
    const title = String(source || '').toLowerCase()
    let prefix = ''
    if (title.includes('financeiro') || item?.tipo === 'financeiro') prefix = 'financeiro-'
    else if (title.includes('document') || title.includes('certid')) prefix = 'doc-'
    else if (title.includes('cliente') || title.includes('lead')) prefix = 'lead-'
    else if (title.includes('caso') || title.includes('risco')) prefix = 'caso-'
    else if (title.includes('oportunidade') || item?.oportunidade_id) prefix = 'opp-'
    return { ...item, id: prefix && realId ? `${prefix}${realId}` : realId, entityId: realId, tipo: item?.tipo || item?.classificacao_triagem || 'registro', titulo: item?.titulo || item?.orgao || item?.objeto || item?.empresa || 'Registro relacionado', detalhe: item?.detalhe || item?.observacoes || item?.objeto || item?.status || 'Registro real vinculado à ação filtrada.', acao: 'Use as ações do detalhe ou abra o módulo de origem para edição completa.', fonte: source }
  }
  async function centralAction(item, action) {
    if (!item?.id) return openRelated(item)
    const rawId = item.entityId || String(item.id).replace(/^[^-]+-/, '').replace(/^(frio|churn|vencido|vencendo|caso)-/, '')
    const contextoOperacional = {
      origem: 'Central Operacional',
      acao: action,
      entidade_relacionada: rawId,
      tipo: item.tipo,
      eixo: item.eixo,
      fonte: item.fonte,
      motivo: item.motivo || item.detalhe || item.tipo,
      impacto: item.impacto,
      urgencia: item.urgencia,
      risco: centralRisk || item.risco || item.impacto || '',
      consequencia: item.consequencia || 'risco operacional se não tratado',
      historico_resumido: item.historico || 'Ação iniciada pela Central Operacional sem histórico anterior explícito.',
      proxima_acao: item.acao || 'acompanhar',
      responsavel: centralResponsible || item.responsavel || 'definir responsável',
      observacao_operador: centralNote || '',
    }
    const obs = centralNote || `Ação ${action} executada pela Central Operacional. Motivo: ${contextoOperacional.motivo}. Impacto: ${contextoOperacional.impacto || 'operacional'}. Consequência: ${contextoOperacional.consequencia}. Responsável: ${contextoOperacional.responsavel}. Origem: ${contextoOperacional.origem}. Próximo passo: ${contextoOperacional.proxima_acao}. Histórico: ${contextoOperacional.historico_resumido}.`
    const payloadContexto = { contexto_operacional: contextoOperacional, historico_resumido: contextoOperacional.historico_resumido, origem: 'central_operacional' }
    const responsavelPatch = centralResponsible ? { responsavel: centralResponsible } : {}
    const riscoPatch = centralRisk ? { risco_operacional: centralRisk, risco: centralRisk } : {}
    setCentralBusy(true); setCentralFeedback('')
    try {
      if (item.id.startsWith('alerta-')) action === 'arquivar' ? await api.arquivarAlerta(rawId) : await api.marcarAlertaLido(rawId)
      else if (item.id.startsWith('follow-')) await api.consultorFullAtualizarFollowup(rawId, { status: action === 'arquivar' ? 'arquivado' : action === 'concluir' ? 'concluido' : 'em andamento', resultado: obs, payload: payloadContexto, ...responsavelPatch })
      else if (item.id.startsWith('lead-')) {
        if (action === 'arquivar') await api.consultorFullAtualizarLead(rawId, { status: 'perdido', pipeline_etapa: 'Operação', observacoes: obs, payload: payloadContexto, ...responsavelPatch, ...riscoPatch })
        else await api.consultorFullAtualizarLead(rawId, { status: action === 'concluir' ? 'ganho' : 'contato', pipeline_etapa: action === 'concluir' ? 'Cliente' : 'Diagnóstico', observacoes: obs, payload: payloadContexto, ...responsavelPatch, ...riscoPatch })
      }
      else if (item.id.startsWith('doc-')) await api.documentalAtualizar(rawId, { status: action === 'arquivar' ? 'arquivado' : action === 'concluir' ? 'válido' : 'pendente', observacoes: obs, payload: payloadContexto, ...riscoPatch })
      else if (item.id.startsWith('caso-') || item.id.startsWith('risco-caso-')) await api.atualizarFaseCaso(rawId, { fase_atual: action === 'concluir' ? 'encerrado' : 'análise', status: action === 'arquivar' ? 'arquivado' : action === 'concluir' ? 'encerrado' : 'ativo', descricao: obs, aprendizado_operacional: `Contexto persistente registrado pela Central: ${contextoOperacional.historico_resumido}`, ...responsavelPatch, ...riscoPatch })
      else if (item.id.startsWith('financeiro-')) await api.fornecedorFullAtualizar(rawId, { status: action === 'arquivar' ? 'arquivado' : action === 'concluir' ? 'concluido' : 'em andamento', observacoes: obs, payload: payloadContexto, ...responsavelPatch, ...riscoPatch })
      else return openRelated(item)
      setCentralFeedback(action === 'arquivar' ? 'Registro arquivado/baixado logicamente com contexto.' : action === 'concluir' ? 'Prioridade resolvida/atualizada com histórico.' : 'Status alterado pela Central Operacional com observação contextual.')
      setCentralNote(''); setCentralResponsible(''); setCentralRisk('')
      refresh()
    } catch (err) { setCentralFeedback(err.message || 'Não foi possível executar a ação rápida.') }
    finally { setCentralBusy(false) }
  }
  const quickActions = [
    { label: 'Retomar cliente frio', items: prioridades.filter((item) => item.tipo?.includes('cliente') || item.eixo === 'comercial') },
    { label: 'Regularizar certidão', items: prioridades.filter((item) => item.tipo?.includes('certidão') || item.eixo === 'documental') },
    { label: 'Destravar proposta', items: oportunidadesReais },
    { label: 'Conferir cobrança', items: financeiroPendentes.length ? financeiroPendentes : fornecedorRegistros.filter((item) => item.tipo === 'financeiro') },
    { label: 'Analisar risco concorrencial', items: casos.filter((caso) => caso.risco_concorrencial || Number(caso.score_estrategico || 0) >= 70) },
    { label: 'Decidir oportunidade urgente', items: oportunidadesReais },
  ]
  const focoAgora = prioridades[0]
  return (
    <StateGate loading={loading} error={error} onRetry={refresh}>
      <div className="space-y-6">
        {centralFeedback && <div className="rounded-2xl border border-emerald-400/25 bg-emerald-500/10 p-4 text-sm font-bold text-emerald-100">{centralFeedback}</div>}
        <FirstStepsGuide profile={profile} onNavigate={onNavigate} />
        <GuidedWorkflow profile={profile} onNavigate={onNavigate} />
        <Section title="Central Operacional Enterprise" subtitle="Responde o que precisa da sua atenção agora — comercial, operacional, documental, financeiro e estratégico no mesmo lugar." action={<button onClick={refresh} className="rounded-xl bg-slate-800 px-4 py-2 text-sm font-bold text-white hover:bg-slate-700"><RefreshCcw size={15} className="mr-2 inline" />Atualizar</button>}>
          <div className="rounded-3xl border border-blue-400/20 bg-blue-500/10 p-5">
            <p className="text-xs font-black uppercase tracking-[0.2em] text-blue-200">O que precisa da minha atenção agora?</p>
            <h2 className="mt-3 text-2xl font-black text-white">{focoAgora?.titulo || 'Nenhuma prioridade crítica agora'}</h2>
            <p className="mt-2 text-sm leading-6 text-blue-100/80">{focoAgora ? `${focoAgora.detalhe} Ação sugerida: ${focoAgora.acao}` : 'A operação está sem bloqueio crítico consolidado. Mantenha monitoramento e rotina de atualização.'}</p>
            {focoAgora && <div className="mt-4 flex flex-wrap gap-2"><Badge value={focoAgora.tipo} /><Badge value={`urgência ${focoAgora.urgencia}`} /><Badge value={`fonte ${focoAgora.fonte}`} /><Badge value="ação supervisionada" /><button disabled={centralBusy} onClick={() => setSelected(focoAgora)} className="rounded-xl bg-blue-600 px-3 py-2 text-xs font-black text-white disabled:opacity-60">Abrir encaminhamento</button><button disabled={centralBusy} onClick={() => centralAction(focoAgora, 'andamento')} className="rounded-xl bg-orange-600 px-3 py-2 text-xs font-black text-white disabled:opacity-60">Assumir agora</button><button disabled={centralBusy} onClick={() => centralAction(focoAgora, 'concluir')} className="rounded-xl bg-emerald-600 px-3 py-2 text-xs font-black text-white disabled:opacity-60">Resolver</button></div>}
          </div>
          <div className="mt-5 grid gap-4 md:grid-cols-2 xl:grid-cols-5">
            <MetricCard label="Comercial" value={porEixo.find((x) => x.eixo === 'comercial')?.total || 0} tone={porEixo.find((x) => x.eixo === 'comercial')?.total ? 'warning' : 'success'} />
            <MetricCard label="Operacional" value={porEixo.find((x) => x.eixo === 'operacional')?.total || 0} tone={porEixo.find((x) => x.eixo === 'operacional')?.total ? 'warning' : 'success'} />
            <MetricCard label="Documental" value={porEixo.find((x) => x.eixo === 'documental')?.total || 0} tone={porEixo.find((x) => x.eixo === 'documental')?.total ? 'danger' : 'success'} />
            <MetricCard label="Financeiro" value={porEixo.find((x) => x.eixo === 'financeiro')?.total || 0} tone={porEixo.find((x) => x.eixo === 'financeiro')?.total ? 'warning' : 'success'} />
            <MetricCard label="Estratégico" value={porEixo.find((x) => x.eixo === 'estratégico')?.total || 0} tone={porEixo.find((x) => x.eixo === 'estratégico')?.total ? 'warning' : 'success'} />
          </div>
        </Section>

        <div className="grid gap-6 xl:grid-cols-[1.15fr_0.85fr]">
          <Section title="Prioridades reais" subtitle="Prazo crítico, certidão vencendo, proposta parada, cobrança pendente, cliente frio e risco concorrencial.">
            {!prioridades.length ? <Empty text="Nenhuma prioridade operacional crítica agora." /> : <div className="grid gap-3 md:grid-cols-2">{prioridades.map((item) => <OperationalCard key={item.id} item={item} onClick={() => setSelected(item)} />)}</div>}
          </Section>
          <Section title="Ações rápidas" subtitle="Atalhos supervisionados para trabalhar sem sair da central.">
            <div className="grid gap-3">
              {quickActions.map((acao) => <button key={acao.label} onClick={() => acao.items.length === 1 ? setSelected(shapeCentralItem(acao.items[0], acao.label)) : openCentralList(acao.label, acao.items, 'Nenhum registro real encontrado para este filtro agora.')} className="rounded-2xl border border-slate-800 bg-slate-950/50 p-4 text-left font-bold text-white transition hover:border-blue-400/40 hover:bg-blue-500/10">{acao.label}<span className="ml-2 text-xs text-slate-500">({acao.items.length})</span></button>)}
            </div>
          </Section>
        </div>

        <div className="grid gap-6 xl:grid-cols-2">
          <Section title="Timeline operacional diária" subtitle="Sequência de atenção do dia: agora, hoje e próximo bloco.">
            <div className="space-y-3">{timeline.map((event, index) => <div key={`${event.titulo}-${index}`} className="flex gap-3"><div className={`mt-1 h-3 w-3 rounded-full ${event.urgencia >= 90 ? 'bg-red-400' : event.urgencia >= 75 ? 'bg-orange-300' : 'bg-blue-300'}`} /><div className="flex-1 rounded-xl border border-slate-800 bg-slate-950/50 p-3"><div className="flex flex-wrap gap-2"><Badge value={event.hora} /><Badge value={event.tipo} /></div><p className="mt-2 font-bold text-white">{event.titulo}</p><p className="text-xs text-slate-500">Fonte: {event.fonte}</p></div></div>)}{!timeline.length && <Empty text="Sem eventos para a timeline diária." />}</div>
          </Section>
          <Section title="Detalhe e encaminhamento" subtitle="Cards clicáveis mostram motivo, fonte e ação recomendada.">
            {!selected ? <Empty text="Clique em uma prioridade ou ação rápida para ver o encaminhamento." /> : <div className="rounded-2xl border border-slate-800 bg-slate-950/70 p-5"><div className="flex flex-wrap gap-2"><Badge value={selected.tipo || 'prioridade'} />{selected.eixo && <Badge value={selected.eixo} />}{selected.urgencia && <Badge value={`urgência ${selected.urgencia}`} />}</div><h3 className="mt-4 text-xl font-black text-white">{selected.titulo}</h3><p className="mt-3 text-sm leading-6 text-slate-300">{selected.detalhe}</p><div className="mt-4 grid gap-3 md:grid-cols-2"><div className="rounded-xl bg-slate-900/80 p-3"><p className="text-xs text-slate-500">Motivo do alerta</p><strong className="text-white">{selected.motivo || selected.detalhe}</strong></div><div className="rounded-xl bg-slate-900/80 p-3"><p className="text-xs text-slate-500">Consequência</p><strong className="text-white">{selected.consequencia || 'Pode travar a operação se não for assumido.'}</strong></div><div className="rounded-xl bg-slate-900/80 p-3"><p className="text-xs text-slate-500">Prazo</p><strong className="text-white">{selected.prazo || 'hoje/próximo bloco'}</strong></div><div className="rounded-xl bg-slate-900/80 p-3"><p className="text-xs text-slate-500">Responsável</p><strong className="text-white">{selected.responsavel || 'definir responsável'}</strong></div></div><div className="mt-4 rounded-xl border border-blue-400/20 bg-blue-500/10 p-4"><p className="text-xs font-black uppercase tracking-wide text-blue-200">Ação sugerida</p><p className="mt-2 text-sm text-blue-50">{selected.acao}</p><p className="mt-2 text-xs text-blue-100/70">Histórico rápido: {selected.historico || 'sem histórico explícito'}</p></div>{selected.memoria && <div className="mt-4 rounded-xl border border-purple-400/20 bg-purple-500/10 p-4"><p className="text-xs font-black uppercase tracking-wide text-purple-200">Memória viva relacionada</p><p className="mt-2 text-sm text-purple-50">{selected.memoria.titulo || selected.memoria.resumo || selected.memoria.conteudo}</p></div>}<div className="mt-4 grid gap-3 md:grid-cols-3"><input value={centralResponsible} onChange={(e) => setCentralResponsible(e.target.value)} placeholder="Alterar responsável" className="input" /><input value={centralRisk} onChange={(e) => setCentralRisk(e.target.value)} placeholder="Atualizar risco" className="input" /><input value={centralNote} onChange={(e) => setCentralNote(e.target.value)} placeholder="Observação rápida" className="input" /></div><div className="mt-4 flex flex-wrap gap-2"><button disabled={centralBusy} onClick={() => centralAction(selected, 'andamento')} className="rounded-xl bg-blue-600 px-4 py-2 text-sm font-black text-white disabled:opacity-60">Atualizar status</button><button disabled={centralBusy} onClick={() => centralAction(selected, 'concluir')} className="rounded-xl bg-emerald-600 px-4 py-2 text-sm font-black text-white disabled:opacity-60">Resolver / concluir</button><button disabled={centralBusy} onClick={() => centralAction(selected, 'arquivar')} className="rounded-xl bg-slate-800 px-4 py-2 text-sm font-black text-white disabled:opacity-60">Arquivar</button><button disabled={centralBusy} onClick={() => setCentralNote(`Follow-up registrado pela Central: ${selected.acao || selected.titulo}`)} className="rounded-xl bg-orange-600 px-4 py-2 text-sm font-black text-white disabled:opacity-60">Preparar follow-up</button></div><p className="mt-3 text-xs text-slate-500">Fonte: {selected.fonte || 'Central Operacional'} · ação rápida supervisionada.</p></div>}
          </Section>
        </div>

        {centralList && <Section title={`Lista filtrada: ${centralList.title}`} subtitle="Ação sem card morto: selecione um registro real com ID para encaminhar ou atualizar no módulo de origem." action={<button onClick={() => setCentralList(null)} className="rounded-xl bg-slate-800 px-3 py-2 text-sm font-bold text-white">Fechar lista</button>}>
          {!centralList.items.length ? <Empty text={centralList.fallbackText || 'Nenhum registro encontrado.'} /> : <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">{centralList.items.slice(0, 24).map((item, index) => <button key={item.id || item.oportunidade_id || index} onClick={() => setSelected(shapeCentralItem(item, centralList.title))} className="rounded-2xl border border-slate-800 bg-slate-950/50 p-4 text-left transition hover:border-blue-400/40"><div className="flex flex-wrap gap-2"><Badge value={item.tipo || item.status || 'registro'} />{(item.id || item.oportunidade_id) && <Badge value="ID real" />}</div><p className="mt-2 font-black text-white">{item.titulo || item.orgao || item.objeto || item.empresa || 'Registro'}</p><p className="mt-1 text-xs text-slate-400">{item.id || item.oportunidade_id || 'sem id'} · {item.status || item.fase_atual || item.classificacao_triagem || 'sem status'}</p></button>)}</div>}
        </Section>}

        <Section title="Movimentações recentes" subtitle="Rastreabilidade operacional para contexto sem trocar de tela.">
          <AuditActivityList items={data?.audit?.logs || []} />
        </Section>
      </div>
    </StateGate>
  )
}

function OperationalCard({ item, onClick }) {
  const tone = item.urgencia >= 90 || item.impacto === 'crítico' ? 'border-red-400/25 bg-red-500/10 hover:border-red-300/50' : item.urgencia >= 75 ? 'border-orange-400/25 bg-orange-500/10 hover:border-orange-300/50' : 'border-slate-800 bg-slate-950/50 hover:border-blue-400/40'
  return (
    <button onClick={onClick} className={`rounded-2xl border p-4 text-left transition ${tone}`}>
      <div className="flex flex-wrap items-center gap-2"><Badge value={item.tipo || 'operacional'} />{item.eixo && <Badge value={item.eixo} />}{item.urgencia && <Badge value={`urgência ${item.urgencia}`} />}</div>
      <p className="mt-3 font-black text-white">{item.titulo || 'Registro operacional'}</p>
      <p className="mt-2 line-clamp-3 text-sm text-slate-300">{item.detalhe || 'Sem detalhe adicional.'}</p>
      <p className="mt-3 text-xs text-slate-500">Fonte: {item.fonte || 'operação'} · clique para encaminhar</p>
    </button>
  )
}

function Orgaos() {
  const { data, loading, error, refresh } = useAsyncData(() => Promise.all([api.orgaos(), api.orgaosEngine()]).then(([lista, engine]) => ({ lista, engine })), [])
  const emptyForm = { nome: '', cnpj: '', esfera: '', uf: '', risco: 'desconhecido', observacoes_estrategicas: '' }
  const [form, setForm] = useState(emptyForm)
  const [filters, setFilters] = useState({ termo: '', uf: '', risco: '' })
  const [selected, setSelected] = useState(null)
  const [editing, setEditing] = useState(null)
  const [saving, setSaving] = useState(false)
  const [actionError, setActionError] = useState('')
  const orgaos = data?.lista?.orgaos || data?.lista?.itens || []
  const filtered = orgaos.filter((orgao) => {
    const q = filters.termo.toLowerCase()
    if (filters.uf && (orgao.uf || '').toLowerCase() !== filters.uf.toLowerCase()) return false
    if (filters.risco && (orgao.risco || '') !== filters.risco) return false
    if (!q) return true
    return [orgao.nome, orgao.cnpj, orgao.esfera, orgao.observacoes_estrategicas].join(' ').toLowerCase().includes(q)
  })
  async function save(event) {
    event.preventDefault(); setSaving(true); setActionError('')
    try {
      if (editing?.id) await api.orgaoAtualizar(editing.id, form)
      else await api.orgaoRegistrar(form)
      setForm(emptyForm); setEditing(null); refresh()
    } catch (err) { setActionError(err.message || 'Erro ao salvar órgão') }
    finally { setSaving(false) }
  }
  function editOrgao(orgao) { setEditing(orgao); setSelected(orgao); setForm({ nome: orgao.nome || '', cnpj: orgao.cnpj || '', esfera: orgao.esfera || '', uf: orgao.uf || '', risco: orgao.risco || 'desconhecido', observacoes_estrategicas: orgao.observacoes_estrategicas || '' }) }
  async function archiveOrgao(orgao) { setSaving(true); setActionError(''); try { await api.orgaoArquivar(orgao.id); if (selected?.id === orgao.id) setSelected(null); refresh() } catch (err) { setActionError(err.message || 'Erro ao arquivar órgão') } finally { setSaving(false) } }
  return (
    <StateGate loading={loading} error={error} onRetry={refresh}>
      <div className="space-y-6">
        {actionError && <ErrorBox text={actionError} />}
        <Section title="Órgãos" subtitle="Cadastro e histórico dos órgãos compradores para decidir onde competir melhor." action={<button onClick={refresh} className="rounded-xl bg-slate-800 px-4 py-2 text-sm font-bold text-white hover:bg-slate-700"><RefreshCcw size={15} className="mr-2 inline" />Atualizar</button>}>
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3"><MetricCard label="Órgãos" value={orgaos.length} /><MetricCard label="Filtrados" value={filtered.length} /><MetricCard label="Base ativa" value={data?.engine?.nome ? 'sim' : 'ok'} tone="success" /></div>
          <div className="mt-4 grid gap-3 md:grid-cols-3"><input value={filters.termo} onChange={(e) => setFilters({ ...filters, termo: e.target.value })} placeholder="Filtrar por nome/CNPJ" className="input" /><input value={filters.uf} onChange={(e) => setFilters({ ...filters, uf: e.target.value.toUpperCase() })} placeholder="UF" className="input" /><select value={filters.risco} onChange={(e) => setFilters({ ...filters, risco: e.target.value })} className="input"><option value="">Todos os riscos</option>{['baixo','médio','alto','crítico','desconhecido'].map((r) => <option key={r} value={r}>{r}</option>)}</select></div>
        </Section>
        <div className="grid gap-6 xl:grid-cols-2">
          <Section title="Órgãos cadastrados" subtitle="Registros filtrados pela organização ativa · ações Detalhe/Editar/Arquivar sempre visíveis">
            {!filtered.length ? <Empty text="Nenhum órgão encontrado." /> : <div className="space-y-3">{filtered.map((orgao) => <div key={orgao.id} className="rounded-xl border border-slate-800 bg-slate-950/50 p-4"><div className="flex flex-wrap gap-2"><Badge value={orgao.uf || 'UF'} /><Badge value={orgao.esfera || 'esfera'} /><Badge value={orgao.risco || 'risco'} />{orgao.metadata?.arquivado && <Badge value="arquivado" />}</div><p className="mt-2 font-bold text-white">{orgao.nome}</p><p className="mt-1 text-sm text-slate-400">{orgao.cnpj || 'Sem CNPJ'} · Score {orgao.score_oportunidade ?? '—'}</p><div className="crud-action-bar mt-3"><span className="crud-action-label">Ações</span><button onClick={() => setSelected(orgao)} className="crud-button">Detalhe</button><button onClick={() => editOrgao(orgao)} className="crud-button-primary">Editar</button><button onClick={() => archiveOrgao(orgao)} disabled={saving} className="crud-button disabled:opacity-60">Arquivar</button></div></div>)}</div>}
          </Section>
          <Section title={editing ? 'Editar órgão' : 'Registrar órgão'} subtitle="Registre histórico, risco e observações para orientar participação futura.">
            <form onSubmit={save} className="grid gap-3 md:grid-cols-2">
              <input required value={form.nome} onChange={(e) => setForm({ ...form, nome: e.target.value })} placeholder="Nome do órgão" className="input" />
              <input value={form.cnpj} onChange={(e) => setForm({ ...form, cnpj: e.target.value })} placeholder="CNPJ" className="input" />
              <input value={form.esfera} onChange={(e) => setForm({ ...form, esfera: e.target.value })} placeholder="Esfera" className="input" />
              <input value={form.uf} onChange={(e) => setForm({ ...form, uf: e.target.value.toUpperCase() })} placeholder="UF" className="input" />
              <select value={form.risco} onChange={(e) => setForm({ ...form, risco: e.target.value })} className="input md:col-span-2">{['baixo','médio','alto','crítico','desconhecido'].map((r) => <option key={r} value={r}>{r}</option>)}</select>
              <textarea value={form.observacoes_estrategicas} onChange={(e) => setForm({ ...form, observacoes_estrategicas: e.target.value })} placeholder="Observações estratégicas" className="input md:col-span-2" />
              <button disabled={saving || !form.nome} className="rounded-2xl bg-blue-600 px-4 py-3 font-black text-white disabled:opacity-60 md:col-span-2">{editing ? 'Atualizar órgão' : 'Registrar órgão'}</button>
              {editing && <button type="button" onClick={() => { setEditing(null); setForm(emptyForm) }} className="rounded-2xl bg-slate-800 px-4 py-3 font-black text-white md:col-span-2">Cancelar edição</button>}
            </form>
          </Section>
        </div>
        {selected && <Section title={`Detalhe do órgão: ${selected.nome}`} subtitle={`ID ${selected.id}`} action={<button onClick={() => setSelected(null)} className="rounded-xl bg-slate-800 px-3 py-2 text-sm font-bold text-white">Fechar</button>}><pre className="max-h-96 overflow-auto whitespace-pre-wrap rounded-2xl border border-slate-800 bg-slate-950 p-5 text-xs text-slate-300">{JSON.stringify(selected, null, 2)}</pre></Section>}
      </div>
    </StateGate>
  )
}

function Notificacoes() {
  const { data, loading, error, refresh } = useAsyncData(() => Promise.all([api.notificacoesEngine(), api.dashboardAlertas(), api.notificacoesLogs().catch((err) => ({ erro: err.message, logs: [] }))]).then(([engine, alertas, logs]) => ({ engine, alertas, logs })), [])
  const [selected, setSelected] = useState(null)
  const [filter, setFilter] = useState('')
  const logs = (data?.logs?.logs || []).filter((log) => {
    const q = filter.toLowerCase()
    if (!q) return true
    return JSON.stringify(log).toLowerCase().includes(q)
  })
  async function archiveLog(log) { await api.arquivarNotificacaoLog(log.id); if (selected?.id === log.id) setSelected(null); refresh() }
  return (
    <StateGate loading={loading} error={error} onRetry={refresh}>
      <div className="space-y-6">
        <Section title="Notificações" subtitle="Avisos controlados, registros recentes e confirmações importantes." action={<button onClick={refresh} className="rounded-xl bg-slate-800 px-4 py-2 text-sm font-bold text-white hover:bg-slate-700"><RefreshCcw size={15} className="mr-2 inline" />Atualizar</button>}>
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4"><MetricCard label="Alertas" value={data?.alertas?.total || 0} /><MetricCard label="Não lidos" value={data?.alertas?.nao_lidos || 0} tone={(data?.alertas?.nao_lidos || 0) ? 'warning' : 'success'} /><MetricCard label="Registros" value={data?.logs?.total || logs.length} /><MetricCard label="Confirmação" value="obrigatória" tone="success" /></div>
          <div className="mt-5 flex flex-wrap gap-2">{(data?.engine?.canais || data?.engine?.channels || ['telegram', 'email/webhook']).map((canal) => <Badge key={canal} value={canal} />)}</div>
        </Section>
        <Section title="Logs de notificação" subtitle="Rastreabilidade de envios/testes" action={<input value={filter} onChange={(e) => setFilter(e.target.value)} placeholder="Filtrar logs" className="rounded-xl border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-200" />}>
          {!logs.length ? <Empty text="Nenhum log de notificação encontrado." /> : <div className="space-y-3">{logs.slice(0, 20).map((log) => <div key={log.id} className="rounded-xl border border-slate-800 bg-slate-950/50 p-4"><div className="flex flex-wrap gap-2"><Badge value={log.status || 'status'} /><Badge value={log.canal || log.channel || 'canal'} />{log.metadata?.arquivado && <Badge value="arquivado" />}</div><p className="mt-2 text-sm text-slate-300">{log.mensagem || log.message || log.assunto || 'Log operacional de notificação'}</p><p className="mt-1 text-xs text-slate-500">{formatDate(log.criado_em || log.created_at || log.data)}</p><div className="mt-3 flex flex-wrap gap-2"><button onClick={() => setSelected(log)} className="rounded-lg bg-slate-800 px-3 py-2 text-xs font-bold text-white">Detalhe</button><button onClick={() => archiveLog(log)} className="rounded-lg bg-slate-800 px-3 py-2 text-xs font-bold text-white">Arquivar</button></div></div>)}</div>}
        </Section>
        {selected && <Section title="Detalhe da notificação" subtitle={`ID ${selected.id}`} action={<button onClick={() => setSelected(null)} className="rounded-xl bg-slate-800 px-3 py-2 text-sm font-bold text-white">Fechar</button>}><pre className="max-h-96 overflow-auto whitespace-pre-wrap rounded-2xl border border-slate-800 bg-slate-950 p-5 text-xs text-slate-300">{JSON.stringify(selected, null, 2)}</pre></Section>}
        <Alertas />
      </div>
    </StateGate>
  )
}

function Observabilidade() {
  const { data, loading, error, refresh } = useAsyncData(() => Promise.all([api.observabilidadeStatus(), api.healthFull(), api.chatMetricas(), api.auditLogs(20)]).then(([status, health, chat, audit]) => ({ status, health, chat, audit })), [])
  return (
    <StateGate loading={loading} error={error} onRetry={refresh}>
      <div className="space-y-6">
        <Section title="Observabilidade" subtitle="Saúde da operação, disponibilidade e registros de controle." action={<button onClick={refresh} className="rounded-xl bg-slate-800 px-4 py-2 text-sm font-bold text-white hover:bg-slate-700"><RefreshCcw size={15} className="mr-2 inline" />Atualizar</button>}>
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
            <MetricCard label="Health" value={data?.health?.status || data?.health?.service || 'ok'} tone="success" />
            <MetricCard label="API" value={data?.status?.api?.status || data?.status?.status || 'ativa'} />
            <MetricCard label="Chat sucesso" value={`${data?.chat?.taxa_sucesso || 0}%`} tone={(data?.chat?.taxa_sucesso || 0) < 70 ? 'warning' : 'success'} />
            <MetricCard label="Audit logs" value={data?.audit?.logs?.length || 0} />
            <MetricCard label="Sem resposta" value={data?.chat?.total_sem_resposta || 0} tone={(data?.chat?.total_sem_resposta || 0) ? 'warning' : 'success'} />
          </div>
          <pre className="mt-5 max-h-96 overflow-auto rounded-2xl border border-slate-800 bg-slate-950/70 p-4 text-xs text-slate-300">{JSON.stringify({ health: data?.health, observabilidade: data?.status }, null, 2)}</pre>
        </Section>
        <ChatTechnicalDashboard metricas={data?.chat} onRefresh={refresh} />
        <Section title="Atividade recente" subtitle="Movimentações registradas na operação."><AuditActivityList items={data?.audit?.logs || []} /></Section>
      </div>
    </StateGate>
  )
}

function MiniList({ title, items }) {
  return <div><p className="text-xs font-bold uppercase tracking-wide text-slate-500">{title}</p><div className="mt-2 space-y-2">{items.length ? items.slice(0, 5).map((item, index) => { const label = typeof item === 'string' ? item : item.valor || item.titulo || item.descricao || 'Registro'; const total = typeof item === 'string' ? '' : item.total ?? item.status ?? ''; return <div key={`${title}-${label}-${index}`} className="flex justify-between gap-3 rounded-xl bg-slate-950/60 px-3 py-2 text-sm text-slate-300"><span className="line-clamp-2">{label}</span>{total !== '' && <strong>{total}</strong>}</div> }) : <p className="text-sm text-slate-500">Sem dados.</p>}</div></div>
}


const fornecedorTipos = ['contrato', 'execucao', 'financeiro', 'risco']
const consultorFullTipos = ['lead', 'agenda', 'tarefa', 'financeiro', 'portal', 'carteira']
const operationalStatuses = ['ativo', 'pendente', 'em andamento', 'concluido', 'regularizar', 'arquivado']


function FornecedorFull() {
  const { data, loading, error, refresh } = useAsyncData(() => Promise.all([api.fornecedorFullDashboard(), api.fornecedorFullRegistros()]).then(([dashboard, registros]) => ({ dashboard, registros })), [])
  const [form, setForm] = useState({ tipo: 'contrato', titulo: '', orgao: '', status: 'ativo', prioridade: 'media', valor: 0, data_inicio: '', data_fim: '', observacoes: '' })
  const [tipoFiltro, setTipoFiltro] = useState('')
  const [saving, setSaving] = useState(false)
  const [feedback, setFeedback] = useState('')
  const [editing, setEditing] = useState(null)
  async function save(e) {
    e.preventDefault(); setSaving(true); setFeedback('')
    try {
      const payload = { ...form, valor: Number(form.valor || 0), data_inicio: form.data_inicio || null, data_fim: form.data_fim || null }
      if (editing?.id) await api.fornecedorFullAtualizar(editing.id, payload)
      else await api.fornecedorFullCriar(payload)
      setForm({ tipo: form.tipo, titulo: '', orgao: '', status: 'ativo', prioridade: 'media', valor: 0, data_inicio: '', data_fim: '', observacoes: '' }); setEditing(null); setFeedback(editing?.id ? 'Registro atualizado. A operação foi sincronizada.' : 'Registro salvo. A operação foi atualizada.'); refresh()
    }
    catch (err) { setFeedback(err.message || 'Não foi possível salvar o registro.') }
    finally { setSaving(false) }
  }
  function fornecedorContexto(item, status) {
    const motivo = item.tipo === 'financeiro' ? 'regularizar recebimento/pagamento' : item.tipo === 'execucao' ? 'destravar medição, entrega ou aceite' : item.tipo === 'risco' ? 'mitigar risco contratual' : 'manter contrato e vigência sob controle'
    return {
      motivo,
      impacto: item.tipo === 'financeiro' ? 'fluxo de caixa e cobrança' : item.tipo === 'risco' ? 'sanção, glosa ou inadimplemento' : 'continuidade executiva',
      observacao: `Status alterado para ${status}.`,
      historico: item.observacoes || 'sem histórico anterior explícito',
      consequencia_operacional: item.tipo === 'financeiro' ? 'se não agir, pagamento pode atrasar e comprometer caixa' : item.tipo === 'execucao' ? 'se não agir, entrega/medição pode travar aceite e faturamento' : item.tipo === 'risco' ? 'se não agir, risco pode virar sanção, glosa ou rescisão' : 'se não agir, vencimento/aditivo pode ser perdido',
      origem: 'Fornecedor Full',
      entidade_relacionada: item.id,
    }
  }
  async function atualizarFornecedor(item, status) {
    if (!item?.id) return
    const ctx = fornecedorContexto(item, status)
    setSaving(true); setFeedback('')
    try { await api.fornecedorFullAtualizar(item.id, { status, observacoes: `${item.observacoes || ''}
${ctx.observacao} Motivo: ${ctx.motivo}. Impacto: ${ctx.impacto}. Consequência: ${ctx.consequencia_operacional}. Histórico: ${ctx.historico}.`.trim(), payload: { contexto_operacional: ctx } }); setFeedback(`Status atualizado para ${status} com contexto executivo.`); refresh() }
    catch (err) { setFeedback(err.message || 'Não foi possível atualizar o status.') }
    finally { setSaving(false) }
  }

  function editFornecedor(item) {
    setEditing(item)
    setForm({
      tipo: item.tipo || 'contrato',
      titulo: item.titulo || '',
      orgao: item.orgao || '',
      status: item.status || 'ativo',
      prioridade: item.prioridade || 'media',
      valor: item.valor || 0,
      data_inicio: item.data_inicio || '',
      data_fim: item.data_fim || '',
      observacoes: item.observacoes || '',
    })
  }
  async function atualizarFornecedorCompleto(item, patch) {
    if (!item?.id) return
    const status = patch.status || item.status || 'em andamento'
    const ctx = fornecedorContexto(item, status)
    setSaving(true); setFeedback('')
    try { await api.fornecedorFullAtualizar(item.id, { ...patch, observacoes: [item.observacoes, patch.observacoes, `Contexto executivo: motivo=${ctx.motivo}; impacto=${ctx.impacto}; consequência=${ctx.consequencia_operacional}; histórico=${ctx.historico}.`].filter(Boolean).join('\n'), payload: { ...(item.payload || {}), ...(patch.payload || {}), contexto_operacional: ctx } }); setFeedback('Registro fornecedor atualizado com histórico executivo.'); refresh() }
    catch (err) { setFeedback(err.message || 'Não foi possível atualizar o registro.') }
    finally { setSaving(false) }
  }
  function prepararRegistroFornecedor(tipo, titulo, status = 'ativo', prioridade = 'alta') {
    setEditing(null)
    setForm({ ...form, tipo, titulo, status, prioridade, valor: tipo === 'financeiro' ? form.valor : 0, observacoes: '' })
  }
  const d = data?.dashboard || {}
  const itens = data?.registros?.itens || []
  const norm = (value) => String(value || '').trim().toLowerCase()
  const today = new Date(); today.setHours(0, 0, 0, 0)
  const daysUntil = (value) => { if (!value) return null; const date = new Date(value); if (Number.isNaN(date.getTime())) return null; date.setHours(0, 0, 0, 0); return Math.ceil((date - today) / 86400000) }
  const filtrados = tipoFiltro ? itens.filter((i) => i.tipo === tipoFiltro) : itens
  const pagamentosPendentes = itens.filter((i) => norm(i.tipo) === 'financeiro' && ['pendente', 'atrasado', 'inadimplente'].some((status) => norm(i.status).includes(status)))
  const contratosVencendo = itens.filter((i) => norm(i.tipo) === 'contrato' && daysUntil(i.data_fim) !== null && daysUntil(i.data_fim) <= 45)
  const riscosAbertos = itens.filter((i) => norm(i.tipo) === 'risco' && !['concluido', 'arquivado', 'encerrado'].some((status) => norm(i.status).includes(status)))
  const execucaoPendente = itens.filter((i) => norm(i.tipo) === 'execucao' && ['pendente', 'atrasado', 'ativo'].some((status) => norm(i.status).includes(status)))
  const valorPendente = pagamentosPendentes.reduce((sum, item) => sum + Number(item.valor || 0), 0)
  return (
    <StateGate loading={loading} error={error} onRetry={refresh}>
      <div className="space-y-6">
        {feedback && <div className="rounded-2xl border border-emerald-400/25 bg-emerald-500/10 p-4 text-sm font-bold text-emerald-100">{feedback}</div>}
        <Section title="Gestão do Fornecedor" subtitle="Contratos, execução, financeiro e riscos em uma visão operacional" action={<button onClick={refresh} className="premium-button"><RefreshCcw size={15} className="mr-2 inline" />Atualizar</button>}>
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            <MetricCard label="Contratos ativos" value={d.contratos_ativos || 0} tone="success" />
            <MetricCard label="Pagamentos pendentes" value={d.pagamentos_pendentes || 0} tone={(d.pagamentos_pendentes || 0) ? 'warning' : 'success'} />
            <MetricCard label="Risco contratual" value={d.risco_contratual_medio || 0} tone={(d.risco_contratual_medio || 0) >= 60 ? 'danger' : 'neutral'} />
            <MetricCard label="Órgãos críticos" value={(d.orgaos_criticos || []).length} tone={(d.orgaos_criticos || []).length ? 'warning' : 'success'} />
            <MetricCard label="Contratos vencendo" value={contratosVencendo.length} tone={contratosVencendo.length ? 'warning' : 'success'} />
            <MetricCard label="Execuções pendentes" value={execucaoPendente.length} tone={execucaoPendente.length ? 'warning' : 'success'} />
            <MetricCard label="Valor pendente" value={formatMoney(valorPendente || d.financeiro?.pendente || 0)} tone={(valorPendente || d.financeiro?.pendente) ? 'danger' : 'success'} />
            <MetricCard label="Riscos abertos" value={riscosAbertos.length} tone={riscosAbertos.length ? 'danger' : 'success'} />
          </div>
        </Section>

        <Section title="Fila de execução e recebimento" subtitle="O que resolver agora: vencimento, medição, aceite, pagamento e risco contratual.">
          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
            {[...contratosVencendo, ...execucaoPendente, ...pagamentosPendentes, ...riscosAbertos].slice(0, 12).map((item) => {
              const prazo = daysUntil(item.data_fim)
              return <div key={item.id || item.titulo} className={`rounded-2xl border p-4 ${item.tipo === 'financeiro' ? 'border-red-400/25 bg-red-500/10' : item.tipo === 'risco' ? 'border-orange-400/25 bg-orange-500/10' : 'border-slate-800 bg-slate-950/50'}`}>
                <div className="flex flex-wrap gap-2"><Badge value={item.tipo} /><Badge value={item.status} />{prazo !== null && <Badge value={prazo < 0 ? `${Math.abs(prazo)}d vencido` : `${prazo}d`} />}</div>
                <h3 className="mt-3 font-black text-white">{item.titulo}</h3>
                <p className="mt-1 text-xs text-slate-400">{item.orgao || 'sem órgão'} · {formatMoney(item.valor || 0)}</p>
                <div className="mt-3 flex flex-wrap gap-2"><button disabled={saving} onClick={() => editFornecedor(item)} className="crud-button-primary">Editar</button><button disabled={saving} onClick={() => atualizarFornecedor(item, item.tipo === 'financeiro' ? 'pago' : 'concluido')} className="crud-button-success">Resolver</button><button disabled={saving} onClick={() => atualizarFornecedorCompleto(item, { status: 'em andamento', observacoes: `${item.observacoes || ''}\nAção iniciada pela fila operacional.`.trim() })} className="crud-button-warning">Em andamento</button></div>
              </div>
            })}
            {![...contratosVencendo, ...execucaoPendente, ...pagamentosPendentes, ...riscosAbertos].length && <Empty text="Sem execução, cobrança ou risco bloqueando a rotina agora." />}
          </div>
        </Section>

        <div className="grid gap-6 xl:grid-cols-2">
          <Section title="Contratos em foco" subtitle="Vigência, renovações, garantias, execução e fluxo financeiro.">
            <div className="grid gap-4 md:grid-cols-2"><MiniBarChart title="Por tipo" data={d.por_tipo || {}} /><MiniBarChart title="Por status" data={d.por_status || {}} /></div>
            <div className="mt-5 grid gap-4 md:grid-cols-2"><FullList title="Renovações/aditivos" items={d.proximas_renovacoes || []} /><FullList title="Pendências de execução" items={d.pendencias_execucao || []} /></div>
          </Section>
          <Section title={editing ? 'Editar item fornecedor' : 'Registrar item fornecedor'} subtitle="Contrato, execução, financeiro ou risco — registro seguro da operação">
            <div className="mb-4 flex flex-wrap gap-2"><button type="button" onClick={() => prepararRegistroFornecedor('contrato', 'Novo contrato / vigência', 'ativo', 'alta')} className="crud-button-primary">+ Contrato</button><button type="button" onClick={() => prepararRegistroFornecedor('execucao', 'Medição / entrega pendente', 'pendente', 'alta')} className="crud-button-warning">+ Execução</button><button type="button" onClick={() => prepararRegistroFornecedor('financeiro', 'Pagamento a receber', 'pendente', 'alta')} className="crud-button-success">+ Cobrança</button><button type="button" onClick={() => prepararRegistroFornecedor('risco', 'Risco contratual', 'ativo', 'alta')} className="crud-button">+ Risco</button></div>
            <form onSubmit={save} className="grid gap-3 md:grid-cols-2">
              <label className="block"><span className="text-sm font-bold text-white">Tipo</span><select value={form.tipo} onChange={(e) => setForm({ ...form, tipo: e.target.value })} className="input mt-2">{fornecedorTipos.map((t) => <option key={t} value={t}>{t}</option>)}</select></label>
              <TextInput label="Título" required value={form.titulo} onChange={(v) => setForm({ ...form, titulo: v })} />
              <TextInput label="Órgão" value={form.orgao} onChange={(v) => setForm({ ...form, orgao: v })} />
              <TextInput label="Status" value={form.status} onChange={(v) => setForm({ ...form, status: v })} />
              <TextInput label="Prioridade" value={form.prioridade} onChange={(v) => setForm({ ...form, prioridade: v })} />
              <TextInput label="Valor" type="number" value={form.valor} onChange={(v) => setForm({ ...form, valor: v })} />
              <TextInput label="Início" value={form.data_inicio} onChange={(v) => setForm({ ...form, data_inicio: v })} />
              <TextInput label="Fim / vencimento" value={form.data_fim} onChange={(v) => setForm({ ...form, data_fim: v })} />
              <textarea value={form.observacoes} onChange={(e) => setForm({ ...form, observacoes: e.target.value })} placeholder="Observações: vigência, aditivo, garantia, medição, glosa, pagamento, sanção..." className="input md:col-span-2" />
              <button disabled={saving} className="premium-button-primary md:col-span-2">{editing ? 'Atualizar registro' : 'Registrar'}</button>{editing && <button type="button" onClick={() => { setEditing(null); setForm({ tipo: 'contrato', titulo: '', orgao: '', status: 'ativo', prioridade: 'media', valor: 0, data_inicio: '', data_fim: '', observacoes: '' }) }} className="rounded-2xl bg-slate-800 px-4 py-3 font-black text-white md:col-span-2">Cancelar edição</button>}
            </form>
          </Section>
        </div>
        <Section title="Registros fornecedor" subtitle="Contratos, execução, financeiro e riscos com ação de continuidade." action={<select value={tipoFiltro} onChange={(e) => setTipoFiltro(e.target.value)} className="input max-w-xs"><option value="">Todos os tipos</option>{fornecedorTipos.map((t) => <option key={t} value={t}>{t}</option>)}</select>}><FullTable items={filtrados} onStatus={atualizarFornecedor} onEdit={editFornecedor} onUpdate={atualizarFornecedorCompleto} /></Section>
      </div>
    </StateGate>
  )
}

function ConsultorFull() {
  const { data, loading, error, refresh } = useAsyncData(() => Promise.all([
    api.consultorFullDashboard(),
    api.consultorFullRegistros(),
    api.consultorFullPipeline(),
    api.consultorFullLeads(),
    api.consultorFullFollowups(),
    api.consultorFullCentral360(),
    api.documentalDocumentos({ limit: 300 }).catch((err) => ({ erro: err.message, itens: [] })),
    api.dashboardCasos().catch((err) => ({ erro: err.message, itens: [] })),
    api.dashboardMemorias().catch((err) => ({ erro: err.message, memorias: [], itens: [] })),
  ]).then(([dashboard, registros, pipeline, leads, followups, central360, documentos, casos, memorias]) => ({ dashboard, registros, pipeline, leads, followups, central360, documentos, casos, memorias })), [])
  const fluxoLeadCRM = ['Lead', 'Diagnóstico', 'Proposta', 'Negociação', 'Cliente', 'Operação', 'Recorrência']
  const fluxoCRM = ['Lead', 'Prospecção', 'Diagnóstico', 'Proposta', 'Negociação', 'Cliente', 'Operação', 'Demanda', 'Licitação', 'Peça', 'Cobrança', 'Recorrência']
  const [leadForm, setLeadForm] = useState({ nome: '', empresa: '', origem: 'manual', status: 'novo', estagio_comercial: 'novo', pipeline_etapa: 'Lead', follow_up_em: '', responsavel: '', potencial: 0, ticket_medio: 0, recorrencia: 0, risco_churn: 0, lucratividade: 0, classificacao: 'C', orgaos_prioritarios: '', observacoes: '' })
  const [taskForm, setTaskForm] = useState({ tipo: 'tarefa', titulo: '', cliente_nome: '', etapa: 'Operação', status: 'pendente', prioridade: 'alta', responsavel: '', valor: 0, observacoes: '' })
  const [filter, setFilter] = useState('')
  const [selectedClient, setSelectedClient] = useState('')
  const [saving, setSaving] = useState(false)
  const [feedback, setFeedback] = useState('')
  const [editingLead, setEditingLead] = useState(null)
  const [editingTask, setEditingTask] = useState(null)
  const d = data?.dashboard || {}
  const itens = data?.registros?.itens || []
  const leads = data?.leads?.itens || []
  const followups = data?.followups?.itens || []
  const pipeline = data?.pipeline || { etapas: [], colunas: {} }
  const central360 = data?.central360 || []
  const documentosCliente = data?.documentos?.itens || []
  const casosCliente = data?.casos?.itens || data?.casos?.casos || []
  const memoriasCliente = data?.memorias?.memorias || data?.memorias?.itens || data?.memorias?.recentes || []
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  const daysUntil = (value) => {
    if (!value) return null
    const date = new Date(value)
    if (Number.isNaN(date.getTime())) return null
    date.setHours(0, 0, 0, 0)
    return Math.ceil((date - today) / 86400000)
  }
  const norm = (value) => String(value || '').trim().toLowerCase()
  const clientKey = (item) => norm(item.empresa || item.cliente_nome || item.nome || item.cliente || item.titulo)
  const filteredLeads = leads.filter((lead) => !filter || [lead.nome, lead.empresa, lead.origem, lead.responsavel, lead.status, lead.pipeline_etapa, lead.classificacao].join(' ').toLowerCase().includes(filter.toLowerCase()))
  const clientes = useMemo(() => {
    const map = new Map()
    leads.forEach((lead) => {
      const key = clientKey(lead)
      if (!key) return
      const atual = map.get(key) || { nome: lead.empresa || lead.nome, leads: [], tarefas: [], followups: [], receita: 0, ticket: 0, potencial: 0, risco: 0, etapa: lead.pipeline_etapa || 'Lead' }
      atual.leads.push(lead)
      atual.receita += Number(lead.recorrencia || lead.ticket_medio || 0)
      atual.ticket += Number(lead.ticket_medio || 0)
      atual.potencial += Number(lead.potencial || 0)
      atual.risco = Math.max(atual.risco, Number(lead.risco_churn || 0))
      atual.etapa = lead.pipeline_etapa || atual.etapa
      map.set(key, atual)
    })
    itens.forEach((item) => {
      const key = clientKey(item)
      if (!key) return
      const atual = map.get(key) || { nome: item.cliente_nome || item.empresa || item.titulo, leads: [], tarefas: [], followups: [], receita: 0, ticket: 0, potencial: 0, risco: 0, etapa: item.etapa || 'Operação' }
      atual.tarefas.push(item)
      atual.receita += Number(item.valor || 0)
      atual.risco = Math.max(atual.risco, item.prioridade === 'alta' ? 65 : 0)
      atual.etapa = item.etapa || atual.etapa
      map.set(key, atual)
    })
    followups.forEach((f) => {
      const key = clientKey(f)
      if (!key) return
      const atual = map.get(key) || { nome: f.cliente_nome || f.empresa || f.titulo, leads: [], tarefas: [], followups: [], receita: 0, ticket: 0, potencial: 0, risco: 0, etapa: 'Follow-up' }
      atual.followups.push(f)
      map.set(key, atual)
    })
    return Array.from(map.entries()).map(([key, value]) => ({ key, ...value, atraso: value.followups.some((f) => daysUntil(f.data || f.follow_up_em || f.prazo) < 0), urgencia: Math.max(value.risco, value.followups.some((f) => daysUntil(f.data || f.follow_up_em || f.prazo) <= 1) ? 80 : 0) })).sort((a, b) => (b.urgencia + b.potencial + b.receita) - (a.urgencia + a.potencial + a.receita))
  }, [leads, itens, followups])
  const activeClient = clientes.find((c) => c.key === selectedClient) || clientes[0]
  const activeCentral = activeClient ? central360.find((c) => norm(c.cliente_nome || c.nome || c.cliente_id) === activeClient.key || norm(c.cliente_nome || c.nome || c.cliente_id) === norm(activeClient.nome)) : null
  const activeDocs = activeClient ? documentosCliente.filter((doc) => [doc.empresa_nome, doc.cliente_nome, doc.titulo, doc.observacoes].join(' ').toLowerCase().includes(activeClient.key)).slice(0, 8) : []
  const activeCases = activeClient ? casosCliente.filter((caso) => [caso.cliente, caso.objeto, caso.orgao, caso.contexto].join(' ').toLowerCase().includes(activeClient.key)).slice(0, 6) : []
  const activeMemories = activeClient ? memoriasCliente.filter((mem) => [mem.titulo, mem.conteudo, mem.resumo, mem.tags].join(' ').toLowerCase().includes(activeClient.key)).slice(0, 5) : []
  const activeOverdueCharge = activeClient ? itens.find((i) => norm(i.tipo) === 'financeiro' && ['inadimplente', 'atrasado', 'pendente'].some((status) => norm(i.status).includes(status)) && clientKey(i) === activeClient.key) : null
  const activePendingFollowup = activeClient ? activeClient.followups.find((f) => daysUntil(f.data || f.follow_up_em || f.prazo) <= 1) : null
  const activeCriticalDemand = activeClient ? activeClient.tarefas.find((t) => t.prioridade === 'alta' || ['pendente','em andamento'].includes(norm(t.status))) : null
  const activeNextText = activePendingFollowup?.titulo || activeCriticalDemand?.titulo || activeOverdueCharge?.titulo || 'Definir próximo movimento supervisionado'
  const stageData = fluxoCRM.map((stage) => {
    const fromBackend = pipeline.colunas?.[stage] || []
    const fromLeads = filteredLeads.filter((lead) => norm(lead.pipeline_etapa) === norm(stage) || (stage === 'Prospecção' && ['lead', 'contato'].includes(norm(lead.status))) || (stage === 'Negociação' && norm(lead.status) === 'negociação'))
    const fromTasks = itens.filter((item) => norm(item.etapa || item.tipo).includes(norm(stage)) || (stage === 'Peça' && ['impugnação', 'recurso', 'contrarrazões'].some((term) => norm(item.titulo || item.observacoes).includes(term))))
    const seen = new Set()
    return [...fromBackend, ...fromLeads, ...fromTasks].filter((lead) => {
      const id = lead.id || `${lead.nome || lead.titulo}-${lead.empresa || lead.cliente_nome}`
      if (seen.has(id)) return false
      seen.add(id)
      return !filter || [lead.nome, lead.empresa, lead.cliente_nome, lead.titulo, lead.origem, lead.responsavel, lead.status, lead.pipeline_etapa, lead.classificacao, lead.etapa].join(' ').toLowerCase().includes(filter.toLowerCase())
    })
  })
  const vencidos = followups.filter((f) => daysUntil(f.data || f.follow_up_em || f.prazo) < 0)
  const hoje = followups.filter((f) => daysUntil(f.data || f.follow_up_em || f.prazo) === 0)
  const propostasParadas = leads.filter((lead) => norm(lead.pipeline_etapa).includes('proposta') || norm(lead.status).includes('proposta'))
  const semContato = clientes.filter((c) => !c.followups.length)
  const receitaPrevista = Number(d.faturamento || d.receita_prevista || clientes.reduce((sum, c) => sum + Number(c.receita || c.potencial || 0), 0))
  const clientesEmRisco = clientes.filter((c) => c.risco >= 60 || c.atraso)
  const agingDias = leads.map((lead) => { const base = lead.atualizado_em || lead.criado_em || lead.follow_up_em; if (!base) return 0; const date = new Date(base); return Number.isNaN(date.getTime()) ? 0 : Math.max(0, Math.floor((Date.now() - date.getTime()) / 86400000)) })
  const agingMedio = agingDias.length ? Math.round(agingDias.reduce((sum, n) => sum + n, 0) / agingDias.length) : 0
  const clientesFrios = clientes.filter((c) => c.atraso || !c.followups.length || c.followups.every((f) => daysUntil(f.data || f.follow_up_em || f.prazo) < -7))
  const inadimplentes = itens.filter((i) => norm(i.tipo) === 'financeiro' && ['inadimplente', 'atrasado', 'pendente'].some((status) => norm(i.status).includes(status)))
  const recorrentes = leads.filter((lead) => Number(lead.recorrencia || 0) > 0 || norm(lead.pipeline_etapa).includes('recorrência'))
  const nextAction = vencidos[0] || hoje[0] || propostasParadas[0] || semContato[0]
  const actionText = nextAction?.titulo || nextAction?.nome || nextAction?.empresa || nextAction?.cliente_nome || nextAction?.nome || 'Definir próximo contato da carteira'
  const workflowEvents = activeClient ? [
    ...activeClient.leads.map((lead) => ({ tipo: 'Comercial', titulo: lead.pipeline_etapa || lead.status || 'Lead', texto: lead.observacoes || lead.origem || 'Registro comercial', data: lead.follow_up_em, tom: lead.risco_churn >= 60 ? 'danger' : 'neutral' })),
    ...activeClient.followups.map((f) => ({ tipo: 'Follow-up', titulo: f.titulo || f.status || 'Ação de contato', texto: f.observacoes || f.descricao || 'Próxima ação', data: f.data || f.follow_up_em || f.prazo, tom: daysUntil(f.data || f.follow_up_em || f.prazo) < 0 ? 'danger' : 'warning' })),
    ...activeClient.tarefas.map((item) => ({ tipo: item.tipo || 'Operação', titulo: item.titulo, texto: item.observacoes || item.status, data: item.criado_em || item.updated_at, tom: item.prioridade === 'alta' ? 'warning' : 'neutral' })),
  ].sort((a, b) => new Date(b.data || 0) - new Date(a.data || 0)) : []
  async function saveLead(e) {
    e.preventDefault(); setSaving(true); setFeedback('')
    try {
      const payload = {
        ...leadForm,
        potencial: Number(leadForm.potencial || 0),
        ticket_medio: Number(leadForm.ticket_medio || 0),
        recorrencia: Number(leadForm.recorrencia || 0),
        risco_churn: Number(leadForm.risco_churn || 0),
        lucratividade: Number(leadForm.lucratividade || 0),
        orgaos_prioritarios: String(leadForm.orgaos_prioritarios || '').split(',').map((x) => x.trim()).filter(Boolean),
        follow_up_em: leadForm.follow_up_em || null,
      }
      if (editingLead?.id) await api.consultorFullAtualizarLead(editingLead.id, payload)
      else await api.consultorFullCriarLead(payload)
      setLeadForm({ ...leadForm, nome: '', empresa: '', potencial: 0, ticket_medio: 0, recorrencia: 0, risco_churn: 0, lucratividade: 0, orgaos_prioritarios: '', observacoes: '' }); setEditingLead(null)
      setFeedback(editingLead?.id ? 'Lead atualizado. Pipeline e carteira foram sincronizados.' : 'Movimento comercial salvo. Pipeline e carteira foram atualizados.')
      refresh()
    } catch (err) { setFeedback(err.message || 'Não foi possível salvar o movimento comercial.') }
    finally { setSaving(false) }
  }
  async function saveTask(e) {
    e.preventDefault(); setSaving(true); setFeedback('')
    try {
      const payload = { ...taskForm, valor: Number(taskForm.valor || 0) }
      if (editingTask?.id) await api.consultorFullAtualizar(editingTask.id, payload)
      else await api.consultorFullCriar(payload)
      setTaskForm({ ...taskForm, titulo: '', cliente_nome: '', valor: 0, observacoes: '' }); setEditingTask(null); setFeedback(editingTask?.id ? 'Registro operacional atualizado.' : 'Próxima ação registrada na operação.'); refresh()
    }
    catch (err) { setFeedback(err.message || 'Não foi possível registrar a próxima ação.') }
    finally { setSaving(false) }
  }

  function editLead(item) {
    setEditingLead(item)
    setLeadForm({
      nome: item.nome || '', empresa: item.empresa || item.cliente_nome || '', origem: item.origem || 'manual', status: item.status || 'novo', estagio_comercial: item.estagio_comercial || item.status || 'novo', pipeline_etapa: item.pipeline_etapa || 'Lead', follow_up_em: item.follow_up_em || '', responsavel: item.responsavel || '', potencial: item.potencial || 0, ticket_medio: item.ticket_medio || 0, recorrencia: item.recorrencia || 0, risco_churn: item.risco_churn || 0, lucratividade: item.lucratividade || 0, classificacao: item.classificacao || 'C', orgaos_prioritarios: (item.orgaos_prioritarios || []).join?.(', ') || item.orgaos_prioritarios || '', observacoes: item.observacoes || ''
    })
  }
  function editRegistroConsultor(item) {
    setEditingTask(item)
    setTaskForm({ tipo: item.tipo || 'tarefa', titulo: item.titulo || '', cliente_nome: item.cliente_nome || item.empresa || '', etapa: item.etapa || 'Operação', status: item.status || 'pendente', prioridade: item.prioridade || 'alta', responsavel: item.responsavel || '', valor: item.valor || 0, observacoes: item.observacoes || '' })
  }
  async function atualizarRegistroConsultorCompleto(item, patch) {
    if (!item?.id) return
    setSaving(true); setFeedback('')
    try { await api.consultorFullAtualizar(item.id, patch); setFeedback('Registro operacional atualizado.'); refresh() }
    catch (err) { setFeedback(err.message || 'Não foi possível atualizar o registro.') }
    finally { setSaving(false) }
  }

  async function atualizarRegistroConsultor(item, status) {
    if (!item?.id) return
    setSaving(true); setFeedback('')
    try { await api.consultorFullAtualizar(item.id, { status }); setFeedback(`Status atualizado para ${status}.`); refresh() }
    catch (err) { setFeedback(err.message || 'Não foi possível atualizar o status.') }
    finally { setSaving(false) }
  }
  async function atualizarLead(item, status) {
    if (!item?.id) return
    const etapaPorStatus = { novo: 'Lead', contato: 'Diagnóstico', diagnóstico: 'Diagnóstico', proposta: 'Proposta', negociação: 'Negociação', ganho: 'Cliente', perdido: item.pipeline_etapa || 'Negociação', arquivado: item.pipeline_etapa || 'Lead' }
    setSaving(true); setFeedback('')
    try { await api.consultorFullAtualizarLead(item.id, { status, estagio_comercial: status, pipeline_etapa: etapaPorStatus[status] || item.pipeline_etapa || 'Lead' }); setFeedback(`Cliente atualizado para ${status}. Histórico e pipeline foram sincronizados.`); refresh() }
    catch (err) { setFeedback(err.message || 'Não foi possível atualizar o cliente no pipeline.') }
    finally { setSaving(false) }
  }
  async function criarFollowupRapido(item) {
    const cliente = item?.cliente_nome || item?.empresa || item?.nome || activeClient?.nome || ''
    setSaving(true); setFeedback('')
    try { await api.consultorFullCriarFollowup({ lead_id: item?.pipeline_etapa ? item.id : null, cliente_nome: cliente, titulo: `Retomar contato — ${cliente || 'cliente'}`, status: 'pendente', prioridade: 'alta', data: new Date().toISOString().slice(0, 10), responsavel: item?.responsavel || '' }); setFeedback('Follow-up criado para continuidade operacional.'); refresh() }
    catch (err) { setFeedback(err.message || 'Não foi possível criar o follow-up.') }
    finally { setSaving(false) }
  }
  async function concluirFollowup(item) {
    if (!item?.id) return
    setSaving(true); setFeedback('')
    try { await api.consultorFullAtualizarFollowup(item.id, { status: 'concluido' }); setFeedback('Follow-up concluído e registrado no histórico.'); refresh() }
    catch (err) { setFeedback(err.message || 'Não foi possível concluir o follow-up.') }
    finally { setSaving(false) }
  }
  async function reagendarFollowup(item, dias = 1) {
    if (!item?.id) return
    const next = new Date(); next.setDate(next.getDate() + dias)
    setSaving(true); setFeedback('')
    try { await api.consultorFullAtualizarFollowup(item.id, { status: 'pendente', data: next.toISOString().slice(0, 10) }); setFeedback('Follow-up reagendado com continuidade registrada.'); refresh() }
    catch (err) { setFeedback(err.message || 'Não foi possível reagendar o follow-up.') }
    finally { setSaving(false) }
  }
  function preencherAcaoCliente(tipo, titulo, etapa = 'Operação', prioridade = 'alta') {
    const cliente = activeClient?.nome || ''
    setTaskForm({ ...taskForm, tipo, cliente_nome: cliente, titulo: `${titulo}${cliente ? ` — ${cliente}` : ''}`, etapa, prioridade, status: 'pendente' })
  }
  return (
    <StateGate loading={loading} error={error} onRetry={refresh}>
      <div className="space-y-6">
        {feedback && <div className="rounded-2xl border border-emerald-400/25 bg-emerald-500/10 p-4 text-sm font-bold text-emerald-100">{feedback}</div>}
        <Section title="CRM Operacional" subtitle="Fluxo contínuo do primeiro contato à recorrência, com próxima ação obrigatória e carteira priorizada." action={<button onClick={refresh} className="premium-button"><RefreshCcw size={15} className="mr-2 inline" />Atualizar</button>}>
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
            <MetricCard label="Clientes sem contato" value={semContato.length} tone={semContato.length ? 'warning' : 'success'} />
            <MetricCard label="Propostas paradas" value={propostasParadas.length} tone={propostasParadas.length ? 'warning' : 'success'} />
            <MetricCard label="Follow-ups vencidos" value={vencidos.length} tone={vencidos.length ? 'danger' : 'success'} />
            <MetricCard label="Receita prevista" value={formatMoney(receitaPrevista)} tone="success" />
            <MetricCard label="Clientes em risco" value={clientesEmRisco.length || d.clientes_risco || 0} tone={(clientesEmRisco.length || d.clientes_risco) ? 'danger' : 'success'} />
            <MetricCard label="Aging médio" value={`${agingMedio}d`} tone={agingMedio > 10 ? 'warning' : 'success'} />
            <MetricCard label="Clientes frios" value={clientesFrios.length} tone={clientesFrios.length ? 'warning' : 'success'} />
            <MetricCard label="Inadimplência" value={formatMoney(inadimplentes.reduce((sum, i) => sum + Number(i.valor || 0), 0) || d.inadimplencia || 0)} tone={(inadimplentes.length || d.inadimplencia) ? 'danger' : 'success'} />
            <MetricCard label="Recorrentes" value={recorrentes.length} tone="success" />
            <MetricCard label="Produtividade" value={`${d.produtividade?.concluidas || 0}/${(d.produtividade?.concluidas || 0) + (d.produtividade?.pendentes || 0)}`} />
          </div>
          <div className="mt-5 rounded-2xl border border-orange-400/25 bg-orange-500/10 p-4">
            <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
              <div>
                <p className="text-xs font-black uppercase tracking-[0.18em] text-orange-200">Próxima ação obrigatória</p>
                <h3 className="mt-2 text-xl font-black text-white">{actionText}</h3>
                <p className="mt-1 text-sm text-orange-100/80">{vencidos.length ? 'Regularizar follow-up vencido antes de abrir nova frente.' : hoje.length ? 'Executar contato previsto para hoje.' : propostasParadas.length ? 'Destravar proposta parada.' : 'Escolher cliente sem contato e registrar o próximo movimento.'}</p>
              </div>
              <button onClick={() => setTaskForm({ ...taskForm, titulo: actionText, cliente_nome: nextAction?.cliente_nome || nextAction?.empresa || nextAction?.nome || activeClient?.nome || '', prioridade: vencidos.length ? 'alta' : 'media', etapa: nextAction?.pipeline_etapa || 'Operação' })} className="rounded-xl bg-orange-500 px-4 py-3 text-sm font-black text-white hover:bg-orange-400">Transformar em tarefa</button>
            </div>
          </div>
        </Section>

        <Section title="Fluxo do cliente" subtitle="Lead → Prospecção → Diagnóstico → Proposta → Negociação → Cliente → Operação → Demanda → Licitação → Peça → Cobrança → Recorrência.">
          <div className="mb-4 grid gap-3 md:grid-cols-3">
            <input value={filter} onChange={(e) => setFilter(e.target.value)} placeholder="Filtrar por cliente, etapa, origem, responsável ou status" className="input md:col-span-2" />
            <select value={selectedClient} onChange={(e) => setSelectedClient(e.target.value)} className="input">
              <option value="">Cliente em foco</option>
              {clientes.map((c) => <option key={c.key} value={c.key}>{c.nome}</option>)}
            </select>
          </div>
          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
            {fluxoCRM.map((stage, index) => {
              const cards = stageData[index] || []
              return <div key={stage} className="rounded-2xl border border-slate-800 bg-slate-950/50 p-3"><div className="flex items-center justify-between"><h3 className="text-sm font-black text-white">{stage}</h3><Badge value={cards.length} /></div><div className="mt-3 space-y-2">{cards.slice(0, 6).map((lead) => {
                const prazo = daysUntil(lead.follow_up_em)
                const atraso = prazo !== null && prazo < 0
                return <div key={lead.id || `${lead.nome}-${lead.empresa}`} className={`rounded-xl p-3 text-sm ${atraso ? 'bg-red-500/12 ring-1 ring-red-400/20' : 'bg-slate-900/80'}`}><div className="flex flex-wrap gap-1.5"><Badge value={lead.classificacao || 'C'} /><Badge value={atraso ? 'atraso' : `urgência ${lead.risco_churn || 0}`} /></div><p className="mt-2 font-bold text-white">{lead.empresa || lead.nome || lead.cliente_nome || lead.titulo}</p><p className="text-xs text-slate-400">{lead.responsavel || 'sem responsável'}</p><p className="mt-1 text-xs text-slate-500">Potencial {formatMoney(lead.potencial || lead.valor || 0)} · Ticket {formatMoney(lead.ticket_medio || 0)}</p>{lead.pipeline_etapa && <div className="mt-3 flex flex-wrap gap-2"><button disabled={saving} onClick={() => editLead(lead)} className="rounded-lg bg-slate-700 px-2 py-1 text-[11px] font-black text-white disabled:opacity-50">Editar</button><button disabled={saving} onClick={() => atualizarLead(lead, 'diagnóstico')} className="rounded-lg bg-indigo-600 px-2 py-1 text-[11px] font-black text-white disabled:opacity-50">Diagnóstico</button><button disabled={saving} onClick={() => atualizarLead(lead, 'proposta')} className="rounded-lg bg-blue-600 px-2 py-1 text-[11px] font-black text-white disabled:opacity-50">Proposta</button><button disabled={saving} onClick={() => atualizarLead(lead, 'negociação')} className="rounded-lg bg-purple-600 px-2 py-1 text-[11px] font-black text-white disabled:opacity-50">Negociar</button><button disabled={saving} onClick={() => atualizarLead(lead, 'ganho')} className="rounded-lg bg-emerald-600 px-2 py-1 text-[11px] font-black text-white disabled:opacity-50">Ganho</button><button disabled={saving} onClick={() => atualizarLead(lead, 'perdido')} className="rounded-lg bg-slate-700 px-2 py-1 text-[11px] font-black text-white disabled:opacity-50">Perdido</button><button disabled={saving} onClick={() => criarFollowupRapido(lead)} className="rounded-lg bg-orange-600 px-2 py-1 text-[11px] font-black text-white disabled:opacity-50">Follow-up</button><button disabled={saving} onClick={() => atualizarLead(lead, 'arquivado')} className="rounded-lg bg-slate-800 px-2 py-1 text-[11px] font-black text-white disabled:opacity-50">Arquivar</button></div>}</div>
              })}{!cards.length && <Empty text="Sem clientes." />}</div></div>
            })}
          </div>
        </Section>

        <div className="grid gap-6 xl:grid-cols-[1.1fr_0.9fr]">
          <Section title="Timeline operacional do cliente" subtitle="Histórico comercial, follow-ups e operação no mesmo painel.">
            {!activeClient ? <Empty text="Nenhum cliente na carteira ainda." /> : <div>
              <div className="mb-4 rounded-2xl border border-slate-800 bg-slate-950/50 p-4">
                <div className="flex flex-wrap gap-2"><Badge value={`etapa ${activeClient.etapa}`} /><Badge value={`risco ${activeClient.risco}`} /><Badge value={`ticket ${formatMoney(activeClient.ticket || 0)}`} /></div>
                <h3 className="mt-3 text-xl font-black text-white">{activeClient.nome}</h3>
                <p className="mt-1 text-sm text-slate-400">Potencial {formatMoney(activeClient.potencial || 0)} · Receita {formatMoney(activeClient.receita || 0)} · Follow-ups {activeClient.followups.length}</p>
                <div className="mt-4 grid gap-2 sm:grid-cols-3">
                  <div className="rounded-xl bg-slate-900/80 p-3"><p className="text-xs text-slate-500">Casos</p><strong className="text-white">{activeCentral?.casos || activeCases.length}</strong></div>
                  <div className="rounded-xl bg-slate-900/80 p-3"><p className="text-xs text-slate-500">Documentos</p><strong className="text-white">{activeCentral?.documentos || activeDocs.length}</strong></div>
                  <div className="rounded-xl bg-slate-900/80 p-3"><p className="text-xs text-slate-500">Peças</p><strong className="text-white">{activeCentral?.pecas || 0}</strong></div>
                  <div className="rounded-xl bg-slate-900/80 p-3"><p className="text-xs text-slate-500">Pendências</p><strong className="text-white">{activeCentral?.pendencias || activeClient.followups.length}</strong></div>
                  <div className="rounded-xl bg-slate-900/80 p-3"><p className="text-xs text-slate-500">Órgãos</p><strong className="text-white">{activeCentral?.orgaos_relacionados || new Set(activeCases.map((c) => c.orgao).filter(Boolean)).size}</strong></div>
                  <div className="rounded-xl bg-slate-900/80 p-3"><p className="text-xs text-slate-500">Concorrentes</p><strong className="text-white">{activeCentral?.concorrentes_relacionados || 0}</strong></div>
                </div>
                <div className="mt-4 rounded-2xl border border-blue-400/20 bg-blue-500/10 p-4">
                  <p className="text-xs font-black uppercase tracking-wide text-blue-200">Contexto operacional contínuo</p>
                  <div className="mt-3 grid gap-3 md:grid-cols-2">
                    <div><p className="text-xs text-blue-100/60">Próxima ação</p><p className="font-bold text-white">{activeNextText}</p></div>
                    <div><p className="text-xs text-blue-100/60">Responsável atual</p><p className="font-bold text-white">{activeClient.leads[0]?.responsavel || activeCriticalDemand?.responsavel || 'definir responsável'}</p></div>
                    <div><p className="text-xs text-blue-100/60">Follow-up pendente</p><p className="font-bold text-white">{activePendingFollowup?.titulo || (activeClient.followups.length ? 'acompanhar próximos contatos' : 'criar follow-up')}</p></div>
                    <div><p className="text-xs text-blue-100/60">Cobrança/recorrência</p><p className="font-bold text-white">{activeOverdueCharge ? `${activeOverdueCharge.status} · ${formatMoney(activeOverdueCharge.valor || 0)}` : `Recorrência ${formatMoney(activeClient.receita || 0)}`}</p></div>
                  </div>
                  <div className="mt-3 grid gap-2 md:grid-cols-3">
                    <div className="rounded-xl bg-slate-950/70 p-3"><p className="text-xs text-slate-500">Documento crítico</p><strong className="text-white">{activeDocs.find((d) => norm(d.status).includes('venc') || ['alta','critica','crítica'].includes(norm(d.criticidade)))?.titulo || 'sem bloqueio explícito'}</strong></div>
                    <div className="rounded-xl bg-slate-950/70 p-3"><p className="text-xs text-slate-500">Caso ativo</p><strong className="text-white">{activeCases[0]?.orgao || activeCases[0]?.objeto || 'sem caso vinculado'}</strong></div>
                    <div className="rounded-xl bg-slate-950/70 p-3"><p className="text-xs text-slate-500">Memória viva</p><strong className="text-white">{activeMemories[0]?.titulo || activeMemories[0]?.resumo || 'sem memória contextual'}</strong></div>
                  </div>
                </div>
                <div className="mt-4 flex flex-wrap gap-2"><button disabled={saving} onClick={() => criarFollowupRapido(activeClient.leads[0] || activeClient)} className="rounded-lg bg-orange-600 px-3 py-2 text-xs font-black text-white disabled:opacity-50">Registrar follow-up</button><button onClick={() => preencherAcaoCliente('tarefa', 'Revisar operação 360', activeClient.etapa || 'Operação', activeClient.risco >= 60 ? 'alta' : 'media')} className="rounded-lg bg-blue-600 px-3 py-2 text-xs font-black text-white">Criar próxima ação</button><button onClick={() => preencherAcaoCliente('financeiro', 'Cobrar honorário / inadimplência', 'Cobrança', 'alta')} className="rounded-lg bg-red-600 px-3 py-2 text-xs font-black text-white">Registrar cobrança</button><button onClick={() => preencherAcaoCliente('carteira', 'Atualizar recorrência e retenção', 'Recorrência', 'media')} className="rounded-lg bg-emerald-600 px-3 py-2 text-xs font-black text-white">Atualizar recorrência</button><button onClick={() => preencherAcaoCliente('tarefa', 'Abrir demanda operacional', 'Demanda', 'alta')} className="rounded-lg bg-slate-700 px-3 py-2 text-xs font-black text-white">Criar demanda</button></div>
              </div>
              <div className="space-y-3">{workflowEvents.slice(0, 10).map((event, idx) => <div key={`${event.tipo}-${idx}`} className="flex gap-3"><div className={`mt-1 h-3 w-3 rounded-full ${event.tom === 'danger' ? 'bg-red-400' : event.tom === 'warning' ? 'bg-orange-300' : 'bg-blue-300'}`} /><div className="flex-1 rounded-xl border border-slate-800 bg-slate-950/50 p-3"><div className="flex flex-wrap items-center gap-2"><Badge value={event.tipo} />{event.data && <span className="text-xs text-slate-500">{String(event.data).slice(0, 10)}</span>}</div><p className="mt-2 font-bold text-white">{event.titulo}</p><p className="text-sm text-slate-400">{event.texto}</p></div></div>)}{!workflowEvents.length && <Empty text="Sem eventos para este cliente." />}</div>
            </div>}
          </Section>

          <Section title="Follow-up visual" subtitle="Atrasados primeiro, depois ações de hoje e próximos contatos.">
            <div className="space-y-3">{[...vencidos, ...hoje, ...followups.filter((f) => daysUntil(f.data || f.follow_up_em || f.prazo) > 0)].slice(0, 12).map((f) => {
              const prazo = daysUntil(f.data || f.follow_up_em || f.prazo)
              return <div key={f.id || f.titulo} className={`rounded-xl border p-3 ${prazo < 0 ? 'border-red-400/25 bg-red-500/10' : prazo === 0 ? 'border-orange-400/25 bg-orange-500/10' : 'border-slate-800 bg-slate-950/50'}`}><div className="flex items-start justify-between gap-3"><div><Badge value={prazo < 0 ? `${Math.abs(prazo)}d atrasado` : prazo === 0 ? 'hoje' : `${prazo}d`} /><p className="mt-2 font-bold text-white">{f.titulo || f.cliente_nome || f.empresa || 'Follow-up'}</p><p className="text-xs text-slate-400">{f.responsavel || 'sem responsável'} · {f.status || 'pendente'}</p></div><div className="flex flex-col gap-2"><button disabled={saving} onClick={() => concluirFollowup(f)} className="rounded-lg bg-emerald-700 px-3 py-2 text-xs font-bold text-white hover:bg-emerald-600 disabled:opacity-50">Concluir</button><button disabled={saving} onClick={() => reagendarFollowup(f, 1)} className="rounded-lg bg-slate-800 px-3 py-2 text-xs font-bold text-white hover:bg-slate-700 disabled:opacity-50">Amanhã</button></div></div></div>
            })}{!followups.length && <Empty text="Nenhum follow-up registrado." />}</div>
          </Section>
        </div>

        <div className="grid gap-6 xl:grid-cols-2">
          <Section title={editingLead ? 'Editar lead / cliente' : 'Novo movimento comercial'} subtitle="Registre sem sair do fluxo: lead, diagnóstico, proposta ou recorrência.">
            <form onSubmit={saveLead} className="grid gap-3 md:grid-cols-2">
              <TextInput label="Nome do contato" required value={leadForm.nome} onChange={(v) => setLeadForm({ ...leadForm, nome: v })} />
              <TextInput label="Empresa / Cliente" value={leadForm.empresa} onChange={(v) => setLeadForm({ ...leadForm, empresa: v })} />
              <TextInput label="Origem" value={leadForm.origem} onChange={(v) => setLeadForm({ ...leadForm, origem: v })} />
              <label className="block"><span className="text-sm font-bold text-white">Status</span><select value={leadForm.status} onChange={(e) => setLeadForm({ ...leadForm, status: e.target.value, estagio_comercial: e.target.value })} className="input mt-2">{['novo','contato','diagnóstico','proposta','negociação','ganho','perdido'].map((s) => <option key={s} value={s}>{s}</option>)}</select></label>
              <label className="block"><span className="text-sm font-bold text-white">Etapa do pipeline</span><select value={leadForm.pipeline_etapa} onChange={(e) => setLeadForm({ ...leadForm, pipeline_etapa: e.target.value })} className="input mt-2">{fluxoLeadCRM.map((s) => <option key={s} value={s}>{s}</option>)}</select></label>
              <label className="block"><span className="text-sm font-bold text-white">Classificação</span><select value={leadForm.classificacao} onChange={(e) => setLeadForm({ ...leadForm, classificacao: e.target.value })} className="input mt-2">{['A','B','C'].map((s) => <option key={s} value={s}>{s}</option>)}</select></label>
              <TextInput label="Responsável" value={leadForm.responsavel} onChange={(v) => setLeadForm({ ...leadForm, responsavel: v })} />
              <TextInput label="Próximo follow-up" value={leadForm.follow_up_em} onChange={(v) => setLeadForm({ ...leadForm, follow_up_em: v })} />
              <TextInput label="Potencial" type="number" value={leadForm.potencial} onChange={(v) => setLeadForm({ ...leadForm, potencial: v })} />
              <TextInput label="Ticket" type="number" value={leadForm.ticket_medio} onChange={(v) => setLeadForm({ ...leadForm, ticket_medio: v })} />
              <TextInput label="Recorrência" type="number" value={leadForm.recorrencia} onChange={(v) => setLeadForm({ ...leadForm, recorrencia: v })} />
              <TextInput label="Risco churn 0-100" type="number" value={leadForm.risco_churn} onChange={(v) => setLeadForm({ ...leadForm, risco_churn: v })} />
              <TextInput label="Lucratividade" type="number" value={leadForm.lucratividade} onChange={(v) => setLeadForm({ ...leadForm, lucratividade: v })} />
              <TextInput label="Órgãos prioritários" value={leadForm.orgaos_prioritarios} onChange={(v) => setLeadForm({ ...leadForm, orgaos_prioritarios: v })} />
              <textarea value={leadForm.observacoes} onChange={(e) => setLeadForm({ ...leadForm, observacoes: e.target.value })} placeholder="Diagnóstico, barreiras, proposta, risco, cobrança ou recorrência..." className="input md:col-span-2" />
              <button disabled={saving} className="premium-button-primary md:col-span-2">{editingLead ? 'Atualizar lead' : 'Registrar movimento'}</button>{editingLead && <button type="button" onClick={() => { setEditingLead(null); setLeadForm({ nome: '', empresa: '', origem: 'manual', status: 'novo', estagio_comercial: 'novo', pipeline_etapa: 'Lead', follow_up_em: '', responsavel: '', potencial: 0, ticket_medio: 0, recorrencia: 0, risco_churn: 0, lucratividade: 0, classificacao: 'C', orgaos_prioritarios: '', observacoes: '' }) }} className="rounded-2xl bg-slate-800 px-4 py-3 font-black text-white md:col-span-2">Cancelar edição</button>}
            </form>
          </Section>
          <Section title={editingTask ? 'Editar demanda / tarefa' : 'Próxima ação da operação'} subtitle="Toda carteira precisa de responsável, prioridade e movimento seguinte.">
            <form onSubmit={saveTask} className="grid gap-3 md:grid-cols-2">
              <label className="block"><span className="text-sm font-bold text-white">Tipo</span><select value={taskForm.tipo} onChange={(e) => setTaskForm({ ...taskForm, tipo: e.target.value })} className="input mt-2">{consultorFullTipos.filter((t) => t !== 'lead').map((t) => <option key={t} value={t}>{t}</option>)}</select></label>
              <TextInput label="Ação obrigatória" required value={taskForm.titulo} onChange={(v) => setTaskForm({ ...taskForm, titulo: v })} />
              <TextInput label="Cliente" value={taskForm.cliente_nome} onChange={(v) => setTaskForm({ ...taskForm, cliente_nome: v })} />
              <label className="block"><span className="text-sm font-bold text-white">Etapa</span><select value={taskForm.etapa} onChange={(e) => setTaskForm({ ...taskForm, etapa: e.target.value })} className="input mt-2">{fluxoCRM.map((s) => <option key={s} value={s}>{s}</option>)}</select></label>
              <TextInput label="Status" value={taskForm.status} onChange={(v) => setTaskForm({ ...taskForm, status: v })} />
              <label className="block"><span className="text-sm font-bold text-white">Prioridade</span><select value={taskForm.prioridade} onChange={(e) => setTaskForm({ ...taskForm, prioridade: e.target.value })} className="input mt-2">{['alta','media','baixa'].map((s) => <option key={s} value={s}>{s}</option>)}</select></label>
              <TextInput label="Responsável" value={taskForm.responsavel} onChange={(v) => setTaskForm({ ...taskForm, responsavel: v })} />
              <TextInput label="Valor / Receita vinculada" type="number" value={taskForm.valor} onChange={(v) => setTaskForm({ ...taskForm, valor: v })} />
              <textarea value={taskForm.observacoes} onChange={(e) => setTaskForm({ ...taskForm, observacoes: e.target.value })} placeholder="O que precisa acontecer agora? contato, proposta, licitação, contrato, cobrança ou recorrência." className="input md:col-span-2" />
              <button disabled={saving} className="premium-button-primary md:col-span-2">{editingTask ? 'Atualizar ação' : 'Registrar próxima ação'}</button>{editingTask && <button type="button" onClick={() => { setEditingTask(null); setTaskForm({ tipo: 'tarefa', titulo: '', cliente_nome: '', etapa: 'Operação', status: 'pendente', prioridade: 'alta', responsavel: '', valor: 0, observacoes: '' }) }} className="rounded-2xl bg-slate-800 px-4 py-3 font-black text-white md:col-span-2">Cancelar edição</button>}
            </form>
          </Section>
        </div>

        <Section title="Cards de carteira" subtitle="Urgência, atraso, risco churn, potencial e ticket por cliente.">
          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">{clientes.slice(0, 12).map((c) => <button key={c.key} onClick={() => setSelectedClient(c.key)} className={`rounded-2xl border p-4 text-left transition hover:border-blue-400/40 ${selectedClient === c.key ? 'border-blue-400/60 bg-blue-500/10' : 'border-slate-800 bg-slate-950/50'}`}><div className="flex flex-wrap gap-2"><Badge value={`urgência ${c.urgencia || 0}`} /><Badge value={c.atraso ? 'atraso' : 'em dia'} /><Badge value={`churn ${c.risco || 0}`} /></div><h3 className="mt-3 font-black text-white">{c.nome}</h3><p className="mt-1 text-sm text-slate-400">Potencial {formatMoney(c.potencial || 0)}</p><p className="text-sm text-slate-400">Ticket {formatMoney(c.ticket || 0)}</p></button>)}{!clientes.length && <Empty text="Nenhum cliente cadastrado." />}</div>
        </Section>

        <Section title="Registros da operação" subtitle="Base de tarefas, finanças, portal, proposta, contrato, cobrança e recorrência."><FullTable items={itens} onStatus={atualizarRegistroConsultor} onEdit={editRegistroConsultor} onUpdate={atualizarRegistroConsultorCompleto} /></Section>
      </div>
    </StateGate>
  )
}

function Documental360() {
  const { data, loading, error, refresh } = useAsyncData(() => Promise.all([api.documentalDashboard(), api.documentalDocumentos({ limit: 300 }), api.dashboardMemorias().catch((err) => ({ erro: err.message, memorias: [], itens: [] }))]).then(([dashboard, documentos, memorias]) => ({ dashboard, documentos, memorias })), [])
  const [form, setForm] = useState({ escopo: 'empresa', empresa_nome: '', cliente_nome: '', tipo_documental: 'certidao', categoria: 'habilitação', titulo: '', validade: '', orgao_emissor: '', tags: '', criticidade: 'media', status: 'pendente', observacoes: '' })
  const [checklist, setChecklist] = useState({ empresa_nome: '', edital_texto: '', tipos_exigidos: '' })
  const [result, setResult] = useState(null)
  const [selectedFile, setSelectedFile] = useState(null)
  const [dossieEmpresa, setDossieEmpresa] = useState('')
  const [dossieResult, setDossieResult] = useState(null)
  const [empresaAtiva, setEmpresaAtiva] = useState('')
  const [atestadosBusca, setAtestadosBusca] = useState('')
  const [atestadosFiltro, setAtestadosFiltro] = useState('')
  const [saving, setSaving] = useState(false)
  const [feedback, setFeedback] = useState('')
  const [editingDoc, setEditingDoc] = useState(null)
  const d = data?.dashboard || {}
  const docs = data?.documentos?.itens || []
  const memoriasDocumentais = data?.memorias?.memorias || data?.memorias?.itens || data?.memorias?.recentes || []
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  const norm = (value) => String(value || '').trim().toLowerCase()
  const daysUntil = (value) => {
    if (!value) return null
    const date = new Date(value)
    if (Number.isNaN(date.getTime())) return null
    date.setHours(0, 0, 0, 0)
    return Math.ceil((date - today) / 86400000)
  }
  const empresaKey = (doc) => norm(doc.empresa_nome || doc.cliente_nome || doc.empresa || doc.cliente || 'sem empresa')
  const empresas = useMemo(() => {
    const map = new Map()
    docs.forEach((doc) => {
      const key = empresaKey(doc)
      const nome = doc.empresa_nome || doc.cliente_nome || doc.empresa || doc.cliente || 'Sem empresa definida'
      const atual = map.get(key) || { key, nome, docs: [], vencidos: 0, vencendo: 0, criticos: 0, pendentes: 0, atestados: 0, scoreSum: 0, scoreCount: 0 }
      const prazo = daysUntil(doc.validade)
      const status = norm(doc.status)
      atual.docs.push(doc)
      if (status.includes('vencido') || (prazo !== null && prazo < 0)) atual.vencidos += 1
      if (status.includes('vencendo') || (prazo !== null && prazo >= 0 && prazo <= 30)) atual.vencendo += 1
      if (['alta', 'critica', 'crítica'].includes(norm(doc.criticidade)) || Number(doc.risco_documental || 0) >= 60) atual.criticos += 1
      if (status.includes('pendente') || status.includes('inválido') || status.includes('invalido')) atual.pendentes += 1
      if (norm(doc.tipo_documental).includes('atestado') || norm(doc.categoria).includes('atestado')) atual.atestados += 1
      const score = Number(doc.score_documental ?? doc.score ?? 0)
      if (score) { atual.scoreSum += score; atual.scoreCount += 1 }
      map.set(key, atual)
    })
    return Array.from(map.values()).map((empresa) => {
      const base = empresa.scoreCount ? Math.round(empresa.scoreSum / empresa.scoreCount) : Number(d.score_documental_medio || 0) || 75
      const penalty = (empresa.vencidos * 18) + (empresa.vencendo * 7) + (empresa.criticos * 10) + (empresa.pendentes * 8)
      const score = Math.max(0, Math.min(100, base - penalty))
      const aptidao = score >= 80 && !empresa.vencidos && empresa.pendentes <= 1 ? 'apta' : score >= 55 && empresa.vencidos <= 1 ? 'parcialmente apta' : 'inapta'
      return { ...empresa, score, aptidao, risco: Math.max(0, 100 - score) }
    }).sort((a, b) => a.score - b.score)
  }, [docs, d.score_documental_medio])
  const activeEmpresa = empresas.find((empresa) => empresa.key === empresaAtiva) || empresas[0]
  const activeDocs = activeEmpresa ? activeEmpresa.docs : docs
  const activeMemoriasDocumentais = activeEmpresa ? memoriasDocumentais.filter((mem) => [mem.titulo, mem.conteudo, mem.resumo, mem.tags, mem.orgao].join(' ').toLowerCase().includes(activeEmpresa.key)).slice(0, 4) : []
  const globalScore = activeEmpresa?.score ?? Number(d.score_documental_medio || 0) ?? 0
  const semaforo = globalScore >= 80 ? { label: 'verde', color: 'emerald', text: 'Apta para competir' } : globalScore >= 55 ? { label: 'amarelo', color: 'orange', text: 'Apta com ressalvas' } : { label: 'vermelho', color: 'red', text: 'Risco de inabilitação' }
  const docsCriticos = activeDocs.filter((doc) => ['alta', 'critica', 'crítica'].includes(norm(doc.criticidade)) || Number(doc.risco_documental || 0) >= 60 || norm(doc.status).includes('vencido'))
  const vencimentosProximos = activeDocs.filter((doc) => { const prazo = daysUntil(doc.validade); return prazo !== null && prazo >= 0 && prazo <= 45 }).sort((a, b) => daysUntil(a.validade) - daysUntil(b.validade))
  const vencidos = activeDocs.filter((doc) => { const prazo = daysUntil(doc.validade); return prazo !== null && prazo < 0 })
  const aptas = empresas.filter((e) => e.aptidao === 'apta')
  const parciais = empresas.filter((e) => e.aptidao === 'parcialmente apta')
  const inaptas = empresas.filter((e) => e.aptidao === 'inapta')
  const timeline = activeDocs.flatMap((doc) => {
    const items = []
    const created = doc.criado_em || doc.created_at || doc.atualizado_em
    if (created) items.push({ tipo: 'upload', titulo: doc.titulo, data: created, texto: doc.tipo_documental || doc.categoria, tom: 'neutral' })
    const prazo = daysUntil(doc.validade)
    if (doc.validade) items.push({ tipo: prazo < 0 ? 'vencimento' : prazo <= 45 ? 'renovação' : 'validade', titulo: doc.titulo, data: doc.validade, texto: prazo < 0 ? `${Math.abs(prazo)} dia(s) vencido` : `${prazo} dia(s) restantes`, tom: prazo < 0 ? 'danger' : prazo <= 45 ? 'warning' : 'success' })
    if (norm(doc.status).includes('pendente') || norm(doc.status).includes('inválido') || norm(doc.status).includes('invalido')) items.push({ tipo: 'regularização', titulo: doc.titulo, data: doc.atualizado_em || created, texto: doc.observacoes || 'Exige regularização', tom: 'warning' })
    return items
  }).sort((a, b) => new Date(b.data || 0) - new Date(a.data || 0))
  const atestados = docs.filter((doc) => norm(doc.tipo_documental).includes('atestado') || norm(doc.categoria).includes('atestado') || norm(doc.titulo).includes('atestado'))
  const atestadosFiltrados = atestados.filter((doc) => {
    const text = [doc.titulo, doc.empresa_nome, doc.cliente_nome, doc.categoria, doc.tags, doc.observacoes, doc.orgao_emissor].join(' ').toLowerCase()
    return (!atestadosBusca || text.includes(atestadosBusca.toLowerCase())) && (!atestadosFiltro || text.includes(atestadosFiltro.toLowerCase()))
  })
  const checklistVisual = result ? [
    ...(result.faltantes || []).map((item) => ({ tipo: 'faltante', titulo: item, tom: 'danger', texto: 'Pode gerar inabilitação se exigido no edital.' })),
    ...(result.vencidos || []).map((item) => ({ tipo: 'vencido', titulo: item, tom: 'danger', texto: 'Regularizar antes do envio da habilitação.' })),
    ...(result.sugestoes_regularizacao || []).map((item) => ({ tipo: 'pendência', titulo: item, tom: 'warning', texto: 'Ação recomendada para reduzir risco.' })),
  ] : []
  const docContexto = (doc) => {
    const prazo = daysUntil(doc.validade)
    const risco = norm(doc.status).includes('vencido') || prazo < 0 ? 'bloqueio de habilitação' : ['alta','critica','crítica'].includes(norm(doc.criticidade)) ? 'risco alto de inabilitação' : prazo !== null && prazo <= 30 ? 'risco de vencimento próximo' : 'risco controlado'
    return {
      impacto: risco,
      caso_afetado: doc.caso_id || doc.payload?.caso_id || 'caso será afetado na próxima habilitação aplicável',
      checklist_afetado: doc.checklist_id || doc.payload?.checklist_id || doc.categoria || 'habilitação documental',
      contrato: doc.contrato_id || doc.payload?.contrato_id || 'sem contrato explícito',
      oportunidade: doc.oportunidade_id || doc.payload?.oportunidade_id || 'oportunidade não vinculada',
      prazo: prazo === null ? 'sem validade informada' : prazo < 0 ? `${Math.abs(prazo)}d vencido` : `${prazo}d para vencer`,
      acao: norm(doc.status).includes('venc') || prazo < 0 ? 'regularizar imediatamente antes de habilitar' : prazo !== null && prazo <= 30 ? 'iniciar renovação e anexar versão atualizada' : 'manter como suporte de habilitação/execução',
    }
  }
  const riscoChecklist = result?.risco_inabilitacao || (vencidos.length || docsCriticos.length ? 'alto' : 'baixo')
  async function save(e) {
    e.preventDefault(); setSaving(true); setFeedback('')
    try {
      const payload = { ...form, tags: String(form.tags || '').split(',').map((x) => x.trim()).filter(Boolean), validade: form.validade || null }
      if (editingDoc?.id) await api.documentalAtualizar(editingDoc.id, payload)
      else await api.documentalCriar(payload)
      setForm({ ...form, titulo: '', validade: '', tags: '', observacoes: '' })
      setEditingDoc(null)
      setFeedback(editingDoc?.id ? 'Documento atualizado. Saúde documental recalculada.' : 'Documento salvo. Saúde documental atualizada.')
      refresh()
    } catch (err) { setFeedback(err.message || 'Não foi possível salvar o documento.') }
    finally { setSaving(false) }
  }
  function editDocumento(doc) {
    setEditingDoc(doc)
    setForm({
      escopo: doc.escopo || 'empresa',
      empresa_nome: doc.empresa_nome || '',
      cliente_nome: doc.cliente_nome || '',
      tipo_documental: doc.tipo_documental || doc.tipo || 'certidao',
      categoria: doc.categoria || 'habilitação',
      titulo: doc.titulo || '',
      validade: doc.validade || '',
      orgao_emissor: doc.orgao_emissor || '',
      tags: (doc.tags || []).join?.(', ') || doc.tags || '',
      criticidade: doc.criticidade || 'media',
      status: doc.status || 'pendente',
      observacoes: doc.observacoes || '',
    })
  }
  async function atualizarDocumentoRapido(doc, patch) {
    if (!doc?.id) return
    setSaving(true); setFeedback('')
    try {
      const ctx = docContexto(doc)
      const normalizedPatch = { ...patch }
      if (normalizedPatch.status === 'regularizar') normalizedPatch.status = 'pendente'
      await api.documentalAtualizar(doc.id, { ...normalizedPatch, observacoes: `${doc.observacoes || ''}\nAção documental rápida. Impacto: ${ctx.impacto}. Caso afetado: ${ctx.caso_afetado}. Checklist: ${ctx.checklist_afetado}. Prazo: ${ctx.prazo}. Ação recomendada: ${ctx.acao}.`.trim(), payload: { ...(doc.payload || {}), contexto_operacional: ctx } }); setFeedback('Documento atualizado por ação rápida com contexto persistente.'); refresh()
    }
    catch (err) { setFeedback(err.message || 'Não foi possível atualizar o documento.') }
    finally { setSaving(false) }
  }
  async function runChecklist(e) {
    e.preventDefault(); setSaving(true)
    try {
      const response = await api.documentalChecklist({ ...checklist, tipos_exigidos: String(checklist.tipos_exigidos || '').split(',').map((x) => x.trim()).filter(Boolean) })
      setResult(response)
    } finally { setSaving(false) }
  }
  async function uploadDoc(e) {
    e.preventDefault(); if (!selectedFile) return; setSaving(true)
    try {
      await api.documentalUpload(selectedFile, { ...form, tags: String(form.tags || '').split(',').map((x) => x.trim()).filter(Boolean), validade: form.validade || null })
      setSelectedFile(null); setForm({ ...form, titulo: '', validade: '', tags: '', observacoes: '' }); setFeedback('Arquivo documental enviado e registrado.'); refresh()
    } catch (err) { setFeedback(err.message || 'Não foi possível enviar o arquivo documental.') }
    finally { setSaving(false) }
  }
  async function loadDossie(e) {
    e.preventDefault(); setSaving(true)
    try { setDossieResult(await api.documentalDossie(dossieEmpresa || activeEmpresa?.nome || form.empresa_nome || checklist.empresa_nome)) }
    finally { setSaving(false) }
  }
  return (
    <StateGate loading={loading} error={error} onRetry={refresh}>
      <div className="space-y-6">
        {feedback && <div className="rounded-2xl border border-emerald-400/25 bg-emerald-500/10 p-4 text-sm font-bold text-emerald-100">{feedback}</div>}
        <Section title="Documental Vivo Enterprise" subtitle="Centro de saúde documental empresarial: aptidão, risco, capacidade competitiva e próxima regularização." action={<button onClick={refresh} className="premium-button"><RefreshCcw size={15} className="mr-2 inline" />Atualizar</button>}>
          <div className="grid gap-5 xl:grid-cols-[0.9fr_1.1fr]">
            <div className={`rounded-3xl border p-6 ${semaforo.color === 'emerald' ? 'border-emerald-400/25 bg-emerald-500/10' : semaforo.color === 'orange' ? 'border-orange-400/25 bg-orange-500/10' : 'border-red-400/25 bg-red-500/10'}`}>
              <p className="text-xs font-black uppercase tracking-[0.22em] text-slate-300">Score documental</p>
              <div className="mt-3 flex items-end gap-3"><span className="text-7xl font-black tracking-tight text-white">{globalScore}</span><span className="pb-3 text-lg font-black text-slate-400">/100</span></div>
              <div className="mt-4 flex flex-wrap gap-2"><Badge value={`semáforo ${semaforo.label}`} /><Badge value={semaforo.text} /><Badge value={activeEmpresa?.nome || 'visão geral'} /></div>
              <p className="mt-4 text-sm leading-6 text-slate-300">O consultor deve priorizar documentos vencidos, críticos e pendentes antes de avançar com habilitação em nova licitação.</p>
            </div>
            <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
              <MetricCard label="Documentos críticos" value={docsCriticos.length} tone={docsCriticos.length ? 'danger' : 'success'} />
              <MetricCard label="Vencimentos próximos" value={vencimentosProximos.length} tone={vencimentosProximos.length ? 'warning' : 'success'} />
              <MetricCard label="Vencidos" value={vencidos.length || d.documentos_vencidos || 0} tone={(vencidos.length || d.documentos_vencidos) ? 'danger' : 'success'} />
              <MetricCard label="Atestados" value={atestados.length || d.atestados_estrategicos || 0} />
              <MetricCard label="Empresas aptas" value={aptas.length} tone="success" />
              <MetricCard label="Parcialmente aptas" value={parciais.length} tone={parciais.length ? 'warning' : 'success'} />
              <MetricCard label="Inaptas" value={inaptas.length} tone={inaptas.length ? 'danger' : 'success'} />
              <MetricCard label="Total documentos" value={d.total_documentos || docs.length} />
            </div>
          </div>
        </Section>

        <Section title="Empresa em foco" subtitle="Abra o cliente e entenda instantaneamente situação documental, risco e capacidade competitiva.">
          <div className="grid gap-4 xl:grid-cols-[0.8fr_1.2fr]">
            <div className="space-y-3">
              <input value={dossieEmpresa} onChange={(e) => setDossieEmpresa(e.target.value)} placeholder="Buscar empresa/cliente" className="input" />
              <div className="max-h-[420px] space-y-2 overflow-y-auto pr-1 mobile-scroll">{empresas.map((empresa) => <button key={empresa.key} onClick={() => { setEmpresaAtiva(empresa.key); setDossieEmpresa(empresa.nome); setChecklist({ ...checklist, empresa_nome: empresa.nome }); setForm({ ...form, empresa_nome: empresa.nome }) }} className={`w-full rounded-2xl border p-4 text-left transition hover:border-blue-400/40 ${activeEmpresa?.key === empresa.key ? 'border-blue-400/60 bg-blue-500/10' : 'border-slate-800 bg-slate-950/50'}`}><div className="flex items-center justify-between gap-3"><p className="font-black text-white">{empresa.nome}</p><Badge value={empresa.aptidao} /></div><p className="mt-2 text-sm text-slate-400">Score {empresa.score} · críticos {empresa.criticos} · vencendo {empresa.vencendo}</p></button>)}{!empresas.length && <Empty text="Nenhuma empresa documental cadastrada." />}</div>
            </div>
            <div className="grid gap-4 md:grid-cols-3">
              <div className="rounded-2xl border border-slate-800 bg-slate-950/50 p-4"><p className="text-xs font-black uppercase tracking-wide text-slate-500">Situação documental</p><p className="mt-2 text-2xl font-black text-white">{activeEmpresa?.aptidao || 'sem dados'}</p><p className="mt-2 text-sm text-slate-400">{activeDocs.length} documento(s) analisados.</p></div>
              <div className="rounded-2xl border border-slate-800 bg-slate-950/50 p-4"><p className="text-xs font-black uppercase tracking-wide text-slate-500">Risco</p><p className="mt-2 text-2xl font-black text-white">{activeEmpresa?.risco ?? 0}</p><p className="mt-2 text-sm text-slate-400">Quanto maior, maior risco de inabilitação.</p></div>
              <div className="rounded-2xl border border-slate-800 bg-slate-950/50 p-4"><p className="text-xs font-black uppercase tracking-wide text-slate-500">Capacidade competitiva</p><p className="mt-2 text-2xl font-black text-white">{(activeEmpresa?.atestados || 0) >= 3 ? 'forte' : (activeEmpresa?.atestados || 0) ? 'moderada' : 'baixa'}</p><p className="mt-2 text-sm text-slate-400">Baseada em atestados e aderência documental.</p></div>
              <div className="md:col-span-3 rounded-2xl border border-slate-800 bg-slate-950/50 p-4"><p className="text-xs font-black uppercase tracking-wide text-slate-500">Próxima regularização</p><p className="mt-2 text-lg font-black text-white">{docsCriticos[0]?.titulo || vencimentosProximos[0]?.titulo || 'Manter monitoramento documental'}</p><p className="mt-1 text-sm text-slate-400">{docsCriticos.length ? 'Corrigir documento crítico antes de disputar.' : vencimentosProximos.length ? 'Renovar antes do vencimento.' : 'Carteira sem bloqueio documental imediato.'}</p></div>
              <div className="md:col-span-3 rounded-2xl border border-purple-400/20 bg-purple-500/10 p-4"><p className="text-xs font-black uppercase tracking-wide text-purple-200">Memória viva documental</p><p className="mt-2 text-sm text-purple-50">{activeMemoriasDocumentais[0]?.titulo || activeMemoriasDocumentais[0]?.resumo || 'Sem padrão documental registrado para esta empresa; registrar aprendizado se houver inabilitação, atraso ou exigência recorrente.'}</p></div>
            </div>
          </div>
        </Section>

        <div className="grid gap-6 xl:grid-cols-[1fr_0.9fr]">
          <Section title="Timeline documental" subtitle="Uploads, renovações, vencimentos e regularizações por empresa.">
            <div className="space-y-3">{timeline.slice(0, 14).map((event, idx) => <div key={`${event.tipo}-${event.titulo}-${idx}`} className="flex gap-3"><div className={`mt-1 h-3 w-3 rounded-full ${event.tom === 'danger' ? 'bg-red-400' : event.tom === 'warning' ? 'bg-orange-300' : event.tom === 'success' ? 'bg-emerald-300' : 'bg-blue-300'}`} /><div className="flex-1 rounded-xl border border-slate-800 bg-slate-950/50 p-3"><div className="flex flex-wrap items-center gap-2"><Badge value={event.tipo} />{event.data && <span className="text-xs text-slate-500">{String(event.data).slice(0, 10)}</span>}</div><p className="mt-2 font-bold text-white">{event.titulo}</p><p className="text-sm text-slate-400">{event.texto}</p></div></div>)}{!timeline.length && <Empty text="Sem eventos documentais para esta empresa." />}</div>
          </Section>
          <Section title="Vencimentos e críticos" subtitle="O que pode bloquear habilitação primeiro.">
            <div className="space-y-3">{[...vencidos, ...vencimentosProximos, ...docsCriticos].slice(0, 12).map((doc) => { const prazo = daysUntil(doc.validade); return <div key={doc.id || doc.titulo} className={`rounded-xl border p-3 ${prazo < 0 ? 'border-red-400/25 bg-red-500/10' : prazo <= 30 ? 'border-orange-400/25 bg-orange-500/10' : 'border-slate-800 bg-slate-950/50'}`}><div className="flex flex-wrap gap-2"><Badge value={doc.tipo_documental || doc.categoria} /><Badge value={prazo === null ? doc.status : prazo < 0 ? `${Math.abs(prazo)}d vencido` : `${prazo}d`} /></div><p className="mt-2 font-bold text-white">{doc.titulo}</p><p className="text-xs text-slate-400">{doc.empresa_nome || doc.cliente_nome || 'sem empresa'} · {doc.orgao_emissor || 'sem emissor'}</p><div className="mt-3 flex flex-wrap gap-2"><button disabled={saving} onClick={() => editDocumento(doc)} className="crud-button-primary">Editar</button><button disabled={saving} onClick={() => atualizarDocumentoRapido(doc, { status: 'pendente', criticidade: 'alta' })} className="crud-button-warning">Regularizar</button><button disabled={saving} onClick={() => atualizarDocumentoRapido(doc, { status: 'válido', criticidade: 'baixa' })} className="crud-button-success">Marcar válido</button></div></div> })}{![...vencidos, ...vencimentosProximos, ...docsCriticos].length && <Empty text="Sem bloqueios imediatos." />}</div>
          </Section>
        </div>

        <div className="grid gap-6 xl:grid-cols-2">
          <Section title="Checklist visual por licitação" subtitle="Faltantes, riscos, pendências e urgência antes de protocolar habilitação.">
            <form onSubmit={runChecklist} className="space-y-3">
              <TextInput label="Empresa" value={checklist.empresa_nome} onChange={(v) => setChecklist({ ...checklist, empresa_nome: v })} />
              <TextInput label="Tipos exigidos (opcional)" value={checklist.tipos_exigidos} onChange={(v) => setChecklist({ ...checklist, tipos_exigidos: v })} />
              <textarea value={checklist.edital_texto} onChange={(e) => setChecklist({ ...checklist, edital_texto: e.target.value })} placeholder="Cole trecho do edital para inferir certidões, balanço, atestados, fiscal/trabalhista..." className="input min-h-32" />
              <button disabled={saving} className="rounded-2xl bg-emerald-600 px-4 py-3 font-black text-white disabled:opacity-60">Gerar checklist</button>
            </form>
            <div className="mt-4 grid gap-3 md:grid-cols-3"><MetricCard label="Risco" value={riscoChecklist} tone={String(riscoChecklist).includes('alto') ? 'danger' : String(riscoChecklist).includes('médio') || String(riscoChecklist).includes('medio') ? 'warning' : 'success'} /><MetricCard label="Faltantes" value={(result?.faltantes || []).length} tone={(result?.faltantes || []).length ? 'danger' : 'success'} /><MetricCard label="Pendências" value={checklistVisual.length} tone={checklistVisual.length ? 'warning' : 'success'} /></div>
            {checklistVisual.length > 0 && <div className="mt-4 space-y-2">{checklistVisual.slice(0, 10).map((item, idx) => <div key={`${item.tipo}-${idx}`} className={`rounded-xl border p-3 ${item.tom === 'danger' ? 'border-red-400/25 bg-red-500/10' : 'border-orange-400/25 bg-orange-500/10'}`}><Badge value={item.tipo} /><p className="mt-2 font-bold text-white">{item.titulo}</p><p className="text-sm text-slate-400">{item.texto}</p></div>)}</div>}
          </Section>

          <Section title="Biblioteca de atestados premium" subtitle="Busca por objeto, CNAE, quantitativos, similaridade e capacidade técnica.">
            <div className="grid gap-3 md:grid-cols-2"><input value={atestadosBusca} onChange={(e) => setAtestadosBusca(e.target.value)} placeholder="Buscar atestado, objeto, órgão ou empresa" className="input" /><input value={atestadosFiltro} onChange={(e) => setAtestadosFiltro(e.target.value)} placeholder="Filtro: CNAE, quantitativo, marca, serviço..." className="input" /></div>
            <div className="mt-4 space-y-3">{atestadosFiltrados.slice(0, 12).map((doc) => { const texto = [doc.observacoes, doc.tags, doc.categoria].join(' '); const similaridade = atestadosBusca ? Math.min(98, 55 + atestadosBusca.split(' ').filter((term) => norm(texto).includes(norm(term))).length * 12) : Number(doc.score_documental || 70); return <div key={doc.id || doc.titulo} className="rounded-xl border border-slate-800 bg-slate-950/50 p-4"><div className="flex flex-wrap gap-2"><Badge value={`similaridade ${similaridade}%`} /><Badge value={doc.status || 'ativo'} /><Badge value={doc.empresa_nome || doc.cliente_nome || 'empresa'} /></div><p className="mt-2 font-black text-white">{doc.titulo}</p><p className="mt-1 text-sm text-slate-400">{doc.orgao_emissor || 'órgão não informado'}</p><p className="mt-2 text-xs text-slate-500">CNAE/quantitativos/capacidade: {doc.observacoes || doc.tags || 'não detalhado'}</p></div> })}{!atestadosFiltrados.length && <Empty text="Nenhum atestado encontrado para os filtros." />}</div>
          </Section>
        </div>

        <div className="grid gap-6 xl:grid-cols-2">
          <Section title={editingDoc ? 'Editar documento' : 'Registrar ou atualizar documento'} subtitle="Cadastre certidões, balanços, atestados, procurações, alvarás, compliance e documentos técnicos.">
            <form onSubmit={save} className="grid gap-3 md:grid-cols-2">
              <label className="block"><span className="text-sm font-bold text-white">Escopo</span><select value={form.escopo} onChange={(e) => setForm({ ...form, escopo: e.target.value })} className="input mt-2"><option value="empresa">Empresa Documental</option><option value="cliente">Cliente Documental</option></select></label>
              <TextInput label="Empresa" value={form.empresa_nome} onChange={(v) => setForm({ ...form, empresa_nome: v })} />
              <TextInput label="Cliente" value={form.cliente_nome} onChange={(v) => setForm({ ...form, cliente_nome: v })} />
              <label className="block"><span className="text-sm font-bold text-white">Tipo documental</span><select value={form.tipo_documental} onChange={(e) => setForm({ ...form, tipo_documental: e.target.value })} className="input mt-2">{['contrato_social','alteracao_contratual','cartao_cnpj','certidao','balanco','indices_contabeis','atestado','procuracao','alvara','iso','compliance','declaracao','documento_tecnico','documento_trabalhista','documento_fiscal'].map((t) => <option key={t} value={t}>{t}</option>)}</select></label>
              <TextInput label="Título" required value={form.titulo} onChange={(v) => setForm({ ...form, titulo: v })} />
              <TextInput label="Categoria" value={form.categoria} onChange={(v) => setForm({ ...form, categoria: v })} />
              <TextInput label="Validade (YYYY-MM-DD)" value={form.validade} onChange={(v) => setForm({ ...form, validade: v })} />
              <TextInput label="Órgão emissor" value={form.orgao_emissor} onChange={(v) => setForm({ ...form, orgao_emissor: v })} />
              <TextInput label="Tags" value={form.tags} onChange={(v) => setForm({ ...form, tags: v })} />
              <label className="block"><span className="text-sm font-bold text-white">Criticidade</span><select value={form.criticidade} onChange={(e) => setForm({ ...form, criticidade: e.target.value })} className="input mt-2">{['baixa','media','alta','critica'].map((t) => <option key={t} value={t}>{t}</option>)}</select></label>
              <label className="block"><span className="text-sm font-bold text-white">Status</span><select value={form.status} onChange={(e) => setForm({ ...form, status: e.target.value })} className="input mt-2">{['válido','vencendo','vencido','pendente','inválido','arquivado'].map((t) => <option key={t} value={t}>{t}</option>)}</select></label>
              <textarea value={form.observacoes} onChange={(e) => setForm({ ...form, observacoes: e.target.value })} placeholder="Quantitativos do atestado, CNAE, capacidade técnica, regularização necessária..." className="input md:col-span-2" />
              <button disabled={saving} className="rounded-2xl bg-blue-600 px-4 py-3 font-black text-white disabled:opacity-60 md:col-span-2">{editingDoc ? 'Atualizar documento' : 'Registrar documento'}</button>{editingDoc && <button type="button" onClick={() => { setEditingDoc(null); setForm({ escopo: 'empresa', empresa_nome: '', cliente_nome: '', tipo_documental: 'certidao', categoria: 'habilitação', titulo: '', validade: '', orgao_emissor: '', tags: '', criticidade: 'media', status: 'pendente', observacoes: '' }) }} className="rounded-2xl bg-slate-800 px-4 py-3 font-black text-white md:col-span-2">Cancelar edição</button>}
            </form>
          </Section>
          <div className="space-y-6">
            <Section title="Upload documental" subtitle="Anexe arquivos ao repositório empresarial com segurança e rastreabilidade.">
              <form onSubmit={uploadDoc} className="space-y-3">
                <input type="file" onChange={(e) => setSelectedFile(e.target.files?.[0] || null)} className="input" />
                <p className="text-xs text-slate-500">Tipos aceitos: PDF, DOCX, TXT, PNG, JPG, WEBP, XLSX e CSV. Arquivos ficam em diretório protegido.</p>
                <button disabled={saving || !selectedFile} className="rounded-2xl bg-blue-600 px-4 py-3 font-black text-white disabled:opacity-60">Enviar arquivo documental</button>
              </form>
            </Section>
            <Section title="Dossiê empresarial" subtitle="Score, pendências, riscos, vencimentos e aptidão licitatória.">
              <form onSubmit={loadDossie} className="flex gap-3"><input value={dossieEmpresa} onChange={(e) => setDossieEmpresa(e.target.value)} placeholder="Empresa/cliente" className="input" /><button disabled={saving} className="rounded-2xl bg-emerald-600 px-4 py-3 font-black text-white disabled:opacity-60">Consultar</button></form>
              {dossieResult && <div className="mt-4 rounded-2xl border border-slate-800 bg-slate-950/70 p-4"><Badge value={dossieResult.aptidao_licitatoria} /><p className="mt-2 font-bold text-white">Score {dossieResult.score_documental}</p><p className="mt-1 text-sm text-slate-400">Válidos {dossieResult.documentos_validos} · pendências {dossieResult.pendencias} · riscos {dossieResult.riscos} · atestados {(dossieResult.capacidade_tecnica || []).length}</p></div>}
            </Section>
          </div>
        </div>

        <div className="grid gap-6 xl:grid-cols-3">
          <Section title="Status documental" subtitle="Válidos, vencendo, vencidos, pendentes e inválidos."><MiniBarChart title="Por status" data={d.por_status || {}} /></Section>
          <Section title="Tipos documentais" subtitle="Biblioteca documental e atestados."><MiniBarChart title="Por tipo" data={d.por_tipo || {}} /></Section>
          <Section title="Alertas críticos" subtitle="Pré-vencimento, vencidos e pendências."><FullList title="Alertas" items={(d.alertas || []).map((a) => ({ ...a, titulo: a.mensagem, tipo: a.tipo }))} /></Section>
        </div>
        <Section title="Painel documentos críticos" subtitle="Validade, risco documental, score e aptidão licitatória.">
          <FullTable items={activeDocs.map((doc) => ({ ...doc, tipo: doc.tipo_documental, valor: doc.risco_documental, score: doc.score_documental, cliente_nome: doc.empresa_nome || doc.cliente_nome }))} onEdit={editDocumento} onUpdate={atualizarDocumentoRapido} onStatus={(doc, status) => atualizarDocumentoRapido(doc, { status })} />
        </Section>
      </div>
    </StateGate>
  )
}

function FullList({ title, items }) {
  return <div className="rounded-2xl border border-slate-800 bg-slate-950/50 p-4"><h3 className="font-black text-white">{title}</h3><div className="mt-3 space-y-2">{!items.length ? <Empty text="Sem registros." /> : items.slice(0, 6).map((i) => <div key={i.id} className="rounded-xl bg-slate-900/70 p-3 text-sm"><div className="flex flex-wrap gap-2"><Badge value={i.tipo} /><Badge value={i.status} /></div><p className="mt-2 font-bold text-white">{i.titulo}</p><p className="text-xs text-slate-500">{i.orgao || i.cliente_nome || i.responsavel || 'sem vínculo'}</p></div>)}</div></div>
}

function FullTable({ items, onStatus, onEdit, onUpdate }) {
  const [quickItem, setQuickItem] = useState(null)
  const [patch, setPatch] = useState({ status: '', prioridade: '', observacoes: '' })
  if (!items.length) return <Empty text="Nenhum registro encontrado." />
  function openQuick(item) {
    setQuickItem(item)
    setPatch({ status: item.status || 'em andamento', prioridade: item.prioridade || item.criticidade || 'media', observacoes: item.observacoes || '' })
  }
  async function saveQuick(event) {
    event.preventDefault()
    if (!quickItem || !onUpdate) return
    await onUpdate(quickItem, patch)
    setQuickItem(null)
  }
  return <div className="space-y-4">
    <div className="overflow-x-auto mobile-scroll"><table className="w-full min-w-[1080px] text-left text-sm"><thead className="text-xs uppercase text-slate-500"><tr><th className="px-3 py-3">Tipo</th><th>Título</th><th>Vínculo</th><th>Status</th><th>Score/Risco</th><th>Valor</th><th>Atualizado</th><th className="sticky-actions px-3 py-3">Ações</th></tr></thead><tbody>{items.slice(0, 200).map((i) => <tr key={i.id} className="table-row text-slate-300"><td className="px-3 py-4"><Badge value={i.tipo} /></td><td className="px-3 py-4 font-bold text-white">{i.titulo}</td><td className="px-3 py-4">{i.orgao || i.cliente_nome || i.contrato_id || '—'}</td><td className="px-3 py-4"><Badge value={i.status} /></td><td className="px-3 py-4">{i.risco_score ?? i.score ?? 0}</td><td className="px-3 py-4">{formatMoney(i.valor || 0)}</td><td className="px-3 py-4">{formatDate(i.atualizado_em || i.updated_at)}</td><td className="sticky-actions px-3 py-4"><div className="crud-action-bar"><span className="crud-action-label">Ações</span>
      {onEdit && <button onClick={() => onEdit(i)} className="crud-button-primary">Editar</button>}
      {onUpdate && <button onClick={() => openQuick(i)} className="crud-button-warning">Ação rápida</button>}
      {onStatus && <button onClick={() => onStatus(i, 'concluido')} className="crud-button-success">Concluir</button>}
      {onStatus && <button onClick={() => onStatus(i, 'regularizar')} className="crud-button-warning">Regularizar</button>}
      {onStatus && <button onClick={() => onStatus(i, 'arquivado')} className="crud-button">Arquivar</button>}
    </div></td></tr>)}</tbody></table>{items.length > 200 && <p className="mt-3 text-xs text-slate-500">Mostrando 200 de {items.length} registros. Use filtros/tipo para reduzir a lista.</p>}</div>
    {quickItem && <form onSubmit={saveQuick} className="rounded-2xl border border-blue-400/25 bg-blue-500/10 p-4">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-end">
        <div className="min-w-0 flex-1"><p className="text-xs font-black uppercase tracking-wide text-blue-200">Ação rápida</p><h3 className="mt-1 font-black text-white">{quickItem.titulo}</h3><p className="mt-1 text-xs text-slate-400">Atualize status, prioridade/risco e observação sem sair da tabela.</p></div>
        <label className="block min-w-44"><span className="text-xs font-bold text-slate-300">Status</span><select value={patch.status} onChange={(e) => setPatch({ ...patch, status: e.target.value })} className="input mt-1">{operationalStatuses.map((s) => <option key={s} value={s}>{s}</option>)}</select></label>
        <label className="block min-w-40"><span className="text-xs font-bold text-slate-300">Prioridade/Risco</span><select value={patch.prioridade} onChange={(e) => setPatch({ ...patch, prioridade: e.target.value, criticidade: e.target.value })} className="input mt-1">{['baixa','media','alta','critica'].map((s) => <option key={s} value={s}>{s}</option>)}</select></label>
        <input value={patch.observacoes} onChange={(e) => setPatch({ ...patch, observacoes: e.target.value })} placeholder="Adicionar observação operacional" className="input min-w-64 flex-1" />
        <button className="rounded-xl bg-blue-600 px-4 py-3 text-sm font-black text-white hover:bg-blue-500">Salvar</button>
        <button type="button" onClick={() => setQuickItem(null)} className="rounded-xl bg-slate-800 px-4 py-3 text-sm font-black text-white hover:bg-slate-700">Fechar</button>
      </div>
    </form>}
  </div>
}

function StructuralModule({ item, profile }) {
  return (
    <div className="space-y-6">
      <Section title={item?.label || 'Área operacional'} subtitle={`Perfil ${profile?.configuracao?.nome || 'operacional'} · área disponível na navegação`}>
        <div className="rounded-2xl border border-slate-800 bg-slate-950/50 p-6">
          <Badge value="área operacional" />
          <h2 className="mt-4 text-2xl font-black text-white">{item?.label || 'Área'} disponível no fluxo</h2>
          <p className="mt-2 text-sm leading-6 text-slate-300">
            Esta área direciona para os fluxos ativos do perfil. Use os painéis relacionados para executar a rotina com histórico e rastreabilidade.
          </p>
          <div className="mt-5 grid gap-4 md:grid-cols-2">
            <div>
              <p className="text-xs font-bold uppercase tracking-wide text-slate-500">Linguagem do perfil</p>
              <p className="mt-2 text-sm text-slate-300">{profile?.configuracao?.linguagem_recomendada}</p>
            </div>
            <div>
              <p className="text-xs font-bold uppercase tracking-wide text-slate-500">Prioridades</p>
              <div className="mt-2 flex flex-wrap gap-2">
                {(profile?.configuracao?.prioridades || []).slice(0, 8).map((priority) => <Badge key={priority} value={priority} />)}
                
              </div>
            </div>
          </div>
        </div>
      </Section>
    </div>
  )
}

function LoginScreen({ onLogin }) {
  const [usuario, setUsuario] = useState('')
  const [senha, setSenha] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  async function submit(event) {
    event.preventDefault()
    setLoading(true)
    setError('')
    try {
      const result = await api.login({ usuario, senha })
      setStoredSession(result.access_token, result.usuario)
      api.setAuthToken(result.access_token)
      onLogin(result.usuario)
    } catch (err) {
      clearStoredSession()
      api.setAuthToken('')
      setError('Usuário ou senha inválidos. Confira as credenciais e tente novamente.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-950 px-4 py-10">
      <div className="w-full max-w-md rounded-3xl border border-slate-800 bg-slate-900/80 p-8 shadow-2xl shadow-black/40">
        <div className="mb-8 text-center">
          <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-3xl bg-blue-500/15 text-3xl ring-1 ring-blue-400/30">⚖️</div>
          <h1 className="mt-4 text-3xl font-black text-white">Entrar na LICI</h1>
          <p className="mt-2 text-sm text-slate-400">Acesse sua central de operação em licitações.</p>
        </div>

        <form onSubmit={submit} className="space-y-4">
          <div>
            <label className="text-sm font-bold text-slate-300">Usuário</label>
            <input
              value={usuario}
              onChange={(event) => setUsuario(event.target.value)}
              autoComplete="username"
              className="mt-2 w-full rounded-2xl border border-slate-700 bg-slate-950 px-4 py-3 text-white outline-none ring-blue-400/30 focus:ring-4"
              placeholder="admin"
              required
            />
          </div>
          <div>
            <label className="text-sm font-bold text-slate-300">Senha</label>
            <input
              value={senha}
              onChange={(event) => setSenha(event.target.value)}
              type="password"
              autoComplete="current-password"
              className="mt-2 w-full rounded-2xl border border-slate-700 bg-slate-950 px-4 py-3 text-white outline-none ring-blue-400/30 focus:ring-4"
              placeholder="••••••••"
              required
            />
          </div>

          {error && (
            <div className="rounded-2xl border border-red-400/30 bg-red-500/10 p-3 text-sm text-red-100">
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={loading}
            className="flex w-full items-center justify-center rounded-2xl bg-blue-600 px-4 py-3 font-black text-white shadow-lg shadow-blue-950/40 hover:bg-blue-500 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {loading && <Loader2 className="mr-2 animate-spin" size={18} />}
            Entrar
          </button>
        </form>
      </div>
    </div>
  )
}

const userProfileToOperational = {
  admin: 'fornecedor',
  consultor: 'consultor',
  fornecedor: 'fornecedor',
  comprador: 'comprador',
  leitura: 'fornecedor',
}

export default function App() {
  const stored = getStoredSession()
  const [current, setCurrent] = useState('dashboard')
  const [sessionUser, setSessionUser] = useState(stored.user)
  const [sessionLoading, setSessionLoading] = useState(Boolean(stored.token))
  const [profile, setProfile] = useState(null)
  const [profileOptions, setProfileOptions] = useState([])
  const [profileLoading, setProfileLoading] = useState(true)
  const [profileError, setProfileError] = useState('')

  function logout() {
    clearStoredSession()
    api.setAuthToken('')
    setSessionUser(null)
    setCurrent('dashboard')
  }

  async function loadProfile(user = sessionUser) {
    setProfileLoading(true)
    setProfileError('')
    try {
      const [actual, configs] = await Promise.all([api.perfilAtual(), api.perfilConfiguracoes()])
      const options = configs.perfis || []
      const targetProfile = user?.perfil_operacional || userProfileToOperational[user?.perfil] || actual?.perfil_atual || 'fornecedor'
      let nextProfile = actual
      if (targetProfile && actual?.perfil_atual !== targetProfile) {
        nextProfile = await api.selecionarPerfil(targetProfile, 'Selecionado automaticamente pelo perfil do usuário autenticado')
      }
      setProfile(nextProfile)
      setProfileOptions(options)
    } catch (err) {
      setProfileError(err.message || 'erro ao carregar perfil')
      setProfileOptions([{ id: 'fornecedor', nome: 'Fornecedor / Empresário' }])
      setProfile({ perfil_atual: 'fornecedor', configuracao: { id: 'fornecedor', nome: 'Fornecedor / Empresário', menus: fallbackNavigation, prioridades: [], linguagem_recomendada: 'Perfil fornecedor padrão em fallback.' } })
    } finally {
      setProfileLoading(false)
    }
  }

  useEffect(() => {
    setUnauthorizedHandler(logout)
    if (!stored.token) {
      setSessionLoading(false)
      setProfileLoading(false)
      return
    }
    api.setAuthToken(stored.token)
    api.me()
      .then((result) => {
        setSessionUser(result.usuario)
        setStoredSession(stored.token, result.usuario)
        return loadProfile(result.usuario)
      })
      .catch(() => logout())
      .finally(() => setSessionLoading(false))
  }, [])

  useEffect(() => {
    if (sessionUser) loadProfile(sessionUser)
  }, [sessionUser?.id])

  const dynamicNavigation = useMemo(() => normalizeNavigation(profile), [profile])

  async function handleLogin(user) {
    setSessionUser(user)
    await loadProfile(user)
  }

  async function selectProfile(perfil) {
    setProfileLoading(true)
    setProfileError('')
    try {
      const next = await api.selecionarPerfil(perfil, 'Selecionado pela interface frontend')
      setProfile(next)
      setCurrent('dashboard')
      const configs = await api.perfilConfiguracoes()
      setProfileOptions(configs.perfis || [])
    } catch (err) {
      setProfileError(err.message || 'erro ao selecionar perfil')
    } finally {
      setProfileLoading(false)
    }
  }

  const page = useMemo(() => {
    const pages = {
      dashboard: <CentralOperacional profile={profile} onNavigate={setCurrent} />,
      central: <CentralOperacional profile={profile} onNavigate={setCurrent} />,
      busca: <BuscaGlobal />,
      chat: <ChatLici />,
      'ia-assistiva': <IaAssistiva />,
      oportunidades: <Oportunidades />,
      casos: <Casos />,
      kanban: <Kanban />,
      consultor: <Consultor />,
      crm: <ConsultorFull />,
      pipeline: <ConsultorFull />,
      clientes: <ConsultorFull />,
      operacao: <ConsultorFull />,
      relatorios: <Dashboard profile={profile} onNavigate={setCurrent} />,
      contratos: <FornecedorFull />,
      financeiro: profile?.perfil_atual === 'consultor' ? <ConsultorFull /> : <FornecedorFull />,
      'fornecedor-full': <FornecedorFull />,
      'consultor-full': <ConsultorFull />,
      documental: <Documental360 />,
      concorrentes: <Concorrentes />,
      orgaos: <Orgaos />,
      alertas: <Alertas />,
      notificacoes: <Notificacoes />,
      observabilidade: <Observabilidade />,
      upload: <Upload />,
      pecas: <Pecas />,
      memorias: <Memorias />,
    }
    if (pages[current]) return pages[current]
    return <StructuralModule item={dynamicNavigation.find((item) => item.id === current)} profile={profile} />
  }, [current, dynamicNavigation, profile])

  if (sessionLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-950 text-slate-200">
        <Loader2 className="mr-3 animate-spin" /> Validando sessão da LICI...
      </div>
    )
  }

  if (!sessionUser) {
    return <LoginScreen onLogin={handleLogin} />
  }

  return (
    <>
      <ApiFeedbackToasts />
      <Shell
        current={current}
        onNavigate={setCurrent}
        navigation={dynamicNavigation}
        profile={profile}
        profileOptions={profileOptions}
        profileLoading={profileLoading}
        profileError={profileError}
        onSelectProfile={selectProfile}
        sessionUser={sessionUser}
        onLogout={logout}
      >
        {page}
      </Shell>
    </>
  )
}
