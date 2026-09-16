# -*- coding: utf-8 -*-
"""
初始数据唯一来源（db/seed_data）：图谱实体 / 关系 / F9 语料 / 业务库种子。
由 db/build_seed.py 读取并生成 app_db.sql、kg_seed.cypher、data/excel/*.xlsx、data/corpus/paragraphs.csv。
修改初始数据只改本包，然后重新运行 build_seed.py；不要手改生成物。
"""
