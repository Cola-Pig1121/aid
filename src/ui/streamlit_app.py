"""Streamlit UI for AID Medical Assistant."""

from __future__ import annotations

import asyncio
import base64
import re
from typing import Any

import streamlit as st
from streamlit.elements.widgets.chat import ChatInputValue

from src.main import check_api_keys, create_components, load_environment

DEMO_PRESETS = [
    {
        "label": "体检报告解读",
        "prompt": "请用通俗中文解释体检报告里常见的血压、血糖、胆固醇异常分别意味着什么。",
    },
    {
        "label": "症状问答",
        "prompt": "窦性心动过缓是什么意思，需要注意什么，什么情况下应该去医院？",
    },
    {
        "label": "医院推荐",
        "prompt": "我最近胸闷心慌，请推荐附近适合就诊的医院和科室。",
    },
]


def run_async(coro: Any) -> Any:
    """Run async code safely inside Streamlit's sync execution model."""
    loop = asyncio.new_event_loop()
    try:
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(coro)
    finally:
        asyncio.set_event_loop(None)
        loop.close()


@st.cache_resource
def get_runtime(provider_override: str | None = None):
    """Initialize runtime dependencies once per session."""
    load_environment()
    provider = provider_override or check_api_keys()
    if not provider:
        raise RuntimeError("未检测到可用的大模型 API 密钥。")
    return create_components(provider)


def get_chat_history() -> list[dict[str, str]]:
    return st.session_state.setdefault("messages", [])


def get_report_context() -> dict[str, str] | None:
    return st.session_state.get("report_context")


def set_report_context(context: dict[str, str]) -> None:
    st.session_state["report_context"] = context


def clear_report_context() -> None:
    st.session_state.pop("report_context", None)


def append_message(role: str, content: str) -> None:
    get_chat_history().append({"role": role, "content": content})


def render_chat_history() -> None:
    for message in get_chat_history():
        with st.chat_message(message["role"]):
            st.markdown(message["content"])


def normalize_chat_submission(submission: str | ChatInputValue | None) -> tuple[str, list[Any]]:
    if submission is None:
        return "", []

    if isinstance(submission, str):
        return submission.strip(), []

    return (submission.text or "").strip(), list(submission.files or [])


def render_user_submission(prompt: str, uploaded_files: list[Any]) -> None:
    lines: list[str] = []
    if prompt:
        lines.append(prompt)
    if uploaded_files:
        file_names = "、".join(file.name for file in uploaded_files)
        lines.append(f"[已上传报告图片：{file_names}]")

    content = "\n\n".join(lines) if lines else "[用户发送了空消息]"
    append_message("user", content)

    with st.chat_message("user"):
        st.markdown(content)
        for file in uploaded_files:
            st.image(file.getvalue(), caption=file.name, width="stretch")


def build_followup_query(prompt: str) -> str:
    """Inject the last analyzed report as hidden context for follow-up questions."""
    context = get_report_context()
    if not context:
        return prompt

    return (
        "当前对话已经分析过一份医疗报告，请把下面信息视为本轮问答的背景，不要重复要求用户重新上传报告。\n\n"
        f"上次报告的核心结论：\n{context['analysis']}\n\n"
        f"建议关注科室：{context['departments']}\n"
        f"位置背景：{context['location']}\n\n"
        f"用户当前追问：{prompt}\n\n"
        "请基于已分析报告继续回答，优先做追问解释、补充建议、风险说明或进一步就医指导。"
    )


def chat_once(agent: Any, query: str) -> str:
    history = get_chat_history()
    effective_query = build_followup_query(query)
    return run_async(agent.run(query=effective_query, chat_history=history[:-1]))


def run_text_prompt(agent: Any, prompt: str) -> None:
    append_message("user", prompt)
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("分析中，请稍候..."):
            response = chat_once(agent, prompt)
            st.markdown(response)

    append_message("assistant", response)


