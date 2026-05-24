from __future__ import annotations

import json
from datetime import date, datetime, timedelta, timezone
from typing import Any
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from fastapi import HTTPException

from app.schemas.case import CaseCreate
from app.schemas.decision import DecisionCriteria, DecisionRequest, MemorySuggestion
from app.schemas.radar import (
    RadarCreateCaseRequest,
    RadarCreateCaseResponse,
    RadarOpportunity,
    RadarOpportunityListResponse,
    RadarSearchRequest,
    RadarSearchResponse,
)
from app.services.case_engine import LiciCaseEngine
from app.services.decision_engine import LiciDecisionEngine
from app.services.memory_core_client import MemoryCoreClient
from app.services.radar_store import HybridRadarStore


class PncpClient:
    def __init__(self, base_url: str = "https://pncp.gov.br/api/consulta/v1", timeout_seconds: float = 12.0):
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds

    def buscar_contratacoes(self, payload: RadarSearchRequest) -> tuple[list[dict[str, Any]], str]:
        hoje = date.today()
        data_inicial = payload.data_inicial or (hoje - timedelta(days=30))
        data_final = payload.data_final or hoje
        modalidades = (
            [payload.codigo_modalidade_contratacao]
            if payload.codigo_modalidade_contratacao is not None
            else [6, 8, 4, 5, 7, 1, 2, 3, 9, 10, 11, 12, 13, 14]
        )
        registros: list[dict[str, Any]] = []
        avisos: list[str] = []
        for modalidade in modalidades:
            params = {
                "dataInicial": data_inicial.strftime("%Y%m%d"),
                "dataFinal": data_final.strftime("%Y%m%d"),
                "codigoModalidadeContratacao": modalidade,
                "pagina": 1,
                "tamanhoPagina": min(max(payload.limite, 10), 50),
            }
            if payload.uf:
                params["uf"] = payload.uf.upper()
            url = f"{self.base_url}/contratacoes/publicacao?{urlencode(params)}"
            request = Request(url, headers={"Accept": "application/json", "User-Agent": "LICI-Radar-Engine/0.1"})
            try:
                with urlopen(request, timeout=self.timeout_seconds) as response:
                    body = response.read().decode("utf-8")
                    data = json.loads(body)
            except (URLError, TimeoutError, json.JSONDecodeError) as exc:
                avisos.append(f"modalidade {modalidade}: {exc}")
                continue

            if isinstance(data, dict):
                itens = data.get("data") or data.get("content") or data.get("items") or []
            elif isinstance(data, list):
                itens = data
            else:
                itens = []
            registros.extend([item for item in itens if isinstance(item, dict)])
            if len(registros) >= payload.limite:
                break
        aviso = "" if registros else ("PNCP sem resultados ou indisponível: " + "; ".join(avisos[:3]) if avisos else "")
        return registros, aviso


