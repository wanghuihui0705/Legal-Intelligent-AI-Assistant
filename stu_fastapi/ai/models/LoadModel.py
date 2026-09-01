'''
专门放与大模型相关的代码11
'''
from langchain_openai import ChatOpenAI
from langchain_ollama import ChatOllama
import os

_stream_llm = None
_no_stream_llm = None
_fast_llm = None

def load_model_stream():
    global _stream_llm
    if _stream_llm is None:
        _stream_llm = ChatOpenAI(
            api_key=os.getenv("DASHSCOPE_API_KEY"),
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
            model="qwen3.7-plus",
            streaming=True,
        )
    return _stream_llm

def load_model_no_stream():
    global _no_stream_llm
    if _no_stream_llm is None:
        _no_stream_llm = ChatOpenAI(
            api_key=os.getenv("DASHSCOPE_API_KEY"),
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
            model="qwen3.7-plus",
            streaming=False,
        )
    return _no_stream_llm

def load_fast_model():
    """高速小模型（本地 Ollama），用于意图识别、查询改写等轻量任务。

    与主大模型（qwen3.7-plus）解耦：意图识别 + 查询改写走小模型，
    主大模型只负责最终答案生成，显著降低整条链路的首字延迟。
    """
    global _fast_llm
    if _fast_llm is None:
        _fast_llm = ChatOllama(
            model=os.getenv("OLLAMA_MODEL_NAME", "qwen2.5:3b"),
            base_url=os.getenv("OLLAMA_HOST", "http://localhost:11434"),
            temperature=0,
        )
    return _fast_llm

if __name__=="__main__":
    # llm=load_model_no_stream()
    # rs=llm.invoke("1加1等于几?")
    # print(rs)
    llm=load_model_stream()
    rs = llm.stream("遇到家暴应该怎么办")
    print(rs) #<generator object BaseChatModel.stream at 0x0000020AE475FA60>
    for chunk in rs:
        print(chunk)