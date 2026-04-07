"""位置工具 - 获取用户地理位置"""

import hashlib
import os
import urllib.parse
from typing import Optional, Any

import httpx
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field


class LocationInput(BaseModel):
    """位置工具输入参数"""
    method: str = Field(default="auto", description="定位方式: 'auto', 'ip', 或 'browser'")


class TencentMapAPI:
    """腾讯地图API客户端，支持SN签名验证"""

    def __init__(self, key: str, secret_key: str):
        self.key = key
        self.secret_key = secret_key
        self.base_url = "https://apis.map.qq.com"

    def _generate_signature(self, params: dict[str, str], request_path: str = "/ws/geocoder/v1") -> str:
        """生成腾讯地图API的SN签名

        根据腾讯地图官方文档:
        https://lbs.qq.com/faq/serverFaq/webServiceKey

        GET请求签名算法:
        1. 按参数名排序(a-z)
        2. 使用原始参数值构建查询字符串(不进行URL编码)
        3. 拼接: 请求路径 + "?" + 查询字符串 + SK
        4. 直接计算MD5哈希(不对整个字符串进行URL编码)
        """
        # 按参数名排序(a-z)
        sorted_params = sorted(params.items())

        # 使用原始值构建查询字符串(签名时不进行URL编码)
        query_parts = []
        for k, v in sorted_params:
            query_parts.append(f"{k}={v}")
        query_string = "&".join(query_parts)

        # 构建签名字符串: 请求路径 + "?" + 查询字符串 + SK
        sig_string = f"{request_path}?{query_string}{self.secret_key}"

        md5_hash = hashlib.md5(sig_string.encode('utf-8')).hexdigest()

        return md5_hash

    def get_address(self, lat: float, lon: float) -> Optional[dict[str, Any]]:
        """使用腾讯地图API通过坐标获取地址"""
        try:
            request_path = "/ws/geocoder/v1"

            params = {
                "location": f"{lat},{lon}",
                "key": self.key,
                "get_poi": "1"
            }

            # 生成签名
            sig = self._generate_signature(params, request_path)
            params["sig"] = sig

            # 构建完整URL
            query_string = urllib.parse.urlencode(params)
            url = f"{self.base_url}{request_path}?{query_string}"

            print(f"[位置服务] 请求腾讯地图API: {url}")

            response = httpx.get(url, timeout=10)

            if response.status_code == 200:
                data = response.json()

                if data.get("status") == 0:
                    result = data.get("result", {})
                    address_component = result.get("address_component", {})

                    return {
                        "code": 200,
                        "nation": address_component.get("nation", "中国"),
                        "province": address_component.get("province", ""),
                        "city": address_component.get("city", ""),
                        "county": address_component.get("district", ""),
                        "town": address_component.get("street", ""),
                        "address": result.get("address", ""),
                        "formatted_addresses": result.get("formatted_addresses", {}),
                        "latitude": lat,
                        "longitude": lon,
                    }
                else:
                    print(f"[位置服务] 腾讯地图API返回错误: {data.get('message', '未知错误')} (状态码: {data.get('status')})")
                    return None
            else:
                print(f"[位置服务] 腾讯地图API请求失败: HTTP {response.status_code}")
                return None

        except Exception as e:
            print(f"[位置服务] 腾讯地图API请求异常: {e}")
            return None


