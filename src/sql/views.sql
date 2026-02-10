
-- ============================================================================
-- LIMPEZA DE VIEWS ANTIGAS (Deprecation)
-- ============================================================================
DROP VIEW IF EXISTS vw_dim_profissionais;
DROP VIEW IF EXISTS vw_dim_clientes;
DROP VIEW IF EXISTS vw_dim_servicos;
DROP VIEW IF EXISTS vw_dim_calendario;
DROP VIEW IF EXISTS vw_dim_categorias;
DROP VIEW IF EXISTS vw_fato_financeiro;
DROP VIEW IF EXISTS vw_fato_taxas_cartao;
DROP VIEW IF EXISTS vw_fato_ocupacao;
DROP VIEW IF EXISTS vw_fato_vendas;
DROP VIEW IF EXISTS vw_competencia;

-- ============================================================================
-- CAMADA SILVER: DIMENSÕES (dim_)
-- ============================================================================

CREATE OR REPLACE VIEW dim_profissionais AS
SELECT
    id_profissional,
    nome,
    cargo,
    'Ativo' AS status
FROM
    tbl_0229_profissionais
WHERE
    nome IS NOT NULL
    AND nome != ''
UNION ALL
SELECT DISTINCT
    md5 (upper(trim(c.profissional))) AS id_profissional,
    c.profissional AS nome,
    'Histórico' AS cargo,
    'Inativo' AS status
FROM
    tbl_0186_comandas c
    LEFT JOIN tbl_0229_profissionais p ON upper(trim(c.profissional)) = upper(trim(p.nome))
WHERE
    p.nome IS NULL
    AND c.profissional IS NOT NULL
    AND c.profissional != '';

CREATE OR REPLACE VIEW dim_clientes AS
SELECT
    id_cliente,
    cliente,
    email,
    celular,
    data_nascimento,
    sexo
FROM
    tbl_0002_clientes;

CREATE OR REPLACE VIEW dim_servicos AS
SELECT DISTINCT
    id_servico,
    servico,
    grupo_servico
FROM
    tbl_0186_comandas
WHERE
    servico IS NOT NULL;

CREATE OR REPLACE VIEW dim_calendario AS
WITH dates AS (
    SELECT unnest(generate_series(DATE '2023-01-01', DATE '2030-12-31', INTERVAL 1 DAY)) AS data_series
)
SELECT
    CAST(data_series AS DATE) AS data,
    EXTRACT(YEAR FROM data_series) AS ano,
    EXTRACT(MONTH FROM data_series) AS mes,
    EXTRACT(DAY FROM data_series) AS dia,
    CASE EXTRACT(DOW FROM data_series)
        WHEN 0 THEN 'Domingo'
        WHEN 1 THEN 'Segunda-feira'
        WHEN 2 THEN 'Terça-feira'
        WHEN 3 THEN 'Quarta-feira'
        WHEN 4 THEN 'Quinta-feira'
        WHEN 5 THEN 'Sexta-feira'
        WHEN 6 THEN 'Sábado'
    END AS dia_semana,
    strftime(data_series, '%B') AS nome_mes,
    EXTRACT(QUARTER FROM data_series) AS trimestre,
    CAST(strftime(data_series, '%Y%m') AS INTEGER) AS ano_mes
FROM dates;

-- ============================================================================
-- CAMADA SILVER: FATOS (fct_)
-- ============================================================================

CREATE OR REPLACE VIEW fct_taxas_cartao AS
SELECT
    data_competencia,
    bandeira,
    valor_faturado,
    valor_liquido,
    (valor_faturado - valor_liquido) AS valor_taxa
FROM
    tbl_0188_bandeirascartao
WHERE
    valor_faturado IS NOT NULL
    AND valor_liquido IS NOT NULL;

CREATE OR REPLACE VIEW fct_ocupacao AS
SELECT
    md5 (UPPER(TRIM(profissional))) AS id_profissional,
    profissional,
    data_competencia,
    horas_agendadas_decimal
FROM
    tbl_0126_ocupacao
WHERE
    profissional IS NOT NULL
    AND profissional != '';

CREATE OR REPLACE VIEW fct_vendas AS
WITH vendas_ranked AS (
    SELECT
        data,
        comanda,
        cliente,
        -- ID único por visita (data + comanda + cliente)
        md5 (data::TEXT || comanda::TEXT || COALESCE(cliente, '')::TEXT) AS id_comanda,
        md5 (UPPER(TRIM(cliente))) AS id_cliente,
        md5 (UPPER(TRIM(profissional))) AS id_profissional,
        profissional,
        servico,
        grupo_servico,
        valor,
        desconto,
        comissao,
        custo,
        liquido,
        ROW_NUMBER() OVER (
            PARTITION BY md5 (UPPER(TRIM(cliente)))
            ORDER BY data
        ) AS venda_numero
    FROM
        tbl_0186_comandas
)
SELECT
    data,
    comanda,
    id_comanda,
    id_cliente,
    id_profissional,
    profissional,
    servico,
    grupo_servico,
    -- Nova coluna com fallback para grupo_servico vazio
    COALESCE(
        NULLIF(TRIM(grupo_servico), ''),
        'Outros'
    ) AS categoria_servico,
    valor,
    desconto,
    comissao,
    custo,
    liquido,
    (venda_numero > 1) AS is_recorrente
