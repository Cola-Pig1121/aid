"""医疗报告解析工具"""

import io

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field
from PIL import Image


class ReportParserInput(BaseModel):
    """报告解析工具输入参数"""
    image_data: str = Field(description="Base64编码的图片数据或文件路径")


class MedicalReportParser:
    """医疗报告解析器"""
    
    def __init__(self):
        self.supported_formats = ['.jpg', '.jpeg', '.png', '.bmp', '.tiff']
    
    def extract_text_from_image(self, image: Image.Image) -> str:
        """使用OCR从图片中提取文字"""
        try:
            import pytesseract
            
            # 配置支持中文和英文
            custom_config = r'--oem 3 --psm 6 -l chi_sim+eng'
            text = pytesseract.image_to_string(image, config=custom_config)
            return text.strip()
        except ImportError:
            return "错误: 未安装pytesseract。请安装pytesseract和Tesseract OCR。"
        except Exception as e:
            return f"提取文字时出错: {str(e)}"
    
    def analyze_medical_report(self, text: str) -> dict:
        """分析医疗报告文字"""
        # 常见医学指标关键词
        indicators = {
            "blood_pressure": ["血压", "blood pressure", "mmHg"],
            "blood_sugar": ["血糖", "blood sugar", "glucose", "mmol/L"],
            "cholesterol": ["胆固醇", "cholesterol", "mmol/L"],
            "liver_function": ["肝功能", "liver", "ALT", "AST", "GPT", "GOT"],
            "kidney_function": ["肾功能", "kidney", "creatinine", "肌酐", "urea", "尿素"],
            "blood_routine": ["血常规", "blood routine", "WBC", "RBC", "HGB", "PLT"],
        }
        
        found_indicators = {}
        text_lower = text.lower()
        
        for category, keywords in indicators.items():
            for keyword in keywords:
                if keyword.lower() in text_lower:
                    found_indicators[category] = True
                    break
        
        return {
            "extracted_text": text,
            "detected_indicators": list(found_indicators.keys()),
            "text_length": len(text),
        }


class ReportParserTool(BaseTool):
    """解析和分析医疗报告的工具"""
    
    name: str = "parse_medical_report"
    description: str = """解析和分析医疗报告图片。在以下情况使用此工具：
    - 用户上传医疗报告图片
    - 需要从医疗文档中提取文字
    - 分析体检报告
    - 从图片中提取健康指标
    """
    args_schema: type[BaseModel] = ReportParserInput
    
    def __init__(self):
        super().__init__()
        self.parser = MedicalReportParser()
    
    def _run(self, image_data: str) -> str:
        """从图片解析医疗报告"""
        try:
            import base64
            
            # 尝试作为base64解码
            try:
                image_bytes = base64.b64decode(image_data)
                image = Image.open(io.BytesIO(image_bytes))
            except Exception:
                # 尝试作为文件路径
                image = Image.open(image_data)
            
            # 提取文字
            text = self.parser.extract_text_from_image(image)
            
            if text.startswith("错误:"):
                return text
            
            # 分析
            analysis = self.parser.analyze_medical_report(text)
            
            # 格式化结果
            result = f"""医疗报告分析：

提取的文字：
{text[:1000]}{'...' if len(text) > 1000 else ''}

检测到的健康指标：
{', '.join(analysis['detected_indicators']) if analysis['detected_indicators'] else '未检测到特定指标'}

请分析这些结果并提供医学见解。"""
            
            return result
            
        except Exception as e:
            return f"解析报告时出错: {str(e)}"
    
    async def _arun(self, image_data: str) -> str:
        """异步解析报告"""
        return self._run(image_data)
