# Dados

- `instacart/`: CSVs originais do Instacart Market Basket Analysis (Kaggle, `psparks/instacart-market-basket-analysis`). **Não vão ao Git**: cada integrante baixa e coloca aqui (`orders.csv`, `order_products__prior.csv`, `order_products__train.csv`, `products.csv`, `aisles.csv`, `departments.csv`).
- `curados/`: tabelas geradas pelo notebook `notebooks/curadoria_dados_cenario5.ipynb`. Os arquivos grandes (`dados_integrados_train.csv`, `pedidos_resumo_all.csv`) não vão ao Git; recriam-se rodando o notebook.
- `layouts/`: layouts L0, L1 e L2 (seção -> corredor e posição na frente).
- `amostras/`: `Pedidos.csv` (100 pedidos de avaliação), `amostra_validacao_1000.csv` e `calibracao_n_min.csv`.

**Atenção:** `curados/coocorrencia_aisles_prior_train.csv` inclui o conjunto train, onde estão os 100 pedidos de avaliação. Não usar para gerar L1 nem L2.