def get_tool(agent: Any, tool_name: str) -> Any:
    tool = getattr(agent, "tools_dict", {}).get(tool_name)
    if tool is None:
        raise RuntimeError(f"未找到工具: {tool_name}")
    return tool


def get_current_location_text(agent: Any) -> str:
    """Call the location tool directly instead of routing through the agent."""
    location_tool = get_tool(agent, "get_current_location")
    try:
        return str(location_tool._run())
    except Exception as exc:
        return f"无法获取位置：{exc}"


def get_location_context(agent: Any) -> tuple[dict[str, Any], str]:
    """Return structured location data plus a clean search locale."""
    location_tool = get_tool(agent, "get_current_location")
    try:
        location_data = location_tool.get_location_dict()
    except Exception:
        return {}, ""

    city = str(location_data.get("city", "") or "").strip()
    district = str(location_data.get("district", "") or "").strip()
    region = str(location_data.get("region", "") or "").strip()
    country = str(location_data.get("country", "") or "").strip()

    parts: list[str] = []
    for value in [district, city, region, country]:
        if value and value != "Unknown" and value not in parts:
            parts.append(value)

    return location_data, ", ".join(parts)


def infer_relevant_departments(analysis_text: str, user_prompt: str) -> str:
    text = f"{user_prompt}\n{analysis_text}"
    rules = [
        ("妇科", ["妇科", "宫颈", "阴道", "外阴", "白带", "月经", "子宫", "卵巢", "hpv", "tct"]),
        ("心内科", ["心电", "心率", "心动过缓", "心慌", "胸闷", "血压", "高血压", "心脏"]),
        ("内分泌科", ["血糖", "糖尿病", "甲状腺", "激素", "胆固醇", "甘油三酯", "尿酸"]),
        ("消化内科", ["肝", "胆", "胃", "腹痛", "转氨酶", "脂肪肝"]),
        ("肾内科", ["肾", "肌酐", "尿蛋白", "尿检", "肾功能"]),
        ("呼吸内科", ["肺", "咳嗽", "胸片", "呼吸", "支气管"]),
    ]

    lowered = text.lower()
    matched = [department for department, keywords in rules if any(keyword in lowered for keyword in keywords)]
    if matched:
        return "、".join(matched[:2])
    return "内科"


def search_hospitals_direct(agent: Any, query: str, location: str | None = None) -> str:
    """Call the hospital search tool directly and keep raw output internal."""
    hospital_tool = get_tool(agent, "search_hospitals")
    try:
        if location:
            return str(hospital_tool._run(query=query, location=location))
        return str(hospital_tool._run(query=query))
    except Exception as exc:
        return f"医院搜索失败：{exc}"


def summarize_hospital_results(search_results: str, departments: str) -> str:
    """Convert raw tool output into a concise user-facing section."""
    if not search_results or "医院搜索失败" in search_results or "错误" in search_results:
        return (
            f"医院推荐：建议优先关注 {departments} 相关门诊。\n\n"
            "暂时未能稳定获取在线医院列表，请直接查看当地正规医院官网或挂号平台，"
            "并以官方科室和出诊信息为准。"
        )

    recommendations: list[tuple[str, str]] = []
    current_title = ""

    for raw_line in search_results.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        title_match = re.match(r"^\d+\.\s+(.*?)(?:\s+\[.*\])?$", line)
        if title_match:
            current_title = title_match.group(1).strip()
            continue

        url_match = re.search(r"https?://\S+", line)
        if url_match:
            url = url_match.group(0).strip()
            if current_title and url:
                recommendations.append((current_title, url))
                current_title = ""

        if len(recommendations) >= 3:
            break

    lines = [f"医院推荐：建议优先关注 {departments} 相关门诊。", ""]
    if recommendations:
        lines.append("可优先核实以下医院或挂号入口：")
        for index, (title, url) in enumerate(recommendations, 1):
            lines.append(f"{index}. {title}")
            lines.append(f"   {url}")
    else:
        lines.append("已完成联网搜索，但未能从结果中稳定提取到医院清单。建议直接查看当地三甲医院官网或正规挂号平台。")

    lines.extend(
        [
            "",
            "就医前建议：",
            "1. 携带原始报告、既往病史和用药信息。",
            "2. 以医院官网或正规挂号平台的科室与出诊安排为准。",
            "3. 如症状明显加重或出现急症，请直接前往急诊。",
        ]
    )
    return "\n".join(lines)


