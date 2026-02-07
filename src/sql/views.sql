CREATE
OR REPLACE VIEW vw_dim_profissionais AS
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

CREATE
OR REPLACE VIEW vw_dim_clientes AS
SELECT
    id_cliente,
    cliente,
    email,
    celular,
    data_nascimento,
    sexo
FROM
    tbl_0002_clientes;

CREATE
OR REPLACE VIEW vw_dim_servicos AS
SELECT DISTINCT
    id_servico,
    servico,
    grupo_servico
FROM
    tbl_0186_comandas
WHERE
    servico IS NOT NULL;

CREATE
OR REPLACE VIEW vw_dim_calendario AS
WITH
    dates AS (
        SELECT
            unnest (
                generate_series (
                    DATE '2023-01-01',
                    DATE '2030-12-31',
                    INTERVAL 1 DAY
                )
            ) AS data_series
    )
SELECT
    CAST(data_series AS DATE) AS data,
    EXTRACT(
        YEAR
        FROM
            data_series
    ) AS ano,
    EXTRACT(
        MONTH
        FROM
            data_series
    ) AS mes,
    EXTRACT(
        DAY
        FROM
            data_series
    ) AS dia,
    CASE EXTRACT(
            DOW
            FROM
                data_series
        )
        WHEN 0 THEN 'Domingo'
        WHEN 1 THEN 'Segunda-feira'
        WHEN 2 THEN 'Terça-feira'
        WHEN 3 THEN 'Quarta-feira'
        WHEN 4 THEN 'Quinta-feira'
        WHEN 5 THEN 'Sexta-feira'
        WHEN 6 THEN 'Sábado'
    END AS dia_semana,
    strftime (data_series, '%B') AS nome_mes, -- DuckDB strftime uses locale, might be English default, but user accepted simple strftime in prompt or we can use CASE if strictly requires PT. Prompt said "verifique documentação or use strftime". I will assume standard strftime is okay, but sticking to CASE for DOW as explicit request.
    EXTRACT(
        QUARTER
        FROM
            data_series
    ) AS trimestre,
    CAST(strftime (data_series, '%Y%m') AS INTEGER) AS ano_mes
FROM
    dates;

-- ============================================================================
-- DIMENSÃO: Categorias Financeiras
-- ============================================================================
-- NOTE: tbl_dim_categorias is a physical table loaded via load_categorias.py
-- This replaces the previous CSV-based view to work in Motherduck cloud.
-- ============================================================================
-- FATO: Financeiro (com hierarquia de categorias)
-- ============================================================================
CREATE
OR REPLACE VIEW vw_fato_financeiro AS
SELECT
    f.*,
    c.nivel_1,
    c.nivel_2,
    c.excluir_dre
FROM
    tbl_0387_financeiro f
    LEFT JOIN tbl_dim_categorias c ON UPPER(TRIM(f.categoria)) = UPPER(TRIM(c.categoria));

-- ============================================================================
-- FATO: Taxas de Cartão
-- ============================================================================
CREATE
OR REPLACE VIEW vw_fato_taxas_cartao AS
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

-- ============================================================================
-- FATO: Ocupação (com ID de profissional via MD5)
-- ============================================================================
CREATE
OR REPLACE VIEW vw_fato_ocupacao AS
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