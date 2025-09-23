import json
import re
import os
import time
from typing import List, Dict, Any, Optional


def extract_json(text) -> List[dict]:
    """Extracts JSON content from a string where JSON is embedded between ```json and ``` tags.

    Parameters:
        text (str): The text containing the JSON content.

    Returns:
        list: A list of extracted JSON strings.
    """
    # Define the regular expression pattern to match JSON blocks
    pattern = r"\`\`\`json(.*?)\`\`\`"

    # Find all non-overlapping matches of the pattern in the string
    matches = re.findall(pattern, text, re.DOTALL)

    # Return the list of matched JSON strings, stripping any leading or trailing whitespace
    try:
        return [match.strip() for match in matches]
    except Exception:
        raise ValueError(f"Failed to parse: {text}")


def get_mock_invoice_data():
    """返回仿真的发票数据，优先从 mock.json 读取，若失败则使用硬编码数据。

    Returns:
        str: 仿真的发票JSON数据字符串
    """
    mock_file_path = os.path.join(os.path.dirname(__file__), 'mock.json')
    default_data = """
    [{
        "docType": "invoice",
        "nameOfInvoice": "御請求書",
        "invoiceNumber": "20393",
        "invoiceDate": "2025-05-02",
        "totalAmount": 23210935.00,
        "totalTaxAmount": 2110085.00,
        "currency": "JPY",
        "billToName": "TVS REGZA株式会社",
        "billFromName": "株式会社 ヒト・コミュニケーションズ",
        "lineItems": [
            {
                "description": "コールセンター業務委託料",
                "quantity": 1,
                "unitPrice": 21100850.00,
                "totalPrice": 21100850.00,
                "taxAmount": 2110085.00
            }
        ]
    }]
    """

    if os.path.exists(mock_file_path):
        try:
            with open(mock_file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                if content.strip(): # 检查内容是否为空
                    # 尝试解析JSON以确保其有效性，但函数本身应返回字符串
                    json.loads(content) 
                    time.sleep(1) # 模拟从文件读取的轻微延迟
                    return content
        except (IOError, json.JSONDecodeError) as e:
            print(f"Error reading or parsing mock.json: {e}. Falling back to default data.")
            # 如果读取或解析失败，则使用默认数据
            pass # 继续执行并返回默认数据

    time.sleep(5)  # 模拟处理时间（仅当使用默认数据时）
    return default_data


def should_use_mock_data():
    """检查是否应该使用仿真数据

    Returns:
        bool: 如果环境变量 USE_MOCK_DATA 设置为 'true' 或 '1'，返回 True
    """
    mock_env = os.environ.get('USE_MOCK_DATA', '').lower()
    return mock_env in ('true', '1', 'yes')


def format_prompt_template(prompt: str, task_data: Optional[Dict[str, Any]] = None) -> str:
    """格式化提示模板，替换占位符

    将提示中的 {{key}} 格式占位符替换为 task_data 中对应键的值。
    如果找不到对应的键，占位符将保持不变。

    Args:
        prompt: 包含占位符的提示模板
        task_data: 任务数据字典，通常来自 task['data']

    Returns:
        str: 替换占位符后的提示文本

    Examples:
        >>> task_data = {"filename": "american", "type": "invoice"}
        >>> prompt = "分析来自{{filename}}的{{type}}"
        >>> format_prompt_template(prompt, task_data)
        '分析来自american的invoice'

        >>> # 缺失的键保持不变
        >>> prompt = "处理{{filename}}和{{missing_key}}"
        >>> format_prompt_template(prompt, {"filename": "test"})
        '处理test和{{missing_key}}'
    """
    if not prompt or not task_data:
        return prompt

    # 使用正则表达式查找所有 {{key}} 格式的占位符
    placeholder_pattern = r'\{\{([^}]+)\}\}'

    def replace_placeholder(match):
        key = match.group(1).strip()

        # 从 task_data 中获取对应的值
        if key in task_data:
            value = task_data[key]
            # 确保返回字符串格式
            if isinstance(value, str):
                return value
            elif value is not None:
                return str(value)

        # 如果找不到对应的键，保持占位符不变
        return match.group(0)

    # 替换所有占位符
    formatted_prompt = re.sub(placeholder_pattern, replace_placeholder, prompt)

    return formatted_prompt