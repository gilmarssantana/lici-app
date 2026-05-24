from __future__ import annotations

import json
from pathlib import Path
from tempfile import NamedTemporaryFile

from app.schemas.profile import CurrentProfileState, OperationalProfileConfig

PROFILE_ROOT = Path("/root/lici-app/perfis")
CURRENT_PROFILE_FILE = PROFILE_ROOT / "perfil_atual.json"
CONFIGURATIONS_FILE = PROFILE_ROOT / "configuracoes.json"


class JsonOperationalProfileStore:
    def __init__(self, root: Path | str = PROFILE_ROOT):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.current_path = self.root / "perfil_atual.json"
        self.config_path = self.root / "configuracoes.json"
        if not self.config_path.exists():
            self._write_json(self.config_path, _default_configurations())
        if not self.current_path.exists():
            self._write_json(self.current_path, CurrentProfileState().model_dump())

    def current(self) -> CurrentProfileState:
        return CurrentProfileState(**json.loads(self.current_path.read_text(encoding="utf-8")))

    def set_current(self, state: CurrentProfileState) -> CurrentProfileState:
        self._write_json(self.current_path, state.model_dump())
        return state

    def configurations(self) -> list[OperationalProfileConfig]:
        raw = json.loads(self.config_path.read_text(encoding="utf-8"))
        return [OperationalProfileConfig(**item) for item in raw]

    def get_config(self, profile_id: str) -> OperationalProfileConfig | None:
        for config in self.configurations():
            if config.id == profile_id:
                return config
        return None

    def _write_json(self, path: Path, data: dict | list[dict]) -> None:
        with NamedTemporaryFile("w", encoding="utf-8", dir=self.root, delete=False) as tmp:
            json.dump(data, tmp, ensure_ascii=False, indent=2)
            tmp.write("\n")
            tmp_path = Path(tmp.name)
        tmp_path.replace(path)


def _menu(id: str, label: str, icon: str = "", enabled: bool = True, status: str = "ativo") -> dict:
    return {"id": id, "label": label, "icon": icon, "enabled": enabled, "status": status}