def build_hospital_query(departments: str, location_data: dict[str, Any]) -> str:
    """Build a locale-aware hospital search query."""
    country = str(location_data.get("country", "") or "").lower()
    english_department_map = {
        "妇科": "gynecology",
        "心内科": "cardiology",
        "内分泌科": "endocrinology",
        "消化内科": "gastroenterology",
        "肾内科": "nephrology",
        "呼吸内科": "pulmonology",
        "内科": "internal medicine",
    }

    if country and "china" not in country and "中国" not in country:
        english_departments = [english_department_map.get(item, "internal medicine") for item in departments.split("、")]
        joined = " and ".join(english_departments[:2])
        return f"best {joined} hospitals"

    return f"{departments} 医院推荐"


def analyze_uploaded_image(llm_client: Any, agent: Any, image_bytes: bytes, user_prompt: str = "") -> str:
    image_base64 = base64.b64encode(image_bytes).decode("utf-8")
    user_need = user_prompt.strip() or "用户未补充文字说明。"
    location_response = get_current_location_text(agent)
    location_data, search_location = get_location_context(agent)

    multimodal_message = {
        "role": "user",
        "content": [
            {
                "type": "text",
                "text": (
                    "这是用户上传的一份医疗报告或检查报告图片。\n"
                    f"用户补充说明：{user_need}\n\n"
                    "请先判断用户想解决的问题，再结合报告内容分析用户的身体状况和需求，并给出回应。\n\n"
                    "请按以下要求输出：\n"
                    "1. 提取并分析报告中的关键医学指标\n"
                    "2. 识别异常值并解释其含义\n"
                    "3. 结合用户补充说明，判断用户当前的主要需求\n"
                    "4. 总结当前身体状况与需要关注的风险点\n"
                    "5. 给出饮食、作息、复查或就医建议\n"
                    "6. 如有必要，列出建议就诊的科室\n\n"
                    "请使用中文详细回复，并明确说明建议仅供参考，不能替代医生诊断。"
                ),
            },
            {
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"},
            },
        ],
    }

    analysis_text = run_async(llm_client.complete([multimodal_message]))
    departments = infer_relevant_departments(analysis_text, user_prompt)
    hospital_query = build_hospital_query(departments, location_data)
    hospital_raw_results = search_hospitals_direct(agent, query=hospital_query, location=search_location or None)
    hospital_summary = summarize_hospital_results(hospital_raw_results, departments)

    set_report_context(
        {
            "analysis": analysis_text,
            "departments": departments,
            "location": location_response,
        }
    )

    return (
        f"位置：{location_response}\n\n"
        f"报告分析：\n{analysis_text}\n\n"
        f"{hospital_summary}"
    )


