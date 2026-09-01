import os
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"
# 新增：强制离线模式，只读取本地缓存，不发起任何网络请求
os.environ["HF_HUB_OFFLINE"] = "1"
from langchain_core.documents import Document
from langchain_huggingface import HuggingFaceEmbeddings
import pandas as pd
from langchain_chroma import Chroma
#根目录路径
root_path=os.path.dirname(os.path.dirname(__file__))#E:\ailearn\stu_nlp\stu_fastapi
#法律数据集路径
datasets_path=os.path.join(root_path,"datasets","法律数据集.csv")
#向量模型存储路径
embedding_model_path=os.path.join(root_path,"models","embedding")
#向量模型名字
# embedding_model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
#向量存储的集合名字
collection_name='law_knowledge_base'
#向量数据库存储路径
vector_db_path=os.path.join(root_path,"vector_db","law_knowledge_base.db")
'''
项目开始之前先单独运行这个脚本,且不再重复执行,因为知识库只构建一次,不能重复构建
'''
#构建外部向量知识库
def build_law_knowledge_base():
    df=pd.read_csv(datasets_path) #datafram
    # print(data.info())
    # print(data.head())
    data=df.values.tolist() #直接去掉了列明和序号值
    # print(data)# [['《中华人民共和国反家庭暴力法》第二十四条规定..'],[''],...,['']]
    #必须要得到list[Document]才能进行向量化存储，page_content：str
    documents=[Document(page_content=item[0]) for item in data] #列表
    # print(type(documents[0])) #列表元素是Document
    print(f"尝试从本地路径加载向量化模型: {embedding_model_path}")
    # 向量化模型
    embedding_model = HuggingFaceEmbeddings(
        model_name = embedding_model_path,
        model_kwargs = {
            "local_files_only": True,
            "device": "cuda"
        },
    )
    Chroma.from_documents(
        documents=documents,
        embedding=embedding_model,
        collection_name=collection_name,
        persist_directory=vector_db_path,
        collection_metadata={
            #余弦相似度规则
            "hnsw:space":"cosine", #当用检索器检索时,会按照这个规则检索
        }
    )
    print("法律知识库构建完成!")

if __name__=="__main__":
    try:
        build_law_knowledge_base()
    except Exception as e:
        print(f"出错了: {e}")