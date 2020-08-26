import unittest
from push_notification import apns


class APNSTestCase(unittest.TestCase):

    def_apns_category = 'MGDailyDealCategory'

    # def setUp(self):

    # def tearDown(self):

    # push_notification

    # push_background

    # make_new_deal_message

    # make_delta_message

    def test_delta_comment_1(self):
        deal_id = 'a6k5A000000kP9LQAU' 
        delta_type = 'commentCount'
        delta_value = 5
        
        message = {
            'id': deal_id,
            'delta_type': delta_type,
            'delta_value': delta_value
        }

        expected = (
            '{"aps": {"content-available": 1}, '
            '"deal-id": "a6k5A000000kP9LQAU", '
            '"adequate-delta-type": "commentCount", '
            '"adequate-delta-value": 5}'
        )

        result = apns.make_delta_message(message)
        self.assertEqual(result, expected)

    def test_delta_status_1(self):
        deal_id = 'a6k5A000000kP9LQAU' 
        delta_type = 'launchStatus'
        delta_value = 'launch'
        
        message = {
            'id': deal_id,
            'delta_type': delta_type,
            'delta_value': delta_value
        }

        expected = (
            '{"aps": {"content-available": 1}, '
            '"deal-id": "a6k5A000000kP9LQAU", '
            '"adequate-delta-type": "launchStatus", '
            '"adequate-delta-value": "launch"}'
        )
        
        result = apns.make_delta_message(message)
        self.assertEqual(result, expected)

    # publish_message

    # _make_notification

    # _parse_detail

    # _encode_message

    # verify_response
