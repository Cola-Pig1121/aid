"""ReAct Agent实现，支持医疗分析"""

import re
from typing import Any, List, Optional

from langchain_core.tools import BaseTool

from src.agent.base import AgentAction, AgentFinish, BaseAgent

MEDICAL_SYSTEM_PROMPT = """你是一位专业的医疗AI助手，可以帮助用户分析医疗报告、解答健康问题、推荐医院和科室。

## 可用工具

{tools}

工具名称: {tool_names}

## 工具使用指南

### 1. 位置获取 (get_current_location)
- **何时使用**: 需要推荐医院、搜索本地服务、用户提到"附近"、"本地"时
- **重要**: 推荐医院前必须先获取用户位置！

### 2. 网络搜索 (tavily_search)
- **何时使用**: 
  - 用户询问症状、疾病信息时
  - 需要查询医院排名、科室信息时
  - 需要获取最新医学知识时
  - 用户问"为什么"、"怎么办"等需要专业知识的问题时
- **重要**: 不要凭记忆回答医学问题，必须搜索获取准确信息！

### 3. 医院搜索 (search_hospitals)
- **何时使用**: 用户明确要求医院推荐时
- **使用方法**: 先获取位置，再搜索医院

### 4. 医疗报告解析 (parse_medical_report)
- **何时使用**: 用户上传医疗报告图片时

### 5. 时间查询 (get_current_datetime)
- **何时使用**: 需要知道当前时间时

### 6. 记忆管理 (memory_manager)
- **何时使用**: 保存或检索重要信息时

## 回答格式

使用以下格式：

Question: 用户的问题
Thought: 思考如何回答问题，考虑需要使用哪些工具
Action: 要采取的行动，必须是以下工具之一 [{tool_names}]
Action Input: 工具的输入

**重要：你只需要生成到 Action Input，不要生成 Observation！Observation 由系统自动提供。**

Thought: 我现在知道最终答案
Final Answer: 对原始问题的最终回答

## 重要规则（必须遵守）

1. **医院推荐流程**:
   - 第一步： 调用 get_current_location 获取用户位置
   - 第二步： 调用 tavily_search 或 search_hospitals 搜索医院
   - 第三步: 基于搜索结果提供推荐

2. **医学问题回答**:
   - 不要凭记忆回答医学问题
   - 必须使用 tavily_search 搜索获取准确信息
   - 提供专业、可靠的医学建议

3. **提供专业的医学解释**
4. **必要时建议就医并推荐当地医院**
5. **明确说明建议仅供参考，不能替代专业医生的诊断**

对话历史:
{chat_history}

现在开始!

Question: {question}
thought:"""


class ReActOutputParser:
    """解析ReAct Agent输出"""
    
    def parse(self, text: str) -> AgentAction | AgentFinish:
        """解析Agent输出"""
        if "Final Answer:" in text:
            final_answer = text.split("Final Answer:")[-1].strip()
            return AgentFinish(return_values={"output": final_answer}, log=text)
        
        text_before_obs = text.split("Observation:")[0] if "Observation:" in text else text
        
        action_match = re.search(r"Action:\s*(\w+)", text_before_obs)
        action_input_match = re.search(r"Action Input:\s*(.+?)(?=\n|$)", text_before_obs, re.DOTALL)
        
        if action_match:
            tool = action_match.group(1).strip()
            tool_input = action_input_match.group(1).strip() if action_input_match else ""
            return AgentAction(tool=tool, tool_input=tool_input, log=text)
        
        return AgentFinish(return_values={"output": text.strip()}, log=text)


