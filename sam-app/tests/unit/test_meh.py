from copy import deepcopy
import json
from pathlib import Path
import unittest
# from deal_check.adequate import meh
from deal_check.adequate.meh import _fix_empty_array, _parse_creation_date, _parse_model_numbers, _parse_response, _remove_duplicates


# NOTE: to run, use following from `/lambdaTest`
# `$ python3 -m unittest tests.test_meh_service`
class MehTestCase(unittest.TestCase):

    # Sample deal (processed)
    """
    {'createdAt': '2020-06-14T04:00:09.381Z',
     'dealYear': '2020',
     'features': "- At this point Roomba isn't just a robot vacuum ...',
     'id': 'a6k5A000000kKh5QAE',
     'items': [{'attributes': [],
            'condition': 'Refurbished',
            'id': '115048',
            'photo': 'https://d2b8wt72ktn9a2.cloudfront.net/mediocre/image/upload/c_pad,f_auto,h_600,q_auto,w_600/a9icodgwrvlm1xyqlclb.png',
            'price': 159}],
     'launches': [{'soldOutAt': None}, {'soldOutAt': None}],
     'modelNumbers': ['iRobot805'],
     'monthDay': '0614',
     'photos': ['https://d2b8wt72ktn9a2.cloudfront.net/mediocre/image/upload/c_pad,f_auto,h_600,q_auto,w_600/a9icodgwrvlm1xyqlclb.png',
            'https://d2b8wt72ktn9a2.cloudfront.net/mediocre/image/upload/c_pad,f_auto,h_600,q_auto,w_600/e7hqntl8um5zovuwq6n7.png',
            'https://d2b8wt72ktn9a2.cloudfront.net/mediocre/image/upload/c_pad,f_auto,h_600,q_auto,w_600/gbtmu8ur7tlhxwi5dx2h.png'],
     'purchaseQuantity': {'maximumLimit': 3, 'minimumLimit': 1},
     'specifications': 'Specs\r\n...',
     'story': {'body': 'In honor of this Refurbished Roomba 805 sale ...',
             'title': 'The Xerox Of Robot Vacuums'},
     'theme': {'accentColor': '#edeed9',
             'backgroundColor': '#7e7a7d',
             'backgroundImage': 'https://d2b8wt72ktn9a2.cloudfront.net/mediocre/image/upload/f_auto,h_1042,q_auto,w_1042/zaaeocesqos7omiluw58.png',
             'foreground': 'light'},
     'title': 'iRobot Roomba 805 Vacuum Cleaning Robot (Refurbished)',
     'topic': {'commentCount': 7,
             'createdAt': '2020-06-14T04:00:09.381Z',
             'id': '5ee5a0c9ee5dc612801231f7',
             'replyCount': 3,
             'url': 'https://meh.com/forum/topics/irobot-roomba-805-vacuum-cleaning-robot-refurbished-2',
             'voteCount': 0},
     'url': 'https://meh.com/deals/irobot-roomba-805-vacuum-cleaning-robot-refurbished-6'}
    """  # noqa E501

    base_path = Path(__file__).parent
    def_deal = 'meh_response_1.json'

    # def setUp(self):

    # def tearDown(self):

    def load_deal(self, file):
        path = (self.base_path / 'data' / file).resolve()
        with open(path, 'r') as f:
            file_contents = json.load(f)
        return file_contents

    # Request

    # Creation Date
    # def test_created_at_X(self):

    # - Deal has topic.createdAt
    def test_created_at_has_topic_created_at(self):
        # TODO: make class properties?
        topic_created_at = '2020-06-14T04:00:09.381Z'
        poll_start_date = ''
        response = {
            'deal': {
                'topic': {'commentCount': 7,
                          'createdAt': topic_created_at,
                          'id': '5ee5a0c9ee5dc612801231f7',
                          'replyCount': 3,
                          'url': 'https://meh.com/forum/topics/irobot',
                          'voteCount': 0}
            },
            'poll': {
                'id': '5ee44f400543030f38fed81c',
                'startDate': poll_start_date
            }
        }
        created_at = _parse_creation_date(response)
        self.assertEqual(created_at, topic_created_at)

    # - Deal has poll.startDate
    def test_created_at_has_poll_start_date(self):
        topic_created_at = None
        # TODO: make a different date?
        poll_start_date = '2020-06-14T04:00:09.381Z'
        response = {
            'deal': {
                'topic': {'commentCount': 7,
                          'createdAt': topic_created_at,
                          'id': '5ee5a0c9ee5dc612801231f7',
                          'replyCount': 3,
                          'url': 'https://meh.com/forum/topics/irobot',
                          'voteCount': 0}
            },
            'poll': {
                'id': '5ee44f400543030f38fed81c',
                'startDate': poll_start_date
            }
        }
        created_at = _parse_creation_date(response)
        self.assertEqual(created_at, poll_start_date)

    # - Deal has neither
    def test_created_at_has_neither(self):
        topic_created_at = None
        poll_start_date = None
        response = {
            'deal': {
                'topic': {'commentCount': 7,
                          'createdAt': topic_created_at,
                          'id': '5ee5a0c9ee5dc612801231f7',
                          'replyCount': 3,
                          'url': 'https://meh.com/forum/topics/irobot',
                          'voteCount': 0}
            },
            'poll': {
                'id': '5ee44f400543030f38fed81c',
                'startDate': poll_start_date
            }
        }
        created_at = _parse_creation_date(response)
        self.assertIsNotNone(created_at)

    # Model Numbers
    # def test_parse_model_numbers_X(self):

    # - Expected model numbers

    # - Missing model numbers

    # Empty Arrays
    # def test_empty_array_X(self):

    def test_empty_array_not_empty_and_nullable(self):
        """Verify method does not alter non-empty, nullable list."""
        key = 'attributes'
        item = {
            'id': 'A123B456C789',
            key: [
                {
                    'key': 'Color',
                    'value': 'Black'
                }
            ]
        }
        expected = deepcopy(item)
        result = _fix_empty_array(item, key, nullable=True)
        self.assertEqual(result, expected)

    def test_empty_array_not_empty_and_non_nullable(self):
        """Verify method does not alter non-empty, non-nullable list."""
        key = 'attributes'
        item = {
            'id': 'A123B456C789',
            key: [
                {
                    'key': 'Color',
                    'value': 'Black'
                }
            ]
        }
        expected = deepcopy(item)
        result = _fix_empty_array(item, key, nullable=False)
        self.assertEqual(result, expected)

    def test_empty_array_empty_and_nullable(self):
        key = 'attributes'
        item = {
            'id': 'A123B456C789',
            key: []
        }
        expected = {
            'id': 'A123B456C789',
            key: [None]
        }
        result = _fix_empty_array(item, key, nullable=True)
        self.assertEqual(result, expected)

    def test_empty_array_empty_and_non_nullable(self):
        key = 'attributes'
        item = {
            'id': 'A123B456C789',
            key: []
        }
        expected = {
            'id': 'A123B456C789',
            key: None
        }
        result = _fix_empty_array(item, key, nullable=False)
        self.assertEqual(result, expected)

    def test_empty_array_missing_and_nullable(self):
        key = 'attributes'
        item = {
            'id': 'A123B456C789'
        }
        expected = {
            'id': 'A123B456C789',
            key: [None]
        }
        result = _fix_empty_array(item, key, nullable=True)
        self.assertEqual(result, expected)

    def test_empty_array_missing_and_non_nullable(self):
        key = 'attributes'
        item = {
            'id': 'A123B456C789'
        }
        expected = {
            'id': 'A123B456C789',
            key: None
        }
        result = _fix_empty_array(item, key, nullable=False)
        self.assertEqual(result, expected)

    # Parse Response
    # def test_parse_response_X(self):

    def test_parse_response_added_custom_attributes(self):
        meh_response = self.load_deal(self.def_deal)

        result = _parse_response(meh_response)

        self.assertIsNotNone(result.get('dealID'))
        self.assertIsNotNone(result.get('createdAt'))
        # self.assertIsNotNone(result.get('model_numbers'))
        self.assertIsNotNone(result.get('launchStatus'))

    def test_remove_duplicates(self):
        expected = ['1', '2', '3', '4', '5']
        photos = ['1', '2', '3', '2', '4', '1', '5']

        result = _remove_duplicates(photos)
        self.assertEqual(result, expected)
