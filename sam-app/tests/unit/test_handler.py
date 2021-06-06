import json
import unittest
# Fix imports
import os, sys
from pathlib import Path
base_path = Path(__file__).parent.parent.parent
DEAL_CHECK = (base_path / 'deal_check').resolve()
sys.path.insert(0, str(DEAL_CHECK))

# Environment Vars
os.environ['API_ENDPOINT'] = ''
os.environ['MEH_API_KEY'] = ''
os.environ['TOPIC_ARN'] = ''
os.environ['BUCKET_NAME'] = ''
os.environ['AWS_LAMBDA_FUNCTION_NAME'] = ''

from deal_check import app


def scheduled_event():
    """ Generates Lambda Event"""

    return {
        "id": "cdc73f9d-aea9-11e3-9d5a-835b769c0d9c",
        "detail-type": "Scheduled Event",
        "source": "aws.events",
        "account": "123456789012",
        "time": "1970-01-01T00:00:00Z",
        "region": "{region}",
        "resources": [
            "arn:{partition}:events:{region}:123456789012:rule/my-schedule"
        ],
        "detail": {}
    }


class DealCheckHandlerTestCase(unittest.TestCase):

    def test_handler(self):
        ret = app.lambda_handler(scheduled_event(), "")
        # data = json.loads(ret["body"])
        self.assertEqual(ret["statusCode"], 200)
