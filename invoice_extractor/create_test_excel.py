#!/usr/bin/env python3
"""
Create a test Excel file for testing the /analyze endpoint
"""

import pandas as pd
import os
from datetime import datetime, timedelta
import numpy as np

def create_test_excel(filename="test_data.xlsx"):
    """Create a test Excel file with sample data"""
    
    # Create sample data for Sheet1 - Sales Data
    dates = pd.date_range(start='2024-01-01', end='2024-12-31', freq='D')[:100]
    sales_data = {
        '日期': dates,
        '产品名称': np.random.choice(['产品A', '产品B', '产品C', '产品D'], 100),
        '销售数量': np.random.randint(10, 100, 100),
        '单价': np.round(np.random.uniform(50, 500, 100), 2),
        '销售额': np.nan,  # Will calculate this
        '销售员': np.random.choice(['张三', '李四', '王五', '赵六'], 100),
        '地区': np.random.choice(['北京', '上海', '广州', '深圳', '杭州'], 100),
        '备注': np.random.choice(['正常', '促销', '批量', None], 100)
    }
    
    df1 = pd.DataFrame(sales_data)
    # Calculate sales amount
    df1['销售额'] = df1['销售数量'] * df1['单价']
    
    # Create sample data for Sheet2 - Customer Data  
    customer_data = {
        '客户ID': [f'C{i:04d}' for i in range(1, 51)],
        '客户名称': [f'客户{chr(65+i%26)}{i}' for i in range(50)],
        '联系电话': [f'138{np.random.randint(10000000, 99999999)}' for _ in range(50)],
        '邮箱': [f'customer{i}@example.com' for i in range(50)],
        '地址': np.random.choice(['北京市朝阳区', '上海市浦东新区', '广州市天河区', '深圳市南山区'], 50),
        '信用等级': np.random.choice(['A', 'B', 'C', 'D'], 50),
        '注册日期': pd.date_range(start='2020-01-01', end='2024-01-01', periods=50),
        '累计消费': np.round(np.random.uniform(1000, 50000, 50), 2)
    }
    
    df2 = pd.DataFrame(customer_data)
    
    # Create sample data for Sheet3 - Inventory Data
    inventory_data = {
        '商品编码': [f'P{i:04d}' for i in range(1, 31)],
        '商品名称': [f'商品{chr(65+i%26)}{i}' for i in range(30)],
        '类别': np.random.choice(['电子产品', '服装', '食品', '家居', '体育用品'], 30),
        '库存数量': np.random.randint(0, 1000, 30),
        '安全库存': np.random.randint(50, 200, 30),
        '采购价格': np.round(np.random.uniform(20, 300, 30), 2),
        '销售价格': np.round(np.random.uniform(30, 500, 30), 2),
        '供应商': np.random.choice(['供应商A', '供应商B', '供应商C', '供应商D'], 30),
        '最后进货日期': pd.date_range(start='2024-01-01', end='2024-12-31', periods=30)
    }
    
    df3 = pd.DataFrame(inventory_data)
    
    # Write to Excel file with multiple sheets
    with pd.ExcelWriter(filename, engine='openpyxl') as writer:
        df1.to_excel(writer, sheet_name='销售数据', index=False)
        df2.to_excel(writer, sheet_name='客户信息', index=False)  
        df3.to_excel(writer, sheet_name='库存管理', index=False)
    
    print(f"✅ Test Excel file created: {filename}")
    print(f"📊 File contains {len(df1)} sales records, {len(df2)} customers, {len(df3)} products")
    
    # Print file info
    file_size = os.path.getsize(filename)
    print(f"📁 File size: {file_size:,} bytes ({file_size/1024:.1f} KB)")
    
    return filename

if __name__ == "__main__":
    # Create test file
    test_file = create_test_excel("test_analysis.xlsx")
    
    print(f"\nTo test the analyze endpoint, run:")
    print(f"python test_analyze.py {test_file}") 