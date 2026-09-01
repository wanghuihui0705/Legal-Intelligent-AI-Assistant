import os
from dotenv import load_dotenv
from langchain_neo4j import Neo4jGraph

# 加载.env文件中的内容
load_dotenv()


# 封装工具
def get_neo4j_conn():
    """使用 LangChain 的 Neo4jGraph 写入节点与关系"""
    # 获取连接对象
    return Neo4jGraph(
        url=os.getenv("NEO4J_URL", "bolt://127.0.0.1:7687"),
        username=os.getenv("NEO4J_USERNAME", "neo4j"),
        password=os.getenv("NEO4J_PASSWORD", "12345678"),
        database=os.getenv("NEO4J_DATABASE", "neo4j"),
    )
