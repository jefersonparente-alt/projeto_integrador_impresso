import zipfile
import shutil
import os
import xml.etree.ElementTree as ET

# Definindo namespaces OpenXML
w_ns = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
ET.register_namespace('w', w_ns)

def create_element(name, text=None, attrib=None):
    el = ET.Element(f'{{{w_ns}}}{name}')
    if attrib:
        for k, v in attrib.items():
            el.set(f'{{{w_ns}}}{k}', v)
    if text:
        el.text = text
    return el

def add_p(body, text="", bold=False, italic=False, font_size=24, align='left', space_before=0, space_after=120, line_spacing=360, is_heading=False):
    p = ET.SubElement(body, f'{{{w_ns}}}p')
    pPr = ET.SubElement(p, f'{{{w_ns}}}pPr')
    
    if align != 'left':
        jc = ET.SubElement(pPr, f'{{{w_ns}}}jc')
        jc.set(f'{{{w_ns}}}val', align)
        
    spacing = ET.SubElement(pPr, f'{{{w_ns}}}spacing')
    spacing.set(f'{{{w_ns}}}before', str(space_before))
    spacing.set(f'{{{w_ns}}}after', str(space_after))
    spacing.set(f'{{{w_ns}}}line', str(line_spacing))
    spacing.set(f'{{{w_ns}}}lineRule', 'auto')
    
    if text:
        r = ET.SubElement(p, f'{{{w_ns}}}r')
        rPr = ET.SubElement(r, f'{{{w_ns}}}rPr')
        
        rFonts = ET.SubElement(rPr, f'{{{w_ns}}}rFonts')
        rFonts.set(f'{{{w_ns}}}ascii', 'Arial')
        rFonts.set(f'{{{w_ns}}}hAnsi', 'Arial')
        rFonts.set(f'{{{w_ns}}}cs', 'Arial')
        
        sz = ET.SubElement(rPr, f'{{{w_ns}}}sz')
        sz.set(f'{{{w_ns}}}val', str(font_size))
        
        if bold or is_heading:
            ET.SubElement(rPr, f'{{{w_ns}}}b')
        if italic:
            ET.SubElement(rPr, f'{{{w_ns}}}i')
            
        t = ET.SubElement(r, f'{{{w_ns}}}t')
        t.text = text
        # Garantir preservação de espaços
        t.set('{http://www.w3.org/XML/1998/namespace}space', 'preserve')
    return p

def add_page_break(body):
    p = ET.SubElement(body, f'{{{w_ns}}}p')
    r = ET.SubElement(p, f'{{{w_ns}}}r')
    ET.SubElement(r, f'{{{w_ns}}}br', {f'{{{w_ns}}}type': 'page'})

