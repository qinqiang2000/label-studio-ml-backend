import json
import re
import os
import time
from typing import List


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
    """返回仿真的发票数据
    
    Returns:
        str: 仿真的发票JSON数据字符串
    """
    time.sleep(5)  # 模拟处理时间
    return """
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


def should_use_mock_data():
    """检查是否应该使用仿真数据
    
    Returns:
        bool: 如果环境变量 USE_MOCK_DATA 设置为 'true' 或 '1'，返回 True
    """
    mock_env = os.environ.get('USE_MOCK_DATA', '').lower()
    return mock_env in ('true', '1', 'yes')