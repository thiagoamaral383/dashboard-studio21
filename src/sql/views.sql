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