def add_table(body, rows_data, col_widths=None):
    tbl = ET.SubElement(body, f'{{{w_ns}}}tbl')
    tblPr = ET.SubElement(tbl, f'{{{w_ns}}}tblPr')
    
    # Bordas
    tblBorders = ET.SubElement(tblPr, f'{{{w_ns}}}tblBorders')
    for border_name in ['top', 'left', 'bottom', 'right', 'insideH', 'insideV']:
        b = ET.SubElement(tblBorders, f'{{{w_ns}}}{border_name}')
        b.set(f'{{{w_ns}}}val', 'single')
        b.set(f'{{{w_ns}}}sz', '4')
        b.set(f'{{{w_ns}}}space', '0')
        b.set(f'{{{w_ns}}}color', 'CCCCCC')
        
    for r_idx, row in enumerate(rows_data):
        tr = ET.SubElement(tbl, f'{{{w_ns}}}tr')
        for c_idx, cell_text in enumerate(row):
            tc = ET.SubElement(tr, f'{{{w_ns}}}tc')
            tcPr = ET.SubElement(tc, f'{{{w_ns}}}tcPr')
            if col_widths and c_idx < len(col_widths):
                tcW = ET.SubElement(tcPr, f'{{{w_ns}}}tcW')
                tcW.set(f'{{{w_ns}}}w', str(col_widths[c_idx]))
                tcW.set(f'{{{w_ns}}}type', 'dxa')
                
            # Shading para cabeçalho
            if r_idx == 0:
                shd = ET.SubElement(tcPr, f'{{{w_ns}}}shd')
                shd.set(f'{{{w_ns}}}val', 'clear')
                shd.set(f'{{{w_ns}}}color', 'auto')
                shd.set(f'{{{w_ns}}}fill', 'EAECEF')
                
            p = ET.SubElement(tc, f'{{{w_ns}}}p')
            pPr = ET.SubElement(p, f'{{{w_ns}}}pPr')
            spacing = ET.SubElement(pPr, f'{{{w_ns}}}spacing')
            spacing.set(f'{{{w_ns}}}before', '60')
            spacing.set(f'{{{w_ns}}}after', '60')
            spacing.set(f'{{{w_ns}}}line', '240')
            
            r = ET.SubElement(p, f'{{{w_ns}}}r')
            rPr = ET.SubElement(r, f'{{{w_ns}}}rPr')
            rFonts = ET.SubElement(rPr, f'{{{w_ns}}}rFonts')
            rFonts.set(f'{{{w_ns}}}ascii', 'Arial')
            rFonts.set(f'{{{w_ns}}}hAnsi', 'Arial')
            sz = ET.SubElement(rPr, f'{{{w_ns}}}sz')
            sz.set(f'{{{w_ns}}}val', '20')
            if r_idx == 0:
                ET.SubElement(rPr, f'{{{w_ns}}}b')
                
            t = ET.SubElement(r, f'{{{w_ns}}}t')
            t.text = cell_text
            t.set('{http://www.w3.org/XML/1998/namespace}space', 'preserve')

