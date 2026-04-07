"""AID 医疗报告智能分析系统 - 主入口"""

import argparse
import os
import sys
from pathlib import Path

from dotenv import load_dotenv


def get_executable_dir():
    """获取可执行文件/脚本所在目录"""
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).parent
    else:
        return Path(__file__).parent.parent.parent


def load_environment():
    """从.env文件加载环境变量"""
    # 尝试多个位置的.env文件
    possible_paths = [
        get_executable_dir() / ".env",
        Path.cwd() / ".env",
        Path(__file__).parent.parent.parent / ".env",
    ]
    
    for env_path in possible_paths:
        if env_path.exists():
            load_dotenv(env_path)
            print(f"[成功] 已加载环境变量: {env_path}")
            return
    
    print("[警告] 未找到 .env 文件，使用系统环境变量")
    print(f"[信息] 查找位置: {[str(p) for p in possible_paths]}")


def check_api_keys():
    """检查必需的API密钥"""
    modelscope_key = os.getenv("MODELSCOPE_API_KEY")
    openrouter_key = os.getenv("OPENROUTER_API_KEY")
    
    tavily_key = os.getenv("TAVILY_API_KEY")
    if tavily_key:
        print("[成功] Tavily API 密钥已配置 (搜索功能已启用)")
    else:
        print("[信息] Tavily API 密钥未配置 (搜索功能已禁用)")
    
    if modelscope_key:
        print("[成功] ModelScope API 密钥已配置")
        return "modelscope"
    elif openrouter_key:
        print("[成功] OpenRouter API 密钥已配置")
        return "openrouter"
    else:
        print("[错误] 未找到 API 密钥!")
        print("请在 .env 文件中设置 MODELSCOPE_API_KEY 或 OPENROUTER_API_KEY")
        print("- ModelScope: https://www.modelscope.cn/my/myaccesstoken")
        print("- OpenRouter: https://openrouter.ai/keys")
        return None


def create_components(provider: str):
    """创建LLM客户端、工具和Agent"""
    from src.llm.client import LLMClient
    from src.agent.react_agent import MedicalAnalysisAgent
    from src.tool.datetime_tool import DateTimeTool
    from src.tool.search_tool import SearchTool, HospitalSearchTool
    from src.tool.location_tool import LocationTool, LocationManager
    from src.tool.memory_tool import MemoryTool
    
    if provider == "modelscope":
        llm_client = LLMClient(
            api_key=os.getenv("MODELSCOPE_API_KEY"),
            base_url=os.getenv("MODELSCOPE_BASE_URL", "https://api-inference.modelscope.cn/v1"),
            model=os.getenv("MODELSCOPE_MODEL", "Qwen/Qwen3.5-27B"),
            provider="modelscope",
            temperature=float(os.getenv("LLM_TEMPERATURE", "0.7")),
        )
    else:
        llm_client = LLMClient(
            api_key=os.getenv("OPENROUTER_API_KEY"),
            base_url=os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
            model=os.getenv("OPENROUTER_MODEL", "qwen/qwen-2.5-72b-instruct"),
            provider="openrouter",
            temperature=float(os.getenv("LLM_TEMPERATURE", "0.7")),
        )
    
    print(f"[成功] LLM 客户端已创建 (提供商: {provider}, 模型: {llm_client.model})")
    
    location_tool = LocationTool()
    
    tools = [
        DateTimeTool(),
        location_tool,
    ]
    
    if os.getenv("TAVILY_API_KEY"):
        tools.append(SearchTool())
        tools.append(HospitalSearchTool())
    
    tools.append(MemoryTool())
    
    print(f"[成功] 已创建 {len(tools)} 个工具: {[t.name for t in tools]}")
    
    agent = MedicalAnalysisAgent(
        llm=llm_client,
        tools=tools,
        max_iterations=15,
    )
    print("[成功] 医疗分析 Agent 已创建")
    
    location_manager = LocationManager()
    location_manager.tool = location_tool 
    
    return llm_client, agent, location_manager


def get_streamlit_script_path() -> Path:
    """获取 Streamlit UI 脚本路径。"""
    if getattr(sys, "frozen", False):
        bundle_root = Path(getattr(sys, "_MEIPASS", get_executable_dir()))
        candidates = [
            bundle_root / "aid" / "ui" / "streamlit_app.py",
            get_executable_dir() / "_internal" / "aid" / "ui" / "streamlit_app.py",
            get_executable_dir() / "aid" / "ui" / "streamlit_app.py",
        ]
    else:
        candidates = [
            Path(__file__).parent / "ui" / "streamlit_app.py",
        ]

    for path in candidates:
        if path.exists():
            return path

    raise FileNotFoundError(f"未找到 Streamlit UI 脚本，可尝试路径: {[str(p) for p in candidates]}")


def launch_streamlit(host: str, port: int):
    """启动 Streamlit Web 界面。"""
    from streamlit.web import cli as stcli

    script_path = get_streamlit_script_path()

    os.environ["STREAMLIT_SERVER_ADDRESS"] = host
    os.environ["STREAMLIT_SERVER_PORT"] = str(port)
    os.environ["STREAMLIT_SERVER_HEADLESS"] = "true"
    os.environ["STREAMLIT_BROWSER_GATHER_USAGE_STATS"] = "false"
    os.environ["STREAMLIT_GLOBAL_DEVELOPMENT_MODE"] = "false"

    sys.argv = [
        "streamlit",
        "run",
        str(script_path),
        "--server.address",
        host,
        "--server.port",
        str(port),
        "--server.headless",
        "true",
        "--browser.gatherUsageStats",
        "false",
        "--global.developmentMode",
        "false",
    ]

    stcli.main()


def main():
    """主入口"""
    parser = argparse.ArgumentParser(
        description="AID 医疗报告智能分析系统",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s                          # 启动 Streamlit Web 界面
  %(prog)s --port 8080              # 指定端口
  %(prog)s --host 127.0.0.1         # 仅本机访问
        """
    )
    
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.getenv("GRADIO_SERVER_PORT", "7860")),
        help="Web 服务器端口 (默认: 7860)"
    )
    
    parser.add_argument(
        "--host",
        type=str,
        default="0.0.0.0",
        help="Web 服务器主机 (默认: 0.0.0.0)"
    )

    parser.add_argument(
        "--share",
        action="store_true",
        help="保留兼容参数，Streamlit 模式下忽略"
    )
    
    parser.add_argument(
        "--debug",
        action="store_true",
        help="启用调试模式"
    )
    
    parser.add_argument(
        "--provider",
        type=str,
        choices=["modelscope", "openrouter"],
        default=None,
        help="选择 API 提供商 (默认: 自动检测)"
    )
    
    args = parser.parse_args()
    
    # 打印横幅
    print("""
============================================================
                                                            
           AID 医疗报告智能分析系统                          
                                                            
     AI Medical Report Analysis System                       
                                                            
     支持: 医疗报告分析 | 医院推荐 | 健康咨询                
                                                            
============================================================
    """)
    
    # 加载环境变量
    load_environment()
    
    # 检查API密钥并获取提供商
    provider = args.provider or check_api_keys()
    if not provider:
        sys.exit(1)
    
    if args.share:
        print("[信息] Streamlit 模式暂不支持 --share，已忽略该参数")

    # 启动 Streamlit 应用
    try:
        import streamlit  # noqa: F401

        print("\n[启动] 正在启动 Streamlit Web 界面...")
        print(f"[信息] 访问地址: http://{args.host}:{args.port}")
        print("-" * 60)

        launch_streamlit(args.host, args.port)
    except Exception as e:
        print(f"[错误] 启动 Streamlit 应用失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
