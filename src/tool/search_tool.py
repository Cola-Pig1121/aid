"""搜索工具 - 使用Tavily进行网络搜索，支持位置感知"""

import os
import re
from typing import Optional

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field


class SearchInput(BaseModel):
    """搜索工具输入参数"""
    query: str = Field(description="搜索查询关键词")
    location: Optional[str] = Field(default=None, description="可选的位置上下文，用于本地搜索")


class SearchTool(BaseTool):
    """使用Tavily进行网络搜索的工具，支持位置感知"""

    name: str = "tavily_search"
    description: str = """搜索互联网获取权威、准确的医疗健康信息。这是最重要的工具之一。

================================================================================
必须使用此工具的场景（以下场景必须搜索，不能凭记忆回答）
================================================================================

一、症状与疾病相关：
- 用户描述症状询问可能原因 - 搜索"XX症状可能是什么病"
- 用户询问某种疾病的症状表现 - 搜索"XX疾病的症状"
- 用户询问疾病的病因、发病机制 - 搜索"XX病是怎么引起的"
- 用户询问疾病的严重程度、并发症 - 搜索"XX病严重吗 并发症"

二、治疗与用药相关：
- 用户询问治疗方法 - 搜索"XX病怎么治疗 治疗方案"
- 用户询问药物信息 - 搜索"XX药的作用 副作用 用法"
- 用户询问用药注意事项 - 搜索"XX药注意事项 禁忌"
- 用户询问治疗效果、疗程 - 搜索"XX治疗需要多久 效果"

三、检查指标相关：
- 用户询问检查指标的含义 - 搜索"XX指标是什么意思"
- 用户询问指标异常的原因 - 搜索"XX偏高/偏低的原因"
- 用户询问指标正常范围 - 搜索"XX正常值范围"
- 用户询问指标异常怎么办 - 搜索"XX偏高/偏低怎么办"

四、医院与科室相关：
- 用户询问医院推荐 - 搜索"XX地最好的XX科医院排名"
- 用户询问科室选择 - 搜索"XX症状挂什么科"
- 用户询问医院特色 - 搜索"XX医院特色科室"
- 用户询问附近医院 - 结合位置搜索"XX附近医院"

五、预防与保健相关：
- 用户询问疾病预防方法 - 搜索"如何预防XX病"
- 用户询问日常保健建议 - 搜索"XX人群保健建议"
- 用户询问饮食禁忌 - 搜索"XX病不能吃什么"
- 用户询问运动建议 - 搜索"XX病可以运动吗"

六、其他医学问题：
- 任何涉及专业医学知识的问题
- 任何需要最新、准确信息的问题
- 任何用户表示担忧或不确定的问题

================================================================================
使用方法
================================================================================

参数说明：
- query: 搜索关键词，要具体明确
  - 好: "高血压的症状和治疗注意事项"
  - 好: "窦性心动过缓是什么意思需要治疗吗"
  - 好: "北京最好的心内科医院排名推荐"
  - 差: "高血压"（太笼统）

- location: 用户所在城市（可选）
  - 用于医院推荐时提供本地化结果
  - 格式: "北京"、"上海浦东"等

================================================================================
重要原则
================================================================================

警告：绝对禁止凭记忆回答医学问题！
警告：所有医学信息必须通过搜索验证！
警告：搜索结果要引用来源，有理有据！
警告：不确定的问题一定要搜索确认！

回答格式建议：
1. 先说明搜索到的权威信息
2. 引用具体来源
3. 给出专业建议
4. 必要时建议就医
    """
    args_schema: type[BaseModel] = SearchInput

    def __init__(self, api_key: Optional[str] = None, max_results: int = 5):
        super().__init__()
        self._api_key = api_key or os.getenv("TAVILY_API_KEY")
        self._max_results = max_results

    def _build_search_query(self, query: str, location: Optional[str] = None) -> str:
        """构建带位置上下文的搜索查询

        如果提供了详细位置信息（如"福建省泉州市丰泽区新华北路"），
        会提取城市级别信息用于搜索，确保搜索结果更精准。
        """
        if location and location != "Unknown":
            # 提取城市级别信息用于搜索
            # 例如: "福建省泉州市丰泽区新华北路" -> "泉州市"
            city_match = re.search(r'(?:省)?([^省市区县]+[市])', location)
            if city_match:
                city = city_match.group(1)
            else:
                # 如果无法提取城市，使用原始位置
                city = location

            medical_keywords = ["医院", "hospital", "诊所", "clinic", "医生", "doctor", "科室", "department", "附近", "nearby"]
            if any(keyword in query for keyword in medical_keywords):
                return f"{city} {query}"
        return query

    def _run(self, query: str, location: Optional[str] = None) -> str:
        """使用Tavily进行搜索"""
        try:
            from tavily import TavilyClient

            if not self._api_key:
                return "错误: 未找到Tavily API密钥。请设置TAVILY_API_KEY环境变量。"

            search_query = self._build_search_query(query, location)

            client = TavilyClient(api_key=self._api_key)
            response = client.search(
                query=search_query,
                max_results=self._max_results,
                search_depth="basic",
                include_answer=True,
            )

            results = response.get("results", [])
            answer = response.get("answer", "")

            if not results and not answer:
                return f"未找到'{search_query}'的搜索结果。"

            formatted_results = []

            if answer:
                formatted_results.append(f"搜索结果摘要:\n{answer}\n")

            if results:
                formatted_results.append("详细信息:")
                for i, result in enumerate(results, 1):
                    title = result.get("title", "无标题")
                    content = result.get("content", "无内容")
                    url = result.get("url", "")
                    score = result.get("score", 0)

                    relevance = "[高相关]" if score > 0.8 else ""
                    formatted_results.append(f"\n{i}. {title} {relevance}")
                    formatted_results.append(f"   {content[:200]}{'...' if len(content) > 200 else ''}")
                    if url:
                        formatted_results.append(f"   链接: {url}")

            return "\n".join(formatted_results)

        except ImportError:
            return "错误: 未安装tavily-python包。"
        except Exception as e:
            return f"搜索时出错: {str(e)}"

    async def _arun(self, query: str, location: Optional[str] = None) -> str:
        """异步搜索"""
        return self._run(query, location)