def generate_docx():
    src_docx = 'docs/Documento_Norteador_Sistema_Solicitacao_Impressos.docx'
    dst_docx = 'docs/Documento_Projeto_Integrador_Final.docx'
    
    # Extrair e inspecionar
    with zipfile.ZipFile(src_docx, 'r') as zin:
        zin.extractall('docs/docx_temp')
        
    doc_path = 'docs/docx_temp/word/document.xml'
    tree = ET.parse(doc_path)
    root = tree.getroot()
    body = root.find(f'{{{w_ns}}}body')
    
    # Guardar sectPr original
    sectPr = body.find(f'{{{w_ns}}}sectPr')
    body.clear()
    
    # ------------------ CAPA ------------------
    add_p(body, "ESCOLA ESTADUAL DE EDUCAÇÃO PROFISSIONAL", bold=True, font_size=26, align='center', space_before=200, space_after=100)
    add_p(body, "CURSO TÉCNICO EM DESENVOLVIMENTO DE SISTEMAS", bold=True, font_size=24, align='center', space_after=600)
    
    add_p(body, "PROJETO INTEGRADOR", bold=True, font_size=28, align='center', space_before=1000, space_after=200)
    add_p(body, "SISTEMA WEB UNIFICADO DE SOLICITAÇÃO E GESTÃO DE IMPRESSÕES COM FILA CRONOLÓGICA (FIFO)", bold=True, font_size=26, align='center', space_after=1200)
    
    add_p(body, "ALUNOS(AS):", bold=True, font_size=22, align='center', space_after=60)
    add_p(body, "[Inserir Nome dos Integrantes da Equipe]", font_size=22, align='center', space_after=300)
    
    add_p(body, "PROFESSOR(A) ORIENTADOR(A):", bold=True, font_size=22, align='center', space_after=60)
    add_p(body, "[Inserir Nome do(a) Professor(a) Orientador(a)]", font_size=22, align='center', space_after=1400)
    
    add_p(body, "SÃO PAULO - SP", bold=True, font_size=22, align='center', space_after=60)
    add_p(body, "NOVEMBRO DE 2026", bold=True, font_size=22, align='center', space_after=200)
    
    add_page_break(body)
    
    # ------------------ FOLHA DE ROSTO ------------------
    add_p(body, "ALUNOS(AS): [Inserir Nomes dos Alunos]", bold=True, font_size=24, align='center', space_before=300, space_after=800)
    
    add_p(body, "SISTEMA WEB UNIFICADO DE SOLICITAÇÃO E GESTÃO DE IMPRESSÕES COM FILA CRONOLÓGICA (FIFO)", bold=True, font_size=26, align='center', space_after=1200)
    
    add_p(body, "Trabalho de Conclusão de Curso / Projeto Integrador apresentado como requisito parcial para obtenção do título de Técnico em Desenvolvimento de Sistemas.", italic=True, font_size=20, align='right', space_after=400, line_spacing=280)
    
    add_p(body, "Área de Concentração: Desenvolvimento Web, Engenharia de Software e Banco de Dados.", italic=True, font_size=20, align='right', space_after=1400, line_spacing=280)
    
    add_p(body, "SÃO PAULO - SP", bold=True, font_size=22, align='center', space_after=60)
    add_p(body, "NOVEMBRO DE 2026", bold=True, font_size=22, align='center', space_after=200)
    
    add_page_break(body)
    
    # ------------------ SUMÁRIO ------------------
    add_p(body, "SUMÁRIO", bold=True, font_size=28, align='center', space_before=200, space_after=400)
    sumario_itens = [
        "1 INTRODUÇÃO ................................................................................................................................. 04",
        "  1.1 OBJETIVOS ............................................................................................................................ 05",
        "    1.1.1 Objetivo Geral ................................................................................................................. 05",
        "    1.1.2 Objetivos Específicos ..................................................................................................... 05",
        "  1.2 METODOLOGIA ...................................................................................................................... 06",
        "2 REFERENCIAL TEÓRICO ......................................................................................................... 07",
        "  2.1 O Modelo Arquitetural MVC / MVT no Django ................................................................. 07",
        "  2.2 Filas de Atendimento e Disciplina FIFO .............................................................................. 08",
        "  2.3 Segurança, Isolamento de Dados e RBAC ......................................................................... 09",
        "3 CONSIDERAÇÕES FINAIS ...................................................................................................... 10",
        "4 REFERÊNCIAS .......................................................................................................................... 12",
        "APÊNDICES ................................................................................................................................. 13",
        "  APÊNDICE A – Registros e Descrições das Telas do Sistema ............................................ 13",
        "  APÊNDICE B – Especificação de Rotas e Contratos de Dados ............................................. 17",
        "ANEXOS ........................................................................................................................................ 18",
        "  ANEXO A – Diagrama Entidade-Relacionamento do Banco de Dados ................................. 18"
    ]
    for item in sumario_itens:
        add_p(body, item, font_size=20, align='left', space_after=80, line_spacing=280)
        
    add_page_break(body)
    
    # ------------------ 1 INTRODUÇÃO ------------------
    add_p(body, "1 INTRODUÇÃO", bold=True, font_size=26, align='left', space_before=200, space_after=200)
    add_p(body, "No cotidiano das instituições de ensino, o setor de reprografia e gráfica desempenha um papel essencial no suporte pedagógico e administrativo, sendo responsável pela produção física de avaliações, apostilas, comunicados, projetos acadêmicos e documentos curriculares. Contudo, em diversas escolas, o recebimento desses pedidos ainda ocorre por meio de canais informais e desestruturados, em especial através de e-mails institucionais ou mensagens instantâneas.", font_size=24, align='both', space_after=140, line_spacing=360)
    add_p(body, "Esse método tradicional acarreta gargalos críticos para a comunidade escolar: mensagens misturadas a conversas gerais, perda de anexos, duplicidade de impressões, ausência de padronização nas especificações técnicas (como frente e verso ou escala de cores), além da incapacidade de responder a questionamentos frequentes sobre a previsão de entrega. A consequência direta é o desgaste entre solicitantes e operadores gráficos, acompanhado pelo desperdício de insumos materiais (papel e toner) e retrabalho contínuo.", font_size=24, align='both', space_after=140, line_spacing=360)
    add_p(body, "Diante desse cenário, este trabalho apresenta o desenvolvimento e a homologação do Sistema de Solicitação e Gestão de Impressões, uma plataforma web completa construída com a linguagem Python e o framework Django. A solução substitui integralmente a caixa de e-mails por um fluxo unificado e auditável, garantindo que todo pedido receba um código de protocolo único no momento do cadastro e seja organizado em uma fila de atendimento estritamente cronológica, baseada no princípio FIFO (First In, First Out).", font_size=24, align='both', space_after=140, line_spacing=360)
    add_p(body, "A aplicação foi planejada considerando as normas e padrões da Associação Brasileira de Normas Técnicas (ABNT), fornecendo uma arquitetura modular, responsiva via Bootstrap 5, com armazenamento seguro de anexos em formato PDF, controle granular de perfis de usuário (Role-Based Access Control - RBAC), painel administrativo executivo com métricas em tempo real e rotina automática de contingência e backup.", font_size=24, align='both', space_after=200, line_spacing=360)
    
    # 1.1 OBJETIVOS
    add_p(body, "1.1 OBJETIVOS", bold=True, font_size=24, align='left', space_before=200, space_after=140)
    
    # 1.1.1 Objetivo Geral
    add_p(body, "1.1.1 Objetivo Geral", bold=True, font_size=22, align='left', space_before=140, space_after=100)
    add_p(body, "Desenvolver e implantar uma plataforma web completa e segura para centralizar, padronizar e gerenciar as solicitações de impressão do ambiente escolar, organizando o fluxo de trabalho do setor de reprografia por ordem cronológica de chegada (FIFO) e garantindo transparência por meio de rastreamento por protocolo.", font_size=24, align='both', space_after=160, line_spacing=360)
    
    # 1.1.2 Objetivos Específicos
    add_p(body, "1.1.2 Objetivos Específicos", bold=True, font_size=22, align='left', space_before=140, space_after=100)
    add_p(body, "• Centralizar e padronizar o recebimento de arquivos: Extinguir o tráfego de pedidos por e-mail, exigindo preenchimento de formulário estruturado e upload restrito a documentos em formato PDF (application/pdf) com validação de tamanho máximo de 25MB.", font_size=24, align='both', space_after=100, line_spacing=360)
    add_p(body, "• Implementar a gestão de fila cronológica auditável (FIFO): Ordenar automaticamente os pedidos do setor pelo timestamp exato de criação (criado_em), assegurando que alterações de status ou prazos informados não burlem a ordem natural de chegada, exceto mediante concessão formal de prioridade justificada.", font_size=24, align='both', space_after=100, line_spacing=360)
    add_p(body, "• Prover transparência e isolamento no rastreamento de pedidos: Permitir que cada usuário acompanhe a evolução de seus pedidos (Recebida, Em andamento, Aguardando correção, Concluída e Cancelada), garantindo isolamento total (Row-Level Security), consulta pública rápida por protocolo e reenvio facilitado de arquivos corrigidos.", font_size=24, align='both', space_after=100, line_spacing=360)
    add_p(body, "• Disponibilizar painel gerencial e rotinas de segurança: Fornecer aos administradores indicadores de volume, distribuição por departamento, gerenciamento de permissões de usuários e rotina de backup compactado com retenção programada.", font_size=24, align='both', space_after=200, line_spacing=360)
    
    # 1.2 METODOLOGIA
    add_p(body, "1.2 METODOLOGIA", bold=True, font_size=24, align='left', space_before=200, space_after=140)
    add_p(body, "O projeto adotou uma abordagem metodológica baseada na pesquisa aplicada e descritiva, conduzida através do ciclo de desenvolvimento de software em conformidade com o modelo ágil adaptado. O processo foi estruturado em cinco fases iterativas:", font_size=24, align='both', space_after=140, line_spacing=360)
    add_p(body, "1. Levantamento e Diagnóstico: Análise detalhada dos procedimentos manuais do setor gráfico descritos no Documento Norteador, identificando pontos de atrito, perfis envolvidos e requisitos regulatórios.", font_size=24, align='both', space_after=100, line_spacing=360)
    add_p(body, "2. Modelagem Arquitetural e de Banco: Elaboração do Diagrama Entidade-Relacionamento contemplando cinco entidades fundamentais (Usuario, Solicitacao, Anexo, HistoricoStatus, ExcecaoPrioridade).", font_size=24, align='both', space_after=100, line_spacing=360)
    add_p(body, "3. Desenvolvimento Iterativo: Implementação na linguagem Python 3.12+ utilizando o framework web Django 6, obedecendo ao padrão estrutural MVT (Model-View-Template), com interface responsiva desenvolvida em HTML5, CSS3 e Bootstrap 5.", font_size=24, align='both', space_after=100, line_spacing=360)
    add_p(body, "4. Verificação e Garantia de Qualidade: Criação de uma suíte formal de testes automatizados com 19 cenários obrigatórios (TC01 ao TC15) cobrindo regras de negócio, invariantes temporais, validações de arquivo e controle de acesso (RBAC).", font_size=24, align='both', space_after=100, line_spacing=360)
    add_p(body, "5. Estratégia de Infraestrutura e Implantação: Concepção de uma arquitetura híbrida com suporte a ambiente de desenvolvimento local (SQLite) e ambiente de produção serverless na Vercel com banco gerenciado PostgreSQL no Neon, distribuição otimizada de estáticos via WhiteNoise e contingência via comando de backup.", font_size=24, align='both', space_after=200, line_spacing=360)
    
    add_page_break(body)
    
    # ------------------ 2 REFERENCIAL TEÓRICO ------------------
    add_p(body, "2 REFERENCIAL TEÓRICO", bold=True, font_size=26, align='left', space_before=200, space_after=200)
    
    # 2.1 MVT
    add_p(body, "2.1 O Modelo Arquitetural MVC / MVT no Django", bold=True, font_size=24, align='left', space_before=140, space_after=140)
    add_p(body, "O desenvolvimento de sistemas corporativos modernos requer desacoplamento entre regras de persistência de dados, lógica de negócio e camada de apresentação. O Django adota a variação MVT (Model-View-Template), originada do clássico padrão MVC (Model-View-Controller) preconizado por Gamma et al. (1995) e adaptado por Holovaty e Kaplan-Moss (2009):", font_size=24, align='both', space_after=140, line_spacing=360)
    add_p(body, "• Model (Modelo): Encapsula a lógica de dados, integridade referencial e validações estruturais via ORM (Object-Relational Mapping), eliminando a necessidade de SQL manual e garantindo portabilidade entre SQLite e PostgreSQL.", font_size=24, align='both', space_after=100, line_spacing=360)
    add_p(body, "• View (Visão/Controlador): Atua como coordenador de fluxo, interceptando requisições HTTP, executando validações de autenticação e permissões, disparando serviços e delegando a apresentação.", font_size=24, align='both', space_after=100, line_spacing=360)
    add_p(body, "• Template (Gabarito de Apresentação): Responsável por renderizar a interface gráfica para o usuário final, utilizando marcação semântica e recursos de herança para reutilização de componentes estruturais.", font_size=24, align='both', space_after=180, line_spacing=360)
    
    # 2.2 Filas FIFO
    add_p(body, "2.2 Filas de Atendimento e Disciplina FIFO", bold=True, font_size=24, align='left', space_before=140, space_after=140)
    add_p(body, "A organização de processos de atendimento ao cliente ou a setores internos baseia-se na teoria das filas. Segundo Taha (2014) e Hillier & Lieberman (2013), a disciplina FIFO (First In, First Out) ou PEPS (Primeiro que Entra, Primeiro que Sai) é a política mais equitativa em sistemas de serviço compartilhado, minimizando a variância do tempo de espera e eliminando percepções de favorecimento indevido. No contexto deste projeto:", font_size=24, align='both', space_after=140, line_spacing=360)
    add_p(body, "• A chave de ordenação da fila do setor é estritamente a tupla ('criado_em', 'id'), computada no instante de persistência pelo servidor.", font_size=24, align='both', space_after=100, line_spacing=360)
    add_p(body, "• O campo prazo_desejado é meramente consultivo e não altera a cronologia de produção, a menos que uma ExcecaoPrioridade seja concedida e justificada formalmente por um usuário autorizado.", font_size=24, align='both', space_after=180, line_spacing=360)
    
    # 2.3 Segurança
    add_p(body, "2.3 Segurança, Isolamento de Dados e RBAC", bold=True, font_size=24, align='left', space_before=140, space_after=140)
    add_p(body, "Conforme as recomendações da OWASP (Open Web Application Security Project, 2021) e da Lei Geral de Proteção de Dados (LGPD - Lei nº 13.709/2018), sistemas de informação que tratam documentos internos devem implementar controle rigoroso de acesso:", font_size=24, align='both', space_after=140, line_spacing=360)
    add_p(body, "• RBAC (Role-Based Access Control): Segregação dos usuários em três níveis funcionais: Solicitante (restrito à submissão e consulta de seus próprios pedidos); Colaborador (visualização da fila unificada e atualização técnica de status); e Administrador (auditoria global, relatórios analíticos e parametrização de contas).", font_size=24, align='both', space_after=100, line_spacing=360)
    add_p(body, "• Proteção de Mídia e Anexos: Bloqueio de diretórios públicos de upload (MEDIA_URL). A entrega de arquivos PDF é efetuada sob demanda através de views protegidas (FileResponse), validando se o requisitante é o autor do pedido ou membro da equipe técnica, prevenindo ataques de enumeração direta de URLs (Direct Object References - IDOR).", font_size=24, align='both', space_after=200, line_spacing=360)
    
    add_page_break(body)
    
    # ------------------ 3 CONSIDERAÇÕES FINAIS ------------------
    add_p(body, "3 CONSIDERAÇÕES FINAIS", bold=True, font_size=26, align='left', space_before=200, space_after=200)
    add_p(body, "A implementação do Sistema de Solicitação e Gestão de Impressões resolveu de maneira definitiva os entraves históricos provocados pelo uso do e-mail no setor gráfico da instituição escolar. Os resultados alcançados pelo projeto destacam:", font_size=24, align='both', space_after=140, line_spacing=360)
    add_p(body, "1. Eficiência e Padronização Operacional: A adoção do formulário eletrônico unificado eliminou pedidos com dados faltantes. A exigência de arquivos estritamente em formato PDF com limite de 25MB padronizou o processo produtivo, evitando paradas por incompatibilidade de formatos proprietários.", font_size=24, align='both', space_after=100, line_spacing=360)
    add_p(body, "2. Equidade e Clareza na Gestão de Prazos: A aplicação da regra FIFO auditada garantiu um fluxo de atendimento justo e transparente. Com os números de protocolo únicos (IMP-AAAAMM-XXXXX) e a timeline de transição de status, os solicitantes podem acompanhar o estado de suas solicitações sem precisar interromper o trabalho da equipe de reprografia.", font_size=24, align='both', space_after=100, line_spacing=360)
    add_p(body, "3. Confiabilidade, Segurança e Auditoria: A rastreabilidade completa em HistoricoStatus e a obrigatoriedade de justificativa formal em ExcecaoPrioridade asseguram conformidade com as diretrizes de governança escolar. O isolamento de acesso aos anexos protege o sigilo de materiais pedagógicos e avaliações escolares.", font_size=24, align='both', space_after=100, line_spacing=360)
    add_p(body, "4. Robustez de Engenharia de Software: Com 100% de aprovação na suíte de testes automatizados (19 casos de teste validados), migrações consistentes, arquitetura híbrida (SQLite local e Neon PostgreSQL em produção) e rotina de backup compactado com retenção histórica, o sistema demonstra maturidade técnica para implantação definitiva.", font_size=24, align='both', space_after=200, line_spacing=360)
    
    # ------------------ 4 REFERÊNCIAS ------------------
    add_p(body, "4 REFERÊNCIAS", bold=True, font_size=26, align='left', space_before=200, space_after=200)
    refs = [
        "BRASIL. Lei nº 13.709, de 14 de agosto de 2018. Lei Geral de Proteção de Dados Pessoais (LGPD). Brasília, DF: Presidência da República, 2018.",
        "GAMMA, Erich; HELM, Richard; JOHNSON, Ralph; VLISSIDES, John. Padrões de Projeto: Soluções Reutilizáveis de Software Orientado a Objetos. Porto Alegre: Bookman, 1995.",
        "HILLIER, Frederick S.; LIEBERMAN, Gerald J. Introdução à Pesquisa Operacional. 9. ed. Porto Alegre: AMGH, 2013.",
        "HOLOVATY, Adrian; KAPLAN-MOSS, Jacob. The Definitive Guide to Django: Web Development Done Right. 2. ed. Nova York: Apress, 2009.",
        "OWASP FOUNDATION. OWASP Top 10: The Ten Most Critical Web Application Security Risks. 2021. Disponível em: <https://owasp.org/Top10/>. Acesso em: 20 nov. 2026.",
        "PYTHON SOFTWARE FOUNDATION. Python 3 Documentation and Language Reference. 2026. Disponível em: <https://docs.python.org/3/>. Acesso em: 18 nov. 2026.",
        "TAHA, Hamdy A. Pesquisa Operacional: Uma Visão Geral. 8. ed. São Paulo: Pearson Prentice Hall, 2014."
    ]
    for ref in refs:
        add_p(body, ref, font_size=22, align='both', space_after=120, line_spacing=280)
        
    add_page_break(body)
    
    # ------------------ APÊNDICES ------------------
    add_p(body, "APÊNDICES", bold=True, font_size=26, align='center', space_before=200, space_after=200)
    
    add_p(body, "APÊNDICE A – Registros e Descrições das Telas do Sistema", bold=True, font_size=24, align='left', space_before=140, space_after=140)
    
    telas = [
        ("Tela 1: Autenticação Segura e Contas de Demonstração", 
         "Acesso ao portal com autenticação por e-mail institucional e senha, com indicação dos perfis de acesso disponíveis para teste (Solicitante, Colaborador e Administrador). Permite que os usuários efetuem login seguro e sejam direcionados automaticamente para suas respectivas interfaces funcionais.",
         "docs/prints/01_login.html"),
        ("Tela 2: Consulta Pública Rápida por Código de Protocolo", 
         "Permite a qualquer membro da comunidade escolar verificar o andamento de um pedido sem necessidade de login prévio, exibindo status atual, solicitante, data/hora e orientações técnicas de entrega ou necessidade de correção.",
         "docs/prints/02_consulta_publica.html"),
        ("Tela 3: Painel do Solicitante (\"Minhas Solicitações\")", 
         "Visão restrita do solicitante exibindo apenas seus próprios pedidos, ordenados pelo histórico com badges coloridos de status, total de cópias, tipo de impressão e botão direto para consulta detalhada da timeline.",
         "docs/prints/03_painel_solicitante.html"),
        ("Tela 4: Formulário de Nova Solicitação com Upload de PDF", 
         "Interface completa para submissão de arquivo digital (restrito a formato PDF até 25MB) com parâmetros de quantidade de cópias, opções de acabamento (frente/verso, escala de cores), prazo desejado meramente consultivo e campo aberto para instruções.",
         "docs/prints/04_nova_solicitacao.html"),
        ("Tela 5: Painel Operacional da Gráfica — Fila Cronológica FIFO", 
         "Painel exclusivo dos colaboradores e administradores exibindo os pedidos em ordem rigorosa de chegada (#1, #2, #3...), com visualizador integrado de documentos, controle de transição de status auditado e registro formal de exceções de prioridade.",
         "docs/prints/05_fila_setor_fifo.html"),
        ("Tela 6: Painel Executivo Administrativo com Indicadores", 
         "Visão gerencial reservada à diretoria e administração, com contadores em tempo real de volume geral, distribuição de demandas por status, divisão por escala de cores (P&B vs Colorida) e busca global de solicitações.",
         "docs/prints/06_painel_administrativo.html"),
        ("Tela 7: Gestão Administrativa de Contas e Perfis de Acesso", 
         "Interface de governança para alteração de perfis (Solicitante, Colaborador, Administrador), ativação e desativação de contas com mecanismo nativo de proteção contra auto-bloqueio de administradores.",
         "docs/prints/07_gestao_usuarios.html"),
    ]
    
    for titulo, desc, path in telas:
        add_p(body, titulo, bold=True, font_size=22, align='left', space_before=140, space_after=80)
        add_p(body, desc, font_size=22, align='both', space_after=80, line_spacing=280)
        add_p(body, f"[Arquivo HTML do Snapshot Operacional: {path}]", italic=True, font_size=20, align='left', space_after=140)
        
    add_p(body, "APÊNDICE B – Especificação de Rotas e Contratos de Dados", bold=True, font_size=24, align='left', space_before=200, space_after=140)
    
    rotas_data = [
        ["Funcionalidade", "Rota", "Método", "Permissão", "Descrição"],
        ["Login", "/login/", "GET, POST", "Pública", "Autenticação por e-mail e senha."],
        ["Auto-cadastro", "/cadastro/", "GET, POST", "Pública", "Criação de conta autônoma de solicitante."],
        ["Consulta Rápida", "/consulta/", "GET", "Pública", "Busca direta de pedido por protocolo."],
        ["Minhas Solicitações", "/", "GET", "Solicitante", "Listagem individual de pedidos do usuário."],
        ["Nova Solicitação", "/solicitacoes/nova/", "GET, POST", "Solicitante", "Submissão de pedido e upload de PDF."],
        ["Detalhes do Pedido", "/solicitacoes/<prot>/", "GET, POST", "Autorizado", "Timeline, download e reenvio de correção."],
        ["Fila FIFO Setor", "/setor/", "GET", "Equipe", "Fila cronológica de atendimento da gráfica."],
        ["Atendimento Técnico", "/setor/atendimento/<prot>/", "GET, POST", "Equipe", "Visualização de PDF e alteração de status."],
        ["Painel Executivo", "/gestao/", "GET", "Admin", "Métricas gerais, volume e relatórios."],
        ["Gestão de Usuários", "/gestao/usuarios/", "GET, POST", "Admin", "Modificação de perfis e ativação de contas."],
        ["Download de Anexo", "/anexos/<id>/download/", "GET", "Autorizado", "Entrega segura de PDF via FileResponse."]
    ]
    add_table(body, rotas_data, [1800, 2200, 1000, 1400, 2800])
    
    add_page_break(body)
    
    # ------------------ ANEXOS ------------------
    add_p(body, "ANEXOS", bold=True, font_size=26, align='center', space_before=200, space_after=200)
    add_p(body, "ANEXO A – Diagrama Entidade-Relacionamento do Banco de Dados", bold=True, font_size=24, align='left', space_before=140, space_after=140)
    add_p(body, "A modelagem relacional homologada do sistema contempla cinco entidades interligadas, refletindo com exatidão o diagrama técnico disponível no repositório (docs/diagrama_er_banco.png):", font_size=24, align='both', space_after=140, line_spacing=360)
    
    er_data = [
        ["Entidade", "Chave Primária", "Chaves Estrangeiras", "Campos Relevantes"],
        ["Usuario", "id (PK)", "Nenhuma", "email (UK), nome, perfil, setor_turma, contato, ativo"],
        ["Solicitacao", "id (PK)", "solicitante_id (FK)", "protocolo (UK), quantidade_copias, tipo_impressao, frente_verso, status_atual, criado_em"],
        ["Anexo", "id (PK)", "solicitacao_id (FK)", "nome_original, arquivo, tipo_arquivo, tamanho_bytes, enviado_em"],
        ["HistoricoStatus", "id (PK)", "solicitacao_id (FK), usuario_id (FK)", "status_anterior, status_novo, data_hora, observacao"],
        ["ExcecaoPrioridade", "id (PK)", "solicitacao_id (FK), autorizado_por_id (FK)", "justificativa, criada_em"]
    ]
    add_table(body, er_data, [1800, 1400, 2600, 3400])
    
    # Recolocar sectPr
    if sectPr is not None:
        body.append(sectPr)
        
    tree.write(doc_path, xml_declaration=True, encoding='utf-8')
    
    # Criar o docx final zipado
    with zipfile.ZipFile(dst_docx, 'w', zipfile.ZIP_DEFLATED) as zout:
        for root_dir, dirs, files in os.walk('docs/docx_temp'):
            for file in files:
                full_path = os.path.join(root_dir, file)
                rel_path = os.path.relpath(full_path, 'docs/docx_temp')
                zout.write(full_path, rel_path)
                
    shutil.rmtree('docs/docx_temp')
    print("Sucesso: Documento_Projeto_Integrador_Final.docx gerado!")

if __name__ == '__main__':
    generate_docx()