class LocationTool(BaseTool):
    """获取当前地理位置的工具"""

    name: str = "get_current_location"
    description: str = """获取用户当前的地理位置。

    【何时使用】
    1. 当需要推荐医院时 - 必须先调用此工具获取用户位置
    2. 当需要搜索本地服务时 - 获取位置以便进行本地化搜索
    3. 当用户询问"附近"、"本地"相关问题时
    4. 在进行医院推荐之前 - 必须先获取位置

    【重要】
    - 推荐医院前必须先调用此工具获取用户位置
    - 获取位置后，再调用搜索工具查找本地医院
    - 返回的信息包括：城市、省份、详细地址、经纬度

    【使用方法】
    不需要任何参数，直接调用即可
    """
    args_schema: type[BaseModel] = LocationInput

    _tencent_api: Any = None
    _cached_location: Optional[dict[str, Any]] = None

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        tencent_key = os.getenv("TENCENT_MAP_KEY")
        tencent_sk = os.getenv("TENCENT_MAP_SK")
        self._tencent_api = TencentMapAPI(tencent_key, tencent_sk)

    def _get_location_by_ip(self) -> dict[str, Any]:
        """使用IP地理定位服务获取位置，包含详细信息"""

        # 步骤1: 使用ipip.net获取公网IP地址
        ip = None
        try:
            response = httpx.get("http://myip.ipip.net", timeout=5)
            if response.status_code == 200:
                ip = response.text.strip()
                print(f"[位置服务] 获取到公网IP: {ip}")
        except Exception as e:
            print(f"[位置服务] 获取IP失败: {e}")

        # 步骤2: 使用ip-api.com从IP获取坐标
        lat, lon = None, None
        try:
            response = httpx.get(
                "http://ip-api.com/json/?fields=status,message,country,countryCode,region,regionName,city,district,zip,lat,lon,timezone,isp,org,as,query",
                timeout=10
            )
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "success":
                    lat = data.get("lat")
                    lon = data.get("lon")
                    if ip is None:
                        ip = data.get("query")
        except Exception:
            pass

        # 回退: 尝试使用ipinfo.io获取坐标
        if lat is None or lon is None:
            try:
                response = httpx.get("https://ipinfo.io/json", timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    loc = data.get("loc", "").split(",")
                    if len(loc) >= 2:
                        lat = float(loc[0])
                        lon = float(loc[1])
                    if ip is None:
                        ip = data.get("ip")
            except Exception:
                pass

        # 步骤3: 使用腾讯地图API获取精确地址(仅中国)
        if lat is not None and lon is not None:
            try:
                tencent_result = self._tencent_api.get_address(lat, lon)
                if tencent_result and tencent_result.get("code") == 200:
                    return {
                        "city": tencent_result.get("city", "Unknown") or tencent_result.get("county", "Unknown"),
                        "region": tencent_result.get("province", "Unknown"),
                        "district": tencent_result.get("county", ""),
                        "town": tencent_result.get("town", ""),
                        "country": tencent_result.get("nation", "中国"),
                        "address": tencent_result.get("address", ""),
                        "latitude": lat,
                        "longitude": lon,
                        "ip": ip or "Unknown",
                        "detailed_location": tencent_result.get("address", ""),
                        "source": "tencent_map_official"
                    }
            except Exception as e:
                print(f"[位置服务] 腾讯地图API调用失败: {e}")

        # 步骤4: 如果腾讯API失败，回退到ip-api.com数据
        try:
            response = httpx.get(
                "http://ip-api.com/json/?fields=status,message,country,countryCode,region,regionName,city,district,zip,lat,lon,timezone,isp,org,as,query",
                timeout=10
            )
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "success":
                    city = data.get("city", "Unknown")
                    region = data.get("regionName", "Unknown")
                    district = data.get("district", "")
                    country = data.get("country", "Unknown")

                    location_parts = []
                    if district:
                        location_parts.append(district)
                    if city != "Unknown":
                        location_parts.append(city)
                    if region != "Unknown" and region != city:
                        location_parts.append(region)
                    if country != "Unknown":
                        location_parts.append(country)

                    detailed_location = ", ".join(location_parts) if location_parts else "Unknown"

                    return {
                        "city": city,
                        "region": region,
                        "district": district,
                        "country": country,
                        "latitude": data.get("lat"),
                        "longitude": data.get("lon"),
                        "ip": data.get("query", "Unknown"),
                        "detailed_location": detailed_location,
                        "source": "ip-api.com"
                    }
        except Exception:
            pass

        return {
            "city": "Unknown",
            "region": "Unknown",
            "country": "Unknown",
            "detailed_location": "Unknown",
            "error": "无法从IP获取位置",
            "source": "failed"
        }

    def _run(self, method: str = "auto") -> str:
        """获取当前位置"""
        # 如果有缓存位置则返回
        if self._cached_location:
            loc = self._cached_location
            return self._format_location_output(loc)

        # 通过IP获取位置
        location_data = self._get_location_by_ip()
        self._cached_location = location_data

        if location_data.get("error"):
            return "无法确定位置。请提供您的城市名称以便推荐当地医院。"

        return self._format_location_output(location_data)

    def _format_location_output(self, loc: dict[str, Any]) -> str:
        """格式化位置数据用于输出，包含详细信息"""
        parts = []

        # 如果有详细位置则使用
        detailed = loc.get("detailed_location", "")
        if detailed and detailed != "Unknown":
            parts.append(f"位置: {detailed}")
        else:
            # 回退到城市/省份/国家
            city = loc.get("city", "Unknown")
            region = loc.get("region", "Unknown")
            country = loc.get("country", "Unknown")

            if city != "Unknown":
                parts.append(f"城市: {city}")
            if region != "Unknown" and region != city:
                parts.append(f"省份: {region}")
            if country != "Unknown":
                parts.append(f"国家: {country}")

        # 区县信息(如果有)
        district = loc.get("district")
        if district:
            parts.append(f"区县: {district}")

        # 街道信息(来自腾讯API)
        town = loc.get("town")
        if town:
            parts.append(f"街道: {town}")

        # 坐标
        lat = loc.get("latitude")
        lon = loc.get("longitude")
        if lat and lon:
            parts.append(f"坐标: {lat:.4f}, {lon:.4f}")

        # IP信息(用于调试)
        ip = loc.get("ip")
        if ip and ip != "Unknown":
            parts.append(f"IP: {ip}")

        # 数据来源
        source = loc.get("source", "unknown")
        parts.append(f"来源: {source}")

        return "当前位置:\n" + "\n".join([f"  - {p}" for p in parts])

    async def _arun(self, method: str = "auto") -> str:
        """异步获取当前位置"""
        return self._run(method)

    def get_location_dict(self) -> dict[str, Any]:
        """以字典形式获取位置供内部使用"""
        if not self._cached_location:
            self._cached_location = self._get_location_by_ip()
        return self._cached_location

    def get_city_name(self) -> str:
        """仅获取城市名称"""
        loc = self.get_location_dict()
        return loc.get("city", "Unknown")

    def get_detailed_location(self) -> str:
        """获取包含区县级别的详细位置字符串"""
        loc = self.get_location_dict()

        # 首先尝试使用detailed_location字段
        detailed = loc.get("detailed_location", "")
        if detailed and detailed != "Unknown":
            return detailed

        # 回退到从组件构建
        town = loc.get("town", "")
        district = loc.get("district", "")
        city = loc.get("city", "")
        region = loc.get("region", "")

        parts = []
        if town and town != "Unknown":
            parts.append(town)
        elif district and district != "Unknown":
            parts.append(district)
        if city and city != "Unknown":
            parts.append(city)
        if region and region != "Unknown" and region != city:
            parts.append(region)

        return ", ".join(parts) if parts else "Unknown"


class LocationManager:
    """处理位置相关操作的Manager"""

    def __init__(self):
        self.tool = LocationTool()

    def get_location(self) -> dict[str, Any]:
        """获取完整位置数据"""
        return self.tool.get_location_dict()

    def get_detailed_location(self) -> str:
        """获取详细位置"""
        return self.tool.get_detailed_location()
