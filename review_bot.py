"""
餐饮差评管理机器人 - 核心代码
功能：接收差评文本，调用DeepSeek API分析类型并生成回复
"""

import json
import time
from typing import Dict, List, Optional, Union

import requests


class DiningReviewAnalyzer:
    """餐饮差评分析与管理机器人"""

    def __init__(self, api_key: str, api_url: str = "https://api.deepseek.com/v1/chat/completions"):
        """
        初始化分析器

        Args:
            api_key: DeepSeek API密钥
            api_url: API端点地址
        """
        self.api_key = api_key
        self.api_url = api_url
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

    def _build_analysis_prompt(self, review: str) -> str:
        """构建分析差评类型的提示词"""
        return f"""你是一位餐饮行业差评分析专家。请分析以下顾客差评，返回JSON格式结果。

差评内容：{review}

请分析：
1. 差评类型（上菜慢/口味差/服务差/分量少/环境差/其他）
2. 严重程度（高/中/低）

判断标准：
- 高：涉及食品安全、健康损害、严重侮辱、法律纠纷
- 中：涉及服务质量、菜品质量明显问题
- 低：轻微不满、个人偏好、建议性意见

请只返回JSON格式，不要额外文字：
{{"类型": "xx", "严重度": "高/中/低"}}"""

    def _build_reply_prompt(self, review: str, analysis_type: str, severity: str) -> str:
        """构建生成回复文案的提示词"""
        return f"""你是一位餐饮店老板，正在回复顾客的差评。请根据以下信息生成回复。

顾客差评：{review}
差评类型：{analysis_type}
严重程度：{severity}

回复要求：
1. 真诚道歉 + 具体解释 + 解决方案 + 邀请再光临
2. 50-100字
3. 口语化，不模板化，像真人老板的语气
4. 不要推卸责任，不要机械套话
5. 对具体问题给出具体回应

请直接输出回复文案，不要加引号和额外文字。"""

    def _call_api(self, prompt: str, max_tokens: int = 500) -> Optional[str]:
        """
        调用DeepSeek API

        Args:
            prompt: 提示词
            max_tokens: 最大生成token数

        Returns:
            API返回的文本内容，失败返回None
        """
        payload = {
            "model": "deepseek-chat",
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "max_tokens": max_tokens,
            "temperature": 0.7
        }

        for attempt in range(3):
            try:
                response = requests.post(
                    self.api_url,
                    headers=self.headers,
                    json=payload,
                    timeout=30
                )
                response.raise_for_status()
                result = response.json()
                return result["choices"][0]["message"]["content"].strip()
            except requests.exceptions.RequestException as e:
                if attempt < 2:
                    time.sleep(2 ** attempt)  # 指数退避
                    continue
                print(f"API调用失败（已重试3次）: {e}")
                return None
            except (KeyError, json.JSONDecodeError) as e:
                print(f"API响应解析失败: {e}")
                return None

    def analyze_single(self, review: str) -> Optional[Dict[str, str]]:
        """
        分析单条差评

        Args:
            review: 差评文本

        Returns:
            {"类型": str, "严重度": str} 或 None
        """
        prompt = self._build_analysis_prompt(review)
        result = self._call_api(prompt, max_tokens=200)

        if not result:
            return None

        # 尝试提取JSON
        try:
            # 处理可能的markdown代码块
            if "```json" in result:
                result = result.split("```json")[1].split("```")[0].strip()
            elif "```" in result:
                result = result.split("```")[1].split("```")[0].strip()

            analysis = json.loads(result)
            # 验证字段
            if "类型" not in analysis or "严重度" not in analysis:
                raise ValueError("缺少必要字段")
            return analysis
        except (json.JSONDecodeError, ValueError) as e:
            print(f"解析分析结果失败: {e}, 原始结果: {result}")
            return None

    def generate_reply(self, review: str, analysis: Dict[str, str]) -> Optional[str]:
        """
        根据分析结果生成回复文案

        Args:
            review: 原始差评
            analysis: 分析结果 {"类型": str, "严重度": str}

        Returns:
            生成的回复文案或None
        """
        prompt = self._build_reply_prompt(
            review,
            analysis.get("类型", "其他"),
            analysis.get("严重度", "中")
        )
        return self._call_api(prompt, max_tokens=300)

    def process_review(self, review: str) -> Optional[Dict[str, Union[Dict[str, str], str]]]:
        """
        处理单条差评：分析 + 生成回复

        Args:
            review: 差评文本

        Returns:
            {"分析": {"类型": str, "严重度": str}, "回复": str} 或 None
        """
        analysis = self.analyze_single(review)
        if not analysis:
            return None

        reply = self.generate_reply(review, analysis)
        if not reply:
            return None

        return {
            "分析": analysis,
            "回复": reply
        }

    def process_batch(self, reviews: List[str]) -> List[Dict[str, Union[Dict[str, str], str]]]:
        """
        批量处理差评列表

        Args:
            reviews: 差评文本列表

        Returns:
            处理结果列表，每条包含分析和回复
        """
        results = []
        for i, review in enumerate(reviews):
            print(f"正在处理第 {i+1}/{len(reviews)} 条差评...")
            result = self.process_review(review)
            if result:
                results.append(result)
            else:
                # 处理失败时返回一个默认结果
                results.append({
                    "分析": {"类型": "其他", "严重度": "中"},
                    "回复": f"非常抱歉给您带来不好的体验！我们已经记录您提到的问题，会立即整改。希望您能给我们改进的机会，欢迎再次光临，我们将为您提供更好的服务。"
                })
            # 避免API限流
            if i < len(reviews) - 1:
                time.sleep(0.5)
        return results


def main():
    """主函数：演示批量处理差评"""
    # 请替换为你的API密钥
    API_KEY = "your-deepseek-api-key-here"

    # 测试差评样例
    test_reviews = [
        "服务极差，老板傲慢，无视客人投诉。一桌只能用一张券，服务员说分桌坐吧。打包菜装盒里不放袋，服务员把餐送餐桌上。",
        "宫保鸡丁里放黄瓜和胡萝卜，毛血旺放牛心切得超厚，米饭是凉的。四川人表示这根本不能叫川菜。",
        "吃出肠胃炎，上吐下泻两天。联系商家，商家说没医院证据不认，还说我恶意评价。",
        "点了蒜香鱼丸，结果全给的辣椒，下面什么都没放。白水煮灰面坨子，香菜也不给。",
        "芝士羽衣甘蓝里只有4块西柚3块橙子6粒葡萄干，T骨牛排发白像水泡解冻，蜜瓜火腿里3片比保鲜膜还薄的火腿。"
    ]

    # 初始化分析器
    analyzer = DiningReviewAnalyzer(API_KEY)

    # 批量处理
    print("开始批量处理差评...")
    results = analyzer.process_batch(test_reviews)

    # 输出结果
    print("\n=== 处理结果 ===")
    for i, result in enumerate(results):
        print(f"\n--- 差评 {i+1} ---")
        print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()