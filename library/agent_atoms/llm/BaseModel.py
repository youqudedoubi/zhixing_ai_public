import os
from typing import Literal,Optional,Iterable,Dict,Any
from openai import OpenAI

#暂时去除了流式方法
class BaseModel:
    #基础的model配置
    def __init__(
        self,
        model_name:str,
        base_url:str,
        api_key:str,
        # kwargs是额外参数字典
        client_kwargs:Optional[Dict[str,Any]]=None,#客户端参数，如timeout
        default_generate_kwargs: Optional[Dict[str, Any]] = None#生成参数，如temperature
    ):
        ##
        # kwargs可以包含：
        # temperature
        # stream
        # timeout

        self.model_name=model_name
        self.base_url=base_url
        self.api_key=api_key
        self.client_kwargs=client_kwargs or {}
        self.default_generate_kwargs= default_generate_kwargs or {}
        self.client=self._init_client()

    def _init_client(self):
        return OpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
            **self.client_kwargs
        )

    def generate_nonstream(self,messages,**kwargs):
        all_params={
            "model":self.model_name,
            "messages": messages,
            "stream":False,
            **self.default_generate_kwargs,
            **kwargs#会覆盖默认配置
        }
        response=self.client.chat.completions.create(**all_params)
        return response

    def print_nonstream(self,response):
        #注：思考过程为reasoning_content变量，适用于官方deepseek，不知道其它模型是不是这个参数
        if hasattr(response.choices[0].message, 'reasoning_content'):
            print("\n思考过程：")
            print(response.choices[0].message.reasoning_content)
        print("\nAI回复：")
        print(response.choices[0].message.content)

    def generate_stream(self,messages,**kwargs):
        all_params = {
            "model": self.model_name,
            "messages": messages,
            "stream": True,
            **self.default_generate_kwargs,
            **kwargs  # 会覆盖默认配置
        }
        stream = self.client.chat.completions.create(**all_params)
        return stream

    def print_stream(self, stream):
        reasoning_started = False
        answer_started = False
        for chunk in stream:
            delta = chunk.choices[0].delta
            if hasattr(delta, "reasoning_content") and delta.reasoning_content:
                if not reasoning_started:
                    print("\n思考过程：", end="")
                    reasoning_started = True
                print(delta.reasoning_content, end="", flush=True)
            if delta.content:
                if reasoning_started and not answer_started:
                    print("\nAI回复：", end="")
                    answer_started = True
                print(delta.content, end="", flush=True)

if __name__=="__main__":
    from code.config import api_key
    default_generate_kwargs = {
        "stream": True,
        "reasoning_effort": "max",#可填high、max
        "extra_body": {"thinking": {"type": "enabled"}}
    }
    def get_deepseek_v4_pro():
        model = BaseModel(
            model_name="deepseek-v4-pro",
            api_key=api_key,
            base_url="https://api.deepseek.com",
            default_generate_kwargs=default_generate_kwargs
        )
        return model
    model=get_deepseek_v4_pro()
    message=[{"role":"user","content":"你是谁？"}]
    stream=model.generate_stream(message)
    model.print_stream(stream)