FROM
    vendas_ranked;

-- ============================================================================
-- CAMADA INTERMEDIÁRIA: FINANCEIRO (int_)
-- ============================================================================

CREATE OR REPLACE VIEW int_financeiro_competencia AS
SELECT
    f.data_movimento,
    f.categoria,
    f.titulo,
    f.fornecedor_cliente,
    f.observacoes,
    f.valor,
    c.nivel_1,
    c.nivel_2,
    c.excluir_dre
FROM
    tbl_0387_financeiro f
    LEFT JOIN tbl_dim_categorias c ON UPPER(TRIM(f.categoria)) = UPPER(TRIM(c.categoria))
WHERE
    f.tipo = 'Competencia';

CREATE OR REPLACE VIEW int_financeiro_caixa AS
SELECT
    f.*,
    c.nivel_1,
    c.nivel_2,
    c.excluir_dre
FROM
    tbl_0387_financeiro f
    LEFT JOIN tbl_dim_categorias c ON UPPER(TRIM(f.categoria)) = UPPER(TRIM(c.categoria))
WHERE
    f.tipo = 'Caixa';

-- ============================================================================
-- CAMADA GOLD: RELATÓRIOS (rep_)
-- ============================================================================

-- Relatório Financeiro por Competência (P&L Unificado)
CREATE OR REPLACE VIEW rep_financeiro_competencia AS
-- 1. Receita Bruta
SELECT
    f.data_movimento AS data,
    'Receita Bruta' AS grupo_metrica,
    f.nivel_2 AS subgrupo,
    f.valor AS valor,
    f.categoria AS categoria_detalhada,
    COALESCE(
        NULLIF(TRIM(f.titulo), ''),
        NULLIF(TRIM(f.fornecedor_cliente), ''),
        NULLIF(TRIM(f.observacoes), ''),
        f.categoria
    ) AS descricao
FROM
    int_financeiro_competencia f
WHERE
    f.nivel_1 = '1. Receita Bruta'

UNION ALL

-- 2. Comissões
SELECT
    v.data,
    'Comissões' AS grupo_metrica,
    'Comissões de Profissionais' AS subgrupo,
    v.comissao * -1 AS valor,
    'Comissões de Profissionais' AS categoria_detalhada,
    'Ref. Venda #' || v.comanda || ' - ' || v.profissional AS descricao
FROM
    fct_vendas v

UNION ALL

-- 3. Custo Serviço/Produto
SELECT
    f.data_movimento AS data,
    'Custo Serviço/Produto' AS grupo_metrica,
    f.nivel_2 AS subgrupo,
    ABS(f.valor) * -1 AS valor,
    f.categoria AS categoria_detalhada,
    COALESCE(
        NULLIF(TRIM(f.titulo), ''),
        NULLIF(TRIM(f.fornecedor_cliente), ''),
        NULLIF(TRIM(f.observacoes), ''),
        f.categoria
    ) AS descricao
FROM
    int_financeiro_competencia f
WHERE
    f.nivel_1 = '3. Custos Variáveis'
    AND UPPER(TRIM(f.categoria)) != 'PROFISSIONAIS - COMISSÕES'

UNION ALL

-- 4. Despesas Operacionais
SELECT
    f.data_movimento AS data,
    'Despesas Operacionais' AS grupo_metrica,
    f.nivel_2 AS subgrupo,
    ABS(f.valor) * -1 AS valor,
    f.categoria AS categoria_detalhada,
    COALESCE(
        NULLIF(TRIM(f.titulo), ''),
        NULLIF(TRIM(f.fornecedor_cliente), ''),
        NULLIF(TRIM(f.observacoes), ''),
        f.categoria
    ) AS descricao
FROM
    int_financeiro_competencia f
WHERE
    f.nivel_1 = '4. Despesas Operacionais'

UNION ALL

-- 5. Despesas Financeiras
SELECT
    data_competencia AS data,
    'Despesas Financeiras' AS grupo_metrica,
    'Taxas de Cartão' AS subgrupo,
    valor_taxa * -1 AS valor,
    'Taxas de Cartão' AS categoria_detalhada,
    'Taxas Maquininha/Antecipação' AS descricao
FROM
    fct_taxas_cartao

UNION ALL

-- 6. Resultado Financeiro
SELECT
    f.data_movimento AS data,
    'Resultado Financeiro' AS grupo_metrica,
    f.nivel_2 AS subgrupo,
    f.valor AS valor,
    f.categoria AS categoria_detalhada,
    COALESCE(
        NULLIF(TRIM(f.titulo), ''),
        NULLIF(TRIM(f.fornecedor_cliente), ''),
        NULLIF(TRIM(f.observacoes), ''),
        f.categoria
    ) AS descricao
FROM
    int_financeiro_competencia f
WHERE
    f.nivel_1 = '5. Resultado Financeiro';