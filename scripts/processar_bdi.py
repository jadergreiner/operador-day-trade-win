#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PROCESSADOR DE BOLETIM DIÁRIO DA B3
===================================
Analista de Dados Expert em Dados da B3
Especialista em Mercado Brasileiro

Funcionalidades:
- Extração de dados do BDI
- Análise comparativa de períodos
- Identificação de tendências e gaps
- Relatório executivo em HTML
- Backlog de oportunidades

Data: Fevereiro 2026
"""

import os
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Optional

class AnalistaBDI:
    """
    Analista especializado em Boletins Diários de Informações da B3.
    Responsável por extrair, análisar e sintetizar dados para operadores.
    """

    def __init__(self, workspace_path: str = None):
        if workspace_path is None:
            workspace_path = r"c:\repo\operador-day-trade-win"

        self.workspace = Path(workspace_path)
        self.bdi_path = self.workspace / "data" / "BDI"
        self.output_path = self.workspace / "data" / "BDI" / "reports"
        self.output_path.mkdir(parents=True, exist_ok=True)

        self.dados_bdi = {}
        self.insights = []
        self.oportunidades = []
        self.gaps = []

    def listar_arquivos_bdi(self) -> List[Tuple[Path, str]]:
        """Lista todos os arquivos BDI disponíveis e os ordena por data."""
        arquivos = []

        # Procura por arquivos de key data
        for arquivo in sorted(self.bdi_path.glob("bdi_*_key_data.txt"), reverse=True):
            try:
                # Extrai data do nome do arquivo (bdi_YYYYMMDD_key_data.txt)
                partes = arquivo.stem.split('_')
                data_str = partes[1]
                arquivos.append((arquivo, data_str))
            except:
                continue

        return arquivos

    def extrair_dados_bdi(self, arquivo: Path, data: str) -> Dict:
        """Extrai dados-chave do arquivo BDI."""
        dados = {
            'arquivo': str(arquivo),
            'data': data,
            'data_formatada': self._formatar_data(data),
            'metrics': {},
            'raw_content': self._ler_arquivo(arquivo)
        }

        # Extrai métricas principais
        conteudo = dados['raw_content']

        # IBOVESPA
        if 'IBOVESPA' in conteudo or 'Fechamento do IBOVESPA' in conteudo:
            ibov_info = self._extrair_ibovespa(conteudo)
            dados['metrics'].update(ibov_info)

        # Derivativos
        if 'Derivativos' in conteudo:
            deriv_info = self._extrair_derivativos(conteudo)
            dados['metrics'].update(deriv_info)

        # Renda Variável
        if 'Renda variável' in conteudo:
            rv_info = self._extrair_renda_variavel(conteudo)
            dados['metrics'].update(rv_info)

        return dados

    def _ler_arquivo(self, arquivo: Path) -> str:
        """Lê o conteúdo do arquivo."""
        try:
            with open(arquivo, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            print(f"Erro ao ler {arquivo}: {e}")
            return ""

    def _formatar_data(self, data_str: str) -> str:
        """Formata data de YYYYMMDD para formato legível."""
        try:
            ano = data_str[:4]
            mes = data_str[4:6]
            dia = data_str[6:8]
            return f"{dia}/{mes}/{ano}"
        except:
            return data_str

    def _extrair_ibovespa(self, conteudo: str) -> Dict:
        """Extrai informações do IBOVESPA."""
        info = {}
        linhas = conteudo.split('\n')

        for i, linha in enumerate(linhas):
            if 'Fechamento do IBOVESPA' in linha:
                try:
                    # Tenta extrair valor e variação
                    partes = linha.split(':')
                    if len(partes) > 1:
                        valor_var = partes[1].strip().split()
                        if len(valor_var) >= 2:
                            info['ibovespa_valor'] = valor_var[0].replace('.', '').replace(',', '.')
                            info['ibovespa_variacao'] = valor_var[1] if len(valor_var) > 1 else "0"
                except:
                    pass

            # Volume negociado
            if 'Volume negociado' in linha and 'milhões' not in linha:
                try:
                    valor = linha.split()[-1]
                    info['volume_negociado'] = valor
                except:
                    pass

            # Quantidade de negócios
            if 'Quantidade de negócios' in linha and ':' not in linha:
                try:
                    valor = linha.split()[-1]
                    info['qtd_negocios'] = valor
                except:
                    pass

        return info

    def _extrair_derivativos(self, conteudo: str) -> Dict:
        """Extrai informações de derivativos."""
        info = {}
        linhas = conteudo.split('\n')

        for linha in linhas:
            # Contratos com minis
            if 'Total com minis' in linha and 'Dia' not in linha:
                try:
                    valor = linha.split()[-1]
                    info['derivativos_com_minis'] = valor
                except:
                    pass

            # Contratos sem minis
            if 'Total sem minis' in linha and 'Dia' not in linha:
                try:
                    valor = linha.split()[-1]
                    info['derivativos_sem_minis'] = valor
                except:
                    pass

        return info

    def _extrair_renda_variavel(self, conteudo: str) -> Dict:
        """Extrai informações de renda variável."""
        info = {}
        linhas = conteudo.split('\n')

        in_acoes_section = False
        for linha in linhas:
            if 'Ações - resumo das operações' in linha:
                in_acoes_section = True

            if in_acoes_section and 'TOTAL GERAL' in linha:
                try:
                    partes = linha.split()
                    if len(partes) >= 3:
                        info['total_valor_negociado'] = partes[-2]
                except:
                    pass

        return info

    def processar_multiplos_bdi(self, quantidade: int = 5) -> List[Dict]:
        """Processa múltiplos boletins para análise comparativa."""
        arquivos = self.listar_arquivos_bdi()[:quantidade]

        print(f"\n🔍 PROCESSANDO {len(arquivos)} BOLETINS DIÁRIOS")
        print("=" * 80)

        for arquivo, data in arquivos:
            print(f"  → {data}: ", end="", flush=True)
            try:
                dados = self.extrair_dados_bdi(arquivo, data)
                self.dados_bdi[data] = dados
                print(f"✓ ({len(dados['metrics'])} métricas)")
            except Exception as e:
                print(f"✗ Erro: {e}")

        return list(self.dados_bdi.values())

    def analisar_tendencias(self):
        """Analisa tendências nos dados extraídos."""
        if not self.dados_bdi:
            print("Nenhum dado disponível para análise de tendências.")
            return

        print("\n📊 ANÁLISE DE TENDÊNCIAS")
        print("=" * 80)

        datas = sorted(self.dados_bdi.keys(), reverse=True)

        # Análise de volatilidade do IBOVESPA
        print("\n1️⃣  VOLATILIDADE E MOVIMENTO DO IBOVESPA")
        variações = []
        for data in datas:
            try:
                var = self.dados_bdi[data]['metrics'].get('ibovespa_variacao', '0')
                var_float = float(var.replace('%', '').strip())
                variações.append((data, var_float))
                print(f"   {data}: {var:>8}")

                if var_float > 0.5:
                    self.insights.append(f"Alta volatilidade positiva em {data}: {var}")
                elif var_float < -0.5:
                    self.insights.append(f"Alta volatilidade negativa em {data}: {var}")
            except:
                pass

        # Análise de volume
        print("\n2️⃣  ANÁLISE DE VOLUME")
        volumes = []
        for data in datas:
            try:
                vol = self.dados_bdi[data]['metrics'].get('volume_negociado', '0')
                if vol and vol != '0':
                    print(f"   {data}: {vol}")
                    volumes.append((data, int(vol.replace('.', ''))))
            except:
                pass

        if len(volumes) > 1:
            vol_medio = sum([v[1] for v in volumes]) / len(volumes)
            print(f"   Volume Médio: {vol_medio:,.0f}")

            for data, vol in volumes[:2]:
                desvio = ((vol - vol_medio) / vol_medio) * 100
                if desvio < -20:
                    self.insights.append(f"Volume abaixo do normal em {data} ({desvio:.1f}%)")
                elif desvio > 20:
                    self.insights.append(f"Volume acima do normal em {data} ({desvio:.1f}%)")

        # Análise de derivativos
        print("\n3️⃣  ATIVIDADE EM DERIVATIVOS")
        for data in datas[:3]:
            try:
                com_minis = int(self.dados_bdi[data]['metrics'].get('derivativos_com_minis', '0'))
                sem_minis = int(self.dados_bdi[data]['metrics'].get('derivativos_sem_minis', '0'))

                if com_minis > 0 or sem_minis > 0:
                    print(f"   {data}: Com minis: {com_minis:>12,} | Sem minis: {sem_minis:>12,}")

                    if com_minis > 70000000:
                        self.insights.append(f"Altíssima atividade em minis em {data}: {com_minis:,} contratos")
                    elif com_minis < 50000000:
                        self.insights.append(f"Baixa atividade em minis em {data}: {com_minis:,} contratos")
            except:
                pass

    def identificar_oportunidades(self):
        """Identifica oportunidades para o operador."""
        print("\n🎯 IDENTIFICAÇÃO DE OPORTUNIDADES")
        print("=" * 80)

        if not self.dados_bdi:
            return

        # Oportunidade 1: Volatilidade para Swing Trade
        print("\n1️⃣  VOLATILIDADE PARA SWING TRADE")
        for data in sorted(self.dados_bdi.keys(), reverse=True)[:2]:
            try:
                var = float(self.dados_bdi[data]['metrics'].get('ibovespa_variacao', '0').replace('%', '').strip())
                if abs(var) > 0.5:
                    op = {
                        'tipo': 'Swing Trade - Volatilidade',
                        'data': data,
                        'metrica': f'Variação IBOV: {var:.2f}%',
                        'acao': 'Investigar padrões de breakout e suporte/resistência',
                        'prioridade': 'ALTA' if abs(var) > 1.0 else 'MÉDIA'
                    }
                    self.oportunidades.append(op)
                    print(f"   ✓ {op['metrica']} → {op['acao']}")
            except:
                pass

        # Oportunidade 2: Volume Anômalo
        print("\n2️⃣  ANOMALIAS DE VOLUME")
        volumes = []
        for data in sorted(self.dados_bdi.keys(), reverse=True)[:5]:
            try:
                vol = int(self.dados_bdi[data]['metrics'].get('volume_negociado', '0').replace('.', ''))
                if vol > 0:
                    volumes.append((data, vol))
            except:
                pass

        if len(volumes) > 3:
            vol_medio = sum([v[1] for v in volumes]) / len(volumes)
            for data, vol in volumes[:2]:
                desvio = ((vol - vol_medio) / vol_medio) * 100
                if desvio > 30 or desvio < -30:
                    op = {
                        'tipo': 'Análise de Volume',
                        'data': data,
                        'metrica': f'Desvio: {desvio:+.1f}%',
                        'acao': 'Verificar causas do volume anômalo (notícias, eventos corporativos)',
                        'prioridade': 'MÉDIA'
                    }
                    self.oportunidades.append(op)
                    print(f"   ✓ {op['metrica']} → {op['acao']}")

        # Oportunidade 3: Derivativos com movimento importante
        print("\n3️⃣  ATIVIDADE ELEVADA EM DERIVATIVOS")
        for data in sorted(self.dados_bdi.keys(), reverse=True)[:2]:
            try:
                minis = int(self.dados_bdi[data]['metrics'].get('derivativos_com_minis', '0'))
                if minis > 70000000:
                    opp_ratio = "Muito alta" if minis > 80000000 else "Alta"
                    opp = {
                        'tipo': 'Mini Índice - Day Trade',
                        'data': data,
                        'metrica': f'Contratos: {minis:,}',
                        'acao': 'Oportunidade para scalping em mini índice com alta liquidez',
                        'prioridade': 'ALTA'
                    }
                    self.oportunidades.append(opp)
                    print(f"   ✓ {opp_ratio} atividade em {data}")
            except:
                pass

        # Oportunidade 4: Mercado a Termo
        print("\n4️⃣  MERCADO A TERMO")
        for data in sorted(self.dados_bdi.keys(), reverse=True)[:2]:
            opp = {
                'tipo': 'Operações a Termo',
                'data': data,
                'metrica': 'Posições em aberto',
                'acao': 'Analisar maiores posições abertas para identificar tendências institucionais',
                'prioridade': 'MÉDIA'
            }
            self.oportunidades.append(opp)

        # Oportunidade 5: Ações mais negociadas
        print("\n5️⃣  AÇÕES MAIS NEGOCIADAS")
        opp = {
            'tipo': 'Maior liquidez em ações',
            'data': sorted(self.dados_bdi.keys(), reverse=True)[0],
            'metrica': 'Top ações por volume',
            'acao': 'Focar em ações com maior volume e spreads menores para entrada/saída',
            'prioridade': 'MÉDIA'
        }
        self.oportunidades.append(opp)
        print(f"   ✓ Oportunidade de focus em ativos de maior liquidez")

    def identificar_gaps(self):
        """Identifica gaps (lacunas) na análise."""
        print("\n⚠️  GAPS IDENTIFICADOS")
        print("=" * 80)

        gaps = [
            {
                'area': 'Dados de Opções',
                'descricao': 'Arquivo BDI não contém detalhe individual de cada opção negociada',
                'recomendacao': 'Buscar relatórios específicos de opções da B3 para análise de IV e open interest'
            },
            {
                'area': 'Dados Intradiários',
                'descricao': 'BDI apresenta apenas dados diários consolidados',
                'recomendacao': 'Integrar dados de pregão em tempo real ou históricos de 1min/5min para scalping'
            },
            {
                'area': 'Análise de Investidores',
                'descricao': 'Faltam detalhes de participação por tipo de investidor',
                'recomendacao': 'Consultar relatórios específicos de fluxo de capitais e participação institucional'
            },
            {
                'area': 'Correlações de Pares',
                'descricao': 'Sem dados diretos de correlação entre pares relacionados',
                'recomendacao': 'Calcular correlações entre ações do mesmo setor e índices'
            }
        ]

        for gap in gaps:
            self.gaps.append(gap)
            print(f"\n❌ {gap['area']}")
            print(f"   Descrição: {gap['descricao']}")
            print(f"   Recomendação: {gap['recomendacao']}")

    def gerar_relatorio_html(self) -> str:
        """Gera relatório executivo em formato HTML."""
        data_relatorio = datetime.now().strftime("%d/%m/%Y %H:%M")

        html = f"""
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Relatório Executivo BDI - {data_relatorio}</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: #333;
            line-height: 1.6;
            padding: 20px;
        }}

        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 10px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.3);
            overflow: hidden;
        }}

        header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 40px 30px;
            text-align: center;
        }}

        header h1 {{
            font-size: 2.5em;
            margin-bottom: 10px;
        }}

        header p {{
            font-size: 1.1em;
            opacity: 0.95;
        }}

        .content {{
            padding: 30px;
        }}

        .section {{
            margin-bottom: 40px;
            padding: 25px;
            background: #f8f9fa;
            border-left: 5px solid #667eea;
            border-radius: 5px;
        }}

        .section h2 {{
            color: #667eea;
            font-size: 1.8em;
            margin-bottom: 20px;
            display: flex;
            align-items: center;
            gap: 10px;
        }}

        .icon {{
            font-size: 1.5em;
        }}

        .metric-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin: 20px 0;
        }}

        .metric {{
            background: white;
            padding: 20px;
            border-radius: 8px;
            border: 2px solid #e9ecef;
            box-shadow: 0 2px 5px rgba(0,0,0,0.05);
        }}

        .metric-value {{
            font-size: 1.8em;
            font-weight: bold;
            color: #667eea;
            margin: 10px 0;
        }}

        .metric-label {{
            color: #666;
            font-size: 0.9em;
            text-transform: uppercase;
            letter-spacing: 1px;
        }}

        .metric.positive .metric-value {{
            color: #28a745;
        }}

        .metric.negative .metric-value {{
            color: #dc3545;
        }}

        .insight-item {{
            background: white;
            padding: 15px;
            margin: 10px 0;
            border-left: 4px solid #ffc107;
            border-radius: 4px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        }}

        .opportunity-item {{
            background: white;
            padding: 15px;
            margin: 10px 0;
            border-left: 4px solid #28a745;
            border-radius: 4px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        }}

        .opportunity-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 10px;
        }}

        .opp-type {{
            font-weight: bold;
            color: #667eea;
        }}

        .priority {{
            padding: 5px 10px;
            border-radius: 3px;
            font-size: 0.8em;
            font-weight: bold;
        }}

        .priority.high {{
            background: #dc3545;
            color: white;
        }}

        .priority.medium {{
            background: #ffc107;
            color: black;
        }}

        .priority.low {{
            background: #17a2b8;
            color: white;
        }}

        .gap-item {{
            background: white;
            padding: 15px;
            margin: 10px 0;
            border-left: 4px solid #dc3545;
            border-radius: 4px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        }}

        .gap-area {{
            font-weight: bold;
            color: #dc3545;
            margin-bottom: 8px;
        }}

        .table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
            background: white;
            border-radius: 5px;
            overflow: hidden;
        }}

        .table th {{
            background: #667eea;
            color: white;
            padding: 15px;
            text-align: left;
            font-weight: bold;
        }}

        .table td {{
            padding: 12px 15px;
            border-bottom: 1px solid #e9ecef;
        }}

        .table tr:last-child td {{
            border-bottom: none;
        }}

        .table tr:hover {{
            background: #f8f9fa;
        }}

        footer {{
            background: #f8f9fa;
            padding: 20px 30px;
            text-align: center;
            color: #666;
            border-top: 1px solid #e9ecef;
        }}

        .highlight {{
            background: #fffacd;
            padding: 15px;
            border-radius: 5px;
            margin: 15px 0;
            border-left: 4px solid #ffc107;
        }}

        .metadata {{
            color: #999;
            font-size: 0.9em;
            margin-top: 15px;
        }}

        .backlog-section {{
            background: #fff3cd;
            padding: 20px;
            border-left: 5px solid #ffc107;
            border-radius: 5px;
            margin-top: 20px;
        }}

        .action-item {{
            background: white;
            padding: 15px;
            margin: 10px 0;
            border-left: 4px solid #007bff;
            border-radius: 4px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}

        .checkbox {{
            width: 20px;
            height: 20px;
            cursor: pointer;
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>📊 RELATÓRIO EXECUTIVO - BDI B3</h1>
            <p>Análise de Dados do Mercado Brasileiro</p>
            <p style="margin-top: 10px; font-size: 0.95em;">Gerado em: {data_relatorio}</p>
        </header>

        <div class="content">

            <!-- RESUMO EXECUTIVO -->
            <section class="section">
                <h2><span class="icon">📈</span>RESUMO EXECUTIVO</h2>
                <p>Análise consolidada dos últimos boletins diários da B3 com foco em identificação de oportunidades operacionais e gaps de dados para operadores de day trading e swing trading.</p>

                <h3 style="margin-top: 20px; color: #667eea;">Principais Métricas</h3>
                <div class="metric-grid">
"""

        # Adiciona métricas principais
        if self.dados_bdi:
            latest_data = list(self.dados_bdi.values())[0]
            metrics = latest_data['metrics']

            if 'ibovespa_valor' in metrics:
                html += f"""
                    <div class="metric">
                        <div class="metric-label">IBOVESPA (Fechamento)</div>
                        <div class="metric-value">{metrics.get('ibovespa_valor', 'N/A')}</div>
                        <div style="color: {'#28a745' if float(metrics.get('ibovespa_variacao', '0').replace('%', '')) > 0 else '#dc3545'}; font-weight: bold;">
                            {metrics.get('ibovespa_variacao', 'N/A')}
                        </div>
                    </div>
"""

            if 'volume_negociado' in metrics:
                html += f"""
                    <div class="metric">
                        <div class="metric-label">Volume Negociado</div>
                        <div class="metric-value">{metrics.get('volume_negociado', 'N/A')}</div>
                        <div style="color: #666;">em R$ (últimas sessões)</div>
                    </div>
"""

            if 'qtd_negocios' in metrics:
                html += f"""
                    <div class="metric">
                        <div class="metric-label">Quantidade de Negócios</div>
                        <div class="metric-value">{metrics.get('qtd_negocios', 'N/A')}</div>
                        <div style="color: #666;">contratos</div>
                    </div>
"""

            if 'derivativos_com_minis' in metrics:
                html += f"""
                    <div class="metric">
                        <div class="metric-label">Derivativos (com minis)</div>
                        <div class="metric-value">{metrics.get('derivativos_com_minis', 'N/A')}</div>
                        <div style="color: #667eea; font-weight: bold;">Muito Líquido</div>
                    </div>
"""

        html += """
                </div>
            </section>

            <!-- INSIGHTS E ANÁLISES -->
            <section class="section">
                <h2><span class="icon">💡</span>INSIGHTS E PONTOS DE ATENÇÃO</h2>
"""

        if self.insights:
            for insight in self.insights:
                html += f'<div class="insight-item">{insight}</div>\n'
        else:
            html += '<div class="insight-item">● Volatilidade moderada observada no período analisado</div>'

        html += """
            </section>

            <!-- OPORTUNIDADES IDENTIFICADAS -->
            <section class="section">
                <h2><span class="icon">🎯</span>OPORTUNIDADES IDENTIFICADAS</h2>
                <div class="highlight">
                    <strong>Total:</strong> {total_opp} oportunidades mapeadas para execução
                </div>
""".format(total_opp=len(self.oportunidades))

        # Agrupa por prioridade
        opp_altas = [o for o in self.oportunidades if o.get('prioridade') == 'ALTA']
        opp_medias = [o for o in self.oportunidades if o.get('prioridade') == 'MÉDIA']

        if opp_altas:
            html += '<h3 style="color: #dc3545; margin-top: 20px;">🔴 Prioridade ALTA</h3>'
            for opp in opp_altas:
                html += f"""
                <div class="opportunity-item">
                    <div class="opportunity-header">
                        <div class="opp-type">{opp['tipo']}</div>
                        <span class="priority high">{opp['prioridade']}</span>
                    </div>
                    <div><strong>Data:</strong> {opp['data']}</div>
                    <div><strong>Métrica:</strong> {opp['metrica']}</div>
                    <div><strong>Ação Recomendada:</strong> {opp['acao']}</div>
                </div>
"""

        if opp_medias:
            html += '<h3 style="color: #ffc107; margin-top: 20px;">🟡 Prioridade MÉDIA</h3>'
            for opp in opp_medias:
                html += f"""
                <div class="opportunity-item">
                    <div class="opportunity-header">
                        <div class="opp-type">{opp['tipo']}</div>
                        <span class="priority medium">{opp['prioridade']}</span>
                    </div>
                    <div><strong>Data:</strong> {opp['data']}</div>
                    <div><strong>Métrica:</strong> {opp['metrica']}</div>
                    <div><strong>Ação Recomendada:</strong> {opp['acao']}</div>
                </div>
"""

        html += """
            </section>

            <!-- GAPS IDENTIFICADOS -->
            <section class="section">
                <h2><span class="icon">⚠️</span>GAPS E RECOMENDAÇÕES</h2>
"""

        for gap in self.gaps:
            html += f"""
            <div class="gap-item">
                <div class="gap-area">❌ {gap['area']}</div>
                <div><strong>Descrição:</strong> {gap['descricao']}</div>
                <div style="margin-top: 10px; color: #28a745;"><strong>✓ Recomendação:</strong> {gap['recomendacao']}</div>
            </div>
"""

        html += """
            </section>

            <!-- BACKLOG DE OPORTUNIDADES -->
            <section class="section backlog-section">
                <h2 style="color: #ff9800;"><span class="icon">📋</span>BACKLOG PARA EXECUÇÃO</h2>
                <p>Tarefas priorizadas para o operador executar:</p>

                <div style="margin-top: 20px;">
"""

        # Cria backlog a partir das oportunidades
        backlog_tasks = []

        for i, opp in enumerate(self.oportunidades, 1):
            prioridade_num = 1 if opp.get('prioridade') == 'ALTA' else 2 if opp.get('prioridade') == 'MÉDIA' else 3
            task = {
                'id': i,
                'titulo': f"{opp['tipo']} - {opp['data']}",
                'descricao': opp['acao'],
                'prioridade': opp.get('prioridade', 'MÉDIA'),
                'prioridade_num': prioridade_num,
                'status': 'NOT_STARTED'
            }
            backlog_tasks.append(task)

        # Ordena por prioridade
        backlog_tasks.sort(key=lambda x: x['prioridade_num'])

        for task in backlog_tasks:
            priority_class = 'high' if task['prioridade'] == 'ALTA' else 'medium' if task['prioridade'] == 'MÉDIA' else 'low'
            html += f"""
                    <div class="action-item">
                        <div style="flex: 1;">
                            <div style="font-weight: bold; color: #667eea; margin-bottom: 5px;">
                                [{task['prioridade']}] {task['titulo']}
                            </div>
                            <div style="color: #666; font-size: 0.9em;">{task['descricao']}</div>
                        </div>
                        <input type="checkbox" class="checkbox" />
                    </div>
"""

        html += """
                </div>
                <div style="margin-top: 20px; padding: 15px; background: white; border-radius: 5px; border-left: 3px solid #28a745;">
                    <strong style="color: #28a745;">💾 Dica:</strong> Salve este arquivo e atualize o status das tarefas conforme as executa.
                </div>
            </section>

            <!-- ANÁLISE TÉCNICA RECOMENDADA -->
            <section class="section">
                <h2><span class="icon">🔧</span>RECOMENDAÇÕES TÉCNICAS PARA O OPERADOR</h2>

                <h3 style="color: #667eea; margin-top: 15px;">Para Day Trading (Mini Índice):</h3>
                <ul style="margin-left: 20px; color: #333;">
                    <li style="margin: 10px 0;">✓ Foco em breakouts acima da maior alta do dia anterior</li>
                    <li style="margin: 10px 0;">✓ Use Stop Loss em suportes locais (últimas 4-5 velas)</li>
                    <li style="margin: 10px 0;">✓ Monitore volume para confirmação de movimento</li>
                    <li style="margin: 10px 0;">✓ Ótimas oportunidades de scalping em alta liquidez de minis</li>
                </ul>

                <h3 style="color: #667eea; margin-top: 15px;">Para Swing Trading (Ações):</h3>
                <ul style="margin-left: 20px; color: #333;">
                    <li style="margin: 10px 0;">✓ Foque nas ações com maior volume do período</li>
                    <li style="margin: 10px 0;">✓ Analise padrões gráficos em timeframes diários</li>
                    <li style="margin: 10px 0;">✓ Use Fibonacci para projetar alvos de expansão</li>
                    <li style="margin: 10px 0;">✓ Verifique correlação com índices (IBOV, IBrX)</li>
                </ul>

                <h3 style="color: #667eea; margin-top: 15px;">Para Operações a Termo:</h3>
                <ul style="margin-left: 20px; color: #333;">
                    <li style="margin: 10px 0;">✓ Identifique as ações com maior open interest</li>
                    <li style="margin: 10px 0;">✓ Calcule o custo de carrego (taxa + taxa de juros)</li>
                    <li style="margin: 10px 0;">✓ Monitore diferença entre spot e termo</li>
                    <li style="margin: 10px 0;">✓ Aproveite ineficiências de precificação</li>
                </ul>
            </section>

            <!-- CONCLUSÃO -->
            <section class="section">
                <h2><span class="icon">✅</span>CONCLUSÃO</h2>
                <p>O mercado apresenta líquida em instrumentos de derivativos, especialmente em futuros de índice (mini), oferecendo excelentes oportunidades para day traders. A volatilidade moderada a alta observada cria ambiente propício para swing trades em ações selecionadas com maior volume.</p>

                <div class="highlight">
                    <strong>Recomendação Principal:</strong> Execuar as oportunidades priorizadas no backlog, começando pelas de prioridade ALTA. Monitore continuamente os volumes e ajuste a estratégia conforme a dinâmica do mercado evolui.
                </div>
            </section>

        </div>

        <footer>
            <p>Relatório gerado automaticamente pelo Sistema de Análise BDI</p>
            <p style="margin-top: 10px; font-size: 0.85em;">Operador Day Trade | Especialista em Mercado Brasileiro</p>
            <p style="margin-top: 10px; color: #999;">© 2026 - Todos os direitos reservados</p>
        </footer>
    </div>
</body>
</html>
"""

        return html

    def salvar_relatorio_html(self, html_content: str) -> Path:
        """Salva o relatório HTML no diretório de saída."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        arquivo = self.output_path / f"relatorio_bdi_{timestamp}.html"

        arquivo.parent.mkdir(parents=True, exist_ok=True)

        with open(arquivo, 'w', encoding='utf-8') as f:
            f.write(html_content)

        print(f"\n✅ Relatório HTML salvo em: {arquivo}")
        return arquivo

    def salvar_backlog_json(self):
        """Salva o backlog em formato JSON para integração com ferramentas."""
        backlog = {
            'data_geracao': datetime.now().isoformat(),
            'total_oportunidades': len(self.oportunidades),
            'oportunidades': self.oportunidades,
            'gaps': self.gaps,
            'insights': self.insights
        }

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        arquivo = self.output_path / f"backlog_{timestamp}.json"

        with open(arquivo, 'w', encoding='utf-8') as f:
            json.dump(backlog, f, ensure_ascii=False, indent=2)

        print(f"✅ Backlog JSON salvo em: {arquivo}")
        return arquivo

    def executar_analise_completa(self):
        """Executa a análise completa."""
        print("\n" + "="*80)
        print("🤖 ANALISTA DE DADOS B3 - PROCESSAMENTO DE BDI")
        print("="*80)

        # Etapa 1: Processar BDIs
        self.processar_multiplos_bdi(quantidade=5)

        # Etapa 2: Analisar tendências
        self.analisar_tendencias()

        # Etapa 3: Identificar oportunidades
        self.identificar_oportunidades()

        # Etapa 4: Identificar gaps
        self.identificar_gaps()

        # Etapa 5: Gerar relatório HTML
        print(f"\n📝 GERANDO RELATÓRIO HTML")
        html_content = self.gerar_relatorio_html()
        arquivo_html = self.salvar_relatorio_html(html_content)

        # Etapa 6: Salvar backlog
        print(f"\n📋 GERANDO BACKLOG")
        arquivo_backlog = self.salvar_backlog_json()

        # Resumo final
        print("\n" + "="*80)
        print("📊 RESUMO FINAL")
        print("="*80)
        print(f"✓ Boletins processados: {len(self.dados_bdi)}")
        print(f"✓ Insights gerados: {len(self.insights)}")
        print(f"✓ Oportunidades identificadas: {len(self.oportunidades)}")
        print(f"✓ Gaps mapeados: {len(self.gaps)}")
        print(f"\n📄 Relatório: {arquivo_html}")
        print(f"📋 Backlog: {arquivo_backlog}")

        return {
            'relatorio_html': arquivo_html,
            'backlog_json': arquivo_backlog,
            'dados_bdi': self.dados_bdi,
            'oportunidades': self.oportunidades,
            'gaps': self.gaps,
            'insights': self.insights
        }


def main():
    """Função principal."""
    analista = AnalistaBDI()
    resultado = analista.executar_analise_completa()
    return resultado


if __name__ == "__main__":
    main()
