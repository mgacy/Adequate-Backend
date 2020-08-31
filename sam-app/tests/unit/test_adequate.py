import copy
from datetime import time
import json
from pathlib import Path
import unittest
from deal_check.adequate import delta_message, alert_message


class AdequateTestCase(unittest.TestCase):

    base_path = Path(__file__).parent
    def_deal = 'processed_deal_1.json'

    def load_deal(self, file):
        path = (self.base_path / 'data' / file).resolve()
        with open(path, 'r') as f:
            file_contents = json.load(f)
        return file_contents

    def setUp(self):
        self.current = self.load_deal(self.def_deal)

    def tearDown(self):
        self.current = None

    # alert_message

    def test_alert_message_single_price_min_1(self):
        current = self.current
        current['purchaseQuantity'] = {
            'maximumLimit': 3,
            'minimumLimit': 1
        }
        current['items'] = [
            {
                'price': 20
            }
        ]

        result = alert_message(current)

        expected_price_string = '$20'
        expected = {
            'message_type': 'new',
            'message': {
                'id': 'a6k310000004DvGAAU',
                'title': '2-Pack: Bamboo Pillows',
                'price_string': expected_price_string,
                'deal_url': 'https://meh.com/deals/2-pack--bamboo-pillows/checkout',  # noqa E501
                'image_url': 'https://res.cloudinary.com/mediocre/image/upload/v1468876208/huvffpdtsofwqgqt7ebq.png'  # noqa E501
            }
        }

        self.assertEqual(result, expected)

    def test_alert_message_single_price_min_2(self):
        current = self.current
        current['purchaseQuantity'] = {
            'maximumLimit': 4,
            'minimumLimit': 2
        }
        current['items'] = [
            {
                'price': 20
            }
        ]

        result = alert_message(current)

        expected_price_string = '$40'
        expected = {
            'message_type': 'new',
            'message': {
                'id': 'a6k310000004DvGAAU',
                'title': '2-Pack: Bamboo Pillows',
                'price_string': expected_price_string,
                'deal_url': 'https://meh.com/deals/2-pack--bamboo-pillows/checkout',  # noqa E501
                'image_url': 'https://res.cloudinary.com/mediocre/image/upload/v1468876208/huvffpdtsofwqgqt7ebq.png'  # noqa E501
            }
        }

        self.assertEqual(result, expected)

    def test_alert_message_multiple_prices_min_1(self):
        current = self.current
        current['purchaseQuantity'] = {
            'maximumLimit': 4,
            'minimumLimit': 1
        }
        current['items'] = [
            {
                'price': 20
            },
            {
                'price': 10
            }
        ]

        result = alert_message(current)

        expected_price_string = '$10 - $20'
        expected = {
            'message_type': 'new',
            'message': {
                'id': 'a6k310000004DvGAAU',
                'title': '2-Pack: Bamboo Pillows',
                'price_string': expected_price_string,
                'deal_url': 'https://meh.com/deals/2-pack--bamboo-pillows/checkout',  # noqa E501
                'image_url': 'https://res.cloudinary.com/mediocre/image/upload/v1468876208/huvffpdtsofwqgqt7ebq.png'  # noqa E501
            }
        }

        self.assertEqual(result, expected)

    def test_alert_message_multiple_prices_min_2(self):
        current = self.current
        current['purchaseQuantity'] = {
            'maximumLimit': 4,
            'minimumLimit': 2
        }
        current['items'] = [
            {
                'price': 20
            },
            {
                'price': 10
            }
        ]

        result = alert_message(current)

        expected_price_string = '$20 - $40'
        expected = {
            'message_type': 'new',
            'message': {
                'id': 'a6k310000004DvGAAU',
                'title': '2-Pack: Bamboo Pillows',
                'price_string': expected_price_string,
                'deal_url': 'https://meh.com/deals/2-pack--bamboo-pillows/checkout',  # noqa E501
                'image_url': 'https://res.cloudinary.com/mediocre/image/upload/v1468876208/huvffpdtsofwqgqt7ebq.png'  # noqa E501
            }
        }

        self.assertEqual(result, expected)

    # delta_message

    def test_delta_message_status_1(self):
        delta = self.current
        delta['id'] = 'current_deal'
        delta.pop('topic')
        deal_id = delta['dealID']

        result = delta_message(deal_id, delta)

        expected = {
            'message_type': 'delta',
            'message': {
                'id': 'a6k310000004DvGAAU',
                'delta_type': 'launchStatus',
                'delta_value': 'soldOut'
            }
        }

        self.assertEqual(result, expected)

    def test_delta_message_comment_1(self):
        delta = self.current
        delta['id'] = 'current_deal'
        delta.pop('launchStatus')
        deal_id = delta['dealID']

        result = delta_message(deal_id, delta)

        expected = {
            'message_type': 'delta',
            'message': {
                'id': 'a6k310000004DvGAAU',
                'delta_type': 'commentCount',
                'delta_value': 58
            }
        }

        self.assertEqual(result, expected)

    def test_delta_message_invalid(self):
        delta = self.current
        delta['id'] = 'current_deal'
        delta.pop('launchStatus')
        delta.pop('topic')
        deal_id = delta['dealID']

        self.assertRaises(
            ValueError, delta_message, deal_id, delta)
