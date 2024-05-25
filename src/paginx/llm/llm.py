from langchain_community.llms import Replicate
import logging

class LLM:
    def __init__(self, provider: str, model_name: str) -> None:
        self.logger = logging.getLogger(__name__)
        self.provider = provider
        self.model_name = model_name
        self.valid_providers = ['Replicate']
        if self.provider not in self.valid_providers:
            self.logger.error(f"Invalid provider: {self.provider}. Valid providers are {self.valid_providers}")
            raise ValueError(f"Invalid provider: {self.provider}. Valid providers are {self.valid_providers}")
        

    def return_llm(self):
        '''
        This function will return the LLM model based on the provider and model_name
        '''
        if self.provider == 'Replicate':
            llm = Replicate(
            model=self.model_name,
            model_kwargs={"temperature": 0},)
            return llm


