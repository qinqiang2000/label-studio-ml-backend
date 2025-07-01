"""
This file contains tests for the API of your model. You can run these tests by installing test requirements:

    ```bash
    pip install -r requirements-test.txt
    ```
Then execute `pytest` in the directory of this file.

- Change `NewModel` to the name of the class in your model.py file.
- Change the `request` and `expected_response` variables to match the input and output of your model.
"""

import pytest
import json
from model import NewModel


@pytest.fixture
def client():
    from _wsgi import init_app
    app = init_app(model_class=NewModel)
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


def test_predict(client):
    request = {
        'tasks': [{
            "id": 661,
            'data': {
                "pdf": "<embed src='/data/local-files/?d=3/fc0fd018.pdf' width='100%' height='811px'/>",
                "filename": "1_3.pdf",
                "invoices_json": ""
            }
        }],
        # Your labeling configuration here
        'label_config': """
            <View style="display: flex;">
                <!-- 左侧：文档渲染区 -->
                <View style="flex: 75%;">
                    <!-- 用内嵌 HTML 渲染 PDF / 图片，也可换成 <Image> / <PDF> -->
                    <HyperText name="pdf" value="$pdf" inline="true" height="900px"/>
                </View>

                <!-- 右侧：字段校对区 -->
                <View style="flex: 30%;padding-left: 1em; border-left: 1px solid #ddd;">
                    <Text name="filename_display" value="$filename" /> 
                    <TextArea name="invoices_json"  value="$invoices_json" toName="pdf" editable="true" rows="39"/>

                    <Text name="comment_display" value="备注"/> 
                    <TextArea name="comment" toName="pdf" rows="1" displayMode="tag" showSubmitButton="false"/>
                </View>
            </View>
        """
    }

    expected_response = {
        'results': [{
            "model_version": "0.0.1",
            "score": 0.9,
            "result": [{
                "id": "vgzE336-a8",
                "from_name": "invoices_json",
                "to_name": "pdf",
                "type": "textarea",
                "value":  { 
                    "text": [
                        "[\n  {\n    \"docType\": \"invoice\",\n    \"nameOfInvoice\": \"料金明細\",\n    \"invoiceDate\": \"2025-05-01\",\n    \"totalAmount\": 759.0,\n    \"currency\": \"JPY\",\n    \"billToName\": \"ハイセンスジャパン\",\n    \"billToComposite\": \"横浜市都筑区茅ヶ崎東 4-5-5\",\n    \"billFromName\": \"東京ガス株式会社\",\n    \"purchaseOrderNumber\": \"1549-228-1066\",\n    \"detailOfGoodsOrServices\": [\n      {\n        \"articleName\": \"基本料金\",\n        \"grossAmount\": 759.0\n      }\n    ]\n  }\n]"
                    ]
                },
            }]
        }]
    }

    response = client.post('/predict', data=json.dumps(request), content_type='application/json')
    assert response.status_code == 200
    response = json.loads(response.data)
    assert response == expected_response
