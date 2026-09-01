from ai.models import LoadModel
from common.LoggerUtil import Logger

logger = Logger.get_logger()
def intention_recognition(q):
    llm = LoadModel.load_fast_model()
    # for chunk in llm.stream("你好"):
    #     print(chunk)
    prompt = """
    #   任务描述
        你是法律意图分类器，仅判断用户的问题文本是否属于法律相关内容，只做二分类输出。

        ## 判定规则
        ### 判定为【相关】的情形
        1. 询问国家法律、法规、司法解释、判例、司法流程；
        2. 咨询纠纷处理、维权、起诉、应诉、仲裁、调解、报案、辩护；
        3. 合同、协议、侵权、债务、婚姻家事、劳动纠纷、刑事犯罪、行政处罚、法律责任、权利义务；
        4. 询问某行为是否违法、是否犯罪、需要承担什么法律后果；
        5. 寻求法律层面的解决方案、风险评估。

        ### 判定为【不相关】的情形
        1. 普通生活科普、情感倾诉、日常闲聊；
        2. 技术编程、美食旅游、游戏娱乐、学习考试；
        3. 单纯道德层面吐槽，没有询问法律后果、法律处理方式；
        4. 仅仅提到“法律”二字，但实际问题和法律事务无关。

        ## 输出硬性约束
        1. 仅允许输出两个结果之一：`true` / `false`
        2. 禁止输出理由、分析、补充说明，禁止markdown，禁止多余符号。
        待分类文本：{{question}}
    """
    # q="你好" # 不相关
    # q = "公安接到报警之后应该怎么处理" # 相关
    rs = llm.invoke([
        {"role": "system", "content": prompt},
        {"role": "user", "content": q},
    ])
    logger.info(f"intentionUtil：用户问题与法律{"相关" if "true" in rs.content else "不相关"}")
    return rs.content
if __name__ == "__main__":
    if(intention_recognition("公安接到报警之后应该怎么处理")=="相关"):
        print(1)
    else:
        print(2)