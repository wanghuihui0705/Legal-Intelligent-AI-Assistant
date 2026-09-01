# # 1. Python字典 → JSON字符串（后端返回给前端）
# import json
#
# data_dict = {
#     "username": "wyh",
#     "password": "123456",
#     "code": 200
# }
# print(data_dict)
# print(type(data_dict))#<class 'dict'>
# json_str = json.dumps(data_dict, ensure_ascii=False, indent=2)
# print("字典转JSON字符串：\n", json_str,type(json_str))#<class 'str'>
import chromadb

# import os
# # ========== 必须放在最顶部，所有 import 之前 ==========
# os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"
# # 强制离线模式：跳过所有网络检查，直接读取本地缓存
# os.environ["HF_HUB_OFFLINE"] = "1"
# # 关闭符号链接警告
# os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
# from pathlib import Path
# from FlagEmbedding import FlagReranker
#
# # 用 Path 包装路径，避免 Windows 路径识别歧义
# model_path = Path(r"E:\ailearn\stu_nlp\stu_fastapi\models\bge-reranker-base").resolve()
#
# # 先校验路径是否真实存在
# print("路径是否存在:", model_path.exists())
# print("目录内文件:", list(model_path.iterdir()))
#
# # 加载模型
# reranker = FlagReranker(str(model_path), use_fp16=True)
# print("模型加载成功")
#
# # 测试重排序计算
# test_pairs = [["测试问题", "这是一段测试文档内容"]]
# scores = reranker.compute_score(test_pairs)
# print(f"计算成功，分数：{scores}")
# print("版本兼容，无冲突")
#
# # 2. 调用一次分数计算（触发tokenizer核心逻辑，最容易暴露冲突）
# test_pairs = [["测试问题", "这是一段测试文档内容"]]
# scores = reranker.compute_score(test_pairs)
# print(f"计算成功，分数：{scores}")
# print("两个库版本兼容，无冲突")

# import torch
# # 1. 查看绑定的 CUDA 版本
# '''
# 12.6：系统安装的 CUDA Toolkit 版本 = 12.6
# 2.6.0+cu126：当前 PyTorch 版本为 2.6.0，编译绑定 CUDA 12.6
# True：torch.cuda.is_available() 返回 True → GPU 加速可用，显卡正常识别
# '''
# print(torch.version.cuda)
# # 2. 查看完整 torch 版本字符串
# print(torch.__version__)
# # 3. 判断 GPU 是否可用
# print(torch.cuda.is_available())

# from langchain_ollama import ChatOllama
#
# llm=ChatOllama(
#     model="qwen2.5:3b",
#     base_url="http://localhost:11434"
# )
# # for chunk in llm.stream("你好"):
# #     print(chunk)
# prompt="""
# #   任务描述
#     你是法律意图分类器，仅判断用户的问题文本是否属于法律相关内容，只做二分类输出。
#
#     ## 判定规则
#     ### 判定为【相关】的情形
#     1. 询问国家法律、法规、司法解释、判例、司法流程；
#     2. 咨询纠纷处理、维权、起诉、应诉、仲裁、调解、报案、辩护；
#     3. 合同、协议、侵权、债务、婚姻家事、劳动纠纷、刑事犯罪、行政处罚、法律责任、权利义务；
#     4. 询问某行为是否违法、是否犯罪、需要承担什么法律后果；
#     5. 寻求法律层面的解决方案、风险评估。
#
#     ### 判定为【不相关】的情形
#     1. 普通生活科普、情感倾诉、日常闲聊；
#     2. 技术编程、美食旅游、游戏娱乐、学习考试；
#     3. 单纯道德层面吐槽，没有询问法律后果、法律处理方式；
#     4. 仅仅提到“法律”二字，但实际问题和法律事务无关。
#
#     ## 输出硬性约束
#     1. 仅允许输出两个结果之一：`相关` / `不相关`
#     2. 禁止输出理由、分析、补充说明，禁止markdown，禁止多余符号。
#     待分类文本：{{question}}
# """
# # q="你好" # 不相关
# q="公安接到报警之后应该怎么处理"
# rs=llm.invoke([
#     {"role":"system","content":prompt},
#     {"role":"user", "content":q},
# ])
# print(rs.content)



client=chromadb.HttpClient(
    host='192.168.2.40', # 老师的
    port=9000
)
print(client) # <chromadb.api.client.Client object at 0x000001879288C6E0>