class HospitalSearchTool(BaseTool):
    """专门用于搜索医院的工具"""

    name: str = "search_hospitals"
    description: str = """搜索医院和医疗机构信息。

================================================================================
使用场景
================================================================================

当用户需要以下信息时使用：
- 医院推荐 - "推荐好的XX科医院"
- 医院排名 - "XX科医院排名"
- 医院信息 - "XX医院怎么样"
- 科室信息 - "XX医院哪个科好"
- 附近医院 - "附近有什么医院"

================================================================================
使用方法
================================================================================

- query: 搜索关键词
  - "心内科医院排名"
  - "肿瘤医院推荐"
  - "三甲医院"

- location: 用户所在城市（重要！）
  - 用于获取本地化推荐
  - 格式: "北京"、"上海"等

注意：
此工具会自动调用tavily_search进行搜索
推荐医院前应先获取用户位置
    """
    args_schema: type[BaseModel] = SearchInput

    def __init__(self, api_key: Optional[str] = None):
        super().__init__()
        self._search_tool = SearchTool(api_key=api_key, max_results=5)

    def _run(self, query: str, location: Optional[str] = None) -> str:
        """搜索医院"""
        hospital_query = f"{query} 医院排名 推荐"
        return self._search_tool._run(hospital_query, location)

    async def _arun(self, query: str, location: Optional[str] = None) -> str:
        """异步搜索"""
        return self._run(query, location)


def format_hospital_recommendations(search_results: str, department: str = "") -> str:
    """将搜索结果格式化为医院推荐"""
    if not search_results or "错误" in search_results:
        return "无法获取医院推荐信息。请手动搜索当地医院。"

    header = "医院推荐"
    if department:
        header += f" - {department}"

    return f"""{header}

{search_results}

建议：
1. 提前预约挂号
2. 携带相关检查报告
3. 咨询医生前准备好病史资料
"""