class ReActAgent(BaseAgent):
    """具备推理和行动能力的ReAct Agent"""
    
    def __init__(
        self,
        llm: Any,
        tools: List[BaseTool],
        system_prompt: Optional[str] = None,
        max_iterations: int = 10,
        verbose: bool = True,
    ):
        super().__init__(llm, tools, system_prompt)
        self.max_iterations = max_iterations
        self.parser = ReActOutputParser()
        self.location: Optional[str] = None
        self.verbose = verbose
        self.tool_logs: List[dict] = []
    
    def _format_tools(self) -> str:
        """格式化工具用于提示词"""
        tool_descriptions = []
        for tool in self.tools:
            tool_descriptions.append(f"{tool.name}: {tool.description}")
        return "\n".join(tool_descriptions)
    
    def _format_tool_names(self) -> str:
        """格式化工具名称用于提示词"""
        return ", ".join([tool.name for tool in self.tools])
    
    def _build_prompt(self, question: str, scratchpad: str = "", chat_history: str = "") -> str:
        """构建提示词"""
        prompt_template = self.system_prompt or MEDICAL_SYSTEM_PROMPT
        prompt = prompt_template.format(
            tools=self._format_tools(),
            tool_names=self._format_tool_names(),
            question=question,
            chat_history=chat_history
        )
        if scratchpad:
            prompt += scratchpad
        return prompt
    
    def _log_tool_call(self, tool_name: str, tool_input: str, tool_output: str):
        """在终端记录工具调用"""
        log_entry = {
            "tool": tool_name,
            "input": tool_input,
            "output": tool_output[:500] + "..." if len(tool_output) > 500 else tool_output
        }
        self.tool_logs.append(log_entry)
        
        if self.verbose:
            print("\n" + "="*60)
            print(f"[工具调用] {tool_name}")
            print("-"*60)
            print(f"输入: {tool_input}")
            print("-"*60)
            print(f"输出: {log_entry['output']}")
            print("="*60 + "\n")
    
    async def run(self, query: str, chat_history: list[dict[str, str]] = None) -> str:
        """运行ReAct Agent"""
        scratchpad = ""
        self.tool_logs = []
        
        history_str = ""
        if chat_history:
            for msg in chat_history:
                role = msg.get("role", "")
                content = msg.get("content", "")
                if role == "user":
                    history_str += f"用户: {content}\n"
                elif role == "assistant":
                    history_str += f"助手: {content}\n"
        
        if self.verbose:
            print("\n" + ">"*60)
            print(f"[Agent 输入] {query}")
            print(f"[历史对话数] {len(chat_history) if chat_history else 0}")
            print(">"*60 + "\n")
        
        for iteration in range(self.max_iterations):
            prompt = self._build_prompt(
                query, 
                scratchpad, 
                chat_history=history_str,
            )
            messages = [{"role": "user", "content": prompt}]
            response = ""
            async for chunk in self.llm.chat(messages, stream=False):
                response += chunk
            
            if self.verbose:
                print(f"[Agent 思考] 第 {iteration + 1} 轮")
                print(f"{response}\n")
        
            parsed = self.parser.parse(response)
            
            if isinstance(parsed, AgentFinish):
                final_answer = parsed.return_values.get("output", "")
                if self.verbose:
                    print("<"*60)
                    print(f"[Agent 输出] {final_answer[:500]}...")
                    print("<"*60 + "\n")
                return final_answer
            
            tool_result = await self._call_tool(parsed.tool, parsed.tool_input)
            
            self._log_tool_call(parsed.tool, parsed.tool_input, tool_result)
            if parsed.tool == "get_current_location" and "location" in tool_result.lower():
                match = re.search(r"Location:\s*([^\n]+)", tool_result)
                if match:
                    self.location = match.group(1).strip()
                    if self.verbose:
                        print(f"[位置已更新] {self.location}")
                else:
                    match = re.search(r"City:\s*([^\n]+)", tool_result)
                    if match:
                        self.location = match.group(1).strip()
                        if self.verbose:
                            print(f"[位置已更新] {self.location}")
            scratchpad += f" {response}\nObservation: {tool_result}\nThought:"
        
        final_answer = "达到最大迭代次数。已找到的信息: " + scratchpad
        if self.verbose:
            print("<"*60)
            print(f"[Agent 输出] {final_answer[:500]}...")
            print("<"*60 + "\n")
        return final_answer


class MedicalAnalysisAgent(ReActAgent):
    """专用于医疗报告分析的Agent"""
    
    def __init__(self, llm: Any, tools: List[BaseTool], max_iterations: int = 15, verbose: bool = True):
        super().__init__(
            llm=llm,
            tools=tools,
            system_prompt=MEDICAL_SYSTEM_PROMPT,
            max_iterations=max_iterations,
            verbose=verbose
        )
    
    async def analyze_medical_report(self, report_text: str) -> str:
        """分析医疗报告并提供建议，使用工具完成"""
        query = f"""请分析以下医疗报告：

{report_text}

你必须使用工具来完成以下步骤：
1. 首先调用 get_current_location 获取用户当前位置
2. 然后使用 tavily_search 搜索相关医学信息来解释异常指标
3. 根据位置和异常指标，使用 search_hospitals 搜索当地合适的医院
4. 提供具体的医院推荐和就医建议

重要：不要自己编造位置信息或医院信息，必须使用工具获取真实数据！

请用中文详细回复。"""
        
        return await self.run(query)