def _default_configurations() -> list[dict]:
    fornecedor_menus = [
        _menu("dashboard", "Dashboard", "LayoutDashboard"),
        _menu("oportunidades", "Oportunidades", "Target"),
        _menu("casos", "Casos", "BriefcaseBusiness"),
        _menu("documental", "Documental", "FileText"),
        _menu("contratos", "Contratos", "BriefcaseBusiness"),
        _menu("financeiro", "Financeiro", "Database"),
        _menu("concorrentes", "Concorrentes", "UserCircle"),
        _menu("orgaos", "Órgãos", "Database"),
        _menu("ia-assistiva", "IA Assistiva", "MessageCircle"),
    ]
    consultor_menus = [
        _menu("dashboard", "Dashboard", "LayoutDashboard"),
        _menu("crm", "CRM", "UserCircle"),
        _menu("pipeline", "Pipeline", "BarChart3"),
        _menu("clientes", "Clientes", "BriefcaseBusiness"),
        _menu("operacao", "Operação", "CheckCircle2"),
        _menu("documental", "Documental", "FileText"),
        _menu("casos", "Casos", "BriefcaseBusiness"),
        _menu("financeiro", "Financeiro", "Database"),
        _menu("relatorios", "Relatórios", "BarChart3"),
        _menu("ia-assistiva", "IA Assistiva", "MessageCircle"),
    ]
    comprador_menus = [
        _menu("dashboard", "Dashboard", "LayoutDashboard"),
        _menu("planejamento", "Planejamento", "ClipboardList", False, "estrutural"),
        _menu("dfd", "DFD", "FileText", False, "estrutural"),
        _menu("etp", "ETP", "FileText", False, "estrutural"),
        _menu("tr", "TR / Projeto Básico", "FileText", False, "estrutural"),
        _menu("precos", "Pesquisa de Preços", "Search", False, "estrutural"),
        _menu("matriz-risco", "Matriz de Risco", "AlertTriangle", False, "estrutural"),
        _menu("editais", "Editais", "FileText", False, "estrutural"),
        _menu("impugnacoes", "Impugnações", "Scale", False, "estrutural"),
        _menu("julgamento", "Julgamento", "CheckCircle2", False, "estrutural"),
        _menu("habilitacao", "Habilitação", "ShieldCheck", False, "estrutural"),
        _menu("contratos", "Contratos", "FileCheck", False, "estrutural"),
        _menu("memorias", "Memórias", "BookOpen"),
    ]
    return [
        {
            "id": "fornecedor",
            "nome": "Fornecedor / Empresário",
            "descricao": "Empresas que vendem ou querem vender para o governo.",
            "linguagem_recomendada": "Competitiva, direta, estratégica e orientada a decisão: participar, impugnar, recorrer, proteger habilitação, vencer, executar e receber.",
            "prioridades": ["oportunidades", "habilitação", "proposta", "impugnação", "recurso", "concorrentes", "contratos", "pagamento", "vitória"],
            "menus": fornecedor_menus,
            "modulos_habilitados": ["dashboard", "radar_engine", "triage_engine", "upload_engine", "edital_analyzer", "decision_engine", "case_engine", "kanban", "document_generator", "export_engine", "alert_engine", "memory_core", "orgaos_engine", "audit_log"],
            "fluxos": ["radar", "triagem", "análise de edital", "go/no-go", "habilitação", "peças", "disputa", "recurso", "contrato", "pagamento"],
            "tipos_caso": ["oportunidade", "edital", "impugnação", "habilitação", "disputa", "recurso", "contrato", "pagamento", "reequilíbrio", "vitória", "perda"],
            "tipos_alerta": ["prazo de proposta", "habilitação incompleta", "impugnação vencendo", "recurso pendente", "contrato com risco", "pagamento atrasado"],
            "tipos_memoria": ["orgao", "concorrente", "tese", "vitoria", "perda", "risco", "padrao", "contrato"],
            "documentos_gerados": ["pedido de esclarecimento", "impugnação", "recurso", "contrarrazões", "checklist de habilitação", "pedido de reequilíbrio", "cobrança administrativa"],
            "dashboard": {"foco": "operação, prioridade e ação imediata", "cards": ["oportunidades prioritárias", "casos com ação", "alertas críticos", "risco concorrencial"]},
        },
        {
            "id": "consultor",
            "nome": "Consultor",
            "descricao": "Analistas e consultorias que atendem múltiplos clientes e CNPJs.",
            "linguagem_recomendada": "Gerencial, consultiva, produtiva e orientada a carteira, SLA, cliente, prazo, entrega, relatório e cobrança.",
            "prioridades": ["clientes", "carteira", "prospecção de clientes", "demandas", "múltiplos CNPJs", "prazos", "produtividade", "peças por cliente", "cobrança", "relatórios", "recorrência"],
            "menus": consultor_menus,
            "modulos_habilitados": ["dashboard", "case_engine", "kanban", "document_generator", "export_engine", "alert_engine", "memory_core", "audit_log", "client_portfolio_engine:planejado", "demand_management_engine:planejado", "billing_engine:planejado"],
            "fluxos": ["prospecção de cliente", "diagnóstico", "demanda", "produção de peça", "entrega", "relatório", "cobrança", "recorrência"],
            "tipos_caso": ["prospecção de cliente", "diagnóstico", "radar por cliente", "edital em análise", "peça em produção", "acompanhamento", "relatório mensal", "cobrança"],
            "tipos_alerta": ["demanda atrasada", "cliente sem atualização", "relatório pendente", "cobrança vencida", "prazo crítico de cliente"],
            "tipos_memoria": ["cliente", "orgao", "tese", "padrao", "produtividade", "cobranca"],
            "documentos_gerados": ["proposta comercial", "diagnóstico de cliente", "plano de ação", "relatório mensal", "relatório de oportunidades", "ata de reunião", "cobrança"],
            "dashboard": {"foco": "carteira, pipeline e ação imediata", "cards": ["leads ativos", "conversão", "carteira", "tarefas pendentes"]},
        },
        {
            "id": "comprador",
            "nome": "Comprador Público",
            "descricao": "Órgãos, agentes de contratação, pregoeiros e equipes públicas.",
            "linguagem_recomendada": "Institucional, técnica, preventiva e orientada a planejamento, conformidade, transparência, motivação e redução de nulidades.",
            "prioridades": ["planejamento da contratação", "DFD", "ETP", "TR", "pesquisa de preços", "matriz de risco", "edital", "resposta a impugnações", "julgamento", "habilitação", "gestão contratual", "transparência", "conformidade"],
            "menus": comprador_menus,
            "modulos_habilitados": ["dashboard", "upload_engine", "edital_analyzer", "case_engine", "document_generator", "export_engine", "alert_engine", "memory_core", "audit_log", "public_planning_engine:planejado", "price_research_engine:planejado", "public_notice_compliance_engine:planejado"],
            "fluxos": ["planejamento", "DFD", "ETP", "TR", "pesquisa de preços", "edital", "impugnação", "julgamento", "habilitação", "contrato", "fiscalização"],
            "tipos_caso": ["planejamento", "DFD", "ETP", "TR", "pesquisa de preços", "edital", "impugnação", "julgamento", "habilitação", "contrato", "fiscalização", "sanção"],
            "tipos_alerta": ["DFD pendente", "ETP pendente", "pesquisa incompleta", "impugnação sem resposta", "sessão próxima", "contrato sem fiscalização", "risco de conformidade"],
            "tipos_memoria": ["orgao", "padrao", "risco", "contrato", "conformidade", "precedente"],
            "documentos_gerados": ["DFD", "ETP", "TR", "matriz de risco", "relatório de pesquisa de preços", "resposta a impugnação", "decisão de julgamento", "despacho de diligência", "relatório de fiscalização"],
            "dashboard": {"foco": "central de conformidade e processo público", "cards": ["planejamentos", "DFDs", "ETPs", "TRs", "impugnações", "contratos", "conformidade"]},
        },
    ]