def render_sidebar(llm_client: Any) -> None:
    st.sidebar.title("AID 控制台")
    st.sidebar.caption("医疗报告分析 / 健康问答 / 医院推荐")

    available_models = [
        "Qwen/Qwen3.5-27B",
        "Qwen/Qwen2.5-72B-Instruct",
        "qwen/qwen-2.5-72b-instruct",
    ]

    default_model = llm_client.model if llm_client.model in available_models else available_models[0]
    selected_model = st.sidebar.selectbox("模型", available_models, index=available_models.index(default_model))
    llm_client.model = selected_model

    temperature = st.sidebar.slider("Temperature", 0.0, 1.0, float(llm_client.temperature), 0.1)
    llm_client.temperature = temperature

    if st.sidebar.button("清空对话", width="stretch"):
        st.session_state["messages"] = []
        clear_report_context()
        st.rerun()

    context = get_report_context()
    if context:
        st.sidebar.markdown("---")
        st.sidebar.markdown("### 当前报告上下文")
        st.sidebar.caption(f"已保存报告上下文，后续追问会自动延续。建议科室：{context['departments']}")
        if st.sidebar.button("清除报告上下文", width="stretch"):
            clear_report_context()
            st.rerun()

    st.sidebar.markdown("---")
    st.sidebar.markdown(
        "\n".join(
            [
                "### 使用提示",
                "- 在底部输入框输入健康问题进行咨询",
                "- 点击输入框左侧的 `+` 号可上传报告图片",
                "- 可以同时输入文字说明和上传图片一起发送",
                "- 上传报告后，后续追问会自动带上该报告的分析背景",
            ]
        )
    )

    st.sidebar.markdown("---")
    st.sidebar.markdown("### 演示模式")
    st.sidebar.caption("点击即可自动填充并发送一条适合现场展示的问题。")
    for preset in DEMO_PRESETS:
        if st.sidebar.button(preset["label"], key=f"demo_{preset['label']}", width="stretch"):
            st.session_state["demo_prompt"] = preset["prompt"]


def main() -> None:
    st.set_page_config(
        page_title="AID 医疗报告智能分析系统",
        page_icon="🩺",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    provider_override = st.query_params.get("provider")
    llm_client, agent, _location_manager = get_runtime(provider_override)

    st.title("AID 医疗报告智能分析系统")
    st.caption("上传医疗报告图片或输入健康问题，系统将提供分析、建议和医院推荐。")

    render_sidebar(llm_client)

    left_col, right_col = st.columns([3, 1], gap="large")

    with left_col:
        render_chat_history()

        if st.session_state.get("demo_prompt"):
            prompt = st.session_state.pop("demo_prompt")
            run_text_prompt(agent, prompt)
            st.rerun()

        submission = st.chat_input(
            "请输入您的健康问题，例如：这份报告还需要复查什么？",
            accept_file=True,
            file_type=["jpg", "jpeg", "png", "bmp", "tiff"],
            width="stretch",
        )
        prompt, uploaded_files = normalize_chat_submission(submission)

        if prompt or uploaded_files:
            render_user_submission(prompt, uploaded_files)

            if uploaded_files:
                first_file = uploaded_files[0]
                with st.chat_message("assistant"):
                    with st.spinner("正在分析用户上传的报告并整理就医建议..."):
                        response = analyze_uploaded_image(llm_client, agent, first_file.getvalue(), prompt)
                        st.markdown(response)
                append_message("assistant", response)
            else:
                with st.chat_message("assistant"):
                    with st.spinner("分析中，请稍候..."):
                        response = chat_once(agent, prompt)
                        st.markdown(response)
                append_message("assistant", response)

            st.rerun()

    with right_col:
        st.subheader("发送方式")
        st.markdown(
            "\n".join(
                [
                    "1. 在底部输入框输入问题",
                    "2. 点击左侧 `+` 号选择报告图片",
                    "3. 可同时输入文字说明与上传图片",
                    "4. 上传报告后可继续多轮追问，不需要重复上传",
                ]
            )
        )
        st.markdown("---")
        st.markdown(
            "\n".join(
                [
                    "### 演示模式预置问题",
                    "- 体检报告解读：请用通俗中文解释体检报告里常见的血压、血糖、胆固醇异常分别意味着什么。",
                    "- 症状问答：窦性心动过缓是什么意思，需要注意什么，什么情况下应该去医院？",
                    "- 医院推荐：我最近胸闷心慌，请推荐附近适合就诊的医院和科室。",
                ]
            )
        )


if __name__ == "__main__":
    main()