class LiciRadarEngine:
    def __init__(
        self,
        store: HybridRadarStore | None = None,
        pncp: PncpClient | None = None,
        memory: MemoryCoreClient | None = None,
        decision_engine: LiciDecisionEngine | None = None,
        case_engine: LiciCaseEngine | None = None,
    ):
        self.store = store or HybridRadarStore()
        self.pncp = pncp or PncpClient()
        self.memory = memory or MemoryCoreClient()
        self.decision_engine = decision_engine or LiciDecisionEngine()
        self.case_engine = case_engine or LiciCaseEngine()

    def buscar(self, payload: RadarSearchRequest) -> RadarSearchResponse:
        registros, aviso = self.pncp.buscar_contratacoes(payload)
        oportunidades = [self._normalizar(item) for item in registros]
        oportunidades = self._filtrar(oportunidades, payload)
        oportunidades = oportunidades[: payload.limite]
        oportunidades = [self._enriquecer_score_memoria(o, payload) for o in oportunidades]
        if payload.salvar:
            oportunidades = self.store.upsert_many(oportunidades)
        return RadarSearchResponse(total=len(oportunidades), oportunidades=oportunidades, filtros=payload, aviso=aviso)

    def listar_oportunidades(self) -> RadarOpportunityListResponse:
        oportunidades = self.store.list()
        return RadarOpportunityListResponse(total=len(oportunidades), oportunidades=oportunidades)

    def criar_caso(self, opportunity_id: str, payload: RadarCreateCaseRequest) -> RadarCreateCaseResponse:
        oportunidade = self.store.get(opportunity_id)
        if oportunidade is None:
            raise HTTPException(status_code=404, detail="oportunidade não encontrada")
        contexto = payload.contexto or (
            f"Oportunidade capturada pelo LICI Radar Engine no PNCP. Valor estimado: {oportunidade.valor_estimado}; "
            f"datas: publicação {oportunidade.data_publicacao}, abertura {oportunidade.data_abertura}, encerramento {oportunidade.data_encerramento}. "
            f"Score preliminar: {oportunidade.score_preliminar}/100. Link: {oportunidade.link}"
        )
        caso = self.case_engine.create_case(
            CaseCreate(
                cliente=payload.cliente,
                orgao=oportunidade.orgao or "Órgão não identificado",
                objeto=oportunidade.objeto or "Objeto não identificado",
                modalidade=oportunidade.modalidade,
                fase_atual="prospecção",
                score_estrategico=oportunidade.score_preliminar,
                riscos=oportunidade.riscos_aparentes,
                oportunidades=oportunidade.oportunidades_estrategicas,
                memorias_relacionadas=oportunidade.memorias_relacionadas,
                contexto=contexto,
            )
        )
        oportunidade.caso_id = caso.id
        oportunidade.atualizado_em = self._now()
        oportunidade.memoria_sugerida = oportunidade.memoria_sugerida or self._memoria_sugerida(oportunidade, "Oportunidade transformada em caso vivo.")
        self.store.update(oportunidade)
        return RadarCreateCaseResponse(oportunidade=oportunidade, caso=caso.model_dump(), memoria_sugerida=oportunidade.memoria_sugerida)

    def _normalizar(self, item: dict[str, Any]) -> RadarOpportunity:
        orgao = self._pick(item, "orgaoEntidade.razaoSocial", "orgaoEntidade.nome", "nomeOrgao", "orgao")
        unidade = self._pick(item, "unidadeOrgao.nomeUnidade", "unidadeOrgao.nome", "unidade")
        uf = self._pick(item, "unidadeOrgao.ufSigla", "uf", "siglaUf", "unidadeOrgao.ufNome")
        objeto = self._pick(item, "objetoCompra", "objeto", "descricaoObjeto", "informacaoComplementar")
        modalidade = self._pick(item, "modalidadeNome", "modalidade", "nomeModalidade")
        valor = self._to_float(self._pick(item, "valorTotalEstimado", "valorEstimado", "valorTotalHomologado"))
        pncp_id = self._pick(item, "numeroControlePNCP", "numeroControlePncp", "id")
        link = self._pick(item, "linkSistemaOrigem", "linkProcessoEletronico", "uri")
        if not link and pncp_id:
            link = f"https://pncp.gov.br/app/editais/{pncp_id}"
        return RadarOpportunity(
            pncp_id=str(pncp_id or ""),
            orgao=str(orgao or ""),
            unidade=str(unidade or ""),
            uf=str(uf or "").upper(),
            objeto=str(objeto or ""),
            modalidade=str(modalidade or ""),
            valor_estimado=valor,
            data_publicacao=str(self._pick(item, "dataPublicacaoPncp", "dataPublicacao", "dataInclusao") or ""),
            data_abertura=str(self._pick(item, "dataAberturaProposta", "dataInicioRecebimentoProposta", "dataAbertura") or ""),
            data_encerramento=str(self._pick(item, "dataEncerramentoProposta", "dataFimRecebimentoProposta", "dataEncerramento") or ""),
            link=str(link or ""),
            raw=item,
        )

    def _filtrar(self, oportunidades: list[RadarOpportunity], payload: RadarSearchRequest) -> list[RadarOpportunity]:
        termos = [t.casefold().strip() for t in payload.palavras_chave if t.strip()]
        if payload.segmento:
            termos.append(payload.segmento.casefold().strip())
        filtradas = []
        for o in oportunidades:
            if payload.uf and o.uf and o.uf != payload.uf.upper():
                continue
            texto = f"{o.orgao} {o.unidade} {o.objeto} {o.modalidade}".casefold()
            if termos and not any(t in texto for t in termos):
                continue
            filtradas.append(o)
        return filtradas

    def _enriquecer_score_memoria(self, oportunidade: RadarOpportunity, payload: RadarSearchRequest) -> RadarOpportunity:
        memorias = self._buscar_memorias(oportunidade)
        oportunidade.memorias_relacionadas = memorias
        segmento = payload.segmento or " ".join(payload.palavras_chave)
        aderencia = self._score_aderencia(oportunidade, payload)
        valor = self._score_valor(oportunidade.valor_estimado)
        prazo = self._score_prazo(oportunidade.data_encerramento)
        risco = self._score_risco(oportunidade)
        estrategica = self._score_oportunidade(oportunidade, segmento, memorias)
        historico = min(100, 45 + len(memorias) * 10)
        criterios = {
            "aderencia_segmento": aderencia,
            "valor_estimado": valor,
            "prazo_disponivel": prazo,
            "risco_aparente": risco,
            "oportunidade_estrategica": estrategica,
            "historico_memoria_orgao": historico,
        }
        score = round(
            aderencia * 0.24
            + valor * 0.16
            + prazo * 0.16
            + (100 - risco) * 0.14
            + estrategica * 0.20
            + historico * 0.10
        )
        oportunidade.criterios_score = criterios
        oportunidade.score_preliminar = max(0, min(100, score))
        oportunidade.riscos_aparentes = self._riscos(oportunidade, prazo, risco)
        oportunidade.oportunidades_estrategicas = self._oportunidades(oportunidade, aderencia, estrategica, memorias)

        decisao = self.decision_engine.decidir(
            DecisionRequest(
                pergunta=f"Radar PNCP: órgão {oportunidade.orgao}; objeto {oportunidade.objeto}; modalidade {oportunidade.modalidade}; valor {oportunidade.valor_estimado}; prazo {oportunidade.data_encerramento}",
                termo_memoria=f"{oportunidade.orgao} {oportunidade.objeto}",
                criterios=DecisionCriteria(
                    aderencia_tecnica=aderencia,
                    risco_habilitacao=45,
                    risco_juridico=risco,
                    oportunidade_competitiva=estrategica,
                    risco_execucao=risco,
                    historico_memoria_viva=historico,
                    necessidade_impugnacao=30,
                    chance_estrategica_vitoria=oportunidade.score_preliminar,
                ),
                consultar_rag=False,
            )
        )
        if decisao.memoria_sugerida or memorias:
            oportunidade.memoria_sugerida = self._memoria_sugerida(
                oportunidade,
                "Radar identificou padrão relevante por histórico/memória ou score estratégico preliminar.",
            )
        return oportunidade

    def _buscar_memorias(self, oportunidade: RadarOpportunity) -> list[dict[str, Any]]:
        resultados: list[dict[str, Any]] = []
        for termo in [oportunidade.orgao, oportunidade.objeto[:80]]:
            if not termo:
                continue
            memoria = self.memory.buscar(termo)
            resultados.extend(memoria.get("resultados", []))
        seen: set[str] = set()
        deduped: list[dict[str, Any]] = []
        for item in resultados:
            key = item.get("id") or repr(item)
            if key not in seen:
                seen.add(key)
                deduped.append(item)
        return deduped

    def _score_aderencia(self, oportunidade: RadarOpportunity, payload: RadarSearchRequest) -> int:
        termos = [t.casefold() for t in payload.palavras_chave if t.strip()]
        if payload.segmento:
            termos.append(payload.segmento.casefold())
        if not termos:
            return 55
        texto = f"{oportunidade.objeto} {oportunidade.modalidade}".casefold()
        hits = sum(1 for termo in termos if termo in texto)
        return min(100, 45 + hits * 25)

    def _score_valor(self, valor: float | None) -> int:
        if valor is None or valor <= 0:
            return 45
        if valor < 50_000:
            return 40
        if valor < 250_000:
            return 60
        if valor < 2_000_000:
            return 80
        return 90

    def _score_prazo(self, data_encerramento: str) -> int:
        dias = self._dias_ate(data_encerramento)
        if dias is None:
            return 45
        if dias < 2:
            return 15
        if dias <= 5:
            return 45
        if dias <= 15:
            return 75
        return 90

    def _score_risco(self, oportunidade: RadarOpportunity) -> int:
        texto = f"{oportunidade.objeto} {oportunidade.modalidade}".casefold()
        risco = 35
        if any(t in texto for t in ["técnica e preço", "tecnica e preco", "obra", "engenharia", "dedicação exclusiva"]):
            risco += 20
        if any(t in texto for t in ["emergencial", "prazo imediato", "24 horas", "exclusiva"]):
            risco += 15
        if self._dias_ate(oportunidade.data_encerramento) is not None and self._dias_ate(oportunidade.data_encerramento) < 5:
            risco += 20
        return max(0, min(100, risco))

    def _score_oportunidade(self, oportunidade: RadarOpportunity, segmento: str, memorias: list[dict[str, Any]]) -> int:
        score = 55
        if segmento and segmento.casefold() in oportunidade.objeto.casefold():
            score += 20
        if oportunidade.valor_estimado and oportunidade.valor_estimado >= 250_000:
            score += 10
        if memorias:
            score += 10
        return max(0, min(100, score))

    def _riscos(self, oportunidade: RadarOpportunity, prazo: int, risco: int) -> list[str]:
        riscos: list[str] = []
        if prazo < 50:
            riscos.append("Prazo disponível curto para análise, habilitação e proposta.")
        if risco >= 60:
            riscos.append("Risco aparente elevado no objeto/modalidade; verificar edital, qualificação técnica e execução.")
        if oportunidade.valor_estimado is None:
            riscos.append("Valor estimado não identificado no PNCP; confirmar viabilidade econômica no edital/anexos.")
        return riscos or ["Risco preliminar moderado; confirmar exigências no edital antes de alocar esforço comercial."]

    def _oportunidades(self, oportunidade: RadarOpportunity, aderencia: int, estrategica: int, memorias: list[dict[str, Any]]) -> list[str]:
        out = []
        if aderencia >= 70:
            out.append("Boa aderência preliminar ao segmento/palavras-chave informadas.")
        if estrategica >= 70:
            out.append("Oportunidade estratégica acima da média; priorizar leitura do edital e checklist de habilitação.")
        if memorias:
            out.append("Há memória relacionada ao órgão/objeto; usar histórico para calibrar decisão e abordagem.")
        return out or ["Oportunidade capturada para triagem; validar aderência técnica e margem antes de criar caso." ]

    def _memoria_sugerida(self, oportunidade: RadarOpportunity, aprendizado: str) -> MemorySuggestion:
        return MemorySuggestion(
            tipo="padrao",
            titulo=f"Radar PNCP: {oportunidade.orgao or 'órgão não identificado'}",
            descricao=f"Oportunidade PNCP identificada: {oportunidade.objeto[:180]}",
            estrategia="Usar Radar para transformar oportunidades relevantes em casos vivos e priorizar por score preliminar.",
            aprendizado=aprendizado,
            uso_futuro="Comparar novas oportunidades do mesmo órgão/objeto com score, risco, valor, prazo e histórico.",
            tags=["radar-engine", "pncp", oportunidade.uf, oportunidade.orgao],
        )

    def _pick(self, item: dict[str, Any], *paths: str) -> Any:
        for path in paths:
            cur: Any = item
            for part in path.split("."):
                if not isinstance(cur, dict) or part not in cur:
                    cur = None
                    break
                cur = cur[part]
            if cur not in (None, ""):
                return cur
        return None

    def _to_float(self, value: Any) -> float | None:
        if value in (None, ""):
            return None
        try:
            return float(str(value).replace(".", "").replace(",", ".")) if isinstance(value, str) else float(value)
        except (TypeError, ValueError):
            return None

    def _dias_ate(self, value: str) -> int | None:
        if not value:
            return None
        text = value.strip()
        try:
            return (datetime.fromisoformat(text.replace("Z", "+00:00")).date() - date.today()).days
        except ValueError:
            pass
        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%Y%m%d"):
            try:
                dt = datetime.strptime(text[:10], fmt)
                return (dt.date() - date.today()).days
            except ValueError:
                continue
        return None

    def _now(self) -> str:
        return datetime.now(timezone.utc).isoformat()
