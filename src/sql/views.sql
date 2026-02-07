CREATE
OR REPLACE VIEW vw_dim_profissionais AS
SELECT
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
    c.profissional AS nome,
    'Não Informado' AS cargo,
    'Historico' AS status
FROM
    tbl_0186_comandas c
    LEFT JOIN tbl_0229_profissionais p ON c.profissional = p.nome
WHERE
    p.nome IS NULL
    AND c.profissional IS NOT NULL
    AND c.profissional != '';